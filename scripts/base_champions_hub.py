import os
import sys
import shutil
import functools
from xml.sax.saxutils import escape

# Ensure UTF-8 output
print = functools.partial(print, flush=True)

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def get_output_base():
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "Champions")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Champions")

from metadata_manager import MetadataManager
import lol_voice_extractor_expert as voice_extractor

CHAMPIONS_OUTPUT_PATH = get_output_base()
HUB_FOLDER_NAME = "_Tum_Varsayilan_Sampiyonlar_A_dan_Z_ye"
HUB_PATH = os.path.join(CHAMPIONS_OUTPUT_PATH, HUB_FOLDER_NAME)
LOL_CHAMPIONS_PATH = voice_extractor.LOL_CHAMPIONS_PATH

def get_all_game_champions():
    champs = []
    seen = set()
    if os.path.exists(LOL_CHAMPIONS_PATH):
        for f in sorted(os.listdir(LOL_CHAMPIONS_PATH)):
            if f.endswith('.wad.client'):
                base = f.replace('.wad.client', '')
                ch = base.split('.')[0]
                if ch and ch not in seen:
                    seen.add(ch)
                    champs.append(ch)
    if not champs:
        meta_mgr = MetadataManager()
        for s in meta_mgr.skins_raw_db:
            c_name = s.get('champion_name') or s.get('champion_alias')
            if c_name and c_name not in seen:
                seen.add(c_name)
                champs.append(c_name)
    champs.sort()
    return champs

def find_champion_base_folder(champ_dir):
    if not os.path.isdir(champ_dir):
        return None
    for sub in os.listdir(champ_dir):
        sub_path = os.path.join(champ_dir, sub)
        if not os.path.isdir(sub_path):
            continue
        sub_lower = sub.lower()
        if sub_lower in ('varsayilan_hali', 'base') or 'varsayilan' in sub_lower or 'varsayılan' in sub_lower:
            return sub_path
    return None

def get_hub_status():
    os.makedirs(HUB_PATH, exist_ok=True)
    all_game_champs = get_all_game_champions()

    # 1. Check what's already in the Hub
    hub_champs = {}
    total_hub_voices = 0
    if os.path.exists(HUB_PATH):
        for entry in sorted(os.listdir(HUB_PATH)):
            entry_path = os.path.join(HUB_PATH, entry)
            if os.path.isdir(entry_path) and not entry.startswith('.'):
                wav_count = sum(1 for root, _, files in os.walk(entry_path) for f in files if f.lower().endswith('.wav'))
                if wav_count > 0:
                    hub_champs[entry] = wav_count
                    total_hub_voices += wav_count

    # 2. Check what's in Champions/ that has a Base folder
    available_to_sync = {}
    for entry in sorted(os.listdir(CHAMPIONS_OUTPUT_PATH)):
        if entry.startswith('_') or entry.startswith('.'):
            continue
        champ_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, entry)
        base_folder = find_champion_base_folder(champ_dir)
        if base_folder:
            wav_count = sum(1 for root, _, files in os.walk(base_folder) for f in files if f.lower().endswith('.wav'))
            if wav_count > 0:
                available_to_sync[entry] = wav_count

    return {
        "hub_path": HUB_PATH,
        "hub_folder_name": HUB_FOLDER_NAME,
        "total_game_champions": len(all_game_champs),
        "synced_champions_count": len(hub_champs),
        "total_synced_voices": total_hub_voices,
        "available_champions_count": len(available_to_sync),
        "hub_champions": hub_champs,
        "available_to_sync": available_to_sync
    }

def sync_all_base_champions_to_hub():
    """
    Scans Champions/ and copies all base skin voice lines into _Tum_Varsayilan_Sampiyonlar_A_dan_Z_ye/{Champion}/.
    """
    os.makedirs(HUB_PATH, exist_ok=True)
    print(f"\n================================================================================")
    print(f" 📦 TÜM VARSAYILAN ŞAMPİYONLAR A-Z HUB'I SENKRONİZASYONU")
    print(f"================================================================================")
    print(f"📂 Hedef Hub Klasörü: {HUB_PATH}\n")

    synced_champs = 0
    synced_files_total = 0

    for entry in sorted(os.listdir(CHAMPIONS_OUTPUT_PATH)):
        if entry.startswith('_') or entry.startswith('.'):
            continue
        champ_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, entry)
        base_folder = find_champion_base_folder(champ_dir)
        if not base_folder:
            continue

        target_champ_hub_dir = os.path.join(HUB_PATH, entry)
        os.makedirs(target_champ_hub_dir, exist_ok=True)

        champ_files = 0
        for root, _, files in os.walk(base_folder):
            for f in files:
                if f.lower().endswith('.wav'):
                    src_f = os.path.join(root, f)
                    dst_f = os.path.join(target_champ_hub_dir, f)
                    if not os.path.exists(dst_f) or os.path.getsize(src_f) != os.path.getsize(dst_f):
                        shutil.copy2(src_f, dst_f)
                    champ_files += 1

        if champ_files > 0:
            synced_champs += 1
            synced_files_total += champ_files
            print(f"   ├─ 🛡️ {entry}: {champ_files} adet varsayılan replik senkronize edildi.")

    print(f"\n✨ Senkronizasyon Tamamlandı! Toplam {synced_champs} şampiyon, {synced_files_total} replik A-Z Hub'ında hazır.")
    return {
        "status": "success",
        "synced_champions": synced_champs,
        "total_files": synced_files_total,
        "hub_path": HUB_PATH
    }

