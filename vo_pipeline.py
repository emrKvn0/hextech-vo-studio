# -*- coding: utf-8 -*-
"""
================================================================================
LoL Replik & Ses Hattı CLI (vo_pipeline.py)
================================================================================
HUKUKİ VE LİSANS BİLDİRİMİ:
- League of Legends Wiki replik metinleri Creative Commons Attribution-
  ShareAlike (CC BY-SA 3.0 / 4.0) lisansına tabidir.
  Kaynak ve atıf URL'si: https://wiki.leagueoflegends.com/
  Oyun içi tüm ses dosyaları ve fikri mülkiyet hakları Riot Games Inc.'e aittir.
- YouTube SkinSpotlights altyazıları kanal sahibinin içeriğidir; yalnızca referans
  ve yedek amacıyla kullanılır.
================================================================================
Kullanım:
  python vo_pipeline.py --champion Sett --skin "Radiant Serpent"
  python vo_pipeline.py --champion Diana --skin "Eternal Aspect Diana"
  python vo_pipeline.py --champion Aatrox --skin "Primordian Aatrox"
================================================================================
"""

import sys
import os
import argparse
import json

# scripts klasörünü sys.path'e dahil et
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(CURRENT_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from wiki_voice_pipeline import VOPipeline, WikiAudioFetcher, SkinSpotlightsCCFetcher

def main():
    parser = argparse.ArgumentParser(description="LoL Şampiyon Replik Metinleri Wiki/YouTube Pipeline CLI")
    parser.add_argument("--champion", "-c", required=True, help="Şampiyon adı (örn: Sett, Diana, Aatrox)")
    parser.add_argument("--skin", "-s", default="Classic", help="Kostüm adı (örn: Classic, Radiant Serpent, Primordian)")
    parser.add_argument("--force-wiki", action="store_true", help="Yerel sesleri atla, doğrudan Wiki/YouTube fallback hattını çalıştır")
    parser.add_argument("--no-translate", action="store_true", help="Türkçe çeviriyi atla")
    parser.add_argument("--check-tabs", action="store_true", help="Sadece şampiyonun mevcut wiki sekmelerini listele")

    args = parser.parse_args()

    # UTF-8 stdout garantisi
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    if args.check_tabs:
        info = WikiAudioFetcher.list_available_sections_and_tabs(args.champion)
        print(f"\n[{args.champion}] Mevcut Wiki Sekmeleri ve Bölümleri:")
        print(f"Sekmeler (Tabs): {info.get('tabs')}")
        print(f"Ana Başlıklar: {info.get('sections')[:10]}")
        return

    print(f"\n=======================================================")
    print(f"🚀 REPLİK VE SES HATTI BAŞLATILIYOR: {args.champion} ({args.skin})")
    print(f"=======================================================")

    res = VOPipeline.run(
        champion=args.champion,
        skin_name=args.skin,
        use_whisper=True,
        translate=(not args.no_translate),
        force_wiki=args.force_wiki
    )

    print(f"\n[DURUM]")
    print(f"- Kaynak: {res['source_used']}")
    print(f"- Toplam Replik Sayısı: {res['total_quotes']}")
    print(f"- Eşleşme Özeti: Matched={res['match_summary'].get('matched_count', 0)}, "
          f"Needs Review={res['match_summary'].get('needs_review_count', 0)}, "
          f"Unmatched={res['match_summary'].get('unmatched_count', 0)}")
    print(f"- Çıktı Dosyası: {res['output_file']}")

    print(f"\n[TETİKLEYİCİ (TRIGGER) DAĞILIMI]:")
    for trg, cnt in list(res['trigger_distribution'].items())[:12]:
        print(f"  • {trg}: {cnt}")
    if len(res['trigger_distribution']) > 12:
        print(f"  ... ve {len(res['trigger_distribution']) - 12} diğer tetikleyici")

    print(f"\n[İLK 5 REPLİK ÖRNEĞİ]:")
    for idx, q in enumerate(res['first_5_quotes'], 1):
        trg = q.get('trigger', '')
        en = q.get('text_en', '')
        tr = q.get('text_tr', '')
        act = q.get('action_note', '')
        aud = q.get('audio_file', '')
        status = q.get('match_status', 'unmatched')
        print(f"  {idx}. [{trg}]")
        print(f"     EN: \"{en}\"")
        if tr:
            print(f"     TR: \"{tr}\"")
        if act:
            print(f"     Sahne Notu: [{act}]")
        if aud:
            print(f"     Ses: {aud} | Durum: {status}")
        print()

if __name__ == "__main__":
    main()
