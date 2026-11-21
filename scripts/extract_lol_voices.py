import os
import sys
import glob
import wave
import struct
import subprocess
import shutil
import zstandard as zstd
from pathlib import Path
from metadata_manager import MetadataManager, sanitize_folder_name
from voice_categorizer import categorize_skin_folder

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

DEFAULT_HASHES_PATH = r"C:\Users\emrKvn\Downloads\Obsidian_5.1.8\hashes\hashes.game.txt"
import lol_voice_extractor_expert as voice_extractor

DEFAULT_LOL_CHAMPIONS_PATH = voice_extractor.LOL_CHAMPIONS_PATH
find_champion_wad_files = voice_extractor.find_champion_wad_files
OUTPUT_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Champions")
VGMSTREAM_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vgmstream", "vgmstream-cli.exe")
OBSIDIAN_HASHES_PATH = r"C:\Users\emrKvn\Downloads\Obsidian_5.1.8\hashes\hashes.game.txt"

def load_hashes(hashes_path):
    print(f"Hashtable yukleniyor: {hashes_path} ...")
    hashes = {}
    if not os.path.exists(hashes_path):
        print(f"HATA: Hashtable dosyasi bulunamadi: {hashes_path}")
        return hashes

    with open(hashes_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(' ', 1)
            if len(parts) == 2:
                try:
                    h_val = int(parts[0], 16)
                    hashes[h_val] = parts[1]
                except ValueError:
                    pass
    print(f"Toplam {len(hashes):,} hash yuklendi.")
    return hashes

def extract_wpk_wem_files(wpk_bytes):
    if len(wpk_bytes) < 12 or wpk_bytes[:4] != b'r3d2':
        return []

    magic, version, count = struct.unpack('<4sII', wpk_bytes[:12])
    if count == 0 or len(wpk_bytes) < (12 + count * 4):
        return []

    offsets = struct.unpack(f'<{count}I', wpk_bytes[12 : 12 + count * 4])
    wem_files = []

    for idx, entry_offset in enumerate(offsets):
        if entry_offset + 40 > len(wpk_bytes):
            continue
        entry_data = wpk_bytes[entry_offset : entry_offset + 40]
        offset, size, file_id = struct.unpack('<III', entry_data[:12])
        if offset + size <= len(wpk_bytes):
            wem_data = wpk_bytes[offset : offset + size]
            wem_files.append((idx, wem_data))

    return wem_files

def process_champion(champion_name, hashes, meta_mgr, lol_champions_dir):
    wad_path, _, resolved_champ = find_champion_wad_files(champion_name)
    if resolved_champ:
        champion_name = resolved_champ

    if not wad_path or not os.path.exists(wad_path):
        print(f" UYARI: {champion_name} ses WAD bulunamadi!")
        return False

    print(f"\n==========================================")
    print(f" Isleniyor: {champion_name}")
    print(f" Arsv: {wad_path}")
    print(f"==========================================")

    dctx = zstd.ZstdDecompressor()
    skins_extracted = set()

    with open(wad_path, 'rb') as f:
        magic = f.read(2)
        if magic != b'RW':
            print(f"HATA: Gecersiz WAD magic {magic}")
            return False

        f.seek(268)
        file_count_bytes = f.read(4)
        if len(file_count_bytes) < 4:
            print(f"HATA: WAD basligi okunamadi")
            return False

        file_count = struct.unpack('<I', file_count_bytes)[0]

        entries = []
        for _ in range(file_count):
            entry_bytes = f.read(32)
            path_hash, data_offset, csize, usize, type_flags = struct.unpack('<QIII4s', entry_bytes[:24])
            comp_type = type_flags[0] & 0xF
            entries.append((path_hash, data_offset, csize, usize, comp_type))

        temp_dir = os.path.join(OUTPUT_BASE_DIR, "_temp")
        os.makedirs(temp_dir, exist_ok=True)

        for path_hash, data_offset, csize, usize, comp_type in entries:
            file_path = hashes.get(path_hash, f"{path_hash:016x}.bin")
            
            if not (file_path.endswith('.wpk') or file_path.endswith('.wem')):
                continue

            f.seek(data_offset)
            raw_data = f.read(csize)
            if comp_type == 3:
                data = dctx.decompress(raw_data, max_output_size=usize)
            else:
                data = raw_data

            # Resolve skin name in Turkish
            raw_skin = "Base"
            parts = file_path.split('/')
            if 'skins' in parts:
                skin_idx = parts.index('skins')
                if skin_idx + 1 < len(parts):
                    raw_skin = parts[skin_idx + 1]

            turkish_skin_name = meta_mgr.resolve_skin_name(champion_name, raw_skin)
            skin_base_dir = os.path.join(OUTPUT_BASE_DIR, champion_name, turkish_skin_name)
            os.makedirs(skin_base_dir, exist_ok=True)
            skins_extracted.add(skin_base_dir)

            wpk_base_name = os.path.splitext(os.path.basename(file_path))[0]

            def convert_raw(wem_bytes, filename_prefix):
                temp_wem = os.path.join(temp_dir, "temp_audio.wem")
                out_wav_path = os.path.join(skin_base_dir, f"{filename_prefix}.wav")
                with open(temp_wem, "wb") as temp_f:
                    temp_f.write(wem_bytes)

                cmd = [VGMSTREAM_PATH, "-o", out_wav_path, temp_wem]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                if os.path.exists(temp_wem):
                    os.remove(temp_wem)

            if file_path.endswith('.wpk'):
                wems = extract_wpk_wem_files(data)
                for wem_idx, wem_bytes in wems:
                    convert_raw(wem_bytes, f"{wpk_base_name}_{wem_idx + 1:04d}")

            elif file_path.endswith('.wem'):
                convert_raw(data, f"{wpk_base_name}_{path_hash:016x}")

        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    print(f"\n[+] {champion_name} sesleri cikarildi, simdi detayli kategorilere ayriliyor...")
    for s_dir in skins_extracted:
        s_name = os.path.basename(s_dir)
        stats = categorize_skin_folder(s_dir, champion_name)
        print(f"\n  [Kostum] {s_name}")
        if stats:
            for cat, count in stats.items():
                if count > 0:
                    print(f"     |-- {cat}: {count} adet .wav")

    return True

def list_available_champions(lol_champions_dir):
    champions = []
    seen = set()
    if os.path.exists(lol_champions_dir):
        for f in sorted(os.listdir(lol_champions_dir)):
            if f.endswith('.wad.client'):
                base = f.replace('.wad.client', '')
                ch = base.split('.')[0]
                if ch and ch not in seen:
                    seen.add(ch)
                    champions.append(ch)
    champions.sort()
    return champions

def main():
    args = sys.argv[1:]
    
    print("==================================================")
    print(" League of Legends Turkce Ses Cikarici & Duzenleyici")
    print("==================================================")

    meta_mgr = MetadataManager()
    
    if "--list" in args:
        champs = list_available_champions(DEFAULT_LOL_CHAMPIONS_PATH)
        print(f"\nKurulu {len(champs)} Sampiyon Bulundu:")
        for i in range(0, len(champs), 6):
            print("  " + ", ".join(champs[i:i+6]))
        return

    hashes = load_hashes(DEFAULT_HASHES_PATH)
    if not hashes:
        return

    target_champions = []
    if "--all" in args:
        target_champions = list_available_champions(DEFAULT_LOL_CHAMPIONS_PATH)
        print(f"\nTum sampiyonlar islenecek ({len(target_champions)} sampiyon)...")
    elif len(args) > 0:
        target_champions = [a for a in args if not a.startswith("--")]
    else:
        target_champions = ["Zed", "Viktor"]

    for champ in target_champions:
        old_champ_dir = os.path.join(OUTPUT_BASE_DIR, champ)
        if os.path.exists(old_champ_dir):
            shutil.rmtree(old_champ_dir, ignore_errors=True)

    for champ in target_champions:
        process_champion(champ, hashes, meta_mgr, DEFAULT_LOL_CHAMPIONS_PATH)

    print("\n==================================================")
    print(" Tum islemler tamamlandi! Sesler 'Champions/' altinda kategorize edildi.")
    print("==================================================")

if __name__ == "__main__":
    main()
