# default.py
from __future__ import absolute_import, division, unicode_literals
import sys, json
from urllib.parse import urlencode, parse_qsl, quote_plus, urljoin
import xbmcplugin, xbmcgui, xbmc

import globals as G
from logger import Logger
import auth
import api
import favorites_manager

try:
    if G and Logger and favorites_manager:
        favorites_manager.initialize_dependencies(G, Logger)
        if hasattr(Logger, 'debug'):
            Logger.debug("favorites_manager inicijalizovan sa G i Logger.")
    else:
        log_msg_fav = "G, Logger, ili favorites_manager nisu u potpunosti dostupni za inicijalizaciju favorites_manager-a."
        if Logger and hasattr(Logger, 'error'): Logger.error(log_msg_fav)
        elif hasattr(xbmc, 'log'): xbmc.log(f"[{G.ADDON_NAME if hasattr(G,'ADDON_NAME') else 'DefaultPyFavInit'}] {log_msg_fav}", xbmc.LOGERROR)
        else: print(f"[DefaultPyFavInit-Fallback] {log_msg_fav}")
except Exception as e_fav_mgr_init:
    err_log_msg_fav = f"Greška pri inicijalizaciji favorites_manager.initialize_dependencies: {e_fav_mgr_init}"
    if Logger and hasattr(Logger, 'error'): Logger.error(err_log_msg_fav)
    elif hasattr(xbmc, 'log'):
        addon_name_fb_fav = "BDZO_STALKER_FAV_FB"
        if hasattr(G, 'ADDON_NAME') and G.ADDON_NAME: addon_name_fb_fav = G.ADDON_NAME
        xbmc.log(f"[{addon_name_fb_fav}] {err_log_msg_fav}", xbmc.LOGERROR)
    else: print(f"[DefaultPyFavInit-Fallback] {err_log_msg_fav}")


SORT_METHOD_NONE,SORT_METHOD_LABEL,SORT_METHOD_LABEL_IGNORE_THE,SORT_METHOD_DATE,SORT_METHOD_SIZE,SORT_METHOD_FILE,SORT_METHOD_EPISODE,SORT_METHOD_VIDEO_TITLE,SORT_METHOD_YEAR,SORT_METHOD_VIDEO_RATING,SORT_METHOD_DURATION,SORT_METHOD_DATEADDED = 0,1,2,3,4,5,9,10,11,12,14,44

if G is not None and hasattr(G,'try_initialize_active_portal_from_cache'): G.try_initialize_active_portal_from_cache()

def build_url(p): return f"{G.BASE_URL}?{urlencode(p)}"
def get_servers_from_json():
    Logger.info(f"Loading servers from: {G.JSON_URL}")
    try: import requests; r=requests.get(G.JSON_URL,timeout=G.REQUEST_TIMEOUT); r.raise_for_status(); return r.json().get("servers",[])
    except Exception as e: Logger.error(f"Err fetch/parse JSON {G.JSON_URL}: {e}"); xbmcgui.Dialog().notification(G.ADDON_NAME,"Greška pri učitavanju servera", xbmcgui.NOTIFICATION_ERROR); return []

def list_servers():
    xbmcplugin.setPluginCategory(G.ADDON_HANDLE, "Serveri")

    li_favorites = xbmcgui.ListItem(label="Omiljene MAC Adrese")
    url_favorites = build_url({"action": "list_favorite_macs"})
    xbmcplugin.addDirectoryItem(G.ADDON_HANDLE, url_favorites, li_favorites, True)

    srvs=get_servers_from_json()
    if not srvs:
        xbmcplugin.endOfDirectory(G.ADDON_HANDLE, succeeded=True)
        return

    for s_data in srvs:
        n,p_url_val,m_list_array = s_data.get("name"),s_data.get("portal"),s_data.get("macs",[])
        if not (n and p_url_val and m_list_array): Logger.warning(f"Skip invalid server: {s_data}"); continue
        if not p_url_val.endswith('/'): p_url_val+='/'
        dev_prms={k:s_data.get(k) for k in ['user_agent','stb_type','image_version','hw_version','device_id','device_id2','signature','serial_number'] if s_data.get(k) is not None and s_data.get(k)!=""}

        act_prms={"action":"connect_server","portal_url":p_url_val,"macs_str":",".join(m_list_array),"server_name":n}
        if dev_prms: act_prms["device_params_json"]=json.dumps(dev_prms)
        plot_text = f"Poveži se na server {n}\n{p_url_val}"
        li=xbmcgui.ListItem(label=n);li.setInfo('video',{'title':n,'plot': plot_text})
        xbmcplugin.addDirectoryItem(G.ADDON_HANDLE,build_url(act_prms),li,True)
    xbmcplugin.addSortMethod(G.ADDON_HANDLE,SORT_METHOD_LABEL); xbmcplugin.endOfDirectory(G.ADDON_HANDLE)

