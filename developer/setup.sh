#!/bin/bash
# Developer environment setup script
#
# Creates a virtual environment and installs all dependencies
# (both core student packages and dev-only tools).
#
# Usage:
#   bash developer/setup.sh
#
# On Windows (native command prompt), use: developer\setup.bat

set -e  # Exit on error

echo "================================================"
echo "Getting Started with JABS - Developer Environment Setup"
echo "================================================"
echo

# Detect platform
OS_TYPE=$(uname -s)
if [[ "$OS_TYPE" == "MINGW64_NT"* ]] || [[ "$OS_TYPE" == "MSYS_NT"* ]]; then
    echo "⚠️  Detected Windows environment (running bash from Git Bash/MSYS)"
    echo "For better compatibility, please use: developer\\setup.bat"
    echo "Attempting to continue with bash..."
    USE_WINDOWS_PATHS=true
    ACTIVATE_CMD=""
else
    USE_WINDOWS_PATHS=false
fi

echo

# Check if .venv already exists
if [ -d ".venv" ]; then
    echo "⚠️  Virtual environment already exists at ./.venv"
    read -p "Do you want to recreate it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing venv..."
        rm -rf .venv
    else
        echo "Using existing venv. Skipping creation."
        SKIP_CREATION=true
    fi
fi

# Create virtual environment
if [ "$SKIP_CREATION" != "true" ]; then
    echo "Creating virtual environment..."
    python3 -m .venv @@
    echo "✓ Virtual environment created"
    echo
fi

# Activate virtual environment
echo "Activating virtual environment..."
if [ "$USE_WINDOWS_PATHS" == "true" ]; then
    # For Git Bash on Windows, use the Windows-style activate script
    source .venv/Scripts/activate
else
    # For Unix/Linux/macOS
    source .venv/bin/activate
fi
echo "✓ Virtual environment activated"
echo

# Upgrade pip, setuptools, wheel
echo "Upgrading pip, setuptools, and wheel..."
# On Windows Git Bash, pip upgrade can fail due to file locking; continue anyway
pip install --upgrade pip setuptools wheel > /dev/null 2>&1 || true
echo "✓ Package managers upgraded"
echo

# Install core dependencies
echo "Installing core dependencies (requirements.txt)..."
pip install --disable-pip-version-check -r requirements.txt > /dev/null
echo "✓ Core dependencies installed"
echo

# Install dev dependencies
echo "Installing development dependencies (requirements-dev.txt)..."
pip install --disable-pip-version-check -r requirements-dev.txt > /dev/null
echo "✓ Dev dependencies installed"
echo

# Run environment verification
echo "Verifying environment..."
python student_scripts/verify_environment.py
echo

# Install pre-commit hooks (optional)
echo "Setting up pre-commit hooks..."
pre-commit install > /dev/null 2>&1 || echo "⚠️  Pre-commit hooks setup skipped (optional)"
echo "✓ Pre-commit configuration ready"
echo

# Register Jupyter kernel
echo "Registering .venv as Jupyter kernel..."
python -m ipykernel install --user --name getting-started-with-jabs --display-name "Python (getting-started-with-jabs)" > /dev/null 2>&1
echo "✓ Jupyter kernel registered (getting-started-with-jabs)"
echo

echo "================================================"
echo "✅ Setup Complete!"
echo "================================================"
echo
echo "Next steps:"
echo "  1. Activate .venv (if not already active):"
echo "     source .venv/bin/activate"
echo
echo "  2. Start working on notebooks:"
echo "     jupyter notebook student_notebooks/"
echo
