#!/usr/bin/env python3
"""
VAST Admin MCP Installer

Installs and configures MCP (Model Context Protocol) servers for VAST Admin tools.
Supports dry-run mode for testing and revert mode for cleanup.

Usage:
    python3 install-vast-mcp.py                 # Standard installation
    python3 install-vast-mcp.py --dry-run       # Preview changes without applying
    python3 install-vast-mcp.py --revert        # Remove installed components
"""

import sys
import os
import json
import subprocess
import platform
import argparse
import logging
import pathlib
import datetime
from typing import Dict, Any, Optional, Tuple

# Constants
INSTALL_DIR = pathlib.Path.home() / ".claude" / "mcp" / "vast-admin"
CONFIG_DIR = pathlib.Path.home() / ".claude" / "config"
INSTALL_LOG_FILE = INSTALL_DIR / "install.log"
INSTALL_STATE_FILE = INSTALL_DIR / "install-state.json"
NEXT_STEPS_FILE = INSTALL_DIR / "NEXT_STEPS.md"
OLLAMA_SETUP_FILE = INSTALL_DIR / "ollama-setup.md"
WRAPPER_SCRIPT = INSTALL_DIR / "vast-admin-mcp.sh"

# Global state
DRY_RUN = False
INSTALL_STATE: Dict[str, Any] = {
    "timestamp": None,
    "os": None,
    "os_version": None,
    "python": None,
    "directories_created": [],
    "files_created": [],
    "files_backed_up": [],
    "clients_configured": [],
    "config_saved": False,
}

# Global logger
logger: Optional[logging.Logger] = None


