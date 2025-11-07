"""Hello World tools for demonstrating tool architecture.

This module provides a simple HelloTools implementation that demonstrates
all the key patterns that future tools should follow:
- Dependency injection via constructor
- Structured response format
- Error handling with error codes
- Type hints for LLM consumption
- Comprehensive docstrings
"""

from typing import Annotated

from pydantic import Field

from agent.config import AgentConfig
from agent.tools.toolset import AgentToolset


class HelloTools(AgentToolset):
    """Hello World tools for demonstrating tool architecture.

    This toolset demonstrates the complete tool lifecycle including:
    - Tool registration via get_tools()
    - Structured success/error responses
    - Type hints and validation
    - Error handling patterns
    - Docstrings for LLM consumption

    Example:
        >>> config = AgentConfig.from_env()
        >>> tools = HelloTools(config)
        >>> result = await tools.hello_world("Alice")
        >>> print(result)
        {'success': True, 'result': 'Hello, Alice!', 'message': 'Greeted Alice'}
    """

    def __init__(self, config: AgentConfig):
        """Initialize HelloTools with configuration.

        Args:
            config: Agent configuration instance
        """
        super().__init__(config)

    def get_tools(self) -> list:
        """Get list of hello tools.

        Returns:
            List containing hello_world and greet_user functions
        """
        return [self.hello_world, self.greet_user]

    async def hello_world(
        self, name: Annotated[str, Field(description="Name to greet")] = "World"
    ) -> dict:
        """Say hello to someone.

        This is a simple demonstration tool that shows the basic patterns
        for tool implementation. It always succeeds and returns a greeting.

        Args:
            name: Name of person to greet (default: "World")

        Returns:
            Success response with greeting message in format:
            {
                "success": True,
                "result": "Hello, <name>!",
                "message": "Greeted <name>"
            }

        Example:
            >>> tools = HelloTools(config)
            >>> result = await tools.hello_world("Alice")
            >>> print(result["result"])
            Hello, Alice!
        """
        greeting = f"Hello, {name}!"
        return self._create_success_response(result=greeting, message=f"Greeted {name}")

    async def greet_user(
        self,
        name: Annotated[str, Field(description="User's name")],
        language: Annotated[str, Field(description="Language code (en, es, fr)")] = "en",
    ) -> dict:
        """Greet user in different languages.

        This tool demonstrates error handling by validating the language
        parameter and returning structured error responses when invalid.

        Supported languages:
        - en: English
        - es: Spanish
        - fr: French

        Args:
            name: User's name
            language: Language code (en, es, fr) - defaults to "en"

        Returns:
            Success response with localized greeting, or error response if
            language not supported.

            Success format:
            {
                "success": True,
                "result": "<greeting in requested language>",
                "message": "Greeted <name> in <language>"
            }

            Error format:
            {
                "success": False,
                "error": "unsupported_language",
                "message": "Language '<language>' not supported. Use: en, es, fr"
            }

        Example:
            >>> tools = HelloTools(config)
            >>> result = await tools.greet_user("Alice", "es")
            >>> print(result["result"])
            ¡Hola, Alice!

            >>> result = await tools.greet_user("Bob", "de")
            >>> print(result["error"])
            unsupported_language
        """
        greetings = {
            "en": f"Hello, {name}!",
            "es": f"¡Hola, {name}!",
            "fr": f"Bonjour, {name}!",
        }

        if language not in greetings:
            return self._create_error_response(
                error="unsupported_language",
                message=f"Language '{language}' not supported. Use: en, es, fr",
            )

        return self._create_success_response(
            result=greetings[language], message=f"Greeted {name} in {language}"
        )
