import os, json
from modmanager.mod_data import CONFIG_FILE

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        return config
    except Exception as e:
        print("Error loading config:", e)
        return {"Game_Folder": ""}

def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print("Error saving config:", e)
