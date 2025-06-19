# favorites_manager.py
from __future__ import absolute_import, division, unicode_literals
import json
import os
import xbmcvfs

G = None
Logger = None

FAVORITES_FILE_NAME = 'favorites_mac.json'

def initialize_dependencies(globals_instance, logger_instance):
    global G, Logger
    G = globals_instance
    Logger = logger_instance
    if G and Logger:
        Logger.debug("favorites_manager.py: G and Logger initialized.")
    else:
        print("favorites_manager.py: Failed to initialize G or Logger for favorites_manager.")

def _get_favorites_file_path():
    if not G or not hasattr(G, 'ADDON_DATA_PATH'):
        if Logger:
            Logger.error(f"FavoritesManager: Nemoguće odrediti putanju za {FAVORITES_FILE_NAME}: G ili G.ADDON_DATA_PATH nisu inicijalizovani.")
        else:
            print(f"KRITIČNO: Nemoguće odrediti putanju za {FAVORITES_FILE_NAME}: G ili G.ADDON_DATA_PATH nisu inicijalizovani.")
        return os.path.join("error_addon_data_path_not_set", FAVORITES_FILE_NAME)
    return os.path.join(G.ADDON_DATA_PATH, FAVORITES_FILE_NAME)

def load_favorites():
    if not G or not Logger:
        print(f"FavoritesManager: G ili Logger nisu inicijalizovani! Ne mogu učitati omiljene unose iz {FAVORITES_FILE_NAME}.")
        return []

    file_path = _get_favorites_file_path()
    if not xbmcvfs.exists(file_path):
        return []
    try:
        with xbmcvfs.File(file_path, 'r') as f:
            content = f.read()
            if not content:
                return []
            favorites_list = json.loads(content)
            if not isinstance(favorites_list, list):
                Logger.error(f"Format fajla omiljenih ({file_path}) nije lista. Resetujem na praznu listu.")
                return []
            valid_favorites = []
            for item in favorites_list:
                if isinstance(item, dict) and 'fav_id' in item and 'portal_url' in item and 'mac_address' in item:
                    valid_favorites.append(item)
                else:
                    Logger.warning(f"Pronađen nevalidan unos u omiljenima, preskačem: {item}")
            return valid_favorites
    except Exception as e:
        Logger.error(f"Greška pri učitavanju fajla omiljenih ({file_path}): {e}")
        return []

def save_favorites(favorites_list):
    if not G or not Logger:
        print(f"FavoritesManager: G ili Logger nisu inicijalizovani! Ne mogu sačuvati omiljene unose u {FAVORITES_FILE_NAME}.")
        return

    file_path = _get_favorites_file_path()
    try:
        if hasattr(G, 'ADDON_DATA_PATH') and not xbmcvfs.exists(G.ADDON_DATA_PATH):
            xbmcvfs.mkdirs(G.ADDON_DATA_PATH)

        with xbmcvfs.File(file_path, 'w') as f:
            json.dump(favorites_list, f, indent=4)
        Logger.debug(f"Omiljeni unosi sačuvani u {file_path}")
    except Exception as e:
        Logger.error(f"Greška pri čuvanju fajla omiljenih ({file_path}): {e}")

def add_favorite(fav_item_dict):
    if not G or not Logger:
        print("FavoritesManager: G ili Logger nisu inicijalizovani! Ne mogu dodati u omiljene.")
        return False

    if not all(k in fav_item_dict for k in ['fav_id', 'portal_url', 'mac_address']):
        Logger.error(f"Pokušaj dodavanja nekompletnog omiljenog unosa: {fav_item_dict}")
        return False

    favorites = load_favorites()
    for item in favorites:
        if item.get('fav_id') == fav_item_dict['fav_id']:
            Logger.info(f"Omiljeni unos sa ID '{fav_item_dict['fav_id']}' već postoji.")
            return "exists"

    favorites.append(fav_item_dict)
    save_favorites(favorites)
    Logger.info(f"Omiljeni unos '{fav_item_dict.get('display_name', fav_item_dict['fav_id'])}' uspešno dodat.")
    return True

def remove_favorite(fav_id_to_remove):
    if not G or not Logger:
        print("FavoritesManager: G ili Logger nisu inicijalizovani! Ne mogu ukloniti iz omiljenih.")
        return False

    favorites = load_favorites()
    original_length = len(favorites)
    favorites_after_removal = [fav for fav in favorites if fav.get('fav_id') != fav_id_to_remove]

    if len(favorites_after_removal) < original_length:
        save_favorites(favorites_after_removal)
        Logger.info(f"Omiljeni unos sa ID '{fav_id_to_remove}' uspešno uklonjen.")
        return True
    else:
        Logger.warning(f"Omiljeni unos sa ID '{fav_id_to_remove}' nije pronađen za uklanjanje.")
        return False

def is_favorite(portal_url, mac_address):
    if not G or not Logger:
        return False

    fav_id_to_check = f"{portal_url.rstrip('/')}-{mac_address.upper()}"
    favorites = load_favorites()
    for item in favorites:
        if item.get('fav_id') == fav_id_to_check:
            return True
    return False