# VAST Admin MCP Installation Script

A robust, cross-platform Python installer for VAST Admin MCP that handles all complexity transparently, with comprehensive error handling, automatic recovery, and detailed logging.

## Overview

This repository contains a production-ready installation script (`install-vast-mcp.py`) designed to deploy VAST Admin MCP to customer systems with minimal user intervention. The script is self-contained, portable, and requires no system-level modifications.

**Target Audience:** Non-technical users who prefer straightforward installation with clear progress indicators and helpful guidance.

---

## Features

### 🎯 Smart Installation

- **Automatic Detection:** Detects OS, Python version, and installed AI tools
- **Intelligent Defaults:** Recommends newest Python version, suggests default options
- **Prerequisite Handling:** Auto-installs missing dependencies (jq) on macOS and Linux
- **Validation:** Tests installation at each step, provides clear feedback
- **Error Recovery:** Automatically fixes common issues (old pip, missing packages, etc.)

### 🛡️ Safety & Reversibility

- **Non-Destructive:** Only modifies `~/vast-mcp/` and `~/.vast-admin-mcp/` directories
- **Backup Protection:** Automatically backs up existing configuration files before modifying
- **Full Revert Capability:** Complete undo via `--revert` mode restores system to pre-installation state
- **Dry-Run Mode:** Preview all changes before execution with `--dry-run`
- **Detailed Logging:** Comprehensive logs for troubleshooting stored in `~/vast-mcp/install.log`

### 🤝 Client Support

- **Claude Desktop:** Auto-configures with MCP server registration
- **VSCode:** Automatic configuration for MCP extension
- **ChatGPT Desktop:** Detection and guidance
- **Ollama:** Special handling with mandatory setup guide for bridge configuration

### 📋 User Guidance

- **Progress Indicators:** Clear emoji-based status (✓, ✗, ⚠, ℹ)
- **Restart Reminders:** Bold warnings when applications must be restarted
- **Setup Guides:** Auto-generated NEXT_STEPS.txt and OLLAMA_SETUP.txt after installation
- **Helpful Prompts:** Clear confirmations and explanations at decision points

### 🔧 Cross-Platform Support

- **macOS:** 14+ (Sonoma, Sequoia, Tahoe, and later)
- **Linux:** AlmaLinux, Rocky Linux, CentOS, RHEL, Fedora (EL9 and later)
- **Python:** 3.10+ (auto-detected and selected)

---

## Quick Start

### Installation

```bash
python3 install-vast-mcp.py
```

The installer will:
1. Detect your operating system and Python version
2. Check and install prerequisites (jq)
3. Create isolated installation in `~/vast-mcp/`
4. Install VAST Admin MCP package
5. Optionally configure cluster credentials
6. Auto-detect and configure your AI tools
7. Provide next steps and restart instructions

### Preview Installation (Safe to Run First)

```bash
python3 install-vast-mcp.py --dry-run
```

Shows exactly what will be installed and configured without making any changes.

### Undo Installation

```bash
python3 install-vast-mcp.py --revert
```

Completely removes the installation and restores backed-up configuration files.

### Get Help

```bash
python3 install-vast-mcp.py --help
```

Shows usage information and examples.

---

## How It Works

### Automatic Detection

The script automatically:
- Detects macOS (with version check: 14+) or Linux distribution (AlmaLinux, Rocky, CentOS, RHEL, Fedora)
- Finds all Python 3.10+ installations and shows the user a ranked list
- Scans for installed AI clients (Claude Desktop, VSCode, ChatGPT, Ollama)
- Checks available disk space (>1GB required)
- Verifies internet connectivity

### Transparent Error Handling

**Auto-Fixed Issues:**
- Outdated pip (automatically upgraded)
- Missing jq (auto-installed via Homebrew on macOS or dnf/yum on Linux)
- Python version detection (finds all versions, lets user choose)
- Existing installations (asks if user wants to reinstall)

**Recoverable Issues:**
- Credential validation failures (warns but saves config anyway)
- Missing keyring (stores credentials plaintext with security warning)
- Client detection failures (continues installation, skips that client)

**Show-Stopping Issues:**
- Python < 3.10 (provides clear upgrade instructions)
- macOS < 14 (prompts user, allows override with understanding)
- No internet connection (prevents package download)
- Permission denied on home directory (explains root cause)

### Configuration Management

- **Cluster Credentials:** Optional setup saves to `~/.vast-admin-mcp/config.json` (0o600 permissions)
- **Client Configs:** Automatically registers MCP server in:
  - Claude Desktop: `~/Library/Application Support/Claude/claude_desktop_config.json`
  - VSCode: `~/.vscode/mcp.json` and `~/Library/Application Support/Code/User/mcp.json`
- **State Tracking:** Saves installation manifest to `~/vast-mcp/INSTALL_LOG.json` for reliable revert

### Verification & Guidance

After installation:
1. Tests that vast-admin-mcp command works
2. Tests cluster connection (if credentials provided)
3. Shows summary with configured clients
4. Provides bold reminders to restart applications
5. Creates detailed NEXT_STEPS.txt guide
6. Creates OLLAMA_SETUP.txt if Ollama detected (with bridge setup instructions)

---

## Important Caveats

### System Requirements

- **Python:** 3.10+ is required (not 3.9 or earlier)
- **Disk Space:** Minimum 1GB free in home directory
- **Internet:** Required for initial setup (all subsequent operations work offline)
- **macOS:** Version 14+ required (older versions will show a warning)
- **Permissions:** Must be able to write to home directory (do NOT use sudo)

