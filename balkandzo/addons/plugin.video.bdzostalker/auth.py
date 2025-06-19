# auth.py
from __future__ import absolute_import, division, unicode_literals
import os
import json
from urllib.parse import quote_plus
import requests
import xbmcvfs
import globals as G
from logger import Logger

def _get_token_cache_file_path():
    return os.path.join(G.ADDON_DATA_PATH, 'stalker_token.json')

def _load_token_from_cache(portal_url_to_check, mac_address_to_check):
    token_cache_file = _get_token_cache_file_path()
    if not xbmcvfs.exists(token_cache_file): return None
    try:
        with xbmcvfs.File(token_cache_file, 'r') as f: data = json.load(f)
        if data.get('portal_url')==portal_url_to_check and data.get('mac_address')==mac_address_to_check and data.get('token'):
            Logger.debug(f"Token found in cache for {portal_url_to_check}/{mac_address_to_check}"); return data['token']
    except Exception as e: Logger.error(f"Err load token from cache: {e}")
    return None

def _save_token_to_cache(p_url, mac, token_val):
    token_cache_file = _get_token_cache_file_path()
    try:
        data={'portal_url':p_url,'mac_address':mac,'token':token_val}
        if not xbmcvfs.exists(G.ADDON_DATA_PATH): xbmcvfs.mkdirs(G.ADDON_DATA_PATH)
        with xbmcvfs.File(token_cache_file,'w') as f: json.dump(data,f)
        Logger.debug(f"Token saved for {p_url}/{mac}")
    except Exception as e: Logger.error(f"Err save token to cache: {e}")

def _clear_token_cache():
    token_cache_file = _get_token_cache_file_path()
    try:
        if xbmcvfs.exists(token_cache_file): xbmcvfs.delete(token_cache_file); Logger.debug("Token cache cleared.")
    except Exception as e: Logger.error(f"Err clear token cache: {e}")

def _perform_handshake():
    if not G.active_portal.full_api_url: Logger.error("Handshake: full_api_url not set."); return None
    prm={'type':'stb','action':'handshake','token':'','mac':G.active_portal.mac_address}
    hdr={'User-Agent':G.active_portal.user_agent,'X-User-Agent':G.active_portal.stb_type,'Referer':G.active_portal.portal_url}
    cki={'mac':G.active_portal.mac_address}
    Logger.debug(f"Handshake: {G.active_portal.full_api_url}, MAC:{G.active_portal.mac_address}, Prms:{prm}")
    r=None
    try:
        r=requests.get(G.active_portal.full_api_url,params=prm,headers=hdr,cookies=cki,timeout=G.REQUEST_TIMEOUT)
        Logger.debug(f"Actual Handshake URL: {r.url}"); r.raise_for_status()
        d=r.json()
        if d.get('js') and d['js'].get('token'): Logger.info(f"Handshake OK for {G.active_portal.mac_address}."); return d['js']['token']
        Logger.error(f"Handshake fail: {d.get('js',{}).get('msg','No token')} | S:{r.status_code}, T:{r.text[:200]}"); return None
    except requests.exceptions.HTTPError as e: Logger.error(f"Handshake HTTP err: {e} | R:{e.response.text[:200] if e.response else 'N/A'}"); return None
    except requests.exceptions.RequestException as e: Logger.error(f"Handshake req err: {e}"); return None
    except json.JSONDecodeError: Logger.error(f"Handshake JSON err: {r.text[:200] if r else 'N/A'}"); return None

def _get_profile_and_refresh_token(current_token):
    if not G.active_portal.full_api_url: Logger.error("GetProfile: full_api_url not set."); return None

    ver_string = 'ImageDescription: 0.2.18-r23-pub-254; ImageDate: Wed Aug 29 10:49:26 EEST 2018; PORTAL version: 5.1.1; API Version: JS API version: 328; STB API version: 134; Player Engine version: 0x566'

    params = {
        'type': 'stb','action': 'get_profile','hd': '1',
        'ver': quote_plus(ver_string),
        'num_banks': '1','stb_type': G.active_portal.stb_type,
        'image_version': G.active_portal.image_version,'video_out': 'hdmi',
        'hw_version': G.active_portal.hw_version,'mac': G.active_portal.mac_address,
        'serial_number': G.active_portal.serial_number, 'device_id': G.active_portal.device_id,
        'device_id2': G.active_portal.device_id2,'signature': G.active_portal.signature,
        'metrics': '','auth_second_step': '0'
    }
    headers = {'User-Agent':G.active_portal.user_agent,'X-User-Agent':G.active_portal.stb_type,'Referer':G.active_portal.portal_url,'Authorization':f'Bearer {current_token}'}
    cookies = {'mac':G.active_portal.mac_address}
    Logger.debug(f"GetProfile for MAC:{G.active_portal.mac_address}, Prms:{params}")
    r=None
    try:
        r=requests.get(G.active_portal.full_api_url,params=params,headers=headers,cookies=cookies,timeout=G.REQUEST_TIMEOUT)
        Logger.debug(f"Actual GetProfile URL: {r.url}"); r.raise_for_status()
        d=r.json()
        if d.get('js') and (d['js'].get('id') is not None or d['js'].get('status')=='OK' or d['js'].get('token') is not None):
            Logger.info(f"GetProfile OK for {G.active_portal.mac_address}. Token '{current_token[:10]}...' valid/refreshed.")
            return d['js'].get('token',current_token)
        Logger.error(f"GetProfile fail: {d.get('js',{}).get('msg','Validation fail')} | S:{r.status_code}, T:{r.text[:200]}"); return None
    except requests.exceptions.HTTPError as e: Logger.error(f"GetProfile HTTP err: {e} | R:{e.response.text[:200] if e.response else 'N/A'}"); return None
    except requests.exceptions.RequestException as e: Logger.error(f"GetProfile req err: {e}"); return None
    except json.JSONDecodeError: Logger.error(f"GetProfile JSON err: {r.text[:200] if r else 'N/A'}"); return None