def connect_server(prms):
    portal_url = prms["portal_url"]
    macs_str = prms["macs_str"]
    server_name = prms.get("server_name", auth.portal_url_base(portal_url))
    device_params_json_str = prms.get("device_params_json")

    category_title = f"Izaberi MAC za server: {server_name}"
    xbmcplugin.setPluginCategory(G.ADDON_HANDLE, category_title)
    mac_list = [m.strip().upper() for m in macs_str.split(",") if m.strip()]

    if not mac_list:
        xbmcgui.Dialog().notification(server_name, "Nema MAC adresa za server.", xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.endOfDirectory(G.ADDON_HANDLE, False)
        return

    for i, mac_addr in enumerate(mac_list):
        display_label = f"MAC {i + 1}: {mac_addr}"
        li = xbmcgui.ListItem(label=display_label)
        li.setInfo('video', {'title': display_label, 'plot': f"Portal: {server_name}\nMAC: {mac_addr}"})

        action_prms = {
            "action": "attempt_mac_connection",
            "portal_url": portal_url,
            "selected_mac": mac_addr,
            "server_name": server_name,
            "original_macs_str": macs_str,
        }
        if device_params_json_str:
            action_prms["device_params_json"] = device_params_json_str
        url = build_url(action_prms)

        cm = []
        fav_action_prms = {
            "action": "add_mac_to_favorites_prompt",
            "portal_url": portal_url,
            "mac_address": mac_addr,
            "server_name": server_name,
            "original_server_macs_str": macs_str,
        }
        if device_params_json_str:
            fav_action_prms["device_params_json"] = device_params_json_str
        cm.append(("Dodaj u omiljene", f"RunPlugin({build_url(fav_action_prms)})"))
        li.addContextMenuItems(cm)

        xbmcplugin.addDirectoryItem(G.ADDON_HANDLE, url, li, True)
    xbmcplugin.addSortMethod(G.ADDON_HANDLE, SORT_METHOD_NONE); xbmcplugin.endOfDirectory(G.ADDON_HANDLE)

def attempt_mac_connection(prms):
    portal_url = prms["portal_url"]
    selected_mac = prms["selected_mac"].upper()
    server_name = prms.get("server_name", auth.portal_url_base(portal_url))
    original_macs_str = prms.get("original_macs_str")
    dev_prms_json_str = prms.get("device_params_json")
    dev_prms = None
    if dev_prms_json_str:
        try:
            dev_prms = json.loads(dev_prms_json_str)
        except json.JSONDecodeError:
            Logger.error(f"Greška pri dekodiranju device_params_json za MAC {selected_mac} na serveru {server_name}")
            dev_prms = None

    dlg = xbmcgui.DialogProgress()
    is_dlg_created = False
    try:
        dlg_msg_connecting = f"Povezivanje sa MAC adresom: {selected_mac}"
        dlg.create(G.ADDON_NAME, dlg_msg_connecting)
        is_dlg_created = True
        dlg.update(50)

        if auth.authenticate_mac(portal_url, selected_mac, dev_params=dev_prms):
            if is_dlg_created: dlg.update(100); dlg.close(); is_dlg_created = False
            
            notif_success_msg = f"Uspešno povezan sa MAC: {selected_mac}"
            xbmcgui.Dialog().notification(server_name, notif_success_msg, xbmcgui.NOTIFICATION_INFO)

            G.current_server_connection_params = {
                "action_to_return_to_mac_selection": "connect_server",
                "portal_url": portal_url,
                "macs_str": original_macs_str,
                "server_name": server_name,
                "device_params_json": dev_prms_json_str,
                "last_successful_mac": selected_mac
            }
            Logger.debug(f"Sačuvan G.current_server_connection_params: {G.current_server_connection_params}")
            list_portal_main_categories(server_name)
        else:
            if is_dlg_created: dlg.close(); is_dlg_created = False
            notif_fail_msg = f"Neuspešno povezivanje sa MAC adresom: {selected_mac}"
            xbmcgui.Dialog().notification(server_name, notif_fail_msg, xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.endOfDirectory(G.ADDON_HANDLE, False)
    except Exception as e:
        if is_dlg_created and hasattr(dlg, 'iscanceled') and not dlg.iscanceled(): dlg.close()
        Logger.error(f"Izuzetak tokom pokušaja konekcije sa MAC adresom ({selected_mac}): {e}")
        import traceback
        Logger.error(traceback.format_exc())
        xbmcgui.Dialog().notification(G.ADDON_NAME, f"Greška: {str(e)}", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(G.ADDON_HANDLE, False)

def list_favorite_macs(prms):
    xbmcplugin.setPluginCategory(G.ADDON_HANDLE, "Omiljene MAC Adrese")
    
    favorites = favorites_manager.load_favorites()
    
    if not favorites:
        xbmcgui.Dialog().notification(G.ADDON_NAME, "Nema omiljenih MAC adresa.", xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(G.ADDON_HANDLE, succeeded=True)
        return
        
    for fav_item in sorted(favorites, key=lambda item: item.get('display_name', '').lower()):
        display_name = fav_item.get('display_name', f"{fav_item.get('server_name','Nepoznat server')} - {fav_item.get('mac_address','Nepoznat MAC')}")
        li = xbmcgui.ListItem(label=display_name)
        plot_info = f"Server: {fav_item.get('server_name', 'N/A')}\nPortal: {fav_item.get('portal_url')}\nMAC: {fav_item.get('mac_address')}"
        li.setInfo('video', {'title': display_name, 'plot': plot_info})

        connect_prms = {
            "action": "attempt_mac_connection",
            "portal_url": fav_item.get('portal_url'),
            "selected_mac": fav_item.get('mac_address'),
            "server_name": fav_item.get('server_name'),
            "original_macs_str": fav_item.get('original_server_macs_str'),
            "device_params_json": fav_item.get('device_params_json')
        }
        url = build_url(connect_prms)
        
        cm = []
        remove_fav_prms = {
            "action": "remove_mac_from_favorites_action",
            "fav_id": fav_item.get('fav_id')
        }
        cm.append(("Ukloni iz omiljenih", f"RunPlugin({build_url(remove_fav_prms)})"))
        li.addContextMenuItems(cm)
        
        xbmcplugin.addDirectoryItem(G.ADDON_HANDLE, url, li, True)

    xbmcplugin.addSortMethod(G.ADDON_HANDLE, SORT_METHOD_LABEL)
    xbmcplugin.endOfDirectory(G.ADDON_HANDLE)

def add_mac_to_favorites_prompt(prms):
    portal_url = prms.get("portal_url")
    mac_address = prms.get("mac_address", "").upper()
    server_name = prms.get("server_name")
    device_params_json_str = prms.get("device_params_json")
    original_server_macs_str = prms.get("original_server_macs_str")

    if not (portal_url and mac_address and server_name and original_server_macs_str):
        Logger.error(f"add_mac_to_favorites_prompt: Nedostaju ključni parametri. {prms}")
        xbmcgui.Dialog().notification(G.ADDON_NAME, "Greška pri dodavanju u omiljene.", xbmcgui.NOTIFICATION_ERROR)
        return

    fav_id = f"{portal_url.rstrip('/')}-{mac_address}"

    if favorites_manager.is_favorite(portal_url, mac_address):
        xbmcgui.Dialog().notification(G.ADDON_NAME, f"Ovaj unos ({mac_address} na {server_name}) je već u omiljenima.", xbmcgui.NOTIFICATION_INFO)
        return

    default_fav_name = f"{server_name} - {mac_address}"
    user_fav_name = xbmcgui.Dialog().input("Unesite ime za omiljeni unos", defaultt=default_fav_name)

    if user_fav_name is None or user_fav_name.strip() == "":
        Logger.info("Dodavanje u omiljene otkazano ili je ime prazno.")
        return

    fav_item = {
        "fav_id": fav_id,
        "display_name": user_fav_name.strip(),
        "portal_url": portal_url,
        "mac_address": mac_address,
        "server_name": server_name,
        "original_server_macs_str": original_server_macs_str,
        "device_params_json": device_params_json_str
    }

    add_result = favorites_manager.add_favorite(fav_item)
    if add_result is True:
        xbmcgui.Dialog().notification(G.ADDON_NAME, f"Dodato u omiljene: {user_fav_name.strip()}", xbmcgui.NOTIFICATION_INFO)
    elif add_result == "exists":
        xbmcgui.Dialog().notification(G.ADDON_NAME, f"Ovaj unos ({mac_address} na {server_name}) je već u omiljenima.", xbmcgui.NOTIFICATION_INFO)
    else:
        xbmcgui.Dialog().notification(G.ADDON_NAME, "Greška pri dodavanju u omiljene.", xbmcgui.NOTIFICATION_WARNING)


def remove_mac_from_favorites_action(prms):
    fav_id_to_remove = prms.get("fav_id")
    
    if not fav_id_to_remove:
        Logger.error("remove_mac_from_favorites_action: Nedostaje fav_id.")
        xbmcgui.Dialog().notification(G.ADDON_NAME, "Greška pri uklanjanju iz omiljenih.", xbmcgui.NOTIFICATION_ERROR)
        return
        
    if favorites_manager.remove_favorite(fav_id_to_remove):
        xbmcgui.Dialog().notification(G.ADDON_NAME, "Uklonjeno iz omiljenih.", xbmcgui.NOTIFICATION_INFO)
    else:
        xbmcgui.Dialog().notification(G.ADDON_NAME, "Omiljeni unos nije pronađen.", xbmcgui.NOTIFICATION_WARNING)
        
    xbmc.executebuiltin("Container.Refresh")

def list_portal_main_categories(s_name_title):
    if not G.active_portal or not G.active_portal.token:
        Logger.error("list_portal_main_cat: Nema tokena.");
        xbmcgui.Dialog().notification(G.ADDON_NAME,"Greška: Nema aktivnog tokena za sesiju. Molimo povežite se ponovo.",xbmcgui.NOTIFICATION_ERROR);
        xbmcplugin.endOfDirectory(G.ADDON_HANDLE,False);return
        
    Logger.info(f"POZIVAM: list_portal_main_categories za server: {s_name_title}")
    Logger.debug(f"Trenutno stanje G.active_portal: URL='{G.active_portal.portal_url}', MAC='{G.active_portal.mac_address}', Token='{G.active_portal.token[:10] if G.active_portal.token else 'None'}'")
    xbmcplugin.setPluginCategory(G.ADDON_HANDLE,s_name_title)

    if G.active_portal and G.active_portal.mac_address and G.current_server_connection_params:
        active_mac_display = G.current_server_connection_params.get("last_successful_mac", G.active_portal.mac_address)
        label_manage_active = f"Osvezi trenutni (MAC: {active_mac_display})"
        li_manage = xbmcgui.ListItem(label=label_manage_active)
        manage_url_params = {"action": "show_active_connection_options"}
        url_manage = build_url(manage_url_params)
        xbmcplugin.addDirectoryItem(G.ADDON_HANDLE, url_manage, li_manage, True)

    cats=[{"label_id_placeholder":30110,"type":"itv","name_key":"Live TV","fallback_label":"[B][COLOR deepskyblue]TV[/B] [COLOR white][I]Kanali[/I][/COLOR]"},
          {"label_id_placeholder":30111,"type":"vod","name_key":"VOD","fallback_label":"[B][COLOR deepskyblue]Filmovi[/B] [COLOR white][I]VOD[/I][/COLOR]"},
          {"label_id_placeholder":30112,"type":"series","name_key":"Series","fallback_label":"[B][COLOR deepskyblue]Serije[/B] [COLOR white][I]VOD[/I][/COLOR]"}]
    item_added = False
    for c_info in cats:
        lbl = c_info['fallback_label']
        Logger.debug(f"Kreiram kategoriju: Labela='{lbl}', Tip='{c_info['type']}'")
        li=xbmcgui.ListItem(label=lbl)
        url=build_url({"action":"list_genres_or_items","content_type":c_info["type"],"category_display_name":lbl})
        Logger.debug(f"Dodajem stavku: Labela='{lbl}', URL='{url}'")
        ok = xbmcplugin.addDirectoryItem(G.ADDON_HANDLE,url,li,True)
        if ok: item_added = True; Logger.debug(f"Stavka '{lbl}' uspešno dodata.")
        else: Logger.error(f"Neuspešno dodavanje stavke '{lbl}'. addDirectoryItem vratio False.")
    
    xbmcplugin.addSortMethod(G.ADDON_HANDLE,SORT_METHOD_LABEL);xbmcplugin.endOfDirectory(G.ADDON_HANDLE)
    Logger.info("ZAVRŠENA funkcija list_portal_main_categories.")


def show_active_connection_options(prms):
    if not G.active_portal or not G.active_portal.mac_address or not G.current_server_connection_params:
        xbmcgui.Dialog().notification(G.ADDON_NAME, "Greška: Nema aktivne sesije...", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(G.ADDON_HANDLE, False)
        return

    active_mac_display = G.current_server_connection_params.get("last_successful_mac", G.active_portal.mac_address)
    server_name = G.current_server_connection_params.get('server_name', "Aktivni Server")

    category_title = f"Opcije za konekciju: {server_name} (MAC: {active_mac_display})"
    xbmcplugin.setPluginCategory(G.ADDON_HANDLE, category_title)

    label_change_mac = f"Promeni MAC adresu za server {server_name}"
    li_change_mac = xbmcgui.ListItem(label=label_change_mac)
    url_change_mac = build_url({"action": "return_to_mac_selection"})
    xbmcplugin.addDirectoryItem(G.ADDON_HANDLE, url_change_mac, li_change_mac, False)

    xbmcplugin.endOfDirectory(G.ADDON_HANDLE)

def return_to_mac_selection(prms_from_menu):
    Logger.info("Akcija: return_to_mac_selection pozvana.")
    if not G.current_server_connection_params:
        Logger.error("Ne mogu se vratiti na izbor MAC adresa: G.current_server_connection_params nije pronađen.")
        xbmcgui.Dialog().notification(G.ADDON_NAME, "Greška: Nije moguće preuzeti detalje servera za ponovni pokušaj.", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(G.ADDON_HANDLE, succeeded=False)
        xbmc.executebuiltin(f"ActivateWindow(Videos,{G.BASE_URL},return)")
        return

    G.active_portal.token = None

    original_connect_server_prms = {
        "action": G.current_server_connection_params.get("action_to_return_to_mac_selection", "connect_server"),
        "portal_url": G.current_server_connection_params.get("portal_url"),
        "macs_str": G.current_server_connection_params.get("macs_str"),
        "server_name": G.current_server_connection_params.get("server_name"),
    }
    if G.current_server_connection_params.get("device_params_json"):
        original_connect_server_prms["device_params_json"] = G.current_server_connection_params.get("device_params_json")

    mac_selection_url = build_url(original_connect_server_prms)

    xbmcplugin.endOfDirectory(G.ADDON_HANDLE, succeeded=False, cacheToDisc=False)
    xbmc.executebuiltin(f"Container.Update({mac_selection_url}, replace)")

def list_genres_or_items(prms):
    if not G.active_portal or not G.active_portal.token: Logger.error("list_genres_or_items: No token.");xbmcgui.Dialog().notification(G.ADDON_NAME,"Greška: Nema aktivnog tokena za sesiju.",xbmcgui.NOTIFICATION_ERROR);xbmcplugin.endOfDirectory(G.ADDON_HANDLE,False);return
    content_type_from_params = prms["content_type"]; category_display_name_from_params = prms.get("category_display_name", content_type_from_params.capitalize()); c_type = content_type_from_params; cat_d_name = category_display_name_from_params
    xbmcplugin.setPluginCategory(G.ADDON_HANDLE,cat_d_name);genres_js=api.get_genres(c_type)
    if genres_js and isinstance(genres_js,list) and len(genres_js)>0:
        for g_data in genres_js:
            g_id,g_title=g_data.get('id'),g_data.get('title')or g_data.get('name')or g_data.get('alias',"Nepoznat Žanr")
            if not g_id: continue
            li=xbmcgui.ListItem(label=str(g_title))
            url=build_url({"action":"list_category_items","content_type":c_type,"genre_id":str(g_id),"category_display_name":f"{cat_d_name} - {g_title}","page":"1"})
            xbmcplugin.addDirectoryItem(G.ADDON_HANDLE,url,li,True)
        xbmcplugin.addSortMethod(G.ADDON_HANDLE,SORT_METHOD_LABEL);xbmcplugin.endOfDirectory(G.ADDON_HANDLE)
    else:
        Logger.info(f"No genres for '{c_type}' or TV. Listing items directly.")
        p_items=prms.copy();p_items["action"]="list_category_items";p_items["page"]="1";p_items.pop("genre_id",None)
        list_category_items(p_items)

def list_category_items(prms):
    if not G.active_portal or not G.active_portal.token: Logger.error("list_category_items: No token.");xbmcgui.Dialog().notification(G.ADDON_NAME,"Greška: Nema aktivnog tokena za sesiju.",xbmcgui.NOTIFICATION_ERROR);xbmcplugin.endOfDirectory(G.ADDON_HANDLE,False);return
    content_type_from_params = prms["content_type"]; genre_id_from_params = prms.get("genre_id"); category_display_name_from_params = prms.get("category_display_name", content_type_from_params.capitalize()); page_from_params = int(prms.get("page",1)); search_term_from_params = prms.get("search_term"); c_type = content_type_from_params; g_id = genre_id_from_params; cat_d_name = category_display_name_from_params; pg = page_from_params; srch = search_term_from_params
    xbmcplugin.setPluginCategory(G.ADDON_HANDLE,cat_d_name)
    if c_type=='itv':xbmcplugin.setContent(G.ADDON_HANDLE,'channels')
    elif c_type=='vod':xbmcplugin.setContent(G.ADDON_HANDLE,'movies')
    elif c_type=='series':xbmcplugin.setContent(G.ADDON_HANDLE,'tvshows')
    else:xbmcplugin.setContent(G.ADDON_HANDLE,'videos')
    api_prms={'p':pg};
    if g_id: api_prms['genre' if c_type=='itv' else 'category']=g_id
    if srch: api_prms['search']=srch
    api_prms['sortby']='number' if c_type=='itv' else 'added'
    items_js=None
    if c_type=='itv' and not g_id and not srch:
        Logger.debug("Attempting get_all_channels.");items_js=api.get_all_channels()
        if items_js and isinstance(items_js,list):items_js={'data':items_js,'total_items':len(items_js),'max_page_items':len(items_js)or 1}
        elif items_js and isinstance(items_js,dict) and 'data' in items_js and isinstance(items_js['data'], list): pass
        else:items_js=None
    if not items_js:items_js=api.get_ordered_list(c_type,api_prms)
    if not items_js or not isinstance(items_js.get('data'),list):
        Logger.warning(f"No items/invalid format for '{cat_d_name}'. Data:{str(items_js)[:200]}");xbmcgui.Dialog().notification(cat_d_name,"Nema stavki u ovoj kategoriji.",xbmcgui.NOTIFICATION_INFO);xbmcplugin.endOfDirectory(G.ADDON_HANDLE,True);return
    
    item_list_from_api = items_js['data']; total_items = int(items_js.get('total_items', 0)); items_per_page_from_api = items_js.get('max_page_items')
    if items_per_page_from_api is not None:
        try: items_per_page = int(items_per_page_from_api)
        except ValueError: items_per_page = len(item_list_from_api) if item_list_from_api else 20
        if items_per_page == 0: items_per_page = len(item_list_from_api) if item_list_from_api else 20
    else: items_per_page = len(item_list_from_api) if item_list_from_api else 20
    if items_per_page == 0: items_per_page = 20
    
    for i_data in item_list_from_api:
        n,i_id_str,cmd_str,logo,desc=i_data.get('name',"Nepoznata Stavka"),str(i_data.get('id','')),str(i_data.get('cmd','')),i_data.get('logo')or i_data.get('screenshot_uri'),i_data.get('description')or i_data.get('info')or i_data.get('plot','')
        y,d_val,r_s,g_s=i_data.get('year'),i_data.get('director'),i_data.get('rating_kinopoisk')or i_data.get('rating_imdb')or i_data.get('rating_mpaa'),i_data.get('genres_str')
        if not i_id_str and not cmd_str: continue
        
        li=xbmcgui.ListItem(label=n); info={'title':n,'plot':desc or ""}
        if y:
            try: info['year']=int(y)
            except ValueError: Logger.warning(f"Invalid year for '{n}': {y}")
        if d_val: info['director']=d_val
        if r_s:
            try: info['rating']=float(str(r_s).replace(',','.'))
            except ValueError: Logger.warning(f"Invalid rating for '{n}': {r_s}")
        if g_s: info['genre']=g_s.replace(', ',' / ')
        if logo and isinstance(logo,str)and not logo.startswith("http"):
            try:logo=urljoin(G.active_portal.portal_url,logo.lstrip('/'))
            except Exception as e:Logger.warning(f"Err joining logo URL '{logo}':{e}");logo=None
        li.setArt({'icon':logo,'thumb':logo,'poster':logo,'fanart':logo if c_type!='itv'else ''})
        
        act_prms={"item_name_for_display":n};is_f=False
        is_ser=(c_type=='series'and(str(i_data.get('is_movie','1'))=='0'or i_data.get('type')=='series'))
        
        if is_ser:
            act_prms.update({"action":"list_series_content","series_id":i_id_str,"series_name":n,"series_poster":logo});is_f=True;info['mediatype']='tvshow'
        else:
            li.setProperty('IsPlayable','true');
            
            media_id_for_action = cmd_str if cmd_str else i_id_str
            
            act_prms.update({"action":"play_item",
                             "content_type_for_play":c_type,
                             "media_id_for_play": media_id_for_action,
                             "cmd_original_from_list": cmd_str, 
                             "id_original_from_list": i_id_str 
                             })
            if c_type=='itv':info['mediatype']='channel'
            elif c_type=='vod':info['mediatype']='movie'
            
        li.setInfo('video',info);xbmcplugin.addDirectoryItem(G.ADDON_HANDLE,build_url(act_prms),li,isFolder=is_f)
        
    if total_items>(page_from_params*items_per_page)and items_per_page>0:
        nxt_prms=prms.copy();nxt_prms["page"]=str(page_from_params+1)
        li_nxt=xbmcgui.ListItem(label=f"[B][COLOR deepskyblue]Sledeća strana[/B] [COLOR white][I]({page_from_params+1})[/I][/COLOR]");xbmcplugin.addDirectoryItem(G.ADDON_HANDLE,build_url(nxt_prms),li_nxt,True)
    xbmcplugin.addSortMethod(G.ADDON_HANDLE,SORT_METHOD_LABEL_IGNORE_THE)
    if c_type!='itv':xbmcplugin.addSortMethod(G.ADDON_HANDLE,SORT_METHOD_YEAR);xbmcplugin.addSortMethod(G.ADDON_HANDLE,SORT_METHOD_VIDEO_RATING)
    xbmcplugin.endOfDirectory(G.ADDON_HANDLE)

def list_series_content(prms):
    if not G.active_portal or not G.active_portal.token: Logger.error("list_series_content: No token.");xbmcgui.Dialog().notification(G.ADDON_NAME,"Greška: Nema aktivnog tokena za sesiju.",xbmcgui.NOTIFICATION_ERROR);xbmcplugin.endOfDirectory(G.ADDON_HANDLE,False);return
    s_id,s_name,s_poster=prms["series_id"],prms.get("series_name","Nepoznata Serija"),prms.get("series_poster")
    xbmcplugin.setPluginCategory(G.ADDON_HANDLE,s_name);xbmcplugin.setContent(G.ADDON_HANDLE,'episodes')
    api_prms={'movie_id':s_id,'sortby':'id'};s_cont_js=api.get_ordered_list('series',api_prms)
    if not s_cont_js or not isinstance(s_cont_js.get('data'),list)or not s_cont_js['data']:
        Logger.warning(f"No episodes for series '{s_name}' (ID:{s_id}). Data:{str(s_cont_js)[:200]}");xbmcgui.Dialog().notification(s_name,"Nema epizoda za ovu seriju.",xbmcgui.NOTIFICATION_INFO);xbmcplugin.endOfDirectory(G.ADDON_HANDLE,True);return
    eps=s_cont_js['data']
    for ep_data in eps:
        ep_n,ep_id_str,ep_cmd_str=ep_data.get('name')or ep_data.get('o_name',"Nepoznata Epizoda"),str(ep_data.get('id','')),str(ep_data.get('cmd',''))
        ep_scr=ep_data.get('screenshot_uri')or s_poster
        if ep_scr and isinstance(ep_scr,str)and not ep_scr.startswith("http"):
            try:ep_scr=urljoin(G.active_portal.portal_url,ep_scr.lstrip('/'))
            except Exception as e:Logger.warning(f"Err joining ep screenshot URL '{ep_scr}':{e}");ep_scr=s_poster
        ep_desc=ep_data.get('description')or ep_data.get('o_description')or"";
        s_num_str=str(ep_data.get('season_num',ep_data.get('season_number',ep_data.get('season','0'))))
        ep_num_str=str(ep_data.get('episode_num',ep_data.get('series_num',ep_data.get('episode','0'))))
        
        if not ep_id_str and not ep_cmd_str: continue

        li=xbmcgui.ListItem(label=ep_n); info={'title':ep_n,'plot':ep_desc,'mediatype':'episode','tvshowtitle':s_name}
        if s_num_str != '0':
            try: info['season']=int(s_num_str)
            except ValueError: Logger.warning(f"Invalid season number for '{ep_n}': {s_num_str}")
        if ep_num_str != '0':
            try: info['episode']=int(ep_num_str)
            except ValueError: Logger.warning(f"Invalid episode number for '{ep_n}': {ep_num_str}")
        li.setArt({'icon':ep_scr,'thumb':ep_scr,'poster':s_poster});li.setProperty('IsPlayable','true')
        
        media_id_for_episode_play = ep_cmd_str if ep_cmd_str else ep_id_str
        
        pl_prms={"action":"play_item",
                 "content_type_for_play":"vod", 
                 "media_id_for_play": media_id_for_episode_play,
                 "cmd_original_from_list": ep_cmd_str, 
                 "id_original_from_list": ep_id_str, 
                 "series_episode_id_for_api":ep_id_str,
                 "item_name_for_display":f"{s_name} - {ep_n}"
                 }
        xbmcplugin.addDirectoryItem(G.ADDON_HANDLE,build_url(pl_prms),li,False)
    xbmcplugin.addSortMethod(G.ADDON_HANDLE,SORT_METHOD_EPISODE);xbmcplugin.addSortMethod(G.ADDON_HANDLE,SORT_METHOD_LABEL);xbmcplugin.endOfDirectory(G.ADDON_HANDLE)

def play_item(prms):
    if not G.active_portal or not G.active_portal.token: Logger.error("play_item: No token.");xbmcgui.Dialog().notification(G.ADDON_NAME,"Greška: Nema aktivnog tokena za sesiju.",xbmcgui.NOTIFICATION_ERROR);xbmcplugin.setResolvedUrl(G.ADDON_HANDLE,False,xbmcgui.ListItem());return

    content_type_for_play = prms["content_type_for_play"]
    initial_try_identifier = prms["media_id_for_play"]
    cmd_original = prms.get("cmd_original_from_list")
    id_original = prms.get("id_original_from_list")
    series_episode_id_for_api = prms.get("series_episode_id_for_api")

    i_name_disp = prms.get("item_name_for_display","Reprodukcija...");
    p_name_disp = auth.portal_url_base(G.active_portal.portal_url)
    xbmcgui.Dialog().notification(f"Pokrećem: {i_name_disp}",p_name_disp,xbmcgui.NOTIFICATION_INFO,3000)

    api_type_for_create_link = "vod" if content_type_for_play == "series" else content_type_for_play

    Logger.debug(f"play_item: Pokušaj reprodukcije za '{i_name_disp}'. Inicijalni identifikator: '{initial_try_identifier}', Tip za API: '{api_type_for_create_link}'")
    if series_episode_id_for_api:
        Logger.debug(f"play_item: ID epizode za 'series' parametar API-ja: '{series_episode_id_for_api}'")

    s_url = api.create_stream_link(
        content_type_for_api=api_type_for_create_link,
        cmd_or_media_id=initial_try_identifier,
        series_episode_id=series_episode_id_for_api
    )

    if not s_url and content_type_for_play != 'itv':
        Logger.warning(f"Prvi pokušaj reprodukcije za '{i_name_disp}' sa identifikatorom '{initial_try_identifier}' nije uspeo.")
        alternative_id_to_try = None
        
        if initial_try_identifier == cmd_original and cmd_original:
            if id_original and id_original != cmd_original:
                alternative_id_to_try = id_original
                Logger.info(f"Pokušavam fallback sa ID original: '{id_original}'")
        elif initial_try_identifier == id_original and id_original:
            if cmd_original and cmd_original != id_original:
                alternative_id_to_try = cmd_original
                Logger.info(f"Pokušavam fallback sa CMD original: '{cmd_original}'")
        
        if alternative_id_to_try:
            s_url = api.create_stream_link(
                content_type_for_api=api_type_for_create_link,
                cmd_or_media_id=alternative_id_to_try,
                series_episode_id=series_episode_id_for_api
            )
            if s_url:
                 Logger.info(f"Fallback reprodukcija za '{i_name_disp}' sa identifikatorom '{alternative_id_to_try}' je uspela.")
            else:
                 Logger.error(f"Fallback reprodukcija za '{i_name_disp}' sa identifikatorom '{alternative_id_to_try}' takođe nije uspela.")

    Logger.info(f"URL from api.create_stream_link (pre-setResolvedUrl): {s_url}")
    if s_url:
        Logger.info(f"Passing to Kodi player URL: {s_url}")
        play_li=xbmcgui.ListItem(path=s_url); play_li.setInfo('video',{'title':i_name_disp})
        Logger.debug("Using minimalist ListItem for setResolvedUrl (no explicit inputstream props).")
        xbmcplugin.setResolvedUrl(G.ADDON_HANDLE,True,listitem=play_li)
        Logger.info(f"setResolvedUrl called OK for URL: {s_url}")
    else:
        Logger.error(f"Cannot get stream URL for: {i_name_disp}")
        xbmcgui.Dialog().notification(i_name_disp,"Ne mogu dobiti link za reprodukciju.",xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(G.ADDON_HANDLE,False,xbmcgui.ListItem())
        Logger.info("setResolvedUrl called FAILED")


def router():
    p_str=sys.argv[2][1:] if len(sys.argv)>2 else ""; prms=dict(parse_qsl(p_str)); act=prms.get("action")
    log_name=G.ADDON_NAME if hasattr(G,'ADDON_NAME')else "BDZO_Router"; Logger.debug(f"Router ({log_name}) pozvan sa: {prms}")
    if G is None or not hasattr(G,'ADDON_NAME'):
        try:import xbmc;xbmc.log("BDZO_ROUTER_ERR: Globals (G) not init!",xbmc.LOGFATAL)
        except:pass;return

    if act is None: list_servers()
    elif act == "connect_server": connect_server(prms)
    elif act == "attempt_mac_connection": attempt_mac_connection(prms)
    elif act == "show_active_connection_options": show_active_connection_options(prms)
    elif act == "return_to_mac_selection": return_to_mac_selection(prms)
    elif act == "list_favorite_macs": list_favorite_macs(prms)
    elif act == "add_mac_to_favorites_prompt": add_mac_to_favorites_prompt(prms)
    elif act == "remove_mac_from_favorites_action": remove_mac_from_favorites_action(prms)
    elif act == "list_portal_main_categories": list_portal_main_categories(prms.get("server_name_title", "Server"))
    elif act == "list_genres_or_items": list_genres_or_items(prms)
    elif act == "list_category_items": list_category_items(prms)
    elif act == "list_series_content": list_series_content(prms)
    elif act == "play_item": play_item(prms)
    else:
        Logger.warning(f"Nepoznata akcija: {act}");
        xbmcgui.Dialog().notification(G.ADDON_NAME, f"Nepoznata akcija: {act}", xbmcgui.NOTIFICATION_WARNING);
        xbmcplugin.endOfDirectory(G.ADDON_HANDLE,False)

if __name__ == '__main__':
    try:
        router()
    except Exception as e:
        logger_available = False; addon_name_fb = "BDZO_STALKER_MAIN_EXC_FB"
        try:
            from logger import Logger as MainLogger; logger_available = True
            if hasattr(G, 'ADDON_NAME') and G.ADDON_NAME: addon_name_fb = G.ADDON_NAME
        except: import xbmc; pass

        error_type_name = type(e).__name__; error_message = str(e); full_traceback = ""
        try: import traceback; full_traceback = traceback.format_exc()
        except: pass
        log_level = xbmc.LOGFATAL if hasattr(xbmc, 'LOGFATAL') else 4

        dialog_msg_key_text = "Kritična greška u addonu. Proverite log za detalje."

        if logger_available:
            MainLogger.error(f"KRITIČNA GREŠKA U ADDONU (default.py __main__): {error_type_name}: {error_message}", level=log_level)
            if full_traceback:
                for line in full_traceback.splitlines(): MainLogger.error(line, level=log_level)
        else:
            xbmc.log(f"[{addon_name_fb}] CRITICAL ERROR (default.py __main__): {error_type_name}: {error_message}", log_level)
            if full_traceback:
                for line in full_traceback.splitlines(): xbmc.log(f"[{addon_name_fb}] {line}", log_level)
        
        error_dialog_message = f"{dialog_msg_key_text}\n{error_type_name}: {error_message[:150]}"
        try:
            dialog_title = G.ADDON_NAME if hasattr(G, 'ADDON_NAME') and G.ADDON_NAME else "BDZO Stalker"
            xbmcgui.Dialog().ok(dialog_title, error_dialog_message)
        except Exception as e_diag:
            diag_err_msg = f"Greška pri prikazu dialoga o kritičnoj grešci: {e_diag}"
            if logger_available: MainLogger.error(diag_err_msg, level=log_level)
            else: xbmc.log(f"[{addon_name_fb}] {diag_err_msg}", log_level)