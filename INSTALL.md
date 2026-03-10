# Installation Guide - Prediction Analyzer

This guide will help you set up and run the Prediction Analyzer tool.

## Prerequisites

- **Python 3.8 or higher** - Download from [python.org](https://python.org)
- **pip** - Usually comes with Python

### Check Your Python Version

```bash
python --version
```

If this shows Python 3.8+, you're ready to proceed!

## Installation Methods

Choose ONE of the following methods:

### Method 1: Quick Install (Recommended for Windows)

**Windows users**: Simply double-click `install.bat` or run:
```cmd
install.bat
```

This will automatically install all required dependencies.

### Method 2: Manual Installation with pip

1. Open a terminal/command prompt in the project directory
2. Run the following command:

```bash
pip install -r requirements.txt
```

### Method 3: Install as a Package (For Developers)

If you want to install the package in development mode:

```bash
pip install -e .
```

This allows you to run `prediction-analyzer` from anywhere on your system.

### Method 4: Install with Extras

```bash
# Install with FastAPI web app support
pip install -e ".[api]"

# Install with MCP server support
pip install -e ".[mcp]"

# Install with development tools
pip install -e ".[dev]"

# Install everything
pip install -e ".[api,mcp,dev]"
```

## Running the Analyzer

After installation, run the analyzer with:

```bash
python run.py
```

The `run.py` script will:
1. Check if all dependencies are installed
2. Provide helpful error messages if anything is missing
3. Launch the Prediction Analyzer interface

## Provider-Specific Setup

### Limitless Exchange
No extra setup needed beyond the base install. Get your API key at [limitless.exchange](https://limitless.exchange) (Profile > API Keys).

### Polymarket
No extra setup needed. You only need your Ethereum wallet address (starts with `0x`).

### Kalshi
Requires the `cryptography` package (included in `requirements.txt`):
```bash
pip install cryptography>=41.0.0
```
Generate an RSA key pair at [kalshi.com](https://kalshi.com) (Settings > API Keys).

### Manifold Markets
No extra setup needed. Get your API key at [manifold.markets](https://manifold.markets) (Profile > API Key).

### Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

Available environment variables:
```
LIMITLESS_API_KEY=lmts_your_key_here
POLYMARKET_WALLET=0xYourWalletAddress
KALSHI_API_KEY_ID=your_key_id
KALSHI_PRIVATE_KEY_PATH=kalshi_private_key.pem
MANIFOLD_API_KEY=manifold_your_key_here
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'pandas'" (or other packages)

This means dependencies are not installed. Please run one of the installation methods above.

### "ModuleNotFoundError: No module named 'cryptography'"

The `cryptography` package is needed for Kalshi API integration:
```bash
pip install cryptography>=41.0.0
```

On some systems you may need build tools:
```bash
# Ubuntu/Debian
sudo apt-get install build-essential libssl-dev libffi-dev python3-dev

# Fedora
sudo dnf install gcc openssl-devel libffi-devel python3-devel
```

### "ModuleNotFoundError: No module named 'setuptools'"

Your Python environment is missing setuptools. Install it with:

```bash
pip install setuptools
```

Then run the installation again.

### "attempted relative import with no known parent package"

Don't run `__main__.py` directly. Always use `run.py` instead:

```bash
python run.py
```

### pip is not recognized

If `pip` command is not found, try:

```bash
python -m pip install -r requirements.txt
```

### Permission Errors (Linux/Mac)

If you get permission errors, you might need to use:

```bash
pip install --user -r requirements.txt
```

Or use a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### GUI Not Launching (Linux)

If the GUI doesn't launch on Linux, you may need to install tkinter:
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch Linux
sudo pacman -S tk
```

## Virtual Environment (Recommended for Advanced Users)

Using a virtual environment keeps dependencies isolated:

### Windows:
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

### Linux/Mac:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

## What Gets Installed

The following packages will be installed:

| Package | Purpose |
|---------|---------|
| **pandas** | Data manipulation and analysis |
| **numpy** | Numerical computing |
| **matplotlib** | Static chart visualization |
| **plotly** | Interactive visualizations |
| **openpyxl** | Excel file support |
| **requests** | HTTP library for API communication |
| **cryptography** | RSA-PSS signing for Kalshi API |
| **fastapi** | Web API framework |
| **sqlalchemy** | Database ORM |
| **PyJWT** | JWT authentication |
| **pydantic** | Data validation |

## Getting Help

If you continue to have issues:

1. Check that Python 3.8+ is installed: `python --version`
2. Make sure you're in the correct directory (where `run.py` is located)
3. Try creating a fresh virtual environment
4. Check the error messages carefully -- they usually indicate what's wrong

## Quick Start After Installation

Once installed, simply run:

```bash
python run.py
```

The tool will guide you through analyzing your prediction market trades!

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).