def setup_logging(log_file: pathlib.Path) -> logging.Logger:
    """
    Configure logging to both stdout and file.

    Args:
        log_file: Path to the log file

    Returns:
        Configured logger instance
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Create logger
    log = logging.getLogger("vast-admin-installer")
    log.setLevel(logging.DEBUG)

    # File handler (DEBUG level)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)

    # Console handler (INFO level)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)

    log.addHandler(file_handler)
    log.addHandler(console_handler)

    return log


def log_info(message: str) -> None:
    """Log an info level message."""
    if logger:
        logger.info(message)


def log_success(message: str) -> None:
    """Log a success message."""
    if logger:
        logger.info(f"✓ {message}")


def log_warn(message: str) -> None:
    """Log a warning level message."""
    if logger:
        logger.warning(message)


def log_error(message: str, fatal: bool = False) -> None:
    """
    Log an error level message.

    Args:
        message: Error message to log
        fatal: If True, exit after logging
    """
    if logger:
        logger.error(message)
    if fatal:
        sys.exit(1)


def print_header(text: str, width: int = 60) -> None:
    """
    Print a centered header.

    Args:
        text: Header text
        width: Total width of the header line
    """
    centered = text.center(width)
    print("\n" + "=" * width)
    print(centered)
    print("=" * width + "\n")


def print_section(title: str) -> None:
    """
    Print a section separator.

    Args:
        title: Section title
    """
    print(f"\n--- {title} ---")


def _detect_linux_distro() -> str:
    """
    Detect Linux distribution from /etc/os-release.

    Returns:
        String like "AlmaLinux 9.2" or "Rocky 8.5"

    Raises:
        SystemExit: If /etc/os-release does not exist
    """
    os_release_path = pathlib.Path("/etc/os-release")

    if not os_release_path.exists():
        log_error(f"/etc/os-release not found. Cannot detect Linux distribution.", fatal=True)

    # Parse /etc/os-release
    os_info = {}
    try:
        with open(os_release_path, "r") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    os_info[key] = value
    except Exception as e:
        log_error(f"Failed to read /etc/os-release: {e}", fatal=True)

    # Extract NAME and VERSION_ID
    name = os_info.get("NAME", "Unknown")
    version = os_info.get("VERSION_ID", "Unknown")
    pretty_name = os_info.get("PRETTY_NAME", "")

    # Check for supported distributions
    supported_distros = ["AlmaLinux", "Rocky", "CentOS", "RHEL", "Fedora"]
    is_supported = any(distro in pretty_name for distro in supported_distros)

    if not is_supported:
        log_warn(
            f"Detected unsupported Linux distribution: {pretty_name}. "
            f"Only AlmaLinux, Rocky, CentOS, RHEL, and Fedora are officially supported."
        )

    return f"{name} {version}"


def detect_os() -> Tuple[str, str]:
    """
    Detect the operating system and version.

    For macOS: Returns ("macos", "X.X") where X.X is the major version
    For Linux: Returns ("linux", "DistroName version")

    Returns:
        Tuple of (os_type, version)

    Raises:
        SystemExit: If OS is neither macOS nor Linux, or on error
    """
    system = platform.system()

    if system == "Darwin":
        # macOS detection
        mac_version = platform.mac_ver()[0]
        if not mac_version:
            log_error("Failed to detect macOS version.", fatal=True)

        # Extract major version number
        try:
            major_version = int(mac_version.split(".")[0])
        except (IndexError, ValueError):
            log_error(f"Invalid macOS version format: {mac_version}", fatal=True)

        # Check if macOS version >= 14
        if major_version < 14:
            log_warn(
                f"macOS {mac_version} is earlier than macOS 14. "
                f"This installer is tested on macOS 14 and later."
            )
            response = input("Continue anyway? (Y/N): ").strip().upper()
            if response != "Y":
                log_error("Installation cancelled by user.", fatal=True)

        INSTALL_STATE["os"] = "macos"
        INSTALL_STATE["os_version"] = mac_version
        log_info(f"Detected: macOS {mac_version}")
        return ("macos", mac_version)

    elif system == "Linux":
        # Linux detection
        linux_distro = _detect_linux_distro()
        INSTALL_STATE["os"] = "linux"
        INSTALL_STATE["os_version"] = linux_distro
        log_info(f"Detected: {linux_distro}")
        return ("linux", linux_distro)

    else:
        log_error(
            f"Unsupported operating system: {system}. "
            f"This installer supports macOS 14+ and RHEL-based Linux distributions.",
            fatal=True
        )


def run_installation() -> None:
    """Run the installation process."""
    print_header("VAST Admin MCP Installer")

    # Detect OS
    os_type, os_version = detect_os()


def run_revert() -> None:
    """Run the revert (cleanup) process."""
    pass


def main() -> None:
    """
    Main entry point.

    Sets up logging, parses arguments, and orchestrates installation or revert.
    """
    global logger, DRY_RUN

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Install and configure MCP servers for VAST Admin tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 install-vast-mcp.py                 # Standard installation
  python3 install-vast-mcp.py --dry-run       # Preview changes without applying
  python3 install-vast-mcp.py --revert        # Remove installed components
        """
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    parser.add_argument(
        "--revert",
        action="store_true",
        help="Remove installed components and revert to previous state"
    )

    args = parser.parse_args()

    # Set global DRY_RUN flag
    DRY_RUN = args.dry_run

    # Setup logging
    logger = setup_logging(INSTALL_LOG_FILE)

    # Initialize install state
    INSTALL_STATE["timestamp"] = datetime.datetime.now().isoformat()
    INSTALL_STATE["os"] = platform.system()
    INSTALL_STATE["os_version"] = platform.release()
    INSTALL_STATE["python"] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    # Print header
    mode = "DRY-RUN" if DRY_RUN else "INSTALLATION"
    if args.revert:
        mode = "REVERT"
    print_header(f"VAST Admin MCP Installer - {mode}")

    # Log environment info
    log_info(f"OS: {INSTALL_STATE['os']} {INSTALL_STATE['os_version']}")
    log_info(f"Python: {INSTALL_STATE['python']}")
    if DRY_RUN:
        log_warn("DRY-RUN MODE: No changes will be applied")

    # Run appropriate mode
    if args.revert:
        run_revert()
    else:
        run_installation()


if __name__ == "__main__":
    main()
