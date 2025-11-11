---
status: accepted
contact: danielscholl
date: 2025-11-07
deciders: danielscholl
---

# Title: CLI Framework Selection - Typer vs Argparse

## Context and Problem Statement

Agent applications need consistent, user-friendly command-line interfaces. The agent-template uses Typer (with Rich formatting) while some examples use argparse (plain text). This inconsistency creates confusion about which pattern to follow for new agents and whether the formatting differences are intentional or accidental.

How should we standardize CLI framework selection across the project to provide consistent user experience while allowing flexibility where appropriate?

## Decision Drivers

- **User Experience**: Modern, readable help output improves usability
- **Developer Experience**: Easy to define and maintain CLI interfaces
- **Consistency**: Agents in the same ecosystem should feel cohesive
- **Flexibility**: Different tools may have different requirements
- **Dependencies**: Balance between features and minimal dependencies
- **Maintainability**: Framework should be well-supported and stable

## Considered Options

1. **Typer as standard with Rich formatting** (agent-template pattern)
2. **Argparse only for all CLIs** (butler-agent pattern)
3. **Click framework** (middle ground alternative)

## Decision Outcome

Chosen option: **"Typer as standard with Rich formatting"**

Typer provides the best developer and user experience for agent CLIs. It automatically enables Rich formatting when available, extracts examples from docstrings, and provides type-safe argument parsing. This becomes the default pattern for all new agent CLIs.

### Decision Details

**Primary Pattern (Agent CLIs):**
- Framework: Typer (`typer>=0.12.0`)
- Formatting: Rich auto-enabled (`rich>=14.1.0`)
- Entry point: Typer app object
- Help style: Boxed, colored, with extracted examples
- Use case: Interactive agents, user-facing tools

**Alternative Pattern (Utility Scripts):**
- Framework: argparse (stdlib)
- Formatting: Plain text
- Entry point: Main function
- Help style: Traditional Unix format
- Use case: Minimal scripts, CI tools, stdlib-only requirements

### Consequences

**Good:**
- Consistent, modern UX across agent CLIs
- Examples automatically extracted from docstrings
- Type-safe argument parsing with Python type hints
- Rich formatting improves readability and accessibility
- Typer handles edge cases (help, errors) elegantly
- Developer-friendly API reduces boilerplate

