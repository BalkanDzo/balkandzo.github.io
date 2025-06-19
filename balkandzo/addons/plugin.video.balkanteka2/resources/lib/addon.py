# -*- coding: utf-8 -*-
# Naziv datoteke: addon.py

import sys
import xbmc
import xbmcaddon
import xbmcgui
import platform 

try:
    _addon_for_log = xbmcaddon.Addon()
    _addon_id_for_log = _addon_for_log.getAddonInfo('id')
except Exception as e:
    xbmc.log(f"[AddonDispatcher] Greška pri inicijalizaciji Addona za logiranje: {e}", xbmc.LOGERROR)
    _addon_id_for_log = "plugin.video.balkanteka2"

def log_dispatcher(message, level=xbmc.LOGINFO):
    xbmc.log(f"[{_addon_id_for_log} - Dispatcher] {message}", level=level)

_KODI_HANDLE_DISPATCHER = -1
if len(sys.argv) > 1 and sys.argv[1].isdigit():
    _KODI_HANDLE_DISPATCHER = int(sys.argv[1])

_PARAMS_STRING_DISPATCHER = ""
if len(sys.argv) > 2:
    _PARAMS_STRING_DISPATCHER = sys.argv[2]

log_dispatcher(f"Pokrenut. Handle: {_KODI_HANDLE_DISPATCHER}, Params: '{_PARAMS_STRING_DISPATCHER[:100]}...'")

try:
    is_windows = xbmc.getCondVisibility('System.Platform.Windows')
    is_android = xbmc.getCondVisibility('System.Platform.Android')
    is_linux = xbmc.getCondVisibility('System.Platform.Linux') and not is_android 
    is_osx = xbmc.getCondVisibility('System.Platform.OSX') 
    is_ios = xbmc.getCondVisibility('System.Platform.IOS') or xbmc.getCondVisibility('System.Platform.TVOS')

    if is_windows:
        log_dispatcher("Detektirana Windows platforma. Učitavam windows_logic.py")
        import windows_logic 
        windows_logic.router(_PARAMS_STRING_DISPATCHER)
        
    elif is_android:
        log_dispatcher("Detektirana Android platforma. Učitavam android_logic.py")
        import android_logic
        android_logic.router(_PARAMS_STRING_DISPATCHER)
        
    elif is_linux:
        log_dispatcher("Detektirana Linux (desktop) platforma. Učitavam android_logic.py (xbmcvfs baza).")
        import android_logic 
        android_logic.router(_PARAMS_STRING_DISPATCHER)
        
    elif is_osx:
        log_dispatcher("Detektirana macOS platforma. Učitavam android_logic.py (xbmcvfs baza).")
        import android_logic
        android_logic.router(_PARAMS_STRING_DISPATCHER)
        
    elif is_ios:
        log_dispatcher("Detektirana iOS/tvOS platforma. Učitavam android_logic.py (xbmcvfs baza).")
        import android_logic
        android_logic.router(_PARAMS_STRING_DISPATCHER)
        
    else: 
        current_os_name = platform.system().lower()
        log_dispatcher(f"Detektiran OS: {current_os_name}. Učitavam android_logic.py (xbmcvfs baza) kao zadano.")
        import android_logic 
        android_logic.router(_PARAMS_STRING_DISPATCHER)

except Exception as e:
    log_dispatcher(f"Kritična greška u OS dispatcheru ili pri učitavanju/izvršavanju platformskog modula: {e}", xbmc.LOGERROR)
    import traceback
    log_dispatcher(traceback.format_exc(), xbmc.LOGERROR)
    try:
        xbmcgui.Dialog().ok(f"{_addon_id_for_log} - Greška", f"Došlo je do greške pri pokretanju dodatka za vašu platformu.\nMolimo provjerite log za detalje.\nGreška: {e}")
    except:
        pass 
    
    if _KODI_HANDLE_DISPATCHER != -1:
        try:
            import xbmcplugin 
            xbmcplugin.endOfDirectory(handle=_KODI_HANDLE_DISPATCHER, succeeded=False)
            log_dispatcher("Pozvan endOfDirectory(False) zbog greške u dispatcheru.")
        except Exception as e_end:
            log_dispatcher(f"Greška pri pokušaju endOfDirectory u dispatcher error handleru: {e_end}", xbmc.LOGERROR)