def generate_base_hub_master_davinci_xml(gap_seconds=0.2, fps=60):
    """
    Generates a master DaVinci Resolve Timeline XML for all Base Champions in A-Z order.
    """
    from davinci_exporter import DaVinciTimelineExporter
    
    os.makedirs(HUB_PATH, exist_ok=True)
    all_files_ordered = []

    # Iterate alphabetically through every champion in the hub
    for champ_folder in sorted(os.listdir(HUB_PATH)):
        champ_path = os.path.join(HUB_PATH, champ_folder)
        if not os.path.isdir(champ_path) or champ_folder.startswith('.'):
            continue

        champ_wavs = []
        for root, _, files in os.walk(champ_path):
            for f in sorted(files):
                if f.lower().endswith('.wav'):
                    champ_wavs.append(os.path.join(root, f))

        if champ_wavs:
            # Sort within champion using narrative ordering
            sorted_champ_wavs = DaVinciTimelineExporter.filter_and_sort_files(
                champ_wavs, exclude_sfx=True, smart_sort=True
            )
            all_files_ordered.extend(sorted_champ_wavs)

    if not all_files_ordered:
        return {
            "status": "error",
            "message": "A-Z Hub klasöründe henüz ses dosyası bulunamadı. Lütfen önce 'Senkronize Et' veya 'Varsayılan Sesleri Çıkar' butonunu kullanın."
        }

    output_xml = os.path.join(
        HUB_PATH, 
        f"00_TUM_VARSAYILANLAR_A_DAN_Z_YE_DaVinci_{gap_seconds}s_Gap.xml"
    )

    timeline_name = f"LoL Tüm Varsayılan Şampiyonlar (A-Z) - {len(all_files_ordered)} Ses"
    
    output_xml, total_clips, total_dur_secs = DaVinciTimelineExporter.generate_fcp7_xml(
        audio_files=all_files_ordered,
        output_path=output_xml,
        gap_seconds=gap_seconds,
        timeline_name=timeline_name,
        fps=fps,
        smart_sort=False, # already sorted per-champion above
        exclude_sfx=False
    )

    minutes = int(total_dur_secs // 60)
    seconds = int(total_dur_secs % 60)
    duration_formatted = f"{minutes:02d}:{seconds:02d}"

    return {
        "status": "success",
        "output_xml_path": output_xml,
        "filename": os.path.basename(output_xml),
        "total_audio_count": total_clips,
        "total_duration_formatted": duration_formatted,
        "total_duration_seconds": total_dur_secs
    }


def batch_extract_all_base_champions(progress_callback=None):
    """
    Extracts all 170 Base Champions' voices in parallel and saves them directly to the A-Z Hub.
    """
    import lol_voice_extractor_expert as extractor
    hashes = extractor.load_hashes()
    all_champs = get_all_game_champions()

    print(f"\n================================================================================")
    print(f" 🚀 TÜM 170+ ŞAMPİYONUN VARSAYILAN SESLERİNİ ÇIKARMA MOTORU (A-Z HUB)")
    print(f"================================================================================")

    extracted_count = 0
    for idx, champ in enumerate(all_champs, 1):
        msg = f"[{idx}/{len(all_champs)}] 🎯 {champ} varsayılan sesleri çıkarılıyor..."
        print(msg)
        if progress_callback:
            progress_callback(msg)

        try:
            extractor.extract_champion_full(champ, hashes, target_skin="Varsayilan_Hali")
            extracted_count += 1
        except Exception as e:
            print(f"   ⚠️ {champ} çıkarılırken hata: {e}")

    # Sync into hub
    sync_res = sync_all_base_champions_to_hub()
    # Generate master DaVinci XML
    xml_res = generate_base_hub_master_davinci_xml(gap_seconds=0.2)

    return {
        "status": "success",
        "extracted_champions": extracted_count,
        "sync_result": sync_res,
        "davinci_xml": xml_res
    }

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'sync':
        sync_all_base_champions_to_hub()
    elif len(sys.argv) > 1 and sys.argv[1] == 'xml':
        res = generate_base_hub_master_davinci_xml()
        print("XML result:", res)
    elif len(sys.argv) > 1 and sys.argv[1] == 'extract-all':
        batch_extract_all_base_champions()
    else:
        status = get_hub_status()
        print("Hub Status:", status)
