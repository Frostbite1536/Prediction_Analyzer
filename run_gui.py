#!/usr/bin/env python3
"""
Launcher script for Prediction Analyzer GUI
Checks dependencies and launches the GUI application
"""
import sys
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
        'eth_account',
        'tkinter'
    ]

    missing_packages = []
    for package in required_packages:
        # Special handling for tkinter
        if package == 'tkinter':
            try:
                __import__(package)
            except ImportError:
                # tkinter might be named differently
                try:
                    import tkinter
                except ImportError:
                    missing_packages.append(package)
        else:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)

    if missing_packages:
        print("ERROR: Missing required dependencies!")
        print("\nThe following packages are not installed:")
        for pkg in missing_packages:
            if pkg == 'tkinter':
                print(f"  - {pkg} (usually comes with Python, may need python3-tk on Linux)")
            else:
                print(f"  - {pkg}")
        print("\nTo install dependencies:")
        print("\n  Option 1 (Recommended):")
        print("    pip install -r requirements.txt")
        print("\n  Option 2 (Windows):")
        print("    install.bat")

        if 'tkinter' in missing_packages:
            print("\nFor tkinter on Linux/Ubuntu:")
            print("    sudo apt-get install python3-tk")
            print("\nFor tkinter on macOS:")
            print("    (tkinter should be included with Python)")

        print("\nAfter installation, run this script again.")
        sys.exit(1)

# Add the package directory to Python path
package_dir = Path(__file__).parent
sys.path.insert(0, str(package_dir))

if __name__ == "__main__":
    # Check dependencies first
    check_dependencies()

    # Import and run the GUI
    try:
        from gui import main
        main()
    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nIf you continue to have issues, please check:")
        print("  1. Python version is 3.8 or higher")
        print("  2. All dependencies are installed")
        print("  3. tkinter is available (python3-tk on Linux)")
        sys.exit(1)
