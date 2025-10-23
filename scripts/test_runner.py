#!/usr/bin/env python3
"""
Test runner with failed test tracking.

This script tracks failed tests and runs only failed ones on subsequent runs
until all tests pass, then resets to run all tests again.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import List


class TestRunner:
    """Test runner that tracks failed tests."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.state_file = project_root / ".test_state.json"
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Load test state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"failed_tests": [], "last_run_all": True}

    def _save_state(self) -> None:
        """Save test state to file."""
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def _run_pytest(self, test_args: List[str]) -> tuple[int, List[str]]:
        """Run pytest and return exit code and failed test list."""
        cmd = [
            "poetry",
            "run",
            "python",
            "-m",
            "pytest",
            "--tb=short",
            "-v",
        ] + test_args

        print(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False,
            )

            # Show pytest output to user
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)

            # Parse failed tests from output
            failed_tests = []
            if result.returncode != 0:
                # Extract test names from pytest output
                lines = result.stdout.split("\n") + result.stderr.split("\n")
                for line in lines:
                    if "FAILED" in line and "::" in line:
                        # Extract test name from line like:
                        # tests/test_file.py::test_function FAILED
                        # or tests/test_file.py::test_function - AssertionError: message
                        if " - " in line:
                            test_name = line.split(" - ")[0].strip()
                        else:
                            # Look for pattern like "tests/file.py::test_name FAILED"
                            parts = line.strip().split()
                            test_name = None
                            for part in parts:
                                if "::" in part and not part.startswith("="):
                                    test_name = part
                                    break

                        if (
                            test_name
                            and "::" in test_name
                            and not test_name.startswith("FAILED")
                        ):
                            failed_tests.append(test_name)

            # Remove duplicates while preserving order
            seen = set()
            unique_failed_tests = []
            for test in failed_tests:
                if test not in seen:
                    seen.add(test)
                    unique_failed_tests.append(test)
            failed_tests = unique_failed_tests

            return result.returncode, failed_tests

        except Exception as e:
            print(f"Error running pytest: {e}")
            return 1, []

    def _get_all_test_files(self) -> List[str]:
        """Get all test files in the tests directory."""
        tests_dir = self.project_root / "tests"
        if not tests_dir.exists():
            return []

        test_files = []
        for file_path in tests_dir.glob("test_*.py"):
            test_files.append(str(file_path.relative_to(self.project_root)))

        return sorted(test_files)

    def run_tests(self) -> int:
        """Run tests with failed test tracking."""
        failed_tests = self.state.get("failed_tests", [])
        last_run_all = self.state.get("last_run_all", True)

        # If we have failed tests from previous run, run only those
        if failed_tests and not last_run_all:
            print("Running previously failed tests only...")
            test_args = failed_tests
        else:
            print("Running all tests...")
            test_args = self._get_all_test_files()

        exit_code, new_failed_tests = self._run_pytest(test_args)

        if exit_code == 0:
            # All tests passed
            if failed_tests:
                print("All previously failed tests now pass! Resetting state.")
                self.state = {"failed_tests": [], "last_run_all": True}
            else:
                print("All tests pass!")
                self.state = {"failed_tests": [], "last_run_all": True}
        else:
            # Some tests failed
            if last_run_all:
                # First run with failures - store failed tests
                print(
                    f"Found {len(new_failed_tests)} failed tests. "
                    "Next run will only test these."
                )
                self.state = {
                    "failed_tests": new_failed_tests,
                    "last_run_all": False,
                }
            else:
                # Subsequent run with failures - update failed tests
                print(f"Still have {len(new_failed_tests)} failed tests.")
                self.state = {
                    "failed_tests": new_failed_tests,
                    "last_run_all": False,
                }

        self._save_state()
        return exit_code

    def reset_state(self) -> None:
        """Reset test state to run all tests."""
        self.state = {"failed_tests": [], "last_run_all": True}
        self._save_state()
        print("Test state reset. Next run will test all tests.")

    def show_status(self) -> None:
        """Show current test status."""
        failed_tests = self.state.get("failed_tests", [])
        last_run_all = self.state.get("last_run_all", True)

        if failed_tests:
            print(f"Currently tracking {len(failed_tests)} failed tests:")
            for test in failed_tests:
                print(f"  - {test}")
            print("Next run will test only these failed tests.")
        else:
            print("No failed tests tracked. Next run will test all tests.")

        print(
            f"Last run was: {'all tests' if last_run_all else 'failed tests only'}"
        )


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python test_runner.py <command>")
        print("Commands:")
        print("  run     - Run tests with failed test tracking")
        print("  reset   - Reset state to run all tests")
        print("  status  - Show current test status")
        sys.exit(1)

    command = sys.argv[1]
    project_root = Path(__file__).parent.parent
    runner = TestRunner(project_root)

    if command == "run":
        exit_code = runner.run_tests()
        sys.exit(exit_code)
    elif command == "reset":
        runner.reset_state()
    elif command == "status":
        runner.show_status()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
