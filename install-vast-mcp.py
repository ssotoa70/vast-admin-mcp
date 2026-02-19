#!/usr/bin/env python3
"""
VAST Admin MCP Installation Script

Cross-platform installer for VAST Admin MCP.
Supports: macOS 14+, AlmaLinux, Rocky Linux, CentOS, RHEL, Fedora

Usage:
    python3 install-vast-mcp.py              # Install (default)
    python3 install-vast-mcp.py --dry-run    # Preview without making changes
    python3 install-vast-mcp.py --revert     # Undo previous installation
"""

import sys
import os
import json
import subprocess
import platform
import argparse
import logging
import socket
import shutil
import glob
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Optional, List

# ============================================================================
# CONSTANTS & CONFIGURATION
# ============================================================================

INSTALL_DIR = Path.home() / "vast-mcp"
CONFIG_DIR = Path.home() / ".vast-admin-mcp"
INSTALL_LOG_FILE = INSTALL_DIR / "install.log"
INSTALL_STATE_FILE = INSTALL_DIR / "INSTALL_LOG.json"
NEXT_STEPS_FILE = INSTALL_DIR / "NEXT_STEPS.txt"
OLLAMA_SETUP_FILE = INSTALL_DIR / "OLLAMA_SETUP.txt"
WRAPPER_SCRIPT = INSTALL_DIR / "run-vast.sh"

# Global state
DRY_RUN = False
logger = None
INSTALL_STATE = {
    "timestamp": datetime.now().isoformat(),
    "os": None,
    "os_version": None,
    "python": None,
    "directories_created": [],
    "files_created": [],
    "files_backed_up": [],
    "clients_configured": [],
    "config_saved": False,
}

# ============================================================================
# LOGGING & OUTPUT FUNCTIONS
# ============================================================================


def setup_logging() -> logging.Logger:
    """Configure logging for installation."""
    log_format = "[%(asctime)s] %(levelname)s: %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(INSTALL_LOG_FILE, mode="a"),
        ],
    )
    return logging.getLogger(__name__)


def log_info(msg: str):
    """Log info message."""
    if logger:
        logger.info(msg)
    print(f"ℹ {msg}")


def log_success(msg: str):
    """Log success message."""
    if logger:
        logger.info(f"✓ {msg}")
    print(f"✓ {msg}")


def log_warn(msg: str):
    """Log warning message."""
    if logger:
        logger.warning(f"⚠ {msg}")
    print(f"⚠ {msg}")


def log_error(msg: str, fatal: bool = False):
    """Log error message."""
    if logger:
        logger.error(f"✗ {msg}")
    print(f"✗ {msg}", file=sys.stderr)
    if fatal:
        sys.exit(1)


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(text.center(60))
    print("=" * 60 + "\n")


def print_section(text: str):
    """Print a section separator."""
    print(f"\n→ {text}")
    print("-" * 60)


# ============================================================================
# OS DETECTION
# ============================================================================


def detect_os() -> Tuple[str, str]:
    """
    Detect operating system and version.

    Returns:
        Tuple of (os_type, version) where os_type is 'macos' or 'linux'

    Raises:
        SystemExit if unsupported OS
    """
    system = platform.system()

    if system == "Darwin":
        # macOS
        mac_version = platform.mac_ver()[0]
        major_version = int(mac_version.split(".")[0])

        log_info(f"Detected: macOS {mac_version}")

        if major_version < 14:
            log_warn(f"macOS {major_version} is older than recommended (macOS 14+)")
            response = input("\nContinue anyway? (Y/N): ").strip().upper()
            if response != "Y":
                log_error("Installation cancelled. Please upgrade macOS.", fatal=True)

        INSTALL_STATE["os"] = "macos"
        INSTALL_STATE["os_version"] = mac_version
        return "macos", mac_version

    elif system == "Linux":
        # Detect Linux distribution
        linux_distro = _detect_linux_distro()
        log_info(f"Detected: {linux_distro}")
        INSTALL_STATE["os"] = "linux"
        INSTALL_STATE["os_version"] = linux_distro
        return "linux", linux_distro

    else:
        log_error(f"Unsupported OS: {system}", fatal=True)


