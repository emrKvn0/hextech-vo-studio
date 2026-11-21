import os
import sys
import wave
import shutil

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

CATEGORIES = [
    ("1_Hareket_ve_Yurume", "Yürüme ve harita içi replikler"),
    ("2_Saldiri_ve_Dovus", "Saldırı ve çatışma replikleri"),
    ("3_Yetenekler_Q_W_E_R", "Q, W, E ve Ulti kullanım replikleri"),
    ("4_Saka_Kiskirtma_ve_Gulus", "Şaka, kışkırtma, kahkaha ve dans replikleri"),
    ("5_Ozel_Karsilasmalar_ve_Atiflar", "Şampiyonlara özel karşılaşma ve öldürme atıfları"),
    ("6_Donus_ve_Olum", "Üsse dönüş (B) ve can verme replikleri"),
    ("7_Efor_ve_Kisa_Efektler", "Kısa vuruş, nefes ve hırıltı efektleri")
]

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

def categorize_skin_folder(skin_dir, champ_name):
    if not os.path.exists(skin_dir):
        return

    all_wavs = []
    for root, dirs, files in os.walk(skin_dir):
        for f in files:
            if f.endswith('.wav'):
                all_wavs.append(os.path.join(root, f))

    if not all_wavs:
        return

    cat_dirs = {}
    for cat_name, _ in CATEGORIES:
        d = os.path.join(skin_dir, cat_name)
        os.makedirs(d, exist_ok=True)
        cat_dirs[cat_name] = d

    wav_info = []
    for p in all_wavs:
        dur = get_audio_duration(p)
        fname = os.path.basename(p)
        wav_info.append({
            'path': p,
            'filename': fname,
            'duration': dur
        })

    wav_info.sort(key=lambda x: x['filename'])

    stats = {cat[0]: 0 for cat in CATEGORIES}

    staging_dir = os.path.join(skin_dir, "_staging")
    os.makedirs(staging_dir, exist_ok=True)

    for item in wav_info:
        staged_p = os.path.join(staging_dir, item['filename'])
        shutil.move(item['path'], staged_p)
        item['staged_path'] = staged_p

    for old_folder in ["Replikler", "Efor_ve_Efektler", "temp"]:
        old_p = os.path.join(skin_dir, old_folder)
        if os.path.exists(old_p):
            shutil.rmtree(old_p, ignore_errors=True)

    for idx, item in enumerate(wav_info):
        dur = item['duration']
        src = item['staged_path']

        if dur < 1.5:
            target_cat = "7_Efor_ve_Kisa_Efektler"
            new_name = f"{champ_name.lower()}_efor_{stats[target_cat]+1:03d}.wav"
        elif dur >= 4.8:
            target_cat = "5_Ozel_Karsilasmalar_ve_Atiflar"
            new_name = f"{champ_name.lower()}_atif_{stats[target_cat]+1:03d}.wav"
        elif dur >= 3.2:
            if idx % 5 == 0:
                target_cat = "4_Saka_Kiskirtma_ve_Gulus"
                new_name = f"{champ_name.lower()}_emote_{stats[target_cat]+1:03d}.wav"
            elif idx % 7 == 0:
                target_cat = "6_Donus_ve_Olum"
                new_name = f"{champ_name.lower()}_donus_{stats[target_cat]+1:03d}.wav"
            else:
                target_cat = "1_Hareket_ve_Yurume"
                new_name = f"{champ_name.lower()}_hareket_{stats[target_cat]+1:03d}.wav"
        else: # 1.5s <= dur < 3.2s
            if idx % 2 == 0:
                target_cat = "3_Yetenekler_Q_W_E_R"
                new_name = f"{champ_name.lower()}_yetenek_{stats[target_cat]+1:03d}.wav"
            else:
                target_cat = "2_Saldiri_ve_Dovus"
                new_name = f"{champ_name.lower()}_saldiri_{stats[target_cat]+1:03d}.wav"

        stats[target_cat] += 1
        dst = os.path.join(cat_dirs[target_cat], new_name)
        shutil.move(src, dst)

    if os.path.exists(staging_dir):
        shutil.rmtree(staging_dir, ignore_errors=True)

    for cat_name, dpath in cat_dirs.items():
        if os.path.exists(dpath) and len(os.listdir(dpath)) == 0:
            os.rmdir(dpath)

    return stats

def categorize_champion(champ_name):
    champ_dir = os.path.join("Champions", champ_name)
    if not os.path.exists(champ_dir):
        print(f"HATA: {champ_name} klasoru bulunamadi!")
        return

    print(f"\n==========================================")
    print(f" Detayli Kategorizasyon: {champ_name}")
    print(f"==========================================")

    for skin in os.listdir(champ_dir):
        skin_path = os.path.join(champ_dir, skin)
        if os.path.isdir(skin_path):
            stats = categorize_skin_folder(skin_path, champ_name)
            print(f"\n  [Kostum] {skin}")
            if stats:
                for cat, count in stats.items():
                    if count > 0:
                        print(f"     |-- {cat}: {count} adet .wav")

if __name__ == "__main__":
    for champ in ["Zed", "Viktor"]:
        categorize_champion(champ)
