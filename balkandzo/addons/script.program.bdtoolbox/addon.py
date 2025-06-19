# -*- coding: utf-8 -*-

import sys
import os
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import xbmcplugin
import json
import zipfile
import shutil
import re
import datetime
import urllib.request
import platform
import subprocess
import time 
from urllib.parse import parse_qsl

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path')

HOME_PATH = 'special://home/'
USERDATA_PATH = 'special://userdata/'
ADDON_DATA_PATH = 'special://userdata/addon_data/'
ADDONS_PATH = 'special://home/addons/'
TEMP_PATH = 'special://home/temp/'
THUMBNAILS_PATH = 'special://userdata/Thumbnails/'
LOG_PATH = 'special://logpath/'
PACKAGES_PATH = 'special://home/addons/packages/'

def android_tools_menu():
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=f"plugin://{ADDON_ID}/?action=android_kodi_settings", listitem=xbmcgui.ListItem("Otvori App Info za Kodi"), isFolder=False)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=f"plugin://{ADDON_ID}/?action=android_wifi_settings", listitem=xbmcgui.ListItem("Otvori Wi-Fi Podešavanja"), isFolder=False)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=f"plugin://{ADDON_ID}/?action=android_reboot_recovery", listitem=xbmcgui.ListItem("[COLOR red]Reboot u Recovery (zahteva Root)[/COLOR]"), isFolder=False)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=f"plugin://{ADDON_ID}/?action=android_reboot_bootloader", listitem=xbmcgui.ListItem("[COLOR red]Reboot u Bootloader (zahteva Root)[/COLOR]"), isFolder=False)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def android_open_kodi_settings():
    xbmc.executebuiltin('StartAndroidActivity("","android.settings.APPLICATION_DETAILS_SETTINGS","package:org.xbmc.kodi")')

def android_open_wifi_settings():
    xbmc.executebuiltin('StartAndroidActivity("","android.settings.WIFI_SETTINGS")')

def android_reboot_recovery():
    dialog = xbmcgui.Dialog()
    if dialog.yesno("UPOZORENJE", "Ova akcija će restartovati vaš uređaj u Recovery mod.\nOvo radite na sopstvenu odgovornost!\n\nDa li ste sigurni?"):
        os.system('su -c reboot recovery')

def android_reboot_bootloader():
    dialog = xbmcgui.Dialog()
    if dialog.yesno("UPOZORENJE", "Ova akcija će restartovati vaš uređaj u Bootloader/Fastboot mod.\nOvo radite na sopstvenu odgovornost!\n\nDa li ste sigurni?"):
        os.system('su -c reboot bootloader')

def get_cpu_info_linux():
    info = []
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if "model name" in line or "Hardware" in line:
                    model = line.split(':')[1].strip()
                    info.append(f" CPU Model: [B]{model}[/B]")
                    break
    except Exception:
        info.append(" CPU Model: [COLOR red]Nije moguće očitati[/COLOR]")
    
    try:
        with open('/proc/stat', 'r') as f:
            line1 = f.readline()
        
        time.sleep(1)
        
        with open('/proc/stat', 'r') as f:
            line2 = f.readline()
            
        parts1 = [int(p) for p in line1.split()[1:]]
        parts2 = [int(p) for p in line2.split()[1:]]
        
        prev_idle = parts1[3] + parts1[4]
        idle = parts2[3] + parts2[4]
        
        prev_total = sum(parts1)
        total = sum(parts2)
        
        total_diff = total - prev_total
        idle_diff = idle - prev_idle
        
        cpu_usage = (1000 * (total_diff - idle_diff) / total_diff + 5) / 10
        info.append(f" CPU Iskorišćenost: [B]{cpu_usage:.1f} %[/B]")
    except Exception:
        info.append(" CPU Iskorišćenost: [COLOR red]Nije moguće očitati[/COLOR]")
        
    return info

