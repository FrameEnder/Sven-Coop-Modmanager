import os, json, glob, zipfile, shutil, re, math
import requests
from PIL import Image
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import QMessageBox
from modmanager.ui_components import SortableTableWidgetItem

# Global directories (set relative to the project root)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODS_FOLDER = os.path.join(BASE_DIR, "Mods")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
ENABLED_FILE = os.path.join(MODS_FOLDER, "Enabled.json")
DATA_DIR = os.path.join(BASE_DIR, "Data")
CACHE_HTML_DIR = os.path.join(DATA_DIR, ".cache", "html", "page")
CACHE_THUMB_DIR = os.path.join(DATA_DIR, ".cache", "thumbs")
DATA_PACK_DIR = os.path.join(BASE_DIR, "data-pack")


def initialize_directories():
    os.makedirs(MODS_FOLDER, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(CACHE_HTML_DIR, exist_ok=True)
    os.makedirs(CACHE_THUMB_DIR, exist_ok=True)
    os.makedirs(DATA_PACK_DIR, exist_ok=True)
    if not os.path.exists(ENABLED_FILE):
        with open(ENABLED_FILE, "w") as f:
            json.dump([], f)
    if not os.path.exists(CONFIG_FILE):
        default_config = {"Game_Folder": ""}
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=4)


def get_mod_list():
    initialize_directories()
    try:
        with open(ENABLED_FILE, "r") as f:
            enabled_mods = json.load(f)
    except:
        enabled_mods = []
    archives = []
    for ext in ["*.zip", "*.7z"]:
        archives.extend(glob.glob(os.path.join(MODS_FOLDER, ext)))
    mod_list = []
    for archive in archives:
        filename = os.path.basename(archive)
        orig_mod_name, ext = os.path.splitext(filename)
        displayed_name = orig_mod_name
        mod_data_dir = os.path.join(DATA_PACK_DIR, orig_mod_name)
        info_path = os.path.join(mod_data_dir, "info.json")
        if os.path.exists(info_path):
            try:
                with open(info_path, "r") as f:
                    info = json.load(f)
                if "name" in info and info["name"]:
                    displayed_name = info["name"]
            except:
                pass
        size_raw = os.path.getsize(archive)
        mod_list.append({
            "orig_mod_name": orig_mod_name,
            "displayed_name": displayed_name,
            "size_raw": size_raw,
            "enabled": orig_mod_name in enabled_mods,
            "archive_path": archive
        })
    return mod_list


def human_file_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.{decimal_places}f} {unit}"
        size /= 1024
    return f"{size:.{decimal_places}f} PB"


def enable_mod(mod_name, parent_widget=None):
    archive_file = None
    for ext in [".zip", ".7z"]:
        path = os.path.join(MODS_FOLDER, mod_name + ext)
        if os.path.exists(path):
            archive_file = path
            break
    if not archive_file:
        if parent_widget:
            QMessageBox.warning(parent_widget, "Error", "Selected mod file not found.")
        return False

    try:
        with open(ENABLED_FILE, "r") as f:
            enabled_mods = json.load(f)
    except:
        enabled_mods = []
    if mod_name not in enabled_mods:
        enabled_mods.append(mod_name)
    with open(ENABLED_FILE, "w") as f:
        json.dump(enabled_mods, f)

    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        game_folder = config.get("Game_Folder", "")
    except:
        game_folder = ""
    if not game_folder:
        if parent_widget:
            QMessageBox.warning(parent_widget, "Error", "Game folder not set in config.")
        return False
    addon_folder = os.path.join(game_folder, "svencoop_addon")
    os.makedirs(addon_folder, exist_ok=True)
    if archive_file.endswith(".zip"):
        try:
            with zipfile.ZipFile(archive_file, 'r') as zip_ref:
                zip_ref.extractall(addon_folder)
        except Exception as e:
            if parent_widget:
                QMessageBox.warning(parent_widget, "Error", f"Failed to extract zip archive: {e}")
            return False
    elif archive_file.endswith(".7z"):
        try:
            import py7zr
            with py7zr.SevenZipFile(archive_file, mode='r') as z:
                z.extractall(path=addon_folder)
        except Exception as e:
            if parent_widget:
                QMessageBox.warning(parent_widget, "Error", f"Failed to extract 7z archive: {e}")
            return False
    return True


def enable_all_mods(selected_mods, parent_widget=None):
    try:
        with open(ENABLED_FILE, "r") as f:
            enabled_mods = json.load(f)
    except:
        enabled_mods = []
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        game_folder = config.get("Game_Folder", "")
    except:
        game_folder = ""
    if not game_folder:
        if parent_widget:
            QMessageBox.warning(parent_widget, "Error", "Game folder not set in config.")
        return False
    addon_folder = os.path.join(game_folder, "svencoop_addon")
    os.makedirs(addon_folder, exist_ok=True)
    for mod in selected_mods:
        mod_name = mod["orig_mod_name"]
        if mod_name not in enabled_mods:
            enabled_mods.append(mod_name)
        archive_file = mod["archive_path"]
        if archive_file.endswith(".zip"):
            try:
                with zipfile.ZipFile(archive_file, 'r') as zip_ref:
                    zip_ref.extractall(addon_folder)
            except Exception as e:
                if parent_widget:
                    QMessageBox.warning(parent_widget, "Error", f"Failed to extract zip archive for {mod_name}: {e}")
        elif archive_file.endswith(".7z"):
            try:
                import py7zr
                with py7zr.SevenZipFile(archive_file, mode='r') as z:
                    z.extractall(path=addon_folder)
            except Exception as e:
                if parent_widget:
                    QMessageBox.warning(parent_widget, "Error", f"Failed to extract 7z archive for {mod_name}: {e}")
    with open(ENABLED_FILE, "w") as f:
        json.dump(enabled_mods, f)
    return True


