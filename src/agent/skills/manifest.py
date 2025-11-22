"""Skill manifest schema and parsing.

This module defines Pydantic models for SKILL.md manifests and provides
utilities for extracting and parsing YAML front matter.

The SKILL.md format follows this structure:
```yaml
---
name: skill-name
description: Brief description of the skill
version: 1.0.0
---

# Skill Documentation
Markdown instructions for using the skill...
```
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from agent.skills.errors import SkillManifestError


class SkillTriggers(BaseModel):
    """Structured triggers for skill matching."""

    keywords: list[str] = Field(default_factory=list)  # Direct keyword matches
    verbs: list[str] = Field(default_factory=list)  # Action verbs
    patterns: list[str] = Field(default_factory=list)  # Regex patterns


class SkillManifest(BaseModel):
    """Pydantic model for SKILL.md YAML front matter.

    Required fields:
        name: Skill identifier (alphanumeric + hyphens/underscores, max 64 chars)
        description: Brief description (max 500 chars)

    Optional fields:
        version: Semantic version (e.g., "1.0.0")
        author: Author name
        repository: Git repository URL
        license: License identifier (e.g., "MIT")
        min_agent_base_version: Minimum compatible agent-base version
        max_agent_base_version: Maximum compatible agent-base version
        toolsets: List of Python toolset classes to load ("module:Class" format)
        scripts: List of script names (auto-discovered if omitted)
        scripts_ignore: Glob patterns to exclude from script discovery
        permissions: Environment variable allowlist for script execution

    Example:
        >>> manifest = SkillManifest(
        ...     name="kalshi-markets",
        ...     description="Access Kalshi prediction market data"
        ... )
    """

    # Required fields
    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field(..., min_length=1, max_length=500)

    # Optional fields
    version: str | None = None
    author: str | None = None
    repository: str | None = None
    license: str | None = None
    min_agent_base_version: str | None = None
    max_agent_base_version: str | None = None
    default_enabled: bool = True  # Default enabled state for bundled skills
    toolsets: list[str] = Field(default_factory=list)
    scripts: list[str] | None = None  # None = auto-discover
    scripts_ignore: list[str] = Field(default_factory=list)
    permissions: dict[str, list[str]] = Field(default_factory=dict)

    # Markdown instructions (not in YAML, extracted separately)
    instructions: str = ""

    # Progressive disclosure fields
    brief_description: str | None = None  # One-line description for registry
    triggers: SkillTriggers | None = None  # Structured triggers for matching

    def model_post_init(self, __context: Any) -> None:
        """Auto-generate brief description and add skill name as trigger."""
        # Auto-generate brief description if not provided
        if not self.brief_description:
            # Take first sentence or first 80 chars, ensuring word boundaries
            desc = self.description or ""
            if "." in desc:
                first_sentence = desc.split(".", 1)[0].strip()
            else:
                first_sentence = desc.strip()

            if len(first_sentence) > 80:
                # Truncate at last space before 77 chars, add "..."
                cutoff = first_sentence[:77].rfind(" ")
                if cutoff == -1:
                    self.brief_description = first_sentence[:77] + "..."
                else:
                    self.brief_description = first_sentence[:cutoff] + "..."
            else:
                self.brief_description = first_sentence

        # Ensure triggers exists (creates new instance, not mutating default)
        if self.triggers is None:
            self.triggers = SkillTriggers()

        # Add skill name as implicit trigger (case-insensitive check)
        # Creates new list to avoid mutating shared defaults
        skill_name_lower = self.name.lower()
        existing_keywords_lower = [kw.lower() for kw in self.triggers.keywords]
        if skill_name_lower not in existing_keywords_lower:
            # Create new list with skill name added
            self.triggers = SkillTriggers(
                keywords=self.triggers.keywords + [skill_name_lower],
                verbs=self.triggers.verbs,
                patterns=self.triggers.patterns,
            )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate skill name format.

        Must be alphanumeric + hyphens/underscores only, 1-64 characters.
        """
        if not re.match(r"^[a-zA-Z0-9_-]{1,64}$", v):
            raise ValueError("Skill name must be alphanumeric with hyphens/underscores, 1-64 chars")
        return v

    @field_validator("toolsets")
    @classmethod
    def validate_toolsets(cls, v: list[str]) -> list[str]:
        """Validate toolset format (module:Class)."""
        for toolset in v:
            if ":" not in toolset:
                raise ValueError(f"Toolset '{toolset}' must be in 'module:Class' format")
        return v

    @field_validator("scripts")
    @classmethod
    def validate_scripts(cls, v: list[str] | None) -> list[str] | None:
        """Normalize script names (accept both 'status' and 'status.py')."""
        if v is None:
            return None
        # Accept both formats, will normalize later
        return v


