#!/usr/bin/env python
"""Standalone runner for agent validation tests.

This script can be run directly to execute all validation tests
without requiring pytest.

Usage:
    python tests/run_validation.py
    # or
    uv run python tests/run_validation.py
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.integration.test_agent_validation import AgentValidator


def main():
    """Main entry point for validation runner."""
    parser = argparse.ArgumentParser(
        description="Run agent validation tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python tests/run_validation.py

  # Use custom config
  python tests/run_validation.py --config custom_tests.yaml

  # Output JSON format
  python tests/run_validation.py --json

  # Verbose output
  python tests/run_validation.py --verbose
        """,
    )

    parser.add_argument(
        "--config",
        type=str,
        default="tests/integration/agent_validation.yaml",
        help="Path to validation config file (default: tests/integration/agent_validation.yaml)",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output (show all test details)",
    )

    parser.add_argument(
        "--category",
        type=str,
        choices=["command_tests", "prompt_tests", "performance_tests", "config_tests"],
        help="Run only tests from specific category",
    )

    args = parser.parse_args()

    # Initialize validator
    try:
        validator = AgentValidator(config_path=args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Filter config if category specified
    if args.category:
        original_config = validator.config.copy()
        validator.config = {
            k: v
            for k, v in original_config.items()
            if k == args.category or k in ["version", "name", "description"]
        }

    # Run tests
    print("Running agent validation tests...\n")
    results = validator.run_all_tests()

    # Output results
    if args.json:
        # JSON output
        print(json.dumps(results, indent=2))
    else:
        # Human-readable output
        report = validator.generate_report(results)
        print(report)

        # Verbose mode - show all test details
        if args.verbose:
            print("\n## Detailed Test Results\n")
            for test in results["tests"]:
                status = "✅ PASSED" if test["passed"] else "❌ FAILED"
                print(f"### {test['name']} - {status}")
                print(f"Command: {test['command']}")
                print(f"Duration: {test['duration']:.2f}s")
                if not test["passed"]:
                    print(f"Exit Code: {test['output']['exit_code']}")
                    if test["output"]["stderr"]:
                        print(f"Error: {test['output']['stderr'][:200]}")
                    print(f"Expected: {test['expected']}")
                print()

    # Exit with appropriate code
    exit_code = 0 if results["failed"] == 0 else 1

    if not args.json:
        print(f"\nExiting with code {exit_code}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