def display_system_status():
    dialog = xbmcgui.Dialog()
    progress = xbmcgui.DialogProgress()
    progress.create(ADDON_NAME, "Prikupljam informacije o sistemu...")
    info_lines = []
    try:
        progress.update(25, "Prikupljam mrežne i sistemske podatke...")
        info_lines.append("[COLOR yellow]-- MREŽA --[/COLOR]")
        info_lines.append(f" Interna IP Adresa: [B]{xbmc.getInfoLabel('Network.IPAddress')}[/B]")
        try:
            ext_ip = urllib.request.urlopen('https://api.ipify.org', timeout=5).read().decode('utf-8')
            info_lines.append(f" Eksterna IP Adresa: [B]{ext_ip}[/B]")
        except Exception: info_lines.append(" Eksterna IP Adresa: [COLOR red]Nedostupna[/COLOR]")
        
        info_lines.append("\n[COLOR yellow]-- KODI SISTEM --[/COLOR]")
        info_lines.append(f" Verzija Kodi-ja: [B]{xbmc.getInfoLabel('System.BuildVersion')}[/B]")
        info_lines.append(f" Skin: [B]{xbmc.getSkinDir()}[/B]")
        
        progress.update(50, "Prikupljam hardverske podatke...")
        info_lines.append("\n[COLOR yellow]-- HARDVER --[/COLOR]")
        
        os_name = platform.system()
        if xbmc.getCondVisibility('System.Platform.Android'):
            os_name = "Android"
        info_lines.append(f" OS: [B]{os_name} {platform.release()}[/B]")

        try:
            real_userdata_path = xbmcvfs.translatePath(USERDATA_PATH)
            total, used, free = shutil.disk_usage(real_userdata_path)
            free_space_gb = free / (1024**3)
            info_lines.append(f" Slobodan Prostor: [B]{free_space_gb:.2f} GB[/B]")
        except Exception as e: info_lines.append(f" Slobodan Prostor: [COLOR red]Nije moguće očitati ({e})[/COLOR]")
        
        progress.update(75, "Analiziram RAM i CPU...")
        if platform.system() == 'Linux':
            try:
                with open('/proc/meminfo', 'r') as f: lines = f.readlines()
                mem_info = {line.split(':')[0]: int(line.split(':')[1].strip().split(' ')[0]) for line in lines}
                total_ram = mem_info.get('MemTotal', 0) / (1024**2); available_ram = mem_info.get('MemAvailable', 0) / (1024**2)
                used_percent = ((total_ram - available_ram) / total_ram) * 100 if total_ram > 0 else 0
                info_lines.append(f" RAM Memorija: [B]{available_ram:.2f} GB slobodno od {total_ram:.2f} GB ({used_percent:.0f} % iskorišćeno)[/B]")
                
                info_lines.extend(get_cpu_info_linux())
            except Exception as e:
                info_lines.append(f" RAM/CPU (Linux): [COLOR red]Greška pri očitavanju ({e})[/COLOR]")
        else:
            info_lines.append(" RAM/CPU: [COLOR yellow]Nije podržano na ovom OS-u[/COLOR]")

        progress.close()
        dialog.textviewer("Status Sistema", "\n".join(info_lines))
    except Exception as e:
        if not progress.iscanceled(): progress.close()
        dialog.ok(ADDON_NAME, f"Došlo je do greške pri prikupljanju informacija:\n{e}")

