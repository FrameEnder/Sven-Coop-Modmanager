@echo off
REM Create a virtual environment named "venv"
python -m venv venv

REM Activate the virtual environment
call venv\Scripts\activate

REM Upgrade pip (optional but recommended)
pip install --upgrade pip

REM Install all required packages from requirements.txt
pip install -r requirements.txt

REM Start the Python script
python sven_map-manager.py
