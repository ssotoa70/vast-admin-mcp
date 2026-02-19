# VAST Admin MCP Installer

## Quick Start

```bash
python3 install-vast-mcp.py
```

That's it! The script handles everything.

---

## What This Does

This script installs VAST Admin MCP to `~/vast-mcp/` and configures it to work with your AI tools.

**Supported Systems:**
- macOS 14+ (Sonoma, Sequoia, Tahoe)
- AlmaLinux, Rocky Linux, CentOS, RHEL, Fedora

**Supported AI Clients:**
- Claude Desktop
- VSCode
- ChatGPT (desktop)
- Ollama (with additional setup)

---

## Installation Modes

### Default Install
```bash
python3 install-vast-mcp.py
```
Performs full installation with prompts for configuration.

### Preview Mode (Dry-Run)
```bash
python3 install-vast-mcp.py --dry-run
```
Shows what WILL happen without making any changes. Safe to run first.

### Undo Installation
```bash
python3 install-vast-mcp.py --revert
```
Removes the installation and restores any backed-up configuration files.

### Help
```bash
python3 install-vast-mcp.py --help
```
Shows available options.

---

## What Gets Installed

✓ VAST Admin MCP package in `~/vast-mcp/`
✓ Python virtual environment (isolated, won't affect your system)
✓ Configuration files for cluster access (optional)
✓ MCP server configuration for your AI tools
✓ Automated setup guides

---

## Important: After Installation

### Restart Your AI Applications

You **MUST** restart these applications completely for them to recognize the MCP server:

**Claude Desktop:**
- Quit Claude Desktop (Cmd+Q on Mac)
- Wait 2 seconds
- Reopen Claude Desktop

**VSCode:**
- Close all VSCode windows
- Reopen VSCode

**ChatGPT or Ollama:**
- Follow the setup guide that appears after installation

### Next Steps

After the installer finishes, check:
```bash
cat ~/vast-mcp/NEXT_STEPS.txt
```

This file has detailed instructions for using VAST Admin MCP with your tools.

---

## Requirements

**Before You Start:**
- Python 3.10 or higher
- For macOS: Homebrew (for jq installation)
- Internet connection (to download packages, first time only)

The script will check these automatically and help you fix any issues.

---

## Troubleshooting

If something goes wrong, the installer creates a detailed log:
```bash
cat ~/vast-mcp/install.log
```

This log contains information about what happened and any errors encountered.

### Common Issues

**"Python 3.10+ not found"**
- Install Python 3.10 or higher
- On Mac: `brew install python@3.12`
- On Linux: `sudo dnf install python3.11`

**"jq not found"**
- On Mac: `brew install jq`
- On Linux: `sudo dnf install jq`

**"No internet connection"**
- Check your internet
- Then run the installer again

**"Permission denied"**
- Make sure your home directory is writable
- Don't run with `sudo` - run without it

---

## Cluster Configuration

The installer can optionally save your VAST cluster credentials for easier access.

When prompted:
- Enter your cluster address (IP or hostname)
- Enter your username
- Enter your password

These are stored securely in `~/.vast-admin-mcp/config.json` with restricted permissions.

If you skip this step, you can configure it later:
```bash
source ~/vast-mcp/venv/bin/activate
vast-admin-mcp setup
```

---

## Uninstalling

To remove VAST Admin MCP:
```bash
python3 install-vast-mcp.py --revert
```

This will:
- Remove `~/vast-mcp/` directory
- Remove `~/.vast-admin-mcp/` directory
- Restore backed-up configuration files
- Remove MCP entries from your AI tool configs

---

## Support

For help or issues:

1. Check the installation log: `cat ~/vast-mcp/install.log`
2. Read the next steps guide: `cat ~/vast-mcp/NEXT_STEPS.txt`
3. For Ollama users: `cat ~/vast-mcp/OLLAMA_SETUP.txt`

---

## Technical Details

This installer is a **single, self-contained Python script**. It requires:
- Python 3.10+
- No external dependencies (uses only Python standard library)
- ~1MB disk space minimum
- ~5-10 minutes to complete (depends on internet speed)

**What it does NOT do:**
- Modify your system files
- Install anything globally (all in `~/vast-mcp/`)
- Require administrative access (no `sudo` needed)
- Pollute your Python environment (uses isolated virtual environment)

---

## Getting Help

If the installer gets stuck or doesn't work:

1. **Cancel and try again**: Press Ctrl+C to stop, then run again
2. **Check your system**: Run `python3 --version` to ensure Python 3.10+
3. **Check connectivity**: Ensure you can access the internet
4. **Review logs**: See `~/vast-mcp/install.log` for details
5. **Use dry-run first**: Test with `python3 install-vast-mcp.py --dry-run`

---

**Ready?** Run `python3 install-vast-mcp.py` to begin!
