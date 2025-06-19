import xbmcgui
import xbmcaddon
import os
import sys
import urllib.request
import re
import json
import sqlite3
import glob
import xbmcvfs
import xbmc

addon = xbmcaddon.Addon(id='plugin.program.balkandzogen')
pvr_client_id = 'pvr.stalker'

def check_and_install_pvr_addon():
    if not xbmc.getCondVisibility('System.HasAddon({})'.format(pvr_client_id)):
        xbmc.executebuiltin('InstallAddon({})'.format(pvr_client_id))

def disable_addon(addon_id):
    my_request = {
        "jsonrpc": "2.0",
        "method": "Addons.SetAddonEnabled",
        "params": {"addonid": addon_id, "enabled": False},
        "id": 1
    }
    xbmc.executeJSONRPC(json.dumps(my_request))

class PVRClient:
    @staticmethod
    def clear_pvr_data():
        db_files = glob.glob(xbmcvfs.translatePath('special://database/TV*.db'))
        db_file_names = [f for f in db_files if ('TV' in f or 'MyPVR' in f)]

        for db_file in db_file_names:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM channels")
            cursor.execute("DELETE FROM timers")
            cursor.execute("DELETE FROM clients")
            cursor.execute("DELETE FROM channelgroups")
            cursor.execute("DELETE FROM map_channelgroups_channels")
            conn.commit()
            conn.close()

check_and_install_pvr_addon()
disable_addon(pvr_client_id)
PVRClient.clear_pvr_data()

def get_group_urls():
    use_user_groups = addon.getSetting('use_user_groups') == 'true'
    groups = {}

    if use_user_groups:
        for i in range(1, 6):
            group_url = addon.getSetting(f'custom_group_{i}')
            if group_url.strip():
                groups[f"Grupa {i}"] = group_url.strip()
    else:
        groups = {
            "Grupa 1": "https://bandateam.ucoz.com/Liste/MGrupa1.txt",
            "Grupa 2": "https://bandateam.ucoz.com/Liste/MGrupa2.txt",
            "Grupa 3": "https://bandateam.ucoz.com/Liste/MGrupa3.txt",
            "Grupa 4": "https://bandateam.ucoz.com/Liste/Mgrupa4.txt",
            "Grupa 5 Razne Liste": "https://bandateam.ucoz.com/Liste/Mgrupa5Razno.txt"
        }

    return groups

groups = get_group_urls()

def choose_group():
    dialog = xbmcgui.Dialog()
    group_names = list(groups.keys())
    chosen_index = dialog.select('Izaberite grupu', group_names)

    if chosen_index == -1:
        xbmcgui.Dialog().ok('Obaveštenje', 'Niste izabrali grupu. Izlazak iz dodatka.')
        sys.exit()

    return group_names[chosen_index]

chosen_group = choose_group()
chosen_url = groups[chosen_group]

try:
    req = urllib.request.Request(
        chosen_url,
        headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://bandateam.ucoz.com/'
        }
    )
    response = urllib.request.urlopen(req)
    lines = [line.strip() for line in response.read().decode('utf-8').splitlines() if line.strip()]
except Exception as e:
    xbmcgui.Dialog().ok('Greška', f'Neuspešno učitavanje sadržaja sa URL-a: {e}')
    sys.exit()

if not lines:
    xbmcgui.Dialog().ok('Greška', f'Grupa "{chosen_group}" nema dostupnih listi.')
    sys.exit()

def choose_list_item():
    dialog = xbmcgui.Dialog()
    chosen_index = dialog.select(f'Izaberite listu iz grupe {chosen_group}', [f"Lista {i+1}" for i in range(len(lines))])

    if chosen_index == -1:
        xbmcgui.Dialog().ok('Obaveštenje', 'Niste izabrali listu. Izlazak iz dodatka.')
        sys.exit()

    return lines[chosen_index]

chosen_item = choose_list_item()

try:
    if '=' not in chosen_item:
        raise ValueError('Linija nije u ispravnom formatu (MAC=server).')

    mac, server = chosen_item.split('=', 1)
except ValueError as e:
    xbmcgui.Dialog().ok('Greška', f'Greška pri parsiranju liste: {str(e)}')
    sys.exit()

addon_id = 'pvr.stalker'

if os.name == 'nt':
    portable_data_path = os.path.join(os.getcwd(), 'portable_data')
    if os.path.isdir(portable_data_path):
        settings_path = os.path.join(portable_data_path, 'userdata', 'addon_data', addon_id, 'instance-settings-1.xml')
    else:
        settings_path = os.path.join(os.getenv('APPDATA'), 'Kodi', 'userdata', 'addon_data', addon_id, 'instance-settings-1.xml')
else:
    settings_path = os.path.join(xbmcvfs.translatePath('special://profile/addon_data'), addon_id, 'instance-settings-1.xml')

if not os.path.exists(settings_path):
    xbmcgui.Dialog().ok('Greška', f'Settings fajl nije pronađen na putanji: {settings_path}')
    sys.exit()

with open(settings_path, 'r', encoding='utf-8') as f:
    settings_xml = f.read()

mac_match = re.findall(r'<setting id="mac">(.*?)</setting>', settings_xml)
server_match = re.findall(r'<setting id="server">(.*?)</setting>', settings_xml)

if not mac_match or not server_match:
    xbmcgui.Dialog().ok('Greška', 'Nisu pronađeni odgovarajući podaci za mac ili server u settings.xml.')
    sys.exit()

settings_xml = re.sub(r'<setting id="mac">.*?</setting>', f'<setting id="mac">{mac}</setting>', settings_xml)
settings_xml = re.sub(r'<setting id="server">.*?</setting>', f'<setting id="server">{server}</setting>', settings_xml)

with open(settings_path, 'w', encoding='utf-8') as f:
    f.write(settings_xml)

xbmcgui.Dialog().ok('Izbor završen', f'Izabrali ste listu: {chosen_item}. PVR lista je ažurirana. Restart Kodi zbog optimizacije PVR-a.')

def enable_addon(addon_id):
    my_request = {
        "jsonrpc": "2.0",
        "method": "Addons.SetAddonEnabled",
        "params": {"addonid": addon_id, "enabled": True},
        "id": 1
    }
    xbmc.executeJSONRPC(json.dumps(my_request))

addon_id_to_enable = "pvr.stalker"
enable_addon(addon_id_to_enable)

if os.name == 'nt':
    os.system('taskkill /IM kodi.exe /F')
    sys.exit(0)
else:
    xbmc.executebuiltin('Quit()')
