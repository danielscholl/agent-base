"""Skill context provider for dynamic instruction injection.

This module provides progressive skill documentation using Agent Framework's
ContextProvider pattern. Skill documentation is injected on-demand based on
user queries and trigger matching, avoiding constant token overhead.
"""

import logging
import re
from collections.abc import MutableSequence
from typing import Any

from agent_framework import ChatMessage, Context, ContextProvider

from agent.skills.documentation_index import SkillDocumentationIndex

logger = logging.getLogger(__name__)


class SkillContextProvider(ContextProvider):
    """Progressive skill documentation with on-demand registry.

    Implements three-tier progressive disclosure:
    1. Minimal breadcrumb (~10 tokens) when skills exist but don't match
    2. Full registry (10-15 tokens/skill) when user asks about capabilities
    3. Full documentation (hundreds of tokens) when triggers match

    Example:
        >>> skill_docs = SkillDocumentationIndex()
        >>> provider = SkillContextProvider(skill_docs, max_skills=3)
        >>> agent = chat_client.create_agent(
        ...     name="Agent",
        ...     instructions="...",
        ...     context_providers=[provider]
        ... )
    """

    def __init__(
        self,
        skill_docs: SkillDocumentationIndex,
        memory_manager: Any | None = None,
        max_skills: int = 3,
        max_all_skills: int = 10,
    ):
        """Initialize skill context provider.

        Args:
            skill_docs: SkillDocumentationIndex with loaded skill metadata
            memory_manager: Optional memory manager for conversation context (unused)
            max_skills: Maximum number of skills to inject when matched (default: 3)
            max_all_skills: Cap for "show all skills" to prevent overflow (default: 10)
        """
        self.skill_docs = skill_docs
        self.memory_manager = memory_manager  # For conversation context (future use)
        self.max_skills = max_skills
        self.max_all_skills = max_all_skills

    async def invoking(
        self, messages: ChatMessage | MutableSequence[ChatMessage], **kwargs: Any
    ) -> Context:
        """Inject skill documentation based on request relevance.

        Args:
            messages: Current conversation messages
            **kwargs: Additional context

        Returns:
            Context with appropriate skill documentation
        """
        # 1. Extract current user message
        current_message = self._get_latest_user_message(messages)
        if not current_message:
            return Context()

        # 2. Check if user is asking about capabilities
        if self._wants_skill_info(current_message):
            return self._inject_skill_registry()

        # 3. Check for "show all skills" escape hatch
        if self._wants_all_skills(current_message):
            return self._inject_all_skills_capped()

        # 4. Match skills based on current message
        relevant_skills = self._match_skills_safely(current_message.lower())

        # 5. Build response based on matches
        if relevant_skills:
            # Inject full documentation for matched skills
            docs = self._build_skill_documentation(relevant_skills[: self.max_skills])
            logger.debug(
                f"Injecting {len(relevant_skills[:self.max_skills])} skill(s) documentation"
            )
            return Context(instructions=docs)
        elif self.skill_docs.has_skills():
            # Hybrid Tier-1 approach:
            # - If any skill has explicit triggers (beyond auto-added name) → minimal breadcrumb
            # - If no skills have explicit triggers → full registry (better discovery)
            if self._any_skill_has_explicit_triggers():
                # Minimal breadcrumb: skill count only
                breadcrumb = f"[{self.skill_docs.count()} skills available]"
                logger.debug(
                    f"No skill match - injecting minimal breadcrumb ({self.skill_docs.count()} skills with triggers)"
                )
                return Context(instructions=breadcrumb)
            else:
                # No triggers defined yet → use registry for LLM discovery
                logger.debug(
                    "No skill match - injecting full registry (no skills have structured triggers)"
                )
                return self._inject_skill_registry()
        else:
            # No skills installed - inject nothing
            return Context()

    def _any_skill_has_explicit_triggers(self) -> bool:
        """Check if any skill has explicit structured triggers (beyond skill name).

        Returns:
            True if at least one skill has more than just its name as a keyword,
            or has verbs or patterns defined.
        """
        for skill in self.skill_docs.get_all_metadata():
            triggers = skill.get("triggers", {})
            keywords = triggers.get("keywords", [])
            # The first keyword is always the skill name (auto-added by model_post_init)
            # Explicit triggers exist if there are additional keywords, verbs, or patterns
            if len(keywords) > 1 or triggers.get("verbs") or triggers.get("patterns"):
                return True
        return False

    def _inject_skill_registry(self) -> Context:
        """Inject skill registry with brief descriptions for LLM-driven discovery."""
        lines = ["## Available Skills\n"]
        for skill in self.skill_docs.get_all_metadata():
            # Include brief description for discoverability (10-15 tokens per skill)
            brief = skill["brief_description"][:80]  # Slightly longer for clarity
            lines.append(f"- **{skill['name']}**: {brief}")

        lines.append(
            "\nWhen you need current information, specialized data, or capabilities "
            "beyond your knowledge, consider whether one of these skills could help. "
            "Skill scripts are available via the script_run tool."
        )
        registry_text = "\n".join(lines)
        logger.debug(f"Injecting skill registry with {self.skill_docs.count()} skills")
        return Context(instructions=registry_text)

    def _wants_skill_info(self, message: str) -> bool:
        """Check if user is asking about capabilities."""
        info_patterns = [
            r"\bwhat.*(?:can|could).*(?:you|u).*do\b",
            r"\b(?:show|list).*capabilities\b",
            r"\bwhat.*skills?\b",
        ]
        message_lower = message.lower()
        return any(re.search(pattern, message_lower) for pattern in info_patterns)

    def _wants_all_skills(self, message: str) -> bool:
        """Check if user wants to see all skill documentation."""
        all_patterns = [
            r"\bshow.*all.*skills?\b",
            r"\blist.*all.*skills?\b",
            r"\ball.*skill.*(?:documentation|docs)\b",
        ]
        message_lower = message.lower()
        return any(re.search(pattern, message_lower) for pattern in all_patterns)

    def _match_skills_safely(self, context: str) -> list[dict]:
        """Match skills with word boundaries and error handling.

        Args:
            context: User message text (lowercase)

        Returns:
            List of matched skill metadata dictionaries
        """
        matched = []
        seen = set()

        for skill in self.skill_docs.get_all_metadata():
            skill_id = skill["name"]
            if skill_id in seen:
                continue

            skill_name_lower = skill["name"].lower()
            triggers = skill.get("triggers", {})

            # Check if triggers dict is effectively empty (no keywords, verbs, or patterns)
            has_triggers = bool(
                triggers.get("keywords") or triggers.get("verbs") or triggers.get("patterns")
            )

            # If no triggers defined, only match by skill name (restrictive fallback)
            if not has_triggers:
                try:
                    if re.search(rf"\b{re.escape(skill_name_lower)}\b", context):
                        matched.append(skill)
                        seen.add(skill_id)
                except re.error as e:
                    logger.warning(f"Regex error matching skill name '{skill_name_lower}': {e}")
                continue

            # Strategy 1: Skill name mentioned (word boundary)
            try:
                if re.search(rf"\b{re.escape(skill_name_lower)}\b", context):
                    matched.append(skill)
                    seen.add(skill_id)
                    continue
            except re.error as e:
                logger.warning(f"Regex error matching skill name '{skill_name_lower}': {e}")

            # Strategy 2: Keyword triggers (word boundary)
            for keyword in triggers.get("keywords", []):
                try:
                    if re.search(rf"\b{re.escape(keyword.lower())}\b", context):
                        matched.append(skill)
                        seen.add(skill_id)
                        break
                except re.error as e:
                    logger.warning(f"Regex error matching keyword '{keyword}': {e}")

            if skill_id in seen:
                continue

            # Strategy 3: Verb triggers (word boundary)
            for verb in triggers.get("verbs", []):
                try:
                    if re.search(rf"\b{re.escape(verb.lower())}\b", context):
                        matched.append(skill)
                        seen.add(skill_id)
                        break
                except re.error as e:
                    logger.warning(f"Regex error matching verb '{verb}': {e}")

            if skill_id in seen:
                continue

            # Strategy 4: Pattern matching (with error handling)
            for pattern in triggers.get("patterns", []):
                try:
                    if re.search(pattern, context, re.IGNORECASE):
                        matched.append(skill)
                        seen.add(skill_id)
                        break
                except re.error as e:
                    logger.warning(f"Invalid regex pattern for {skill_id}: {pattern} - {e}")

        return matched

    def _build_skill_documentation(self, skills: list[dict]) -> str:
        """Build full documentation for matched skills.

        Args:
            skills: List of skill metadata dictionaries

        Returns:
            Formatted skill documentation string
        """
        docs = ["## Relevant Skill Documentation\n"]
        for skill in skills:
            docs.append(f"### {skill['name']}\n")
            docs.append(skill.get("instructions", ""))
            docs.append("")
        return "\n".join(docs)

    def _inject_all_skills_capped(self) -> Context:
        """Inject skill documentation with cap to avoid context overflow."""
        all_skills = self.skill_docs.get_all_metadata()

        if len(all_skills) <= self.max_all_skills:
            # Show all if under cap
            docs = self._build_skill_documentation(all_skills)
        else:
            # Show capped list with note
            docs = self._build_skill_documentation(all_skills[: self.max_all_skills])
            docs += f"\n\n*Showing {self.max_all_skills} of {len(all_skills)} skills. "
            docs += "Ask about specific skills for more details.*"

        logger.debug(f"Injecting all skills (capped at {self.max_all_skills})")
        return Context(instructions=docs)

    def _get_latest_user_message(self, messages: ChatMessage | MutableSequence[ChatMessage]) -> str:
        """Extract the latest user message.

        Args:
            messages: Current conversation messages

        Returns:
            Latest user message text or empty string
        """
        msg_list = messages if isinstance(messages, MutableSequence) else [messages]

        # Find user message (robust extraction like MemoryContextProvider)
        for msg in reversed(msg_list):
            role = str(getattr(msg, "role", ""))
            if "user" in role.lower():
                return self._extract_message_text(msg)

        return ""

    def _extract_message_text(self, msg: ChatMessage) -> str:
        """Extract text from a ChatMessage (copied from MemoryContextProvider).

        Args:
            msg: Chat message

        Returns:
            Message text or empty string
        """
        # Try different attributes the message might have
        if hasattr(msg, "text"):
            return str(msg.text)
        elif hasattr(msg, "content"):
            content = msg.content
            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                # Handle list of content items
                texts = []
                for item in content:
                    if hasattr(item, "text"):
                        texts.append(str(item.text))
                    elif isinstance(item, dict) and "text" in item:
                        texts.append(str(item["text"]))
                return " ".join(texts) if texts else ""
            else:
                return str(content)
        else:
            # Fallback to string representation
            return str(msg) if msg else ""