def list_addons():
    rpc_request = { "jsonrpc": "2.0", "method": "Addons.GetAddons", "params": { "properties": ["name", "version", "author", "enabled"] }, "id": 1 }
    rpc_response_str = xbmc.executeJSONRPC(json.dumps(rpc_request))
    rpc_response = json.loads(rpc_response_str)
    if 'result' in rpc_response and 'addons' in rpc_response['result']:
        for addon in rpc_response['result']['addons']:
            li = xbmcgui.ListItem(f"{addon['name']} - {'[COLOR green]Omogućen[/COLOR]' if addon['enabled'] else '[COLOR red]Onemogućen[/COLOR]'}")
            url = f"plugin://{ADDON_ID}/?action=toggle_addon&id={addon['addonid']}&current_status={addon['enabled']}"
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=False)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))
def toggle_addon(addon_id, current_status):
    dialog = xbmcgui.Dialog(); new_status = not (current_status == 'True'); action_text = "onemogućiti" if new_status is False else "omogućiti"
    if dialog.yesno("Potvrda", f"Da li ste sigurni da želite {action_text} addon '{addon_id}'?"):
        rpc_request = { "jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": { "addonid": addon_id, "enabled": new_status }, "id": 1 }
        xbmc.executeJSONRPC(json.dumps(rpc_request)); xbmc.sleep(500); dialog.notification(ADDON_NAME, f"Addon '{addon_id}' je sada {'omogućen' if new_status else 'onemogućen'}.", xbmcgui.NOTIFICATION_INFO, 3000); xbmc.executebuiltin("Container.Refresh")
def file_explorer(path=None):
    if path is None: path = HOME_PATH
    real_path = xbmcvfs.translatePath(path)
    try: dirs, files = xbmcvfs.listdir(real_path)
    except Exception as e: xbmcgui.Dialog().ok(ADDON_NAME, f"Nije moguće pristupiti putanji:\n{path}\n\nGreška: {e}"); return
    if path.rstrip('/') != HOME_PATH.rstrip('/'):
        parent_path = '/'.join(path.rstrip('/').split('/')[:-1]) + '/'; li = xbmcgui.ListItem('..'); url = f"plugin://{ADDON_ID}/?action=file_explorer&path={parent_path}"
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=True)
    for d in sorted(dirs):
        child_path = f"{path.rstrip('/')}/{d}/"; li = xbmcgui.ListItem(f"[DIR] {d}"); url = f"plugin://{ADDON_ID}/?action=file_explorer&path={child_path}"
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=True)
    for f in sorted(files):
        file_path = f"{path.rstrip('/')}/{f}"; li = xbmcgui.ListItem(f); li.addContextMenuItems([('Obriši fajl', f'RunPlugin(plugin://{ADDON_ID}/?action=delete_file&path={file_path})')])
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url="", listitem=li, isFolder=False)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))
def delete_file(path):
    dialog = xbmcgui.Dialog()
    if dialog.yesno("Potvrda", f"Da li ste sigurni da želite obrisati fajl:\n{path}?"):
        if xbmcvfs.delete(path): dialog.notification(ADDON_NAME, "Fajl obrisan.", xbmcgui.NOTIFICATION_INFO, 2000); xbmc.executebuiltin("Container.Refresh")
        else: dialog.notification(ADDON_NAME, "Greška pri brisanju fajla.", xbmcgui.NOTIFICATION_ERROR, 2000)
def backup_addons():
    dialog = xbmcgui.Dialog(); selected_folder = dialog.browseSingle(3, "Izaberite FOLDER za čuvanje kompletnog Kodi backup-a", "files")
    if not selected_folder: return
    default_name = f"Kodi_Full_Backup_{datetime.datetime.now().strftime('%Y-%m-%d')}.zip"; typed_name = dialog.input("Unesite ime fajla za backup", default_name)
    if not typed_name: return
    real_folder_path = xbmcvfs.translatePath(selected_folder); backup_path = os.path.join(real_folder_path, typed_name)
    progress_dialog = xbmcgui.DialogProgress(); progress_dialog.create(ADDON_NAME, "Priprema za kreiranje kompletnog backup-a...")
    try:
        real_home_path = xbmcvfs.translatePath(HOME_PATH); real_userdata_path = xbmcvfs.translatePath(USERDATA_PATH); real_addons_path = xbmcvfs.translatePath(ADDONS_PATH)
        folders_to_backup = []
        if xbmcvfs.exists(USERDATA_PATH): folders_to_backup.append({'name': 'userdata', 'path': real_userdata_path})
        if xbmcvfs.exists(ADDONS_PATH): folders_to_backup.append({'name': 'addons', 'path': real_addons_path})
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            total_items = len(folders_to_backup)
            for i, folder_info in enumerate(folders_to_backup):
                folder_name = folder_info['name']; folder_path = folder_info['path']
                progress_dialog.update(int((i / total_items) * 100), f"Arhiviram folder: {folder_name}...")
                for root, dirs, files in os.walk(folder_path):
                    if ADDON_ID in root: continue
                    for file in files: file_path = os.path.join(root, file); arcname = os.path.relpath(file_path, real_home_path); zipf.write(file_path, arcname)
        progress_dialog.close(); dialog.ok(ADDON_NAME, f"Kompletan Kodi backup je uspešno kreiran:\n{backup_path}")
    except Exception as e:
        progress_dialog.close(); xbmc.log(f"BDTOOLBOX Backup Error: {e}", level=xbmc.LOGERROR); dialog.ok(ADDON_NAME, f"Došlo je do greške prilikom backup-a:\n{e}")
