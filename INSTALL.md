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

## Running the Analyzer

After installation, run the analyzer with:

```bash
python run.py
```

The `run.py` script will:
1. Check if all dependencies are installed
2. Provide helpful error messages if anything is missing
3. Launch the Prediction Analyzer interface

## Troubleshooting

### "ModuleNotFoundError: No module named 'pandas'" (or other packages)

This means dependencies are not installed. Please run one of the installation methods above.

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

- **pandas** - Data manipulation and analysis
- **numpy** - Numerical computing
- **matplotlib** - Data visualization
- **plotly** - Interactive visualizations
- **openpyxl** - Excel file support
- **requests** - HTTP library
- **eth-account** - Ethereum account utilities

## Getting Help

If you continue to have issues:

1. Check that Python 3.8+ is installed: `python --version`
2. Make sure you're in the correct directory (where `run.py` is located)
3. Try creating a fresh virtual environment
4. Check the error messages carefully - they usually indicate what's wrong

## Quick Start After Installation

Once installed, simply run:

```bash
python run.py
```

The tool will guide you through analyzing your prediction market trades!