### Application Restart Required

After installation, you **MUST** completely restart your AI applications:
- **Claude Desktop:** Close completely (Cmd+Q), wait 2 seconds, reopen
- **VSCode:** Close all windows, reopen
- Failure to restart means the MCP server won't be recognized

### Ollama Requires Additional Setup

Ollama does NOT natively support MCP. If you use Ollama:
1. A mandatory warning will appear during installation (must type "yes" to acknowledge)
2. You will need to install a bridge application (Dive or mcphost)
3. You will need to run a compatible model with function-calling support (llama3.2, qwen2.5-coder, mistral-small)
4. Detailed setup guide provided in `~/vast-mcp/OLLAMA_SETUP.txt`

### Python Version Multiplicity

If you have multiple Python versions installed:
- Script finds ALL versions and shows them ranked by preference
- User explicitly selects which Python to use
- A wrapper script is created that uses the selected version (avoiding PATH issues)

### Configuration File Security

Cluster credentials saved to `~/.vast-admin-mcp/config.json` use restrictive file permissions (0o600).
- **Recommendation:** Change credentials immediately if they appear in logs
- **Alternative:** Use keyring for secure credential storage (automatic if available)

### No System Modifications

The installer:
- ✅ Only modifies `~/vast-mcp/` and `~/.vast-admin-mcp/` directories
- ✅ Creates isolated Python virtual environment (doesn't affect system Python)
- ✅ Does NOT require sudo or administrative access
- ✅ Does NOT modify system libraries or global Python packages
- ✅ Does NOT create system-wide configuration files

### Revert Limitations

The `--revert` mode:
- Removes installation directories
- Restores backed-up client configuration files
- Does NOT remove VAST Admin MCP if it was previously installed system-wide
- Does NOT uninstall cluster credentials from keyring (if stored there)

---

## Installation Lifecycle

### First Time: Discovery

```bash
python3 install-vast-mcp.py --dry-run
```
Preview what will happen. Safe, non-destructive.

### First Time: Installation

```bash
python3 install-vast-mcp.py
```
Performs full installation with user prompts for configuration choices.

### Troubleshooting

Check the installation log:
```bash
cat ~/vast-mcp/install.log
```

Review the next steps guide:
```bash
cat ~/vast-mcp/NEXT_STEPS.txt
```

For Ollama users:
```bash
cat ~/vast-mcp/OLLAMA_SETUP.txt
```

### Re-Installation

Running the installer again:
```bash
python3 install-vast-mcp.py
```
Will detect existing installation and ask if you want to reinstall (backs up existing state first).

### Cleanup

Remove everything:
```bash
python3 install-vast-mcp.py --revert
```
Completely undoes the installation and restores any backed-up configurations.

---

## Technical Architecture

### Single-File Design

- **Portability:** Single Python script with no external dependencies (uses only Python standard library)
- **Simplicity:** No installation required, download and run immediately
- **Transparency:** All code in one place, easy to review

### Implementation Details

- **36 Functions:** Organized by concern (logging, detection, installation, configuration, etc.)
- **Type Hints:** Full type annotations on all functions
- **Error Handling:** Comprehensive try/except blocks with informative messages
- **State Management:** JSON-based installation manifest for reliable revert
- **Logging:** Dual output to console (emoji indicators) and file (detailed logs)

### No Hardcoded Paths

All paths use `Path.home()` for dynamic resolution:
- Works for any user
- No user-specific paths embedded
- Fully portable across systems

---

## Troubleshooting

### Python Not Found

```
✗ No Python 3.10+ installation found
```

**Solution:** Install Python 3.10+
- macOS: `brew install python@3.12`
- Linux: `sudo dnf install python3.11`

### jq Installation Failed

```
✗ Failed to install jq
```

**Solution:** Install manually
- macOS: `brew install jq`
- Linux: `sudo dnf install jq`

### No Internet Connection

```
✗ No internet connection detected
```

**Solution:** Ensure you can access the internet, then run again.

### macOS Version Too Old

```
⚠ macOS 13 is older than recommended
```

**Solution:** Upgrade to macOS 14+, or type "Y" to continue anyway at your own risk.

### Permission Denied

```
✗ Permission denied on home directory
```

**Solution:**
- Do NOT use `sudo` (it breaks permissions)
- Run without sudo: `python3 install-vast-mcp.py`
- Ensure your user owns the home directory

### Installation Takes Too Long

**Normal:** 3-10 minutes depending on internet speed and system performance.

If stuck:
- Cancel (Ctrl+C) and try again
- Use `--dry-run` first to check for issues
- Check log: `cat ~/vast-mcp/install.log`

---

## Distribution

This installer is designed for distribution to customers:

1. **Email:** Attach `install-vast-mcp.py` to email
2. **Web:** Host on website for download
3. **Documentation:** Include `INSTALLER_README.md` or paste instructions
4. **Guidance:** Recommend starting with `python3 install-vast-mcp.py --help`

No additional setup or configuration needed by recipients.

---

## Support

For issues or questions:

1. Check the installation log: `~/vast-mcp/install.log`
2. Review the next steps guide: `~/vast-mcp/NEXT_STEPS.txt`
3. Try dry-run mode: `python3 install-vast-mcp.py --dry-run`
4. Try revert and reinstall: `python3 install-vast-mcp.py --revert` then `python3 install-vast-mcp.py`

---

## License

[MIT]

## Author

[Sergio Soto/VAST Data]

## Last Updated

February 2026
