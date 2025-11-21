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
    - Concise docstrings for LLM (comprehensive docs here)

    ## Detailed Implementation Guide

    ### hello_world(name: str = "World") -> dict
    Simple demonstration tool showing basic patterns. Always succeeds.

    **Response format:**
    ```python
    {
        "success": True,
        "result": "Hello, <name>! ◉‿◉",
        "message": "Greeted <name>"
    }
    ```

    **Usage:**
    ```python
    >>> config = AgentConfig.from_env()
    >>> tools = HelloTools(config)
    >>> result = await tools.hello_world("Alice")
    >>> print(result["result"])
    Hello, Alice! ◉‿◉
    ```

    **Tests:** `tests/unit/tools/test_hello_tools.py`

    ### greet_user(name: str, language: str = "en") -> dict
    Demonstrates error handling with language validation.

    **Supported languages:**
    - en: English
    - es: Spanish
    - fr: French

    **Success response format:**
    ```python
    {
        "success": True,
        "result": "<localized greeting>",
        "message": "Greeted <name> in <language>"
    }
    ```

    **Error response format:**
    ```python
    {
        "success": False,
        "error": "unsupported_language",
        "message": "Language '<language>' not supported. Use: en, es, fr"
    }
    ```

    **Usage:**
    ```python
    >>> tools = HelloTools(config)
    >>> result = await tools.greet_user("Alice", "es")
    >>> print(result["result"])
    ¡Hola, Alice! ◉‿◉

    >>> result = await tools.greet_user("Bob", "de")
    >>> print(result["error"])
    unsupported_language
    ```

    **Tests:** `tests/unit/tools/test_hello_tools.py`
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

    """
    {
      "name": "hello_world",
      "description": "Say hello to someone. Returns greeting message.",
      "parameters": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "description": "Name to greet",
            "default": "World"
          }
        },
        "required": []
      }
    }
    """

    async def hello_world(
        self, name: Annotated[str, Field(description="Name to greet")] = "World"
    ) -> dict:
        """Say hello to someone. Returns greeting message."""
        greeting = f"Hello, {name}! ◉‿◉"
        return self._create_success_response(result=greeting, message=f"Greeted {name}")

    """
    {
      "name": "greet_user",
      "description": "Greet user in different languages (en, es, fr). Returns localized greeting or error if language unsupported.",
      "parameters": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "description": "User's name"
          },
          "language": {
            "type": "string",
            "description": "Language code (en, es, fr)",
            "default": "en"
          }
        },
        "required": ["name"]
      }
    }
    """

    async def greet_user(
        self,
        name: Annotated[str, Field(description="User's name")],
        language: Annotated[str, Field(description="Language code (en, es, fr)")] = "en",
    ) -> dict:
        """Greet user in different languages (en, es, fr). Returns localized greeting or error if language unsupported."""
        greetings = {
            "en": f"Hello, {name}! ◉‿◉",
            "es": f"¡Hola, {name}! ◉‿◉",
            "fr": f"Bonjour, {name}! ◉‿◉",
        }

        if language not in greetings:
            return self._create_error_response(
                error="unsupported_language",
                message=f"Language '{language}' not supported. Use: en, es, fr",
            )

        return self._create_success_response(
            result=greetings[language], message=f"Greeted {name} in {language}"
        )
