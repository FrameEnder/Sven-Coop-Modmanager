#!/bin/bash
# Create a virtual environment named "venv"
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Upgrade pip (optional but recommended)
pip install --upgrade pip

# Install all required packages from requirements.txt
pip install -r requirements.txt

# Start the Python script
python main.py
