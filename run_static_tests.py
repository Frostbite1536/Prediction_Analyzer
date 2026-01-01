#!/usr/bin/env python3
"""
Static Pattern Test Runner

Run this script BEFORE implementing new features to ensure the codebase
is in a stable state and all patterns/contracts are maintained.

Usage:
    python run_static_tests.py              # Run all static tests
    python run_static_tests.py --quick      # Run only import tests (fastest)
    python run_static_tests.py --coverage   # Run with coverage report
    python run_static_tests.py --verbose    # Run with verbose output
    python run_static_tests.py --category imports  # Run specific category

Categories:
    imports     - Import integrity tests
    api         - API contract tests
    dataclass   - Trade dataclass tests
    config      - Configuration integrity tests
    filters     - Filter behavior tests
    pnl         - PnL calculation tests
    edge        - Edge case tests
    integrity   - Data integrity tests
    utility     - Utility function tests
"""
import sys
import subprocess
import argparse
from pathlib import Path


# Test categories and their corresponding test files
TEST_CATEGORIES = {
    "imports": "test_imports.py",
    "api": "test_api_contracts.py",
    "dataclass": "test_dataclass_contracts.py",
    "config": "test_config_integrity.py",
    "filters": "test_filter_contracts.py",
    "pnl": "test_pnl_contracts.py",
    "edge": "test_edge_cases.py",
    "integrity": "test_data_integrity.py",
    "utility": "test_utility_functions.py",
}


def get_test_path():
    """Get the path to the static_patterns test directory."""
    return Path(__file__).parent / "tests" / "static_patterns"


def run_tests(args):
    """Run the tests with specified options."""
    test_path = get_test_path()

    # Build pytest command
    cmd = ["python", "-m", "pytest"]

    # Add verbosity
    if args.verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")

    # Add coverage if requested
    if args.coverage:
        cmd.extend([
            "--cov=prediction_analyzer",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
        ])

    # Determine which tests to run
    if args.quick:
        # Quick mode: only run import tests
        cmd.append(str(test_path / "test_imports.py"))
        print("Running quick import tests only...")
    elif args.category:
        # Run specific category
        if args.category not in TEST_CATEGORIES:
            print(f"Unknown category: {args.category}")
            print(f"Available categories: {', '.join(TEST_CATEGORIES.keys())}")
            return 1
        test_file = TEST_CATEGORIES[args.category]
        cmd.append(str(test_path / test_file))
        print(f"Running {args.category} tests...")
    else:
        # Run all static pattern tests
        cmd.append(str(test_path))
        print("Running all static pattern tests...")

    # Add any extra pytest args
    if args.pytest_args:
        cmd.extend(args.pytest_args)

    print(f"Command: {' '.join(cmd)}\n")
    print("=" * 60)

    # Run pytest
    result = subprocess.run(cmd)

    print("=" * 60)

    if result.returncode == 0:
        print("\nAll tests passed! Safe to implement new features.")
    else:
        print("\nSome tests failed! Fix issues before implementing new features.")

    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Run static pattern tests before implementing new features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Run only import tests (fastest check)"
    )

    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run with coverage report"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Run with verbose output"
    )

    parser.add_argument(
        "--category",
        choices=list(TEST_CATEGORIES.keys()),
        help="Run only tests from a specific category"
    )

    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="Additional arguments to pass to pytest"
    )

    args = parser.parse_args()
    sys.exit(run_tests(args))


if __name__ == "__main__":
    main()
