"""Keybinding manager for registering and creating keybindings.

Provides centralized registry for keybinding handlers.
Adapted from butler-agent for agent-template.
"""

from collections.abc import Callable
from typing import Any

from prompt_toolkit.key_binding import KeyBindings

from agent.utils.keybindings.handler import KeybindingHandler


class KeybindingManager:
    """Manages keybinding handlers and creates prompt_toolkit KeyBindings.

    Example:
        >>> manager = KeybindingManager()
        >>> manager.register_handler(ClearPromptHandler())
        >>> key_bindings = manager.create_keybindings()
        >>> session = PromptSession(key_bindings=key_bindings)
    """

    def __init__(self) -> None:
        """Initialize keybinding manager."""
        self._handlers: list[KeybindingHandler] = []

    def register_handler(self, handler: KeybindingHandler) -> None:
        """Register a keybinding handler.

        Args:
            handler: KeybindingHandler instance to register

        Example:
            >>> manager.register_handler(ClearPromptHandler())
        """
        self._handlers.append(handler)

    def create_keybindings(self) -> KeyBindings:
        """Create prompt_toolkit KeyBindings from registered handlers.

        Returns:
            KeyBindings instance with all registered handlers

        Example:
            >>> kb = manager.create_keybindings()
            >>> session = PromptSession(key_bindings=kb)
        """
        kb = KeyBindings()

        for handler in self._handlers:
            # Create closure to capture handler (prevents late-binding issues)
            def make_handler(h: KeybindingHandler) -> Callable[[Any], None]:
                # Use eager=True for escape key to trigger immediately
                # without waiting for potential escape sequences
                is_escape = h.trigger_key == "escape"

                @kb.add(h.trigger_key, eager=is_escape)
                def _(event: Any) -> None:
                    h.handle(event)

                return _

            make_handler(handler)

        return kb