def restore_addons():
    dialog = xbmcgui.Dialog(); zip_path = dialog.browseSingle(1, "Izaberite backup ZIP fajl za vraćanje", "files", ".zip")
    if not zip_path: return
    warning_title = "[B]UPOZORENJE - KOMPLETAN RESTORE[/B]"; warning_text = ("Ova akcija će u potpunosti PREGAZITI SVA vaša trenutna Kodi podešavanja, biblioteku, skin i addone sa onima iz backup-a.\n\n[B]OVAJ PROCES SE NE MOŽE PONIŠTITI![/B]\n\nDa li ste apsolutno sigurni da želite da nastavite?")
    if not dialog.yesno(warning_title, warning_text): return
    progress_dialog = xbmcgui.DialogProgress(); progress_dialog.create(ADDON_NAME, "Vraćanje kompletnog backup-a...")
    try:
        real_home_path = xbmcvfs.translatePath(HOME_PATH)
        with zipfile.ZipFile(zip_path, 'r') as zipf: zipf.extractall(real_home_path)
        progress_dialog.close(); dialog.ok(ADDON_NAME, "Backup uspešno vraćen.\nKodi će sada biti prisilno zatvoren. Molimo pokrenite ga ponovo.")
        xbmc.executebuiltin('Quit()')
    except Exception as e:
        progress_dialog.close(); dialog.ok(ADDON_NAME, f"Došlo je do greške:\n{e}")
def run_speedtest():
    lib_path = os.path.join(xbmcvfs.translatePath(ADDON_PATH), 'lib')
    if lib_path not in sys.path: sys.path.insert(0, lib_path)
    dialog = xbmcgui.DialogProgress(); dialog.create(ADDON_NAME, "Pokretanje speed testa...")
    try:
        if not hasattr(sys.stdout, 'fileno'): sys.stdout.fileno = lambda: 1
        if not hasattr(sys.stderr, 'fileno'): sys.stderr.fileno = lambda: 2
        import speedtest
        dialog.update(0, "Inicijalizacija..."); s = speedtest.Speedtest(); dialog.update(33, "Tražim najbolji server..."); s.get_best_server(); dialog.update(66, "Testiram brzinu preuzimanja (Download)..."); s.download(); dialog.update(100, "Testiram brzinu slanja (Upload)..."); s.upload(); dialog.close()
        results = s.results.dict(); download_speed = results["download"] / 10**6; upload_speed = results["upload"] / 10**6; ping = results["ping"]; server_name = results["server"]["name"]; server_location = results["server"]["country"]
        result_text = (f"Download: [B]{download_speed:.2f} Mbit/s[/B]\n" f"Upload: [B]{upload_speed:.2f} Mbit/s[/B]\n" f"Ping: [B]{ping:.2f} ms[/B]\n\n" f"Server: {server_name} ({server_location})")
        xbmcgui.Dialog().ok("Rezultati Speed Testa", result_text)
    except ImportError:
        dialog.close(); xbmcgui.Dialog().ok(ADDON_NAME, "Greška: Modul 'speedtest.py' nije pronađen!\n\nProverite da li se fajl nalazi u 'lib' folderu unutar addona.")
    except Exception as e:
        dialog.close(); xbmc.log(f"BDTOOLBOX: Greška u speedtest-cli: {e}", level=xbmc.LOGERROR); xbmcgui.Dialog().ok(ADDON_NAME, f"Test nije uspeo. Greška:\n{e}")
