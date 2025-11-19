# Skills Architecture

This guide explains how to design, structure, and implement skills for Agent Base. A skill provides domain-specific capabilities without increasing the size of the core runtime, giving you a clean way to deliver optional functionality as a standalone module. Skills are isolated, versioned independently, and discovered automatically at runtime.

## Overview

A skill is a small, self-contained package containing two parts: a manifest (SKILL.md) and one or more scripts implemented as standalone PEP 723 modules. The manifest supplies the metadata needed for discovery and routing. Scripts provide the executable behavior and are loaded only when invoked. This separation keeps context usage low while enabling rich extensibility.

Skill packages can live inside the main repository (bundled skills) or be installed from any Git source (plugin skills). Installation simply places the skill in the correct directory—no changes to the core codebase or global dependency files are required.

### Design Considerations

Skills follow several principles to remain lightweight and maintainable:

**Progressive disclosure**: Only the manifest is loaded into the agent's context at startup. Scripts and dependencies stay dormant until execution, keeping overhead predictable even when many skills are installed.

**Dependency isolation**: Scripts declare dependencies through PEP 723 metadata, preventing environment pollution and avoiding version conflicts across skills.

**Simple distribution model**: Because a skill is just a directory containing a manifest and scripts, it can be versioned, shared, and installed from any Git-compatible source.

### When to Use Skills

Skills are most appropriate for capabilities that are optional, domain-specific, or require external packages. Common uses include API integrations, specialized computations, or tools relevant to particular workflows. Capabilities required by all users or features foundational to the agent should be implemented in the core toolset instead.

## Skill Structure

A skill consists of a manifest and a scripts subdirectory located at the repository root. The manifest defines metadata and documentation, while scripts implement functionality and declare dependencies inline.

```
SKILL.md
scripts/
    ├── action1.py
    └── action2.py
```

## Loading Model

Skill loading happens in two stages. During discovery, the system identifies skills by locating directories containing SKILL.md, parses the frontmatter, verifies the scripts directory, and injects the manifest content into the system prompt. This gives the agent the information it needs to understand when and how a skill should be used.

During execution, if a user request triggers a skill, the agent runs the selected script via `uv run`, which installs dependencies as needed and executes the script in an isolated environment. This model keeps startup cost low and ensures consistent behavior across environments. The manifest typically consumes under 5K tokens, and script code never enters the LLM context.

## Building a Skill

The following example illustrates the minimum elements required for a functional skill that fetches content from URLs. It assumes you are creating a new skill repository from scratch.

### Write the Manifest

The manifest uses YAML frontmatter followed by markdown documentation. Required fields are `name` and `description`. The description should include natural-language trigger cues that help the agent understand when the skill applies.

Create `SKILL.md` at the repository root:

```markdown
---
name: web-fetch
description: Retrieve content from HTTP/HTTPS URLs
---

# web-fetch

This skill provides a simple mechanism for fetching URL content.

## Triggers

Use when a user asks to retrieve a web page or download information
from an HTTP/HTTPS source.

## Scripts

### fetch.py

Fetch content from a URL.

**Usage**: `script_run web-fetch fetch --url "https://example.com" --json`

**Parameters**:
- `--url`: HTTP/HTTPS URL to fetch
- `--timeout`: Request timeout in seconds (default: 30)
- `--json`: Return structured JSON response
```

The triggers section provides natural language cues for routing. The scripts section documents entry points and usage patterns. This documentation is loaded at startup and is what the agent reads during request interpretation.

### Implement the Script

Scripts must include PEP 723 metadata and expose a small CLI using Click. They should return structured JSON when invoked with the `--json` flag.

Create `scripts/fetch.py`:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27.0", "click>=8.1.0"]
# ///
"""Fetch content from URLs."""

import json
import sys
import click
import httpx

@click.command()
@click.option("--url", required=True, help="URL to fetch")
@click.option("--timeout", default=30, type=int, help="Timeout in seconds")
@click.option("--json", "output_json", is_flag=True, help="JSON output")
def main(url, timeout, output_json):
    """Fetch content from a URL."""
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            result = {
                "success": True,
                "result": response.text,
                "message": f"Fetched {len(response.text)} characters"
            }
    except httpx.HTTPStatusError as e:
        result = {
            "success": False,
            "error": "http_error",
            "message": f"HTTP {e.response.status_code}"
        }
    except httpx.RequestError as e:
        result = {
            "success": False,
            "error": "request_error",
            "message": str(e)
        }

    if output_json:
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(result.get("result", result.get("message")))

    sys.exit(0 if result["success"] else 1)

