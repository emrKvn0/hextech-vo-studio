#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os

def get_resolve():
    try:
        if 'resolve' in globals() and resolve: return resolve
    except NameError: pass
    try:
        if 'app' in globals() and app: return app.GetResolve()
    except NameError: pass
    try:
        import bmd
        return bmd.scriptapp('Resolve')
    except Exception: pass
    for mod in ['DaVinciResolveScript', 'fusionscript']:
        try:
            m = __import__(mod)
            r = m.scriptapp('Resolve')
            if r: return r
        except Exception: pass
    return None

def main():
    print('=' * 70)
    print('🎬 LoL Standart FCPXML Kliplerine Fade In (1.5s) / Out (0.5s) Başlatıldı')
    print('=' * 70)

    res = get_resolve()
    if not res:
        print('❌ DaVinci Resolve nesnesi bulunamadı.')
        return

    pm = res.GetProjectManager()
    proj = pm.GetCurrentProject() if pm else None
    if not proj:
        print('❌ Aktif proje yok.')
        return

    timeline = proj.GetCurrentTimeline()
    if not timeline:
        print('❌ Aktif timeline yok.')
        return

    fps = float(timeline.GetSetting('timelineFrameRate') or 60.0)
    in_frames = int(round(1.5 * fps))
    out_frames = int(round(0.5 * fps))
    print(f'📌 Timeline: {timeline.GetName()} ({fps} FPS)')
    print(f'⏱️ Fade In: {in_frames} frame | Fade Out: {out_frames} frame')

    track_count = timeline.GetTrackCount('video')
    for t_idx in range(1, track_count + 1):
        items = timeline.GetItemListInTrack('video', t_idx) or []
        if not items: continue
        print(f'\n🎯 Video {t_idx} taranıyor ({len(items)} klip)...')
        for itm in items:
            name = itm.GetName() or 'Klip'
            dur = itm.GetDuration()
            # Standart klip kulakçıkları / Fade ayarları
            try:
                itm.SetProperty('FadeInFrames', in_frames)
                itm.SetProperty('FadeOutFrames', out_frames)
            except Exception as e:
                pass
            print(f'  ✓ {name} (Dur: {dur})')

    print('\n' + '=' * 70)
    print('🎉 Tamamlandı!')
    print('=' * 70)

if __name__ == '__main__':
    main()
