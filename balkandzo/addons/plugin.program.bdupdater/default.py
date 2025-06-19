import os
import urllib.request
import urllib.error
import zipfile
import xbmc
import xbmcgui
import xbmcvfs
import time

ADDONS_FOLDER = xbmcvfs.translatePath('special://home/')

def check_url_available(url):
    try:
        request = urllib.request.Request(url, method='HEAD')
        response = urllib.request.urlopen(request, timeout=10)
        return response.status == 200
    except Exception as e:
        xbmc.log(f"URL check error: {str(e)}", level=xbmc.LOGERROR)
        return False

def download_and_extract_zip(url, destination_folder):
    zip_path = os.path.join(destination_folder, 'addon.zip')
    dp = None
    download_successful = False

    try:
        dp = xbmcgui.DialogProgress()
        dp.create("Preuzimanje dodatka")
        dp.update(0, "Molimo sačekajte, inicijalizacija...")
        
        xbmc.log(f"Attempting to download from: {url}", level=xbmc.LOGINFO)
        with urllib.request.urlopen(url, timeout=30) as response:
            content_length_header = response.headers.get('content-length')
            total_size = 0
            if content_length_header and content_length_header.isdigit():
                total_size = int(content_length_header)
            
            downloaded = 0
            
            if total_size > 0:
                line1 = f"Ukupna veličina: {total_size // 1024}KB"
                line2 = "Započinjanje preuzimanja..."
                dp.update(0, f"{line1}\n{line2}")
            else:
                line1 = "Započinjanje preuzimanja..."
                line2 = "Ukupna veličina nepoznata."
                dp.update(0, f"{line1}\n{line2}")

            start_time = time.time()
            
            with open(zip_path, 'wb') as f:
                while True:
                    if dp.iscanceled():
                        xbmc.log("Download cancelled by user.", level=xbmc.LOGINFO)
                        break
                    
                    chunk = response.read(8192)
                    if not chunk:
                        download_successful = True
                        break
                    
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        percent = min(int((downloaded * 100) / total_size), 100)
                        elapsed_time = time.time() - start_time
                        speed = (downloaded / elapsed_time / 1024) if elapsed_time > 0 else 0
                        
                        line1_msg = f"Preuzeto: {downloaded // 1024}KB / {total_size // 1024}KB"
                        line2_msg = f"Status: {percent}% ({speed:.1f} KB/s)"
                        dp.update(percent, f"{line1_msg}\n{line2_msg}")
                    else:
                        spinner_percent = (downloaded // 8192) % 101
                        line1_msg = f"Preuzeto: {downloaded // 1024}KB"
                        line2_msg = "Veličina nepoznata, preuzimanje u toku..."
                        dp.update(spinner_percent, f"{line1_msg}\n{line2_msg}")
        
        if dp.iscanceled():
             xbmcgui.Dialog().notification("Preuzimanje", "Preuzimanje otkazano.", xbmcgui.NOTIFICATION_WARNING, 3000)

    except Exception as e:
        xbmcgui.Dialog().notification("Greška", f"Došlo je do greške: {str(e)}", xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmc.log(f"An error occurred: {str(e)}", level=xbmc.LOGERROR)
        download_successful = False
    finally:
        if dp:
            try:
                dp.close()
            except RuntimeError:
                xbmc.log("Dialog could not be closed as it was not created.", level=xbmc.LOGDEBUG)
            dp = None

    if not download_successful:
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
                xbmc.log(f"Removed incomplete/failed download: {zip_path}", level=xbmc.LOGINFO)
            except Exception as remove_err:
                xbmc.log(f"Error removing zip after failed download: {str(remove_err)}", level=xbmc.LOGERROR)
        return

    try:
        xbmcgui.Dialog().notification("Ekstrakcija", "Ekstrakcija dodatka je u toku...", xbmcgui.NOTIFICATION_INFO, 5000)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(destination_folder)
        xbmcgui.Dialog().notification("Ekstrakcija", "Ekstrakcija završena.", xbmcgui.NOTIFICATION_INFO, 3000)
        xbmc.log(f"Successfully extracted to: {destination_folder}", level=xbmc.LOGINFO)

        try:
            os.remove(zip_path)
            xbmc.log(f"Removed zip file: {zip_path}", level=xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"Could not remove zip file {zip_path}: {str(e)}", level=xbmc.LOGWARNING)

        time.sleep(2)

        line1 = 'Potrebno je restartovati Kodi da bi se ažurirale promene.'
        line2 = 'Da li želite sada da restartujete?'
        full_message = f"{line1}\n{line2}"

        result = xbmcgui.Dialog().yesno(
            'Restart Kodi',
            full_message,
            yeslabel="Restartuj",
            nolabel="Ne kasnije"
        )
        if result:
            xbmc.executebuiltin('Quit()')

    except zipfile.BadZipFile:
        xbmcgui.Dialog().notification("Greška ZIP fajla", "Preuzeti fajl nije ispravna ZIP arhiva.", xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmc.log("BadZipFile during extraction.", level=xbmc.LOGERROR)
    except Exception as e:
        xbmcgui.Dialog().notification("Greška", f"Greška prilikom instalacije: {str(e)}", xbmcgui.NOTIFICATION_ERROR, 5000)
        xbmc.log(f"Extraction or post-download error: {str(e)}", level=xbmc.LOGERROR)

if __name__ == '__main__':
    ZIP_URL = 'https://github.com/BalkanDzo/balkandzo.github.io/raw/refs/heads/main/zips/updates.zip'

    xbmc.log("Addon execution started.", level=xbmc.LOGINFO)
    if check_url_available(ZIP_URL):
        xbmc.log(f"URL {ZIP_URL} is available. Starting download and extract process.", level=xbmc.LOGINFO)
        download_and_extract_zip(ZIP_URL, ADDONS_FOLDER)
    else:
        xbmc.log(f"URL {ZIP_URL} is not available or check failed.", level=xbmc.LOGWARNING)
        xbmcgui.Dialog().notification("Obaveštenje", "Trenutno nema dostupnih ažuriranja.", xbmcgui.NOTIFICATION_WARNING, 5000)
    
    xbmc.log("Addon execution finished.", level=xbmc.LOGINFO)