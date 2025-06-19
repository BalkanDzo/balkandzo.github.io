import urllib.request
import xbmcgui
import xbmcaddon
import random
import re
import os
import sys
import sqlite3
import xbmcvfs
import glob
import time
import json
import xbmc

# Balkan Dzo Addon by Dzon Dzoe

pvr_client_id = 'pvr.stalker'

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

addon_id_to_disable = "pvr.stalker" 
disable_addon(addon_id_to_disable)

class PVRClient:
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

    def update_pvr_client():
        dialog = xbmcgui.DialogProgress()
        dialog.create('PVR MAC Generator', 'Generisanje MAC Liste')
        dialog.update(0, 'Generisanje MAC Liste, Molimo vas sacekajte da se proces zavrsi')
        PVRClient.clear_pvr_data()
        for i in range(0, 101, 4):
            dialog.update(i, 'Generisanje MAC Liste, Molimo vas sacekajte da se proces zavrsi')
            xbmc.sleep(600) 
        
        dialog.update(100, 'Generisanje MAC Liste je zavrseno')

        xbmc.sleep(2000)
        dialog.close()

PVRClient.update_pvr_client()

addon_id = 'pvr.stalker'

if os.name == 'nt':  
    portable_data_path = os.path.join(os.getcwd(), 'portable_data')
    if os.path.isdir(portable_data_path):
        settings_path = os.path.join(portable_data_path, 'userdata', 'addon_data', addon_id, 'instance-settings-1.xml')
    else:
        settings_path = os.path.join(os.getenv('APPDATA'), 'Kodi', 'userdata', 'addon_data', addon_id, 'instance-settings-1.xml')
else:  
    settings_path = os.path.join(xbmcvfs.translatePath('special://profile/addon_data'), addon_id, 'instance-settings-1.xml')

url = 'https://bandateam.ucoz.com/Liste/balkanske.txt'

headers = {
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://bandateam.ucoz.com/'
}

request = urllib.request.Request(url, headers=headers)
response = urllib.request.urlopen(request)
mac_server_login_password_data = response.read().decode('utf-8')

mac_server_login_password_pairs = re.findall(r'(\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2})=(\S+)=(\S*),(\S*)', mac_server_login_password_data)
mac_server_login_password_dict = {pair[0]: pair[1:] for pair in mac_server_login_password_pairs}

chosen_pair = random.choice(list(mac_server_login_password_dict.items()))
chosen_mac = chosen_pair[0]
chosen_server = chosen_pair[1][0]
chosen_login = chosen_pair[1][1] if chosen_pair[1][1] else ""
chosen_password = chosen_pair[1][2] if chosen_pair[1][2] else ""

with open(settings_path, 'r') as f:
    settings_xml = f.read()

settings_xml = re.sub('<setting id="mac">.*?</setting>', '<setting id="mac">{}</setting>'.format(chosen_mac), settings_xml)
settings_xml = re.sub('<setting id="server">.*?</setting>', '<setting id="server">{}</setting>'.format(chosen_server), settings_xml)

with open(settings_path, 'w') as f:
    f.write(settings_xml)

xbmcgui.Dialog().ok('MAC Lista je generisana', 'Ako vam generisana lista pokazuje gresku pokrenite opet generator.')

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