def maintenance_db():
    dialog = xbmcgui.Dialog()
    if dialog.yesno(ADDON_NAME, "Ova operacija će optimizovati (kompaktovati) vaše baze podataka za video i muziku. Može potrajati nekoliko trenutaka.\n\nDa li želite da nastavite?"):
        dialog.notification(ADDON_NAME, "Optimizacija baze podataka je počela...", xbmcgui.NOTIFICATION_INFO, 2000)
        xbmc.executebuiltin("CompactVideoDatabase"); xbmc.executebuiltin("CompactMusicDatabase"); xbmc.sleep(1000)
        dialog.ok(ADDON_NAME, "Baze podataka su uspešno optimizovane.")
def clean_packages():
    dialog = xbmcgui.Dialog(); real_packages_path = xbmcvfs.translatePath(PACKAGES_PATH)
    if not xbmcvfs.exists(real_packages_path):
        dialog.notification(ADDON_NAME, "Packages folder ne postoji.", xbmcgui.NOTIFICATION_INFO, 2000); return
    if dialog.yesno("Potvrda", "Obrisaće se svi preuzeti paketi dodataka. Ovo je sigurno uraditi.\nNastavi?"):
        try: shutil.rmtree(real_packages_path); os.makedirs(real_packages_path); dialog.notification(ADDON_NAME, "Packages folder očišćen.", xbmcgui.NOTIFICATION_INFO, 2000)
        except Exception as e: dialog.notification(ADDON_NAME, f"Greška pri čišćenju packages: {e}", xbmcgui.NOTIFICATION_ERROR, 3000)
def clean_cache():
    real_temp_path = xbmcvfs.translatePath(TEMP_PATH)
    if xbmcvfs.exists(real_temp_path):
        try: shutil.rmtree(real_temp_path); os.makedirs(real_temp_path); xbmcgui.Dialog().notification(ADDON_NAME, "Cache očišćen.", xbmcgui.NOTIFICATION_INFO, 2000)
        except Exception as e: xbmcgui.Dialog().notification(ADDON_NAME, f"Greška pri čišćenju cache-a: {e}", xbmcgui.NOTIFICATION_ERROR, 2000)
def clean_thumbnails():
    real_thumbnails_path = xbmcvfs.translatePath(THUMBNAILS_PATH)
    if xbmcvfs.exists(real_thumbnails_path):
        try: shutil.rmtree(real_thumbnails_path); os.makedirs(real_thumbnails_path); xbmcgui.Dialog().notification(ADDON_NAME, "Thumbnails obrisani.", xbmcgui.NOTIFICATION_INFO, 2000)
        except Exception as e: xbmcgui.Dialog().notification(ADDON_NAME, f"Greška pri brisanju thumbnailsa: {e}", xbmcgui.NOTIFICATION_ERROR, 2000)
def delete_logs():
    dialog = xbmcgui.Dialog(); deleted_files_messages = []; real_log_path = xbmcvfs.translatePath(LOG_PATH); old_log_file = os.path.join(real_log_path, 'kodi.old.log')
    if xbmcvfs.exists(old_log_file):
        if xbmcvfs.delete(old_log_file): deleted_files_messages.append("- 'kodi.old.log' je obrisan.")
    try:
        dirs, files = xbmcvfs.listdir(real_log_path); crash_logs_found = 0
        for filename in files:
            if 'crashlog' in filename.lower():
                crash_log_path = os.path.join(real_log_path, filename)
                if xbmcvfs.delete(crash_log_path): crash_logs_found += 1
        if crash_logs_found > 0: deleted_files_messages.append(f"- Obrisano {crash_logs_found} crash log fajlova.")
    except Exception as e: xbmc.log(f"BDTOOLBOX: Greška pri čitanju log foldera: {e}", level=xbmc.LOGERROR)
    if deleted_files_messages: dialog.ok(ADDON_NAME, "Uspešno obrisano:\n" + "\n".join(deleted_files_messages))
    else: dialog.ok(ADDON_NAME, "Nije pronađen nijedan stari ili crash log za brisanje.")
