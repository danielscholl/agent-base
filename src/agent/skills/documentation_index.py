"""In-memory skill documentation index for runtime context injection.

This module provides SkillDocumentationIndex for runtime documentation management,
separate from SkillRegistry which handles persistent install metadata.
"""

from dataclasses import dataclass
from typing import Any

from agent.skills.manifest import SkillManifest


@dataclass
class SkillDocumentation:
    """Runtime documentation for a single skill."""

    name: str
    brief_description: str
    triggers: dict[str, list[str]]  # {keywords: [], verbs: [], patterns: []}
    instructions: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for context provider."""
        return {
            "name": self.name,
            "brief_description": self.brief_description,
            "triggers": self.triggers,
            "instructions": self.instructions,
        }


class SkillDocumentationIndex:
    """In-memory index of skill documentation for context injection.

    Separate from SkillRegistry to avoid mixing persistent install
    metadata with runtime documentation. This index is built at agent
    initialization and used by SkillContextProvider for progressive disclosure.

    Example:
        >>> skill_docs = SkillDocumentationIndex()
        >>> skill_docs.add_skill("hello-extended", manifest)
        >>> skill_docs.has_skills()
        True
        >>> skill_docs.count()
        1
        >>> metadata = skill_docs.get_all_metadata()
    """

    def __init__(self) -> None:
        self._skills: dict[str, SkillDocumentation] = {}

    def add_skill(self, name: str, manifest: SkillManifest) -> None:
        """Add skill documentation from manifest.

        Args:
            name: Canonical skill name (normalized)
            manifest: Parsed SkillManifest with instructions and triggers
        """
        # Convert triggers to dict format with consistent structure
        triggers_dict = {
            "keywords": manifest.triggers.keywords if manifest.triggers else [],
            "verbs": manifest.triggers.verbs if manifest.triggers else [],
            "patterns": manifest.triggers.patterns if manifest.triggers else [],
        }

        self._skills[name] = SkillDocumentation(
            name=name,
            brief_description=manifest.brief_description or manifest.description[:80],
            triggers=triggers_dict,
            instructions=manifest.instructions,
        )

    def get_all_metadata(self) -> list[dict[str, Any]]:
        """Get all skill metadata for matching.

        Returns:
            List of skill metadata dictionaries with name, brief_description,
            triggers, and instructions fields.
        """
        return [skill.to_dict() for skill in self._skills.values()]

    def has_skills(self) -> bool:
        """Check if any skills are loaded.

        Returns:
            True if at least one skill is in the index.
        """
        return bool(self._skills)

    def count(self) -> int:
        """Get number of loaded skills.

        Returns:
            Number of skills in the index.
        """
        return len(self._skills)
