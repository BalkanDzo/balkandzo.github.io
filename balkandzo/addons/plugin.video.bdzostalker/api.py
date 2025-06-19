# api.py
from __future__ import absolute_import, division, unicode_literals
import json
from urllib.parse import urlencode 
import requests 
import globals as G 
from logger import Logger


def _make_api_request(params, is_json_response=True, attempt_reauth_on_failure=True):

    if not G.active_portal.token or not G.active_portal.mac_address or not G.active_portal.full_api_url:
        Logger.error("API request failed: Portal, MAC or Token not set in G.active_portal config.")
        return None

    final_params = params.copy() 
    if 'mac' not in final_params:
        final_params['mac'] = G.active_portal.mac_address 
    
    headers = {
        'User-Agent': G.active_portal.user_agent,
        'X-User-Agent': G.active_portal.stb_type,
        'Referer': G.active_portal.portal_url, 
        'Authorization': f'Bearer {G.active_portal.token}',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest'
    }
    cookies = {'mac': G.active_portal.mac_address}

    Logger.debug(f"API Request URL (base for requests): {G.active_portal.full_api_url}")
    Logger.debug(f"API Request params (pre urlencode by requests): {final_params}")

    response = None 
    try:
        response = requests.get(G.active_portal.full_api_url, params=final_params, headers=headers, cookies=cookies, timeout=G.REQUEST_TIMEOUT)
        Logger.debug(f"Actual API URL called by requests: {response.url}") 

        if response.status_code == 401 or (response.status_code == 200 and "Authorization failed" in response.text):
            Logger.warning(f"Authorization failed for action {params.get('action', '')} (status {response.status_code}). Token might be expired.")
            if attempt_reauth_on_failure:
                Logger.info("Attempting to re-authenticate...")
                import auth 
                
                current_device_params = {
                   'user_agent': G.active_portal.user_agent, 'stb_type': G.active_portal.stb_type,
                   'image_version': G.active_portal.image_version, 'hw_version': G.active_portal.hw_version,
                   'device_id': G.active_portal.device_id, 'device_id2': G.active_portal.device_id2,
                   'signature': G.active_portal.signature, 'serial_number': G.active_portal.serial_number
                }

                if auth.authenticate_mac(G.active_portal.portal_url, G.active_portal.mac_address, 
                                         server_specific_device_params=current_device_params):
                    Logger.info("Re-authentication successful. Retrying API request.")
                    return _make_api_request(params, is_json_response, attempt_reauth_on_failure=False)
                else:
                    Logger.error("Re-authentication failed. API request cannot proceed.")
                    return None 
            else: 
                Logger.error("Not attempting re-authentication (already tried or disabled). API request failed.")
                return None 
        
        response.raise_for_status()  

        if is_json_response:
            raw_response_text = response.text 
            Logger.debug(f"Raw JSON response for action {params.get('action', '')} (params: {final_params}): {raw_response_text[:2000]}") 
            try:
                data = response.json() 
                if 'js' in data and data['js'] is not None:
                    Logger.debug(f"Returning 'js' object for action {params.get('action', '')}: {str(data['js'])[:500]}")
                    return data['js']
                else:
                    Logger.warning(f"API response for action {params.get('action', '')} did not have a 'js' root object or 'js' is null. Full response logged above.")
                    return data if 'js' not in data else None 
            except json.JSONDecodeError:
                Logger.error(f"API response was not valid JSON (full response logged above as 'Raw JSON response').")
                return None
        else: 
            Logger.debug(f"Raw TEXT response for action {params.get('action', '')}: {response.text[:1000]}")
            return response.text 

    except requests.exceptions.HTTPError as e: 
        Logger.error(f"API HTTP error for action {params.get('action', '')} (status {e.response.status_code if e.response else 'N/A'}): {e} | Response: {e.response.text[:200] if e.response else 'No response text'}")
        return None
    except requests.exceptions.RequestException as e: 
        Logger.error(f"API request (RequestException) for action {params.get('action', '')}: {e}")
        return None
    except Exception as e: 
        Logger.error(f"Unexpected error during API request for action {params.get('action', '')}: {type(e).__name__} - {e}")
        import traceback
        Logger.error(traceback.format_exc())
        return None