def authenticate_mac(p_url, mac, dev_params=None, server_specific_device_params=None):
    G.active_portal.portal_url,G.active_portal.mac_address,G.active_portal.token = p_url,mac,None
    active_dev_params = server_specific_device_params if server_specific_device_params is not None else dev_params

    if active_dev_params and isinstance(active_dev_params,dict):
        G.active_portal.user_agent=active_dev_params.get('user_agent',G.USER_AGENT_SETTING);G.active_portal.stb_type=active_dev_params.get('stb_type',G.DEFAULT_STB_TYPE)
        G.active_portal.image_version=active_dev_params.get('image_version',G.DEFAULT_IMAGE_VERSION);G.active_portal.hw_version=active_dev_params.get('hw_version',G.DEFAULT_HW_VERSION)
        G.active_portal.device_id=active_dev_params.get('device_id',G.DEFAULT_DEVICE_ID);G.active_portal.device_id2=active_dev_params.get('device_id2',G.DEFAULT_DEVICE_ID2)
        G.active_portal.signature=active_dev_params.get('signature',G.DEFAULT_SIGNATURE);G.active_portal.serial_number=active_dev_params.get('serial_number',G.DEFAULT_SERIAL_NUMBER)
    else:
        G.active_portal.user_agent,G.active_portal.stb_type,G.active_portal.image_version,G.active_portal.hw_version=G.USER_AGENT_SETTING,G.DEFAULT_STB_TYPE,G.DEFAULT_IMAGE_VERSION,G.DEFAULT_HW_VERSION
        G.active_portal.device_id,G.active_portal.device_id2,G.active_portal.signature,G.active_portal.serial_number=G.DEFAULT_DEVICE_ID,G.DEFAULT_DEVICE_ID2,G.DEFAULT_SIGNATURE,G.DEFAULT_SERIAL_NUMBER

    if not G.active_portal.full_api_url: Logger.error(f"Auth fail: full_api_url not determined for {G.active_portal.portal_url}. Check STALKER_API_PATH."); return False
    Logger.info(f"Auth attempt for: {G.active_portal.portal_url} MAC: {G.active_portal.mac_address}")

    token=_load_token_from_cache(G.active_portal.portal_url,G.active_portal.mac_address)
    if token:
        Logger.debug("Validating cached token...");
        validated_token = _get_profile_and_refresh_token(token)
        if not validated_token:
            Logger.warning("Cached token validation failed. Clearing & requesting new.");
            _clear_token_cache();
            token=None
        else:
            token=validated_token

    if not token:
        Logger.info(f"No valid cache/validation failed. New handshake for MAC: {G.active_portal.mac_address}");
        _clear_token_cache()
        handshake_token = _perform_handshake()

        if handshake_token:
            Logger.info("Handshake OK, get_profile to activate/validate.")
            activated_token = _get_profile_and_refresh_token(handshake_token)
            if not activated_token:
                Logger.error("Failed to activate/validate token post-handshake.")
                token = None
            else:
                token = activated_token
        else:
            token = None

    if token:
        G.active_portal.token=token
        _save_token_to_cache(G.active_portal.portal_url,G.active_portal.mac_address,token)
        Logger.info(f"Auth SUCCEEDED for MAC {G.active_portal.mac_address} on {portal_url_base(G.active_portal.portal_url)}")
        return True

    G.active_portal.token=None
    Logger.error(f"Auth FAILED for MAC {G.active_portal.mac_address} on {portal_url_base(G.active_portal.portal_url)}")
    return False

def portal_url_base(full_url):
    from urllib.parse import urlparse
    if not full_url: return "Unknown Portal"
    try: return urlparse(full_url).netloc
    except: return str(full_url)