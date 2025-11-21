"""Core Agent class with multi-provider LLM support."""

import logging
import os
import re
from collections.abc import AsyncIterator
from importlib import resources
from pathlib import Path
from typing import Any, cast

from agent.config import load_config
from agent.config.schema import AgentSettings
from agent.tools.filesystem import FileSystemTools
from agent.tools.hello import HelloTools
from agent.tools.toolset import AgentToolset

logger = logging.getLogger(__name__)


class Agent:
    """Agent with multi-provider LLM support and extensible tools.

    Supports seven LLM providers through Microsoft Agent Framework:
    - OpenAI: Direct OpenAI API
    - Anthropic: Direct Anthropic API
    - Azure OpenAI: Azure-hosted OpenAI models
    - Azure AI Foundry: Microsoft's managed AI platform
    - Google Gemini: Google's Gemini models (custom integration)
    - GitHub Models: GitHub's AI models via OpenAI-compatible API
    - Local (Docker Models): Local models via Docker Desktop

    Example:
        >>> from agent.config import load_config
        >>> settings = load_config()
        >>> agent = Agent(settings)
        >>> response = await agent.run("Say hello")
        >>> print(response)
        Hello! How can I help you today?
    """

    def __init__(
        self,
        settings: AgentSettings | None = None,
        chat_client: Any | None = None,
        toolsets: list[AgentToolset] | None = None,
        middleware: list | None = None,
        memory_manager: Any | None = None,
    ):
        """Initialize Agent.

        Args:
            settings: Agent settings (loads from file + env if not provided)
            chat_client: Chat client for testing (optional, for dependency injection)
            toolsets: List of toolsets (default: HelloTools, FileSystemTools)
            middleware: List of middleware (framework auto-categorizes by type)
            memory_manager: Memory manager for conversation storage (optional)

        Example:
            # Production use
            >>> from agent.config import load_config
            >>> settings = load_config()
            >>> agent = Agent(settings)

            # Testing with mocks
            >>> from tests.mocks import MockChatClient
            >>> from tests.fixtures.config import mock_openai_settings
            >>> settings = mock_openai_settings()
            >>> mock_client = MockChatClient(response="Test response")
            >>> agent = Agent(settings=settings, chat_client=mock_client)

            # With custom middleware
            >>> from agent.middleware import create_middleware
            >>> mw = create_middleware()
            >>> agent = Agent(settings=settings, middleware=mw)
        """
        self.settings = settings or load_config()
        # Legacy alias for compatibility during migration
        self.config = self.settings

        # Dependency injection for testing
        if chat_client is not None:
            self.chat_client = chat_client
        else:
            self.chat_client = self._create_chat_client()

        # Initialize memory manager if enabled
        if memory_manager is not None:
            self.memory_manager = memory_manager
        elif self.settings.memory_enabled:
            from agent.memory import create_memory_manager

            self.memory_manager = create_memory_manager(self.settings)
            logger.info(f"Memory enabled: {self.settings.memory_type}")
        else:
            self.memory_manager = None

        # Initialize toolsets (avoid global state)
        if toolsets is None:
            toolsets = [HelloTools(self.settings), FileSystemTools(self.settings)]

            # Load skills from settings
            try:
                # Auto-detect bundled_dir if not set
                if self.settings.skills.bundled_dir is None:
                    # Use importlib.resources to find bundled skills in package
                    try:
                        bundled_skills_path = resources.files("agent").joinpath("_bundled_skills")
                        self.settings.skills.bundled_dir = str(bundled_skills_path)
                        logger.debug(
                            f"Auto-detected bundled_dir: {self.settings.skills.bundled_dir}"
                        )
                    except (ModuleNotFoundError, AttributeError, TypeError) as e:
                        logger.warning(f"Could not auto-detect bundled_dir: {e}")

                from agent.skills.loader import SkillLoader

                skill_loader = SkillLoader(self.settings)
                skill_toolsets, script_tools, skill_docs = skill_loader.load_enabled_skills()

                # Store skill documentation index for context provider
                self.skill_docs = skill_docs

                if skill_toolsets:
                    toolsets.extend(skill_toolsets)
                    logger.info(f"Loaded {len(skill_toolsets)} skill toolsets")

                if script_tools:
                    toolsets.append(script_tools)
                    logger.info(f"Loaded script wrapper with {script_tools.script_count} scripts")

                if skill_docs.has_skills():
                    logger.info(f"Loaded {skill_docs.count()} skill(s) for progressive disclosure")

            except Exception as e:
                logger.error(f"Failed to load skills: {e}", exc_info=True)
                # Continue without skills - graceful degradation

        self.toolsets = toolsets

        # Collect all tools from toolsets
        self.tools = []
        for toolset in self.toolsets:
            self.tools.extend(toolset.get_tools())

        # Initialize middleware (create default if not provided)
        if middleware is None:
            from agent.middleware import create_middleware

            middleware = create_middleware()
        self.middleware = middleware

        # Create agent
        self.agent = self._create_agent()

    def _create_chat_client(self) -> Any:
        """Create chat client based on configuration.

        Supports:
        - openai: OpenAI API (gpt-5-mini, gpt-4o, etc.)
        - anthropic: Anthropic API (claude-sonnet-4-5, claude-opus-4, etc.)
        - azure: Azure OpenAI (gpt-5-codex, gpt-4o, etc.)
        - foundry: Azure AI Foundry with managed models
        - gemini: Google Gemini (gemini-2.0-flash-exp, gemini-2.5-pro, etc.)
        - github: GitHub Models (phi-4, llama-3.3-70b-instruct, etc.)
        - local: Local models via Docker Desktop (phi4, etc.)

        Returns:
            Configured chat client for the selected provider

        Raises:
            ValueError: If provider is unknown or not supported
        """
        if self.settings.llm_provider == "openai":
            from agent_framework.openai import OpenAIChatClient

            return OpenAIChatClient(
                model_id=self.settings.openai_model,
                api_key=self.settings.openai_api_key,
            )
        elif self.settings.llm_provider == "anthropic":
            from agent_framework.anthropic import AnthropicClient

            return AnthropicClient(
                model_id=self.settings.anthropic_model,
                api_key=self.settings.anthropic_api_key,
            )
        elif self.settings.llm_provider == "azure":
            from agent_framework.azure import AzureOpenAIChatClient, AzureOpenAIResponsesClient
            from azure.identity import AzureCliCredential, DefaultAzureCredential

            # gpt-5-codex requires the responses endpoint, use AzureOpenAIResponsesClient
            # gpt-5-mini and others use chat completions endpoint, use AzureOpenAIChatClient
            deployment_name = self.settings.azure_openai_deployment or ""
            use_responses_client = "codex" in deployment_name.lower()
            client_class = (
                AzureOpenAIResponsesClient if use_responses_client else AzureOpenAIChatClient
            )

            # Use API key if provided, otherwise use Azure CLI credential
            if self.settings.azure_openai_api_key:
                return client_class(
                    endpoint=self.settings.azure_openai_endpoint,
                    deployment_name=self.settings.azure_openai_deployment,
                    api_version=self.settings.azure_openai_api_version,
                    api_key=self.settings.azure_openai_api_key,
                )
            else:
                # Try AzureCliCredential first, fall back to DefaultAzureCredential
                credential: AzureCliCredential | DefaultAzureCredential
                try:
                    credential = AzureCliCredential()
                    return client_class(
                        endpoint=self.settings.azure_openai_endpoint,
                        deployment_name=self.settings.azure_openai_deployment,
                        api_version=self.settings.azure_openai_api_version,
                        credential=credential,
                    )
                except Exception:
                    credential = DefaultAzureCredential()
                    return client_class(
                        endpoint=self.settings.azure_openai_endpoint,
                        deployment_name=self.settings.azure_openai_deployment,
                        api_version=self.settings.azure_openai_api_version,
                        credential=credential,
                    )
        elif self.settings.llm_provider == "foundry":
            from agent_framework.azure import AzureAIAgentClient
            from azure.identity.aio import AzureCliCredential as AsyncAzureCliCredential

            return AzureAIAgentClient(
                project_endpoint=self.settings.azure_project_endpoint,
                model_deployment_name=self.settings.azure_model_deployment,
                async_credential=AsyncAzureCliCredential(),
            )
        elif self.settings.llm_provider == "gemini":
            from agent.providers.gemini import GeminiChatClient

            return GeminiChatClient(
                model_id=self.settings.gemini_model,
                api_key=self.settings.gemini_api_key,
                project_id=self.settings.gemini_project_id,
                location=self.settings.gemini_location,
                use_vertexai=self.settings.gemini_use_vertexai,
            )
        elif self.settings.llm_provider == "github":
            from agent.providers.github import GitHubChatClient

            return GitHubChatClient(
                model_id=self.settings.github_model,
                token=self.settings.github_token,
                endpoint=self.settings.github_endpoint,
                org=self.settings.github_org,
            )
        elif self.settings.llm_provider == "local":
            from agent_framework.openai import OpenAIChatClient

            return OpenAIChatClient(
                model_id=self.settings.local_model,
                base_url=self.settings.local_base_url,
                api_key="not-needed",  # Docker doesn't require authentication
            )
        else:
            raise ValueError(
                f"Unknown provider: {self.settings.llm_provider}. "
                f"Supported: openai, anthropic, azure, foundry, gemini, github, local"
            )

    def _load_system_prompt(self) -> str:
        """Load system prompt with three-tier fallback and placeholder replacement.

        Loading priority:
        1. AGENT_SYSTEM_PROMPT env variable (explicit override)
        2. ~/.agent/system.md (user's default custom prompt)
        3. Package default from prompts/system.md
        4. Hardcoded fallback (if all file loading fails)

        Returns:
            System prompt string with placeholders replaced and YAML front matter stripped
        """
        prompt_content = ""

        # Tier 1: Try explicit env variable override (AGENT_SYSTEM_PROMPT)
        if self.settings.system_prompt_file:
            try:
                # Expand environment variables and user home directory
                expanded_path = os.path.expandvars(self.settings.system_prompt_file)
                custom_path = Path(expanded_path).expanduser()
                prompt_content = custom_path.read_text(encoding="utf-8")
                logger.info(
                    f"Loaded system prompt from AGENT_SYSTEM_PROMPT: {self.settings.system_prompt_file}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to load system prompt from AGENT_SYSTEM_PROMPT={self.settings.system_prompt_file}: {e}. "
                    "Trying next fallback."
                )

        # Tier 2: Try user's default custom prompt (~/.agent/system.md)
        if not prompt_content and self.settings.agent_data_dir:
            try:
                user_default_path = self.settings.agent_data_dir / "system.md"
                if user_default_path.exists():
                    prompt_content = user_default_path.read_text(encoding="utf-8")
                    logger.info(f"Loaded system prompt from user default: {user_default_path}")
            except Exception as e:
                logger.warning(
                    f"Failed to load user default system prompt: {e}. Trying next fallback."
                )

        # Tier 3: Try package default
        if not prompt_content:
            try:
                # Use importlib.resources for package resource loading
                prompt_files = resources.files("agent.prompts")
                prompt_file = prompt_files.joinpath("system.md")
                prompt_content = prompt_file.read_text(encoding="utf-8")
                logger.info("Loaded system prompt from package default: prompts/system.md")
            except Exception as e:
                logger.warning(
                    f"Failed to load package default system prompt: {e}. Using hardcoded fallback."
                )

        # Tier 4: Hardcoded fallback
        if not prompt_content:
            prompt_content = """You are a helpful AI assistant that can use tools to assist with various tasks.

You help users with:
- Natural language interactions
- Information synthesis and summarization
- Tool-based task execution
- Context-aware conversations

Be helpful, concise, and clear in your responses."""
            logger.warning("Using hardcoded fallback system prompt")

        # Strip YAML front matter if present (more robust regex-based approach)
        yaml_pattern = r"^---\s*\n.*?\n---\s*\n"
        if re.match(yaml_pattern, prompt_content, re.DOTALL):
            prompt_content = re.sub(yaml_pattern, "", prompt_content, flags=re.DOTALL)
            logger.info("Stripped YAML front matter from system prompt")

        # Replace placeholders with settings values
        replacements = {
            "{{DATA_DIR}}": str(self.settings.agent_data_dir),
            "{{SESSION_DIR}}": str(self.settings.agent_session_dir),
            "{{MODEL}}": self.settings.get_model_display_name(),
            "{{PROVIDER}}": self.settings.llm_provider,
            "{{MEMORY_ENABLED}}": str(self.settings.memory_enabled),
        }

        for placeholder, value in replacements.items():
            prompt_content = prompt_content.replace(placeholder, value)

        # Warn if any unresolved placeholders remain
        unresolved = re.findall(r"\{\{[^}]+\}\}", prompt_content)
        if unresolved:
            logger.warning(
                f"Unresolved placeholders in system prompt: {', '.join(set(unresolved))}"
            )

        return prompt_content

    def _create_agent(self) -> Any:
        """Create agent with tools, instructions, and middleware.

        Returns:
            Configured agent instance ready to handle requests
        """
        instructions = self._load_system_prompt()

        # Create context providers for dynamic injection
        context_providers: list[Any] = []

        # Add memory context provider if enabled
        if self.memory_manager:
            from agent.memory import MemoryContextProvider

            memory_provider = MemoryContextProvider(
                self.memory_manager, history_limit=self.settings.memory_history_limit
            )
            context_providers.append(memory_provider)
            logger.info("Memory context provider enabled")

        # Add skill context provider if skills are loaded
        if hasattr(self, "skill_docs") and self.skill_docs.has_skills():
            from agent.skills.context_provider import SkillContextProvider

            skill_provider = SkillContextProvider(
                skill_docs=self.skill_docs,
                memory_manager=None,  # Not used in current implementation
                max_skills=3,
            )
            context_providers.append(skill_provider)
            logger.info(f"Skill context provider enabled with {self.skill_docs.count()} skills")

        # IMPORTANT: Pass middleware as a list, not dict
        # Agent Framework automatically categorizes middleware by signature
        # Converting to dict breaks middleware invocation
        logger.info(
            f"Creating agent with {len(context_providers)} context providers: {[type(p).__name__ for p in context_providers]}"
        )
        return self.chat_client.create_agent(
            name="Agent",
            instructions=instructions,
            tools=self.tools,
            middleware=self.middleware,  # Must be list, not dict
            context_providers=context_providers if context_providers else None,
        )

    def get_new_thread(self) -> Any:
        """Create a new conversation thread.

        Returns:
            New thread instance for maintaining conversation context

        Example:
            >>> agent = Agent(config)
            >>> thread = agent.get_new_thread()
            >>> response = await agent.run("Hello", thread=thread)
        """
        if hasattr(self.chat_client, "create_thread"):
            return self.chat_client.create_thread()
        # Fallback: some providers may not support explicit threads (e.g., OpenAI)
        # They manage conversation context automatically through message history
        return None

    async def run(self, prompt: str, thread: Any | None = None) -> str:
        """Run agent with prompt.

        Args:
            prompt: User prompt
            thread: Optional thread for conversation context

        Returns:
            Agent response as a string

        Example:
            >>> agent = Agent(config)
            >>> response = await agent.run("Say hello to Alice")
            >>> print(response)
            Hello, Alice!

            >>> # With thread for context
            >>> thread = agent.get_new_thread()
            >>> response = await agent.run("Hello", thread=thread)
        """
        if thread:
            result = await self.agent.run(prompt, thread=thread)
        else:
            result = await self.agent.run(prompt)

        # Handle different provider return types
        # OpenAI returns str, Anthropic returns AgentRunResponse with .text
        if isinstance(result, str):
            return result
        elif hasattr(result, "text"):
            return str(result.text)
        else:
            return cast(str, result)

    async def run_stream(self, prompt: str, thread: Any | None = None) -> AsyncIterator[str]:
        """Run agent with streaming response.

        Args:
            prompt: User prompt
            thread: Optional thread for conversation context

        Yields:
            Response chunks as they become available

        Example:
            >>> agent = Agent(config)
            >>> async for chunk in agent.run_stream("Say hello"):
            ...     print(chunk, end="")
            Hello! How can I help you?

            >>> # With thread for context
            >>> thread = agent.get_new_thread()
            >>> async for chunk in agent.run_stream("Hello", thread=thread):
            ...     print(chunk, end="")
        """
        if thread:
            stream = self.agent.run_stream(prompt, thread=thread)
        else:
            stream = self.agent.run_stream(prompt)

        async for chunk in stream:
            # Handle different provider chunk types
            # OpenAI returns str, Anthropic returns AgentRunResponseUpdate with .text
            if isinstance(chunk, str):
                yield chunk
            elif hasattr(chunk, "text"):
                yield chunk.text
            else:
                yield str(chunk)
