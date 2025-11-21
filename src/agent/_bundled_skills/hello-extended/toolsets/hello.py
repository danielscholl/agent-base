"""Extended hello toolset demonstrating Python toolset pattern.

This toolset provides structured, testable greeting methods for frequently-used operations.
"""

from typing import Annotated

from pydantic import Field

from agent.tools.toolset import AgentToolset


class HelloExtended(AgentToolset):
    """Extended hello toolset with multi-language support.

    Demonstrates the Python toolset pattern for skills:
    - Type-safe with Pydantic Field annotations
    - Testable (inherits from AgentToolset)
    - IDE-friendly with autocomplete
    - Loaded into agent context (use for frequent operations)

    Example:
        >>> from agent.config import AgentConfig
        >>> config = AgentConfig.from_env()
        >>> toolset = HelloExtended(config)
        >>> tools = toolset.get_tools()
    """

    def get_tools(self) -> list:
        """Get list of greeting tools."""
        return [
            self.greet_in_language,
            self.greet_multiple,
        ]

    """
    {
      "name": "greet_in_language",
      "description": "Generate greeting in specified language (en, es, fr, de, ja, zh). Returns culturally appropriate greeting.",
      "parameters": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "description": "Name to greet"
          },
          "language": {
            "type": "string",
            "description": "Language code (en, es, fr, de, ja, zh)",
            "default": "en"
          }
        },
        "required": ["name"]
      }
    }
    """

    async def greet_in_language(
        self,
        name: Annotated[str, Field(description="Name to greet")],
        language: Annotated[
            str, Field(description="Language code (en, es, fr, de, ja, zh)")
        ] = "en",
    ) -> dict:
        """Generate greeting in specified language (en, es, fr, de, ja, zh). Returns culturally appropriate greeting."""
        greetings = {
            "en": f"Hello, {name}!",
            "es": f"¡Hola, {name}!",
            "fr": f"Bonjour, {name}!",
            "de": f"Guten Tag, {name}!",
            "ja": f"こんにちは, {name}さん!",
            "zh": f"你好, {name}!",
        }

        if language not in greetings:
            return self._create_error_response(
                error="unsupported_language",
                message=f"Language '{language}' not supported. Available: {', '.join(greetings.keys())}",
            )

        greeting = greetings[language]
        return self._create_success_response(
            result=greeting, message=f"Generated greeting in {language}"
        )

    """
    {
      "name": "greet_multiple",
      "description": "Generate greetings for multiple people in same language. Returns list of greeting messages.",
      "parameters": {
        "type": "object",
        "properties": {
          "names": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of names to greet"
          },
          "language": {
            "type": "string",
            "description": "Language code",
            "default": "en"
          }
        },
        "required": ["names"]
      }
    }
    """

    async def greet_multiple(
        self,
        names: Annotated[list[str], Field(description="List of names to greet")],
        language: Annotated[str, Field(description="Language code")] = "en",
    ) -> dict:
        """Generate greetings for multiple people in same language. Returns list of greeting messages."""
        greetings = []

        for name in names:
            result = await self.greet_in_language(name, language)
            if result["success"]:
                greetings.append(result["result"])
            else:
                return result  # Propagate error

        return self._create_success_response(
            result=greetings, message=f"Generated {len(greetings)} greetings"
        )