def clean_system_menu():
    dialog = xbmcgui.Dialog(); options = ["Očisti Cache", "Očisti Thumbnails (Sličice)", "Očisti Packages", "Obriši Stare i Crash Logove", "Očisti Sve"]
    choice = dialog.select("Izaberite opciju čišćenja", options)
    if choice == 0: clean_cache()
    elif choice == 1: clean_thumbnails()
    elif choice == 2: clean_packages()
    elif choice == 3: delete_logs()
    elif choice == 4:
        if dialog.yesno("Potvrda", "Da li ste sigurni da želite očistiti SVE (Cache, Thumbnails, Packages, Stare i Crash Logove)?"):
            clean_cache(); clean_thumbnails(); clean_packages(); delete_logs(); dialog.notification(ADDON_NAME, "Kompletno čišćenje završeno.", xbmcgui.NOTIFICATION_INFO, 3000)
def view_log():
    log_file_path = os.path.join(xbmcvfs.translatePath(LOG_PATH), 'kodi.log')
    if not xbmcvfs.exists(log_file_path):
        xbmcgui.Dialog().ok(ADDON_NAME, "Log fajl (kodi.log) ne postoji."); return
    f = xbmcvfs.File(log_file_path, 'r'); content = f.read(); f.close()
    xbmcgui.Dialog().textviewer("Kodi Log Pregled", content)
def write_advanced_settings(memorysize, buffermode, readfactor):
    dialog = xbmcgui.Dialog(); xml_content = f"""<advancedsettings><cache><buffermode>{buffermode}</buffermode><memorysize>{memorysize}</memorysize><readfactor>{readfactor}</readfactor></cache></advancedsettings>"""
    as_path = os.path.join(xbmcvfs.translatePath(USERDATA_PATH), 'advancedsettings.xml')
    try:
        f = xbmcvfs.File(as_path, 'w'); f.write(xml_content); f.close()
        dialog.ok(ADDON_NAME, "Fajl 'advancedsettings.xml' je uspešno kreiran.\nPotrebno je restartovati Kodi da bi promene bile primenjene.")
    except Exception as e: dialog.ok(ADDON_NAME, f"Greška pri pisanju fajla:\n{e}")
def auto_buffer_menu():
    dialog = xbmcgui.Dialog(); options = ["Profil za 1GB RAM uređaje", "Profil za 2GB RAM uređaje", "Profil za 3GB RAM uređaje", "Profil za 4GB RAM uređaje", "Profil za 6GB+ RAM uređaje", "Ukloni podešavanja bafera (vrati na default)"]
    choice = dialog.select("Automatsko podešavanje bafera", options); buffermode = 1; readfactor = 8
    if choice == 0: write_advanced_settings(150 * 1024 * 1024, buffermode, readfactor)
    elif choice == 1: write_advanced_settings(250 * 1024 * 1024, buffermode, readfactor)
    elif choice == 2: write_advanced_settings(350 * 1024 * 1024, buffermode, readfactor)
    elif choice == 3: write_advanced_settings(500 * 1024 * 1024, buffermode, readfactor)
    elif choice == 4: write_advanced_settings(650 * 1024 * 1024, buffermode, readfactor)
    elif choice == 5:
        as_path = os.path.join(xbmcvfs.translatePath(USERDATA_PATH), 'advancedsettings.xml')
        if xbmcvfs.exists(as_path):
            if dialog.yesno("Potvrda", "Da li ste sigurni da želite obrisati advancedsettings.xml?"):
                xbmcvfs.delete(as_path); dialog.ok(ADDON_NAME, "Podešavanja bafera su uklonjena. Restartujte Kodi.")
        else: dialog.ok(ADDON_NAME, "Fajl advancedsettings.xml ne postoji.")