def get_genres(content_type='vod'):
    params = {
        'type': content_type,
        'action': 'get_genres'
    }
    return _make_api_request(params)

def get_ordered_list(content_type, addition_params=None):
    params = {
        'type': content_type,
        'action': 'get_ordered_list'
    }
    if addition_params:
        params.update(addition_params)
    return _make_api_request(params)

def get_all_channels():
    params = {
        'type': 'itv',
        'action': 'get_all_channels'
    }
    return _make_api_request(params)

def create_stream_link(content_type_for_api, cmd_or_media_id, series_episode_id=None):
    params = {
        'type': content_type_for_api, 
        'action': 'create_link',
        'cmd': cmd_or_media_id 
    }
    if content_type_for_api != 'itv' and series_episode_id is not None: 
        params['series'] = str(series_episode_id)
    
    response_data_js = _make_api_request(params) 
    if response_data_js and response_data_js.get('cmd'):
        stream_cmd = response_data_js['cmd']
        if stream_cmd.lower().startswith("ffmpeg "):
            return stream_cmd[7:]
        elif stream_cmd.lower().startswith("auto "):
            return stream_cmd[5:]
        return stream_cmd
    else:
        error_details = response_data_js.get('msg') if isinstance(response_data_js, dict) else "No 'cmd' in response or invalid data."
        Logger.error(f"Failed to create stream link. Details: {error_details}")
        return None

def set_favourite(content_type, media_id, is_tv_channel=False):
    action_params = {}
    if is_tv_channel:
        Logger.warning("Using simplified 'set_fav' for TV. May not work on all portals.")
        action_params = {'type': 'itv', 'action': 'set_fav', 'fav_add': media_id}
    else: 
        action_params = {'type': content_type, 'action': 'set_fav', 'video_id': media_id}
    
    response_js = _make_api_request(action_params)
    if response_js is not None:
        Logger.info(f"Set favorite possibly successful for {media_id} (type: {content_type})")
        return True
    Logger.error(f"Set favorite failed for {media_id} (type: {content_type})")
    return False

def remove_favourite(content_type, media_id, is_tv_channel=False):
    action_params = {}
    if is_tv_channel:
        Logger.warning("Using simplified 'del_fav' for TV. May not work on all portals.")
        action_params = {'type': 'itv', 'action': 'set_fav', 'fav_del': media_id} 
    else: 
        action_params = {'type': content_type, 'action': 'del_fav', 'video_id': media_id}
            
    response_js = _make_api_request(action_params)
    if response_js is not None:
        Logger.info(f"Remove favorite possibly successful for {media_id} (type: {content_type})")
        return True
    Logger.error(f"Remove favorite failed for {media_id} (type: {content_type})")
    return False

def get_profile_info():
    from urllib.parse import quote_plus as url_quote_plus 

    params = {
        'type': 'stb',
        'action': 'get_profile',
        'hd': '1',
        'ver': url_quote_plus(f'ImageVersion:{G.active_portal.image_version},ImageDescription:0.2.18-r14-pub-250'),
        'num_banks': '1',
        'stb_type': G.active_portal.stb_type,
        'image_version': G.active_portal.image_version,
        'video_out': 'hdmi',
        'hw_version': G.active_portal.hw_version,
        'serial_number': url_quote_plus(G.active_portal.serial_number), 
        'device_id': url_quote_plus(G.active_portal.device_id),
        'device_id2': url_quote_plus(G.active_portal.device_id2),
        'signature': url_quote_plus(G.active_portal.signature),
        'metrics': '',
        'auth_second_step': '0'
    }
    return _make_api_request(params)