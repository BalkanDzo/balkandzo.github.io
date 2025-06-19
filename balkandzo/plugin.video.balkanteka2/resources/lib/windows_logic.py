# -*- coding: utf-8 -*-

import xbmcvfs, xbmcaddon, xbmcgui, xbmcplugin, xbmc
import os
import sys
import urllib.request
import urllib.parse
import hashlib
import zipfile
import json
from urllib.parse import urlencode, parse_qsl
import shutil

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')
PROFILE_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))

KODI_HANDLE = -1
if len(sys.argv) > 1 and sys.argv[1].isdigit():
    KODI_HANDLE = int(sys.argv[1])
else:
    try:
        current_addon_id_for_log = ADDON_ID if 'ADDON_ID' in globals() else "UnknownAddon"
        xbmc.log(f"[{current_addon_id_for_log}] UPOZORENJE: KODI_HANDLE nije ispravno postavljen iz sys.argv u android_logic.py", xbmc.LOGWARNING)
    except NameError:
        xbmc.log(f"[UnknownAddonEarly] UPOZORENJE: KODI_HANDLE problem u android_logic.py, ADDON_ID nedostupan.", xbmc.LOGWARNING)

def log_message(message, level=xbmc.LOGINFO):
    try:
        addon_id_log = ADDON_ID if 'ADDON_ID' in globals() else "UnknownAddon"
        addon_version_log = ADDON_VERSION if 'ADDON_VERSION' in globals() else "UnknownVersion"
        xbmc.log(f"[{addon_id_log} {addon_version_log} WinLogic] {message}", level=level)
    except NameError:
         xbmc.log(f"[UnknownAddonLogic] {message}", level=level)

try:
    import resolveurl
    RESOLVEURL_AVAILABLE = True
    log_message("ResolveURL modul uspješno importovan.")
except ImportError:
    RESOLVEURL_AVAILABLE = False
    log_message("ResolveURL modul NIJE pronađen. Linkovi će se pokušati pustiti direktno.", level=xbmc.LOGWARNING)

CONTENT_SOURCES = {
    'domaci': {
        'name': "Domaći Sadržaj",
        'checksum_url': "https://raw.githubusercontent.com/BalkanDzo/balkandzodom/refs/heads/main/data/domaci/checksum_kodi_domaci.txt",
        'zip_url': "https://github.com/BalkanDzo/balkandzodom/raw/refs/heads/main/data/domaci/data_kodi_domaci.zip",
        'extracted_path': os.path.join(PROFILE_PATH, 'data_extracted_domaci'),
        'local_checksum_file': os.path.join(PROFILE_PATH, 'local_checksum_domaci.txt'),
        'categories_file_name': 'categories_domaci.json'
    },
    'strani': {
        'name': "Strani Sadržaj",
        'checksum_url': "https://raw.githubusercontent.com/BalkanDzo/balkandzostr/refs/heads/main/data/strani/checksum_kodi_strani.txt",
        'zip_url': "https://github.com/BalkanDzo/balkandzostr/raw/refs/heads/main/data/strani/data_kodi_strani.zip",
        'extracted_path': os.path.join(PROFILE_PATH, 'data_extracted_strani'),
        'local_checksum_file': os.path.join(PROFILE_PATH, 'local_checksum_strani.txt'),
        'categories_file_name': 'categories_strani.json'
    }
}

DEFAULT_CATEGORIES_CONFIG = {
    'filmovi': {'name': 'Filmovi', 'icon': 'DefaultVideo.png'},
    'serije': {'name': 'Serije', 'icon': 'DefaultTVShows.png'},
    'crtani-filmovi': {'name': 'Crtani Filmovi', 'icon': 'DefaultVideo.png'},
    'crtane-serije': {'name': 'Crtane Serije', 'icon': 'DefaultTVShows.png'},
    'kolekcije': {'name': 'Kolekcije', 'icon': 'DefaultFolder.png'}
}

LINK_GROUP_DISPLAY_NAMES = {
    'glavni': "Glavni Link",
    'alternativni_1': "Alternativni Link 1",
    'alternativni_2': "Alternativni Link 2"
}

def add_dir(name, params, is_folder=True, thumb=None, fanart=None, info_labels=None, total_items=0, is_playable=False):
    url = f"{sys.argv[0]}?{urlencode(params)}"
    list_item = xbmcgui.ListItem(label=name)
    if info_labels: list_item.setInfo(type='video', infoLabels=info_labels)
    art = {}
    if thumb: art['thumb'] = art['icon'] = thumb
    if fanart: art['fanart'] = fanart
    if art: list_item.setArt(art)
    if is_playable:
        list_item.setProperty('IsPlayable', 'true')
        is_folder = False
    xbmcplugin.addDirectoryItem(handle=KODI_HANDLE, url=url, listitem=list_item, isFolder=is_folder, totalItems=total_items)

def end_directory(succeeded=True, update_listing=False, cache_to_disc=True):
    xbmcplugin.endOfDirectory(KODI_HANDLE, succeeded=succeeded, updateListing=update_listing, cacheToDisc=cache_to_disc)

def get_remote_checksum(content_type):
    url = CONTENT_SOURCES[content_type]['checksum_url']
    try:
        req = urllib.request.Request(url, headers={'User-Agent': f'{ADDON_ID}/{ADDON_VERSION}'})
        with urllib.request.urlopen(req, timeout=15) as response:
            checksum = response.read().decode('utf-8').strip()
        return checksum
    except Exception as e:
        log_message(f"Greška pri preuzimanju udaljenog checksuma ({content_type}): {e}", xbmc.LOGERROR); return None