**Neutral:**
- Requires `typer` and `rich` dependencies
- Different from traditional Unix tool aesthetic
- New contributors must learn Typer (but it's intuitive)

**Bad:**
- Not suitable for stdlib-only requirements
- Slightly more opinionated than argparse
- Rich formatting may not render well on all terminals (rare)

## Pros and Cons of the Options

### Typer with Rich Formatting

**Example implementation:**
```python
import typer
from rich.console import Console

app = typer.Typer(help="Agent - AI-powered assistant")
console = Console()

@app.command()
def main(
    prompt: str = typer.Option(None, "-p", "--prompt", help="Execute a prompt"),
    check: bool = typer.Option(False, "--check", help="Run health check"),
):
    """Agent - Generic chatbot agent with extensible tools.

    Examples:
        # Run health check
        agent --check

        # Execute prompt
        agent -p "Say hello"
    """
    if check:
        run_health_check()
    elif prompt:
        run_prompt(prompt)
```

- Good, because modern, readable help output improves UX
- Good, because examples extracted from docstrings automatically
- Good, because type hints provide validation and IDE support
- Good, because Rich formatting is automatic (no configuration)
- Good, because reduces boilerplate compared to argparse
- Neutral, because adds dependencies (but already in project)
- Bad, because not suitable for stdlib-only requirements

### Argparse Only

**Example implementation:**
```python
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="Agent - AI-powered assistant"
    )
    parser.add_argument("-p", "--prompt", help="Execute a prompt")
    parser.add_argument("--check", action="store_true", help="Run health check")

    args = parser.parse_args()

    if args.check:
        run_health_check()
    elif args.prompt:
        run_prompt(args.prompt)
```

- Good, because stdlib only (no dependencies)
- Good, because familiar to developers from Unix background
- Good, because very stable and well-documented
- Neutral, because traditional plain text format
- Bad, because more boilerplate code required
- Bad, because no automatic example extraction
- Bad, because inconsistent formatting with modern CLIs

### Click Framework

Click is a middle ground between Typer and argparse.

- Good, because popular and well-maintained
- Good, because more flexible than argparse
- Neutral, because requires dependency (like Typer)
- Bad, because doesn't auto-enable Rich formatting
- Bad, because more verbose than Typer
- Bad, because we already use Typer in agent-template

## Implementation Patterns

### Agent Template Pattern (src/agent/cli.py)

**Framework:** Typer + Rich
**Entry Point:** `agent = "agent.cli:app"` (Typer app object)
**Help Output:**
```
 Usage: agent [OPTIONS]

 Agent - Generic chatbot agent with extensible tools.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --prompt              -p      TEXT  Execute a single prompt and exit         │
│ --check                             Run health check for configuration       │
│ --config                            Show current configuration               │
│ --version                           Show version                             │
│ --help                              Show this message and exit.              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

**Key Features:**
- Boxed, colored output
- Examples extracted from docstring
- Type-safe arguments
- Automatic help generation

### Butler Agent Pattern (Example Only)

**Framework:** argparse
**Entry Point:** `butler = "agent.cli:main"` (main function)
**Help Output:**
```
usage: butler [-h] [-p PROMPT] [-q] [-v] [--check] [--config]

Butler - AI-powered Kubernetes infrastructure management

options:
  -h, --help            show this help message and exit
  -p PROMPT, --prompt PROMPT
                        Execute a single prompt and exit
  -q, --quiet           Minimal output
```

**Key Features:**
- Plain text, traditional Unix style
- Stdlib only
- Familiar to traditional tooling

## Guidelines for New CLIs

### When to Use Typer (Default)

Use Typer for:
- New agent implementations
- User-facing interactive tools
- CLIs that benefit from modern UX
- Tools used by non-technical users
- Projects already using Rich for output

### When to Use Argparse (Exception)

Use argparse only when:
- Stdlib-only requirement is critical
- Building minimal utility scripts
- Integration with legacy systems requiring plain text
- CI/CD tools where dependencies must be minimal
- Traditional Unix tool aesthetic is explicitly required

### Docstring Format for Examples

Typer automatically extracts examples from docstrings:

```python
@app.command()
def main(
    option: str = typer.Option(None, "--opt", help="An option"),
):
    """Brief description.

    Examples:
        # Example 1 with comment
        command --opt value

        # Example 2 with comment
        command --other-flag
    """
    pass
```

The examples will appear in `--help` output under an "Examples:" section.

## Validation

**Implementation Check:**
```bash
# Verify agent uses Typer
grep "import typer" src/agent/cli.py

# Verify help output has Rich formatting
uv run agent --help | grep "╭─ Options"
```

**Dependency Check:**
```bash
# Verify pyproject.toml includes Typer and Rich
grep "typer>=" pyproject.toml
grep "rich>=" pyproject.toml
```

**Entry Point Check:**
```bash
# Verify entry point is Typer app object
grep 'agent = "agent.cli:app"' pyproject.toml
```

## Related Decisions

- ADR-0002: Repository Infrastructure (dependency management)
- ADR-0008: Testing Strategy (CLI testing approach)

## References

- [Typer Documentation](https://typer.tiangolo.com/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [Python argparse Documentation](https://docs.python.org/3/library/argparse.html)
- Agent Template: `src/agent/cli.py:1-152`
- Analysis: `docs/analysis/cli-help-formatting-comparison.md`
- Spec: `docs/specs/bug-cli-help-formatting-inconsistency.md`

## More Information

This decision resolves the formatting inconsistency identified in the agent-template vs butler-agent CLI help output. The butler-agent's argparse usage is acknowledged as a valid alternative pattern but not the recommended default for new agents.

**Future Considerations:**
- Monitor Typer adoption and maintenance
- Re-evaluate if Rich formatting causes issues on certain terminals
- Consider Click if Typer development stalls
- Document how to disable Rich formatting if needed (set `FORCE_COLOR=0`)
