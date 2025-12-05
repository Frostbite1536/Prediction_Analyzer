#!/usr/bin/env python3
"""
Standalone runner for Prediction Analyzer
This script allows you to run the package without installing it
"""
import sys
from pathlib import Path

# Add the package directory to Python path
package_dir = Path(__file__).parent
sys.path.insert(0, str(package_dir))

# Import and run the main function
from prediction_analyzer.__main__ import main

if __name__ == "__main__":
    main()
