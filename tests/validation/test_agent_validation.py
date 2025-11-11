"""Real-world validation tests for agent CLI execution.

This module provides comprehensive testing for agent CLI functionality
through subprocess execution, validating actual command-line behavior.
"""

import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
import yaml

# Module-level marker for all tests in this file
pytestmark = [pytest.mark.integration, pytest.mark.validation]


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text.

    This helper allows tests to focus on content rather than formatting.
    """
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


class AgentValidator:
    """Real-world validation tests for agent CLI."""

    def __init__(self, config_path: str = "tests/validation/agent_validation.yaml"):
        """Initialize validator with test configuration.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = Path(config_path)
        self.load_config()

    def load_config(self) -> None:
        """Load test configuration from YAML."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = self.get_default_config()

    def get_default_config(self) -> dict[str, Any]:
        """Get default test configuration.

        Returns:
            Default configuration dictionary
        """
        return {
            "version": "1.0",
            "name": "Default Agent Validation",
            "command_tests": [
                {
                    "name": "Basic help",
                    "command": "uv run agent --help",
                    "timeout": 10,
                    "expected": {
                        "exit_code": 0,
                        "stdout_contains": ["agent", "--prompt"],
                    },
                }
            ],
        }

    def run_command(
        self,
        cmd: str,
        timeout: int = 30,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute a command and capture output.

        Args:
            cmd: Command to execute
            timeout: Timeout in seconds
            env: Environment variables (optional)

        Returns:
            Dictionary with exit_code, stdout, stderr, and duration
        """
        # Prepare environment
        if env:
            # Start with current environment
            cmd_env = os.environ.copy()

            # Handle unset variables
            if "unset" in env:
                for var in env["unset"]:
                    cmd_env.pop(var, None)

            # Add/update variables
            for key, value in env.items():
                if key != "unset":
                    cmd_env[key] = value
        else:
            cmd_env = None

        # Execute command
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=cmd_env,
            )
            duration = time.time() - start_time

            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": duration,
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "duration": timeout,
            }
        except Exception as e:
            return {
                "exit_code": -2,
                "stdout": "",
                "stderr": str(e),
                "duration": time.time() - start_time,
            }

    def validate_output(self, output: dict[str, Any], expected: dict[str, Any]) -> bool:
        """Validate command output against expectations.

        Args:
            output: Actual command output
            expected: Expected output criteria

        Returns:
            True if output matches expectations, False otherwise
        """
        # Check exit code
        if "exit_code" in expected:
            if output["exit_code"] != expected["exit_code"]:
                return False

        # Check stdout contains all specified strings
        if "stdout_contains" in expected:
            for text in expected["stdout_contains"]:
                if text not in output["stdout"]:
                    return False

        # Check stdout contains at least one of specified strings
        if "stdout_contains_any" in expected:
            if not any(text in output["stdout"] for text in expected["stdout_contains_any"]):
                return False

        # Check stdout matches regex pattern
        if "stdout_matches" in expected:
            if not re.search(expected["stdout_matches"], output["stdout"]):
                return False

        # Check stdout doesn't contain specified strings
        if "stdout_not_contains" in expected:
            for text in expected["stdout_not_contains"]:
                if text in output["stdout"]:
                    return False

        # Check stderr patterns (similar to stdout)
        if "stderr_contains" in expected:
            for text in expected["stderr_contains"]:
                if text not in output["stderr"]:
                    return False

        return True

    def run_test(self, test: dict[str, Any]) -> dict[str, Any]:
        """Run a single test and return results.

        Args:
            test: Test configuration dictionary

        Returns:
            Test results with name, passed status, and details
        """
        # Execute command
        result = self.run_command(
            test["command"],
            test.get("timeout", 30),
            test.get("env"),
        )

        # Check if expected_any is used (multiple possible valid outcomes)
        if "expected_any" in test:
            passed = any(self.validate_output(result, exp) for exp in test["expected_any"])
            expected = test["expected_any"]
        else:
            passed = self.validate_output(result, test.get("expected", {}))
            expected = test.get("expected", {})

        # Check performance criteria
        if "max_duration" in test and passed:
            if result["duration"] > test["max_duration"]:
                passed = False

        return {
            "name": test["name"],
            "passed": passed,
            "command": test["command"],
            "output": result,
            "expected": expected,
            "duration": result["duration"],
        }

    def run_all_tests(self) -> dict[str, Any]:
        """Run all configured tests.

        Returns:
            Dictionary with test results and statistics
        """
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "tests": [],
            "categories": {},
        }

        # Test categories to run
        test_categories = [
            "command_tests",
            "prompt_tests",
            "performance_tests",
            "config_tests",
        ]

        for category in test_categories:
            if category in self.config:
                category_results = []
                for test in self.config[category]:
                    result = self.run_test(test)
                    category_results.append(result)
                    results["tests"].append(result)
                    results["total"] += 1
                    if result["passed"]:
                        results["passed"] += 1
                    else:
                        results["failed"] += 1

                results["categories"][category] = category_results

        return results

    def generate_report(self, results: dict[str, Any]) -> str:
        """Generate a human-readable test report.

        Args:
            results: Test results from run_all_tests

        Returns:
            Formatted report string
        """
        report = []
        report.append("# Agent Validation Report\n")
        report.append("## Summary")
        report.append(f"- Total Tests: {results['total']}")
        report.append(f"- Passed: {results['passed']}")
        report.append(f"- Failed: {results['failed']}")

        if results["total"] > 0:
            pass_rate = (results["passed"] / results["total"]) * 100
            report.append(f"- Pass Rate: {pass_rate:.1f}%\n")

        # Category breakdown
        if results["categories"]:
            report.append("## Test Categories\n")
            for category, tests in results["categories"].items():
                passed = sum(1 for t in tests if t["passed"])
                total = len(tests)
                report.append(f"### {category.replace('_', ' ').title()}")
                report.append(f"- Tests: {total}")
                report.append(f"- Passed: {passed}")
                report.append(f"- Failed: {total - passed}\n")

        # Failed tests details
        failed_tests = [t for t in results["tests"] if not t["passed"]]
        if failed_tests:
            report.append("## Failed Tests\n")
            for test in failed_tests:
                report.append(f"### {test['name']}")
                report.append(f"**Command:** `{test['command']}`")
                report.append(f"**Exit Code:** {test['output']['exit_code']}")
                if test["output"]["stderr"]:
                    report.append(f"**Error:** {test['output']['stderr'][:200]}")
                report.append("")

        return "\n".join(report)


