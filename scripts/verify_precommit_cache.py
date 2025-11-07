#!/usr/bin/env python3
"""
Caching verification script for pre-commit hooks.

This script verifies that pre-commit caching is working correctly by:
- Running pre-commit twice and comparing execution times
- Verifying tool installations are cached
- Documenting cache locations and invalidation

Requirements: 6.3
"""

import json
import subprocess
import time
from pathlib import Path


class CacheVerifier:
    """Verify pre-commit caching functionality."""

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

    def get_cache_locations(self) -> dict:
        """Identify pre-commit cache locations."""
        print("Identifying cache locations...")

        cache_locations = {}

        # Pre-commit cache directory (tool installations)
        home = Path.home()
        precommit_cache = home / ".cache" / "pre-commit"

        if precommit_cache.exists():
            cache_locations["pre-commit_cache"] = {
                "path": str(precommit_cache),
                "exists": True,
                "size_mb": self._get_dir_size(precommit_cache),
            }
            print(f"  Pre-commit cache: {precommit_cache}")
        else:
            cache_locations["pre-commit_cache"] = {
                "path": str(precommit_cache),
                "exists": False,
            }
            print(f"  Pre-commit cache: Not found at {precommit_cache}")

        # Git hooks directory
        git_hooks = self.repo_root / ".git" / "hooks"
        if git_hooks.exists():
            cache_locations["git_hooks"] = {
                "path": str(git_hooks),
                "exists": True,
                "pre_commit_hook": (git_hooks / "pre-commit").exists(),
            }
            print(f"  Git hooks: {git_hooks}")
        else:
            cache_locations["git_hooks"] = {
                "path": str(git_hooks),
                "exists": False,
            }

        return cache_locations

    def _get_dir_size(self, path: Path) -> float:
        """Calculate directory size in MB."""
        try:
            total_size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            return round(total_size / (1024 * 1024), 2)
        except (OSError, PermissionError):
            return 0.0

    def verify_cache_speedup(self) -> dict:
        """Verify that second run is faster due to caching."""
        print("\nVerifying cache speedup...")

        # Create a test file
        test_file = self.repo_root / "test_cache_verify.py"
        test_file.write_text(
            '''"""Test module for cache verification."""


def test_function():
    """A simple test function."""
    return "Hello, World!"
'''
        )

        try:
            # Stage the file
            subprocess.run(
                ["git", "add", str(test_file)],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
            )

            # First run (cold cache)
            print("  Running pre-commit (first run - cold cache)...")
            elapsed1, returncode1, _ = self.run_command(
                ["pre-commit", "run", "--files", str(test_file)]
            )
            print(f"    First run: {elapsed1:.2f}s")

            # Second run (warm cache)
            print("  Running pre-commit (second run - warm cache)...")
            elapsed2, returncode2, _ = self.run_command(
                ["pre-commit", "run", "--files", str(test_file)]
            )
            print(f"    Second run: {elapsed2:.2f}s")

            # Calculate speedup
            speedup_percent = ((elapsed1 - elapsed2) / elapsed1 * 100) if elapsed1 > 0 else 0

            # Unstage the file
            subprocess.run(
                ["git", "reset", "HEAD", str(test_file)],
                check=False,
                cwd=self.repo_root,
                capture_output=True,
            )

            # Cache is working if second run is faster or similar
            # (similar times indicate files haven't changed)
            cache_working = elapsed2 <= elapsed1 * 1.1  # Allow 10% variance

            result = {
                "first_run_time": round(elapsed1, 2),
                "second_run_time": round(elapsed2, 2),
                "speedup_percent": round(speedup_percent, 2),
                "cache_working": cache_working,
                "status": "PASS" if cache_working else "FAIL",
                "message": (
                    f"Cache working - {speedup_percent:.1f}% speedup"
                    if cache_working
                    else "Cache may not be working - second run slower"
                ),
            }

            print(f"  Speedup: {speedup_percent:.1f}% - {result['status']}")
            return result

        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()

    def verify_tool_cache(self) -> dict:
        """Verify that tool installations are cached."""
        print("\nVerifying tool installation cache...")

        cache_locations = self.get_cache_locations()

        if not cache_locations.get("pre-commit_cache", {}).get("exists"):
            return {
                "status": "FAIL",
                "message": "Pre-commit cache directory not found",
                "cache_exists": False,
            }

        cache_path = Path(cache_locations["pre-commit_cache"]["path"])

        # Check for cached tool installations
        cached_tools = []
        if cache_path.exists():
            # Pre-commit stores tools in subdirectories
            for item in cache_path.iterdir():
                if item.is_dir():
                    cached_tools.append(item.name)

        result = {
            "cache_path": str(cache_path),
            "cache_size_mb": cache_locations["pre-commit_cache"].get("size_mb", 0),
            "cached_items": len(cached_tools),
            "cache_exists": True,
            "status": "PASS" if len(cached_tools) > 0 else "WARN",
            "message": (
                f"Found {len(cached_tools)} cached items"
                if len(cached_tools) > 0
                else "Cache directory exists but is empty"
            ),
        }

        print(f"  Cached items: {len(cached_tools)} - {result['status']}")
        return result

    def document_cache_invalidation(self) -> dict:
        """Document cache invalidation methods."""
        print("\nDocumenting cache invalidation methods...")

        invalidation_methods = {
            "manual_clean": {
                "command": "pre-commit clean",
                "description": "Removes all cached tool installations",
                "use_case": "Force reinstall of all tools",
            },
            "version_change": {
                "trigger": "Changing 'rev' in .pre-commit-config.yaml",
                "description": "Automatically invalidates cache for that tool",
                "use_case": "Updating to new tool version",
            },
            "config_change": {
                "trigger": "Modifying tool configuration files",
                "description": "May require manual cache clean",
                "use_case": "Changing tool behavior",
            },
            "autoupdate": {
                "command": "pre-commit autoupdate",
                "description": "Updates tool versions and invalidates cache",
                "use_case": "Updating all tools to latest versions",
            },
        }

        result = {
            "invalidation_methods": invalidation_methods,
            "status": "INFO",
            "message": "Cache invalidation methods documented",
        }

        print("  Cache invalidation methods:")
        for method, details in invalidation_methods.items():
            if "command" in details:
                print(f"    - {method}: {details['command']}")
            else:
                print(f"    - {method}: {details['trigger']}")

        return result

    def run_all_verifications(self) -> dict:
        """Run all cache verifications."""
        print("\n" + "=" * 60)
        print("Pre-commit Cache Verification")
        print("=" * 60 + "\n")

        self.results["cache_locations"] = self.get_cache_locations()
        self.results["cache_speedup"] = self.verify_cache_speedup()
        self.results["tool_cache"] = self.verify_tool_cache()
        self.results["invalidation"] = self.document_cache_invalidation()

        self.print_summary()

        return self.results

    def print_summary(self):
        """Print verification summary."""
        print("\n" + "=" * 60)
        print("Cache Verification Summary")
        print("=" * 60 + "\n")

        if "cache_speedup" in self.results:
            status = self.results["cache_speedup"]["status"]
            speedup = self.results["cache_speedup"].get("speedup_percent", 0)
            print(f"Cache speedup: {status} ({speedup:.1f}% faster)")

        if "tool_cache" in self.results:
            status = self.results["tool_cache"]["status"]
            items = self.results["tool_cache"].get("cached_items", 0)
            print(f"Tool cache: {status} ({items} items cached)")

        if "cache_locations" in self.results:
            precommit_cache = self.results["cache_locations"].get("pre-commit_cache", {})
            if precommit_cache.get("exists"):
                size = precommit_cache.get("size_mb", 0)
                print(f"Cache size: {size} MB")

        print("\n" + "=" * 60)
        print("✓ Cache verification complete")
        print("=" * 60 + "\n")

    def save_results(self, output_file: Path):
        """Save verification results to JSON file."""
        output_file.write_text(json.dumps(self.results, indent=2))
        print(f"Results saved to: {output_file}")


def main():
    """Main entry point."""
    repo_root = Path(__file__).parent.parent
    verifier = CacheVerifier(repo_root)

    results = verifier.run_all_verifications()

    # Save results
    output_file = repo_root / "precommit_cache_verification.json"
    verifier.save_results(output_file)


if __name__ == "__main__":
    main()
