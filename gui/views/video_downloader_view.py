import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QProgressBar, QTextEdit, QFrame, QSplitter
)
from PySide6.QtCore import Qt
from gui.theme import HEXTECH_PALETTE
from metadata_manager import MetadataManager
import lol_voice_extractor_expert as voice_extractor

LOL_CHAMPIONS_PATH = voice_extractor.LOL_CHAMPIONS_PATH
CHAMPIONS_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Champions")

class VideoDownloaderView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.all_champions = []
        self.setup_ui()
        self.load_champions_list()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # 1. Top Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        title_box = QVBoxLayout()
        title_row = QHBoxLayout()
        icon_lbl = QLabel("🎬")
        icon_lbl.setStyleSheet("font-size: 22px;")
        title = QLabel("Canlı Duvar Kağıtları & 4K Video Hub")
        title.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {HEXTECH_PALETTE['gold_primary']}; letter-spacing: 0.5px;")
        title_row.addWidget(icon_lbl)
        title_row.addWidget(title)
        title_row.addStretch(1)

        subtitle = QLabel("MotionBGS ve Resmi YouTube Giriş Ekranlarından 4K hareketli canlı splash videolarını tek tıkla indirir.")
        subtitle.setStyleSheet(f"color: {HEXTECH_PALETTE['text_secondary']}; font-size: 12.5px;")
        
        title_box.addLayout(title_row)
        title_box.addWidget(subtitle)
        top_bar.addLayout(title_box, stretch=1)

        self.download_btn = QPushButton("📥 4K Canlı Videoları İndir")
        self.download_btn.setObjectName("PrimaryGoldButton")
        self.download_btn.setMinimumHeight(40)
        self.download_btn.clicked.connect(self.start_download)
        top_bar.addWidget(self.download_btn)

        main_layout.addLayout(top_bar)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Splitter Layout (3 Columns)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(6)

        # Panel 1: Champion List
        champ_panel = QFrame()
        champ_panel.setObjectName("GlassCard")
        champ_layout = QVBoxLayout(champ_panel)
        champ_layout.setContentsMargins(10, 10, 10, 10)
        champ_layout.setSpacing(10)

        champ_lbl = QLabel("🎮 Şampiyon Seçin")
        champ_lbl.setStyleSheet(f"font-weight: 700; color: {HEXTECH_PALETTE['gold_bright']}; font-size: 13px;")
        champ_layout.addWidget(champ_lbl)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Şampiyon ara...")
        self.search_input.textChanged.connect(self.filter_champions)
        champ_layout.addWidget(self.search_input)

        self.champ_list = QListWidget()
        self.champ_list.itemClicked.connect(self.on_champion_clicked)
        champ_layout.addWidget(self.champ_list)

        splitter.addWidget(champ_panel)

        # Panel 2: Downloaded Videos List
        video_panel = QFrame()
        video_panel.setObjectName("GlassCard")
        video_layout = QVBoxLayout(video_panel)
        video_layout.setContentsMargins(10, 10, 10, 10)
        video_layout.setSpacing(10)

        v_top = QHBoxLayout()
        video_lbl = QLabel("🎥 İndirilen Canlı Videolar (.mp4)")
        video_lbl.setStyleSheet(f"font-weight: 700; color: {HEXTECH_PALETTE['gold_bright']}; font-size: 13px;")
        v_top.addWidget(video_lbl, stretch=1)

        self.open_folder_btn = QPushButton("📁 Klasörü Aç")
        self.open_folder_btn.setObjectName("CyanActionButton")
        self.open_folder_btn.setFixedHeight(28)
        self.open_folder_btn.clicked.connect(self.open_current_video_folder)
        v_top.addWidget(self.open_folder_btn)
        video_layout.addLayout(v_top)

        self.video_list = QListWidget()
        video_layout.addWidget(self.video_list)

        splitter.addWidget(video_panel)

        # Panel 3: Live Logs
        log_panel = QFrame()
        log_panel.setObjectName("GlassCard")
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(10, 10, 10, 10)
        log_layout.setSpacing(10)

        log_lbl = QLabel("📋 İndirme Günlüğü")
        log_lbl.setStyleSheet(f"font-weight: 700; color: {HEXTECH_PALETTE['text_secondary']}; font-size: 12px;")
        log_layout.addWidget(log_lbl)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("ConsoleView")
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text, stretch=1)

        splitter.addWidget(log_panel)
        splitter.setSizes([260, 420, 380])

        main_layout.addWidget(splitter)

    def load_champions_list(self):
        self.champ_list.clear()
        self.all_champions = []
        seen = set()
        if os.path.exists(LOL_CHAMPIONS_PATH):
            for f in sorted(os.listdir(LOL_CHAMPIONS_PATH)):
                if f.endswith('.wad.client'):
                    base = f.replace('.wad.client', '')
                    ch = base.split('.')[0]
                    if ch and ch not in seen:
                        seen.add(ch)
                        self.all_champions.append(ch)
                        item = QListWidgetItem(f"🎬  {ch}")
                        item.setData(Qt.UserRole, ch)
                        self.champ_list.addItem(item)
        if not self.all_champions:
            meta_mgr = MetadataManager()
            for s in meta_mgr.skins_raw_db:
                c_name = s.get('champion_name') or s.get('champion_alias')
                if c_name and c_name not in seen:
                    seen.add(c_name)
                    self.all_champions.append(c_name)
                    item = QListWidgetItem(f"🎬  {c_name}")
                    item.setData(Qt.UserRole, c_name)
                    self.champ_list.addItem(item)
            self.all_champions.sort()

        if self.champ_list.count() > 0:
            self.champ_list.setCurrentRow(0)
            self.on_champion_clicked(self.champ_list.item(0))

    def filter_champions(self, text):
        query = text.lower().strip()
        for i in range(self.champ_list.count()):
            item = self.champ_list.item(i)
            ch = item.data(Qt.UserRole).lower()
            item.setHidden(query not in ch)

    def on_champion_clicked(self, item):
        ch = item.data(Qt.UserRole)
        self.refresh_video_list(ch)

    def refresh_video_list(self, champion_name):
        self.video_list.clear()
        video_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, champion_name, "Canlı_Duvar_Kagitlari")
        if not os.path.exists(video_dir):
            item = QListWidgetItem(f"⚠️ {champion_name} için henüz video indirilmedi.")
            item.setForeground(Qt.gray)
            self.video_list.addItem(item)
            return

        found = 0
        for f in sorted(os.listdir(video_dir)):
            if f.endswith('.mp4'):
                found += 1
                sz_mb = os.path.getsize(os.path.join(video_dir, f)) / (1024 * 1024)
                item = QListWidgetItem(f"🎬 {f}  ({sz_mb:.1f} MB)")
                item.setForeground(Qt.white)
                self.video_list.addItem(item)

        if found == 0:
            item = QListWidgetItem(f"⚠️ {champion_name} video klasörü boş.")
            item.setForeground(Qt.gray)
            self.video_list.addItem(item)

    def open_current_video_folder(self):
        curr_item = self.champ_list.currentItem()
        if not curr_item:
            return
        ch = curr_item.data(Qt.UserRole)
        video_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, ch, "Canlı_Duvar_Kagitlari")
        os.makedirs(video_dir, exist_ok=True)
        os.startfile(video_dir)

    def start_download(self):
        curr_item = self.champ_list.currentItem()
        if not curr_item:
            return
        ch = curr_item.data(Qt.UserRole)

        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.log_text.clear()
        self.log_text.append(f"🎬 {ch} için 4K canlı duvar kağıtları taranıyor...\n")

        self.worker = VideoDownloadWorker(ch)
        self.worker.progress_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.on_download_finished)
        self.worker.start()

    def append_log(self, text):
        self.log_text.append(text)
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_download_finished(self, success, message):
        self.download_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.log_text.append(f"\n{message}\n")
        
        curr_item = self.champ_list.currentItem()
        if curr_item:
            ch = curr_item.data(Qt.UserRole)
            self.refresh_video_list(ch)
