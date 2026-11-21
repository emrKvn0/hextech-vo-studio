import os
import sys
import json
from analyze_competitor_channels import run_competitor_analysis, get_available_channels

def handle_competitors_get(handler, path, params, context):
    broadcast_log = context['broadcast_log']
    meta_mgr = context['meta_mgr']
    # 9. Get Available Competitor Channels
    if path == '/api/competitor-channels':
        handler.send_json({"status": "success", "data": get_available_channels()})
        return True

    # 10. Get Competitor YouTube Analysis
    if path == '/api/competitor-analysis':
        try:
            is_refresh = params.get('refresh', ['0'])[0] in ['1', 'true', 'True']
            channels_param = params.get('channels', [''])[0]
            selected_channels = [c.strip() for c in channels_param.split(',') if c.strip()] if channels_param else None

            chan_label = f" ({len(selected_channels)} seçili kanal)" if selected_channels else " (Tüm 6 kanal)"
            broadcast_log(f"🔍 YouTube Kanalları taranıyor{chan_label}...")

            res = run_competitor_analysis(meta_mgr.skins_raw_db, selected_channel_ids=selected_channels, force_refresh=is_refresh)
            broadcast_log(f"✅ YouTube Analizi Tamamlandı: {res['total_videos']} video incelendi, {len(res['uncovered_champions'])} şampiyon için fırsat bulundu!")
            handler.send_json({"status": "success", "data": res})
        except Exception as e:
            broadcast_log(f"❌ YouTube Analizi Hatası: {e}")
            handler.send_json({"status": "error", "message": str(e)}, 500)
        return True


    return False
