"""Mock chat client for testing without LLM calls."""

from collections.abc import AsyncIterator
from typing import Any


class MockAgent:
    """Mock agent for testing.

    Simulates an agent created by the chat client. Returns configurable
    responses without making actual LLM calls.
    """

    def __init__(self, response: str = "Mock response"):
        """Initialize mock agent.

        Args:
            response: The response to return from run/run_stream
        """
        self.response = response

    async def run_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Stream mock response word by word.

        Args:
            prompt: User prompt (ignored in mock)
            **kwargs: Additional arguments (ignored)

        Yields:
            Words from the mock response
        """
        for word in self.response.split():
            yield word + " "

    async def run(self, prompt: str, **kwargs) -> str:
        """Return full mock response.

        Args:
            prompt: User prompt (ignored in mock)
            **kwargs: Additional arguments (ignored)

        Returns:
            Complete mock response
        """
        return self.response


class MockChatClient:
    """Mock chat client for testing.

    Replaces real chat clients (OpenAI, Anthropic, etc.) in tests.
    Creates MockAgent instances instead of real agents.
    """

    def __init__(self, response: str = "Mock response"):
        """Initialize mock chat client.

        Args:
            response: Default response for created agents
        """
        self.response = response
        self.created_agents = []

    def create_agent(
        self,
        name: str,
        instructions: str,
        tools: list = None,
        middleware: dict = None,
        context_providers: list = None,
        **kwargs: Any,
    ) -> MockAgent:
        """Create a mock agent.

        Captures the agent creation parameters for inspection in tests
        and returns a MockAgent that will return the configured response.

        Args:
            name: Agent name
            instructions: System instructions
            tools: List of tools (captured but not used)
            middleware: Middleware configuration (captured but not used)
            context_providers: Context providers (captured but not used)
            **kwargs: Additional arguments (captured but not used)

        Returns:
            MockAgent instance
        """
        agent = MockAgent(self.response)

        # Capture creation parameters for test inspection
        self.created_agents.append(
            {
                "name": name,
                "instructions": instructions,
                "tools": tools or [],
                "middleware": middleware or {},
                "context_providers": context_providers or [],
                "kwargs": kwargs,
            }
        )

        return agent
