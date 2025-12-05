#!/usr/bin/env python3
"""
Standalone runner for Prediction Analyzer
This script allows you to run the package without installing it
"""
import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'pandas',
        'numpy',
        'matplotlib',
        'plotly',
        'openpyxl',
        'requests',
        'eth_account'
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print("ERROR: Missing required dependencies!")
        print("\nThe following packages are not installed:")
        for pkg in missing_packages:
            print(f"  - {pkg}")
        print("\nTo install all required dependencies, run ONE of the following commands:")
        print("\n  Option 1 (Recommended):")
        print("    pip install -r requirements.txt")
        print("\n  Option 2 (Install as package):")
        print("    pip install -e .")
        print("\n  Option 3 (Windows batch file):")
        print("    install.bat")
        print("\nAfter installation, run this script again.")
        sys.exit(1)

# Add the package directory to Python path
package_dir = Path(__file__).parent
sys.path.insert(0, str(package_dir))

if __name__ == "__main__":
    # Check dependencies first
    check_dependencies()

    # Import and run the main function
    try:
        from prediction_analyzer.__main__ import main
        main()
    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nIf you continue to have issues, please check:")
        print("  1. Python version is 3.8 or higher")
        print("  2. All dependencies are installed (see above)")
        print("  3. You're running from the correct directory")
        sys.exit(1)