def manual_buffer_editor():
    dialog = xbmcgui.Dialog(); mem_size_mb = dialog.numeric(0, "Unesite veličinu bafera (memorysize) u MB", "100")
    if not mem_size_mb: return
    mem_size_bytes = int(mem_size_mb) * 1024 * 1024
    buffer_mode_choice = dialog.select("Izaberite mod bafera (buffermode)", ['Sve (Internet i lokalni fajlovi)', 'Samo Internet', 'Bez bafera'])
    if buffer_mode_choice == -1: return
    buffermode = [1, 0, 3][buffer_mode_choice]
    read_factor = dialog.numeric(0, "Unesite faktor čitanja (readfactor)", "10")
    if not read_factor: return
    write_advanced_settings(mem_size_bytes, buffermode, readfactor)

def main_menu():
    if xbmc.getCondVisibility('System.Platform.Android'):
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=f"plugin://{ADDON_ID}/?action=android_menu", listitem=xbmcgui.ListItem("[COLOR orange]Android Alati[/COLOR]"), isFolder=True)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=f"plugin://{ADDON_ID}/?action=system_status", listitem=xbmcgui.ListItem("Status Sistema"), isFolder=False)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=f"plugin://{ADDON_ID}/?action=list_addons", listitem=xbmcgui.ListItem("Upravljanje Addon-ima"), isFolder=True)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=f"plugin://{ADDON_ID}/?action=file_explorer", listitem=xbmcgui.ListItem("File Explorer"), isFolder=True)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=f"plugin://{ADDON_ID}/?action=backup", listitem=xbmcgui.ListItem("Full Backup"), isFolder=False)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=f"plugin://{ADDON_ID}/?action=restore", listitem=xbmcgui.ListItem("Full Restore"), isFolder=False)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=f"plugin://{ADDON_ID}/?action=maintenance_db", listitem=xbmcgui.ListItem("Održavanje Baze Podataka"), isFolder=False)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=f"plugin://{ADDON_ID}/?action=speedtest", listitem=xbmcgui.ListItem("Pokreni Speed Test"), isFolder=False)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=f"plugin://{ADDON_ID}/?action=clean_menu", listitem=xbmcgui.ListItem("Alati za Čišćenje"), isFolder=False)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=f"plugin://{ADDON_ID}/?action=view_log", listitem=xbmcgui.ListItem("Pregled Log Fajla"), isFolder=False)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=f"plugin://{ADDON_ID}/?action=auto_buffer", listitem=xbmcgui.ListItem("Automatsko podešavanje bafera"), isFolder=False)
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=f"plugin://{ADDON_ID}/?action=manual_buffer", listitem=xbmcgui.ListItem("Ručni Editor Bafera"), isFolder=False)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def router(paramstring):
    params = dict(parse_qsl(paramstring))
    action = params.get('action')
    if action is None: main_menu()
    elif action == 'android_menu': android_tools_menu()
    elif action == 'android_kodi_settings': android_open_kodi_settings()
    elif action == 'android_wifi_settings': android_open_wifi_settings()
    elif action == 'android_reboot_recovery': android_reboot_recovery()
    elif action == 'android_reboot_bootloader': android_reboot_bootloader()
    elif action == 'system_status': display_system_status()
    elif action == 'list_addons': list_addons()
    elif action == 'toggle_addon': toggle_addon(params['id'], params['current_status'])
    elif action == 'file_explorer': file_explorer(params.get('path'))
    elif action == 'delete_file': delete_file(params['path'])
    elif action == 'backup': backup_addons()
    elif action == 'restore': restore_addons()
    elif action == 'maintenance_db': maintenance_db()
    elif action == 'speedtest': run_speedtest()
    elif action == 'clean_menu': clean_system_menu()
    elif action == 'view_log': view_log()
    elif action == 'auto_buffer': auto_buffer_menu()
    elif action == 'manual_buffer': manual_buffer_editor()

if __name__ == '__main__':
    paramstring = sys.argv[2][1:] if len(sys.argv) > 2 else ""
    router(paramstring)