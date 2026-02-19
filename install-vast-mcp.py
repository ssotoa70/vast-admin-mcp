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
from typing import Dict, Any, Optional

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


def run_installation() -> None:
    """Run the installation process."""
    pass


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
