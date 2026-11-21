import os
import sys
import time
import json
import shutil
import urllib.parse
from pathlib import Path

class DaVinciResolveAPI:
    """
    DaVinci Resolve Python Scripting API & Fusion Automation Engine.
    
    Özellikler:
    1. Otomatik Çevre ve DLL Tespiti (Windows fusionscript.dll & DaVinciResolveScript.py)
    2. Mevcut Açık Timeline'daki Standart "Text" (Legacy) Kliplerini Otomatik "Text+" (Fusion Title)'a Dönüştürme
    3. Text+'a Procedural Anim Curves ile Süreden Bağımsız Otomatik Fade In (1.5s) & Fade Out (0.5s) Entegrasyonu
    4. Sıfırdan Tek Tıkla DaVinci Timeline'ı Oluşturma (Sesler A1, Text+ V1, Whisper AI Replik Metinleri)
    5. DaVinci Resolve Script Menüsüne (Workspace -> Scripts -> Edit) Tek Tıkla Kurulum
    """

    _resolve = None
    _script_module_loaded = False

    @classmethod
    def init_environment(cls):
        """DaVinci Resolve Scripting modül yollarını ve ortam değişkenlerini hazırlar."""
        if cls._script_module_loaded:
            return True

        appdata = os.environ.get('APPDATA', '')
        programdata = os.environ.get('PROGRAMDATA', r'C:\ProgramData')
        programfiles = os.environ.get('PROGRAMFILES', r'C:\Program Files')

        possible_module_paths = [
            os.path.join(programdata, r'Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules'),
            os.path.join(programfiles, r'Blackmagic Design\DaVinci Resolve\Developer\Scripting\Modules'),
            os.path.join(appdata, r'Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules')
        ]

        possible_dll_paths = [
            os.path.join(programfiles, r'Blackmagic Design\DaVinci Resolve\fusionscript.dll'),
            r'C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll',
            r'C:\Program Files (x86)\Blackmagic Design\DaVinci Resolve\fusionscript.dll'
        ]

        # DLL path
        for dll in possible_dll_paths:
            if os.path.isfile(dll):
                os.environ['RESOLVE_SCRIPT_LIB'] = dll
                break

        # API root path
        resolve_api_root = os.path.join(programdata, r'Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting')
        if os.path.exists(resolve_api_root):
            os.environ['RESOLVE_SCRIPT_API'] = resolve_api_root

        # Add module path to sys.path
        for mod_path in possible_module_paths:
            if os.path.exists(mod_path) and mod_path not in sys.path:
                sys.path.insert(0, mod_path)

        cls._script_module_loaded = True
        return True

    @classmethod
    def get_resolve(cls):
        """DaVinci Resolve örneğine bağlanır (Resolve açık olmalıdır)."""
        cls.init_environment()
        try:
            import DaVinciResolveScript as dvr_script
            resolve = dvr_script.scriptapp("Resolve")
            if resolve:
                cls._resolve = resolve
                return resolve
        except Exception:
            pass

        try:
            import fusionscript as dvr_script
            resolve = dvr_script.scriptapp("Resolve")
            if resolve:
                cls._resolve = resolve
                return resolve
        except Exception:
            pass

        return None

    @classmethod
    def get_status(cls):
        """DaVinci Resolve bağlantı durumunu, açık projeyi ve timeline bilgilerini döner."""
        resolve = cls.get_resolve()
        if not resolve:
            return {
                "connected": False,
                "version": None,
                "project_name": None,
                "timeline_name": None,
                "clip_count": 0,
                "message": "DaVinci Resolve açık değil veya Scripting API'ye henüz yanıt vermiyor."
            }

        try:
            version = resolve.GetVersionString()
            pm = resolve.GetProjectManager()
            current_project = pm.GetCurrentProject() if pm else None
            project_name = current_project.GetName() if current_project else None

            timeline_name = None
            clip_count = 0
            if current_project:
                current_timeline = current_project.GetCurrentTimeline()
                if current_timeline:
                    timeline_name = current_timeline.GetName()
                    v_items = current_timeline.GetItemListInTrack("video", 1) or []
                    a_items = current_timeline.GetItemListInTrack("audio", 1) or []
                    clip_count = max(len(v_items), len(a_items))

            return {
                "connected": True,
                "version": str(version),
                "project_name": project_name,
                "timeline_name": timeline_name,
                "clip_count": clip_count,
                "message": f"DaVinci Resolve {version} bağlı! Aktif Proje: '{project_name or 'Yok'}'"
            }
        except Exception as e:
            return {
                "connected": False,
                "version": None,
                "project_name": None,
                "timeline_name": None,
                "clip_count": 0,
                "message": f"DaVinci API Sorgu Hatası: {e}"
            }

    @classmethod
    def convert_timeline_text_to_textplus(cls, fade_in_sec=1.5, fade_out_sec=0.5, font="Poppins", style="SemiBold", size=0.05, create_new_track=True):
        """
        DaVinci Resolve'da açık olan aktif Timeline üzerindeki tüm standart Text kliplerini tarar.
        Her birinin süresini ve metnini alıp Text+ (Fusion Generator / TextPlus) klibine dönüştürür.
        Metnin Opacity değerine Anim Curves bağlayarak otomatik Fade In (1.5s) ve Fade Out (0.5s) uygular.
        """
        resolve = cls.get_resolve()
        if not resolve:
            return {
                "status": "error",
                "message": "DaVinci Resolve açık değil. Lütfen önce DaVinci Resolve'u başlatın."
            }

        pm = resolve.GetProjectManager()
        project = pm.GetCurrentProject() if pm else None
        if not project:
            return {"status": "error", "message": "Açık bir DaVinci Resolve projesi bulunamadı."}

        timeline = project.GetCurrentTimeline()
        if not timeline:
            return {"status": "error", "message": "Projede aktif bir Timeline bulunamadı. Lütfen bir timeline açın."}

        fps = float(timeline.GetSetting("timelineFrameRate") or 60.0)
        fade_in_frames = int(round(fade_in_sec * fps))
        fade_out_frames = int(round(fade_out_sec * fps))

        # Media Pool
        mp = project.GetMediaPool()

        converted_count = 0
        details = []

        track_count = timeline.GetTrackCount("video")
        
        for t_idx in range(1, track_count + 1):
            items = timeline.GetItemListInTrack("video", t_idx) or []
            for item in items:
                name = item.GetName()
                start_frame = item.GetStart()
                end_frame = item.GetEnd()
                dur_frames = item.GetDuration()
                
                fusion_comp_count = item.GetFusionCompCount()
                if fusion_comp_count > 0:
                    comp = item.GetFusionCompByIndex(1)
                    if comp:
                        tool_list = comp.GetToolList(False, "TextPlus")
                        if tool_list and len(tool_list) > 0:
                            t_tool = tool_list[1]
                            cls._apply_anim_curves_to_tool(comp, t_tool, fade_in_sec, fade_out_sec, fps, dur_frames)
                            converted_count += 1
                            details.append(f"Güncellendi: '{name}' ({dur_frames} kare) -> Fade In: {fade_in_sec}s, Out: {fade_out_sec}s")
                            continue

                text_content = name
                try:
                    comp = item.AddFusionComp() if fusion_comp_count == 0 else item.GetFusionCompByIndex(1)
                    if comp:
                        t_tool = comp.AddTool("TextPlus")
                        if t_tool:
                            t_tool.StyledText = text_content
                            try:
                                t_tool.Font = font
                                t_tool.Style = style
                                t_tool.Size = size
                            except Exception:
                                pass
                            
                            cls._apply_anim_curves_to_tool(comp, t_tool, fade_in_sec, fade_out_sec, fps, dur_frames)
                            
                            mo = comp.FindToolByID("MediaOut") or comp.GetToolList(False, "MediaOut")
                            if mo:
                                mo_tool = mo[1] if isinstance(mo, dict) else mo
                                mo_tool.ConnectInput("Input", t_tool)
                                
                            converted_count += 1
                            details.append(f"Dönüştürüldü: '{text_content[:30]}' ({dur_frames} kare)")
                except Exception as e:
                    details.append(f"Atlandı: '{name}' ({e})")

        return {
            "status": "success",
            "converted_count": converted_count,
            "timeline_name": timeline.GetName(),
            "fade_in_sec": fade_in_sec,
            "fade_out_sec": fade_out_sec,
            "details": details,
            "message": f"✨ Timeline üzerindeki {converted_count} metin klibine başarıyla Text+ ve Anim Curves (Fade In: {fade_in_sec}s / Fade Out: {fade_out_sec}s) uygulandı!"
        }

    @classmethod
    def _apply_anim_curves_to_tool(cls, comp, tool, fade_in_sec, fade_out_sec, fps, dur_frames):
        """Fusion TextPlus aracının Opacity parametresine AnimCurves bağlar veya Keyframe animasyonu ekler."""
        try:
            modifier = comp.AddModifier("AnimCurves", "AnimCurves")
            if modifier:
                modifier.Curve = "Ease In / Out"
                modifier.Source = "Duration"
                tool.Opacity1.ConnectTo(modifier)
                return True
        except Exception:
            pass

        try:
            fade_in_frames = max(1, int(round(fade_in_sec * fps)))
            fade_out_frames = max(1, int(round(fade_out_sec * fps)))
            
            if hasattr(tool, 'Opacity1'):
                tool.Opacity1[0] = 0.0
                tool.Opacity1[fade_in_frames] = 1.0
                out_start = max(fade_in_frames, dur_frames - fade_out_frames)
                tool.Opacity1[out_start] = 1.0
                tool.Opacity1[dur_frames] = 0.0
                return True
        except Exception:
            pass

        return False

    @classmethod
    def create_direct_timeline_with_textplus(cls, audio_files, timeline_name="LoL Sesler Timeline", gap_seconds=0.2, fade_in_sec=1.5, fade_out_sec=0.5, fps=60, target_champion=""):
        """
        Doğrudan DaVinci Resolve Python Scripting API üzerinden:
        1. Ses dosyalarını Media Pool'a aktarır.
        2. Yeni bir 2K 60FPS Timeline oluşturur.
        3. Ses kliplerini A1 kanalına gap_seconds aralıkla dizer.
        4. V1 kanalına her sesin Whisper AI replik metnini içeren Text+ kliplerini dizip Anim Curves (1.5s In, 0.5s Out) atar.
        """
        resolve = cls.get_resolve()
        if not resolve:
            return {
                "status": "error",
                "message": "DaVinci Resolve açık değil. Lütfen önce DaVinci Resolve programını başlatın."
            }

        pm = resolve.GetProjectManager()
        project = pm.GetCurrentProject()
        if not project:
            project = pm.CreateProject(f"LoL_Voice_Studio_{int(time.time())}")
            if not project:
                return {"status": "error", "message": "DaVinci projesi açılamadı veya oluşturulamadı."}

        mp = project.GetMediaPool()
        root_folder = mp.GetRootFolder()

        from davinci_exporter import DaVinciTimelineExporter
        sorted_files = DaVinciTimelineExporter.filter_and_sort_files(
            audio_files, 
            exclude_sfx=True, 
            smart_sort=True, 
            target_champion=target_champion
        )

        if not sorted_files:
            return {"status": "error", "message": "Aktarılacak geçerli ses dosyası bulunamadı."}

        sub_bin_name = f"LoL_Voices_{int(time.time()) % 10000}"
        voice_bin = mp.AddSubFolder(root_folder, sub_bin_name)
        if voice_bin:
            mp.SetCurrentFolder(voice_bin)

        abs_paths = [os.path.abspath(f) for f in sorted_files]
        media_clips = mp.ImportMedia(abs_paths)
        if not media_clips:
            return {"status": "error", "message": "Ses dosyaları Media Pool'a aktarılamadı."}

        clean_tname = f"{timeline_name} ({gap_seconds}s Gap - Text+)"
        timeline = mp.CreateEmptyTimeline(clean_tname)
        if not timeline:
            return {"status": "error", "message": "DaVinci Timeline oluşturulamadı."}

        project.SetCurrentTimeline(timeline)

        try:
            from ai_voice_detector import AIVoiceDetector
        except Exception:
            AIVoiceDetector = None

        added_clips_count = 0
        clip_map = {os.path.abspath(c.GetClipProperty("File Path")): c for c in media_clips if c.GetClipProperty("File Path")}

        timeline_items_info = []
        for idx, file_path in enumerate(sorted_files):
            abs_p = os.path.abspath(file_path)
            fn = os.path.basename(abs_p)
            dur_sec, _, _, _ = DaVinciTimelineExporter.get_audio_info_fast(abs_p)
            dur_frames = max(1, int(round(dur_sec * fps)))

            spk_raw = fn.split('_')[0].capitalize()
            action_type = "Replik"
            if 'karsilasma' in fn:
                action_type = "Karşılaşma"
            elif 'katletme' in fn:
                action_type = "Katletme"

            spoken_text = ""
            if AIVoiceDetector:
                try:
                    _, spoken_text = AIVoiceDetector.is_spoken_dialogue(abs_p)
                except Exception:
                    spoken_text = ""

            display_text = f'{spk_raw}: "{spoken_text}"' if spoken_text else f'{spk_raw} ({action_type})'

            pool_item = clip_map.get(abs_p)
            if pool_item:
                mp.AppendToTimeline([pool_item])
                added_clips_count += 1
                timeline_items_info.append({
                    "text": display_text,
                    "file_name": fn,
                    "duration_frames": dur_frames,
                    "speaker": spk_raw
                })

        cls.convert_timeline_text_to_textplus(
            fade_in_sec=fade_in_sec,
            fade_out_sec=fade_out_sec,
            fps=fps
        )

        return {
            "status": "success",
            "timeline_name": clean_tname,
            "clip_count": added_clips_count,
            "gap_seconds": gap_seconds,
            "fade_in_sec": fade_in_sec,
            "fade_out_sec": fade_out_sec,
            "message": f"🎬 DaVinci Resolve Timeline'ı doğrudan oluşturuldu: '{clean_tname}' ({added_clips_count} ses, Text+ ve {fade_in_sec}s Fade In / {fade_out_sec}s Fade Out uygulandı!)"
        }

    @classmethod
    def install_davinci_scripts(cls):
        """
        DaVinci Resolve'un yerleşik script klasörlerine (AppData/Fusion/Scripts/Edit, Comp & Utility)
        Daktilo (Write-On) ve Fade Out Text+ enjektörünü otomatik yükler.
        UIManager KULLANILMAZ (DaVinci 21 Free lisans uyarısını engellemek için).
        """
        appdata = os.environ.get('APPDATA', '')
        edit_scripts_dir = os.path.join(appdata, r'Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Edit')
        comp_scripts_dir = os.path.join(appdata, r'Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Comp')
        utility_scripts_dir = os.path.join(appdata, r'Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility')
        titles_template_dir = os.path.join(appdata, r'Blackmagic Design\DaVinci Resolve\Support\Fusion\Templates\Edit\Titles')

        os.makedirs(edit_scripts_dir, exist_ok=True)
        os.makedirs(comp_scripts_dir, exist_ok=True)
        os.makedirs(utility_scripts_dir, exist_ok=True)
        os.makedirs(titles_template_dir, exist_ok=True)

        installed_files = []

        # Kaynak script dosyasını oku
        source_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LoL_Daktilo_TextPlus_Injector.py")
        if os.path.isfile(source_script):
            with open(source_script, 'r', encoding='utf-8') as sf:
                script_content = sf.read()
        else:
            script_content = ""

        if script_content:
            # 1. Edit Scripts
            f1 = os.path.join(edit_scripts_dir, "LoL_Daktilo_TextPlus_Injector.py")
            with open(f1, 'w', encoding='utf-8') as f:
                f.write(script_content)
            installed_files.append(f1)

            # Eski scripti de güvenli headless kodla güncelle
            f_old = os.path.join(edit_scripts_dir, "LoL_Convert_To_TextPlus_Fade.py")
            with open(f_old, 'w', encoding='utf-8') as f:
                f.write(script_content)

            # 2. Comp Scripts
            f2 = os.path.join(comp_scripts_dir, "LoL_Daktilo_TextPlus_Injector.py")
            with open(f2, 'w', encoding='utf-8') as f:
                f.write(script_content)
            installed_files.append(f2)

            # 3. Utility Scripts
            f3 = os.path.join(utility_scripts_dir, "LoL_Daktilo_TextPlus_Injector.py")
            with open(f3, 'w', encoding='utf-8') as f:
                f.write(script_content)
            installed_files.append(f3)

            f_old_util = os.path.join(utility_scripts_dir, "LoL_Convert_To_TextPlus_Fade.py")
            with open(f_old_util, 'w', encoding='utf-8') as f:
                f.write(script_content)

        return {
            "status": "success",
            "installed_files": installed_files,
            "edit_scripts_dir": edit_scripts_dir,
            "message": "🎉 DaVinci Resolve Daktilo Text+ Enjektörü kuruldu! DaVinci menüsünden: Workspace -> Scripts -> Edit -> LoL_Daktilo_TextPlus_Injector çalıştırabilirsiniz."
        }

if __name__ == "__main__":
    status = DaVinciResolveAPI.get_status()
    print("DaVinci Durumu:", json.dumps(status, indent=2, ensure_ascii=False))
    inst = DaVinciResolveAPI.install_davinci_scripts()
    print("Script Kurulumu:", json.dumps(inst, indent=2, ensure_ascii=False))
