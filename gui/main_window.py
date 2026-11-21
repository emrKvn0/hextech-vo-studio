import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QStackedWidget, QButtonGroup, QFrame
)
from PySide6.QtCore import Qt

from gui.theme import HEXTECH_PALETTE, MAIN_STYLE_QSS
from gui.views.voice_extractor_view import VoiceExtractorView
from gui.views.reference_detector_view import ReferenceDetectorView
from gui.views.video_downloader_view import VideoDownloaderView

OUTPUT_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Champions")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("League of Legends Ses & Video Otomasyon Stüdyosu")
        self.resize(1320, 840)
        self.setMinimumSize(1100, 700)

        self.setStyleSheet(MAIN_STYLE_QSS)
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # -------------------------------------------------------------
        # 1. SOL SIDEBAR (Hextech Glass Navigation)
        # -------------------------------------------------------------
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 16)
        sidebar_layout.setSpacing(4)

        # App Logo & Header Frame
        header_frame = QFrame()
        header_frame.setObjectName("SidebarHeader")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        logo_badge = QLabel("⚡ HEXTECH STUDIO")
        logo_badge.setObjectName("SidebarSubtitle")

        app_title = QLabel("LoL Ses & Medya\nOtomasyonu")
        app_title.setObjectName("SidebarTitle")

        header_layout.addWidget(logo_badge)
        header_layout.addWidget(app_title)
        sidebar_layout.addWidget(header_frame)

        # Nav Buttons Group
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.btn_voices = QPushButton("🎙️  Ses & Kostüm Çıkarıcı")
        self.btn_voices.setObjectName("NavButton")
        self.btn_voices.setCheckable(True)
        self.btn_voices.setChecked(True)
        self.nav_group.addButton(self.btn_voices, 0)
        sidebar_layout.addWidget(self.btn_voices)

        self.btn_references = QPushButton("🎯  Tersine Atıf Dedektörü")
        self.btn_references.setObjectName("NavButton")
        self.btn_references.setCheckable(True)
        self.nav_group.addButton(self.btn_references, 1)
        sidebar_layout.addWidget(self.btn_references)

        self.btn_videos = QPushButton("🎬  4K Canlı Duvar Kağıtları")
        self.btn_videos.setObjectName("NavButton")
        self.btn_videos.setCheckable(True)
        self.nav_group.addButton(self.btn_videos, 2)
        sidebar_layout.addWidget(self.btn_videos)

        sidebar_layout.addStretch(1)

        # Bottom Actions Frame
        bottom_box = QVBoxLayout()
        bottom_box.setContentsMargins(14, 0, 14, 0)
        bottom_box.setSpacing(8)

        open_folder_btn = QPushButton("📂 Çıktı Klasörünü Aç")
        open_folder_btn.setObjectName("CyanActionButton")
        open_folder_btn.clicked.connect(self.open_champions_dir)
        bottom_box.addWidget(open_folder_btn)

        ver_lbl = QLabel("Wwise HIRC v2024.1 • 100% Deterministic")
        ver_lbl.setStyleSheet(f"color: {HEXTECH_PALETTE['text_muted']}; font-size: 10px; text-align: center;")
        ver_lbl.setAlignment(Qt.AlignCenter)
        bottom_box.addWidget(ver_lbl)

        sidebar_layout.addLayout(bottom_box)
        root_layout.addWidget(sidebar)

        # -------------------------------------------------------------
        # 2. SAĞ İÇERİK ALANI (QStackedWidget)
        # -------------------------------------------------------------
        self.stack = QStackedWidget()

        self.view_voices = VoiceExtractorView()
        self.view_references = ReferenceDetectorView()
        self.view_videos = VideoDownloaderView()

        self.stack.addWidget(self.view_voices)
        self.stack.addWidget(self.view_references)
        self.stack.addWidget(self.view_videos)

        root_layout.addWidget(self.stack, stretch=1)

        # Connect Navigation
        self.nav_group.idClicked.connect(self.switch_tab)

    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)

    def open_champions_dir(self):
        os.makedirs(OUTPUT_BASE, exist_ok=True)
        os.startfile(OUTPUT_BASE)