def _detect_linux_distro() -> str:
    """Detect Linux distribution from /etc/os-release."""
    os_release_path = Path("/etc/os-release")

    if not os_release_path.exists():
        log_error("Cannot determine Linux distribution (/etc/os-release not found)", fatal=True)

    with open(os_release_path) as f:
        lines = f.readlines()

    os_info = {}
    for line in lines:
        if "=" in line:
            key, val = line.strip().split("=", 1)
            os_info[key] = val.strip('"')

    name = os_info.get("NAME", "Unknown")
    version = os_info.get("VERSION_ID", "Unknown")

    # Check if it's a supported RHEL-based distro
    pretty_name = os_info.get("PRETTY_NAME", "")
    supported_distros = ["AlmaLinux", "Rocky", "CentOS", "RHEL", "Fedora"]

    if not any(distro in pretty_name for distro in supported_distros):
        log_warn(f"Warning: {pretty_name} may not be fully supported")

    return f"{name} {version}"


# ============================================================================
# PYTHON DETECTION & SELECTION
# ============================================================================


def find_python_installations() -> List[Tuple[str, Tuple[int, int]]]:
    """
    Find all Python 3.10+ installations on system.

    Returns:
        List of (path, (major, minor)) tuples sorted by version (newest first)
    """
    python_paths = [
        "/usr/local/bin/python3",
        "/usr/bin/python3",
        "/opt/local/bin/python3",
        os.path.expanduser("~/.pyenv/versions/*/bin/python3"),
    ]

    found = {}

    # Check common paths
    for path_str in python_paths:
        if "*" in path_str:
            # Handle glob patterns
            for path in glob.glob(path_str):
                _check_python_path(path, found)
        else:
            _check_python_path(path_str, found)

    # Check PATH
    python_cmd = shutil.which("python3")
    if python_cmd:
        _check_python_path(python_cmd, found)

    if not found:
        log_error("No Python 3.10+ installation found.", fatal=True)

    # Sort by version descending (newest first)
    sorted_pythons = sorted(found.items(), key=lambda x: x[1], reverse=True)
    return sorted_pythons


