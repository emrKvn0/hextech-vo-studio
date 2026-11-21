import os
import sys
import json

# Add scripts to sys.path
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import static_wallpaper_engine

def handle_static_wallpapers_get(handler, path, params, context):
    broadcast_log = context['broadcast_log']

    # 1. Get champions list
    if path == '/api/static-wallpapers/champions':
        try:
            champs = static_wallpaper_engine.get_all_champions()
            handler.send_json({"status": "success", "data": champs})
        except Exception as e:
            handler.send_json({"status": "error", "message": str(e)}, 500)
        return True

    # 2. Get champion skins
    if path == '/api/static-wallpapers/skins':
        champ = params.get('champion', [''])[0]
        if not champ:
            handler.send_json({"status": "error", "message": "Şampiyon belirtilmedi"}, 400)
            return True
        try:
            skins = static_wallpaper_engine.get_champion_skins(champ)
            handler.send_json({"status": "success", "data": skins})
        except Exception as e:
            handler.send_json({"status": "error", "message": str(e)}, 500)
        return True

    # 3. Search skins or champions
    if path == '/api/static-wallpapers/search':
        query = params.get('q', [''])[0]
        try:
            results = static_wallpaper_engine.search_skins(query)
            handler.send_json({"status": "success", "data": results})
        except Exception as e:
            handler.send_json({"status": "error", "message": str(e)}, 500)
        return True

    # 4. Get downloaded static wallpapers
    if path == '/api/static-wallpapers/downloaded':
        try:
            files = static_wallpaper_engine.get_downloaded_static_wallpapers()
            handler.send_json({"status": "success", "data": files})
        except Exception as e:
            handler.send_json({"status": "error", "message": str(e)}, 500)
        return True

    # 5. Serve local downloaded wallpaper image preview
    if path == '/api/static-wallpapers/preview':
        file_path = params.get('file', [''])[0]
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                handler.send_response(200)
                ext = os.path.splitext(file_path)[1].lower()
                mime = 'image/jpeg' if ext in ['.jpg', '.jpeg'] else 'image/png'
                handler.send_header('Content-Type', mime)
                handler.send_header('Content-Length', str(len(content)))
                handler.send_header('Cache-Control', 'max-age=86400')
                handler.end_headers()
                handler.wfile.write(content)
                return True
            except Exception as e:
                handler.send_json({"status": "error", "message": str(e)}, 500)
                return True
        else:
            handler.send_json({"status": "error", "message": "Dosya bulunamadı"}, 404)
            return True

    return False

def handle_static_wallpapers_post(handler, path, body, context):
    broadcast_log = context['broadcast_log']

    # 1. Download static wallpaper
    if path == '/api/static-wallpapers/download':
        skin_data = body.get('skin', {})
        force_4k = body.get('force_4k', True)
        set_desktop = body.get('set_desktop', False)

        if not skin_data:
            handler.send_json({"status": "error", "message": "Geçersiz kostüm verisi"}, 400)
            return True

        c_name = skin_data.get('champion_name') or skin_data.get('champion_alias') or 'Şampiyon'
        s_name = skin_data.get('name_tr') or skin_data.get('name_en') or 'Kostüm'
        broadcast_log(f"🖼️ 4K Normal Duvar Kağıdı İndiriliyor: {c_name} - {s_name}...")

        try:
            result = static_wallpaper_engine.download_skin_wallpaper(
                skin_data=skin_data,
                force_4k=force_4k,
                set_as_desktop=set_desktop
            )
            broadcast_log(f"✨ 4K Duvar Kağıdı Başarıyla İndirildi: {result.get('file_name')} ({result.get('resolution')}, {result.get('file_size_mb')} MB)")
            if result.get('desktop_set'):
                broadcast_log("🖥️ Windows Masaüstü Duvar Kağıdı Güncellendi!")
            handler.send_json(result)
        except Exception as e:
            broadcast_log(f"❌ 4K Duvar Kağıdı İndirme Hatası: {str(e)}")
            handler.send_json({"status": "error", "message": str(e)}, 500)
        return True

    # 2. Set desktop wallpaper directly
    if path == '/api/static-wallpapers/set-desktop':
        file_path = body.get('file_path')
        if not file_path or not os.path.exists(file_path):
            handler.send_json({"status": "error", "message": "Dosya bulunamadı"}, 404)
            return True
        success = static_wallpaper_engine.set_desktop_wallpaper(file_path)
        if success:
            broadcast_log(f"🖥️ Masaüstü Arka Planı Değiştirildi: {os.path.basename(file_path)}")
            handler.send_json({"status": "success"})
        else:
            handler.send_json({"status": "error", "message": "Masaüstü ayarlanamadı"}, 500)
        return True

    # 3. Open download folder
    if path == '/api/static-wallpapers/open-folder':
        champ_name = body.get('champ_name')
        opened = static_wallpaper_engine.open_download_folder(champ_name)
        broadcast_log(f"📂 4K Duvar Kağıtları Klasörü Açıldı: {opened}")
        handler.send_json({"status": "success", "folder": opened})
        return True

    # 4. Delete downloaded wallpaper
    if path == '/api/static-wallpapers/delete':
        file_path = body.get('file_path')
        if not file_path:
            handler.send_json({"status": "error", "message": "Geçersiz dosya"}, 400)
            return True
        deleted = static_wallpaper_engine.delete_downloaded_wallpaper(file_path)
        if deleted:
            broadcast_log(f"🗑️ 4K Duvar Kağıdı Silindi: {os.path.basename(file_path)}")
            handler.send_json({"status": "success"})
        else:
            handler.send_json({"status": "error", "message": "Silinemedi"}, 500)
        return True

    return False
