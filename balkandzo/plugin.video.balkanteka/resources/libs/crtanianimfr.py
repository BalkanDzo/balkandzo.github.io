# -*- coding: utf-8 -*-
import xbmcgui
import xbmcplugin
import json
import urllib.request
import sys
import urllib.parse
import xbmc
import resolveurl
import random

BASE_URL = "plugin://plugin.video.balkanteka/?action=crtanianimfr"
HANDLE = int(sys.argv[1])
JSON_URL = 'https://raw.githubusercontent.com/BalkanDzo/balkandzo.github.io/refs/heads/main/fm/crtanianimfr'
COUNTRIES_PER_PAGE = 15

def load_data_from_json():
    try:
        response = urllib.request.urlopen(JSON_URL)
        data = json.load(response)
        return data
    except Exception as e:
        xbmcgui.Dialog().ok('Greška', f'Greška u otvaranju liste. Provjerite konekciju.\n{e}')
        return None

def show_countries_list(page):
    data = load_data_from_json()
    if not data:
        return

    base_icon_url = 'http://balkandzo.byethost13.com/fomoti/'
    countries = sorted(data['countries'], key=lambda x: x['country'])
    start_index = (page - 1) * COUNTRIES_PER_PAGE
    end_index = page * COUNTRIES_PER_PAGE

    for country in countries[start_index:end_index]:
        list_item = xbmcgui.ListItem(label=country['country'])
        encoded = urllib.parse.quote(country['country'])
        icon = base_icon_url + encoded + '.jpg'
        list_item.setArt({'icon': icon})
        url = f"{BASE_URL}&subaction=channels&country={encoded}"
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=list_item, isFolder=True)

    if page > 1:
        list_item = xbmcgui.ListItem(label=f'[I][COLOR deepskyblue]-Prethodna Stranica- {page - 1}[/I][/COLOR]')
        url = f"{BASE_URL}&subaction=country&page={page - 1}"
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=list_item, isFolder=True)

    list_item = xbmcgui.ListItem(label='[I][COLOR deepskyblue]-Pocetna Stranica-[/I][/COLOR]')
    url = f"{BASE_URL}&subaction=country&page=1"
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=list_item, isFolder=True)

    if end_index < len(countries):
        list_item = xbmcgui.ListItem(label=f'[I][COLOR deepskyblue]-Sledeca Stranica- {page + 1}[/I][/COLOR]')
        url = f"{BASE_URL}&subaction=country&page={page + 1}"
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=list_item, isFolder=True)

    list_item = xbmcgui.ListItem(label='[I][COLOR deepskyblue]-Vrati se u Balkanteku-[/I][/COLOR]')
    xbmcplugin.addDirectoryItem(handle=HANDLE, url='plugin://plugin.video.balkanteka/', listitem=list_item, isFolder=True)

    list_item = xbmcgui.ListItem(label='[B]Pretraga[/B]')
    url = f"{BASE_URL}&subaction=search"
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=list_item, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE)

def show_channels_list(country):
    data = load_data_from_json()
    if not data:
        return

    for channel in data['channels']:
        if country.lower() in channel['country'].lower():
            list_item = xbmcgui.ListItem(label=channel['channel'])
            list_item.setArt({'thumb': channel['logo']})
            list_item.setInfo('video', {'title': channel['channel']})
            id1 = channel.get('id1')
            id2 = channel.get('id2')
            id3 = channel.get('id3')
            url = f"{BASE_URL}&subaction=play&id1={id1}&id2={id2}&id3={id3}"
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=list_item)

    xbmcplugin.endOfDirectory(HANDLE)

def play_channel(id1, id2, id3):
    data = load_data_from_json()
    if not data:
        return

    urls = data['urls']
    qualities = []
    if id1: qualities.append('Stream 1')
    if id2: qualities.append('Stream 2')
    if id3: qualities.append('Stream 3')

    dialog = xbmcgui.Dialog()
    index = dialog.select('Izaberite Stream:', qualities)
    if index == -1:
        return

    selected = qualities[index]
    chosen_id = None
    url_group = None

    if selected == 'Stream 1': chosen_id, url_group = id1, 'urls1'
    elif selected == 'Stream 2': chosen_id, url_group = id2, 'urls2'
    elif selected == 'Stream 3': chosen_id, url_group = id3, 'urls3'

    if not chosen_id:
        xbmcgui.Dialog().ok('Greška', 'Nijedan stream link nije pronađen.')
        return

    stream = random.choice(urls[url_group])
    channel_url = stream + chosen_id

    logo = ''
    channel_name = ''
    for ch in data['channels']:
        if (url_group == 'urls1' and ch['id1'] == chosen_id) or \
           (url_group == 'urls2' and ch['id2'] == chosen_id) or \
           (url_group == 'urls3' and ch['id3'] == chosen_id):
            channel_name = ch['channel']
            logo = ch['logo']
            break

    if not channel_name:
        xbmcgui.Dialog().ok('Greška', 'Film nije pronađen.')
        return

    list_item = xbmcgui.ListItem(channel_name)
    list_item.setArt({'thumb': logo})
    list_item.setInfo('video', {'title': channel_name})

    playable = resolveurl.resolve(channel_url)
    if playable:
        list_item.setProperty('IsPlayable', 'true')
        xbmcplugin.setResolvedUrl(HANDLE, True, listitem=list_item)
        xbmc.Player().play(playable, listitem=list_item)
    else:
        xbmcgui.Dialog().ok('Greška', 'Link ne radi. Pokušajte ponovo.')

def search(query):
    data = load_data_from_json()
    if not data:
        return

    base_icon_url = 'http://balkandzo.byethost13.com/fomoti/'
    results = []

    for country in data['countries']:
        if query.lower() in country['country'].lower():
            results.append({'type': 'country', 'data': country})

        for channel in data['channels']:
            if query.lower() in channel['channel'].lower() and country['country'] == channel['country']:
                results.append({'type': 'channel', 'data': channel})

    for result in results:
        if result['type'] == 'country':
            encoded = urllib.parse.quote(result['data']['country'])
            icon = base_icon_url + encoded + '.jpg'
            item = xbmcgui.ListItem(label=result['data']['country'])
            item.setArt({'icon': icon})
            url = f"{BASE_URL}&subaction=channels&country={encoded}"
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=item, isFolder=True)
        elif result['type'] == 'channel':
            ch = result['data']
            item = xbmcgui.ListItem(label=ch['channel'])
            item.setArt({'thumb': ch['logo']})
            item.setInfo('video', {'title': ch['channel']})
            url = f"{BASE_URL}&subaction=play&id1={ch.get('id1')}&id2={ch.get('id2')}&id3={ch.get('id3')}"
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=item)

    xbmcplugin.endOfDirectory(HANDLE)

def run():
    params = dict(urllib.parse.parse_qsl(sys.argv[2].replace('?', '')))
    action = params.get('subaction')

    if not action:
        show_countries_list(page=1)
    elif action == 'country':
        page = int(params.get('page', 1))
        show_countries_list(page)
    elif action == 'channels':
        show_channels_list(params.get('country', ''))
    elif action == 'play':
        play_channel(params.get('id1'), params.get('id2'), params.get('id3'))
    elif action == 'search':
        query = xbmcgui.Dialog().input('Unesite ključnu reč za pretragu')
        if query:
            search(query)