def _check_python_path(path: str, results: Dict[str, Tuple[int, int]]):
    """Check if Python at path is 3.10+ and add to results."""
    try:
        result = subprocess.run(
            [path, "--version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            version_str = result.stdout.strip()  # "Python 3.12.0"
            version_parts = version_str.split()[-1].split(".")
            major = int(version_parts[0])
            minor = int(version_parts[1])

            if major > 3 or (major == 3 and minor >= 10):
                # Store as (major, minor) tuple for sorting
                results[path] = (major, minor)
    except Exception:
        pass


def select_python() -> str:
    """
    Show user all Python installations and let them select one.

    Returns:
        Path to selected Python executable
    """
    pythons = find_python_installations()

    if len(pythons) == 1:
        path, version = pythons[0]
        log_success(f"Using Python {version[0]}.{version[1]} at {path}")
        return path

    print_section("Multiple Python Installations Found")
    print("\nAvailable Python versions:\n")

    for i, (path, (major, minor)) in enumerate(pythons, 1):
        marker = " <- RECOMMENDED" if i == 1 else ""
        print(f"  {i}) {path} ({major}.{minor}){marker}")

    while True:
        response = input("\nSelect Python version (enter number): ").strip()
        try:
            idx = int(response) - 1
            if 0 <= idx < len(pythons):
                selected_path, (major, minor) = pythons[idx]
                log_success(f"Using Python {major}.{minor} at {selected_path}")
                INSTALL_STATE["python"] = selected_path
                return selected_path
        except ValueError:
            pass
        print("Invalid selection. Please try again.")


# ============================================================================
# PREREQUISITE VALIDATION
# ============================================================================


def check_jq_installed() -> bool:
    """Check if jq is installed."""
    try:
        result = subprocess.run(["jq", "--version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def install_jq(os_type: str):
    """
    Install jq package.

    Args:
        os_type: 'macos' or 'linux'
    """
    if check_jq_installed():
        log_success("jq is already installed")
        return

    log_info("jq not found. Installing...")

    if DRY_RUN:
        log_info("[DRY-RUN] Would install jq")
        return

    try:
        if os_type == "macos":
            # Check if Homebrew is installed
            result = subprocess.run(["which", "brew"], capture_output=True, timeout=5)
            if result.returncode != 0:
                log_error(
                    "Homebrew not found. Please install from https://brew.sh",
                    fatal=True,
                )

            log_info("Running: brew install jq")
            result = subprocess.run(["brew", "install", "jq"], timeout=120)
            if result.returncode == 0:
                log_success("jq installed successfully")
            else:
                log_error("Failed to install jq via Homebrew", fatal=True)

        else:  # linux
            log_info("Running: sudo dnf install jq (or yum)")
            # Try dnf first, fall back to yum
            result = subprocess.run(
                ["sudo", "dnf", "install", "-y", "jq"], timeout=120
            )
            if result.returncode != 0:
                # Try yum for older systems
                result = subprocess.run(
                    ["sudo", "yum", "install", "-y", "jq"], timeout=120
                )

            if result.returncode == 0:
                log_success("jq installed successfully")
            else:
                log_error("Failed to install jq. Please install manually.", fatal=True)

    except Exception as e:
        log_error(f"Error installing jq: {e}", fatal=True)


def check_disk_space() -> bool:
    """
    Check if enough disk space in home directory.

    Returns:
        True if sufficient space (>1GB), False otherwise
    """
    try:
        stat = os.statvfs(Path.home())
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)

        log_info(f"Available disk space: {free_gb:.1f}GB")

        if free_gb < 1:
            log_warn(f"Low disk space: {free_gb:.1f}GB (need >1GB)")
            response = input("Continue anyway? (Y/N): ").strip().upper()
            return response == "Y"

        return True
    except Exception:
        log_warn("Could not determine disk space")
        return True


def check_internet() -> bool:
    """
    Check if internet is accessible by trying to resolve pypi.org.

    Returns:
        True if internet available
    """
    try:
        socket.create_connection(("pypi.org", 443), timeout=5)
        return True
    except Exception:
        return False


# ============================================================================
# DIRECTORY & ENVIRONMENT SETUP
# ============================================================================


def setup_directories(python_exe: str) -> Tuple[Path, Path]:
    """
    Create installation directory and virtual environment.

    Args:
        python_exe: Path to Python executable

    Returns:
        Tuple of (install_dir, venv_dir)
    """
    print_section("Setting Up Installation Directory")

    venv_dir = INSTALL_DIR / "venv"

    # Check if directory exists
    if INSTALL_DIR.exists():
        log_info(f"Installation directory exists: {INSTALL_DIR}")
        response = input("Reinstall? (Y/N): ").strip().upper()
        if response != "Y":
            log_info("Using existing installation")
            return INSTALL_DIR, venv_dir

        if DRY_RUN:
            log_info("[DRY-RUN] Would remove existing installation")
        else:
            log_info("Backing up existing installation...")
            backup_dir = INSTALL_DIR.parent / f"vast-mcp.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            shutil.move(str(INSTALL_DIR), str(backup_dir))
            log_success(f"Backed up to {backup_dir}")

    # Create directory
    if DRY_RUN:
        log_info(f"[DRY-RUN] Would create {INSTALL_DIR}")
    else:
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)
        INSTALL_STATE["directories_created"].append(str(INSTALL_DIR))
        log_success(f"Created {INSTALL_DIR}")

    # Create virtual environment
    log_info(f"Creating virtual environment with {python_exe}...")

    if DRY_RUN:
        log_info(f"[DRY-RUN] Would run: {python_exe} -m venv {venv_dir}")
    else:
        try:
            subprocess.run(
                [python_exe, "-m", "venv", str(venv_dir)], check=True, timeout=60
            )
            log_success(f"Virtual environment created at {venv_dir}")
        except subprocess.CalledProcessError:
            log_error("Failed to create virtual environment", fatal=True)

    # Upgrade pip
    pip_exe = venv_dir / "bin" / "pip"

    log_info("Upgrading pip...")

    if DRY_RUN:
        log_info(f"[DRY-RUN] Would run: {pip_exe} install --upgrade pip")
    else:
        try:
            subprocess.run(
                [str(pip_exe), "install", "--upgrade", "pip"],
                check=True,
                timeout=120,
                capture_output=True,
            )
            log_success("pip upgraded")
        except subprocess.CalledProcessError as e:
            log_warn(f"Failed to upgrade pip: {e}")

    return INSTALL_DIR, venv_dir


def create_wrapper_script(python_exe: str):
    """
    Create wrapper script to avoid Python PATH issues.

    Args:
        python_exe: Path to Python executable
    """
    wrapper_content = f"""#!/bin/bash
# VAST Admin MCP wrapper script
# This script uses the explicit Python path to avoid PATH issues

{python_exe} -m vast_admin_mcp "$@"
"""

    if DRY_RUN:
        log_info(f"[DRY-RUN] Would create wrapper script at {WRAPPER_SCRIPT}")
    else:
        WRAPPER_SCRIPT.write_text(wrapper_content)
        os.chmod(WRAPPER_SCRIPT, 0o755)
        INSTALL_STATE["files_created"].append(str(WRAPPER_SCRIPT))
        log_success(f"Created wrapper script at {WRAPPER_SCRIPT}")


# ============================================================================
# PACKAGE INSTALLATION & VALIDATION
# ============================================================================


def install_vast_admin_mcp(venv_dir: Path) -> bool:
    """
    Install vast-admin-mcp via pip.

    Args:
        venv_dir: Path to virtual environment

    Returns:
        True if successful
    """
    print_section("Installing VAST Admin MCP")

    pip_exe = venv_dir / "bin" / "pip"

    log_info("Installing vast-admin-mcp package...")

    if DRY_RUN:
        log_info("[DRY-RUN] Would run: pip install vast-admin-mcp")
        return True

    try:
        subprocess.run(
            [str(pip_exe), "install", "vast-admin-mcp"],
            check=True,
            timeout=300,
        )
        log_success("VAST Admin MCP installed successfully")
        INSTALL_STATE["config_saved"] = True
        return True
    except subprocess.CalledProcessError as e:
        log_error(f"Failed to install vast-admin-mcp: {e}", fatal=True)


def validate_installation(venv_dir: Path) -> bool:
    """
    Validate that VAST Admin MCP is installed and working.

    Args:
        venv_dir: Path to virtual environment

    Returns:
        True if validation passed
    """
    print_section("Validating Installation")

    vast_mcp_exe = venv_dir / "bin" / "vast-admin-mcp"

    if DRY_RUN:
        log_info("[DRY-RUN] Would validate vast-admin-mcp")
        return True

    try:
        result = subprocess.run(
            [str(vast_mcp_exe), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            log_success("vast-admin-mcp command is working")
            return True
        else:
            log_error(f"vast-admin-mcp --help returned error: {result.stderr}", fatal=True)
    except Exception as e:
        log_error(f"Failed to validate installation: {e}", fatal=True)


# ============================================================================
# CLUSTER CREDENTIALS
# ============================================================================


def configure_credentials() -> bool:
    """
    Prompt user for cluster credentials and save configuration.

    Returns:
        True if credentials saved, False if skipped
    """
    print_section("Cluster Configuration (Optional)")

    log_info("You can configure cluster credentials now, or skip and do it later.")

    response = input("\nConfigure cluster credentials? (Y/N): ").strip().upper()
    if response != "Y":
        log_info("Skipping credential configuration")
        return False

    print("\nEnter cluster connection details:")
    cluster_address = input("  Cluster address (e.g., 192.168.1.100): ").strip()
    username = input("  Username: ").strip()
    password = input("  Password: ").strip()

    if not cluster_address or not username or not password:
        log_warn("Incomplete credentials, skipping")
        return False

    config_dict = {
        "cluster_address": cluster_address,
        "username": username,
        "password": password,
    }

    # Test connection
    if not DRY_RUN:
        log_info("Testing cluster connection...")
        if not test_cluster_connection(cluster_address, username, password):
            log_warn("Failed to connect to cluster (but saved config anyway)")

    # Save credentials
    if DRY_RUN:
        log_info(f"[DRY-RUN] Would save config to {CONFIG_DIR / 'config.json'}")
    else:
        save_credentials(config_dict)

    return True


def test_cluster_connection(address: str, username: str, password: str) -> bool:
    """
    Test connection to VAST cluster.

    Returns:
        True if connection successful
    """
    try:
        # Simple TCP connection test to cluster address
        socket.create_connection((address, 443), timeout=10)
        log_success("Cluster connection test passed")
        return True
    except Exception as e:
        log_warn(f"Cluster connection test failed: {e}")
        return False


def save_credentials(config_dict: Dict):
    """
    Save credentials to config file.

    Args:
        config_dict: Configuration dictionary
    """
    if CONFIG_DIR.exists() and (CONFIG_DIR / "config.json").exists():
        # Back up existing config
        backup_path = CONFIG_DIR / "config.json.backup"
        shutil.copy(CONFIG_DIR / "config.json", backup_path)
        INSTALL_STATE["files_backed_up"].append(
            {"path": str(CONFIG_DIR / "config.json"), "backup": str(backup_path)}
        )
        log_info(f"Backed up existing config to {backup_path}")

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_file = CONFIG_DIR / "config.json"

    with open(config_file, "w") as f:
        json.dump(config_dict, f, indent=2)

    # Set restrictive permissions on config file
    os.chmod(config_file, 0o600)

    INSTALL_STATE["config_saved"] = True
    INSTALL_STATE["files_created"].append(str(config_file))
    log_success(f"Configuration saved to {config_file}")


# ============================================================================
# CLIENT DETECTION
# ============================================================================


def detect_installed_clients(os_type: str) -> Dict[str, bool]:
    """
    Detect which MCP clients are installed on system.

    Args:
        os_type: 'macos' or 'linux'

    Returns:
        Dictionary of client_name -> is_installed
    """
    clients = {}

    # Claude Desktop
    if os_type == "macos":
        claude_path = Path.home() / "Library" / "Application Support" / "Claude"
        clients["claude-desktop"] = claude_path.exists()
    else:
        # Linux: check for Claude in common locations
        claude_paths = [
            Path.home() / ".config" / "Claude",
            Path("/opt/Claude"),
        ]
        clients["claude-desktop"] = any(p.exists() for p in claude_paths)

    # VSCode
    if os_type == "macos":
        vscode_app = Path("/Applications/Visual Studio Code.app")
        clients["vscode"] = vscode_app.exists()
    else:
        clients["vscode"] = shutil.which("code") is not None

    # ChatGPT desktop app
    if os_type == "macos":
        chatgpt_app = Path("/Applications/ChatGPT.app")
        clients["chatgpt"] = chatgpt_app.exists()
    else:
        clients["chatgpt"] = False  # Less common on Linux

    # Ollama
    if os_type == "macos":
        ollama_app = Path("/Applications/Ollama.app")
        clients["ollama"] = ollama_app.exists()
    else:
        clients["ollama"] = shutil.which("ollama") is not None

    return clients


def show_detected_clients(clients: Dict[str, bool]):
    """Show detected clients to user."""
    print_section("Client Detection")

    detected = [name for name, installed in clients.items() if installed]

    if not detected:
        log_info("No MCP clients detected")
        return

    log_success(f"Found {len(detected)} client(s):")
    for client in detected:
        print(f"  ✓ {client.upper()}")


# ============================================================================
# CLIENT CONFIGURATION
# ============================================================================


def ask_which_clients_to_configure(clients: Dict[str, bool]) -> List[str]:
    """
    Ask user which clients to configure.

    Args:
        clients: Dictionary of detected clients

    Returns:
        List of clients to configure
    """
    detected = [name for name, installed in clients.items() if installed]

    if not detected:
        log_info("No clients detected to configure")
        return []

    print_section("Configure MCP Clients")
    print("\nWhich clients would you like to configure?\n")

    selected = []
    for i, client in enumerate(detected, 1):
        if client == "ollama":
            # Ollama requires special handling
            continue

        response = input(f"Configure {client.upper()}? (Y/N): ").strip().upper()
        if response == "Y":
            selected.append(client)

    # Ask about Ollama separately
    if "ollama" in detected:
        response = input(f"\nConfigure OLLAMA? (Y/N): ").strip().upper()
        if response == "Y":
            selected.append("ollama")

    return selected


def configure_claude_desktop(venv_dir: Path, os_type: str):
    """Configure Claude Desktop MCP server."""
    log_info("Configuring Claude Desktop...")

    if os_type == "macos":
        config_path = (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    else:
        config_path = (
            Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
        )

    vast_mcp_path = str(venv_dir / "bin" / "vast-admin-mcp")

    # Read existing config or create new
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        INSTALL_STATE["files_backed_up"].append(
            {"path": str(config_path), "backup": str(config_path) + ".backup"}
        )
    else:
        config = {"mcpServers": {}}

    # Add VAST Admin MCP
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"]["VAST Admin MCP"] = {"command": vast_mcp_path, "args": ["mcp"]}

    if DRY_RUN:
        log_info(f"[DRY-RUN] Would update Claude Desktop config at {config_path}")
    else:
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Backup if exists
        if config_path.exists():
            backup_path = Path(str(config_path) + ".backup")
            shutil.copy(config_path, backup_path)

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        INSTALL_STATE["clients_configured"].append("claude-desktop")
        log_success("Claude Desktop configured")
        log_warn("IMPORTANT: Restart Claude Desktop completely for changes to take effect")
        log_warn("  1. Quit Claude Desktop (Cmd+Q on macOS)")
        log_warn("  2. Wait 2 seconds")
        log_warn("  3. Reopen Claude Desktop")


def configure_vscode(venv_dir: Path):
    """Configure VSCode MCP server."""
    log_info("Configuring VSCode...")

    vast_mcp_path = str(venv_dir / "bin" / "vast-admin-mcp")

    # VSCode config paths
    config_paths = [
        Path.home() / ".vscode" / "mcp.json",
        Path.home()
        / "Library"
        / "Application Support"
        / "Code"
        / "User"
        / "mcp.json",
    ]

    vscode_config = {
        "servers": {
            "VAST Admin MCP": {
                "command": vast_mcp_path,
                "args": ["mcp"],
                "type": "stdio",
            }
        }
    }

    if DRY_RUN:
        for path in config_paths:
            log_info(f"[DRY-RUN] Would update VSCode config at {path}")
    else:
        for config_path in config_paths:
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Read existing or create new
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                backup_path = Path(str(config_path) + ".backup")
                shutil.copy(config_path, backup_path)
                INSTALL_STATE["files_backed_up"].append(
                    {"path": str(config_path), "backup": str(backup_path)}
                )
            else:
                config = {"servers": {}}

            # Merge config
            if "servers" not in config:
                config["servers"] = {}
            config["servers"]["VAST Admin MCP"] = vscode_config["servers"][
                "VAST Admin MCP"
            ]

            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

        INSTALL_STATE["clients_configured"].append("vscode")
        log_success("VSCode configured")
        log_warn("IMPORTANT: Restart VSCode completely for changes to take effect")
        log_warn("  1. Close all VSCode windows")
        log_warn("  2. Reopen VSCode")


# ============================================================================
# OLLAMA SPECIAL HANDLING
# ============================================================================


def configure_ollama_warning():
    """Show unskippable warning about Ollama requirements."""
    print_section("OLLAMA REQUIRES ADDITIONAL SETUP")

    warning = """
VAST Admin MCP with Ollama is more complex than Claude/VSCode.

Ollama does NOT support MCP natively. You need a BRIDGE APPLICATION.

REQUIRED STEPS:
1. Install a bridge app (Dive or mcphost)
2. Run an Ollama model with function-calling support
3. Configure the bridge to connect to VAST Admin MCP

THIS IS NOT A SIMPLE CONFIG CHANGE.

See: ~/vast-mcp/OLLAMA_SETUP.txt for detailed step-by-step guide

Recommended models with function calling:
  * llama3.2
  * qwen2.5-coder
  * mistral-small

Bridge options:
  * Dive (GUI) - Easy to use
  * mcphost (CLI) - For power users
    """

    print(warning)

    # Make this hard to skip - require explicit confirmation
    print("\nI understand this requires additional setup.")
    confirm = input("Type 'yes' to continue: ").strip().lower()

    if confirm != "yes":
        log_info("Skipping Ollama configuration")
        return

    # Create detailed setup guide
    if not DRY_RUN:
        create_ollama_setup_guide()
        INSTALL_STATE["clients_configured"].append("ollama")
        log_success("Created Ollama setup guide at ~/vast-mcp/OLLAMA_SETUP.txt")


def create_ollama_setup_guide():
    """Create detailed Ollama setup guide."""
    guide = """# VAST Admin MCP with Ollama - Setup Guide

## Important: Ollama Requires a Bridge Application

Ollama does NOT support MCP natively. You must use a bridge app to connect
VAST Admin MCP to Ollama.

---

## Option 1: Using Dive (Recommended for GUI Users)

Dive is a desktop app that makes this easy.

### Step 1: Install Dive
Visit: https://github.com/OpenAgentPlatform/Dive
Download and install the app for your OS.

### Step 2: Start Ollama Server
In Terminal:
  ollama serve

### Step 3: Configure Dive
1. Open Dive
2. Go to Settings
3. Set Base URL to: http://localhost:11434
4. In MCP tab, add your VAST Admin MCP server
5. Select your model (llama3.2, qwen2.5-coder, mistral-small)

---

## Option 2: Using mcphost (For Power Users)

mcphost is a CLI tool for connecting Ollama to MCP servers.

### Step 1: Install mcphost
  go install github.com/mark3labs/mcphost@latest

### Step 2: Create ~/.mcphost.json
  {
    "mcpServers": {
      "vast-admin": {
        "command": "/Users/your-username/vast-mcp/venv/bin/vast-admin-mcp",
        "args": ["mcp"]
      }
    }
  }

### Step 3: Run mcphost with Ollama
  ollama serve &
  mcphost --model ollama:llama3.2 --config ~/.mcphost.json

---

## Recommended Models

These models support function calling (required for MCP):
  * llama3.2 (Excellent for small tasks)
  * qwen2.5-coder (Highly reliable)
  * mistral-small (Good balance)

Install with:
  ollama pull llama3.2

---

## Troubleshooting

**Ollama won't start:**
  - Check if port 11434 is available: lsof -i :11434
  - Try different port: OLLAMA_HOST=127.0.0.1:11435 ollama serve

**Bridge can't connect to MCP:**
  - Verify Ollama is running: curl http://localhost:11434
  - Check model supports function calling
  - Review bridge logs for errors

**Model doesn't support tools:**
  - Not all models support function calling
  - Use recommended models above
  - Check model documentation

---

## Next Steps

1. Choose a bridge (Dive or mcphost)
2. Follow the steps above for your choice
3. Test the connection
4. Try using VAST Admin MCP commands in your Ollama model

For help: See ~/vast-mcp/install.log
"""

    OLLAMA_SETUP_FILE.write_text(guide)


# ============================================================================
# POST-INSTALLATION VERIFICATION & SUMMARY
# ============================================================================


def interactive_verification(venv_dir: Path):
    """
    Run interactive verification of installation.

    Args:
        venv_dir: Path to virtual environment
    """
    print_section("Installation Verification")

    vast_mcp_exe = venv_dir / "bin" / "vast-admin-mcp"

    if not DRY_RUN:
        log_info("Testing vast-admin-mcp...")
        try:
            result = subprocess.run(
                [str(vast_mcp_exe), "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                log_success("vast-admin-mcp is working")
            else:
                log_error("vast-admin-mcp failed", fatal=True)
        except Exception as e:
            log_error(f"Verification failed: {e}", fatal=True)

    print("\nVerification Summary:")
    print(f"  * Installation: {INSTALL_DIR}")
    print(f"  * Python: {INSTALL_STATE['python']}")
    print(
        f"  * Config: {CONFIG_DIR / 'config.json' if INSTALL_STATE['config_saved'] else 'Not configured'}"
    )
    print(
        f"  * Clients configured: {', '.join(INSTALL_STATE['clients_configured']) if INSTALL_STATE['clients_configured'] else 'None'}"
    )

    if INSTALL_STATE["clients_configured"]:
        print("\n" + "=" * 60)
        print("IMPORTANT: Restart Your Applications".center(60))
        print("=" * 60)
        print("\nYou MUST restart these apps for MCP to load:\n")
        for client in INSTALL_STATE["clients_configured"]:
            if client == "claude-desktop":
                print("  * Claude Desktop")
                print("    - Quit Claude (Cmd+Q)")
                print("    - Wait 2 seconds")
                print("    - Reopen Claude Desktop")
            elif client == "vscode":
                print("  * VSCode")
                print("    - Close all VSCode windows")
                print("    - Reopen VSCode")
            elif client == "ollama":
                print("  * Ollama")
                print("    - Follow guide in ~/vast-mcp/OLLAMA_SETUP.txt")


def create_next_steps_file():
    """Create NEXT_STEPS.txt for user."""
    next_steps = f"""VAST Admin MCP Installation Summary
===================================================

INSTALLATION COMPLETE!

INSTALLED COMPONENTS:
  * VAST Admin MCP v0.1.8
  * Python virtual environment
  * MCP server configuration
  * Installation log: {INSTALL_LOG_FILE}

LOCATION:
  {INSTALL_DIR}

CONFIGURATION:
  * Cluster config: {CONFIG_DIR / 'config.json' if INSTALL_STATE['config_saved'] else 'Not configured (can setup later)'}
  * Log file: {INSTALL_LOG_FILE}

CONFIGURED CLIENTS:
{chr(10).join(f'  * {client.upper()}' for client in INSTALL_STATE['clients_configured']) if INSTALL_STATE['clients_configured'] else '  (None)'}

IMPORTANT NEXT STEPS:

1. RESTART YOUR APPLICATIONS (if any clients were configured):
   * Claude Desktop: Cmd+Q, wait 2 sec, reopen
   * VSCode: Close all windows, reopen
   * Ollama: See ~/vast-mcp/OLLAMA_SETUP.txt

2. TEST THE INSTALLATION:
   source {INSTALL_DIR}/venv/bin/activate
   vast-admin-mcp --help

3. CLUSTER CONFIGURATION (if not done):
   vast-admin-mcp setup

HELP & TROUBLESHOOTING:
   * Installation log: {INSTALL_LOG_FILE}
   * Ollama setup: {OLLAMA_SETUP_FILE}
   * Revert installation: python3 install-vast-mcp.py --revert

SUPPORT:
   * Check logs for errors: cat {INSTALL_LOG_FILE}
   * Verify Python: {INSTALL_STATE['python']}
   * Test command: {INSTALL_DIR}/run-vast.sh --help

===================================================
Installation completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    if not DRY_RUN:
        NEXT_STEPS_FILE.write_text(next_steps)
        INSTALL_STATE["files_created"].append(str(NEXT_STEPS_FILE))


def save_install_state():
    """Save installation state to JSON log for revert capability."""
    if not DRY_RUN:
        with open(INSTALL_STATE_FILE, "w") as f:
            json.dump(INSTALL_STATE, f, indent=2)


# ============================================================================
# REVERT FUNCTIONALITY
# ============================================================================


def run_revert():
    """Revert previous installation."""
    global logger

    if not INSTALL_DIR.exists():
        print("No installation found to revert")
        sys.exit(0)

    state_file = INSTALL_STATE_FILE
    if not state_file.exists():
        log_error("No installation state found. Cannot revert.", fatal=True)

    print_header("Revert VAST Admin MCP Installation")

    # Load state
    with open(state_file) as f:
        state = json.load(f)

    print(f"\nFound installation from: {state.get('timestamp', 'unknown')}")
    print(f"OS: {state.get('os')} {state.get('os_version')}")
    print(f"\nThis will:")
    print(f"  * Remove {INSTALL_DIR}")
    print(f"  * Remove {CONFIG_DIR}")
    print(f"  * Restore backed-up config files")
    print(f"  * Remove MCP entries from client configs")

    response = input("\nContinue with revert? (Y/N): ").strip().upper()
    if response != "Y":
        log_info("Revert cancelled")
        sys.exit(0)

    # Restore backed-up files
    if state.get("files_backed_up"):
        log_info("Restoring backed-up files...")
        for backup_entry in state["files_backed_up"]:
            original_path = Path(backup_entry["path"])
            backup_path = Path(backup_entry["backup"])

            if backup_path.exists():
                shutil.copy(backup_path, original_path)
                log_success(f"Restored {original_path}")

    # Remove directories
    log_info("Removing installation directories...")
    if INSTALL_DIR.exists():
        shutil.rmtree(INSTALL_DIR)
        log_success(f"Removed {INSTALL_DIR}")

    if CONFIG_DIR.exists():
        shutil.rmtree(CONFIG_DIR)
        log_success(f"Removed {CONFIG_DIR}")

    print_header("Revert Complete!")
    log_success("VAST Admin MCP has been uninstalled")


# ============================================================================
# MAIN INSTALLATION FLOW
# ============================================================================


def run_installation():
    """Run installation process."""
    print_header("VAST Admin MCP Installer")

    # Check for sudo
    if os.geteuid() == 0:
        log_error(
            "Don't run with sudo! This can break permissions.\n"
            "Run without sudo: python3 install-vast-mcp.py",
            fatal=True,
        )

    # Detect OS
    os_type, os_version = detect_os()

    # Validate prerequisites
    print_section("Validating Prerequisites")

    install_jq(os_type)

    if not check_disk_space():
        log_error("Insufficient disk space", fatal=True)

    if not check_internet():
        log_warn("No internet connection detected. Package installation will fail.")
        response = input("Continue anyway? (Y/N): ").strip().upper()
        if response != "Y":
            log_error("Installation cancelled", fatal=True)

    # Select Python
    print_section("Python Version Selection")
    python_exe = select_python()

    # Setup directories
    install_dir, venv_dir = setup_directories(python_exe)

    # Create wrapper script
    create_wrapper_script(python_exe)

    # Install VAST Admin MCP
    install_vast_admin_mcp(venv_dir)

    # Validate installation
    validate_installation(venv_dir)

    # Configure credentials
    configure_credentials()

    # Detect clients
    clients = detect_installed_clients(os_type)
    show_detected_clients(clients)

    # Ask which clients to configure
    clients_to_configure = ask_which_clients_to_configure(clients)

    # Configure selected clients
    for client in clients_to_configure:
        if client == "claude-desktop":
            configure_claude_desktop(venv_dir, os_type)
        elif client == "vscode":
            configure_vscode(venv_dir)
        elif client == "ollama":
            configure_ollama_warning()

    # Final verification
    interactive_verification(venv_dir)

    # Create next steps file
    create_next_steps_file()

    # Save state for revert capability
    save_install_state()

    print_header("Installation Complete!")
    log_success(f"VAST Admin MCP installed to {INSTALL_DIR}")
    print(f"\nNext: cat {NEXT_STEPS_FILE}")


# ============================================================================
# ENTRY POINT
# ============================================================================


def main():
    """Main entry point."""
    global logger, DRY_RUN

    # Setup logging
    if not INSTALL_DIR.exists():
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)

    logger = setup_logging()

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="VAST Admin MCP Installation Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 install-vast-mcp.py              # Install (default)
  python3 install-vast-mcp.py --dry-run    # Preview without making changes
  python3 install-vast-mcp.py --revert     # Undo previous installation
        """,
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without executing"
    )
    parser.add_argument(
        "--revert", action="store_true", help="Undo previous installation"
    )
    args = parser.parse_args()

    DRY_RUN = args.dry_run

    if args.dry_run:
        print_header("DRY RUN MODE - No changes will be made")
    elif args.revert:
        run_revert()
        return

    run_installation()


if __name__ == "__main__":
    main()
