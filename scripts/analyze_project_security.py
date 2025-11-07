#!/usr/bin/env python3
"""
Project Analysis Script for Security Pre-commit Setup
Analyzes project structure, Python version, and identifies sensitive files/directories.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set


def check_python_version() -> Dict[str, str]:
    """Check Python version compatibility."""
    version_info = sys.version_info
    version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"

    is_compatible = version_info >= (3, 12)

    return {
        "version": version_str,
        "major": str(version_info.major),
        "minor": str(version_info.minor),
        "micro": str(version_info.micro),
        "compatible": is_compatible,
        "required": "3.12+",
        "status": "✓ Compatible" if is_compatible else "✗ Incompatible",
    }


def detect_project_languages(root_path: Path) -> Dict[str, List[str]]:
    """Detect programming languages and file types in the project."""
    languages = {
        "python": [],
        "yaml": [],
        "toml": [],
        "json": [],
        "ini": [],
        "txt": [],
        "markdown": [],
        "shell": [],
        "docker": [],
    }

    # File extension mappings
    ext_map = {
        ".py": "python",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".json": "json",
        ".ini": "ini",
        ".txt": "txt",
        ".md": "markdown",
        ".sh": "shell",
        ".bash": "shell",
    }

    # Special files
    special_files = {
        "Dockerfile": "docker",
        "docker-compose.yml": "docker",
        "docker-compose.override.yml": "docker",
    }

    # Walk through project directory
    for item in root_path.rglob("*"):
        if item.is_file():
            # Skip hidden directories and common excludes
            if any(part.startswith(".") for part in item.parts[1:]):
                if not any(
                    part in [".kiro", ".vscode", ".github"] for part in item.parts
                ):
                    continue

            # Skip virtual environments and cache
            if any(
                part in ["venv", ".venv", "__pycache__", "node_modules", ".git"]
                for part in item.parts
            ):
                continue

            # Check special files
            if item.name in special_files:
                lang = special_files[item.name]
                languages[lang].append(str(item.relative_to(root_path)))
                continue

            # Check by extension
            ext = item.suffix.lower()
            if ext in ext_map:
                lang = ext_map[ext]
                languages[lang].append(str(item.relative_to(root_path)))

    # Sort and limit results
    for lang in languages:
        languages[lang] = sorted(languages[lang])[:50]  # Limit to first 50 files

    return languages


def identify_sensitive_files(root_path: Path) -> Dict[str, List[str]]:
    """Identify files and directories that may contain sensitive information."""
    sensitive_patterns = {
        "environment_files": [".env", ".env.local", ".env.production"],
        "credential_files": [
            "google_service_key.json",
            "credentials.json",
            "service_account.json",
        ],
        "database_files": ["*.db", "*.sqlite", "*.sqlite3"],
        "log_files": ["*.log"],
        "config_files": ["config.json", "config.yaml", "secrets.yaml"],
        "key_files": ["*.pem", "*.key", "*.p12", "*.pfx"],
        "backup_files": ["*.bak", "*.backup"],
    }

    found_sensitive = {category: [] for category in sensitive_patterns}

    for item in root_path.rglob("*"):
        if item.is_file():
            # Skip virtual environments and cache
            if any(
                part in ["venv", ".venv", "__pycache__", "node_modules", ".git"]
                for part in item.parts
            ):
                continue

            rel_path = str(item.relative_to(root_path))

            for category, patterns in sensitive_patterns.items():
                for pattern in patterns:
                    if pattern.startswith("*."):
                        # Extension match
                        if item.suffix == pattern[1:]:
                            found_sensitive[category].append(rel_path)
                    else:
                        # Exact name match
                        if item.name == pattern:
                            found_sensitive[category].append(rel_path)

    return found_sensitive


def identify_directories_for_scanning(root_path: Path) -> Dict[str, List[str]]:
    """Identify directories that should be included/excluded from security scanning."""

    # Directories to scan
    scan_dirs = []
    for item in root_path.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            if item.name not in ["venv", ".venv", "__pycache__", "node_modules"]:
                scan_dirs.append(item.name)

    # Directories to exclude
    exclude_dirs = [
        ".venv",
        "venv",
        "__pycache__",
        ".git",
        ".pytest_cache",
        "node_modules",
        "build",
        "dist",
        "*.egg-info",
        ".mypy_cache",
        ".tox",
        "htmlcov",
    ]

    # Specific subdirectories that need attention
    critical_dirs = ["telegram_bot", "scripts", "tests", "alembic", "docs"]

    return {
        "scan_directories": sorted(scan_dirs),
        "exclude_patterns": exclude_dirs,
        "critical_directories": critical_dirs,
    }


def analyze_dependencies(root_path: Path) -> Dict[str, any]:
    """Analyze project dependencies from requirements.txt and pyproject.toml."""
    deps_info = {
        "requirements_txt": None,
        "pyproject_toml": None,
        "total_dependencies": 0,
        "security_relevant": [],
    }

    # Check requirements.txt
    req_file = root_path / "requirements.txt"
    if req_file.exists():
        with open(req_file, "r") as f:
            lines = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
            deps_info["requirements_txt"] = len(lines)
            deps_info["total_dependencies"] += len(lines)

            # Identify security-relevant packages
            security_keywords = [
                "crypto",
                "auth",
                "security",
                "password",
                "token",
                "jwt",
                "oauth",
            ]
            for line in lines:
                pkg_name = line.split(">=")[0].split("==")[0].split("[")[0].lower()
                if any(keyword in pkg_name for keyword in security_keywords):
                    deps_info["security_relevant"].append(line)

    # Check pyproject.toml
    pyproject_file = root_path / "pyproject.toml"
    if pyproject_file.exists():
        deps_info["pyproject_toml"] = "present"

    return deps_info


def get_project_structure_summary(root_path: Path) -> Dict[str, int]:
    """Get summary statistics about project structure."""
    stats = {
        "total_python_files": 0,
        "total_test_files": 0,
        "total_config_files": 0,
        "total_directories": 0,
    }

    for item in root_path.rglob("*"):
        # Skip excluded directories
        if any(
            part in ["venv", ".venv", "__pycache__", "node_modules", ".git"]
            for part in item.parts
        ):
            continue

        if item.is_dir():
            stats["total_directories"] += 1
        elif item.is_file():
            if item.suffix == ".py":
                stats["total_python_files"] += 1
                if "test" in item.name or "tests" in str(item.parent):
                    stats["total_test_files"] += 1
            elif item.suffix in [".yaml", ".yml", ".toml", ".ini", ".json"]:
                stats["total_config_files"] += 1

    return stats


def main():
    """Main analysis function."""
    root_path = Path.cwd()

    print("=" * 80)
    print("PROJECT SECURITY ANALYSIS REPORT")
    print("=" * 80)
    print()

    # 1. Python Version Check
    print("1. PYTHON VERSION COMPATIBILITY")
    print("-" * 80)
    py_version = check_python_version()
    print(f"   Current Version: {py_version['version']}")
    print(f"   Required Version: {py_version['required']}")
    print(f"   Status: {py_version['status']}")
    print()

    # 2. Project Structure
    print("2. PROJECT STRUCTURE SUMMARY")
    print("-" * 80)
    structure = get_project_structure_summary(root_path)
    print(f"   Total Python Files: {structure['total_python_files']}")
    print(f"   Total Test Files: {structure['total_test_files']}")
    print(f"   Total Config Files: {structure['total_config_files']}")
    print(f"   Total Directories: {structure['total_directories']}")
    print()

    # 3. Languages Detected
    print("3. DETECTED LANGUAGES AND FILE TYPES")
    print("-" * 80)
    languages = detect_project_languages(root_path)
    for lang, files in languages.items():
        if files:
            print(f"   {lang.upper()}: {len(files)} files")
            if len(files) <= 10:
                for f in files[:5]:
                    print(f"      - {f}")
            else:
                for f in files[:3]:
                    print(f"      - {f}")
                print(f"      ... and {len(files) - 3} more")
    print()

    # 4. Dependencies
    print("4. DEPENDENCY ANALYSIS")
    print("-" * 80)
    deps = analyze_dependencies(root_path)
    if deps["requirements_txt"]:
        print(f"   requirements.txt: {deps['requirements_txt']} dependencies")
    if deps["pyproject_toml"]:
        print(f"   pyproject.toml: {deps['pyproject_toml']}")
    print(f"   Total Dependencies: {deps['total_dependencies']}")
    if deps["security_relevant"]:
        print(f"   Security-Relevant Packages:")
        for pkg in deps["security_relevant"][:5]:
            print(f"      - {pkg}")
    print()

    # 5. Sensitive Files
    print("5. SENSITIVE FILES IDENTIFIED")
    print("-" * 80)
    sensitive = identify_sensitive_files(root_path)
    for category, files in sensitive.items():
        if files:
            print(f"   {category.replace('_', ' ').title()}:")
            for f in files:
                print(f"      - {f}")
    print()

    # 6. Directory Scanning Strategy
    print("6. DIRECTORY SCANNING STRATEGY")
    print("-" * 80)
    dirs = identify_directories_for_scanning(root_path)
    print("   Directories to Scan:")
    for d in dirs["scan_directories"]:
        print(f"      - {d}/")
    print()
    print("   Directories to Exclude:")
    for d in dirs["exclude_patterns"][:10]:
        print(f"      - {d}")
    print()
    print("   Critical Directories (High Priority):")
    for d in dirs["critical_directories"]:
        print(f"      - {d}/")
    print()

    # 7. Security Recommendations
    print("7. SECURITY SCANNING RECOMMENDATIONS")
    print("-" * 80)
    print("   Based on the analysis, the following security tools are recommended:")
    print()
    print("   ✓ GitLeaks - For detecting hardcoded secrets in:")
    print("      - Python files (telegram_bot/, scripts/, tests/)")
    print("      - Configuration files (.env, *.yaml, *.toml, *.json)")
    print("      - Documentation (docs/, README.md)")
    print()
    print("   ✓ Bandit - For Python security analysis in:")
    print("      - telegram_bot/ (main application code)")
    print("      - scripts/ (utility scripts)")
    print("      - Exclude: tests/, alembic/versions/")
    print()
    print("   ✓ Safety - For dependency vulnerability scanning:")
    print("      - requirements.txt")
    print("      - pyproject.toml")
    print()
    print("   ✓ Semgrep - For pattern-based security analysis:")
    print("      - Custom rules for Telegram bot security")
    print("      - OWASP Top 10 detection")
    print("      - SQL injection patterns")
    print()
    print("   ✓ Ruff - For fast Python linting and security rules:")
    print("      - All Python files")
    print("      - Security-focused rule sets (S-prefix)")
    print()

    # 8. Summary
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print()
    print(f"✓ Python Version: {py_version['version']} ({py_version['status']})")
    print(f"✓ Project Type: Python Telegram Bot")
    print(f"✓ Total Python Files: {structure['total_python_files']}")
    print(f"✓ Sensitive Files Found: {sum(len(files) for files in sensitive.values())}")
    print(f"✓ Dependencies to Scan: {deps['total_dependencies']}")
    print()
    print("Next Steps:")
    print("  1. Install pre-commit framework and security tools")
    print("  2. Configure security tools based on identified patterns")
    print("  3. Set up pre-commit hooks for automated scanning")
    print("  4. Test configuration with sample vulnerable code")
    print()

    # Export JSON report
    report = {
        "python_version": py_version,
        "project_structure": structure,
        "languages": {k: len(v) for k, v in languages.items() if v},
        "dependencies": deps,
        "sensitive_files": {k: v for k, v in sensitive.items() if v},
        "directories": dirs,
    }

    report_file = root_path / "project_security_analysis.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Detailed report saved to: {report_file}")
    print()


if __name__ == "__main__":
    main()
