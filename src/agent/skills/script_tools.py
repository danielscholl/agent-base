"""Script wrapper tools for executing PEP 723 scripts.

Provides generic tools for progressive disclosure: script_list, script_help, script_run.
These tools enable LLMs to discover and execute standalone scripts without loading
their code into context.
"""

import asyncio
import json as json_module
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field

from agent.skills.security import normalize_script_name, normalize_skill_name
from agent.tools.toolset import AgentToolset


class ScriptToolset(AgentToolset):
    """Generic wrapper tools for executing skill scripts.

    Provides progressive disclosure: LLM can list scripts, get help, then execute.
    Scripts are NOT loaded into context - only metadata is registered.

    Example:
        >>> scripts = {"hello-extended": [{"name": "advanced_greeting", "path": Path("...")}]}
        >>> toolset = ScriptToolset(config, scripts)
        >>> tools = toolset.get_tools()
    """

    def __init__(self, config: Any, scripts: dict[str, list[dict[str, Any]]]):
        """Initialize script toolset.

        Args:
            config: AgentConfig with script execution settings
            scripts: Dict mapping skill names to script metadata lists
                     Format: {skill_name: [{"name": str, "path": Path}, ...]}
        """
        super().__init__(config)
        self.scripts = scripts

        # Execution safety limits (use config values with safe defaults)
        self.timeout = getattr(config, "script_timeout", 60)
        self.max_output = getattr(config, "max_script_output", 1048576)
        self.max_args = 100  # Not configurable - hard security limit
        self.max_args_length = 4096  # Not configurable - hard security limit

    def get_tools(self) -> list:
        """Get list of script wrapper tools."""
        return [
            self.script_list,
            self.script_help,
            self.script_run,
        ]

    @property
    def script_count(self) -> int:
        """Get total number of scripts across all skills."""
        return sum(len(scripts) for scripts in self.scripts.values())

    """
    {
      "name": "script_list",
      "description": "List available scripts for skill or all skills. Returns script metadata with names and paths.",
      "parameters": {
        "type": "object",
        "properties": {
          "skill_name": {
            "type": ["string", "null"],
            "description": "Skill name, or None for all skills",
            "default": null
          }
        },
        "required": []
      }
    }
    """

    async def script_list(
        self,
        skill_name: Annotated[
            str | None, Field(description="Skill name, or None for all skills")
        ] = None,
    ) -> dict:
        """List available scripts for skill or all skills. Returns script metadata with names and paths."""
        try:
            if skill_name is not None:
                # Normalize skill name
                canonical = normalize_skill_name(skill_name)

                if canonical not in self.scripts:
                    return self._create_error_response(
                        error="not_found", message=f"Skill '{skill_name}' not found"
                    )

                # Return scripts for this skill only
                scripts_list = [
                    {"name": s["name"], "path": str(s["path"])} for s in self.scripts[canonical]
                ]

                return self._create_success_response(
                    result={canonical: scripts_list},
                    message=f"Found {len(scripts_list)} scripts in '{skill_name}'",
                )
            else:
                # Return all scripts
                all_scripts = {}
                total_count = 0

                for skill, scripts in self.scripts.items():
                    scripts_list = [{"name": s["name"], "path": str(s["path"])} for s in scripts]
                    all_scripts[skill] = scripts_list
                    total_count += len(scripts_list)

                return self._create_success_response(
                    result=all_scripts,
                    message=f"Found {total_count} scripts across {len(self.scripts)} skills",
                )

        except Exception as e:
            return self._create_error_response(
                error="execution_failed", message=f"Failed to list scripts: {e}"
            )

    """
    {
      "name": "script_help",
      "description": "Get help for skill script by running --help. Use to discover arguments and options before running. Returns help text.",
      "parameters": {
        "type": "object",
        "properties": {
          "skill_name": {
            "type": "string",
            "description": "Skill name (e.g., 'sample-skill')"
          },
          "script_name": {
            "type": "string",
            "description": "Script name (e.g., 'sample' or 'sample.py')"
          }
        },
        "required": ["skill_name", "script_name"]
      }
    }
    """

    async def script_help(
        self,
        skill_name: Annotated[str, Field(description="Skill name (e.g., 'sample-skill')")],
        script_name: Annotated[
            str, Field(description="Script name (e.g., 'sample' or 'sample.py')")
        ],
    ) -> dict:
        """Get help for skill script by running --help. Use to discover arguments and options before running. Returns help text."""
        try:
            # Normalize names
            canonical_skill = normalize_skill_name(skill_name)
            canonical_script = normalize_script_name(script_name)

            # Find script path
            script_path = self._find_script(canonical_skill, canonical_script)
            if script_path is None:
                return self._create_error_response(
                    error="not_found",
                    message=f"Script '{script_name}' not found in skill '{skill_name}'",
                )

            # Execute with --help
            cmd = [self._get_uv_executable(), "run", str(script_path), "--help"]

            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=script_path.parent,
            )

            try:
                stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=self.timeout)
            except TimeoutError:
                result.kill()
                return self._create_error_response(
                    error="timeout",
                    message=f"Script help timed out after {self.timeout}s",
                )

            stdout_text = stdout.decode("utf-8")
            stderr_text = stderr.decode("utf-8")

            if result.returncode != 0:
                return self._create_error_response(
                    error="execution_failed",
                    message=f"Script help failed with exit code {result.returncode}\nstderr: {stderr_text[-500:]}",
                )

            return self._create_success_response(
                result={"help_text": stdout_text, "usage": stdout_text},
                message=f"Retrieved help for {script_name}",
            )

        except Exception as e:
            return self._create_error_response(
                error="execution_failed", message=f"Failed to get script help: {e}"
            )

    """
    {
      "name": "script_run",
      "description": "Execute skill script with arguments. Most scripts support --json for structured output. Check --help first. Max 100 args. Returns script output.",
      "parameters": {
        "type": "object",
        "properties": {
          "skill_name": {
            "type": "string",
            "description": "Skill name"
          },
          "script_name": {
            "type": "string",
            "description": "Script name"
          },
          "args": {
            "type": ["array", "null"],
            "items": {"type": "string"},
            "description": "Script arguments",
            "default": null
          },
          "json_output": {
            "type": "boolean",
            "description": "Request JSON output",
            "default": true
          }
        },
        "required": ["skill_name", "script_name"]
      }
    }
    """

    async def script_run(
        self,
        skill_name: Annotated[str, Field(description="Skill name")],
        script_name: Annotated[str, Field(description="Script name")],
        args: Annotated[list[str] | None, Field(description="Script arguments")] = None,
        json_output: Annotated[bool, Field(description="Request JSON output")] = True,
    ) -> dict:
        """Execute skill script with arguments. Most scripts support --json for structured output. Check --help first. Max 100 args. Returns script output."""
        try:
            # Normalize args
            if args is None:
                args = []

            # Validate args limits
            if len(args) > self.max_args:
                return self._create_error_response(
                    error="args_too_large",
                    message=f"Too many arguments: {len(args)} (max {self.max_args})",
                )

            total_length = sum(len(arg) for arg in args)
            if total_length > self.max_args_length:
                return self._create_error_response(
                    error="args_too_large",
                    message=f"Arguments too large: {total_length} bytes (max {self.max_args_length})",
                )

            # Normalize names
            canonical_skill = normalize_skill_name(skill_name)
            canonical_script = normalize_script_name(script_name)

            # Find script path
            script_path = self._find_script(canonical_skill, canonical_script)
            if script_path is None:
                return self._create_error_response(
                    error="not_found",
                    message=f"Script '{script_name}' not found in skill '{skill_name}'",
                )

            # Build command
            cmd = [self._get_uv_executable(), "run", str(script_path)] + args
            if json_output:
                cmd.append("--json")

            # Execute script
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=script_path.parent,
            )

            try:
                stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=self.timeout)
            except TimeoutError:
                result.kill()
                return self._create_error_response(
                    error="timeout",
                    message=f"Script timed out after {self.timeout}s",
                )

            stdout_text = stdout.decode("utf-8")
            stderr_text = stderr.decode("utf-8")

            # Check output size
            if len(stdout_text) > self.max_output:
                stdout_text = stdout_text[: self.max_output]
                stderr_text += f"\nWarning: Output truncated at {self.max_output} bytes"

            # Handle non-zero exit code
            if result.returncode != 0:
                return self._create_error_response(
                    error="execution_failed",
                    message=f"Script failed with exit code {result.returncode}\nstderr: {stderr_text[-500:]}",
                )

            # Parse JSON if requested
            if json_output:
                try:
                    parsed = json_module.loads(stdout_text)
                    return self._create_success_response(
                        result=parsed, message=f"Executed {script_name} script"
                    )
                except json_module.JSONDecodeError:
                    return self._create_error_response(
                        error="parse_error",
                        message=f"Expected JSON output, got: {stdout_text[:200]}\nstderr: {stderr_text[-500:]}",
                    )
            else:
                # Return plain text
                return self._create_success_response(
                    result=stdout_text, message=f"Executed {script_name} script"
                )

        except Exception as e:
            return self._create_error_response(
                error="execution_failed", message=f"Failed to execute script: {e}"
            )

    def _find_script(self, canonical_skill: str, canonical_script: str) -> Path | None:
        """Find script path by canonical skill and script names.

        Args:
            canonical_skill: Normalized skill name
            canonical_script: Normalized script name (with .py extension)

        Returns:
            Path to script or None if not found
        """
        if canonical_skill not in self.scripts:
            return None

        script_stem = canonical_script.removesuffix(".py")

        for script in self.scripts[canonical_skill]:
            if script["name"] == script_stem:
                script_path: Path = script["path"]
                return script_path

        return None

    def _get_uv_executable(self) -> str:
        """Get uv executable path.

        Tries 'uv' first, falls back to 'python -m uv' if not on PATH.

        Returns:
            uv executable path or fallback command
        """
        # Try 'uv' directly (most common case)
        # For now, assume 'uv' is on PATH
        # Phase 2: Add Windows fallback to sys.executable -m uv
        return "uv"
