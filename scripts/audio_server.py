# -*- coding: utf-8 -*-
"""
⚡ Dedicated LoL JIT Audio Streaming Server
Lightweight, rock-solid HTTP daemon for on-demand audio extraction and playback.
Port 8080 with full CORS support.
"""

import os
import sys
import re
import shutil
import subprocess
import json
import urllib.parse
import http.server
import socketserver

# Sistemdeki mevcut DaVinci Resolve NVIDIA CUDA 12 ve cuBLAS DLL'lerini otomatik bağla
davinci_dir = r"C:\Program Files\Blackmagic Design\DaVinci Resolve"
if os.path.exists(davinci_dir):
    try:
        os.add_dll_directory(davinci_dir)
    except Exception:
        pass
    os.environ['PATH'] = davinci_dir + ';' + os.environ.get('PATH', '')

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import importlib
import event_categorizer
import jit_audio_streamer
import pair_interactions_extractor
import champion_voice_extractor
import davinci_exporter

def hot_reload_all_modules():
    """
    Sunucuyu yeniden başlatmaya gerek kalmadan tüm alt modülleri (event_categorizer,
    champion_voice_extractor, jit_audio_streamer, davinci_exporter) anında bellekte yeniler.
    """
    global event_categorizer, jit_audio_streamer, pair_interactions_extractor, champion_voice_extractor, davinci_exporter
    for mod in (event_categorizer, jit_audio_streamer, pair_interactions_extractor, champion_voice_extractor, davinci_exporter):
        try:
            importlib.reload(mod)
        except Exception as e:
            print(f"⚠️ Hot-reload uyarısı ({getattr(mod, '__name__', mod)}): {e}")

class AudioStreamHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Keep console clean, only print essential requests
        sys.stdout.write(f"🎧 [AudioServer] {self.address_string()} - {format % args}\n")
        sys.stdout.flush()

    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/api/davinci-export-stream':
            content_length = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_length)
            try:
                data = json.loads(post_body.decode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Geçersiz JSON: {e}"}, ensure_ascii=False).encode('utf-8'))
                return

            items = data.get('items', [])
            gap_seconds = float(data.get('gap_seconds', 0.2))
            timeline_name = data.get('timeline_name', 'LoL_Secilen_Atiflar')
            fps = int(data.get('fps', 60))
            include_splash = bool(data.get('include_splash', True))
            include_action_label = bool(data.get('include_action_label', True))
            action_pos_x = float(data.get('action_pos_x', 2090))
            action_pos_y = float(data.get('action_pos_y', 890))
            action_zoom = float(data.get('action_zoom', 0.64))
            bundle_folder = bool(data.get('bundle_folder', True))
            layout_mode = str(data.get('layout_mode', 'matrix_default'))
            font_family = str(data.get('font_family', 'Montserrat'))
            font_face = str(data.get('font_face', 'Bold'))
            font_size_spk = int(data.get('font_size_spk', 46))
            font_size_quote = int(data.get('font_size_quote', 50))
            stroke_width = float(data.get('stroke_width', 1))
            spk_color_hex = str(data.get('spk_color_hex', '#40e0f2'))
            quote_color_hex = str(data.get('quote_color_hex', '#ffe047'))
            include_subtitles = bool(data.get('include_subtitles', True)) if 'include_subtitles' in data else bool(data.get('include_text', True))

            if not items:
                self.send_response(400)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "Aktarilacak replik secilmedi"}')
                return

            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('X-Accel-Buffering', 'no')
            self.end_headers()

            def progress_callback(payload):
                try:
                    chunk = f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode('utf-8')
                    self.wfile.write(chunk)
                    self.wfile.flush()
                except Exception:
                    pass

            try:
                hot_reload_all_modules()
                from davinci_exporter import DaVinciTimelineExporter
                result = DaVinciTimelineExporter.export_matrix_items(
                    items=items,
                    timeline_name=timeline_name,
                    gap_seconds=gap_seconds,
                    fps=fps,
                    include_splash=include_splash,
                    include_action_label=include_action_label,
                    action_pos_x=action_pos_x,
                    action_pos_y=action_pos_y,
                    action_zoom=action_zoom,
                    bundle_folder=bundle_folder,
                    layout_mode=layout_mode,
                    font_family=font_family,
                    font_face=font_face,
                    font_size_spk=font_size_spk,
                    font_size_quote=font_size_quote,
                    stroke_width=stroke_width,
                    spk_color_hex=spk_color_hex,
                    quote_color_hex=quote_color_hex,
                    include_subtitles=include_subtitles,
                    progress_callback=progress_callback
                )
                if not result:
                    progress_callback({"type": "error", "message": "Timeline olusturulamadi (ses dosyalari bulunamadi)"})
            except Exception as e:
                progress_callback({"type": "error", "message": f"Dışa aktarım hatası: {str(e)}"})
            return

        if path == '/api/davinci-export':
            content_length = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_length)
            try:
                data = json.loads(post_body.decode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Geçersiz JSON: {e}"}, ensure_ascii=False).encode('utf-8'))
                return

            items = data.get('items', [])
            gap_seconds = float(data.get('gap_seconds', 0.2))
            timeline_name = data.get('timeline_name', 'LoL_Secilen_Atiflar')
            fps = int(data.get('fps', 60))
            include_splash = bool(data.get('include_splash', True))
            include_action_label = bool(data.get('include_action_label', True))
            action_pos_x = float(data.get('action_pos_x', 2090))
            action_pos_y = float(data.get('action_pos_y', 890))
            action_zoom = float(data.get('action_zoom', 0.64))
            bundle_folder = bool(data.get('bundle_folder', True))
            layout_mode = str(data.get('layout_mode', 'matrix_default'))
            font_family = str(data.get('font_family', 'Montserrat'))
            font_face = str(data.get('font_face', 'Bold'))
            font_size_spk = int(data.get('font_size_spk', 46))
            font_size_quote = int(data.get('font_size_quote', 50))
            stroke_width = float(data.get('stroke_width', 1))
            spk_color_hex = str(data.get('spk_color_hex', '#40e0f2'))
            quote_color_hex = str(data.get('quote_color_hex', '#ffe047'))
            include_subtitles = bool(data.get('include_subtitles', True)) if 'include_subtitles' in data else bool(data.get('include_text', True))

            if not items:
                self.send_response(400)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "Aktarilacak replik secilmedi"}')
                return

            try:
                hot_reload_all_modules()
                from davinci_exporter import DaVinciTimelineExporter
                result = DaVinciTimelineExporter.export_matrix_items(
                    items=items,
                    timeline_name=timeline_name,
                    gap_seconds=gap_seconds,
                    fps=fps,
                    include_splash=include_splash,
                    include_action_label=include_action_label,
                    action_pos_x=action_pos_x,
                    action_pos_y=action_pos_y,
                    action_zoom=action_zoom,
                    bundle_folder=bundle_folder,
                    layout_mode=layout_mode,
                    font_family=font_family,
                    font_face=font_face,
                    font_size_spk=font_size_spk,
                    font_size_quote=font_size_quote,
                    stroke_width=stroke_width,
                    spk_color_hex=spk_color_hex,
                    quote_color_hex=quote_color_hex,
                    include_subtitles=include_subtitles
                )

                if not result:
                    self.send_response(500)
                    self.send_cors_headers()
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"error": "Timeline olusturulamadi (ses dosyalari bulunamadi)"}')
                    return

                self.send_response(200)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
                return
            except Exception as e:
                self.send_response(500)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode('utf-8'))
                return

        if path == '/api/update-transcript':
            content_length = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_length)
            try:
                data = json.loads(post_body.decode('utf-8'))
                wid = str(data.get('wem_id') or '').strip()
                ev = str(data.get('raw_event') or data.get('event') or '').strip()
                speaker = str(data.get('speaker_champ') or data.get('speaker') or '').strip()
                new_text = str(data.get('transcript') or data.get('text') or '').strip()

                if new_text and (wid or ev):
                    from davinci_exporter import DaVinciTimelineExporter
                    cache = DaVinciTimelineExporter.get_transcript_cache()
                    keys_to_save = [k for k in (wid, f"{speaker}_{ev}_{wid}" if (speaker and ev and wid) else None, ev if not wid else None) if k]
                    for k in keys_to_save:
                        cache[k] = new_text
                    DaVinciTimelineExporter.save_transcript_cache(cache)

                    # LoR veritabanını da senkronize et
                    lmd_p = os.path.join(ROOT_DIR, "lol-matrix-web", "public", "data", "lor_matrix_data.json")
                    if os.path.exists(lmd_p):
                        try:
                            with open(lmd_p, 'r', encoding='utf-8') as f:
                                lmd = json.load(f)
                            for c in lmd.get('champions', []):
                                for item in c.get('outgoing_items', []) + c.get('incoming_items', []):
                                    iwid = str(item.get('wem_id') or '').strip()
                                    iev = str(item.get('raw_event') or '').strip()
                                    if (wid and iwid == wid) or (iev == ev):
                                        item['transcript'] = new_text
                                        item['text'] = new_text
                            with open(lmd_p, 'w', encoding='utf-8') as f:
                                json.dump(lmd, f, ensure_ascii=False, indent=2)
                        except Exception:
                            pass

                    self.send_response(200)
                    self.send_cors_headers()
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"status": "ok"}')
                    return
                else:
                    self.send_response(400)
                    self.send_cors_headers()
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"error": "Eksik parametre"}')
                    return
            except Exception as e:
                self.send_response(500)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode('utf-8'))
                return

        if path in ('/api/generate-transcripts-stream', '/api/transcribe-batch-stream'):
            content_length = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_length)
            try:
                data = json.loads(post_body.decode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Gecersiz JSON: {e}"}, ensure_ascii=False).encode('utf-8'))
                return

            items = data.get('items', [])
            total_count = len(items)
            force_retranscribe = bool(data.get('force_retranscribe', False))

            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('X-Accel-Buffering', 'no')
            self.end_headers()

            def send_sse(payload):
                try:
                    chunk = f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode('utf-8')
                    self.wfile.write(chunk)
                    self.wfile.flush()
                except Exception:
                    pass

            try:
                from davinci_exporter import DaVinciTimelineExporter
                from ai_voice_detector import AIVoiceDetector
                cache = DaVinciTimelineExporter.get_transcript_cache()
                resolved = {}
                newly_transcribed = {}
                send_sse({"type": "log", "message": f"⚡ Whisper Large-v3-Turbo motoru devrede. Toplam {total_count} replik analiz edilecek..."})

                # İlgili şampiyonların Wiki veri setlerini dinamik olarak hazırla
                try:
                    from wiki_quote_sync import ensure_champion_wiki_dataset
                    unique_spks = {it.get('speaker_champ') or it.get('speaker') for it in items if (it.get('speaker_champ') or it.get('speaker'))}
                    for s in unique_spks:
                        w_entries = ensure_champion_wiki_dataset(s)
                        if w_entries:
                            send_sse({"type": "log", "message": f"🌐 [{s}] Resmi Wiki replik veri seti devrede ({len(w_entries)} replik bağlamı doğrulandı)."})
                except Exception:
                    pass

                for idx, it in enumerate(items, start=1):
                    spk = it.get('speaker_champ') or it.get('speaker') or ''
                    tgt = it.get('target_champ') or it.get('target') or ''
                    ev = it.get('raw_event') or it.get('event') or ''
                    wid = str(it.get('wem_id') or '').strip()
                    ref_text = it.get('transcript') or it.get('text') or ''
                    game = str(it.get('game') or 'lol').lower()
                    if not wid and not ev:
                        continue

                    key = wid or ev
                    cached_text = None
                    if not force_retranscribe:
                        # Varyasyonlu seslerde genel event adına bakma, sadece o WEM'e bak
                        lookup_keys = [wid, f"{spk}_{ev}_{wid}"] if (wid and spk and ev) else ([wid] if wid else [ev, f"{spk}_{ev}"])
                        for k in lookup_keys:
                            if k and k in cache and cache[k]:
                                cached_text = DaVinciTimelineExporter.fix_champion_names_in_text(cache[k])
                                break

                    # Eğer önbellekte varsa ve zorlama yoksa
                    if cached_text:
                        # Hatalı/şüpheli kelime veya bozukluk analizi
                        needs_rev = any(w in cached_text.lower() for w in ['teşkürt', 'şurima', 'demasya', 'undefined', 'null'])
                        resolved[key] = {
                            "text": cached_text,
                            "confidence_score": 75 if needs_rev else 98,
                            "needs_review": needs_rev,
                            "source": "cache",
                            "speaker": spk,
                            "target": tgt
                        }
                        log_msg = f"⚡ [Önbellek {idx}/{total_count}] {spk}: \"{cached_text}\"" + (" ⚠️ (İnceleme Gerekli)" if needs_rev else "")
                        send_sse({
                            "type": "progress",
                            "current": idx,
                            "total": total_count,
                            "key": key,
                            "text": cached_text,
                            "confidence_score": 75 if needs_rev else 98,
                            "needs_review": needs_rev,
                            "speaker": spk,
                            "target": tgt,
                            "log": log_msg
                        })
                        continue

                    # 2. Whisper Large-v3-Turbo + Fonetik Güven Skoru ile Dinle
                    wav_p = jit_audio_streamer.get_or_extract_audio(spk, ev, target_champ=tgt, wem_id=wid, game=game)
                    if wav_p and os.path.exists(wav_p):
                        ai_res = AIVoiceDetector.transcribe_with_confidence(
                            file_path=wav_p,
                            speaker=spk,
                            target=tgt,
                            reference_text=ref_text or cached_text or ""
                        )
                        final_text = ai_res.get("text", "")
                        score = ai_res.get("confidence_score", 0)
                        needs_rev = (score < 80) or any(w in final_text.lower() for w in ['teşkürt', 'şurima', 'demasya'])

                        if final_text:
                            # Teşkürtün -> Püskürtün otomatik düzeltme
                            final_text = re.sub(r'\bteşkürtün\b', 'Püskürtün', final_text, flags=re.IGNORECASE)
                            final_text = re.sub(r'\bteşkürt\b', 'Püskürt', final_text, flags=re.IGNORECASE)

                            resolved[key] = {
                                "text": final_text,
                                "confidence_score": score,
                                "needs_review": needs_rev,
                                "source": "whisper_turbo_ai",
                                "speaker": spk,
                                "target": tgt
                            }
                            newly_transcribed[key] = final_text

                            # Cache'e kaydet (Varyasyonlu ise SADECE wem_id ve spesifik key'e yaz, generic ev'ye yazma!)
                            save_keys = [wid, f"{spk}_{ev}_{wid}"] if (wid and spk and ev) else ([wid] if wid else [ev])
                            save_keys = [k for k in save_keys if k]
                            for sk in save_keys:
                                cache[sk] = final_text
                            DaVinciTimelineExporter.save_transcript_cache(cache)

                            status_badge = " ⚠️ [İnceleme Gerekli]" if needs_rev else ""
                            log_msg = f"🎙️ [Whisper AI {idx}/{total_count}] {spk}: \"{final_text}\" (Fonetik Güven: %{score}){status_badge}"
                            send_sse({
                                "type": "progress",
                                "current": idx,
                                "total": total_count,
                                "key": key,
                                "text": final_text,
                                "confidence_score": score,
                                "needs_review": needs_rev,
                                "speaker": spk,
                                "target": tgt,
                                "log": log_msg
                            })
                        else:
                            log_msg = f"🔇 [{idx}/{total_count}] {spk}: Konuşma tespit edilmedi (Combat efekti / VAD kırptı)"
                            send_sse({
                                "type": "progress",
                                "current": idx,
                                "total": total_count,
                                "key": key,
                                "text": "",
                                "confidence_score": 0,
                                "speaker": spk,
                                "target": tgt,
                                "log": log_msg
                            })
                    else:
                        log_msg = f"⚠️ [{idx}/{total_count}] Ses dosyası bulunamadı: {spk} ({ev})"
                        send_sse({
                            "type": "progress",
                            "current": idx,
                            "total": total_count,
                            "key": key,
                            "text": "",
                            "confidence_score": 0,
                            "speaker": spk,
                            "target": tgt,
                            "log": log_msg
                        })

                # DB'leri senkronize et
                if newly_transcribed:
                    try:
                        def _sync_dbs():
                            lmd_p = os.path.join(ROOT_DIR, "lol-matrix-web", "public", "data", "lor_matrix_data.json")
                            if os.path.exists(lmd_p):
                                with open(lmd_p, 'r', encoding='utf-8') as f:
                                    lmd = json.load(f)
                                for c in lmd.get('champions', []):
                                    for item in c.get('outgoing_items', []) + c.get('incoming_items', []):
                                        key1 = str(item.get('wem_id') or '').strip()
                                        key2 = str(item.get('raw_event') or '').strip()
                                        if key1 in newly_transcribed:
                                            item['transcript'] = newly_transcribed[key1]
                                            item['text'] = newly_transcribed[key1]
                                        elif key2 in newly_transcribed:
                                            item['transcript'] = newly_transcribed[key2]
                                            item['text'] = newly_transcribed[key2]
                                with open(lmd_p, 'w', encoding='utf-8') as f:
                                    json.dump(lmd, f, ensure_ascii=False, indent=2)
                        import threading
                        threading.Thread(target=_sync_dbs, daemon=True).start()
                    except Exception:
                        pass

                send_sse({"type": "done", "transcripts": resolved, "count": len(resolved)})
            except Exception as e:
                send_sse({"type": "error", "message": f"Transkripsiyon hatası: {str(e)}"})
            return

        if path in ('/api/generate-transcripts-only', '/api/transcribe-batch'):
            content_length = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_length)
            try:
                data = json.loads(post_body.decode('utf-8'))
                items = data.get('items', [])
                force_retranscribe = bool(data.get('force_retranscribe', False))
                from davinci_exporter import DaVinciTimelineExporter
                from ai_voice_detector import AIVoiceDetector
                cache = DaVinciTimelineExporter.get_transcript_cache()
                resolved = {}
                newly_transcribed = {}

                for it in items[:1000]:
                    spk = it.get('speaker_champ') or it.get('speaker') or ''
                    tgt = it.get('target_champ') or it.get('target') or ''
                    ev = it.get('raw_event') or it.get('event') or ''
                    wid = str(it.get('wem_id') or '').strip()
                    ref_text = it.get('transcript') or it.get('text') or ''
                    game = str(it.get('game') or 'lol').lower()
                    if not wid and not ev:
                        continue

                    key = wid or ev
                    cached_text = None
                    if not force_retranscribe:
                        for k in (wid, f"{spk}_{ev}_{wid}" if spk and ev and wid else None, ev, f"{spk}_{ev}" if spk and ev else None):
                            if k and k in cache and cache[k]:
                                cached_text = DaVinciTimelineExporter.fix_champion_names_in_text(cache[k])
                                break

                    if cached_text:
                        resolved[key] = {
                            "text": cached_text,
                            "confidence_score": 98,
                            "source": "cache"
                        }
                        continue

                    # Çoklu Yapay Zeka & Fonetik Güven Skoru
                    wav_p = jit_audio_streamer.get_or_extract_audio(spk, ev, target_champ=tgt, wem_id=wid, game=game)
                    if wav_p and os.path.exists(wav_p):
                        ai_res = AIVoiceDetector.transcribe_with_confidence(
                            file_path=wav_p,
                            speaker=spk,
                            target=tgt,
                            reference_text=ref_text or cached_text or ""
                        )
                        txt = ai_res.get("text", "")
                        score = ai_res.get("confidence_score", 0)
                        if txt:
                            resolved[key] = {
                                "text": txt,
                                "confidence_score": score,
                                "source": "whisper_turbo_ai"
                            }
                            newly_transcribed[key] = txt
                            save_keys = [k for k in (wid, f"{spk}_{ev}_{wid}" if spk and ev and wid else None, ev) if k]
                            for sk in save_keys:
                                cache[sk] = txt

                if newly_transcribed:
                    DaVinciTimelineExporter.save_transcript_cache(cache)
                    try:
                        def _sync_dbs_sync():
                            lmd_p = os.path.join(ROOT_DIR, "lol-matrix-web", "public", "data", "lor_matrix_data.json")
                            if os.path.exists(lmd_p):
                                with open(lmd_p, 'r', encoding='utf-8') as f:
                                    lmd = json.load(f)
                                for c in lmd.get('champions', []):
                                    for item in c.get('outgoing_items', []) + c.get('incoming_items', []):
                                        key1 = str(item.get('wem_id') or '').strip()
                                        key2 = str(item.get('raw_event') or '').strip()
                                        if key1 in newly_transcribed:
                                            item['transcript'] = newly_transcribed[key1]
                                            item['text'] = newly_transcribed[key1]
                                        elif key2 in newly_transcribed:
                                            item['transcript'] = newly_transcribed[key2]
                                            item['text'] = newly_transcribed[key2]
                                with open(lmd_p, 'w', encoding='utf-8') as f:
                                    json.dump(lmd, f, ensure_ascii=False, indent=2)
                        import threading
                        threading.Thread(target=_sync_dbs_sync, daemon=True).start()
                    except Exception:
                        pass

                self.send_response(200)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                # Geriye dönük uyumluluk: hem transcript dict hem de meta döner
                flat_transcripts = {k: (v["text"] if isinstance(v, dict) else v) for k, v in resolved.items()}
                self.send_response_data = {"success": True, "transcripts": flat_transcripts, "details": resolved}
                self.wfile.write(json.dumps(self.send_response_data, ensure_ascii=False).encode('utf-8'))
                return
            except Exception as e:
                self.send_response(500)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode('utf-8'))
                return

        if path == '/api/batch-export-wavs':
            content_length = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_length)
            try:
                data = json.loads(post_body.decode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Gecersiz JSON: {e}"}, ensure_ascii=False).encode('utf-8'))
                return

            champion = data.get('champion', 'Bilinmeyen_Sampiyon')
            items = data.get('items', [])
            group_by_category = bool(data.get('group_by_category', True))
            open_folder = bool(data.get('open_folder', True))
            custom_folder_name = data.get('folder_name', '').strip()

            def sanitize_filename(name: str) -> str:
                name = re.sub(r'[\\/*?:"<>|]', '_', str(name))
                name = re.sub(r'\s+', '_', name).strip('_')
                return name or "audio"

            base_folder_name = sanitize_filename(custom_folder_name or champion)
            target_base_dir = os.path.join(ROOT_DIR, "Indirilen_Sesler", base_folder_name)
            os.makedirs(target_base_dir, exist_ok=True)

            exported_files = []
            for idx, it in enumerate(items, 1):
                ev = it.get('event', '')
                wem = it.get('wem_id', '')
                spk = it.get('speaker', champion)
                cat = sanitize_filename(it.get('category_title', 'Genel'))
                act = sanitize_filename(it.get('action_name', ev or f'Ses_{idx}'))

                wav_src = jit_audio_streamer.get_or_extract_audio(spk, ev, wem_id=wem if wem else None)
                if not wav_src or not os.path.exists(wav_src):
                    continue

                if group_by_category:
                    dest_dir = os.path.join(target_base_dir, cat)
                    os.makedirs(dest_dir, exist_ok=True)
                    dest_filename = f"{idx:02d}_{act}_{wem or '0'}.wav"
                else:
                    dest_dir = target_base_dir
                    dest_filename = f"{idx:02d}_{cat}_{act}_{wem or '0'}.wav"

                dest_path = os.path.join(dest_dir, dest_filename)
                try:
                    shutil.copy2(wav_src, dest_path)
                    exported_files.append(dest_path)
                except Exception as copy_err:
                    print(f"Kopyalama hatasi: {copy_err}")

            if open_folder and sys.platform == 'win32' and os.path.exists(target_base_dir):
                try:
                    os.startfile(target_base_dir)
                except Exception as ex:
                    print(f"Klasor acma hatasi: {ex}")

            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "exported_count": len(exported_files),
                "folder_path": os.path.abspath(target_base_dir),
                "group_by_category": group_by_category
            }, ensure_ascii=False).encode('utf-8'))
            return

        if path == '/api/save-single-wav':
            content_length = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_length)
            try:
                data = json.loads(post_body.decode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Gecersiz JSON: {e}"}, ensure_ascii=False).encode('utf-8'))
                return

            speaker = data.get('speaker', 'Bilinmeyen_Sampiyon')
            event = data.get('event', '')
            wem_id = data.get('wem_id', '')
            action_name = data.get('action_name', event or 'Replik')
            category_title = data.get('category_title', 'Genel')
            open_folder = bool(data.get('open_folder', False))

            def sanitize_filename(name: str) -> str:
                name = str(name).replace('&', '_ve_')
                name = re.sub(r'[\\/*?:"<>|]', '_', name)
                name = re.sub(r'\s+', '_', name).strip('_')
                return name or "audio"

            safe_champ = sanitize_filename(speaker)
            safe_cat = sanitize_filename(category_title)
            safe_act = sanitize_filename(action_name)

            target_dir = os.path.join(ROOT_DIR, "Indirilen_Sesler", safe_champ, safe_cat)
            os.makedirs(target_dir, exist_ok=True)

            wav_src = jit_audio_streamer.get_or_extract_audio(speaker, event, wem_id=wem_id if wem_id else None)
            if not wav_src or not os.path.exists(wav_src):
                self.send_response(404)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "Ses dosyasi cikarilamadi"}')
                return

            dest_filename = f"{safe_act}_{wem_id or '0'}.wav"
            dest_path = os.path.join(target_dir, dest_filename)
            try:
                shutil.copy2(wav_src, dest_path)
            except Exception as e:
                self.send_response(500)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Kopyalama hatasi: {e}"}).encode('utf-8'))
                return

            if open_folder and sys.platform == 'win32':
                try:
                    subprocess.Popen(f'explorer /select,"{os.path.abspath(dest_path)}"')
                except Exception:
                    os.startfile(target_dir)

            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "folder_path": os.path.abspath(target_dir),
                "file_path": os.path.abspath(dest_path),
                "filename": dest_filename,
                "action_name": action_name,
                "category_title": category_title
            }, ensure_ascii=False).encode('utf-8'))
            return

        if path == '/api/open-folder':
            content_length = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_length)
            try:
                data = json.loads(post_body.decode('utf-8')) if post_body else {}
                file_path = data.get('file_path', '')
                folder_path = data.get('folder_path', '')

                if not folder_path and file_path:
                    folder_path = os.path.dirname(file_path)
                if not folder_path:
                    folder_path = os.path.join(ROOT_DIR, "Indirilen_Sesler")

                folder_path = os.path.abspath(folder_path)
                os.makedirs(folder_path, exist_ok=True)

                if sys.platform == 'win32':
                    try:
                        os.startfile(folder_path)
                    except Exception as ex:
                        print(f"os.startfile hatasi: {ex}")
                        subprocess.Popen(f'explorer "{folder_path}"')

                self.send_response(200)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"success": true}')
                return
            except Exception as e:
                self.send_response(500)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
                return

        self.send_response(404)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        global jit_audio_streamer, pair_interactions_extractor, champion_voice_extractor, davinci_exporter, importlib
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == '/api/health':
            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return

        if path == '/api/champion-voices':
            champion = params.get('champion', [''])[0]
            skin_num = params.get('skin_num', ['0'])[0]
            include_sfx = params.get('include_sfx', ['true'])[0].lower() in ['true', '1', 'yes']
            game = params.get('game', ['lol'])[0].lower()

            if not champion:
                self.send_response(400)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error":"champion parametresi zorunludur"}')
                return

            try:
                if game == 'lor':
                    hot_reload_all_modules()
                    data = jit_audio_streamer.extract_lor_champion_voices(champion, skin_num=skin_num)
                else:
                    hot_reload_all_modules()
                    data = champion_voice_extractor.extract_champion_voices(champion, skin_num=skin_num, include_sfx=include_sfx)
                if not data:
                    self.send_response(404)
                    self.send_cors_headers()
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": f"{champion} icin ses verisi bulunamadi"}).encode('utf-8'))
                    return

                self.send_response(200)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
                return
            except Exception as e:
                self.send_response(500)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
                return

        if path == '/api/pair-interactions':
            champA = params.get('champA', [''])[0]
            champB = params.get('champB', [''])[0]
            force_refresh = params.get('refresh', ['false'])[0].lower() in ['true', '1', 'yes']
            game = params.get('game', ['lol'])[0].lower()

            if not champA or not champB:
                self.send_response(400)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error":"champA ve champB parametreleri zorunludur"}')
                return

            try:
                if game == 'lor':
                    importlib.reload(jit_audio_streamer)
                    data = jit_audio_streamer.extract_lor_pair_interactions(champA, champB)
                else:
                    importlib.reload(pair_interactions_extractor)
                    data = pair_interactions_extractor.extract_pair_interactions(champA, champB, force_refresh=force_refresh)
                if not data:
                    self.send_response(404)
                    self.send_cors_headers()
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": f"{champA} ve {champB} icin veri bulunamadi"}).encode('utf-8'))
                    return

                self.send_response(200)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
                return
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                return
            except Exception as e:
                try:
                    self.send_response(500)
                    self.send_cors_headers()
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
                except Exception:
                    pass
                return

        if path == '/api/featured-pairs':
            game = params.get('game', ['lol'])[0].lower()
            try:
                if game == 'lor':
                    db = jit_audio_streamer.get_lor_full_db()
                    pair_dialogues = db.get('pair_dialogues', {})
                    cached_summaries = {}
                    for pk, ch_list in pair_dialogues.items():
                        turns_cnt = sum(c.get('turn_count', 2) for c in ch_list)
                        cached_summaries[pk] = {
                            'dialogue_chains_count': len(ch_list),
                            'dialogue_turns_count': turns_cnt,
                            'one_way_quotes_count': 0,
                            'total_interactions': turns_cnt
                        }
                    self.send_response(200)
                    self.send_cors_headers()
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"pairs": [], "cached_summaries": cached_summaries}, ensure_ascii=False).encode('utf-8'))
                    return

                importlib.reload(pair_interactions_extractor)
                pairs = pair_interactions_extractor.get_featured_pairs()
                cached_summaries = pair_interactions_extractor.get_cached_pair_summaries()
                self.send_response(200)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"pairs": pairs, "cached_summaries": cached_summaries}, ensure_ascii=False).encode('utf-8'))
                return
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                return
            except Exception as e:
                try:
                    self.send_response(500)
                    self.send_cors_headers()
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
                except Exception:
                    pass
                return

        if path == '/api/davinci-download':
            filepath = params.get('file', [''])[0]
            if filepath and os.path.exists(filepath):
                try:
                    with open(filepath, 'rb') as f:
                        data = f.read()
                    filename = os.path.basename(filepath)
                    content_type = 'application/zip' if filename.endswith('.zip') else 'application/xml'
                    self.send_response(200)
                    self.send_cors_headers()
                    self.send_header('Content-Type', content_type)
                    self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception as e:
                    pass
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()
            return

        if path == '/api/audio-play':
            speaker = params.get('speaker', [''])[0]
            raw_event = params.get('event', [''])[0]
            target = params.get('target', [''])[0]
            wem_id = params.get('wem_id', [''])[0]

            wav_path = jit_audio_streamer.get_or_extract_audio(speaker, raw_event, target, wem_id=wem_id if wem_id else None)
            if wav_path and os.path.exists(wav_path):
                try:
                    with open(wav_path, 'rb') as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_cors_headers()
                    self.send_header('Content-Type', 'audio/wav')
                    self.send_header('Content-Length', str(len(data)))
                    self.send_header('Cache-Control', 'public, max-age=86400')
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                    return
                except Exception as e:
                    try:
                        self.send_response(500)
                        self.send_cors_headers()
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
                    except Exception:
                        pass
                    return

            self.send_response(404)
            self.send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error":"Audio cue not found"}')
            return

        if path == '/api/audio-download':
            speaker = params.get('speaker', [''])[0]
            raw_event = params.get('event', [''])[0]
            target = params.get('target', [''])[0]
            wem_id = params.get('wem_id', [''])[0]
            filename = params.get('filename', [''])[0]

            wav_path = jit_audio_streamer.get_or_extract_audio(speaker, raw_event, target, wem_id=wem_id if wem_id else None)
            if wav_path and os.path.exists(wav_path):
                try:
                    with open(wav_path, 'rb') as f:
                        data = f.read()

                    if not filename:
                        safe_spk = re.sub(r'[^\w\-_]', '_', speaker)
                        safe_ev = re.sub(r'[^\w\-_]', '_', raw_event)
                        filename = f"{safe_spk}_{safe_ev}_{wem_id or '0'}.wav"
                    else:
                        filename = re.sub(r'[^\w\-_. ]', '_', filename)
                        if not filename.lower().endswith('.wav'):
                            filename += '.wav'

                    self.send_response(200)
                    self.send_cors_headers()
                    self.send_header('Content-Type', 'audio/wav')
                    self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception as e:
                    self.send_response(500)
                    self.send_cors_headers()
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
                    return

            self.send_response(404)
            self.send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error":"Audio cue not found"}')
            return

        if path == '/api/audio':
            filepath = params.get('path', [''])[0]
            if filepath and os.path.exists(filepath):
                try:
                    with open(filepath, 'rb') as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_cors_headers()
                    self.send_header('Content-Type', 'audio/wav')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception as e:
                    pass
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()
            return

        self.send_response(404)
        self.send_cors_headers()
        self.end_headers()

def run_server(port=8080):
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    server = socketserver.ThreadingTCPServer(('127.0.0.1', port), AudioStreamHandler)
    print(f"=======================================================")
    print(f"🎧 LoL JIT Ses Sunucusu Hazır: http://127.0.0.1:{port}")
    print(f"=======================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Ses sunucusu kapatıldı.")
        server.shutdown()

if __name__ == '__main__':
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
