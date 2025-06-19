# -*- coding: utf-8 -*-
import sys
import os
import urllib.parse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')
ICONS_PATH = os.path.join(ADDON_PATH, 'resources', 'icons')
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]

CATEGORIES = [
    {"name": "[B][COLOR deepskyblue]Domaci Filmovi[/B][/COLOR]", "action": "domfilm", "icon": "domfilm.png"},
    {"name": "[B][COLOR deepskyblue]Domaci Filmovi[/B] [I](filmske kolekcije)[/I][/COLOR]", "action": "domfilmfr", "icon": "domfilmfr.png"},
    {"name": "[B][COLOR deepskyblue]Domace Serije[/B] [I](emitovanje u toku)[/I][/COLOR]", "action": "domserijenew", "icon": "domserijenew.png"},
    {"name": "[B][COLOR deepskyblue]Domace Serije[/B] [I](zavrsene serije)[/I][/COLOR]", "action": "domserijefinal", "icon": "domserijefinal.png"},
    {"name": "[B][COLOR deepskyblue]Crtani - Animirani Filmovi (sinhronizovano)[/B][/COLOR]", "action": "crtanianim", "icon": "crtanianim.png"},
    {"name": "[B][COLOR deepskyblue]Crtani - Animirani Filmovi (sinhronizovano)[/B] [I](filmske kolekcije)[/I][/COLOR]", "action": "crtanianimfr", "icon": "crtanianimfr.png"},
    {"name": "[B][COLOR deepskyblue]Crtane - Animirane Serije[/B] [I](epizodne)[/I][/COLOR]", "action": "crtanser", "icon": "crtanser.png"},
    {"name": "------------------------------------------------------------------------------------------------------------", "action": "skip", "icon": ""},
    {"name": "[B][COLOR deepskyblue]4K Filmovi[/B][/COLOR]", "action": "film4k", "icon": "film4k.png"},
    {"name": "[B][COLOR deepskyblue]Strani Filmovi[/B][/COLOR]", "action": "strfilm", "icon": "strfilm.png"},
    {"name": "[B][COLOR deepskyblue]Strani Filmovi[/B] [I](filmske kolekcije)[/I][/COLOR]", "action": "strfilmfr", "icon": "strfilmfr.png"},
    {"name": "[B][COLOR deepskyblue]Strane Serije[/B] [I](emitovanje u toku)[/I][/COLOR]", "action": "strserijenew", "icon": "strserijenew.png"},
    {"name": "[B][COLOR deepskyblue]Strane Serije[/B] [I](zavrsene serije)[/I][/COLOR]", "action": "strserijefinal", "icon": "strserijefinal.png"},
]

def show_categories():
    xbmcplugin.setPluginCategory(HANDLE, "Balkanteka")

    for category in CATEGORIES:
        action = category.get('action', '')
        name = category.get('name', '')
        icon_file = category.get('icon', '')

        if action == 'skip':
            list_item = xbmcgui.ListItem(label=name)
            list_item.setArt({'icon': 'DefaultFolder.png'})
            xbmcplugin.addDirectoryItem(handle=HANDLE, url="", listitem=list_item, isFolder=False)
            continue

        url = f"{BASE_URL}?action={action}"
        list_item = xbmcgui.ListItem(label=name)
        icon_path = os.path.join(ICONS_PATH, icon_file)

        if os.path.isfile(icon_path):
            list_item.setArt({'icon': icon_path, 'poster': icon_path})
        else:
            list_item.setArt({'icon': 'DefaultFolder.png', 'poster': 'DefaultFolder.png'})

        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=list_item, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE)

def run_addon():
    if len(sys.argv) < 3:
        show_categories()
        return

    params = dict(urllib.parse.parse_qsl(sys.argv[2].replace('?', '')))
    action = params.get('action')

    if not action:
        show_categories()
        return

    try:
        mod = __import__(f"resources.libs.{action}", fromlist=['run'])
        mod.run()
    except Exception as e:
        xbmcgui.Dialog().notification("Greška", f"Greška pri pokretanju: {action}\n{str(e)}", xbmcgui.NOTIFICATION_ERROR, 5000)

if __name__ == '__main__':
    run_addon()
