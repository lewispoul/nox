#!/usr/bin/env python3
"""
Setup script for Nox API Python SDK
v8.0.0 Developer Experience Enhancement
"""

import os

from setuptools import find_packages, setup


# Read README for long description
def read_readme():
    try:
        with open("README.md", "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return "Advanced Python SDK for the Nox API platform with AI capabilities"


# Read requirements
def read_requirements():
    try:
        with open("requirements.txt", "r", encoding="utf-8") as fh:
            return [
                line.strip() for line in fh if line.strip() and not line.startswith("#")
            ]
    except FileNotFoundError:
        return [
            "aiohttp>=3.8.0",
            "requests>=2.28.0",
            "pyjwt>=2.6.0",
            "cryptography>=3.4.8",
            "bcrypt>=4.0.0",
            "python-dateutil>=2.8.2",
        ]


# Get version
def get_version():
    version_file = os.path.join(os.path.dirname(__file__), "nox_sdk", "__init__.py")
    with open(version_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip('"')
    return "8.0.0"


setup(
    name="nox-sdk",
    version=get_version(),
    author="Nox Development Team",
    author_email="dev@nox.example.com",
    description="Advanced Python SDK for the Nox API platform with AI capabilities",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/nox-platform/python-sdk",
    project_urls={
        "Documentation": "https://docs.nox.example.com/python-sdk",
        "Source": "https://github.com/nox-platform/python-sdk",
        "Tracker": "https://github.com/nox-platform/python-sdk/issues",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: System :: Systems Administration",
        "Topic :: Security",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "isort>=5.12.0",
            "pre-commit>=3.0.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.2.0",
            "sphinx-autodoc-typehints>=1.19.0",
        ],
        "biometric": [
            "pillow>=9.0.0",
            "numpy>=1.21.0",
            "opencv-python>=4.6.0",
        ],
        "performance": [
            "psutil>=5.9.0",
            "prometheus-client>=0.16.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "nox-cli=nox_sdk.cli:main",
        ],
    },
    include_package_data=True,
    keywords=[
        "nox",
        "api",
        "sdk",
        "automation",
        "scripting",
        "ai",
        "security",
        "biometric",
        "authentication",
        "policy",
        "cloud",
        "distributed",
    ],
    zip_safe=False,
)
