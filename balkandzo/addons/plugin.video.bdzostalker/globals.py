# globals.py
from __future__ import absolute_import, division, unicode_literals
import sys
import dataclasses
import xbmcaddon
import xbmcvfs
import json
import os

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')

ADDON_DATA_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
BASE_URL = sys.argv[0]
ADDON_HANDLE = int(sys.argv[1])

def get_setting(setting_id, default_value=""):
    val = ADDON.getSetting(setting_id)
    return val if val else default_value

def get_setting_as_int(setting_id, default_value=0):
    try:
        return int(get_setting(setting_id, str(default_value)))
    except ValueError:
        return default_value

def get_setting_as_bool(setting_id, default_value=False):
    val = get_setting(setting_id, str(default_value).lower())
    return val == 'true'

JSON_URL = get_setting('json_url', "https://bandateam.ucoz.com/stalkerlist.json")
REQUEST_TIMEOUT = get_setting_as_int('request_timeout', 15)
USER_AGENT_SETTING = get_setting('user_agent', "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3")

STALKER_API_PATH = get_setting('stalker_api_path', "/stalker_portal/server/load.php")

DEFAULT_STB_TYPE = get_setting('stb_type', "MAG250")
DEFAULT_IMAGE_VERSION = get_setting('image_version', "218")
DEFAULT_HW_VERSION = get_setting('hw_version', "1.7-BD-00")
DEFAULT_DEVICE_ID = get_setting('device_id', "")
DEFAULT_DEVICE_ID2 = get_setting('device_id2', "")
DEFAULT_SIGNATURE = get_setting('signature', "")
DEFAULT_SERIAL_NUMBER = get_setting('serial_number', "")


@dataclasses.dataclass
class ActivePortalConfig:
    portal_url: str = None
    mac_address: str = None
    token: str = None

    user_agent: str = USER_AGENT_SETTING
    stb_type: str = DEFAULT_STB_TYPE
    image_version: str = DEFAULT_IMAGE_VERSION
    hw_version: str = DEFAULT_HW_VERSION
    device_id: str = DEFAULT_DEVICE_ID
    device_id2: str = DEFAULT_DEVICE_ID2
    signature: str = DEFAULT_SIGNATURE
    serial_number: str = DEFAULT_SERIAL_NUMBER

    @property
    def full_api_url(self):
        from urllib.parse import urlparse, urlunparse
        if not self.portal_url:
            return None

        parsed_portal_base = urlparse(self.portal_url)
        base_url_scheme_domain = urlunparse(
            (parsed_portal_base.scheme, parsed_portal_base.netloc, '', '', '', '')
        )

        api_path_from_settings = STALKER_API_PATH

        if not api_path_from_settings.startswith('/'):
            api_path_from_settings = '/' + api_path_from_settings

        return base_url_scheme_domain.rstrip('/') + api_path_from_settings

active_portal = ActivePortalConfig()

current_server_connection_params = None


def try_initialize_active_portal_from_cache():
    try:
        from logger import Logger # Lokalni uvoz Logger-a
    except ImportError:
        import xbmc
        class Logger:
            @staticmethod
            def info(msg): xbmc.log(f"[{ADDON_NAME}-globals_init_fb] {msg}", xbmc.LOGINFO)
            @staticmethod
            def error(msg): xbmc.log(f"[{ADDON_NAME}-globals_init_fb] {msg}", xbmc.LOGERROR)
            @staticmethod
            def debug(msg): xbmc.log(f"[{ADDON_NAME}-globals_init_fb] {msg}", xbmc.LOGDEBUG)
        Logger.info("Using fallback logger during try_initialize_active_portal_from_cache.")

    token_cache_path = os.path.join(ADDON_DATA_PATH, 'stalker_token.json')

    if xbmcvfs.exists(token_cache_path):
        try:
            with xbmcvfs.File(token_cache_path, 'r') as f:
                cache_data = json.load(f)
                cached_portal_url = cache_data.get('portal_url')
                cached_mac = cache_data.get('mac_address')
                cached_token = cache_data.get('token')

                if cached_portal_url and cached_mac and cached_token:
                    Logger.info(f"Inicijalizujem G.active_portal iz keša: Portal: {cached_portal_url}, MAC: {cached_mac[:9]}...")
                    active_portal.portal_url = cached_portal_url
                    active_portal.mac_address = cached_mac
                    active_portal.token = cached_token

                    active_portal.user_agent = USER_AGENT_SETTING
                    active_portal.stb_type = DEFAULT_STB_TYPE
                    active_portal.image_version = DEFAULT_IMAGE_VERSION
                    active_portal.hw_version = DEFAULT_HW_VERSION
                    active_portal.device_id = DEFAULT_DEVICE_ID
                    active_portal.device_id2 = DEFAULT_DEVICE_ID2
                    active_portal.signature = DEFAULT_SIGNATURE
                    active_portal.serial_number = DEFAULT_SERIAL_NUMBER

                    Logger.debug(f"G.active_portal re-initialized from cache: URL={active_portal.portal_url}, MAC={active_portal.mac_address}, Token valid (will be checked by API call)")
                else:
                    Logger.info("Podaci u token kešu su nepotpuni. G.active_portal ostaje na default vrednostima.")
        except Exception as e:
            Logger.error(f"Greška pri učitavanju aktivnog portala iz keša: {e}")
    else:
        Logger.info("Token cache fajl ne postoji. G.active_portal ostaje na default vrednostima.")

def initialize_addon_data_dir():
    if not xbmcvfs.exists(ADDON_DATA_PATH):
        try:
            from logger import Logger
            log_func_g = Logger.info
            err_log_func_g = Logger.error
        except ImportError:
            import xbmc
            global log_func_g_fb, err_log_func_g_fb
            def log_func_g_fb(msg): xbmc.log(f"[{ADDON_NAME}-globals_dir_fb] {msg}", xbmc.LOGINFO)
            def err_log_func_g_fb(msg): xbmc.log(f"[{ADDON_NAME}-globals_dir_fb] {msg}", xbmc.LOGERROR)
            log_func_g = log_func_g_fb
            err_log_func_g = err_log_func_g_fb
            log_func_g("Logger module not available yet during initialize_addon_data_dir, using direct xbmc.log.")

        if xbmcvfs.mkdirs(ADDON_DATA_PATH):
            log_func_g(f"Kreiran direktorijum za podatke addona: {ADDON_DATA_PATH}")
        else:
            err_log_func_g(f"Neuspešno kreiranje direktorijuma za podatke addona: {ADDON_DATA_PATH}")

initialize_addon_data_dir()