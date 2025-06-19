# logger.py
from __future__ import absolute_import, division, unicode_literals
import xbmc
import xbmcaddon

ADDON_INSTANCE = xbmcaddon.Addon()
ADDON_ID = ADDON_INSTANCE.getAddonInfo('id')
ADDON_NAME = ADDON_INSTANCE.getAddonInfo('name')

class Logger:
    @staticmethod
    def log(message, level=xbmc.LOGINFO):
        try:
            log_message = f"[{ADDON_NAME}] {str(message)}"
            xbmc.log(log_message, level)
        except Exception as e:
            xbmc.log(f"[{ADDON_NAME}] Error in logger: {str(e)}", xbmc.LOGERROR)
            xbmc.log(f"[{ADDON_NAME}] Original message (partial): {str(message)[:200]}", xbmc.LOGERROR)

    @staticmethod
    def info(message):
        Logger.log(message, xbmc.LOGINFO)

    @staticmethod
    def error(message, level=xbmc.LOGERROR): 
        Logger.log(message, level) 

    @staticmethod
    def warning(message):
        Logger.log(message, xbmc.LOGWARNING)

    @staticmethod
    def debug(message):
        Logger.log(message, xbmc.LOGDEBUG)