class SkillRegistryEntry(BaseModel):
    """Pydantic model for skill registry persistence.

    Tracks installed skills with metadata for reproducibility and trust.

    Fields:
        name: Display name (original case preserved)
        name_canonical: Normalized for matching (lowercase, hyphens)
        git_url: Git repository URL (None for bundled/local skills)
        commit_sha: Pinned commit for reproducibility
        branch: Git branch (e.g., "main")
        tag: Git tag (e.g., "v1.0.0")
        installed_path: Absolute path to skill directory
        trusted: User explicitly approved (bundled=True, git requires confirmation)
        installed_at: Installation timestamp

    Example:
        >>> entry = SkillRegistryEntry(
        ...     name="kalshi-markets",
        ...     name_canonical="kalshi-markets",
        ...     git_url=None,
        ...     installed_path=Path("/path/to/skills/core/kalshi-markets"),
        ...     trusted=True
        ... )
    """

    name: str
    name_canonical: str
    git_url: str | None = None
    commit_sha: str | None = None
    branch: str | None = None
    tag: str | None = None
    installed_path: Path
    trusted: bool = False
    installed_at: datetime = Field(default_factory=datetime.now)

    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            Path: str,
            datetime: lambda v: v.isoformat(),
        },
    }


def extract_yaml_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Extract YAML front matter from SKILL.md content.

    SKILL.md format:
    ```
    ---
    name: skill-name
    description: Brief description
    ---

    # Markdown instructions...
    ```

    Args:
        content: Full SKILL.md file content

    Returns:
        Tuple of (yaml_data, markdown_instructions)

    Raises:
        SkillManifestError: If YAML front matter is missing or malformed
    """
    # Match YAML front matter between --- markers
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)"
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        raise SkillManifestError(
            "SKILL.md must start with YAML front matter delimited by '---' markers"
        )

    yaml_content = match.group(1)
    markdown_content = match.group(2).strip()

    try:
        yaml_data = yaml.safe_load(yaml_content)
        if not isinstance(yaml_data, dict):
            raise SkillManifestError("YAML front matter must be a dictionary")
    except yaml.YAMLError as e:
        raise SkillManifestError(f"Invalid YAML front matter: {e}")

    return yaml_data, markdown_content


def parse_skill_manifest(skill_path: Path) -> SkillManifest:
    """Parse SKILL.md manifest from a skill directory.

    Args:
        skill_path: Path to skill directory containing SKILL.md

    Returns:
        Parsed SkillManifest with YAML data and instructions

    Raises:
        SkillManifestError: If SKILL.md is missing, malformed, or invalid
    """
    manifest_path = skill_path / "SKILL.md"

    if not manifest_path.exists():
        raise SkillManifestError(f"SKILL.md not found in {skill_path}")

    try:
        content = manifest_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise SkillManifestError("SKILL.md must be UTF-8 encoded")

    yaml_data, instructions = extract_yaml_frontmatter(content)

    # Add instructions to the data for model creation
    yaml_data["instructions"] = instructions

    try:
        return SkillManifest(**yaml_data)
    except Exception as e:
        raise SkillManifestError(f"Invalid SKILL.md manifest: {e}")
