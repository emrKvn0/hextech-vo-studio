import os
import sys
import subprocess

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("⚡ PyInstaller ile Bağımsız PyWebView .EXE Yeniden Derleniyor...")

cmd = [
    "pyinstaller",
    "--noconsole",
    "--windowed",
    "--name=LoL_Studio",
    f"--paths={os.path.join(ROOT_DIR, 'scripts')}",
    f"--paths={ROOT_DIR}",
    f"--add-data={os.path.join(ROOT_DIR, 'web')};web",
    f"--add-data={os.path.join(ROOT_DIR, 'scripts')};scripts",
    f"--add-data={os.path.join(ROOT_DIR, 'all_lol_skins_database.json')};.",
    f"--add-data={os.path.join(ROOT_DIR, 'vgmstream')};vgmstream",
    "--hidden-import=webview",
    "--hidden-import=webview.platforms.winforms",
    "--hidden-import=webview.platforms.edgechromium",
    "--hidden-import=server_backend",
    "--hidden-import=http.server",
    "--hidden-import=socketserver",
    "--hidden-import=metadata_manager",
    "--hidden-import=event_categorizer",
    "--hidden-import=lol_voice_extractor_expert",
    "--hidden-import=extract_target_references",
    "--hidden-import=analyze_competitor_channels",
    "--hidden-import=xml.etree.ElementTree",
    "--hidden-import=concurrent.futures",
    "--hidden-import=zstandard",
    "--hidden-import=urllib.request",
    "--clean",
    "-y",
    os.path.join(ROOT_DIR, "main_gui.py")
]

print(f"Komut: {' '.join(cmd)}")
res = subprocess.run(cmd, cwd=ROOT_DIR)

if res.returncode == 0:
    print("\n✅ DERLEME BAŞARILI! dist/LoL_Studio/LoL_Studio.exe hazır!")
else:
    print(f"\n❌ Derleme hatası: {res.returncode}")