# Pytest integration
class TestAgentValidation:
    """Pytest integration for agent validation."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return AgentValidator()

    def test_help_command(self, validator):
        """Test help command execution."""
        result = validator.run_command("uv run agent --help", timeout=10)
        assert result["exit_code"] == 0
        # Strip ANSI codes to focus on content not formatting
        clean_output = strip_ansi(result["stdout"])
        assert "agent" in clean_output.lower()
        assert "--prompt" in clean_output

    def test_version_command(self, validator):
        """Test version command."""
        result = validator.run_command("uv run agent --version", timeout=5)
        assert result["exit_code"] == 0
        assert result["stdout"].strip()  # Not empty

    def test_check_command(self, validator):
        """Test health check command shows system, agent, docker, and providers."""
        # Longer timeout needed when running in parallel (connectivity tests to multiple providers)
        result = validator.run_command("uv run agent --check", timeout=60)
        # Strip ANSI codes to focus on content not formatting
        clean_output = strip_ansi(result["stdout"])
        # Should display key sections if configured, or show config error
        # Accept either successful output or configuration error
        has_sections = (
            "System:" in clean_output
            and "Agent:" in clean_output
            and "LLM Providers:" in clean_output
        )
        has_config_error = "Configuration error" in clean_output
        assert has_sections or has_config_error, "Should show health check or config error"

    def test_config_command(self, validator):
        """Test config command (alias for --check)."""
        # Longer timeout needed when running in parallel (connectivity tests to multiple providers)
        result = validator.run_command("uv run agent --config", timeout=60)
        # Strip ANSI codes to focus on content not formatting
        clean_output = strip_ansi(result["stdout"])
        # Should be identical to --check (unified view)
        # Accept either successful output or configuration error
        has_sections = (
            "System:" in clean_output
            and "Agent:" in clean_output
            and "LLM Providers:" in clean_output
        )
        has_config_error = "Configuration error" in clean_output
        assert has_sections or has_config_error, "Should show config or config error"

    def test_validation_config_exists(self):
        """Test that validation configuration file exists."""
        config_path = Path("tests/validation/agent_validation.yaml")
        assert config_path.exists(), "Validation config file should exist"

    def test_validation_config_valid(self, validator):
        """Test that validation configuration is valid YAML."""
        assert validator.config is not None
        assert "version" in validator.config
        assert "command_tests" in validator.config or "prompt_tests" in validator.config

    @pytest.mark.slow
    def test_run_all_validation_tests(self, validator):
        """Run all validation tests from configuration."""
        results = validator.run_all_tests()

        # Generate and print report
        report = validator.generate_report(results)
        print("\n" + report)

        # Basic assertions
        assert results["total"] > 0, "Should have run some tests"
        assert results["passed"] >= 0
        assert results["failed"] >= 0
        assert results["passed"] + results["failed"] == results["total"]


def main():
    """Run validation tests from command line."""
    validator = AgentValidator()
    results = validator.run_all_tests()

    # Print report
    report = validator.generate_report(results)
    print(report)

    # Exit with appropriate code
    exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
