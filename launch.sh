#!/bin/bash
# Trading Dashboard Launcher
# This script launches the Trading Dashboard from the source directory

cd "$(dirname "$0")/../.." || exit 1
source .venv/bin/activate
python ui_app.py
