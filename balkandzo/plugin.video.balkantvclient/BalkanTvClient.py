import xbmcgui
import xbmcplugin
import json
import urllib.request
import sys
import xbmcaddon
import urllib.parse
import random 
import xbmc
import time
import os 
import xbmcvfs 

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_INSTALL_PATH = ADDON.getAddonInfo('path') 
ADDON_PROFILE_PATH = ADDON.getAddonInfo('profile') 
ADDON_HANDLE = int(sys.argv[1])

ICON_PATH_BASE = os.path.join(ADDON_INSTALL_PATH, 'resources', 'icons')

def get_setting(setting_id, convert_to_type=str):
    value = ADDON.getSetting(setting_id)
    default_values = {
        'processed_list_url': '',
        'processed_list_cache_hours': 1,
        'stream_check_timeout': 7,
        'playback_user_agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36"
    }
    if convert_to_type == int:
        try: return int(value)
        except ValueError: return default_values.get(setting_id, 0)
    return value if value else default_values.get(setting_id, '')

PROCESSED_LIST_URL = get_setting('processed_list_url')
PROCESSED_LIST_CACHE_HOURS = get_setting('processed_list_cache_hours', int)
STREAM_CHECK_TIMEOUT = get_setting('stream_check_timeout', int)
PLAYBACK_USER_AGENT = get_setting('playback_user_agent')

PROCESSED_DATA_CACHE_FILE = os.path.join(ADDON_PROFILE_PATH, 'processed_data_cache.json')

def log(message, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_NAME}] {message}", level=level)

def http_get(url):
    if not url:
        log("URL nije naveden za http_get.", xbmc.LOGERROR)
        return None
    try:
        ua_for_lists = "Mozilla/5.0 (compatible; KodiAddonClient/2.0)"
        req = urllib.request.Request(url, headers={'User-Agent': ua_for_lists})
        with urllib.request.urlopen(req, timeout=20) as response:
            if response.getcode() == 200:
                return response.read().decode('utf-8', errors='ignore')
            log(f"Greška pri dohvaćanju URL-a: {url}, Status: {response.getcode()}", xbmc.LOGERROR)
    except Exception as e:
        log(f"Iznimka pri dohvaćanju URL-a: {url}, Greška: {e}", xbmc.LOGERROR)
    return None

def load_processed_data():
    if not PROCESSED_LIST_URL:
        log("URL za obrađenu listu kanala nije postavljen.", xbmc.LOGERROR)
        xbmcgui.Dialog().ok(ADDON_NAME, "Greška: URL za obrađenu listu kanala nije konfiguriran.")
        return None
    if xbmcvfs.exists(PROCESSED_DATA_CACHE_FILE):
        try:
            f = xbmcvfs.File(PROCESSED_DATA_CACHE_FILE, 'r')
            content = f.read(); f.close()
            cached_data = json.loads(content)
            cache_age = time.time() - cached_data.get('timestamp', 0)
            if cache_age < PROCESSED_LIST_CACHE_HOURS * 3600:
                log(f"Koristim keširanu obrađenu listu (stara {int(cache_age/60)} min).")
                return cached_data.get('data', None)
            else: log("Keš obrađene liste je istekao.")
        except Exception as e: log(f"Greška pri čitanju keša obrađene liste: {e}", xbmc.LOGWARNING)

    log("Dohvaćam obrađenu listu kanala s URL-a: " + PROCESSED_LIST_URL)
    json_content = http_get(PROCESSED_LIST_URL)
    if json_content:
        try:
            data = json.loads(json_content)
            if not xbmcvfs.exists(ADDON_PROFILE_PATH): xbmcvfs.mkdirs(ADDON_PROFILE_PATH)
            if xbmcvfs.exists(ADDON_PROFILE_PATH):
                f = xbmcvfs.File(PROCESSED_DATA_CACHE_FILE, 'w')
                f.write(json.dumps({'timestamp': time.time(), 'data': data}, indent=4, ensure_ascii=False))
                f.close()
                log("Obrađena lista kanala spremljena u keš.")
            return data
        except json.JSONDecodeError as e:
            log(f"Greška pri parsiranju JSON-a obrađene liste: {e}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok(ADDON_NAME, f"Greška: Nije moguće parsirati obrađenu listu.\n{e}")
        except Exception as e:
            log(f"Neočekivana greška kod spremanja keša obrađene liste: {e}", xbmc.LOGERROR)
            if 'data' in locals(): return data 
    else: xbmcgui.Dialog().ok(ADDON_NAME, "Greška: Nije moguće dohvatiti obrađenu listu s URL-a.")
    if xbmcvfs.exists(PROCESSED_DATA_CACHE_FILE): 
        try:
            f = xbmcvfs.File(PROCESSED_DATA_CACHE_FILE, 'r')
            content = f.read(); f.close()
            cached_data = json.loads(content)
            log("Koristim stari (fallback) keš obrađene liste.", xbmc.LOGWARNING)
            return cached_data.get('data', None)
        except Exception as e: log(f"Greška pri čitanju fallback keša obrađene liste: {e}", xbmc.LOGERROR)
    return None

def show_categories(processed_data):
    if not processed_data or 'countries' not in processed_data:
        xbmcgui.Dialog().ok(ADDON_NAME, "Greška: Lista kategorija nije ispravna ili nedostupna.")
        xbmcplugin.endOfDirectory(ADDON_HANDLE, succeeded=False)
        return
    li_cache = xbmcgui.ListItem(label="[B]Osvježi Listu (Obriši Keš)[/B]")
    li_cache.setArt({'icon': 'DefaultCacheMaintenance.png'})
    url_cache_clear = f"{sys.argv[0]}?action=clearcache"
    xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=url_cache_clear, listitem=li_cache, isFolder=False)
    for category_item in processed_data['countries']:
        if not category_item.get('enabled', True): continue
        category_name = category_item['country_name']
        li = xbmcgui.ListItem(label=category_name)
        icon_file = category_name + '.png'
        local_icon = os.path.join(ICON_PATH_BASE, icon_file)
        if os.path.exists(local_icon): 
            li.setArt({'icon': local_icon, 'thumb': local_icon})
        else: li.setArt({'icon': 'DefaultFolder.png'})
        url_params = {'action': 'show_channels_for_category', 'category_name': category_name}
        url = f"{sys.argv[0]}?{urllib.parse.urlencode(url_params)}"
        xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=url, listitem=li, isFolder=True)
    xbmcplugin.addSortMethod(ADDON_HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)

