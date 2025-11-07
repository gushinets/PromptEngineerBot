#!/usr/bin/env python3
"""
Security Tools Installation Script

Automated installation and setup of pre-commit security configuration.
This script installs and validates all security tools required for the project.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
"""

import platform
import subprocess
import sys
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class ProgressIndicator:
    """Simple progress indicator for installation steps"""

    def __init__(self, total_steps: int):
        self.total_steps = total_steps
        self.current_step = 0

    def next_step(self, description: str):
        """Move to next step and display progress"""
        self.current_step += 1
        progress = (self.current_step / self.total_steps) * 100
        print(
            f"\n{Colors.CYAN}[{self.current_step}/{self.total_steps}] "
            f"({progress:.0f}%) {description}{Colors.RESET}"
        )


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message"""
    try:
        print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")
    except UnicodeEncodeError:
        print(f"{Colors.GREEN}[OK] {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message"""
    try:
        print(f"{Colors.RED}✗ {text}{Colors.RESET}")
    except UnicodeEncodeError:
        print(f"{Colors.RED}[ERROR] {text}{Colors.RESET}")


def print_warning(text: str):
    """Print warning message"""
    try:
        print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")
    except UnicodeEncodeError:
        print(f"{Colors.YELLOW}[WARNING] {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message"""
    try:
        print(f"{Colors.CYAN}i {text}{Colors.RESET}")
    except UnicodeEncodeError:
        print(f"{Colors.CYAN}[INFO] {text}{Colors.RESET}")


def run_command(
    cmd: list[str],
    check: bool = True,
    capture_output: bool = True,
    timeout: int = 300,
) -> subprocess.CompletedProcess | None:
    """
    Run a command and return the result.

    Args:
        cmd: Command to run as list of strings
        check: Whether to raise exception on non-zero exit
        capture_output: Whether to capture stdout/stderr
        timeout: Command timeout in seconds

    Returns:
        CompletedProcess object or None on error
    """
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
        )
        return result
    except subprocess.TimeoutExpired:
        print_error(f"Command timed out after {timeout}s: {' '.join(cmd)}")
        return None
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed with exit code {e.returncode}: {' '.join(cmd)}")
        if capture_output and e.stderr:
            print_error(f"Error output: {e.stderr[:500]}")
        return None
    except Exception as e:
        print_error(f"Unexpected error running command: {e}")
        return None


def detect_python_version() -> tuple[bool, str]:
    """
    Detect Python version and verify compatibility.

    Returns:
        Tuple of (is_compatible, version_string)
    """
    version_info = sys.version_info
    version_string = f"{version_info.major}.{version_info.minor}.{version_info.micro}"

    # Requirement 8.1: Python 3.12+
    is_compatible = version_info >= (3, 12)

    return is_compatible, version_string


def detect_environment() -> dict[str, str]:
    """
    Detect the current environment and system information.

    Returns:
        Dictionary with environment details
    """
    env_info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
    }

    # Detect if running in virtual environment
    env_info["in_venv"] = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )

    # Detect git
    git_result = run_command(["git", "--version"], check=False)
    env_info["git_available"] = git_result is not None and git_result.returncode == 0
    if env_info["git_available"] and git_result:
        env_info["git_version"] = git_result.stdout.strip()

    return env_info


def install_pip_package(package_name: str, display_name: str | None = None) -> bool:
    """
    Install a Python package via pip.

    Args:
        package_name: Package name for pip install
        display_name: Human-readable name for display

    Returns:
        True if installation successful, False otherwise
    """
    display = display_name or package_name

    print_info(f"Installing {display}...")

    # Try to install the package
    result = run_command(
        [sys.executable, "-m", "pip", "install", "--upgrade", package_name],
        check=False,
    )

    if result and result.returncode == 0:
        print_success(f"{display} installed successfully")
        return True

    print_error(f"Failed to install {display}")
    if result and result.stderr:
        print_error(f"Error: {result.stderr[:300]}")

    return False


def validate_tool_installation(
    command: list[str], tool_name: str, version_flag: str = "--version"
) -> tuple[bool, str | None]:
    """
    Validate that a tool is installed and accessible.

    Args:
        command: Command to run (e.g., ["ruff"])
        tool_name: Human-readable tool name
        version_flag: Flag to get version info

    Returns:
        Tuple of (is_installed, version_string)
    """
    try:
        result = run_command([*command, version_flag], check=False, timeout=10)

        if result and result.returncode == 0:
            version = result.stdout.strip().split("\n")[0]
            return True, version

        return False, None

    except Exception as e:
        print_error(f"Error validating {tool_name}: {e}")
        return False, None


