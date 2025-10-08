#!/usr/bin/env python3
"""
Check all files in the project for linting and formatting issues.

This script runs all the same checks as pre-commit but on all files,
not just staged ones.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"Running {description}...")
    try:
        subprocess.run(
            cmd, shell=True, check=True, capture_output=True, text=True
        )
        print(f"✅ {description} passed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(e.stdout)
        print(e.stderr)
        return False


def main():
    """Run all checks on the entire project."""
    project_root = Path(__file__).parent.parent

    # Change to project root
    import os

    os.chdir(project_root)

    print("🔍 Checking all files in the project...")
    print(f"Project root: {project_root}")
    print("-" * 50)

    checks = [
        ("poetry run flake8 .", "flake8 linting"),
        ("poetry run black --check .", "black formatting"),
        ("poetry run isort --check-only .", "isort import sorting"),
        ("poetry run pytest tests/ -v", "pytest tests"),
    ]

    failed_checks = []

    for cmd, description in checks:
        if not run_command(cmd, description):
            failed_checks.append(description)
        print()

    if failed_checks:
        print("❌ The following checks failed:")
        for check in failed_checks:
            print(f"  - {check}")
        print("\n💡 Run the following commands to fix issues:")
        print("  poetry run black .")
        print("  poetry run isort .")
        print("  poetry run flake8 .")
        sys.exit(1)
    else:
        print("🎉 All checks passed!")


if __name__ == "__main__":
    main()