if __name__ == "__main__":
    main()
```

The PEP 723 block declares dependencies the script needs. `uv run` installs them in an isolated environment on first execution and reuses the environment in subsequent runs.

### Test the Script

Test scripts directly with `uv run`:

```bash
uv run scripts/fetch.py --help
uv run scripts/fetch.py --url "https://example.com" --json
uv run scripts/fetch.py --url "https://api.example.com/data" --timeout 60 --json
```

Direct testing makes it easy to validate behavior before integrating with the agent. The first run installs dependencies; subsequent runs are cached and fast.

## Manifest Format

SKILL.md contains YAML frontmatter followed by markdown content. The `name` (lowercase with hyphens, 1–64 characters) and `description` are required. Optional fields such as `version`, `author`, or `repository` may be included.

Names are normalized automatically—e.g., `My-Skill`, `my_skill`, and `MY-SKILL` all become `my-skill`.

The documentation following the frontmatter should describe the purpose of the skill, when it applies, and usage patterns for each script. Aim to keep SKILL.md concise (generally under 250 tokens). Detailed parameter documentation belongs in the script's `--help` output.

A typical manifest includes a purpose statement, a triggers section in natural language, and a scripts section with usage examples. If the skill requires environment variables or external services, document them clearly.

## Script Implementation

Scripts are standalone Python modules that use PEP 723 inline metadata to declare dependencies. `uv run` reads this metadata and creates an isolated environment for execution.

### PEP 723 Metadata

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.0",
# ]
# ///
```

Dependencies should specify minimum versions. Prefer lightweight libraries unless heavier ones are necessary.

### CLI Interface

Scripts should use Click for option parsing and support both human-readable and JSON output. When `--json` is specified, produce only JSON—no additional text.

```python
@click.command()
@click.option("--arg", required=True)
@click.option("--json", "output_json", is_flag=True)
def main(arg, output_json):
    result = perform_operation(arg)
    click.echo(json.dumps(result, indent=2) if output_json else result["result"])
    sys.exit(0 if result["success"] else 1)
```

Exit codes must follow the convention: 0 for success, non-zero for errors.

## Response Format

All skills must return responses in the agent-base structured format. Success responses include `success: true`, a `result`, and an optional `message`. Error responses contain `success: false`, an `error` code, and a human-readable `message`.

Example success response:

```json
{
  "success": true,
  "result": "content here",
  "message": "Fetched successfully"
}
```

Example error response:

```json
{
  "success": false,
  "error": "timeout",
  "message": "Request timed out after 30 seconds"
}
```

Use descriptive error codes such as `invalid_url`, `timeout`, `http_error`, or `request_error`.

## Discovery and Management

Skills are installed via:

```bash
agent skill install <git-url>
```

The agent discovers installed skills at startup by parsing each manifest and registering the skill in the runtime registry. Only the manifest is loaded into the LLM context; script code remains on disk until execution.

Skills can be inspected and controlled via:

```bash
agent skill show
agent skill enable <name>
agent skill disable <name>
```

## Best Practices

### Keep Skills Focused

Each skill should address a single domain or capability. Avoid mixing unrelated functions in a single skill.

### Minimize Context Overhead

Since manifest content is loaded into the context, keep it short and written in clear natural language.

### Handle Errors Gracefully

Validate inputs early, return structured error responses, and let unexpected exceptions propagate so they can be fixed.

### Security Considerations

Validate URLs, avoid shell execution, sanitize paths, and document environment variables without embedding credentials.

### Test Incrementally

Use `uv run` during development for fast feedback, then test through the agent once the script behaves correctly.

### Document Clearly

Provide realistic usage examples and document required environment variables. Keep detailed parameter documentation in script help.

## See Also

See [Architecture](architecture.md) and [Requirements](requirements.md) for broader design context, and [CONTRIBUTING.md](../../CONTRIBUTING.md) for development workflow. The [PEP 723](https://peps.python.org/pep-0723/) specification covers the inline metadata format in detail.
