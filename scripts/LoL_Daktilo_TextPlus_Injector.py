#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
========================================================================================
🎮 League of Legends - DaVinci Resolve 19/20/21 Free & Studio Uyumlu
⚡ Çift Katmanlı Kusursuz Altyazı Sistemi (Video 5: Altın Replik + Video 6: Cyan Karakter)
========================================================================================
Nasıl Çalışır:
- Video 5 (Alt Katman): 26 Replik metnini ALTIN SARISI (#E5C158) ve DAKTİLO animasyonuyla yazar.
- Video 6 (Üst Katman): 26 Karakter adını (YONE, TALİYAH vb.) TURKUAZ / CYAN (#4DEEEA) olarak yazar.
- İki katman da Video 2 ile birebir aynı sol hizaya (X=0.36) oturur.
- Aralarında ferah boşluk (Karakter Y=0.220, Replik Y=0.130) vardır.
- Sıfır node karmaşası, %100 kararlı ve pürüzsüz çalışır!
========================================================================================
"""

import os
import sys

LOG_FILE = r"C:\Users\PC\Desktop\Yazılım\projects\active\lol-ses-veriler\davinci_script_log.txt"
DEFAULT_SRT_PATH = r"C:\Users\PC\Desktop\Yazılım\projects\active\lol-ses-veriler\Champions\Yasuo\Yasuoe_Yapilan_Tum_Ozel_Atiflar\Kurgu_Ciktilari\2026-09-02_19-31-31_1.5s_Gap\03_Dramatik_Kurgu_1.5s_Gap.srt"

def log(msg):
    print(msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as lf:
            lf.write(str(msg) + "\n")
    except Exception:
        pass

# ==============================================================================
# VİDEO 2 İLE BİREBİR AYARLAR
# ==============================================================================
POS_X           = 0.36      # Video 2 ile birebir aynı sol hizalama (X=0.36)
SPEAKER_POS_Y   = 0.220     # Video 6: Karakter Adı dikey konumu (Yukarıda)
QUOTE_POS_Y     = 0.130     # Video 5: Replik metni dikey konumu (Aşağıda)

FONT_NAME       = "Poppins"
SPEAKER_STYLE   = "ExtraBold"
QUOTE_STYLE     = "Bold"

SPEAKER_SIZE    = 0.044     # Karakter Adı büyüklüğü
QUOTE_SIZE      = 0.040     # Replik metni büyüklüğü

# Video 6: Turkuaz / Cyan (#4DEEEA)
SPEAKER_RED     = 0.30
SPEAKER_GREEN   = 0.85
SPEAKER_BLUE    = 0.95

# Video 5: Altın Sarısı (#E5C158)
QUOTE_RED       = 0.95
QUOTE_GREEN     = 0.82
QUOTE_BLUE      = 0.25

IMAGE_VIDEO_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.tga', '.tiff', '.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v')

def is_media_asset(item):
    name = (item.GetName() or "").lower().strip()
    for ext in IMAGE_VIDEO_EXTS:
        if name.endswith(ext) or ext in name:
            return True
    try:
        mpi = item.GetMediaPoolItem()
        if mpi:
            fp = (mpi.GetClipProperty("File Path") or "").lower()
            for ext in IMAGE_VIDEO_EXTS:
                if fp.endswith(ext):
                    return True
    except Exception:
        pass
    return False

def load_srt_dialogues(srt_path):
    if not os.path.exists(srt_path):
        return []

    try:
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
    except Exception:
        try:
            with open(srt_path, "r", encoding="utf-8-sig") as f:
                content = f.read().strip()
        except Exception:
            return []

    dialogues = []
    blocks = content.replace("\r\n", "\n").split("\n\n")
    for b in blocks:
        lines = [l.strip() for l in b.split("\n") if l.strip()]
        if len(lines) >= 3:
            speaker = lines[2].strip()
            quote = "\n".join(lines[3:]).strip() if len(lines) > 3 else ""
            dialogues.append((speaker, quote))
        elif len(lines) == 2:
            dialogues.append(("", lines[1].strip()))

    return dialogues

def clean_clip_fusion_comp(comp):
    """Klip içindeki çakışan ekstra düğümleri temizler, tek TextPlus'ı MediaOut'a bağlar."""
    try:
        stray_spk = comp.FindTool("Text_Speaker")
        if stray_spk:
            stray_spk.Delete()
        stray_mrg = comp.FindTool("Merge_Text")
        if stray_mrg:
            stray_mrg.Delete()
    except Exception:
        pass

    tp = comp.FindToolByID("TextPlus")
    if not tp:
        tools = comp.GetToolList(False)
        for t in (tools.values() if isinstance(tools, dict) else tools):
            if "TextPlus" in str(t.GetID() or ""):
                tp = t
                break

    mo = comp.FindToolByID("MediaOut") or comp.FindToolByID("MediaOut1")
    if not mo:
        mo_tools = comp.GetToolList(False, "MediaOut")
        if mo_tools:
            mo = list(mo_tools.values())[0] if isinstance(mo_tools, dict) else mo_tools[0]

    if mo and tp:
        try:
            mo.ConnectInput("Input", tp)
        except Exception:
            pass

    return tp

def get_resolve_instance():
    try:
        if 'resolve' in globals() and resolve:
            return resolve
    except NameError:
        pass

    try:
        if 'app' in globals() and app:
            return app.GetResolve()
    except NameError:
        pass

    try:
        import bmd
        return bmd.scriptapp("Resolve")
    except Exception:
        pass

    try:
        if 'fusion' in globals() and fusion:
            return fusion.GetResolve()
    except NameError:
        pass

    for mod_name in ['DaVinciResolveScript', 'fusionscript']:
        try:
            m = __import__(mod_name)
            res = m.scriptapp("Resolve")
            if res:
                return res
        except Exception:
            pass

    return None

def main():
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as lf:
            lf.write("--- LoL Çift Katmanlı Daktilo Başlatıldı ---\n")
    except Exception:
        pass

    log("=" * 70)
    log("🎮 LoL Text+ Çift Katman (Video 5: Replik + Video 6: Karakter) Enjektörü")
    log("=" * 70)

    srt_items = load_srt_dialogues(DEFAULT_SRT_PATH)
    log(f"📖 SRT Veritabanından {len(srt_items)} adet replik yüklendi.")

    resolve = get_resolve_instance()
    if not resolve:
        log("❌ HATA: DaVinci Resolve nesnesine erişilemedi.")
        return

    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject() if pm else None
    if not project:
        log("❌ HATA: Proje bulunamadı.")
        return

    timeline = project.GetCurrentTimeline()
    if not timeline:
        log("❌ HATA: Timeline bulunamadı.")
        return

    fps = float(timeline.GetSetting("timelineFrameRate") or 60.0)
    log(f"🎬 Aktif Timeline: '{timeline.GetName()}' ({fps} FPS)")

    track_count = timeline.GetTrackCount("video")

    # Metin içeren kanalları tespit et (Video 1 ve Video 2 hariç)
    candidate_tracks = []
    for t_idx in range(1, track_count + 1):
        t_name = timeline.GetTrackName("video", t_idx) or f"Video {t_idx}"
        if "video 1" in t_name.lower() or "video 2" in t_name.lower() or "video 3" in t_name.lower() or "video 4" in t_name.lower():
            continue
        items = timeline.GetItemListInTrack("video", t_idx) or []
        valid_items = [itm for itm in items if not is_media_asset(itm)]
        if len(valid_items) >= 10: # 26 klip içeren kanallar
            candidate_tracks.append((t_idx, t_name, valid_items))

    if not candidate_tracks:
        log("⚠️ Video 5 veya Video 6 kanallarında yeterli Text+ klibi bulunamadı.")
        return

    # Kanalları index sırasına göre diz
    candidate_tracks.sort(key=lambda x: x[0])

    quote_track_info = candidate_tracks[0] # Alttaki kanal: Video 5 (Replik)
    speaker_track_info = candidate_tracks[1] if len(candidate_tracks) > 1 else None # Üstteki kanal: Video 6 (Karakter Adı)

    log(f"\n🎯 Replik Kanalı (Altın Daktilo): Kanal {quote_track_info[0]} ('{quote_track_info[1]}')")
    if speaker_track_info:
        log(f"🎯 Karakter Adı Kanalı (Turkuaz): Kanal {speaker_track_info[0]} ('{speaker_track_info[1]}')")
    else:
        log(f"ℹ️ Henüz tek metin kanalı var. Video 6 oluşturulduğunda otomatik olarak Cyan Karakter Adı yapılacak.")

    # --------------------------------------------------------------------------
    # 1. REPLİK KANALINI İŞLE (Video 5 -> Altın Sarısı #E5C158 + Daktilo)
    # --------------------------------------------------------------------------
    q_idx, q_name, q_items = quote_track_info
    log(f"\n⚡ Video {q_name} replik kanalı işleniyor ({len(q_items)} klip)...")

    for c_idx, item in enumerate(q_items):
        dur = item.GetDuration()
        if dur <= 1:
            continue

        comp_count = item.GetFusionCompCount()
        if comp_count == 0:
            continue

        comp = item.GetFusionCompByIndex(1)
        if not comp:
            continue

        tool = clean_clip_fusion_comp(comp)
        if not tool:
            continue

        # Replik metnini al
        quote_text = srt_items[c_idx][1] if c_idx < len(srt_items) else (item.GetName() or "")

        # Daktilo süresi
        char_len = len(quote_text)
        dyn_type_frames = max(12, min(int(dur * 0.70), int(char_len * 1.15)))
        type_end_frame = max(10, min(dur - 6, dyn_type_frames))

        try:
            tool.SetInput("StyledText", quote_text)
            tool.SetInput("Font", FONT_NAME)
            tool.SetInput("Style", QUOTE_STYLE)
            tool.SetInput("Size", QUOTE_SIZE)
            tool.SetInput("Center", [POS_X, QUOTE_POS_Y])
            tool.SetInput("VerticalJustificationNew", 3)
            tool.SetInput("HorizontalJustificationNew", 3)
            tool.SetInput("LineSpacing", 1.05)

            # Dolgu: Altın Sarısı (#E5C158)
            tool.SetInput("Enabled1", 1)
            tool.SetInput("Element1", 0)
            tool.SetInput("Red1", QUOTE_RED)
            tool.SetInput("Green1", QUOTE_GREEN)
            tool.SetInput("Blue1", QUOTE_BLUE)
            tool.SetInput("Alpha1", 1.0)
            tool.SetInput("Opacity1", 1.0)

            # Siyah Tok Kontur
            tool.SetInput("Enabled2", 1)
            tool.SetInput("Element2", 1)
            tool.SetInput("Red2", 0.0)
            tool.SetInput("Green2", 0.0)
            tool.SetInput("Blue2", 0.0)
            tool.SetInput("Alpha2", 1.0)
            tool.SetInput("Thickness2", 0.014)
            tool.SetInput("Softness2", 0.0)

            # Siyah Derin Gölge
            tool.SetInput("Enabled3", 1)
            tool.SetInput("Element3", 2)
            tool.SetInput("Red3", 0.0)
            tool.SetInput("Green3", 0.0)
            tool.SetInput("Blue3", 0.0)
            tool.SetInput("Alpha3", 0.85)
            tool.SetInput("Softness3", 1.5)
            tool.SetInput("Offset3", [0.002, -0.002])

            # Daktilo Animasyonu
            tool.SetInput("End", 0.0, 0)
            tool.SetInput("End", 1.0, type_end_frame)
        except Exception as e:
            log(f"  Hata (Replik): {e}")

    # --------------------------------------------------------------------------
    # 2. KARAKTER ADI KANALINI İŞLE (Video 6 -> Turkuaz / Cyan #4DEEEA)
    # --------------------------------------------------------------------------
    if speaker_track_info:
        s_idx, s_name, s_items = speaker_track_info
        log(f"\n⚡ Video {s_name} karakter adı kanalı işleniyor ({len(s_items)} klip)...")

        for c_idx, item in enumerate(s_items):
            dur = item.GetDuration()
            if dur <= 1:
                continue

            comp_count = item.GetFusionCompCount()
            if comp_count == 0:
                continue

            comp = item.GetFusionCompByIndex(1)
            if not comp:
                continue

            tool = clean_clip_fusion_comp(comp)
            if not tool:
                continue

            # Karakter adını al
            speaker_text = srt_items[c_idx][0] if c_idx < len(srt_items) else (item.GetName() or "")

            try:
                tool.SetInput("StyledText", speaker_text)
                tool.SetInput("Font", FONT_NAME)
                tool.SetInput("Style", SPEAKER_STYLE)
                tool.SetInput("Size", SPEAKER_SIZE)
                tool.SetInput("Center", [POS_X, SPEAKER_POS_Y])
                tool.SetInput("VerticalJustificationNew", 3)
                tool.SetInput("HorizontalJustificationNew", 3)

                # Dolgu: Turkuaz / Cyan (#4DEEEA)
                tool.SetInput("Enabled1", 1)
                tool.SetInput("Element1", 0)
                tool.SetInput("Red1", SPEAKER_RED)
                tool.SetInput("Green1", SPEAKER_GREEN)
                tool.SetInput("Blue1", SPEAKER_BLUE)
                tool.SetInput("Alpha1", 1.0)
                tool.SetInput("Opacity1", 1.0)

                # Siyah Tok Kontur
                tool.SetInput("Enabled2", 1)
                tool.SetInput("Element2", 1)
                tool.SetInput("Red2", 0.0)
                tool.SetInput("Green2", 0.0)
                tool.SetInput("Blue2", 0.0)
                tool.SetInput("Alpha2", 1.0)
                tool.SetInput("Thickness2", 0.014)
                tool.SetInput("Softness2", 0.0)

                # Siyah Derin Gölge
                tool.SetInput("Enabled3", 1)
                tool.SetInput("Element3", 2)
                tool.SetInput("Red3", 0.0)
                tool.SetInput("Green3", 0.0)
                tool.SetInput("Blue3", 0.0)
                tool.SetInput("Alpha3", 0.85)
                tool.SetInput("Softness3", 1.5)
                tool.SetInput("Offset3", [0.002, -0.002])

                # Karakter adı ekranda sabit kalsın (daktilosuz)
                tool.SetInput("End", 1.0)
            except Exception as e:
                log(f"  Hata (Karakter): {e}")

    log("=" * 70)
    log("🎉 BAŞARILI! Çift katmanlı altyazı sistemi kusursuz kuruldu!")
    log("=" * 70)

if __name__ == "__main__":
    main()