def install_precommit_framework() -> bool:
    """
    Install pre-commit framework.

    Requirement 8.2: Install pre-commit framework
    """
    print_info("Installing pre-commit framework...")

    # Install pre-commit
    if not install_pip_package("pre-commit", "Pre-commit framework"):
        return False

    # Validate installation
    is_installed, version = validate_tool_installation(["pre-commit"], "pre-commit", "--version")

    if is_installed:
        print_success(f"Pre-commit framework validated: {version}")
        return True

    print_error("Pre-commit framework installation could not be validated")
    return False


def install_ruff() -> bool:
    """
    Install Ruff for Python linting and formatting.

    Requirement 8.2: Install Ruff
    """
    print_info("Installing Ruff...")

    # Install Ruff
    if not install_pip_package("ruff", "Ruff"):
        return False

    # Validate installation
    is_installed, version = validate_tool_installation(["ruff"], "Ruff", "--version")

    if is_installed:
        print_success(f"Ruff validated: {version}")
        return True

    print_error("Ruff installation could not be validated")
    return False


def install_gitleaks() -> bool:
    """
    Install GitLeaks for secrets detection.

    Requirement 8.2: Install GitLeaks
    Note: GitLeaks is a Go binary, installation method varies by platform
    """
    print_info("Installing GitLeaks...")

    system = platform.system()

    # Check if already installed
    is_installed, version = validate_tool_installation(["gitleaks"], "GitLeaks", "version")
    if is_installed:
        print_success(f"GitLeaks already installed: {version}")
        return True

    # Platform-specific installation
    if system == "Windows":
        print_warning("GitLeaks installation on Windows requires manual setup or package manager")
        print_info("Please install GitLeaks using one of these methods:")
        print_info("  1. Download from: https://github.com/gitleaks/gitleaks/releases")
        print_info("  2. Using Chocolatey: choco install gitleaks")
        print_info("  3. Using Scoop: scoop install gitleaks")
        print_warning("Continuing without GitLeaks - please install manually")
        return False

    if system == "Darwin":  # macOS
        print_info("Attempting to install GitLeaks via Homebrew...")
        result = run_command(["brew", "install", "gitleaks"], check=False)
        if result and result.returncode == 0:
            is_installed, version = validate_tool_installation(["gitleaks"], "GitLeaks", "version")
            if is_installed:
                print_success(f"GitLeaks installed: {version}")
                return True

    elif system == "Linux":
        print_info("Attempting to install GitLeaks...")
        # Try to download and install binary
        print_warning("GitLeaks installation on Linux may require manual setup")
        print_info("Please install GitLeaks using one of these methods:")
        print_info("  1. Download from: https://github.com/gitleaks/gitleaks/releases")
        print_info("  2. Using package manager (if available)")
        print_warning("Continuing without GitLeaks - please install manually")
        return False

    print_warning("GitLeaks not installed - secrets detection will be limited")
    return False


def install_bandit() -> bool:
    """
    Install Bandit for Python security analysis.

    Requirement 8.2: Install Bandit
    """
    print_info("Installing Bandit...")

    # Install Bandit
    if not install_pip_package("bandit", "Bandit"):
        return False

    # Validate installation
    is_installed, version = validate_tool_installation(["bandit"], "Bandit", "--version")

    if is_installed:
        print_success(f"Bandit validated: {version}")
        return True

    print_error("Bandit installation could not be validated")
    return False


def install_safety() -> bool:
    """
    Install Safety for dependency scanning.

    Requirement 8.2: Install Safety
    """
    print_info("Installing Safety...")

    # Install Safety
    if not install_pip_package("safety", "Safety"):
        return False

    # Validate installation
    is_installed, version = validate_tool_installation(["safety"], "Safety", "--version")

    if is_installed:
        print_success(f"Safety validated: {version}")
        return True

    print_error("Safety installation could not be validated")
    return False


def install_semgrep() -> bool:
    """
    Install Semgrep for pattern-based analysis.

    Requirement 8.2: Install Semgrep
    """
    print_info("Installing Semgrep...")

    # Install Semgrep
    if not install_pip_package("semgrep", "Semgrep"):
        return False

    # Validate installation
    is_installed, version = validate_tool_installation(["semgrep"], "Semgrep", "--version")

    if is_installed:
        print_success(f"Semgrep validated: {version}")
        return True

    print_error("Semgrep installation could not be validated")
    return False


