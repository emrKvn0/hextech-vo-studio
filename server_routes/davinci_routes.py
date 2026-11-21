import os
import sys
import json
from davinci_exporter import DaVinciTimelineExporter
from davinci_resolve_api import DaVinciResolveAPI

def handle_davinci_post(handler, path, body, context):
    ROOT_DIR = context['ROOT_DIR']
    CHAMPIONS_OUTPUT_PATH = context['CHAMPIONS_OUTPUT_PATH']
    broadcast_log = context['broadcast_log']
    # 4. DaVinci Resolve Timeline Exporter (with Dynamic Gap & Text+ Fade)
    if path == '/api/export-davinci':
        champion = body.get('champion', '')
        skin = body.get('skin', '')
        try:
            gap_seconds = float(body.get('gap_seconds', 0.8))
        except Exception:
            gap_seconds = 0.8
        try:
            fade_in_seconds = float(body.get('fade_in_seconds', 0.5))
        except Exception:
            fade_in_seconds = 0.5
        try:
            fade_out_seconds = float(body.get('fade_out_seconds', 0.3))
        except Exception:
            fade_out_seconds = 0.3
        try:
            fps = int(body.get('fps', 60))
        except Exception:
            fps = 60
        custom_files = body.get('audio_files', [])
        include_splash = bool(body.get('include_splash', True))
        include_subtitles = bool(body.get('include_subtitles', True)) if 'include_subtitles' in body else bool(body.get('include_text', True))
        background_media = body.get('background_media', None)
        try:
            splash_zoom = float(body.get('splash_zoom', 0.6))
        except Exception:
            splash_zoom = 0.6
        try:
            splash_pos_x = float(body.get('splash_pos_x', -430))
        except Exception:
            splash_pos_x = -430
        try:
            splash_pos_y = float(body.get('splash_pos_y', 160))
        except Exception:
            splash_pos_y = 160
        try:
            text_pos_x = float(body.get('text_pos_x', -430))
        except Exception:
            text_pos_x = -430
        try:
            text_pos_y = float(body.get('text_pos_y', -450))
        except Exception:
            text_pos_y = -450
        try:
            text_zoom = float(body.get('text_zoom', 1.0))
        except Exception:
            text_zoom = 1.0
        try:
            timeline_w = int(body.get('timeline_w', 2560))
        except Exception:
            timeline_w = 2560
        try:
            timeline_h = int(body.get('timeline_h', 1440))
        except Exception:
            timeline_h = 1440

        try:
            files_to_export = []
            if custom_files and isinstance(custom_files, list) and len(custom_files) > 0:
                files_to_export = [f for f in custom_files if os.path.isfile(f)]

            if not files_to_export:
                search_dir = None
                if champion:
                    champ_clean = champion.lower().replace("'", "").replace(" ", "").replace("_", "")
                    real_champ_dir = None
                    if os.path.exists(CHAMPIONS_OUTPUT_PATH):
                        for cd in os.listdir(CHAMPIONS_OUTPUT_PATH):
                            if cd.lower().replace("'", "").replace(" ", "").replace("_", "") == champ_clean:
                                real_champ_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, cd)
                                break

                    if real_champ_dir and os.path.exists(real_champ_dir):
                        search_dir = real_champ_dir
                        if skin and skin != 'ALL':
                            skin_norm = skin.lower().replace("'", "").replace(" ", "").replace("_", "")
                            for sd in os.listdir(real_champ_dir):
                                sd_norm = sd.lower().replace("'", "").replace(" ", "").replace("_", "")
                                if skin_norm in sd_norm or sd_norm in skin_norm:
                                    search_dir = os.path.join(real_champ_dir, sd)
                                    break

                if search_dir and os.path.exists(search_dir):
                    for root, _, fnames in os.walk(search_dir):
                        for fn in sorted(fnames):
                            if fn.lower().endswith('.wav'):
                                files_to_export.append(os.path.join(root, fn))

            if not files_to_export:
                handler.send_json({
                    "status": "error", 
                    "message": f"'{champion or 'Seçili'}' için henüz çıkarılmış ses dosyası bulunamadı. Lütfen önce yukarıdaki 'Seçili Kostümü Çıkar' butonuna basın."
                }, 200)
                return True

            # Target XML output path
            safe_champ = (champion or 'LoL_Sesler').replace(' ', '_')
            safe_skin = (skin or 'Replikler').replace(' ', '_')

            target_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, safe_champ)
            if os.path.exists(CHAMPIONS_OUTPUT_PATH):
                for d in os.listdir(CHAMPIONS_OUTPUT_PATH):
                    if d.lower().replace('_', '').replace(' ', '') == safe_champ.lower().replace('_', '').replace(' ', ''):
                        target_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, d)
                        break

            # If this is a reference export (custom files provided)
            if custom_files:
                ref_dir = os.path.join(target_dir, f"{safe_champ}e_Yapilan_Tum_Ozel_Atiflar")
                if os.path.exists(ref_dir):
                    target_dir = ref_dir
                xml_name = f"{safe_champ}_{safe_skin}_Secilen_{len(files_to_export)}ses_DaVinci_{gap_seconds}s.xml"
            else:
                xml_name = f"{safe_champ}_{safe_skin}_DaVinci_{gap_seconds}s_Gap.xml"
                if skin and skin != 'ALL':
                    skin_path = os.path.join(target_dir, safe_skin)
                    if os.path.exists(skin_path):
                        target_dir = skin_path
                    elif os.path.exists(target_dir):
                        for sd in os.listdir(target_dir):
                            if sd.lower().replace('_', '').replace(' ', '') == safe_skin.lower().replace('_', '').replace(' ', ''):
                                target_dir = os.path.join(target_dir, sd)
                                break

            # Create dedicated DaVinci_XML subfolder
            xml_dir = os.path.join(target_dir, "DaVinci_XML")
            os.makedirs(xml_dir, exist_ok=True)
            out_xml_path = os.path.join(xml_dir, xml_name)

            t_name = f"{champion} {skin} ({gap_seconds}s Gap)".strip()
            saved_path, count, total_dur = DaVinciTimelineExporter.generate_fcp7_xml(
                files_to_export,
                out_xml_path,
                gap_seconds=gap_seconds,
                timeline_name=t_name,
                fps=fps,
                smart_sort=True,
                exclude_sfx=True,
                target_champion=champion,
                generate_srt=include_subtitles,
                include_text=include_subtitles,
                fade_in_seconds=fade_in_seconds,
                fade_out_seconds=fade_out_seconds,
                background_media=background_media,
                include_splash=include_splash,
                splash_pos_x=splash_pos_x,
                splash_pos_y=splash_pos_y,
                splash_zoom=splash_zoom,
                text_pos_x=text_pos_x,
                text_pos_y=text_pos_y,
                text_zoom=text_zoom,
                timeline_w=timeline_w,
                timeline_h=timeline_h
            )

            setting_path = os.path.splitext(saved_path)[0] + "_Daktilo_TextPlus.setting"
            has_setting = os.path.isfile(setting_path)

            broadcast_log(f"🎬 DaVinci Resolve Timeline hazırlandı: {xml_name} ({count} ses, {gap_seconds}s aralık, In:{fade_in_seconds}s Out:{fade_out_seconds}s, {total_dur:.1f}s)")
            if has_setting:
                broadcast_log(f"✨ Daktilo animasyonlu Text+ Fusion şablonu panonuza kopyalandı! DaVinci Fusion sayfasına geçip Ctrl+V yapabilirsiniz.")

            handler.send_json({
                "status": "success",
                "file_path": saved_path,
                "file_name": xml_name,
                "fcpxml_path": saved_path.replace('.xml', '.fcpxml'),
                "srt_path": saved_path.replace('.xml', '.srt'),
                "setting_path": setting_path if has_setting else None,
                "setting_name": os.path.basename(setting_path) if has_setting else None,
                "clipboard_copied": has_setting,
                "clip_count": count,
                "clips_count": count,
                "total_duration": total_dur,
                "total_duration_sec": total_dur,
                "gap_seconds": gap_seconds,
                "fade_in_seconds": fade_in_seconds,
                "fade_out_seconds": fade_out_seconds,
                "fps": fps
            })
            return True
        except Exception as e:
            broadcast_log(f"❌ DaVinci Export Hatası: {e}")
            handler.send_json({"status": "error", "message": str(e)}, 500)
            return True

    # 4.1 DaVinci Resolve Python Scripting API Status
    if path == '/api/davinci-status':
        try:
            status = DaVinciResolveAPI.get_status()
            handler.send_json(status)
        except Exception as e:
            handler.send_json({"connected": False, "message": str(e)}, 200)
        return True

    # 4.2 DaVinci Resolve Python Scripting Direct Push (Sesler + Text+ Timeline)
    if path == '/api/davinci-direct-push':
        champion = body.get('champion', '')
        skin = body.get('skin', '')
        try:
            gap_seconds = float(body.get('gap_seconds', 0.2))
        except Exception:
            gap_seconds = 0.2
        try:
            fade_in_sec = float(body.get('fade_in_seconds', 1.5))
        except Exception:
            fade_in_sec = 1.5
        try:
            fade_out_sec = float(body.get('fade_out_seconds', 0.5))
        except Exception:
            fade_out_sec = 0.5
        try:
            fps = int(body.get('fps', 60))
        except Exception:
            fps = 60
        custom_files = body.get('audio_files', [])

        try:
            files_to_export = []
            if custom_files and isinstance(custom_files, list) and len(custom_files) > 0:
                files_to_export = [f for f in custom_files if os.path.isfile(f)]

            if not files_to_export:
                search_dir = None
                if champion:
                    champ_clean = champion.lower().replace("'", "").replace(" ", "").replace("_", "")
                    real_champ_dir = None
                    if os.path.exists(CHAMPIONS_OUTPUT_PATH):
                        for cd in os.listdir(CHAMPIONS_OUTPUT_PATH):
                            if cd.lower().replace("'", "").replace(" ", "").replace("_", "") == champ_clean:
                                real_champ_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, cd)
                                break

                    if real_champ_dir and os.path.exists(real_champ_dir):
                        search_dir = real_champ_dir
                        if skin and skin != 'ALL':
                            skin_norm = skin.lower().replace("'", "").replace(" ", "").replace("_", "")
                            for sd in os.listdir(real_champ_dir):
                                sd_norm = sd.lower().replace("'", "").replace(" ", "").replace("_", "")
                                if skin_norm in sd_norm or sd_norm in skin_norm:
                                    search_dir = os.path.join(real_champ_dir, sd)
                                    break

                if search_dir and os.path.exists(search_dir):
                    for root, _, fnames in os.walk(search_dir):
                        for fn in sorted(fnames):
                            if fn.lower().endswith('.wav'):
                                files_to_export.append(os.path.join(root, fn))

            if not files_to_export:
                handler.send_json({"status": "error", "message": "DaVinci'ye aktarılacak ses dosyası bulunamadı."}, 200)
                return True

            broadcast_log(f"⚡ DaVinci Resolve Python API ile doğrudan Timeline oluşturuluyor ({len(files_to_export)} ses, Text+ Fade: In {fade_in_sec}s / Out {fade_out_sec}s)...")
            res = DaVinciResolveAPI.create_direct_timeline_with_textplus(
                files_to_export,
                timeline_name=f"{champion} {skin}".strip() or "LoL Replikler",
                gap_seconds=gap_seconds,
                fade_in_sec=fade_in_sec,
                fade_out_sec=fade_out_sec,
                fps=fps,
                target_champion=champion
            )
            broadcast_log(f"✨ {res.get('message', 'DaVinci Timeline hazır!')}")
            handler.send_json(res)
        except Exception as e:
            broadcast_log(f"❌ DaVinci Direct Push Hatası: {e}")
            handler.send_json({"status": "error", "message": str(e)}, 500)
        return True

    # 4.3 DaVinci Resolve Convert Active Timeline Text to Text+
    if path == '/api/davinci-convert-textplus':
        try:
            fade_in_sec = float(body.get('fade_in_seconds', 1.5))
            fade_out_sec = float(body.get('fade_out_seconds', 0.5))
            broadcast_log(f"🔄 DaVinci açık Timeline'daki standart Text'ler Text+'a dönüştürülüyor (Fade In: {fade_in_sec}s, Out: {fade_out_sec}s)...")
            res = DaVinciResolveAPI.convert_timeline_text_to_textplus(
                fade_in_sec=fade_in_sec,
                fade_out_sec=fade_out_sec
            )
            broadcast_log(f"✨ {res.get('message', 'Dönüştürme tamamlandı!')}")
            handler.send_json(res)
        except Exception as e:
            broadcast_log(f"❌ DaVinci Text+ Dönüştürme Hatası: {e}")
            handler.send_json({"status": "error", "message": str(e)}, 500)
        return True

    # 4.4 DaVinci Scripts Installer
    if path == '/api/davinci-install-scripts':
        try:
            res = DaVinciResolveAPI.install_davinci_scripts()
            broadcast_log("🛠️ DaVinci Resolve menü scriptleri (Workspace -> Scripts) başarıyla güncellendi!")
            handler.send_json(res)
        except Exception as e:
            handler.send_json({"status": "error", "message": str(e)}, 500)
        return True

    # 6. Generate Base Hub Master DaVinci Timeline XML
    if path == '/api/export-base-hub-davinci':
        gap_seconds = float(body.get('gap_seconds', 0.2))
        fps = int(body.get('fps', 60))
        try:
            import base_champions_hub as base_hub
            res = base_hub.generate_base_hub_master_davinci_xml(gap_seconds=gap_seconds, fps=fps)
            if res.get('status') == 'success':
                broadcast_log(f"🎬 Tüm Varsayılanlar A-Z Master DaVinci XML Hazır: {res['filename']} ({res['total_audio_count']} ses, {res['total_duration_formatted']})")
            handler.send_json(res)
        except Exception as e:
            broadcast_log(f"❌ Master DaVinci XML Hatası: {e}")
            handler.send_json({"status": "error", "message": str(e)}, 500)
        return True


    return False
