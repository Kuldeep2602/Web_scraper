#!/bin/bash
# Setup script for Linux/Mac

set -e

echo "================================================"
echo "   Apache Jira Scraper - Setup"
echo "================================================"
echo ""

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "[1/5] Python found"
python3 --version
echo ""

# Create virtual environment
echo "[2/5] Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists"
else
    python3 -m venv venv
    echo "Virtual environment created successfully"
fi
echo ""

# Activate virtual environment
echo "[3/5] Activating virtual environment..."
source venv/bin/activate
echo "Virtual environment activated"
echo ""

# Install dependencies
echo "[4/5] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "Dependencies installed successfully"
echo ""

# Setup configuration
echo "[5/5] Setting up configuration..."
if [ -f ".env" ]; then
    echo "Configuration file .env already exists"
else
    cp .env.example .env
    echo "Configuration file .env created from template"
    echo "Please edit .env to customize settings"
fi
echo ""

# Create directories
mkdir -p output
mkdir -p state

echo "================================================"
echo "   Setup Complete!"
echo "================================================"
echo ""
echo "To run the scraper:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run: python run.py"
echo ""
echo "For more information, see README.md"
echo ""
