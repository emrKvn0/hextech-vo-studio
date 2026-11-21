# -*- coding: utf-8 -*-
"""
League of Legends - Doğrudan İstemci Başlatıcı (Stabil Checkpoint)
=================================================================
Riot Client yerel REST API'sini kullanarak doğrudan League of Legends istemcisini
tetikler. LoL tetiklendikten sonra kendini anında (sys.exit) kapatır.
Arka planda kesinlikle kalıcı hiçbir servis veya bellek kalıntısı bırakmaz.
"""
import os
import sys
import time
import ssl
import base64
import urllib.request
import urllib.error
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
            if 'leagueclientux' in p.info['name'].lower():
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

def main():
    log("=== League Direct Launcher Started ===")

    # 1. League of Legends zaten açıksa doğrudan çık
    if is_league_running():
        log("LeagueClientUx zaten açık.")
        sys.exit(0)

    # 2. Kalıntı lockfile temizliği
    clean_stale_lockfile()

    # 3. Riot Client çalışıyor mu kontrol et, çalışmıyorsa başlat
    riot_info = get_lockfile_info()
    if not riot_info:
        log("Riot Client çalışmıyor. Başlatılıyor...")
        os.startfile(
            SERVICES_EXE,
            "open",
            arguments="--launch-product=league_of_legends --launch-patchline=live",
            cwd=r"C:\Riot Games\Riot Client"
        )

        start_wait = time.time()
        while time.time() - start_wait < 15:
            riot_info = get_lockfile_info()
            if riot_info:
                log(f"Lockfile tespit edildi: Port {riot_info['port']} (PID {riot_info['pid']})")
                break
            time.sleep(0.15)

    if not riot_info:
        log("HATA: Riot Client lockfile bulunamadı.")
        sys.exit(0)

    port = riot_info["port"]
    token = riot_info["token"]

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    auth = base64.b64encode(f"riot:{token}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }

    launch_url = f"https://127.0.0.1:{port}/product-launcher/v1/products/league_of_legends/patchlines/live"

    # 4. API hazır olur olmaz POST ile doğrudan League Client'ı başlat
    start_req = time.time()
    while time.time() - start_req < 20:
        try:
            req = urllib.request.Request(launch_url, data=b"{}", headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=2) as resp:
                if resp.status in (200, 204):
                    log(f"Başlatma isteği başarılı (HTTP {resp.status})!")
                    break
        except urllib.error.HTTPError as e:
            if e.code in (423, 400, 409):
                log(f"İstemci zaten başlatılıyor veya aktif (HTTP {e.code}).")
                break
        except Exception:
            pass
        time.sleep(0.2)

    log("=== Direct Launcher Finished (Exiting) ===")
    sys.exit(0)

if __name__ == "__main__":
    main()