def install_git_hooks() -> bool:
    """
    Install git hooks using pre-commit.

    Requirement 8.3: Configure git hooks
    """
    print_info("Installing git hooks...")

    # Check if .pre-commit-config.yaml exists
    if not Path(".pre-commit-config.yaml").exists():
        print_error(".pre-commit-config.yaml not found")
        print_error("Please ensure the pre-commit configuration file exists")
        return False

    # Install hooks
    result = run_command(["pre-commit", "install"], check=False)

    if result and result.returncode == 0:
        print_success("Git hooks installed successfully")

        # Install hooks for all stages
        result = run_command(["pre-commit", "install", "--hook-type", "commit-msg"], check=False)

        # Verify hooks are installed
        hooks_dir = Path(".git/hooks")
        if hooks_dir.exists() and (hooks_dir / "pre-commit").exists():
            print_success("Pre-commit hook verified in .git/hooks/")
            return True

        print_warning("Git hooks installed but could not verify")
        return True

    print_error("Failed to install git hooks")
    return False


def validate_configuration_files() -> bool:
    """
    Validate that all configuration files exist.

    Requirement 8.4: Validate configuration
    """
    print_info("Validating configuration files...")

    required_files = {
        ".pre-commit-config.yaml": "Pre-commit configuration",
        ".gitleaks.toml": "GitLeaks configuration",
        ".bandit": "Bandit configuration",
        "ruff.toml": "Ruff configuration",
        ".semgrep.yml": "Semgrep configuration",
    }

    all_exist = True

    for file_path, description in required_files.items():
        if Path(file_path).exists():
            print_success(f"{description} found: {file_path}")
        else:
            print_warning(f"{description} not found: {file_path}")
            all_exist = False

    if all_exist:
        # Validate pre-commit config syntax
        result = run_command(["pre-commit", "validate-config"], check=False)
        if result and result.returncode == 0:
            print_success("Pre-commit configuration is valid")
            return True
        print_error("Pre-commit configuration validation failed")
        return False

    print_warning("Some configuration files are missing")
    print_info("The setup will continue, but some tools may not work correctly")
    return False


def install_precommit_hooks_dependencies() -> bool:
    """
    Install pre-commit hook dependencies.

    Requirement 8.5: Install hook dependencies
    """
    print_info("Installing pre-commit hook dependencies...")

    # This will download and install all hook dependencies
    result = run_command(["pre-commit", "install", "--install-hooks"], check=False, timeout=600)

    if result and result.returncode == 0:
        print_success("Pre-commit hook dependencies installed")
        return True

    print_warning("Some hook dependencies may not have installed correctly")
    print_info("Hooks will be installed on first use")
    return True  # Non-critical, hooks install on first run


def print_installation_summary(results: dict[str, bool]):
    """
    Print a summary of installation results.

    Args:
        results: Dictionary mapping tool names to installation success status
    """
    print_header("Installation Summary")

    installed = []
    failed = []

    for tool, success in results.items():
        if success:
            installed.append(tool)
            print_success(f"{tool}: Installed and validated")
        else:
            failed.append(tool)
            print_error(f"{tool}: Installation failed or not available")

    print(f"\n{Colors.BOLD}Results:{Colors.RESET}")
    print(f"  {Colors.GREEN}✓ Installed: {len(installed)}/{len(results)}{Colors.RESET}")

    if failed:
        print(f"  {Colors.RED}✗ Failed: {len(failed)}/{len(results)}{Colors.RESET}")
        print(f"\n{Colors.YELLOW}Failed tools:{Colors.RESET}")
        for tool in failed:
            print(f"    - {tool}")


def print_next_steps(results: dict[str, bool]):
    """
    Print next steps based on installation results.

    Args:
        results: Dictionary mapping tool names to installation success status
    """
    print_header("Next Steps")

    # Check critical tools
    critical_tools = ["Pre-commit Framework", "Ruff", "Bandit"]
    critical_missing = [tool for tool in critical_tools if not results.get(tool, False)]

    if critical_missing:
        print_error("Critical tools are missing!")
        print_info("Please install the following tools manually:")
        for tool in critical_missing:
            print(f"  - {tool}")
        print()

    # Check optional tools
    optional_tools = ["GitLeaks", "Safety", "Semgrep"]
    optional_missing = [tool for tool in optional_tools if not results.get(tool, False)]

    if optional_missing:
        print_warning("Some optional tools are missing:")
        for tool in optional_missing:
            print(f"  - {tool}")
        print_info("Security coverage will be reduced without these tools")
        print()

    # Success case
    if not critical_missing:
        print_success("Core security tools are installed!")
        print()
        print(f"{Colors.BOLD}You can now:{Colors.RESET}")
        print("  1. Test the configuration:")
        print(f"     {Colors.CYAN}pre-commit run --all-files{Colors.RESET}")
        print()
        print("  2. Make a commit to test hooks:")
        print(f"     {Colors.CYAN}git add . && git commit -m 'test'{Colors.RESET}")
        print()
        print("  3. Run individual tools:")
        print(f"     {Colors.CYAN}ruff check .{Colors.RESET}")
        print(f"     {Colors.CYAN}bandit -r telegram_bot/{Colors.RESET}")
        print()
        print("  4. View documentation:")
        print(f"     {Colors.CYAN}docs/security/pre-commit-setup.md{Colors.RESET}")
        print()


