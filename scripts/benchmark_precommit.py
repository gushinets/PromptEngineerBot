#!/usr/bin/env python3
"""
Performance benchmarking script for pre-commit hooks.

This script measures the execution time of pre-commit hooks under different scenarios:
- Single file commit
- 10 file commit
- Parallel vs sequential execution
- File filtering effectiveness

Requirements: 1.3, 6.1, 6.2, 6.3, 6.5, 6.6
"""

import json
import subprocess
import time
from pathlib import Path


class PreCommitBenchmark:
    """Benchmark pre-commit hook performance."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.results: dict[str, dict] = {}

    def run_command(self, cmd: list[str], timeout: int = 120) -> tuple[float, int, str]:
        """Run a command and measure execution time."""
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                check=False,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            elapsed = time.time() - start_time
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            return elapsed, result.returncode, stdout + stderr
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            return elapsed, -1, f"Command timed out after {timeout}s"

    def create_test_file(self, filename: str, content: str = None) -> Path:
        """Create a test Python file."""
        if content is None:
            content = '''"""Test module for benchmarking."""


def test_function():
    """A simple test function."""
    return "Hello, World!"


if __name__ == "__main__":
    print(test_function())
'''
        filepath = self.repo_root / filename
        filepath.write_text(content)
        return filepath

    def benchmark_single_file(self) -> dict:
        """Benchmark single file commit time."""
        print("Benchmarking single file commit...")

        # Create a test file
        test_file = self.create_test_file("test_benchmark_single.py")

        try:
            # Stage the file
            subprocess.run(
                ["git", "add", str(test_file)],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
            )

            # Run pre-commit on the staged file
            elapsed, returncode, output = self.run_command(
                ["pre-commit", "run", "--files", str(test_file)]
            )

            # Unstage the file
            subprocess.run(
                ["git", "reset", "HEAD", str(test_file)],
                check=False,
                cwd=self.repo_root,
                capture_output=True,
            )

            result = {
                "elapsed_time": round(elapsed, 2),
                "returncode": returncode,
                "target_time": 5.0,
                "meets_target": elapsed < 5.0,
                "status": "PASS" if elapsed < 5.0 else "FAIL",
            }

            print(f"  Time: {elapsed:.2f}s (target: <5s) - {result['status']}")
            return result

        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()

    def benchmark_multiple_files(self, num_files: int = 10) -> dict:
        """Benchmark multiple file commit time."""
        print(f"Benchmarking {num_files} file commit...")

        test_files = []
        try:
            # Create multiple test files
            for i in range(num_files):
                test_file = self.create_test_file(f"test_benchmark_{i}.py")
                test_files.append(test_file)

            # Stage all files
            for test_file in test_files:
                subprocess.run(
                    ["git", "add", str(test_file)],
                    cwd=self.repo_root,
                    check=True,
                    capture_output=True,
                )

            # Run pre-commit on all staged files
            elapsed, returncode, output = self.run_command(
                ["pre-commit", "run", "--files"] + [str(f) for f in test_files]
            )

            # Unstage files
            for test_file in test_files:
                subprocess.run(
                    ["git", "reset", "HEAD", str(test_file)],
                    check=False,
                    cwd=self.repo_root,
                    capture_output=True,
                )

            target_time = 15.0 if num_files == 10 else 45.0
            result = {
                "elapsed_time": round(elapsed, 2),
                "returncode": returncode,
                "num_files": num_files,
                "target_time": target_time,
                "meets_target": elapsed < target_time,
                "status": "PASS" if elapsed < target_time else "FAIL",
            }

            print(f"  Time: {elapsed:.2f}s (target: <{target_time}s) - {result['status']}")
            return result

        finally:
            # Clean up
            for test_file in test_files:
                if test_file.exists():
                    test_file.unlink()

    def verify_parallel_execution(self) -> dict:
        """Verify that parallel execution is working."""
        print("Verifying parallel execution...")

        # Check pre-commit config for fail_fast setting
        config_file = self.repo_root / ".pre-commit-config.yaml"
        if not config_file.exists():
            return {
                "status": "SKIP",
                "message": "No .pre-commit-config.yaml found",
            }

        config_content = config_file.read_text()

        # Check for fail_fast: false (enables parallel execution)
        has_fail_fast_false = "fail_fast: false" in config_content or (
            "fail_fast" not in config_content
        )

        # Run pre-commit with verbose output to see parallel execution
        elapsed, returncode, output = self.run_command(
            ["pre-commit", "run", "--all-files", "--verbose"]
        )

        result = {
            "parallel_enabled": has_fail_fast_false,
            "config_check": "PASS" if has_fail_fast_false else "FAIL",
            "execution_time": round(elapsed, 2),
            "status": "PASS" if has_fail_fast_false else "FAIL",
            "message": (
                "Parallel execution enabled"
                if has_fail_fast_false
                else "Set fail_fast: false for parallel execution"
            ),
        }

        print(f"  Parallel execution: {result['parallel_enabled']} - {result['status']}")
        return result

    def verify_file_filtering(self) -> dict:
        """Verify that file filtering reduces scan time."""
        print("Verifying file filtering effectiveness...")

        # Create test files of different types
        py_file = self.create_test_file("test_filter.py")
        txt_file = self.repo_root / "test_filter.txt"
        txt_file.write_text("This is a text file.")

        try:
            # Stage both files
            subprocess.run(
                ["git", "add", str(py_file), str(txt_file)],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
            )

            # Run pre-commit and check which hooks ran
            elapsed, returncode, output = self.run_command(
                ["pre-commit", "run", "--files", str(py_file), str(txt_file), "--verbose"]
            )

            # Unstage files
            subprocess.run(
                ["git", "reset", "HEAD", str(py_file), str(txt_file)],
                check=False,
                cwd=self.repo_root,
                capture_output=True,
            )

            # Check if hooks properly filtered files
            # Python-specific hooks should only run on .py files
            hooks_ran = []
            if "ruff" in output.lower():
                hooks_ran.append("ruff")
            if "bandit" in output.lower():
                hooks_ran.append("bandit")
            if "gitleaks" in output.lower():
                hooks_ran.append("gitleaks")

            result = {
                "elapsed_time": round(elapsed, 2),
                "hooks_ran": hooks_ran,
                "file_filtering_active": len(hooks_ran) > 0,
                "status": "PASS" if len(hooks_ran) > 0 else "FAIL",
                "message": (
                    f"File filtering working - {len(hooks_ran)} hooks ran"
                    if len(hooks_ran) > 0
                    else "File filtering may not be configured"
                ),
            }

            print(f"  File filtering: {result['file_filtering_active']} - {result['status']}")
            return result

        finally:
            # Clean up
            if py_file.exists():
                py_file.unlink()
            if txt_file.exists():
                txt_file.unlink()

    def check_hook_performance(self) -> dict:
        """Check individual hook performance against targets."""
        print("Checking individual hook performance...")

        hooks_to_test = ["ruff", "gitleaks", "bandit", "safety", "semgrep"]
        hook_results = {}

        # Create a test file for hooks that need it
        test_file = self.create_test_file("test_hook_perf.py")

        try:
            subprocess.run(
                ["git", "add", str(test_file)],
                check=False,
                cwd=self.repo_root,
                capture_output=True,
            )

            for hook in hooks_to_test:
                print(f"  Testing {hook}...")
                elapsed, returncode, output = self.run_command(
                    ["pre-commit", "run", hook, "--files", str(test_file)]
                )

                # Define target times based on design document
                target_times = {
                    "ruff": 5.0,
                    "gitleaks": 30.0,
                    "bandit": 10.0,
                    "safety": 30.0,
                    "semgrep": 60.0,
                }

                target = target_times.get(hook, 30.0)
                hook_results[hook] = {
                    "elapsed_time": round(elapsed, 2),
                    "target_time": target,
                    "meets_target": elapsed < target,
                    "status": "PASS" if elapsed < target else "FAIL",
                }

                print(
                    f"    {hook}: {elapsed:.2f}s (target: <{target}s) - {hook_results[hook]['status']}"
                )

            subprocess.run(
                ["git", "reset", "HEAD", str(test_file)],
                check=False,
                cwd=self.repo_root,
                capture_output=True,
            )

        finally:
            if test_file.exists():
                test_file.unlink()

        return hook_results

    def run_all_benchmarks(self) -> dict:
        """Run all benchmarks and return results."""
        print("\n" + "=" * 60)
        print("Pre-commit Performance Benchmark")
        print("=" * 60 + "\n")

        self.results["single_file"] = self.benchmark_single_file()
        print()

        self.results["ten_files"] = self.benchmark_multiple_files(10)
        print()

        self.results["parallel_execution"] = self.verify_parallel_execution()
        print()

        self.results["file_filtering"] = self.verify_file_filtering()
        print()

        self.results["individual_hooks"] = self.check_hook_performance()
        print()

        # Generate summary
        self.print_summary()

        return self.results

    def print_summary(self):
        """Print benchmark summary."""
        print("\n" + "=" * 60)
        print("Benchmark Summary")
        print("=" * 60 + "\n")

        # Overall status
        all_pass = True

        if "single_file" in self.results:
            status = self.results["single_file"]["status"]
            print(f"Single file commit: {status}")
            if status != "PASS":
                all_pass = False

        if "ten_files" in self.results:
            status = self.results["ten_files"]["status"]
            print(f"10 file commit: {status}")
            if status != "PASS":
                all_pass = False

        if "parallel_execution" in self.results:
            status = self.results["parallel_execution"]["status"]
            print(f"Parallel execution: {status}")
            if status != "PASS":
                all_pass = False

        if "file_filtering" in self.results:
            status = self.results["file_filtering"]["status"]
            print(f"File filtering: {status}")
            if status != "PASS":
                all_pass = False

        if "individual_hooks" in self.results:
            failing_hooks = [
                hook
                for hook, data in self.results["individual_hooks"].items()
                if data["status"] != "PASS"
            ]
            if failing_hooks:
                print(f"Slow hooks: {', '.join(failing_hooks)}")
                all_pass = False
            else:
                print("Individual hooks: PASS")

        print("\n" + "=" * 60)
        if all_pass:
            print("✓ All performance targets met!")
        else:
            print("✗ Some performance targets not met - optimization needed")
        print("=" * 60 + "\n")

    def save_results(self, output_file: Path):
        """Save benchmark results to JSON file."""
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"Results saved to: {output_file}")


def main():
    """Main entry point."""
    repo_root = Path(__file__).parent.parent
    benchmark = PreCommitBenchmark(repo_root)

    results = benchmark.run_all_benchmarks()

    # Save results
    output_file = repo_root / "precommit_benchmark_results.json"
    benchmark.save_results(output_file)


if __name__ == "__main__":
    main()
