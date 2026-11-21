import os
import sys
import wave
import struct
import shutil
import subprocess
import zstandard as zstd
from metadata_manager import MetadataManager

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import lol_voice_extractor_expert as voice_extractor

HASHES_PATH = r"C:\Users\emrKvn\Downloads\Obsidian_5.1.8\hashes\hashes.game.txt"
LOL_CHAMPIONS_PATH = voice_extractor.LOL_CHAMPIONS_PATH
find_champion_wad_files = voice_extractor.find_champion_wad_files
VGMSTREAM_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vgmstream", "vgmstream-cli.exe")
OUTPUT_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Champions")

def load_hashes():
    hashes = {}
    if os.path.exists(HASHES_PATH):
        with open(HASHES_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(' ', 1)
                if len(parts) == 2:
                    try:
                        hashes[int(parts[0], 16)] = parts[1]
                    except ValueError:
                        pass
    return hashes

def extract_wpk_wems(wpk_bytes):
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
        offset, size, wem_id = struct.unpack('<III', entry_data[:12])
        if offset + size <= len(wpk_bytes):
            wem_data = wpk_bytes[offset : offset + size]
            wem_files.append((wem_id, wem_data))

    return wem_files

def get_audio_duration(wav_path):
    try:
        with wave.open(wav_path, 'rb') as w:
            frames = w.getnframes()
            rate = w.getframerate()
            if rate > 0:
                return frames / float(rate)
    except Exception:
        pass
    return 0.0

def process_champion(champ_name, lol_dir, hashes, meta_mgr):
    wad_path, _, resolved_champ = find_champion_wad_files(champ_name)
    if resolved_champ:
        champ_name = resolved_champ

    if not wad_path or not os.path.exists(wad_path):
        print(f"HATA: {champ_name} ses WAD dosyası bulunamadı!")
        return

    print(f"\n==================================================")
    print(f" 🎮 {champ_name} - Oyun Dosyaları Çıkarılıyor")
    print(f"==================================================")

    dctx = zstd.ZstdDecompressor()
    champ_out = os.path.join(OUTPUT_BASE, champ_name)
    temp_dir = os.path.join(OUTPUT_BASE, f"_temp_{champ_name}")
    os.makedirs(temp_dir, exist_ok=True)

    with open(wad_path, 'rb') as f:
        f.seek(268)
        fc = struct.unpack('<I', f.read(4))[0]
        entries = []
        for _ in range(fc):
            eb = f.read(32)
            phash, doff, csz, usz, tflags = struct.unpack('<QIII4s', eb[:24])
            entries.append((phash, doff, csz, usz, tflags[0] & 0xF))

        skins_wpk_list = {}

        for phash, doff, csz, usz, ctype in entries:
            fname = hashes.get(phash, f"{phash:016x}.bin")
            if fname.endswith('.wpk'):
                f.seek(doff)
                raw = f.read(csz)
                data = dctx.decompress(raw, max_output_size=usz) if ctype == 3 else raw

                raw_skin = "Base"
                parts = fname.split('/')
                if 'skins' in parts:
                    s_idx = parts.index('skins')
                    if s_idx + 1 < len(parts):
                        raw_skin = parts[s_idx + 1]

                turkish_skin = meta_mgr.resolve_skin_name(champ_name, raw_skin)
                skins_wpk_list.setdefault(turkish_skin, []).append(data)

    for skin_name, wpk_bytes_list in sorted(skins_wpk_list.items()):
        skin_dir = os.path.join(champ_out, skin_name)
        shutil.rmtree(skin_dir, ignore_errors=True)
        
        replikler_dir = os.path.join(skin_dir, "Replikler")
        efektler_dir = os.path.join(skin_dir, "Ses_Efektleri")
        os.makedirs(replikler_dir, exist_ok=True)
        os.makedirs(efektler_dir, exist_ok=True)

        replik_count = 0
        efekt_count = 0

        for wpk_data in wpk_bytes_list:
            wems = extract_wpk_wems(wpk_data)
            for wem_id, wem_bytes in wems:
                twem = os.path.join(temp_dir, f"temp_{wem_id}.wem")
                twav = os.path.join(temp_dir, f"temp_{wem_id}.wav")
                with open(twem, 'wb') as tf:
                    tf.write(wem_bytes)

                cmd = [VGMSTREAM_PATH, "-o", twav, twem]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                if os.path.exists(twav):
                    dur = get_audio_duration(twav)

                    if dur < 1.3:
                        efekt_count += 1
                        dst_name = f"{champ_name.lower()}_efekt_{efekt_count:03d}.wav"
                        shutil.copyfile(twav, os.path.join(efektler_dir, dst_name))
                    else:
                        replik_count += 1
                        dst_name = f"{champ_name.lower()}_replik_{replik_count:03d}_wem_{wem_id}.wav"
                        shutil.copyfile(twav, os.path.join(replikler_dir, dst_name))

                    try:
                        os.remove(twav)
                    except Exception:
                        pass

                if os.path.exists(twem):
                    try:
                        os.remove(twem)
                    except Exception:
                        pass

        print(f"  [Kostüm] {skin_name}:")
        print(f"     ├─ 🗣️ Replikler: {replik_count} adet .wav")
        print(f"     └─ 🔊 Ses Efektleri: {efekt_count} adet .wav")

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"✅ {champ_name} için tüm kostümler eksiksiz çıkarıldı!")

def main():
    hashes = load_hashes()
    meta_mgr = MetadataManager()
    for champ in ["Zed", "Viktor"]:
        process_champion(champ, LOL_CHAMPIONS_PATH, hashes, meta_mgr)

if __name__ == "__main__":
    main()
