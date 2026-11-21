# -*- coding: utf-8 -*-
"""
League of Legends - Doğrudan ve Güvenli İstemci Başlatıcı
=========================================================
1. Doğrudan yerel Riot API üzerinden League of Legends'ı başlatmayı dener.
2. API yanıt vermezse veya gecikirse, resmi başlatma komutu ile normal şekilde
   LoL istemcisini açar (böylece görev çubuğunda veya masaüstünde asla takılmaz).
3. LoL tetiklendikten sonra kendini anında (sys.exit) kapatır.
"""
import os
import sys
import time
import ssl
import base64
import urllib.request
import urllib.error
import subprocess
import psutil

SERVICES_EXE = r"C:\Riot Games\Riot Client\RiotClientServices.exe"
LOCKFILE = os.path.expandvars(r"%LOCALAPPDATA%\Riot Games\Riot Client\Config\lockfile")
LOG_FILE = os.path.expandvars(r"%LOCALAPPDATA%\Riot Games\direct_launch.log")

def log(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

def is_league_running():
    for p in psutil.process_iter(['name']):
        try:
            n = p.info['name'].lower()
            if 'leagueclientux.exe' == n or 'leagueclient.exe' == n:
                return True
        except Exception:
            pass
    return False

def clean_stale_lockfile():
    if os.path.exists(LOCKFILE):
        try:
            with open(LOCKFILE, "r", encoding="utf-8") as f:
                parts = f.read().strip().split(":")
                if len(parts) >= 2 and not psutil.pid_exists(int(parts[1])):
                    os.remove(LOCKFILE)
        except Exception:
            pass

def get_lockfile_info():
    if not os.path.exists(LOCKFILE):
        return None
    try:
        with open(LOCKFILE, "r", encoding="utf-8") as f:
            parts = f.read().strip().split(":")
            if len(parts) >= 5 and psutil.pid_exists(int(parts[1])):
                return {
                    "name": parts[0],
                    "pid": int(parts[1]),
                    "port": int(parts[2]),
                    "token": parts[3],
                    "protocol": parts[4]
                }
    except Exception:
        pass
    return None

def fallback_launch():
    """Resmi komutla normal şekilde LoL'ü başlatır."""
    log("Resmi komut ile LoL başlatılıyor (Normal başlatma)...")
    try:
        os.startfile(
            SERVICES_EXE,
            "open",
            arguments="--launch-product=league_of_legends --launch-patchline=live",
            cwd=r"C:\Riot Games\Riot Client"
        )
        return True
    except Exception as e:
        log(f"Normal başlatma hatası: {e}")
        return False

def try_api_launch(port, token):
    """Yerel REST API üzerinden doğrudan LoL'ü tetiklemeyi dener."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    auth = base64.b64encode(f"riot:{token}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }

    launch_url = f"https://127.0.0.1:{port}/product-launcher/v1/products/league_of_legends/patchlines/live"

    try:
        req = urllib.request.Request(launch_url, data=b"{}", headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=3) as resp:
            if resp.status in (200, 204):
                log(f"Doğrudan başlatma API isteği kabul edildi (HTTP {resp.status})!")
                return True
    except urllib.error.HTTPError as e:
        if e.code in (423, 400, 409):
            log(f"İstemci zaten sıraya alındı / aktif (HTTP {e.code}).")
            return True
        log(f"API HTTP Hatası: {e.code}")
    except Exception as e:
        log(f"API Bağlantı Hatası: {e}")
    return False

def main():
    log("=== League Direct Launcher Başlatıldı ===")

    # 1. League of Legends zaten açıksa doğrudan çık
    if is_league_running():
        log("League of Legends zaten açık. Çıkılıyor.")
        sys.exit(0)

    # 2. Kalıntı lockfile temizliği
    clean_stale_lockfile()

    # 3. Riot Client açık mı?
    riot_info = get_lockfile_info()
    api_success = False

    if riot_info:
        log(f"Riot Client aktif tespit edildi (Port: {riot_info['port']}). Doğrudan başlatma deneniyor...")
        # 3 saniye boyunca API ile doğrudan başlatmayı dene
        start_req = time.time()
        while time.time() - start_req < 3:
            if try_api_launch(riot_info["port"], riot_info["token"]):
                api_success = True
                break
            time.sleep(0.3)

    # 4. API başarılı olamadıysa veya Riot Client kapalıysa resmi normal başlatmayı yap
    if not api_success:
        if not is_league_running():
            fallback_launch()

    log("=== Başlatıcı Görevini Tamamladı. Kapanıyor (sys.exit) ===")
    sys.exit(0)

if __name__ == "__main__":
    main()
