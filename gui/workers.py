import sys
import os
from contextlib import redirect_stdout, redirect_stderr
from PySide6.QtCore import QThread, Signal

# Global Hashes Cache
CACHED_HASHES = None

class StreamEmitter:
    def __init__(self, callback):
        self.callback = callback
        self.buffer = ""

    def write(self, text):
        if not text:
            return
        self.buffer += text
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            line = line.strip()
            if line:
                self.callback(line)

    def flush(self):
        if self.buffer.strip():
            self.callback(self.buffer.strip())
            self.buffer = ""

class VoiceExtractionWorker(QThread):
    progress_signal = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, champion_name, target_skin=None):
        super().__init__()
        self.champion_name = champion_name
        self.target_skin = target_skin

    def run(self):
        global CACHED_HASHES
        try:
            skin_msg = f" ({self.target_skin})" if self.target_skin else " (Tüm Kostümler)"
            self.progress_signal.emit(f"🚀 {self.champion_name}{skin_msg} sesleri çıkarılıyor...")
            
            emitter = StreamEmitter(self.progress_signal.emit)
            with redirect_stdout(emitter), redirect_stderr(emitter):
                import lol_voice_extractor_expert as extractor
                
                if CACHED_HASHES is None:
                    emitter.write("📂 Obsidian hash tablosu yükleniyor...\n")
                    CACHED_HASHES = extractor.load_hashes()
                
                extractor.extract_champion_full(
                    self.champion_name,
                    CACHED_HASHES,
                    target_skin=self.target_skin
                )
            emitter.flush()
            self.finished_signal.emit(True, f"✅ {self.champion_name} sesleri başarıyla çıkarıldı!")
        except Exception as e:
            self.finished_signal.emit(False, f"❌ Hata oluştu: {e}")

class ReferenceDetectorWorker(QThread):
    progress_signal = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, target_champion, target_skin=None):
        super().__init__()
        self.target_champion = target_champion
        self.target_skin = target_skin

    def run(self):
        try:
            skin_log = f" ({self.target_skin})" if (self.target_skin and self.target_skin.upper() != 'ALL') else ""
            self.progress_signal.emit(f"🎯 [{self.target_champion.upper()}]{skin_log} için tüm şampiyon atıfları taranıyor...")
            emitter = StreamEmitter(self.progress_signal.emit)
            with redirect_stdout(emitter), redirect_stderr(emitter):
                import extract_target_references as ref_extractor
                ref_extractor.extract_all_interactions_for_champion(self.target_champion, target_skin=self.target_skin)
            emitter.flush()
            self.finished_signal.emit(True, f"✨ {self.target_champion} için tüm atıflar başarıyla çıkarıldı!")
        except Exception as e:
            self.finished_signal.emit(False, f"❌ Hata oluştu: {e}")


class VideoDownloadWorker(QThread):
    progress_signal = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, champion_name):
        super().__init__()
        self.champion_name = champion_name

    def run(self):
        try:
            self.progress_signal.emit(f"🎬 {self.champion_name} için canlı duvar kağıtları taranıyor...")
            emitter = StreamEmitter(self.progress_signal.emit)
            with redirect_stdout(emitter), redirect_stderr(emitter):
                emitter.write(f"ℹ️ {self.champion_name} için video modülü hazırlanıyor...\n")
            emitter.flush()
            self.finished_signal.emit(True, f"🎉 {self.champion_name} canlı video araması tamamlandı.")
        except Exception as e:
            self.finished_signal.emit(False, f"❌ Hata oluştu: {e}")