def get_local_checksum(content_type):
    checksum_file = CONTENT_SOURCES[content_type]['local_checksum_file']
    if os.path.exists(checksum_file):
        try:
            with open(checksum_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            log_message(f"Greška pri čitanju lokalnog checksuma ({content_type}) sa {checksum_file} koristeći open: {e}", xbmc.LOGERROR)
    return None

def save_local_checksum(content_type, checksum):
    checksum_file = CONTENT_SOURCES[content_type]['local_checksum_file']
    try:
        os.makedirs(os.path.dirname(checksum_file), exist_ok=True)
        with open(checksum_file, 'w', encoding='utf-8') as f:
            f.write(str(checksum))
    except Exception as e:
        log_message(f"Greška pri čuvanju lokalnog checksuma ({content_type}) u {checksum_file} koristeći open: {e}", xbmc.LOGERROR)

def shutil_like_copyfileobj(fsrc, fdst, length=16*1024):
    while True:
        buf = fsrc.read(length)
        if not buf: break
        fdst.write(buf)

def robust_delete_directory_os(path_to_delete):
    log_message(f"Pokušaj robustnog brisanja direktorijuma (os/shutil): {path_to_delete}", xbmc.LOGINFO)
    if not os.path.exists(path_to_delete):
        log_message(f"Direktorijum {path_to_delete} ne postoji, preskačem.", xbmc.LOGINFO)
        return True
    
    shutil_used_and_successful = False
    try:
        log_message(f"Pokušavam sa shutil.rmtree({path_to_delete})", xbmc.LOGDEBUG)
        shutil.rmtree(path_to_delete)
        if not os.path.exists(path_to_delete):
            log_message(f"Direktorijum {path_to_delete} uspješno obrisan koristeći shutil.rmtree.", xbmc.LOGINFO)
            shutil_used_and_successful = True
            return True
        else:
            log_message(f"UPOZORENJE: shutil.rmtree({path_to_delete}) nije prijavio grešku, ali direktorijum i dalje postoji! Prelazim na os fallback.", xbmc.LOGWARNING)
    except NameError:
        log_message("shutil modul ili rmtree nije dostupan, prelazim na os fallback.", xbmc.LOGWARNING)
    except FileNotFoundError:
        log_message(f"Direktorijum {path_to_delete} nije pronađen za shutil.rmtree (možda već obrisan). Smatram uspješnim.", xbmc.LOGINFO)
        return True
    except PermissionError as e_shutil_perm:
        log_message(f"Greška dozvole pri shutil.rmtree za {path_to_delete}: {e_shutil_perm}. Prelazim na os fallback.", xbmc.LOGERROR)
    except OSError as e_shutil_os:
        log_message(f"OSError pri shutil.rmtree za {path_to_delete}: {e_shutil_os}. Provjerite da li su fajlovi zaključani. Prelazim na os fallback.", xbmc.LOGERROR)
    except Exception as e_shutil_other:
        log_message(f"Neočekivana greška pri shutil.rmtree za {path_to_delete}: {type(e_shutil_other).__name__} - {e_shutil_other}. Prelazim na os fallback.", xbmc.LOGERROR)

    if shutil_used_and_successful:
         return True

    log_message(f"shutil.rmtree nije uspio ili nije korišten za {path_to_delete}. Pokušavam sa os modulom.", xbmc.LOGINFO)
    try:
        if not os.path.isdir(path_to_delete):
            if os.path.exists(path_to_delete):
                log_message(f"{path_to_delete} nije direktorijum (provjereno sa os.path.isdir), pokušavam os.remove().", xbmc.LOGDEBUG)
                os.remove(path_to_delete)
                log_message(f"Stavka (fajl) {path_to_delete} uspješno obrisana koristeći os.remove.", xbmc.LOGINFO)
                return not os.path.exists(path_to_delete)
            else:
                log_message(f"{path_to_delete} ne postoji, smatram obrisanim (os fallback).", xbmc.LOGINFO)
                return True

        all_content_deleted_successfully = True
        try:
            dir_listing = os.listdir(path_to_delete)
        except Exception as e_listdir_fallback:
            log_message(f"Ne mogu listati direktorijum {path_to_delete} u os fallback: {e_listdir_fallback}", xbmc.LOGERROR)
            return False

        for item_name in dir_listing:
            item_path = os.path.join(path_to_delete, item_name)
            try:
                if os.path.isdir(item_path):
                    if not robust_delete_directory_os(item_path):
                        log_message(f"Neuspjeh rekurzivnog brisanja pod-direktorijuma (os): {item_path}", xbmc.LOGERROR)
                        all_content_deleted_successfully = False
                else:
                    log_message(f"Pokušavam os.remove({item_path})", xbmc.LOGDEBUG)
                    os.remove(item_path)
            except PermissionError as e_perm_item:
                 log_message(f"Greška dozvole pri brisanju stavke (os): {item_path} - {e_perm_item}", xbmc.LOGERROR)
                 all_content_deleted_successfully = False
            except OSError as e_os_item:
                log_message(f"OSError pri brisanju stavke (os): {item_path} - {e_os_item}", xbmc.LOGERROR)
                all_content_deleted_successfully = False
            except Exception as e_item_general:
                log_message(f"Opšta greška pri brisanju stavke (os): {item_path} - {e_item_general}", xbmc.LOGERROR)
                all_content_deleted_successfully = False
        
        if not all_content_deleted_successfully:
            log_message(f"Nije sav sadržaj unutar {path_to_delete} uspješno obrisan (os fallback).", xbmc.LOGWARNING)
            return False

        log_message(f"Pokušavam os.rmdir({path_to_delete})", xbmc.LOGDEBUG)
        os.rmdir(path_to_delete)
        
        if not os.path.exists(path_to_delete):
            log_message(f"Direktorijum {path_to_delete} uspješno obrisan koristeći os.rmdir.", xbmc.LOGINFO)
            return True
        else:
            log_message(f"UPOZORENJE: os.rmdir({path_to_delete}) nije prijavio grešku, ali direktorijum i dalje postoji!", xbmc.LOGWARNING)
            return False
            
    except PermissionError as e_os_perm:
        log_message(f"Greška dozvole tokom os fallback brisanja za {path_to_delete}: {e_os_perm}", xbmc.LOGERROR)
        import traceback; log_message(traceback.format_exc(), xbmc.LOGERROR)
        return False
    except OSError as e_os_specific:
        log_message(f"Specifična OS greška tokom os fallback brisanja za {path_to_delete}: {type(e_os_specific).__name__} - {e_os_specific}", xbmc.LOGERROR)
        import traceback; log_message(traceback.format_exc(), xbmc.LOGERROR)
        return False
    except Exception as e_os_general:
        log_message(f"Opšta greška tokom os fallback brisanja za {path_to_delete}: {type(e_os_general).__name__} - {e_os_general}", xbmc.LOGERROR)
        import traceback; log_message(traceback.format_exc(), xbmc.LOGERROR)
        return False

def download_and_extract_zip(content_type):
    source_info = CONTENT_SOURCES[content_type]
    progress_dialog = xbmcgui.DialogProgress()
    progress_dialog.create(f"{ADDON_NAME} - {source_info['name']}", "Priprema za ažuriranje...")
    
    extracted_path_real = source_info['extracted_path']
    
    log_message(f"POČETAK AŽURIRANJA za '{source_info['name']}'. Prvo brisanje starog direktorijuma: {extracted_path_real}")
    if os.path.exists(extracted_path_real):
        if not robust_delete_directory_os(extracted_path_real):
            log_message(f"Brisanje direktorijuma {extracted_path_real} NIJE uspjelo. Ažuriranje za '{source_info['name']}' se prekida.", xbmc.LOGERROR)
            progress_dialog.close()
            xbmcgui.Dialog().notification(f"{ADDON_NAME} - {source_info['name']}", "Greška: Nije moguće obrisati stare podatke. Provjerite logove i dozvole.", xbmcgui.NOTIFICATION_ERROR, 7000)
            return False
        else:
            log_message(f"Direktorijum {extracted_path_real} uspješno obrisan.")
    else:
        log_message(f"Direktorijum {extracted_path_real} ne postoji, preskačem brisanje.")

    log_message(f"Kreiram osnovni direktorijum za ekstrakciju (os.makedirs): {extracted_path_real}")
    try:
        os.makedirs(extracted_path_real, exist_ok=True)
        if not os.path.exists(extracted_path_real) or not os.path.isdir(extracted_path_real):
             log_message(f"KRITIČNA GREŠKA: Direktorijum {extracted_path_real} nije uspješno kreiran.", xbmc.LOGERROR)
             progress_dialog.close()
             xbmcgui.Dialog().notification(f"{ADDON_NAME} - {source_info['name']}", "Greška pri pripremi direktorija.", xbmcgui.NOTIFICATION_ERROR, 5000)
             return False
    except Exception as e_mkdir:
        log_message(f"NEUSPJEH: Kreiranje direktorija {extracted_path_real} (os.makedirs): {e_mkdir}", xbmc.LOGERROR)
        progress_dialog.close()
        xbmcgui.Dialog().notification(f"{ADDON_NAME} - {source_info['name']}", "Greška pri kreiranju direktorija.", xbmcgui.NOTIFICATION_ERROR, 5000)
        return False

    temp_zip_dir_kodi = xbmcvfs.translatePath("special://home/temp_addon_zip/")
    if not os.path.exists(temp_zip_dir_kodi):
        os.makedirs(temp_zip_dir_kodi, exist_ok=True)
    temp_zip_path = os.path.join(temp_zip_dir_kodi, f'temp_data_{content_type}.zip')
    
    response_obj = None
    progress_dialog.update(0, "Započinjem preuzimanje...")
    try:
        log_message(f"Preuzimanje ZIP-a ({content_type}) sa: {source_info['zip_url']}")
        req = urllib.request.Request(source_info['zip_url'], headers={'User-Agent': f'{ADDON_ID}/{ADDON_VERSION}'})
        response_obj = urllib.request.urlopen(req, timeout=300)
        total_size_header = response_obj.getheader('Content-Length')
        total_size = int(total_size_header) if total_size_header and total_size_header.isdigit() else None
        downloaded_size = 0; chunk_size = 8192

        with open(temp_zip_path, 'wb') as file_obj_local_download:
            while True:
                if progress_dialog.iscanceled():
                    log_message(f"Preuzimanje ({content_type}) otkazano.", xbmc.LOGWARNING)
                    if os.path.exists(temp_zip_path): os.remove(temp_zip_path)
                    progress_dialog.close(); return False
                chunk = response_obj.read(chunk_size)
                if not chunk: break
                file_obj_local_download.write(chunk); downloaded_size += len(chunk)
                if total_size:
                    percent = int(downloaded_size * 100 / total_size)
                    progress_dialog.update(percent, f"Preuzimanje: {downloaded_size // 1048576}MB / {total_size // 1048576}MB ({percent}%)")
                else:
                    progress_dialog.update(0, f"Preuzimanje: {downloaded_size // 1048576}MB")
        
        log_message(f"ZIP preuzet ({content_type}): {temp_zip_path}")
        progress_dialog.update(0, message="Ekstraktovanje sadržaja...")
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            members_to_extract = zip_ref.infolist()
            total_members = len(members_to_extract)
            log_message(f"Pokušaj ekstrakcije {total_members} članova ZIP-a jedan po jedan u: {extracted_path_real}")

            for i, member in enumerate(members_to_extract):
                if progress_dialog.iscanceled():
                    log_message(f"Ekstrakcija ({content_type}) otkazana.", xbmc.LOGWARNING)
                    if os.path.exists(temp_zip_path): os.remove(temp_zip_path)
                    progress_dialog.close(); return False

                member_filename_cleaned = member.filename.replace('\\', '/')
                target_path_for_member = os.path.join(extracted_path_real, member_filename_cleaned)

                if member_filename_cleaned == source_info['categories_file_name']:
                    log_message(f"EKSTRAKCIJA KATEGORIJSKOG FAJLA: Član ZIP-a='{member.filename}', Ciljna putanja='{target_path_for_member}'", xbmc.LOGWARNING)

                if not os.path.abspath(target_path_for_member).startswith(os.path.abspath(extracted_path_real)):
                    log_message(f"Preskačem potencijalno nesigurnog člana ZIP-a: {member.filename}", xbmc.LOGWARNING)
                    continue
                
                if member.is_dir() or member.filename.endswith('/'):
                    if not os.path.exists(target_path_for_member):
                         log_message(f"Kreiram direktorijum (os.makedirs): {target_path_for_member}")
                    try:
                        os.makedirs(target_path_for_member, exist_ok=True)
                    except Exception as e_mkdir_member:
                            log_message(f"NEUSPJEH: Kreiranje direktorija {target_path_for_member} nije uspjelo (os.makedirs): {e_mkdir_member}", xbmc.LOGERROR)
                else: 
                    parent_dir_for_file = os.path.dirname(target_path_for_member)
                    if not os.path.exists(parent_dir_for_file):
                        log_message(f"Kreiram roditeljski direktorij (os.makedirs) za datoteku: {parent_dir_for_file}")
                        try:
                            os.makedirs(parent_dir_for_file, exist_ok=True)
                        except Exception as e_mkdir_parent:
                            log_message(f"NEUSPJEH: Kreiranje rod. direktorija {parent_dir_for_file} nije uspjelo (os.makedirs): {e_mkdir_parent}", xbmc.LOGERROR)
                    
                    if os.path.isdir(target_path_for_member):
                        log_message(f"UPOZORENJE: Putanja za datoteku {target_path_for_member} već postoji kao direktorij. Preskačem ekstrakciju ove datoteke.", xbmc.LOGWARNING)
                        continue

                    try:
                        with zip_ref.open(member.filename) as source_file_in_zip, \
                             open(target_path_for_member, 'wb') as destination_file_os:
                            shutil_like_copyfileobj(source_file_in_zip, destination_file_os)
                    except Exception as e_write_os:
                        log_message(f"Greška pri pisanju datoteke {target_path_for_member} koristeći open/shutil_like: {e_write_os}", xbmc.LOGERROR)
                
                percent = int((i + 1) * 100 / total_members) if total_members > 0 else 100
                progress_dialog.update(percent, f"Ekstraktovanje: {member.filename[:30]}... ({percent}%)")

        log_message(f"Završena ekstrakcija članova jedan po jedan za {content_type}.")
        if os.path.exists(temp_zip_path): os.remove(temp_zip_path)
        progress_dialog.update(100, message="Ažuriranje završeno!"); progress_dialog.close()
        xbmcgui.Dialog().notification(f"{ADDON_NAME} - {source_info['name']}", "Sadržaj uspješno ažuriran!", xbmcgui.NOTIFICATION_INFO, 3000); return True
    
    except Exception as e:
        log_message(f"Greška tokom preuzimanja ili ekstrakcije ({content_type}): {e}", xbmc.LOGERROR)
        import traceback; log_message(traceback.format_exc(), xbmc.LOGERROR)
        if os.path.exists(temp_zip_path): os.remove(temp_zip_path)
        if progress_dialog: progress_dialog.close()
        xbmcgui.Dialog().notification(f"{ADDON_NAME} - {source_info['name']}", f"Greška pri ažuriranju: {e}", xbmcgui.NOTIFICATION_ERROR, 5000); return False
    finally:
        if response_obj:
            try: response_obj.close()
            except: pass

def check_for_updates(content_type, force_update=False):
    log_message(f"Provjera ažuriranja za {content_type}. Force update: {force_update}")
    source_info = CONTENT_SOURCES[content_type]
    extracted_path_real = source_info['extracted_path']
    
    if force_update:
        log_message(f"Forsirano ažuriranje za {content_type}. Pokrećem download_and_extract_zip.")
        remote_checksum_for_save = get_remote_checksum(content_type)
        if remote_checksum_for_save is None and not force_update:
             log_message(f"Nije moguće dohvatiti udaljeni checksum za {content_type} tokom forsiranog ažuriranja (za čuvanje).", xbmc.LOGWARNING)

        if download_and_extract_zip(content_type):
            if remote_checksum_for_save:
                save_local_checksum(content_type, remote_checksum_for_save)
            else:
                local_checksum_path = CONTENT_SOURCES[content_type]['local_checksum_file']
                if os.path.exists(local_checksum_path):
                    try:
                        os.remove(local_checksum_path)
                        log_message(f"Obrisan stari lokalni checksum za {content_type} jer novi nije bio dostupan.", xbmc.LOGWARNING)
                    except Exception as e_remove_cs:
                        log_message(f"Greška pri brisanju starog lokalnog checksuma za {content_type}: {e_remove_cs}", xbmc.LOGERROR)

            log_message(f"Forsirano ažuriranje za {content_type} uspješno.")
            return True
        else:
            log_message(f"Forsirano ažuriranje za {content_type} NIJE uspjelo (download_and_extract_zip vratio False).", xbmc.LOGERROR)
            return False

    remote_checksum = get_remote_checksum(content_type)
    local_checksum = get_local_checksum(content_type)
    
    local_data_exists_and_not_empty = False
    if os.path.exists(extracted_path_real) and os.path.isdir(extracted_path_real):
        try:
            if os.listdir(extracted_path_real): local_data_exists_and_not_empty = True
        except OSError as e_listdir:
            log_message(f"Greška pri os.listdir za {extracted_path_real} u check_for_updates: {e_listdir}", xbmc.LOGWARNING)
            local_data_exists_and_not_empty = False
            
    update_needed = (local_checksum != remote_checksum) or not local_data_exists_and_not_empty
    log_message(f"check_for_updates [{content_type}]: RemoteCS='{remote_checksum}', LocalCS='{local_checksum}', DataExists='{local_data_exists_and_not_empty}', UpdateNeeded='{update_needed}'")

    if remote_checksum is None:
        if local_data_exists_and_not_empty:
            xbmcgui.Dialog().notification(ADDON_NAME, f"Nije moguće provjeriti ažuriranja za {source_info['name']}. Koriste se postojeći podaci.", xbmcgui.NOTIFICATION_WARNING, 3000)
            return True 
        else:
            xbmcgui.Dialog().ok(ADDON_NAME, f"Nije moguće provjeriti ažuriranja za {source_info['name']} i nema lokalnih podataka.\nProvjerite internet konekciju.")
            return False 

    if update_needed:
        log_message(f"Potrebno ažuriranje za {content_type} (checksum ili nepostojeći podaci). Pokrećem download_and_extract_zip.")
        if download_and_extract_zip(content_type):
            save_local_checksum(content_type, remote_checksum)
            log_message(f"Ažuriranje za {content_type} uspješno, sačuvan novi checksum.")
            return True
        else: 
            log_message(f"download_and_extract_zip za {content_type} vratio False. AŽURIRANJE NIJE USPJELO. Izvor '{source_info['name']}' se smatra neispravnim.", xbmc.LOGERROR)
            return False
    else:
        log_message(f"Sadržaj za {content_type} je ažuran.")
        return True

def get_categories_config_from_zip(content_type):
    source_info = CONTENT_SOURCES[content_type]
    extracted_path_real = source_info['extracted_path']
    categories_file_path = os.path.join(extracted_path_real, source_info['categories_file_name'])
    log_message(f"get_categories_config_from_zip: Pokušaj čitanja za '{content_type}' sa putanje (os.path): {categories_file_path}")
    if os.path.exists(categories_file_path) and os.path.isfile(categories_file_path):
        content_var = ""
        try:
            with open(categories_file_path, 'r', encoding='utf-8') as f:
                content_var = f.read()
            if not content_var.strip(): 
                log_message(f"Fajl '{categories_file_path}' je PRAZAN!", xbmc.LOGWARNING)
                return DEFAULT_CATEGORIES_CONFIG
            parsed_json = json.loads(content_var)
            log_message(f"JSON uspešno parsiran iz {categories_file_path}")
            return parsed_json
        except json.JSONDecodeError as e_json:
            log_message(f"Greška pri parsiranju JSON-a iz {categories_file_path}: {e_json}. Sadržaj (prvih 200b): '{content_var[:200]}...'", xbmc.LOGERROR)
        except Exception as e:
            log_message(f"Greška pri čitanju ili parsiranju {categories_file_path} koristeći open: {e}", xbmc.LOGERROR)
    else:
        log_message(f"Fajl kategorija NIJE PRONAĐEN ili nije fajl (os.path): {categories_file_path}", xbmc.LOGWARNING)
    log_message(f"Koriste se podrazumijevane kategorije za {content_type}.", xbmc.LOGWARNING)
    return DEFAULT_CATEGORIES_CONFIG

def main_menu():
    log_message("POZIV: main_menu (WinLogic)")
    wait_dialog = xbmcgui.DialogProgressBG()
    wait_dialog.create(ADDON_NAME, "Automatsko ažuriranje sadržaja...")
    sources_status = {}
    try:
        for key, source_details in CONTENT_SOURCES.items():
            if "VAŠ_RAW_GITHUB_LINK" in source_details['checksum_url'] or \
               "VAŠ_RAW_GITHUB_LINK" in source_details['zip_url']:
                log_message(f"Preskačem automatsko ažuriranje za '{key}' zbog placeholder URL-ova.", xbmc.LOGWARNING)
                sources_status[key] = False 
                continue

            log_message(f"Pokrećem automatsko ažuriranje (ponašanje kao 'force_specific_update') za: {key}")

            sources_status[key] = check_for_updates(key, force_update=True)
            
    finally:
        wait_dialog.close()

    num_valid_sources = sum(1 for status_ok in sources_status.values() if status_ok)
    total_display_items = 1 + num_valid_sources + 1

    add_dir("Pretraga Sadržaja...",{'action': 'prompt_search'},is_folder=True, thumb='DefaultAddonsSearch.png', total_items=total_display_items)
    
    for key, is_ok in sources_status.items():
        if is_ok:
            add_dir(CONTENT_SOURCES[key]['name'], {'action': 'list_categories', 'content_type': key}, is_folder=True, total_items=total_display_items)
    
    add_dir("Ručno Ažuriranje Sadržaja", {'action': 'manual_update_selection'}, is_folder=True, thumb='DefaultAddonsUpdates.png', total_items=total_display_items)
            
    if num_valid_sources == 0:
        xbmcgui.Dialog().notification(ADDON_NAME, "Nijedan izvor sadržaja nije automatski učitan ili ažuriran. Pokušajte ručno ažuriranje.", xbmcgui.NOTIFICATION_ERROR, 5000)
    elif num_valid_sources < len(CONTENT_SOURCES):
         xbmcgui.Dialog().notification(ADDON_NAME, "Neki izvori sadržaja nisu uspješno ažurirani. Provjerite logove ili pokušajte ručno.", xbmcgui.NOTIFICATION_WARNING, 5000)


    end_directory(succeeded=True)

def manual_update_selection():
    log_message("POZIV: manual_update_selection (WinLogic)")
    xbmcplugin.setPluginCategory(KODI_HANDLE, "Ručno Ažuriranje - Odaberite Izvor")
    items_for_update = []
    valid_sources_count = 0
    for c_type, c_info in CONTENT_SOURCES.items():
        if "VAŠ_RAW_GITHUB_LINK" in c_info['checksum_url'] or \
           "VAŠ_RAW_GITHUB_LINK" in c_info['zip_url']:
            log_message(f"Preskačem opciju ažuriranja za '{c_type}' zbog placeholder URL-ova.")
            continue
        items_for_update.append({'name': f"Ažuriraj {c_info['name']}", 'params': {'action': 'force_specific_update', 'content_type': c_type}})
        valid_sources_count +=1
    if not items_for_update:
        xbmcgui.Dialog().ok(ADDON_NAME, "Nema konfiguriranih izvora za ručno ažuriranje.")
        end_directory(succeeded=False); return
    for item in items_for_update:
        add_dir(item['name'], item['params'], is_folder=True, thumb='DefaultAddonProgram.png', total_items=valid_sources_count)
    end_directory(succeeded=True)

def force_specific_update(content_type):
    log_message(f"POKRENUTO (RUČNO ILI FORSIRANO AUTOMATSKO) AŽURIRANJE za: {content_type} (WinLogic)")
    source_info = CONTENT_SOURCES[content_type]

    if not check_for_updates(content_type, force_update=True):
        log_message(f"Ručno (forsirano) ažuriranje za {content_type} NIJE uspjelo.", xbmc.LOGERROR)
    else:
        log_message(f"Ručno (forsirano) ažuriranje za {content_type} uspješno završeno.")

def list_categories_for_type(content_type):
    log_message(f"POZIV: list_categories_for_type, content_type={content_type}")
    categories_config = get_categories_config_from_zip(content_type)
    log_message(f"list_categories_for_type: Učitane kategorije za {content_type}: {categories_config}")
    source_name = CONTENT_SOURCES[content_type]['name']
    xbmcplugin.setPluginCategory(KODI_HANDLE, source_name)
    if not isinstance(categories_config, dict) or not categories_config:
        log_message(f"Nema validne konfiguracije kategorija za {content_type}. Tip: {type(categories_config)}", xbmc.LOGWARNING)
        xbmcgui.Dialog().ok(ADDON_NAME, f"Nema konfiguracije kategorija za {source_name}."); end_directory(succeeded=True); return
    item_added_count = 0
    total_cat_items = sum(1 for details in categories_config.values() if isinstance(details, dict) and 'name' in details)
    for cat_id, details in categories_config.items():
        if isinstance(details, dict) and 'name' in details:
            log_message(f"Dodavanje kategorije: ID='{cat_id}', Naziv='{details['name']}'")
            add_dir(details['name'],{'action': 'list_items_in_category', 'content_type': content_type, 'category_id': cat_id}, is_folder=True,thumb=details.get('icon'), total_items=total_cat_items); item_added_count +=1
    if item_added_count == 0:
        log_message(f"Nijedna kategorija nije dodata za {content_type}.", xbmc.LOGWARNING)
        xbmcgui.Dialog().ok(ADDON_NAME, f"Nema dostupnih kategorija za {source_name}.")
    end_directory(succeeded=True)

def list_items_in_category(content_type, category_id):
    log_message(f"POZIV: list_items_in_category, content_type={content_type}, category_id={category_id}")
    source_info = CONTENT_SOURCES[content_type]; extracted_path_real = source_info['extracted_path']
    categories_config = get_categories_config_from_zip(content_type)
    category_name_display = category_id.replace('-', ' ').capitalize() 
    if category_id in categories_config and 'name' in categories_config[category_id]: category_name_display = categories_config[category_id]['name']
    xbmcplugin.setPluginCategory(KODI_HANDLE, f"{source_info['name']} - {category_name_display}")
    if category_id in ['serije', 'crtane-serije']: xbmcplugin.setContent(KODI_HANDLE, 'tvshows')
    elif category_id == 'kolekcije': xbmcplugin.setContent(KODI_HANDLE, 'movies') 
    else: xbmcplugin.setContent(KODI_HANDLE, 'movies')
    category_data_path = os.path.join(extracted_path_real, category_id)
    if not os.path.exists(category_data_path) or not os.path.isdir(category_data_path):
        log_message(f"Direktorijum kategorije '{category_id}' nije pronađen (os.path): {category_data_path}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, f"Sadržaj za kategoriju '{category_name_display}' nije pronađen."); end_directory(succeeded=True); return
    log_message(f"[WinLogic list_items_in_category] Direktorijum kategorije '{category_id}' PRONAĐEN (os.path): {category_data_path}")
    sub_items = []; dir_content_list = []
    try: 
        dir_content_list = sorted(os.listdir(category_data_path))
    except OSError as e_listdir:
        log_message(f"Greška pri os.listdir za {category_data_path}: {e_listdir}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, f"Greška pri čitanju sadržaja kategorije '{category_name_display}'."); end_directory(succeeded=True); return
    log_message(f"[WinLogic list_items_in_category] Sadržaj za {category_id} - {dir_content_list} (os.listdir)")
    if category_id == 'kolekcije':
        for item_file in dir_content_list:
            item_full_path = os.path.join(category_data_path, item_file)
            if item_file.endswith('.json') and os.path.isfile(item_full_path):
                item_name_from_file = os.path.splitext(item_file)[0].replace('-', ' ').capitalize(); thumb_coll = None
                try:
                    with open(item_full_path, 'r', encoding='utf-8') as f_coll: coll_data = json.load(f_coll)
                    item_name_from_file = coll_data.get('title', item_name_from_file); thumb_coll = coll_data.get('thumb')
                except Exception as e_coll: log_message(f"Greška pri čitanju JSON-a kolekcije {item_file} (open): {e_coll}", xbmc.LOGWARNING)
                sub_items.append({'name': item_name_from_file, 'params': {'action': 'display_collection_movies', 'content_type': content_type, 'category_id': category_id, 'collection_filename': item_file}, 'is_folder': True, 'thumb': thumb_coll})
    elif category_id in ['serije', 'crtane-serije']:
        ongoing_path_segment = 'emitovanje-u-toku'
        ongoing_full_path = os.path.join(category_data_path, ongoing_path_segment)
        if ongoing_path_segment in dir_content_list and os.path.isdir(ongoing_full_path):
            try:
                if os.listdir(ongoing_full_path): 
                    sub_items.append({'name': "Emitovanje u toku", 'params': {'action': 'list_titles_in_subfolder', 'content_type': content_type, 'category_id': category_id, 'subfolder_name': ongoing_path_segment}, 'is_folder': True})
            except OSError: pass
        for year_folder in dir_content_list:
            year_folder_full_path = os.path.join(category_data_path, year_folder)
            if year_folder.isdigit() and os.path.isdir(year_folder_full_path):
                sub_items.append({'name': year_folder, 'params': {'action': 'list_titles_in_subfolder', 'content_type': content_type, 'category_id': category_id, 'subfolder_name': year_folder}, 'is_folder': True})
    else: 
        for year_folder in dir_content_list:
            year_folder_full_path = os.path.join(category_data_path, year_folder)
            if year_folder.isdigit() and os.path.isdir(year_folder_full_path):
                sub_items.append({'name': year_folder, 'params': {'action': 'list_titles_in_subfolder', 'content_type': content_type, 'category_id': category_id, 'subfolder_name': year_folder}, 'is_folder': True})
    if not sub_items:
        xbmcgui.Dialog().ok(ADDON_NAME, f"Nema dostupnih podkategorija ili stavki u '{category_name_display}'."); end_directory(succeeded=True); return
    for item_data in sub_items:
        add_dir(item_data['name'], item_data['params'], is_folder=item_data['is_folder'], thumb=item_data.get('thumb'), total_items=len(sub_items))
    end_directory()

def display_collection_movies(content_type, category_id, collection_filename):
    log_message(f"POZIV: display_collection_movies, collection_filename={collection_filename}")
    source_info = CONTENT_SOURCES[content_type]; extracted_path_real = source_info['extracted_path']
    collection_file_path = os.path.join(extracted_path_real, category_id, collection_filename)
    try:
        with open(collection_file_path, 'r', encoding='utf-8') as f: collection_data = json.load(f)
        collection_title_display = collection_data.get('title', os.path.splitext(collection_filename)[0].replace('-', ' ').capitalize())
        xbmcplugin.setPluginCategory(KODI_HANDLE, collection_title_display); xbmcplugin.setContent(KODI_HANDLE, 'movies') 
        movies_in_collection = collection_data.get('movies', [])
        if not movies_in_collection:
            xbmcgui.Dialog().ok(ADDON_NAME, f"Kolekcija '{collection_title_display}' ne sadrži filmove."); end_directory(succeeded=True); return
        for movie_data in movies_in_collection:
            title = movie_data.get('title', "Nepoznat film"); thumb = movie_data.get('thumb'); plot = movie_data.get('plot'); year_val = movie_data.get('year')
            info = {'title': title, 'plot': plot, 'mediatype': 'movie'}
            if year_val: info['year'] = str(year_val)
            add_dir( title, { 'action': 'list_link_groups_for_item', 'content_type': content_type, 'category_id': category_id, 
                           'subfolder_name': collection_filename, 'file_name': title, 'item_title': title, 'item_thumb': thumb, 'is_collection_movie': 'true' },
                is_folder=False, is_playable=True, thumb=thumb, info_labels=info, total_items=len(movies_in_collection))
    except Exception as e:
        log_message(f"Greška pri čitanju filmova iz kolekcije {collection_filename} (open): {e}", xbmc.LOGERROR)
        import traceback; log_message(traceback.format_exc(), xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, f"Greška pri otvaranju kolekcije '{collection_filename}'."); end_directory(succeeded=False); return
    end_directory()

def list_titles_in_subfolder(content_type, category_id, subfolder_name):
    log_message(f"list_titles_in_subfolder: content_type={content_type}, category_id={category_id}, subfolder_name={subfolder_name}")
    source_info = CONTENT_SOURCES[content_type]; extracted_path_real = source_info['extracted_path']
    current_data_path = os.path.join(extracted_path_real, category_id, subfolder_name)
    categories_config = get_categories_config_from_zip(content_type)
    category_name_display = category_id.replace('-', ' ').capitalize()
    if category_id in categories_config and 'name' in categories_config[category_id]: category_name_display = categories_config[category_id]['name']
    xbmcplugin.setPluginCategory(KODI_HANDLE, f"{source_info['name']} - {category_name_display} - {subfolder_name}")
    is_series_category = category_id in ['serije', 'crtane-serije']
    xbmcplugin.setContent(KODI_HANDLE, 'tvshows' if is_series_category else 'movies')
    if not os.path.exists(current_data_path) or not os.path.isdir(current_data_path):
        log_message(f"Direktorijum {current_data_path} nije pronađen (os.path).", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, f"Nema sadržaja u '{subfolder_name}'."); end_directory(succeeded=True); return
    items_to_display = []
    for item_file in sorted(os.listdir(current_data_path)): 
        if item_file.endswith('.json'):
            item_full_path = os.path.join(current_data_path, item_file)
            try:
                with open(item_full_path, 'r', encoding='utf-8') as f: data = json.load(f)
                title = data.get('title', os.path.splitext(item_file)[0].replace('-', ' ').capitalize()); thumb = data.get('thumb'); plot = data.get('plot')
                year_val = data.get('year_info') if data.get('is_ongoing') else data.get('year'); info = {'title': title, 'plot': plot}
                if year_val: info['year'] = str(year_val)
                params = { 'content_type': content_type, 'category_id': category_id, 'subfolder_name': subfolder_name, 'file_name': item_file, 'item_title': title, 'item_thumb': thumb }
                item_is_folder_flag = False 
                if is_series_category: params['action'] = 'display_seasons'; info['mediatype'] = 'tvshow'; item_is_folder_flag = True 
                else: params['action'] = 'list_link_groups_for_item'; info['mediatype'] = 'movie'
                items_to_display.append({ 'name': title, 'params': params, 'is_folder': item_is_folder_flag, 'thumb': thumb, 'info': info })
            except Exception as e: log_message(f"Greška pri čitanju JSON fajla {item_file} u {current_data_path} (open): {e}", xbmc.LOGWARNING)
    if not items_to_display:
        xbmcgui.Dialog().ok(ADDON_NAME, f"Nema dostupnog sadržaja u '{subfolder_name}'."); end_directory(succeeded=True); return
    for item in items_to_display:
        add_dir( item['name'], item['params'], is_folder=item['is_folder'], is_playable=not item['is_folder'], thumb=item.get('thumb'), info_labels=item.get('info'), total_items=len(items_to_display) )
    end_directory()

def display_seasons_action(content_type, category_id, subfolder_name, file_name):
    log_message(f"display_seasons_action: file_name={file_name}")
    extracted_path_real = CONTENT_SOURCES[content_type]['extracted_path']
    file_full_path = os.path.join(extracted_path_real, category_id, subfolder_name, file_name)
    try:
        with open(file_full_path, 'r', encoding='utf-8') as f: data = json.load(f)
        series_title = data.get('title', "Serija")
        xbmcplugin.setPluginCategory(KODI_HANDLE, series_title); xbmcplugin.setContent(KODI_HANDLE, 'seasons') 
        seasons_data_raw = data.get('seasons', {}); seasons_data_dict = {}
        if isinstance(seasons_data_raw, list):
            for i, season_entry in enumerate(seasons_data_raw):
                s_num = season_entry.get('season_number', str(i + 1)); seasons_data_dict[str(s_num)] = season_entry
        elif isinstance(seasons_data_raw, dict): seasons_data_dict = seasons_data_raw
        else:
            log_message(f"Neočekivan format 'seasons' podatka za {file_name}: {type(seasons_data_raw)}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok(ADDON_NAME, f"Greška u formatu podataka o sezonama za '{series_title}'."); end_directory(succeeded=False); return
        if not seasons_data_dict:
            xbmcgui.Dialog().ok(ADDON_NAME, f"Nema sezona za seriju '{series_title}'."); end_directory(succeeded=True); return
        sorted_season_keys = sorted(seasons_data_dict.keys(), key=lambda x: int(x) if x.isdigit() else float('inf'))
        for season_num_str in sorted_season_keys:
            s_data = seasons_data_dict[season_num_str]; s_title = s_data.get('title', f"Sezona {season_num_str}"); s_thumb = s_data.get('thumb', data.get('thumb')) 
            info = { 'title': s_title, 'tvshowtitle': series_title, 'season': int(season_num_str) if season_num_str.isdigit() else 0, 'mediatype':'season' }
            add_dir( s_title, { 'action': 'display_episodes', 'content_type': content_type, 'category_id': category_id, 'subfolder_name': subfolder_name, 'file_name': file_name, 'season_num_str': season_num_str },
                is_folder=True, thumb=s_thumb, info_labels=info, total_items=len(sorted_season_keys) )
    except Exception as e:
        log_message(f"Greška pri čitanju sezona za {file_name} (open): {e}", xbmc.LOGERROR)
        import traceback; log_message(traceback.format_exc(), xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, "Greška pri učitavanju sezona."); end_directory(succeeded=False); return
    end_directory()

def display_episodes_action(content_type, category_id, subfolder_name, file_name, season_num_str):
    log_message(f"display_episodes_action: file_name={file_name}, season_num_str={season_num_str}")
    extracted_path_real = CONTENT_SOURCES[content_type]['extracted_path']
    file_full_path = os.path.join(extracted_path_real, category_id, subfolder_name, file_name)
    try:
        with open(file_full_path, 'r', encoding='utf-8') as f: data = json.load(f)
        series_title = data.get('title', "Serija"); seasons_data_raw = data.get('seasons', {}); seasons_data_dict = {}
        if isinstance(seasons_data_raw, list):
            for i, season_entry in enumerate(seasons_data_raw):
                s_num = season_entry.get('season_number', str(i + 1)); seasons_data_dict[str(s_num)] = season_entry
        elif isinstance(seasons_data_raw, dict): seasons_data_dict = seasons_data_raw
        current_season_data = seasons_data_dict.get(season_num_str)
        if not current_season_data:
            log_message(f"Sezona {season_num_str} nije pronađena u {file_name}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok(ADDON_NAME, f"Sezona {season_num_str} nije pronađena."); end_directory(succeeded=False); return
        season_title_display = current_season_data.get('title', f"Sezona {season_num_str}")
        xbmcplugin.setPluginCategory(KODI_HANDLE, f"{series_title} - {season_title_display}"); xbmcplugin.setContent(KODI_HANDLE, 'episodes') 
        episodes = current_season_data.get('episodes', [])
        if not episodes:
            xbmcgui.Dialog().ok(ADDON_NAME, f"Nema epizoda za {series_title} - {season_title_display}."); end_directory(succeeded=True); return 
        for ep_data in episodes:
            ep_num_raw = ep_data.get('episode_number'); ep_title = ep_data.get('title', f"Epizoda {ep_num_raw if ep_num_raw is not None else '#'}")
            ep_plot = ep_data.get('plot', data.get('plot')); ep_thumb = ep_data.get('thumb', current_season_data.get('thumb', data.get('thumb'))) 
            info = { 'title': ep_title, 'tvshowtitle': series_title, 'season': int(season_num_str) if season_num_str.isdigit() else 0,
                     'episode': int(ep_num_raw) if ep_num_raw is not None and str(ep_num_raw).isdigit() else 0, 'plot': ep_plot, 'mediatype':'episode' }
            add_dir( ep_title, { 'action': 'list_link_groups_for_item', 'content_type': content_type, 'category_id': category_id,
                              'subfolder_name': subfolder_name, 'file_name': file_name, 'season_num_str': season_num_str, 
                              'episode_num_str': str(ep_num_raw) if ep_num_raw is not None else "0", 'item_title': ep_title, 'item_thumb': ep_thumb },
                is_folder=False, is_playable=True, thumb=ep_thumb, info_labels=info, total_items=len(episodes) )
    except Exception as e:
        log_message(f"Greška pri čitanju epizoda za {file_name} S{season_num_str} (open): {e}", xbmc.LOGERROR)
        import traceback; log_message(traceback.format_exc(), xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, "Greška pri učitavanju epizoda."); end_directory(succeeded=False); return
    end_directory()

def list_link_groups_for_item_action(content_type, category_id, subfolder_name, file_name, item_title, item_thumb, season_num_str=None, episode_num_str=None, is_collection_movie=None):
    log_message(f"list_link_groups_for_item_action: item_title='{item_title}', is_collection_movie='{is_collection_movie}', file_name='{file_name}', subfolder_name='{subfolder_name}'")
    extracted_path_real = CONTENT_SOURCES[content_type]['extracted_path']; main_json_file_path = ""; movie_title_to_find_in_collection = None 
    if is_collection_movie == 'true':
        main_json_file_path = os.path.join(extracted_path_real, category_id, subfolder_name); movie_title_to_find_in_collection = file_name
    else: main_json_file_path = os.path.join(extracted_path_real, category_id, subfolder_name, file_name)
    display_item_title_for_dialog = item_title
    if season_num_str and episode_num_str and not (is_collection_movie == 'true'): 
        try:
            with open(main_json_file_path, 'r', encoding='utf-8') as f_series_title_check: series_data_for_title = json.load(f_series_title_check)
            actual_series_title = series_data_for_title.get('title', "Serija")
            display_item_title_for_dialog = f"{actual_series_title} S{season_num_str.zfill(2)}E{episode_num_str.zfill(2)} - {item_title}"
        except Exception as e_title: 
            log_message(f"Mala greška pri formatiranju naslova za dijalog (open): {e_title}", xbmc.LOGINFO)
    xbmcplugin.setPluginCategory(KODI_HANDLE, f"Linkovi za: {display_item_title_for_dialog}") 
    try:
        with open(main_json_file_path, 'r', encoding='utf-8') as f_main_json: data_main_json = json.load(f_main_json)
        item_data_with_links = None 
        if is_collection_movie == 'true':
            found_movie_in_collection = False
            for movie_in_coll in data_main_json.get('movies', []): 
                if movie_in_coll.get('title') == movie_title_to_find_in_collection: item_data_with_links = movie_in_coll; found_movie_in_collection = True; break
            if not found_movie_in_collection: xbmcgui.Dialog().ok(ADDON_NAME, f"Film '{movie_title_to_find_in_collection}' nije pronađen u kolekciji."); end_directory(succeeded=False); return 
        elif season_num_str and episode_num_str: 
            seasons_data_raw = data_main_json.get('seasons', {}); seasons_data_dict = {}
            if isinstance(seasons_data_raw, list):
                for i, season_entry in enumerate(seasons_data_raw): s_num = season_entry.get('season_number', str(i + 1)); seasons_data_dict[str(s_num)] = season_entry
            elif isinstance(seasons_data_raw, dict): seasons_data_dict = seasons_data_raw
            current_season_data = seasons_data_dict.get(season_num_str)
            if current_season_data:
                found_episode = False
                for ep in current_season_data.get('episodes', []):
                    if str(ep.get('episode_number')) == episode_num_str: item_data_with_links = ep; found_episode = True; break
                if not found_episode: xbmcgui.Dialog().ok(ADDON_NAME, f"Epizoda S{season_num_str}E{episode_num_str} nije pronađena."); end_directory(succeeded=False); return
            else: xbmcgui.Dialog().ok(ADDON_NAME, f"Sezona {season_num_str} nije pronađena."); end_directory(succeeded=False); return
        else: item_data_with_links = data_main_json 
        if item_data_with_links is None: 
            log_message(f"Nisu pronađeni podaci za linkove za: {item_title}", xbmc.LOGERROR); xbmcgui.Dialog().ok(ADDON_NAME, "Greška: Nisu pronađeni podaci za linkove."); end_directory(succeeded=False); return
        link_groups_from_json = item_data_with_links.get('link_groups', {})
        if not link_groups_from_json: xbmcgui.Dialog().ok(ADDON_NAME, f"Nema dostupnih linkova za '{item_title}'."); end_directory(succeeded=True); return 
        available_links_for_dialog = []; link_urls_for_dialog = []; defined_link_group_order = ['glavni', 'alternativni_1', 'alternativni_2'] 
        for group_id in defined_link_group_order:
            if group_id in link_groups_from_json:
                links_or_url = link_groups_from_json[group_id]; display_name_prefix = LINK_GROUP_DISPLAY_NAMES.get(group_id, group_id.replace('_',' ').capitalize())
                if isinstance(links_or_url, list): 
                    for i, link_url_item in enumerate(links_or_url):
                        if link_url_item and isinstance(link_url_item, str): available_links_for_dialog.append(f"{display_name_prefix} ({i+1})"); link_urls_for_dialog.append(link_url_item)
                elif isinstance(links_or_url, str) and links_or_url: available_links_for_dialog.append(display_name_prefix); link_urls_for_dialog.append(links_or_url)
        if not available_links_for_dialog: xbmcgui.Dialog().ok(ADDON_NAME, f"Nema validnih URL-ova u link grupama za '{item_title}'."); end_directory(succeeded=True); return
        dialog = xbmcgui.Dialog(); selected_index = dialog.select(f"Izaberite link za: {display_item_title_for_dialog}", available_links_for_dialog)
        if selected_index == -1: 
            log_message("Korisnik otkazao izbor linka."); li_cancel = xbmcgui.ListItem(label=display_item_title_for_dialog)
            if item_thumb: li_cancel.setArt({'thumb': item_thumb, 'icon': item_thumb})
            xbmcplugin.setResolvedUrl(KODI_HANDLE, False, listitem=li_cancel); return 
        chosen_url = link_urls_for_dialog[selected_index]; play_video_action(chosen_url, display_item_title_for_dialog, item_thumb)
    except Exception as e:
        log_message(f"Greška pri listanju link grupa za '{item_title}' (open): {e}", xbmc.LOGERROR)
        import traceback; log_message(traceback.format_exc(), xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, f"Došlo je do greške pri prikazu linkova za '{item_title}'.")
        li_error = xbmcgui.ListItem(label=display_item_title_for_dialog)
        if item_thumb: li_error.setArt({'thumb': item_thumb, 'icon': item_thumb})
        xbmcplugin.setResolvedUrl(KODI_HANDLE, False, listitem=li_error)

def play_video_action(url, title_for_player, thumb_for_player=None):
    log_message(f"play_video_action: POČETAK za '{title_for_player}' - URL za obradu: {url}")
    list_item = xbmcgui.ListItem(label=title_for_player, path=url); list_item.setProperty('IsPlayable', 'true') 
    info_labels = {'title': title_for_player, 'mediatype': 'video'}; list_item.setInfo(type='video', infoLabels=info_labels)
    if thumb_for_player: list_item.setArt({'thumb': thumb_for_player, 'icon': thumb_for_player})
    final_url_to_play = url; busy_dialog_active = False 
    if RESOLVEURL_AVAILABLE:
        try:
            log_message(f"Pokušaj razrešavanja sa ResolveURL za: {url}"); hmf = resolveurl.HostedMediaFile(url=url) 
            if hmf and hmf.valid_url():
                log_message(f"play_video_action: ResolveURL: URL '{url}' je validan."); xbmc.executebuiltin("ActivateWindow(busydialognocancel)"); busy_dialog_active = True
                log_message("play_video_action: ResolveURL: Pozivanje hmf.resolve()..."); resolved_url_temp = hmf.resolve()
                if busy_dialog_active: xbmc.executebuiltin("Dialog.Close(busydialognocancel, true)"); busy_dialog_active = False
                if resolved_url_temp and isinstance(resolved_url_temp, str): 
                    final_url_to_play = resolved_url_temp; log_message(f"play_video_action: ResolveURL uspješno vratio: {final_url_to_play}"); list_item.setPath(final_url_to_play) 
                elif resolved_url_temp is False: 
                    log_message(f"play_video_action: ResolveURL nije uspeo (vratio False): {url}", xbmc.LOGWARNING)
                    xbmcgui.Dialog().ok(ADDON_NAME, "Nije moguće razrešiti link (ResolveURL greška)."); xbmcplugin.setResolvedUrl(KODI_HANDLE, False, listitem=list_item); return
                else: log_message(f"play_video_action: ResolveURL vratio neočekivano za: {url}. Direktno puštanje.", xbmc.LOGWARNING)
            else: log_message(f"play_video_action: ResolveURL ne prepoznaje hoster za: {url}. Direktno puštanje.", xbmc.LOGINFO)
        except TypeError as te: 
            log_message(f"play_video_action: TypeError sa ResolveURL: {te}", xbmc.LOGERROR)
            if busy_dialog_active: xbmc.executebuiltin("Dialog.Close(busydialognocancel, true)")
            xbmcgui.Dialog().notification(ADDON_NAME, "Problem ResolveURL config, pokušaj direktno.", xbmcgui.NOTIFICATION_WARNING, 3000)
        except Exception as e_resolve:
            log_message(f"play_video_action: Neočekivana greška ResolveURL za '{url}': {e_resolve}", xbmc.LOGERROR)
            import traceback; log_message(traceback.format_exc(), xbmc.LOGERROR)
            if busy_dialog_active: xbmc.executebuiltin("Dialog.Close(busydialognocancel, true)")
            xbmcgui.Dialog().notification(ADDON_NAME, "Greška ResolveURL, pokušaj direktno.", xbmcgui.NOTIFICATION_WARNING, 3000)
    else: log_message("play_video_action: ResolveURL nije dostupan. Direktno puštanje.", xbmc.LOGINFO)
    log_message(f"play_video_action: Prosleđivanje Kodi plejeru za '{title_for_player}': URL='{final_url_to_play}'")
    xbmcplugin.setResolvedUrl(KODI_HANDLE, True, listitem=list_item); log_message(f"play_video_action: Pozvan setResolvedUrl za '{title_for_player}'")

def prompt_search_action():
    log_message("POZIV: prompt_search_action"); keyboard = xbmc.Keyboard('', 'Unesite pojam za pretragu'); keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():
        query = keyboard.getText().strip() 
        if not query:
            log_message("Pretraga otkazana - prazan unos.", xbmc.LOGINFO)
            xbmcgui.Dialog().notification(ADDON_NAME, "Unos za pretragu ne može biti prazan.", xbmcgui.NOTIFICATION_INFO, 2000)
            xbmcplugin.setPluginCategory(KODI_HANDLE, "Pretraga"); end_directory(succeeded=True); return 
        log_message(f"Korisnik uneo za pretragu: {query}. Pozivam perform_search_action."); perform_search_action(query)
    else: log_message("Pretraga otkazana."); xbmcplugin.setPluginCategory(KODI_HANDLE, "Pretraga"); end_directory(succeeded=True) 

def perform_search_action(query):
    log_message(f"POZIV: perform_search_action, query='{query}'")
    if not query: 
        log_message("Prazan upit za pretragu primljen u perform_search_action.", xbmc.LOGWARNING)
        xbmcgui.Dialog().ok(ADDON_NAME, "Pojam za pretragu nije validan."); end_directory(succeeded=False); return
    results = []; search_query_lower = query.lower()
    xbmcplugin.setPluginCategory(KODI_HANDLE, f"Rezultati pretrage za: '{query}'"); xbmcplugin.setContent(KODI_HANDLE, 'videos') 
    for content_type, source_config in CONTENT_SOURCES.items():
        extracted_path = source_config['extracted_path']
        if not os.path.exists(extracted_path) or not os.path.isdir(extracted_path):
            log_message(f"Izvor '{content_type}' nema validan extracted_path (os.path): {extracted_path}", xbmc.LOGINFO); continue
        try:
            if not os.listdir(extracted_path):
                log_message(f"Izvor '{content_type}' extracted_path je prazan (os.listdir): {extracted_path}", xbmc.LOGINFO); continue
        except OSError as e_list: 
            log_message(f"Greška pri čitanju {extracted_path} za '{content_type}' (os.listdir): {e_list}", xbmc.LOGWARNING); continue
        log_message(f"Pretražujem izvor: {content_type}"); categories_config = get_categories_config_from_zip(content_type)
        for cat_id, cat_details_unused in categories_config.items():
            category_data_path = os.path.join(extracted_path, cat_id)
            if not os.path.exists(category_data_path) or not os.path.isdir(category_data_path): continue
            try:
                dir_content_cat = sorted(os.listdir(category_data_path))
            except OSError: continue
            if cat_id == 'kolekcije':
                for collection_filename in dir_content_cat:
                    if collection_filename.endswith('.json'):
                        collection_file_path = os.path.join(category_data_path, collection_filename)
                        if not os.path.isfile(collection_file_path): continue
                        try:
                            with open(collection_file_path, 'r', encoding='utf-8') as f_coll: coll_data = json.load(f_coll)
                            collection_display_title = coll_data.get('title', os.path.splitext(collection_filename)[0].replace('-', ' ').capitalize())
                            for movie_data in coll_data.get('movies', []):
                                movie_title = movie_data.get('title', '')
                                if search_query_lower in movie_title.lower():
                                    year_val = movie_data.get('year'); plot_val = movie_data.get('plot'); thumb_val = movie_data.get('thumb')
                                    info = {'title': movie_title, 'plot': plot_val, 'mediatype': 'movie'}
                                    if year_val: info['year'] = str(year_val)
                                    results.append({ 'name': f"{movie_title} (Kolekcija: {collection_display_title})",
                                        'params': { 'action': 'list_link_groups_for_item', 'content_type': content_type, 'category_id': cat_id,
                                                    'subfolder_name': collection_filename, 'file_name': movie_title, 
                                                    'item_title': movie_title, 'item_thumb': thumb_val, 'is_collection_movie': 'true' },
                                        'is_folder': False, 'is_playable': True, 'thumb': thumb_val, 'info': info })
                        except Exception as e_s_coll: log_message(f"Greška pretrage kolekcije {collection_filename} (open): {e_s_coll}", xbmc.LOGWARNING)
            elif cat_id in ['serije', 'crtane-serije', 'filmovi', 'crtani-filmovi']:
                for subfolder_name_iter in dir_content_cat:
                    items_subfolder_path = os.path.join(category_data_path, subfolder_name_iter)
                    if os.path.isdir(items_subfolder_path):
                        try:
                            for item_filename in sorted(os.listdir(items_subfolder_path)):
                                if item_filename.endswith('.json'):
                                    item_file_path = os.path.join(items_subfolder_path, item_filename)
                                    if not os.path.isfile(item_file_path): continue
                                    try:
                                        with open(item_file_path, 'r', encoding='utf-8') as f_item: item_data = json.load(f_item)
                                        item_display_title = item_data.get('title', '')
                                        if search_query_lower in item_display_title.lower():
                                            year_val = item_data.get('year_info') if item_data.get('is_ongoing') else item_data.get('year')
                                            plot_val = item_data.get('plot'); thumb_val = item_data.get('thumb')
                                            if cat_id in ['serije', 'crtane-serije']:
                                                info = {'title': item_display_title, 'plot': plot_val, 'mediatype': 'tvshow'}
                                                if year_val: info['year'] = str(year_val)
                                                results.append({ 'name': item_display_title,
                                                    'params': { 'action': 'display_seasons', 'content_type': content_type, 'category_id': cat_id,
                                                                'subfolder_name': subfolder_name_iter, 'file_name': item_filename,
                                                                'item_title': item_display_title, 'item_thumb': thumb_val },
                                                    'is_folder': True, 'is_playable': False, 'thumb': thumb_val, 'info': info })
                                            else: 
                                                info = {'title': item_display_title, 'plot': plot_val, 'mediatype': 'movie'}
                                                if year_val: info['year'] = str(year_val)
                                                results.append({ 'name': item_display_title,
                                                    'params': { 'action': 'list_link_groups_for_item', 'content_type': content_type, 'category_id': cat_id,
                                                                'subfolder_name': subfolder_name_iter, 'file_name': item_filename,
                                                                'item_title': item_display_title, 'item_thumb': thumb_val },
                                                    'is_folder': False, 'is_playable': True, 'thumb': thumb_val, 'info': info })
                                    except Exception as e_s_item: log_message(f"Greška pretrage stavke {item_filename} (open): {e_s_item}", xbmc.LOGWARNING)
                        except OSError: pass
    if not results:
        xbmcgui.Dialog().ok(ADDON_NAME, f"Nema rezultata za traženi pojam: '{query}'"); end_directory(succeeded=True); return
    for res_item in results:
        add_dir( name=res_item['name'], params=res_item['params'], is_folder=res_item['is_folder'], 
                 thumb=res_item.get('thumb'), info_labels=res_item.get('info'), 
                 total_items=len(results), is_playable=res_item['is_playable'] )
    end_directory(succeeded=True)

def router(paramstring):
    params = dict(parse_qsl(paramstring.lstrip('?')))
    action = params.get('action')
    log_message(f"RUTER (android_logic.py pozvan): Akcija='{action}', Parametri='{params}'")
    content_type = params.get('content_type'); category_id = params.get('category_id')
    subfolder_name = params.get('subfolder_name'); file_name = params.get('file_name') 
    season_num_str = params.get('season_num_str'); episode_num_str = params.get('episode_num_str') 
    item_title = params.get('item_title'); item_thumb = params.get('item_thumb')
    is_collection_movie = params.get('is_collection_movie'); collection_filename = params.get('collection_filename') 
    query_param = params.get('query')

    if action is None: main_menu()
    elif action == 'list_categories' and content_type: list_categories_for_type(content_type)
    elif action == 'list_items_in_category' and content_type and category_id: list_items_in_category(content_type, category_id)
    elif action == 'manual_update_selection': manual_update_selection()
    elif action == 'force_specific_update' and content_type: force_specific_update(content_type)
    elif action == 'display_collection_movies' and content_type and category_id == 'kolekcije' and collection_filename: display_collection_movies(content_type, category_id, collection_filename)
    elif action == 'list_titles_in_subfolder' and content_type and category_id and subfolder_name: list_titles_in_subfolder(content_type, category_id, subfolder_name)
    elif action == 'display_seasons' and content_type and category_id and subfolder_name and file_name: display_seasons_action(content_type, category_id, subfolder_name, file_name)
    elif action == 'display_episodes' and content_type and category_id and subfolder_name and file_name and season_num_str: display_episodes_action(content_type, category_id, subfolder_name, file_name, season_num_str)
    elif action == 'list_link_groups_for_item':
        if all(p is not None for p in [content_type, category_id, subfolder_name, file_name, item_title]):
             list_link_groups_for_item_action(content_type, category_id, subfolder_name, file_name,item_title, item_thumb,season_num_str, episode_num_str, is_collection_movie)
        else:
            log_message(f"Nedostaju parametri za 'list_link_groups_for_item' u android_logic: {params}", xbmc.LOGWARNING)
            li_err = xbmcgui.ListItem("Greška parametara"); xbmcplugin.setResolvedUrl(KODI_HANDLE, False, li_err)
    elif action == 'prompt_search': prompt_search_action()
    elif action == 'perform_search' and query_param: perform_search_action(query_param)
    elif action == 'perform_search':
        log_message("Akcija 'perform_search' pozvana bez 'query' parametra u ruteru.", xbmc.LOGWARNING)
        end_directory(succeeded=False)
    else:
        log_message(f"Nepoznata akcija ili nedostaju parametri: action='{action}', params='{params}'", xbmc.LOGWARNING)
        end_directory(succeeded=False)

# if __name__ == '__main__':
# pass