def disable_mod(mod_name, parent_widget=None):
    try:
        with open(ENABLED_FILE, "r") as f:
            enabled_mods = json.load(f)
    except:
        enabled_mods = []
    if mod_name in enabled_mods:
        enabled_mods.remove(mod_name)
    with open(ENABLED_FILE, "w") as f:
        json.dump(enabled_mods, f)
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        game_folder = config.get("Game_Folder", "")
    except:
        game_folder = ""
    if not game_folder:
        if parent_widget:
            QMessageBox.warning(parent_widget, "Error", "Game folder not set in config.")
        return False
    addon_folder = os.path.join(game_folder, "svencoop_addon")
    if os.path.isdir(addon_folder):
        for filename in os.listdir(addon_folder):
            file_path = os.path.join(addon_folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                if parent_widget:
                    QMessageBox.warning(parent_widget, "Error", f"Failed to delete {file_path}: {e}")
    else:
        if parent_widget:
            QMessageBox.warning(parent_widget, "Error", "svencoop_addon folder not found in game folder.")
        return False
    # Re-enable remaining mods
    for mod in enabled_mods:
        for ext in [".zip", ".7z"]:
            archive_path = os.path.join(MODS_FOLDER, mod + ext)
            if os.path.exists(archive_path):
                if archive_path.endswith(".zip"):
                    try:
                        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                            zip_ref.extractall(addon_folder)
                    except Exception as e:
                        if parent_widget:
                            QMessageBox.warning(parent_widget, "Error", f"Failed to extract zip archive: {e}")
                elif archive_path.endswith(".7z"):
                    try:
                        import py7zr
                        with py7zr.SevenZipFile(archive_path, mode='r') as z:
                            z.extractall(path=addon_folder)
                    except Exception as e:
                        if parent_widget:
                            QMessageBox.warning(parent_widget, "Error", f"Failed to extract 7z archive: {e}")
    return True


def delete_mod(mod_name, parent_widget=None):
    for ext in [".zip", ".7z"]:
        file_path = os.path.join(MODS_FOLDER, mod_name + ext)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                if parent_widget:
                    QMessageBox.warning(parent_widget, "Error", f"Failed to delete {file_path}: {e}")
    remove_from_download_cache_by_zipname(mod_name)
    return True


def rename_mod(mod_name, new_alias, parent_widget=None):
    mod_data_dir = os.path.join(DATA_PACK_DIR, mod_name)
    os.makedirs(mod_data_dir, exist_ok=True)
    info_path = os.path.join(mod_data_dir, "info.json")
    info = {}
    if os.path.exists(info_path):
        try:
            with open(info_path, "r") as f:
                info = json.load(f)
        except:
            info = {}
    info["name"] = new_alias
    with open(info_path, "w") as f:
        json.dump(info, f, indent=4)
    return True


def set_mod_description(mod_name, description, parent_widget=None):
    mod_data_dir = os.path.join(DATA_PACK_DIR, mod_name)
    os.makedirs(mod_data_dir, exist_ok=True)
    info_path = os.path.join(mod_data_dir, "info.json")
    info = {}
    if os.path.exists(info_path):
        try:
            with open(info_path, "r") as f:
                info = json.load(f)
        except:
            info = {}
    info["description"] = description
    with open(info_path, "w") as f:
        json.dump(info, f, indent=4)
    return True


def set_mod_thumbnail(mod_name, source_path, parent_widget=None):
    mod_data_dir = os.path.join(DATA_PACK_DIR, mod_name)
    os.makedirs(mod_data_dir, exist_ok=True)
    thumb_path = os.path.join(mod_data_dir, "thumbnail.jpg")
    try:
        im = Image.open(source_path)
        rgb_im = im.convert('RGB')
        rgb_im.save(thumb_path, format='JPEG')
    except Exception as e:
        if parent_widget:
            QMessageBox.warning(parent_widget, "Error", f"Failed to convert and save image: {e}")
        return False
    return True


def load_download_cache():
    cache_path = os.path.join(DATA_DIR, "Download_Cache.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading Download_Cache.json: {e}")
    return {}


def save_download_cache(cache):
    cache_path = os.path.join(DATA_DIR, "Download_Cache.json")
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving Download_Cache.json: {e}")


def remove_from_download_cache_by_title(mod_title):
    cache = load_download_cache()
    keys_to_remove = [key for key, val in cache.items() if val.get("Title", "").strip() == mod_title.strip()]
    for key in keys_to_remove:
        del cache[key]
    save_download_cache(cache)


def remove_from_download_cache_by_zipname(zip_name):
    cache = load_download_cache()
    keys_to_remove = [
        key for key, val in cache.items()
        if os.path.splitext(val.get("zipName", ""))[0].strip().lower() == zip_name.strip().lower()
    ]
    for key in keys_to_remove:
        del cache[key]
    save_download_cache(cache)


def disable_all_mods(parent_widget=None):
    with open(ENABLED_FILE, "w") as f:
        json.dump([], f)
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        game_folder = config.get("Game_Folder", "")
    except:
        game_folder = ""
    if not game_folder:
        if parent_widget:
            QMessageBox.warning(parent_widget, "Error", "Game folder not set in config.")
        return False
    addon_folder = os.path.join(game_folder, "svencoop_addon")
    if os.path.isdir(addon_folder):
        for filename in os.listdir(addon_folder):
            file_path = os.path.join(addon_folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                if parent_widget:
                    QMessageBox.warning(parent_widget, "Error", f"Failed to delete {file_path}: {e}")
    else:
        if parent_widget:
            QMessageBox.warning(parent_widget, "Error", "svencoop_addon folder not found in game folder.")
        return False
    return True
