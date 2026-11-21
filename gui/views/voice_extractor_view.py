import os
import json
import re
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QSplitter,
    QProgressBar, QTextEdit, QFrame, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from gui.theme import HEXTECH_PALETTE
from gui.workers import VoiceExtractionWorker
from gui.widgets.audio_player import AudioPlayerWidget
from metadata_manager import MetadataManager
import lol_voice_extractor_expert as voice_extractor

LOL_CHAMPIONS_PATH = voice_extractor.LOL_CHAMPIONS_PATH
CHAMPIONS_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Champions")

class VoiceExtractorView(QWidget):
    audio_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.all_champions = []
        self.meta_mgr = MetadataManager()
        self.setup_ui()
        self.load_champions_list()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # -------------------------------------------------------------
        # 1. TOP HEADER & ACTION TOOLBAR
        # -------------------------------------------------------------
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        title_box = QVBoxLayout()
        title_row = QHBoxLayout()
        
        icon_lbl = QLabel("🎙️")
        icon_lbl.setStyleSheet("font-size: 22px;")
        title = QLabel("Şampiyon Ses & Kostüm Çıkarıcı")
        title.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {HEXTECH_PALETTE['gold_primary']}; letter-spacing: 0.5px;")
        
        title_row.addWidget(icon_lbl)
        title_row.addWidget(title)
        title_row.addStretch(1)
        
        subtitle = QLabel("Riot Wwise HIRC Event grafiğiyle sesleri sıfır hata ve Türkçe kategorileriyle anında ayıklayın.")
        subtitle.setStyleSheet(f"color: {HEXTECH_PALETTE['text_secondary']}; font-size: 12.5px;")
        
        title_box.addLayout(title_row)
        title_box.addWidget(subtitle)
        top_bar.addLayout(title_box, stretch=1)

        # Action Buttons
        self.base_hub_btn = QPushButton("📦 A-Z Tüm Varsayılanlar Hub'ı")
        self.base_hub_btn.setObjectName("GhostButton")
        self.base_hub_btn.setMinimumHeight(40)
        self.base_hub_btn.clicked.connect(self.open_base_hub_actions)
        top_bar.addWidget(self.base_hub_btn)

        self.extract_selected_btn = QPushButton("⚡ Seçili Kostümü Çıkar")
        self.extract_selected_btn.setObjectName("PrimaryGoldButton")
        self.extract_selected_btn.setMinimumHeight(40)
        self.extract_selected_btn.clicked.connect(self.start_extraction_selected)
        top_bar.addWidget(self.extract_selected_btn)

        self.extract_all_btn = QPushButton("🔥 Tüm Kostümleri Çıkar")
        self.extract_all_btn.setObjectName("CyanActionButton")
        self.extract_all_btn.setMinimumHeight(40)
        self.extract_all_btn.clicked.connect(self.start_extraction_all)
        top_bar.addWidget(self.extract_all_btn)

        main_layout.addLayout(top_bar)


        # Indeterminate Progress Bar (Animated)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # -------------------------------------------------------------
        # 2. MAIN 3-COLUMN SPLITTER LAYOUT (Tailwind Style)
        # -------------------------------------------------------------
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(6)

        # -------------------------------------------------------------
        # COLUMN 1: CHAMPION & SKIN SELECTOR
        # -------------------------------------------------------------
        col1_panel = QFrame()
        col1_panel.setObjectName("GlassCard")
        col1_layout = QVBoxLayout(col1_panel)
        col1_layout.setContentsMargins(10, 10, 10, 10)
        col1_layout.setSpacing(10)

        # Champ Header
        c1_head = QLabel("🎮 1. Şampiyon Seçin")
        c1_head.setStyleSheet(f"font-weight: 700; color: {HEXTECH_PALETTE['gold_bright']}; font-size: 13px;")
        col1_layout.addWidget(c1_head)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Şampiyon ara (örn. Aatrox, Ahri)...")
        self.search_input.textChanged.connect(self.filter_champions)
        col1_layout.addWidget(self.search_input)

        self.champ_list = QListWidget()
        self.champ_list.itemClicked.connect(self.on_champion_clicked)
        col1_layout.addWidget(self.champ_list, stretch=3)

        # Skin Header
        c2_head = QLabel("🎭 2. Kostüm Seçin")
        c2_head.setStyleSheet(f"font-weight: 700; color: {HEXTECH_PALETTE['gold_bright']}; font-size: 13px; margin-top: 4px;")
        col1_layout.addWidget(c2_head)

        self.skins_list = QListWidget()
        self.skins_list.itemClicked.connect(self.on_skin_clicked)
        col1_layout.addWidget(self.skins_list, stretch=2)

        splitter.addWidget(col1_panel)

        # -------------------------------------------------------------
        # COLUMN 2: EXTRACTED VOICE EXPLORER (TREE)
        # -------------------------------------------------------------
        col2_panel = QFrame()
        col2_panel.setObjectName("GlassCard")
        col2_layout = QVBoxLayout(col2_panel)
        col2_layout.setContentsMargins(10, 10, 10, 10)
        col2_layout.setSpacing(10)

        col2_head_row = QHBoxLayout()
        col2_head = QLabel("📂 Çıkarılan Sesler & Kategoriler")
        col2_head.setStyleSheet(f"font-weight: 700; color: {HEXTECH_PALETTE['gold_bright']}; font-size: 13px;")
        
        self.refresh_btn = QPushButton("🔄 Yenile")
        self.refresh_btn.setObjectName("GhostButton")
        self.refresh_btn.setFixedHeight(26)
        self.refresh_btn.clicked.connect(self.refresh_current_champ_tree)
        
        col2_head_row.addWidget(col2_head)
        col2_head_row.addStretch(1)
        col2_head_row.addWidget(self.refresh_btn)
        col2_layout.addLayout(col2_head_row)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Ses Dosyası / Kategori"])
        self.tree_widget.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)
        self.tree_widget.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        col2_layout.addWidget(self.tree_widget)

        splitter.addWidget(col2_panel)

        # -------------------------------------------------------------
        # COLUMN 3: AUDIO HUB & LIVE TERMINAL LOGS
        # -------------------------------------------------------------
        col3_panel = QFrame()
        col3_panel.setObjectName("GlassCard")
        col3_layout = QVBoxLayout(col3_panel)
        col3_layout.setContentsMargins(10, 10, 10, 10)
        col3_layout.setSpacing(10)

        # Audio Player Widget
        self.player_widget = AudioPlayerWidget()
        col3_layout.addWidget(self.player_widget)

        # Terminal Log Header
        log_head = QLabel("📋 Canlı İşlem Konsolu")
        log_head.setStyleSheet(f"font-weight: 700; color: {HEXTECH_PALETTE['text_secondary']}; font-size: 12px; margin-top: 4px;")
        col3_layout.addWidget(log_head)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("ConsoleView")
        self.log_text.setReadOnly(True)
        col3_layout.addWidget(self.log_text, stretch=1)

        splitter.addWidget(col3_panel)

        # Splitter initial width distribution [Left: 300px, Mid: 380px, Right: 440px]
        splitter.setSizes([290, 360, 430])

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
                        item = QListWidgetItem(f"🛡️  {ch}")
                        item.setData(Qt.UserRole, ch)
                        self.champ_list.addItem(item)
        if not self.all_champions and self.meta_mgr.skins_raw_db:
            for s in self.meta_mgr.skins_raw_db:
                c_name = s.get('champion_name') or s.get('champion_alias')
                if c_name and c_name not in seen:
                    seen.add(c_name)
                    self.all_champions.append(c_name)
                    item = QListWidgetItem(f"🛡️  {c_name}")
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
        self.populate_skins_for_champion(ch)
        self.refresh_extracted_tree(ch)

    def populate_skins_for_champion(self, champion_name):
        self.skins_list.clear()
        
        # 1. "Tüm Kostümler" seçeneği
        all_item = QListWidgetItem("🌟  [TÜM KOSTÜMLERİ ÇIKAR]")
        all_item.setData(Qt.UserRole, "ALL")
        all_item.setForeground(Qt.cyan)
        self.skins_list.addItem(all_item)

        # 2. Şampiyonun veritabanındaki tüm kostümlerini anında getir
        c_clean = champion_name.lower().replace("'", "").replace(" ", "").replace("_", "")
        skins_found = self.meta_mgr.skins_by_champ.get(c_clean, {})

        if not skins_found:
            for s in self.meta_mgr.skins_raw_db:
                c_alias = s.get('champion_alias', '').lower()
                c_name = s.get('champion_name', '').lower()
                if c_alias == c_clean or c_name == c_clean:
                    s_num = s.get('skin_num', 0)
                    s_name = s.get('name_tr', '')
                    if s_name:
                        skins_found[s_num] = s_name.replace(" ", "_")

        for s_num, s_name in sorted(skins_found.items(), key=lambda x: x[0]):
            label = "🛡️  Varsayılan Hali" if s_num == 0 else f"🎭  {s_name}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, s_name if s_num != 0 else f"Varsayilan_{champion_name}")
            self.skins_list.addItem(item)

        self.skins_list.setCurrentRow(0)

    def on_skin_clicked(self, item):
        pass

    def refresh_current_champ_tree(self):
        curr_item = self.champ_list.currentItem()
        if curr_item:
            ch = curr_item.data(Qt.UserRole)
            self.refresh_extracted_tree(ch)

    def refresh_extracted_tree(self, champion_name):
        self.tree_widget.clear()
        target_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, champion_name)
        if not os.path.exists(target_dir):
            root_item = QTreeWidgetItem([f"⚠️ {champion_name} henüz çıkarılmadı."])
            root_item.setForeground(0, Qt.gray)
            self.tree_widget.addTopLevelItem(root_item)
            return

        def populate_tree(directory, parent_item):
            try:
                for entry in sorted(os.listdir(directory)):
                    full_path = os.path.join(directory, entry)
                    if os.path.isdir(full_path):
                        # Klasör altındaki ses sayısını hesapla
                        wav_count = sum(1 for f in os.listdir(full_path) if f.endswith('.wav'))
                        count_tag = f" ({wav_count} ses)" if wav_count > 0 else ""
                        dir_item = QTreeWidgetItem([f"📁 {entry}{count_tag}"])
                        dir_item.setForeground(0, Qt.yellow)
                        parent_item.addChild(dir_item)
                        populate_tree(full_path, dir_item)
                    elif entry.endswith('.wav'):
                        file_item = QTreeWidgetItem([f"🔊 {entry}"])
                        file_item.setData(0, Qt.UserRole, full_path)
                        file_item.setForeground(0, Qt.white)
                        parent_item.addChild(file_item)
            except Exception:
                pass

        total_skins_count = 0
        for skin_dir in sorted(os.listdir(target_dir)):
            skin_path = os.path.join(target_dir, skin_dir)
            if os.path.isdir(skin_path) and not skin_dir.startswith('_'):
                total_skins_count += 1
                skin_item = QTreeWidgetItem([f"🎭 {skin_dir}"])
                skin_item.setForeground(0, Qt.cyan)
                self.tree_widget.addTopLevelItem(skin_item)
                populate_tree(skin_path, skin_item)
                skin_item.setExpanded(True)

        if total_skins_count == 0:
            root_item = QTreeWidgetItem([f"⚠️ {champion_name} klasörü boş."])
            root_item.setForeground(0, Qt.gray)
            self.tree_widget.addTopLevelItem(root_item)

    def on_tree_item_clicked(self, item, col):
        file_path = item.data(0, Qt.UserRole)
        if file_path and os.path.exists(file_path):
            self.player_widget.load_audio(file_path)

    def on_tree_item_double_clicked(self, item, col):
        file_path = item.data(0, Qt.UserRole)
        if file_path and os.path.exists(file_path):
            self.player_widget.load_audio(file_path)
            self.player_widget.play()

    def start_extraction_selected(self):
        curr_champ = self.champ_list.currentItem()
        curr_skin = self.skins_list.currentItem()
        if not curr_champ or not curr_skin:
            return
        
        ch = curr_champ.data(Qt.UserRole)
        skin_tag = curr_skin.data(Qt.UserRole)
        target_skin = None if skin_tag == "ALL" else skin_tag

        self.execute_worker(ch, target_skin)

    def start_extraction_all(self):
        curr_champ = self.champ_list.currentItem()
        if not curr_champ:
            return
        ch = curr_champ.data(Qt.UserRole)
        self.execute_worker(ch, None)

    def execute_worker(self, champion_name, target_skin):
        self.extract_selected_btn.setEnabled(False)
        self.extract_all_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.log_text.clear()

        skin_label = f"[{target_skin}]" if target_skin else "[TÜM KOSTÜMLER]"
        self.log_text.append(f"🚀 {champion_name} {skin_label} için ses çıkarma başlatıldı...\n")

        self.worker = VoiceExtractionWorker(champion_name, target_skin=target_skin)
        self.worker.progress_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.on_extraction_finished)
        self.worker.start()

    def append_log(self, text):
        self.log_text.append(text)
        # Scroll to bottom
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_extraction_finished(self, success, message):
        self.extract_selected_btn.setEnabled(True)
        self.extract_all_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.log_text.append(f"\n{message}\n")
        
        curr_item = self.champ_list.currentItem()
        if curr_item:
            ch = curr_item.data(Qt.UserRole)
            self.refresh_extracted_tree(ch)

    def open_base_hub_actions(self):
        try:
            import scripts.base_champions_hub as hub
            hub_dir = hub.HUB_PATH
            os.makedirs(hub_dir, exist_ok=True)
            self.append_log("📦 A-Z Hub senkronize ediliyor ve Master DaVinci XML üretiliyor...")
            sync_res = hub.sync_all_base_champions_to_hub()
            xml_res = hub.generate_base_hub_master_davinci_xml(gap_seconds=0.2)
            self.append_log(f"✨ Senkronizasyon Tamamlandı: {sync_res['synced_champions']} şampiyon, {sync_res['total_files']} replik!")
            if xml_res.get('status') == 'success':
                self.append_log(f"🎬 Master DaVinci XML Hazır: {xml_res['filename']} ({xml_res['total_audio_count']} ses, {xml_res['total_duration_formatted']})")
            os.startfile(hub_dir)
        except Exception as e:
            self.append_log(f"❌ Hub Hatası: {e}")

