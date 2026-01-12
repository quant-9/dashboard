#!/usr/bin/env python3
"""
Trading Dashboard - Citadel Quant Metrics

Build script for creating a standalone macOS application.
Run with: python build_app.py
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Build the macOS application bundle."""
    
    # Ensure we're in the right directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # PyInstaller command for macOS app
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=Trading Dashboard",
        "--windowed",  # --windowed creates a .app bundle on macOS
        "--onedir",    # Creates a directory bundle (faster startup)
        "--noconfirm", # Overwrite output directory
        "--clean",     # Clean cache before building
        "--hidden-import", "PyQt6.QtWidgets",
        "--hidden-import", "PyQt6.QtCore", 
        "--hidden-import", "PyQt6.QtGui",
        "--hidden-import", "matplotlib.backends.backend_qtagg",
        "--hidden-import", "pandas",
        "--hidden-import", "numpy",
        "--collect-submodules", "matplotlib",
        "--collect-submodules", "pandas",
        "ui_app.py",
    ]
    
    print("=" * 60)
    print("Building Trading Dashboard for macOS...")
    print("=" * 60)
    
    try:
        subprocess.run(cmd, check=True)
        
        print("\n" + "=" * 60)
        print("✅ Build completed successfully!")
        print("=" * 60)
        print("\nThe application bundle is located at:")
        print(f"  {project_dir}/dist/Trading Dashboard.app")
        print("\nTo install:")
        print("  1. Drag 'Trading Dashboard.app' to your Applications folder")
        print("  2. Launch from Spotlight or Applications")
        print("\nNote: On first launch, you may need to right-click and select 'Open'")
        print("      if macOS Gatekeeper blocks the app.")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed with error code {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    main()
