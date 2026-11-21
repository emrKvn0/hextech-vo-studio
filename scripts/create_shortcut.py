import os
import sys
import subprocess

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

desktop_dir = os.path.expanduser("~/Desktop")
shortcut_path = os.path.join(desktop_dir, "LoL Ses ve Video Studyosu.lnk")
target_exe = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist", "LoL_Studio", "LoL_Studio.exe")
work_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist", "LoL_Studio")

ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
$Shortcut.TargetPath = '{target_exe}'
$Shortcut.WorkingDirectory = '{work_dir}'
$Shortcut.Description = 'League of Legends Ses & Video Otomasyon Studyosu'
$Shortcut.Save()
"""

cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script]
res = subprocess.run(cmd, capture_output=True, text=True)

if os.path.exists(shortcut_path):
    print(f"✅ Masaüstü .EXE kısayolu başarıyla güncellendi: {shortcut_path}")
else:
    print(f"Hata: {res.stderr}")
