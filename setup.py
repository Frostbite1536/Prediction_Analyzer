# setup.py
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="prediction-analyzer",
    version="1.0.0",
    author="Your Name",
    author_email="you@example.com",
    description="A complete modular analysis tool for prediction market traders",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/prediction_analyzer",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "pandas>=1.5.0",
        "numpy>=1.23.0",
        "matplotlib>=3.7.0",
        "plotly>=5.20.0",
        "openpyxl>=3.1.0",
        "requests>=2.28.0",
        "eth-account>=0.8.0"
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0"
        ],
    },
    entry_points={
        "console_scripts": [
            "prediction-analyzer=prediction_analyzer.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
)
