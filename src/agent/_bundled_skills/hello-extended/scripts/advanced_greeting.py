#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.1.0",
# ]
# ///
"""Advanced greeting script with complex formatting.

Demonstrates PEP 723 standalone script pattern for context-heavy operations.
This script is NOT loaded into agent context - only executed when needed.
"""

import json
from datetime import datetime

import click


@click.command()
@click.option("--name", required=True, help="Name to greet")
@click.option(
    "--style",
    type=click.Choice(["formal", "casual", "enthusiastic"]),
    default="casual",
    help="Greeting style",
)
@click.option("--time-aware", is_flag=True, help="Include time-based greeting")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def main(name: str, style: str, time_aware: bool, json_output: bool):
    """Generate advanced personalized greeting.

    Examples:
        $ advanced_greeting.py --name Alice --style formal
        $ advanced_greeting.py --name Bob --style enthusiastic --time-aware
        $ advanced_greeting.py --name Charlie --json
    """
    greeting = generate_greeting(name, style, time_aware)

    if json_output:
        output = {
            "greeting": greeting,
            "name": name,
            "style": style,
            "time_aware": time_aware,
            "timestamp": datetime.now().isoformat(),
        }
        click.echo(json.dumps(output, indent=2))
    else:
        click.echo(greeting)


def generate_greeting(name: str, style: str, time_aware: bool) -> str:
    """Generate greeting based on style and time awareness.

    Args:
        name: Name to greet
        style: Greeting style (formal, casual, enthusiastic)
        time_aware: Include time-based greeting

    Returns:
        Generated greeting text
    """
    # Time-based prefix if requested
    prefix = ""
    if time_aware:
        hour = datetime.now().hour
        if hour < 12:
            prefix = "Good morning, "
        elif hour < 18:
            prefix = "Good afternoon, "
        else:
            prefix = "Good evening, "

    # Style-based greeting
    if style == "formal":
        greeting = f"{prefix}Dear {name}, I hope this message finds you well."
    elif style == "casual":
        greeting = f"{prefix}Hey {name}! How's it going?"
    else:  # enthusiastic
        greeting = f"{prefix}Hello {name}! Great to see you! 🎉"

    return greeting


if __name__ == "__main__":
    main()