def show_channels_for_category(processed_data, category_filter_name):
    if not processed_data or 'channels' not in processed_data:
        xbmcgui.Dialog().ok(ADDON_NAME, "Greška: Lista kanala nije ispravna ili nedostupna.")
        xbmcplugin.endOfDirectory(ADDON_HANDLE, succeeded=False)
        return
    found_any_channel = False
    for channel_data in processed_data['channels']:
        if channel_data.get('country_ref') == category_filter_name and channel_data.get('enabled', True):
            found_any_channel = True
            display_name = channel_data['channel_display_name']
            logo_url = channel_data.get('logo', '')
            stream_urls_list = channel_data.get('available_streams', [])
            if not stream_urls_list:
                log(f"Kanal '{display_name}' nema definiranih stream URL-ova. Preskačem prikaz.")
                continue 
            li = xbmcgui.ListItem(label=display_name)
            li.setArt({'thumb': logo_url, 'icon': logo_url, 'fanart': logo_url})
            li.setInfo('video', {'title': display_name, 'mediatype': 'video', 'plot': display_name})
            li.setProperty('IsPlayable', 'true')
            play_params = {
                'action': 'play_channel',
                'channel_name': display_name, 
                'logo': logo_url
            }
            url = f"{sys.argv[0]}?{urllib.parse.urlencode(play_params)}"
            xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=url, listitem=li, isFolder=False)
    if not found_any_channel:
        xbmcgui.Dialog().ok(ADDON_NAME, f"Nema dostupnih kanala za kategoriju: {category_filter_name}")
    xbmcplugin.addSortMethod(ADDON_HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    xbmcplugin.endOfDirectory(ADDON_HANDLE, succeeded=True)

def test_stream_url(url_to_test, timeout=None):
    current_timeout = timeout if timeout is not None else STREAM_CHECK_TIMEOUT
    log(f"Testiram stream URL: {url_to_test} sa timeoutom {current_timeout}s")
    try:
        request = urllib.request.Request(url_to_test, headers={"User-Agent": PLAYBACK_USER_AGENT})
        with urllib.request.urlopen(request, timeout=current_timeout) as response:
            return response.getcode() >= 200 and response.getcode() < 300
    except urllib.error.HTTPError as e: log(f"HTTPError za {url_to_test}: {e.code} {e.reason}", xbmc.LOGWARNING)
    except urllib.error.URLError as e: log(f"URLError za {url_to_test}: {e.reason}", xbmc.LOGWARNING)
    except Exception as e: log(f"Opća greška pri testiranju {url_to_test}: {e}", xbmc.LOGWARNING)
    return False

def play_selected_channel(channel_name, logo_url):
    log(f"--- Pokušaj reprodukcije za: '{channel_name}' ---")
    processed_data = load_processed_data() 
    if not processed_data or 'channels' not in processed_data:
        xbmcgui.Dialog().ok(ADDON_NAME, "Greška: Nije moguće učitati podatke o kanalima za reprodukciju.")
        xbmcplugin.setResolvedUrl(handle=ADDON_HANDLE, succeeded=False, listitem=xbmcgui.ListItem(channel_name))
        return

    target_channel_data = None
    for ch_data in processed_data['channels']:
        if ch_data.get('channel_display_name') == channel_name:
            target_channel_data = ch_data
            break
    if not target_channel_data:
        xbmcgui.Dialog().ok(ADDON_NAME, f"Kanal '{channel_name}' nije pronađen u obrađenoj listi.")
        xbmcplugin.setResolvedUrl(handle=ADDON_HANDLE, succeeded=False, listitem=xbmcgui.ListItem(channel_name))
        return

    available_streams = target_channel_data.get('available_streams', [])
    if not available_streams:
        xbmcgui.Dialog().ok(ADDON_NAME, f"Nema dostupnih streamova za kanal: {channel_name}")
        xbmcplugin.setResolvedUrl(handle=ADDON_HANDLE, succeeded=False, listitem=xbmcgui.ListItem(channel_name))
        return

    log(f"Pronađeno {len(available_streams)} streamova za '{channel_name}'.")
    
    streams_to_try = list(available_streams) 
    if len(streams_to_try) > 1:
        random.shuffle(streams_to_try) 
        log(f"Lista od {len(streams_to_try)} kandidatskih streamova je izmiješana. Prva 3 (ili manje) za pokušaj: {streams_to_try[:3]}")
    elif streams_to_try:
        log(f"Pronađen samo jedan stream, pokušavam njega: {streams_to_try[0]}")

    progress_dialog = xbmcgui.DialogProgress()
    created_progress = False
    stream_played = False
    try:
        if streams_to_try:
            progress_dialog.create(f"{ADDON_NAME} - Tražim stream", f"Kanal: {channel_name}")
            created_progress = True
        for i, stream_url in enumerate(streams_to_try):
            if created_progress and progress_dialog.iscanceled():
                log("Korisnik otkazao traženje streama.")
                break
            if created_progress:
                progress_dialog.update(
                    int(((i + 1) / len(streams_to_try)) * 100),
                    f"Testiram link {i + 1}/{len(streams_to_try)}"
                )
            if test_stream_url(stream_url): 
                log(f"Stream radi: {stream_url}")
                url_for_kodi_player = f"{stream_url}|User-Agent={urllib.parse.quote(PLAYBACK_USER_AGENT)}"
                log(f"URL za Kodi player s User-Agentom: {url_for_kodi_player}")
                list_item_to_resolve = xbmcgui.ListItem(channel_name)
                final_logo_url = logo_url 
                list_item_to_resolve.setArt({'thumb': final_logo_url, 'icon': final_logo_url, 'fanart': final_logo_url})
                list_item_to_resolve.setInfo('video', {'title': channel_name, "mediatype": "video", "plot": f"Stream za {channel_name}"})
                list_item_to_resolve.setProperty('IsPlayable', 'true')
                list_item_to_resolve.setPath(path=url_for_kodi_player)
                if created_progress and not progress_dialog.iscanceled(): progress_dialog.close()
                xbmcplugin.setResolvedUrl(handle=ADDON_HANDLE, succeeded=True, listitem=list_item_to_resolve)
                stream_played = True
                return 
            else: log(f"Stream ne radi: {stream_url}")
    finally:
        if created_progress and 'progress_dialog' in locals() and progress_dialog: 
            try: progress_dialog.close()
            except: pass
    if not stream_played:
        xbmcgui.Dialog().ok(ADDON_NAME, f"Nijedan ispravan stream nije pronađen za: {channel_name}")
        xbmcplugin.setResolvedUrl(handle=ADDON_HANDLE, succeeded=False, listitem=xbmcgui.ListItem(channel_name))

def router(paramstring):
    params = dict(urllib.parse.parse_qsl(paramstring))
    action = params.get('action')
    log(f"[ROUTER] Akcija: {action}, Parametri: {params}", level=xbmc.LOGERROR)

    if action == 'settings': ADDON.openSettings(); return 
    if action == 'clearcache':
        if xbmcvfs.exists(PROCESSED_DATA_CACHE_FILE):
            if xbmcvfs.delete(PROCESSED_DATA_CACHE_FILE):
                log("Keš obrađene liste kanala obrisan.")
                xbmcgui.Dialog().ok(ADDON_NAME, "Keš je obrisan. Osvježite listu.")
            else:
                log(f"Neuspješno brisanje keša: {PROCESSED_DATA_CACHE_FILE}", xbmc.LOGERROR)
                xbmcgui.Dialog().ok(ADDON_NAME, "Greška pri brisanju keša.")
        else: xbmcgui.Dialog().ok(ADDON_NAME, "Keš nije pronađen (već je prazan).")
        xbmc.executebuiltin("Container.Refresh"); return

    processed_data = load_processed_data()
    if not processed_data:
        log("Obrađena lista kanala nije dostupna. Ne mogu nastaviti.", xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(ADDON_HANDLE, succeeded=False); return

    if action is None: show_categories(processed_data)
    elif action == 'show_channels_for_category':
        category_name = params.get('category_name')
        show_channels_for_category(processed_data, category_name)
    elif action == 'play_channel':
        channel_name = params.get('channel_name')
        logo_url = params.get('logo')
        if channel_name:
            play_selected_channel(channel_name, logo_url)
        else:
            log("Nedostaje channel_name za 'play_channel' akciju.", xbmc.LOGERROR)
            xbmcplugin.setResolvedUrl(handle=ADDON_HANDLE, succeeded=False, listitem=xbmcgui.ListItem())
    else:
        log(f"Nepoznata akcija: {action}")
        xbmcplugin.endOfDirectory(ADDON_HANDLE, succeeded=False)

if __name__ == '__main__':
    paramstring = sys.argv[2][1:] if len(sys.argv) > 2 and sys.argv[2] else ""
    router(paramstring)