#!/bin/bash

# AppLab-V3 - Build Windows Executable
# Creates a standalone .exe file for Windows

echo "🚀 Building AppLab-V3 Windows Executable..."
echo

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.8+"
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

# Install PyInstaller
echo "📦 Installing PyInstaller..."
$PYTHON_CMD -m pip install pyinstaller

# Create executable
echo "🏗️ Creating Windows executable..."
echo "This may take several minutes..."

# Build with PyInstaller
$PYTHON_CMD -m pyinstaller \
    --onefile \
    --windowed \
    --name AppLab-V3 \
    --add-data "backend/templates:templates" \
    --add-data "backend/static:static" \
    --hidden-import flask_sqlalchemy \
    --hidden-import pandas \
    --hidden-import openpyxl \
    --hidden-import xlrd \
    --hidden-import sqlalchemy \
    --hidden-import werkzeug \
    --hidden-import jinja2 \
    backend/app.py

# Check if executable was created
if [ -f "dist/AppLab-V3.exe" ]; then
    echo "✅ SUCCESS! Windows executable created: dist/AppLab-V3.exe"
    echo
    echo "📦 Creating distribution package..."
    mkdir -p "AppLab-V3_Windows"
    cp "dist/AppLab-V3.exe" "AppLab-V3_Windows/"
    cp "README.md" "AppLab-V3_Windows/README.txt"
    
    echo "📁 Distribution ready in: AppLab-V3_Windows/"
    echo "💾 Zip the entire folder for easy sharing!"
    echo
    echo "🎯 Instructions for users:"
    echo "1. Extract the AppLab-V3_Windows folder anywhere"
    echo "2. Double-click AppLab-V3.exe"
    echo "3. Browser opens automatically at http://localhost:5000"
    echo "4. Data is saved in user's Documents/AppLab-V3 folder"
else
    echo "❌ Build failed - check for errors above"
    exit 1
fi