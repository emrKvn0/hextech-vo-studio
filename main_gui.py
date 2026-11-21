import sys
import os
import multiprocessing
import traceback
import ctypes

def log_crash(exc_type, exc_value, exc_traceback):
    err_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        crash_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log")
        with open(crash_file, "a", encoding="utf-8") as f:
            f.write("\n=== CRASH LOG ===\n" + err_str)
    except Exception:
        pass
    print("💥 CRASH:", err_str)
    try:
        if sys.platform == 'win32':
            ctypes.windll.user32.MessageBoxW(0, f"Uygulama başlatılırken bir hata oluştu:\n\n{err_str[:400]}", "LoL Medya Stüdyosu - Hata", 0x10)
    except Exception:
        pass

sys.excepthook = log_crash

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import json
import webview
from server_backend import start_server

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_PATH = os.path.join(ROOT_DIR, ".app_storage")
os.makedirs(STORAGE_PATH, exist_ok=True)
WINDOW_STATE_FILE = os.path.join(STORAGE_PATH, "window_state.json")

def load_window_state():
    state = {"width": 1340, "height": 860, "x": None, "y": None}
    if os.path.exists(WINDOW_STATE_FILE):
        try:
            with open(WINDOW_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    state.update(data)
        except Exception:
            pass
    return state

def save_window_state(w, h, x=None, y=None):
    if w and h and w >= 800 and h >= 500:
        try:
            data = {"width": int(w), "height": int(h), "x": int(x) if x is not None else None, "y": int(y) if y is not None else None}
            with open(WINDOW_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

def main():
    try:
        # Start embedded high-performance background HTTP server
        server, port = start_server(port=0)
        app_url = f"http://127.0.0.1:{port}/index.html"
        print(f"🚀 Hextech Studio yerel sunucusu başlatıldı: {app_url}")

        state = load_window_state()
        win_kwargs = {
            "title": "League of Legends Ses & Medya Stüdyosu",
            "url": app_url,
            "width": max(1100, state.get("width", 1340)),
            "height": max(700, state.get("height", 860)),
            "min_size": (1000, 650),
            "background_color": "#040810",
            "easy_drag": False
        }
        if state.get("x") is not None and state.get("y") is not None:
            win_kwargs["x"] = state["x"]
            win_kwargs["y"] = state["y"]

        window = webview.create_window(**win_kwargs)

        def on_closing():
            try:
                save_window_state(window.width, window.height, window.x, window.y)
            except Exception:
                pass

        def on_resized():
            try:
                save_window_state(window.width, window.height, window.x, window.y)
            except Exception:
                pass

        def on_moved():
            try:
                save_window_state(window.width, window.height, window.x, window.y)
            except Exception:
                pass

        window.events.closing += on_closing
        window.events.resized += on_resized
        window.events.moved += on_moved

        webview.start(debug=False, storage_path=STORAGE_PATH, private_mode=False)
    except Exception as e:
        log_crash(type(e), e, e.__traceback__)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
