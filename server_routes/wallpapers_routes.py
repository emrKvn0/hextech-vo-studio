import os
import sys
import json
import wallpaper_engine

def handle_wallpapers_get(handler, path, params, context):
    broadcast_log = context['broadcast_log']
    # 11. Wallpapers Search API (DesktopHut, MotionBGS, YouTube)
    if path == '/api/wallpapers/search':
        query = params.get('q', [''])[0]
        source = params.get('source', ['all'])[0]
        resolution = params.get('resolution', ['all'])[0]
        try:
            results = wallpaper_engine.search_wallpapers(query=query, source=source, resolution=resolution)
            handler.send_json({"status": "success", "data": results})
        except Exception as e:
            handler.send_json({"status": "error", "message": str(e)}, 500)
        return True

    # 12. Wallpapers Downloaded List
    if path == '/api/wallpapers/downloaded':
        try:
            files = wallpaper_engine.get_downloaded_wallpapers()
            handler.send_json({"status": "success", "data": files})
        except Exception as e:
            handler.send_json({"status": "error", "message": str(e)}, 500)
        return True

    # 13. Wallpapers Active Download Status
    if path == '/api/wallpapers/status':
        dl_id = params.get('id', [''])[0]
        if dl_id:
            data = wallpaper_engine.ACTIVE_DOWNLOADS.get(dl_id, {"status": "unknown"})
        else:
            data = wallpaper_engine.ACTIVE_DOWNLOADS
        handler.send_json({"status": "success", "data": data})
        return True


    return False

def handle_wallpapers_post(handler, path, body, context):
    broadcast_log = context['broadcast_log']
    # 10. Wallpapers Download Start
    if path == '/api/wallpapers/download':
        item_data = body.get('item', {})
        champ_name = body.get('champ_name')
        title = item_data.get('title', 'Duvar Kağıdı')
        if not item_data:
            handler.send_json({"status": "error", "message": "Geçersiz veri"}, 400)
            return True
        broadcast_log(f"🎬 Canlı Duvar Kağıdı İndirme Başlatıldı: {title} ({item_data.get('source', '')})")
        dl_id = wallpaper_engine.start_download_async(item_data, champ_name=champ_name)
        handler.send_json({"status": "started", "download_id": dl_id})
        return True

    # 11. Wallpapers Open Download Folder
    if path == '/api/wallpapers/open-folder':
        champ_name = body.get('champ_name')
        opened = wallpaper_engine.open_download_folder(champ_name=champ_name)
        broadcast_log(f"📂 Duvar Kağıtları Klasörü Açıldı: {opened}")
        handler.send_json({"status": "success", "folder": opened})
        return True


    return False