def main():
    """Main installation function"""
    print_header("Security Tools Installation")
    print(f"{Colors.BOLD}Automated setup for pre-commit security configuration{Colors.RESET}\n")

    # Step 1: Detect environment (Requirement 8.1)
    progress = ProgressIndicator(10)
    progress.next_step("Detecting environment")

    env_info = detect_environment()

    print_info(f"Operating System: {env_info['os']} ({env_info['architecture']})")
    print_info(f"Python Version: {env_info['python_version']}")
    print_info(f"Python Implementation: {env_info['python_implementation']}")
    print_info(f"Virtual Environment: {'Yes' if env_info['in_venv'] else 'No'}")
    print_info(f"Git Available: {'Yes' if env_info['git_available'] else 'No'}")

    # Verify Python version (Requirement 8.1)
    is_compatible, version = detect_python_version()
    if not is_compatible:
        print_error(f"Python {version} is not compatible")
        print_error("This project requires Python 3.12 or higher")
        print_info("Please upgrade Python and try again")
        return 1

    print_success(f"Python {version} is compatible")

    # Check git
    if not env_info["git_available"]:
        print_error("Git is not available")
        print_error("Git is required for pre-commit hooks")
        return 1

    # Check if in git repository
    if not Path(".git").exists():
        print_error("Not in a git repository")
        print_error("Please run this script from the project root")
        return 1

    # Warn if not in virtual environment
    if not env_info["in_venv"]:
        print_warning("Not running in a virtual environment")
        print_info("It's recommended to use a virtual environment")
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != "y":
            print_info("Installation cancelled")
            return 0

    # Track installation results
    results = {}

    # Step 2: Install pre-commit framework (Requirement 8.2)
    progress.next_step("Installing pre-commit framework")
    results["Pre-commit Framework"] = install_precommit_framework()

    if not results["Pre-commit Framework"]:
        print_error("Pre-commit framework is required but failed to install")
        print_error("Cannot continue without pre-commit framework")
        return 1

    # Step 3: Install Ruff (Requirement 8.2)
    progress.next_step("Installing Ruff")
    results["Ruff"] = install_ruff()

    # Step 4: Install GitLeaks (Requirement 8.2)
    progress.next_step("Installing GitLeaks")
    results["GitLeaks"] = install_gitleaks()

    # Step 5: Install Bandit (Requirement 8.2)
    progress.next_step("Installing Bandit")
    results["Bandit"] = install_bandit()

    # Step 6: Install Safety (Requirement 8.2)
    progress.next_step("Installing Safety")
    results["Safety"] = install_safety()

    # Step 7: Install Semgrep (Requirement 8.2)
    progress.next_step("Installing Semgrep")
    results["Semgrep"] = install_semgrep()

    # Step 8: Validate configuration files (Requirement 8.4)
    progress.next_step("Validating configuration files")
    validate_configuration_files()

    # Step 9: Install git hooks (Requirement 8.3)
    progress.next_step("Installing git hooks")
    results["Git Hooks"] = install_git_hooks()

    # Step 10: Install hook dependencies (Requirement 8.5)
    progress.next_step("Installing hook dependencies")
    install_precommit_hooks_dependencies()

    # Print summary (Requirement 8.6)
    print()
    print_installation_summary(results)

    # Print next steps
    print_next_steps(results)

    # Determine exit code
    critical_tools = ["Pre-commit Framework", "Ruff", "Bandit", "Git Hooks"]
    critical_failed = any(not results.get(tool, False) for tool in critical_tools)

    if critical_failed:
        print_error("\nInstallation completed with errors")
        print_info("Please resolve the errors above and run the script again")
        return 1

    print_success("\n✓ Installation completed successfully!")
    print_info("Your security configuration is ready to use")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Installation cancelled by user{Colors.RESET}")
        sys.exit(130)
    except Exception as e:
        print_error(f"\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
