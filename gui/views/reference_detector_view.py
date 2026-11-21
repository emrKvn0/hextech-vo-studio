import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QSplitter,
    QProgressBar, QTextEdit, QFrame, QHeaderView, QComboBox, QAbstractItemView
)
from PySide6.QtCore import Qt
from gui.theme import HEXTECH_PALETTE
from gui.workers import ReferenceDetectorWorker
import davinci_timeline_exporter
from metadata_manager import MetadataManager
import lol_voice_extractor_expert as voice_extractor

LOL_CHAMPIONS_PATH = voice_extractor.LOL_CHAMPIONS_PATH
CHAMPIONS_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Champions")

class ReferenceDetectorView(QWidget):
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
        icon_lbl = QLabel("🎯")
        icon_lbl.setStyleSheet("font-size: 22px;")
        title = QLabel("Hedef Şampiyon & Kostüm Tersine Atıf Dedektörü")
        title.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {HEXTECH_PALETTE['gold_primary']}; letter-spacing: 0.5px;")
        title_row.addWidget(icon_lbl)
        title_row.addWidget(title)
        title_row.addStretch(1)

        subtitle = QLabel("Oyundaki tüm şampiyonları tarayarak seçilen hedef ve konuşan kostümlerine göre atıfları ayıklar.")
        subtitle.setStyleSheet(f"color: {HEXTECH_PALETTE['text_secondary']}; font-size: 12.5px;")
        
        title_box.addLayout(title_row)
        title_box.addWidget(subtitle)
        top_bar.addLayout(title_box, stretch=1)

        self.scan_btn = QPushButton("🚀 Tüm Atıfları Tara & Çıkar")
        self.scan_btn.setObjectName("PrimaryGoldButton")
        self.scan_btn.setMinimumHeight(40)
        self.scan_btn.clicked.connect(self.start_scan)
        top_bar.addWidget(self.scan_btn)

        main_layout.addLayout(top_bar)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Splitter Layout (3 Columns)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(6)

        # Panel 1: Target Champion Selection & Dual Filters
        target_panel = QFrame()
        target_panel.setObjectName("GlassCard")
        target_layout = QVBoxLayout(target_panel)
        target_layout.setContentsMargins(10, 10, 10, 10)
        target_layout.setSpacing(8)

        t_lbl = QLabel("🎯 1. Hedef Şampiyon")
        t_lbl.setStyleSheet(f"font-weight: 700; color: {HEXTECH_PALETTE['gold_bright']}; font-size: 13px;")
        target_layout.addWidget(t_lbl)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Hedef ara (Gangplank, Garen)...")
        self.search_input.textChanged.connect(self.filter_champions)
        target_layout.addWidget(self.search_input)

        self.champ_list = QListWidget()
        self.champ_list.itemClicked.connect(self.on_target_clicked)
        target_layout.addWidget(self.champ_list, stretch=1)

        # Target Skin Selector
        s_lbl = QLabel("🎭 2. Hedef Kostüm Filtresi")
        s_lbl.setStyleSheet(f"font-weight: 700; color: {HEXTECH_PALETTE['gold_bright']}; font-size: 12px; margin-top: 4px;")
        target_layout.addWidget(s_lbl)

        self.skin_combo = QComboBox()
        self.skin_combo.currentIndexChanged.connect(self.on_skin_changed)
        target_layout.addWidget(self.skin_combo)

        # Speaker Type Filter
        spk_lbl = QLabel("🎙️ 3. Konuşan Şampiyon Türü")
        spk_lbl.setStyleSheet(f"font-weight: 700; color: {HEXTECH_PALETTE['cyan_neon']}; font-size: 12px; margin-top: 4px;")
        target_layout.addWidget(spk_lbl)

        self.speaker_type_combo = QComboBox()
        self.speaker_type_combo.addItem("🌟 Tümü (Varsayılan + Kostümler)", "all")
        self.speaker_type_combo.addItem("🛡️ Yalnızca Varsayılan Şampiyonlar (Kanon)", "base_only")
        self.speaker_type_combo.addItem("🎭 Yalnızca Kostümlü Şampiyonlar (AU)", "skins_only")
        self.speaker_type_combo.currentIndexChanged.connect(self.on_speaker_type_changed)
        target_layout.addWidget(self.speaker_type_combo)

        splitter.addWidget(target_panel)

        # Panel 2: Detected References Tree & Multi-Select Action Bar
        ref_panel = QFrame()
        ref_panel.setObjectName("GlassCard")
        ref_layout = QVBoxLayout(ref_panel)
        ref_layout.setContentsMargins(10, 10, 10, 10)
        ref_layout.setSpacing(8)

        ref_head_row = QHBoxLayout()
        ref_lbl = QLabel("📁 Tespit Edilen Atıf Replikleri")
        ref_lbl.setStyleSheet(f"font-weight: 700; color: {HEXTECH_PALETTE['gold_bright']}; font-size: 13px;")
        
        self.refresh_btn = QPushButton("🔄 Yenile")
        self.refresh_btn.setObjectName("GhostButton")
        self.refresh_btn.setFixedHeight(26)
        self.refresh_btn.clicked.connect(self.refresh_current_target_tree)

        ref_head_row.addWidget(ref_lbl)
        ref_head_row.addStretch(1)
        ref_head_row.addWidget(self.refresh_btn)
        ref_layout.addLayout(ref_head_row)

        # Multi-Select Toolbar
        multi_tool_row = QHBoxLayout()
        multi_tool_row.setSpacing(6)

        self.sel_count_lbl = QLabel("0 ses seçildi")
        self.sel_count_lbl.setStyleSheet(f"color: {HEXTECH_PALETTE['cyan_neon']}; font-weight: 700; font-size: 11px;")
        multi_tool_row.addWidget(self.sel_count_lbl)
        multi_tool_row.addStretch(1)

        self.btn_select_all = QPushButton("Tümünü Seç")
        self.btn_select_all.setObjectName("GhostButton")
        self.btn_select_all.setFixedHeight(24)
        self.btn_select_all.clicked.connect(self.select_all_tree_items)
        multi_tool_row.addWidget(self.btn_select_all)

        self.btn_clear_sel = QPushButton("Temizle")
        self.btn_clear_sel.setObjectName("GhostButton")
        self.btn_clear_sel.setFixedHeight(24)
        self.btn_clear_sel.clicked.connect(self.clear_tree_selection)
        multi_tool_row.addWidget(self.btn_clear_sel)

        self.davinci_btn = QPushButton("🎬 DaVinci Timeline'a Aktar")
        self.davinci_btn.setObjectName("PrimaryGoldButton")
        self.davinci_btn.setFixedHeight(26)
        self.davinci_btn.clicked.connect(self.export_selected_to_davinci)
        multi_tool_row.addWidget(self.davinci_btn)

        ref_layout.addLayout(multi_tool_row)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Konuşan Şampiyon / Kostüm / Replik"])
        self.tree_widget.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tree_widget.setSelectionMode(QAbstractItemView.ExtendedSelection) # Native Shift+Click and Ctrl+Click
        self.tree_widget.itemSelectionChanged.connect(self.on_tree_selection_changed)
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)
        self.tree_widget.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        ref_layout.addWidget(self.tree_widget, stretch=1)

        splitter.addWidget(ref_panel)

        # Panel 3: Audio Player & Live Log
        right_panel = QFrame()
        right_panel.setObjectName("GlassCard")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)

        self.player_widget = AudioPlayerWidget()
        right_layout.addWidget(self.player_widget)

        log_lbl = QLabel("📋 Tarama & İşlem Günlüğü")
        log_lbl.setStyleSheet(f"font-weight: 700; color: {HEXTECH_PALETTE['text_secondary']}; font-size: 12px;")
        right_layout.addWidget(log_lbl)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("ConsoleView")
        self.log_text.setReadOnly(True)
        right_layout.addWidget(self.log_text, stretch=1)

        splitter.addWidget(right_panel)
        splitter.setSizes([260, 440, 380])

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
                        item = QListWidgetItem(f"🎯  {ch}")
                        item.setData(Qt.UserRole, ch)
                        self.champ_list.addItem(item)
        if not self.all_champions:
            meta_mgr = MetadataManager()
            for s in meta_mgr.skins_raw_db:
                c_name = s.get('champion_name') or s.get('champion_alias')
                if c_name and c_name not in seen:
                    seen.add(c_name)
                    self.all_champions.append(c_name)
                    item = QListWidgetItem(f"🎯  {c_name}")
                    item.setData(Qt.UserRole, c_name)
                    self.champ_list.addItem(item)
            self.all_champions.sort()

        if self.champ_list.count() > 0:
            self.champ_list.setCurrentRow(0)
            self.on_target_clicked(self.champ_list.item(0))

    def filter_champions(self, text):
        query = text.lower().strip()
        for i in range(self.champ_list.count()):
            item = self.champ_list.item(i)
            ch = item.data(Qt.UserRole).lower()
            item.setHidden(query not in ch)

    def on_target_clicked(self, item):
        ch = item.data(Qt.UserRole)
        self.load_target_skins(ch)
        self.refresh_references_tree(ch)

    def load_target_skins(self, champion_name):
        self.skin_combo.blockSignals(True)
        self.skin_combo.clear()
        self.skin_combo.addItem("🌟 Tüm Kostümler (Full Paket)", "ALL")
        
        try:
            from metadata_manager import MetadataManager
            meta_mgr = MetadataManager()
            c_clean = champion_name.lower().replace("'", "").replace(" ", "").replace("_", "")
            skins_found = dict(meta_mgr.skins_by_champ.get(c_clean, {}))
            
            if not skins_found:
                for s in meta_mgr.skins_raw_db:
                    c_alias = s.get('champion_alias', '').lower()
                    c_name = s.get('champion_name', '').lower()
                    if c_alias == c_clean or c_name == c_clean:
                        s_num = s.get('skin_num', 0)
                        s_name = s.get('name_tr', '')
                        if s_name:
                            skins_found[s_num] = s_name.replace(" ", "_")

            for s_num, s_name in sorted(skins_found.items(), key=lambda x: x[0]):
                label = f"🛡️ Varsayılan {champion_name}" if s_num == 0 else f"🎭 {s_name.replace('_', ' ')}"
                val = f"Varsayilan_{champion_name}" if s_num == 0 else s_name
                self.skin_combo.addItem(label, val)
        except Exception:
            pass
        self.skin_combo.blockSignals(False)

    def on_skin_changed(self, index):
        curr_item = self.champ_list.currentItem()
        if curr_item:
            ch = curr_item.data(Qt.UserRole)
            self.refresh_references_tree(ch)

    def on_speaker_type_changed(self, index):
        curr_item = self.champ_list.currentItem()
        if curr_item:
            ch = curr_item.data(Qt.UserRole)
            self.refresh_references_tree(ch)

    def refresh_current_target_tree(self):
        curr_item = self.champ_list.currentItem()
        if curr_item:
            ch = curr_item.data(Qt.UserRole)
            self.refresh_references_tree(ch)

    def refresh_references_tree(self, target_champion):
        self.tree_widget.clear()
        target_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, target_champion, f"{target_champion}e_Yapilan_Tum_Ozel_Atiflar")
        if not os.path.exists(target_dir):
            target_dir = os.path.join(CHAMPIONS_OUTPUT_PATH, f"Interactions_{target_champion}")
            if not os.path.exists(target_dir):
                root_item = QTreeWidgetItem([f"⚠️ {target_champion} için henüz atıf taraması yapılmadı."])
                root_item.setForeground(0, Qt.gray)
                self.tree_widget.addTopLevelItem(root_item)
                self.on_tree_selection_changed()
                return

        target_skin = self.skin_combo.currentData() if self.skin_combo.count() > 0 else "ALL"
        speaker_type = self.speaker_type_combo.currentData() if self.speaker_type_combo.count() > 0 else "all"

        norm_skin = None
        if target_skin and target_skin.upper() != 'ALL':
            norm_skin = target_skin.lower().replace('_', '').replace(' ', '').replace("'", "")

        for cat_folder in sorted(os.listdir(target_dir)):
            if norm_skin:
                clean_cat = cat_folder.lower().replace('_', '').replace(' ', '')
                if norm_skin not in clean_cat and clean_cat not in norm_skin:
                    continue

            cat_path = os.path.join(target_dir, cat_folder)
            if not os.path.isdir(cat_path):
                continue

            root_cat = QTreeWidgetItem([f"🌟 {cat_folder.replace('_', ' ')}"])
            root_cat.setForeground(0, Qt.cyan)

            added_speakers = 0
            for spk_champ in sorted(os.listdir(cat_path)):
                spk_path = os.path.join(cat_path, spk_champ)
                if not os.path.isdir(spk_path):
                    continue

                spk_item = QTreeWidgetItem([f"🗣️ {spk_champ}"])
                spk_item.setForeground(0, Qt.yellow)

                added_skins = 0
                for sk_folder in sorted(os.listdir(spk_path)):
                    sk_path = os.path.join(spk_path, sk_folder)
                    if not os.path.isdir(sk_path):
                        continue

                    is_base = (sk_folder == "Varsayilan_Hali" or "varsayilan" in sk_folder.lower())
                    if speaker_type == 'base_only' and not is_base:
                        continue
                    if speaker_type == 'skins_only' and is_base:
                        continue

                    badge = " [🛡️ Varsayılan]" if is_base else " [🎭 Kostüm]"
                    skin_item = QTreeWidgetItem([f"🎭 {sk_folder.replace('_', ' ')}{badge}"])
                    skin_item.setForeground(0, Qt.lightGray)

                    added_files = 0
                    for fname in sorted(os.listdir(sk_path)):
                        if fname.lower().endswith('.wav'):
                            f_item = QTreeWidgetItem([f"🔊 {fname}"])
                            f_item.setData(0, Qt.UserRole, os.path.join(sk_path, fname))
                            f_item.setForeground(0, Qt.white)
                            skin_item.addChild(f_item)
                            added_files += 1

                    if added_files > 0:
                        spk_item.addChild(skin_item)
                        added_skins += 1

                if added_skins > 0:
                    root_cat.addChild(spk_item)
                    added_speakers += 1

            if added_speakers > 0:
                self.tree_widget.addTopLevelItem(root_cat)
                root_cat.setExpanded(True)

        self.on_tree_selection_changed()

    def get_selected_audio_files(self):
        selected_files = []
        for item in self.tree_widget.selectedItems():
            fpath = item.data(0, Qt.UserRole)
            if fpath and os.path.isfile(fpath) and fpath.endswith('.wav'):
                selected_files.append(fpath)
        return selected_files

    def on_tree_selection_changed(self):
        sel_files = self.get_selected_audio_files()
        count = len(sel_files)
        self.sel_count_lbl.setText(f"{count} ses seçildi")
        self.davinci_btn.setEnabled(count > 0)

    def select_all_tree_items(self):
        def select_children(parent):
            for i in range(parent.childCount()):
                child = parent.child(i)
                fpath = child.data(0, Qt.UserRole)
                if fpath and os.path.isfile(fpath):
                    child.setSelected(True)
                select_children(child)

        for i in range(self.tree_widget.topLevelItemCount()):
            top = self.tree_widget.topLevelItem(i)
            select_children(top)

    def clear_tree_selection(self):
        self.tree_widget.clearSelection()

    def on_tree_item_clicked(self, item, col):
        file_path = item.data(0, Qt.UserRole)
        if file_path and os.path.exists(file_path):
            self.player_widget.load_audio(file_path)

    def on_tree_item_double_clicked(self, item, col):
        file_path = item.data(0, Qt.UserRole)
        if file_path and os.path.exists(file_path):
            self.player_widget.load_audio(file_path)
            self.player_widget.play()

    def export_selected_to_davinci(self):
        selected_files = self.get_selected_audio_files()
        if not selected_files:
            self.append_log("⚠️ Lütfen DaVinci'ye aktarmak için en az bir ses dosyası seçin (Shift / Ctrl ile çoklu seçebilirsiniz).")
            return

        curr_item = self.champ_list.currentItem()
        ch = curr_item.data(Qt.UserRole) if curr_item else "Hedef_Atiflar"
        target_skin = self.skin_combo.currentData() if self.skin_combo.count() > 0 else "ALL"

        out_xml = os.path.join(CHAMPIONS_OUTPUT_PATH, f"{ch}_{target_skin}_Secilen_{len(selected_files)}ses_DaVinci.xml")
        self.append_log(f"🎬 DaVinci Resolve Timeline oluşturuluyor ({len(selected_files)} ses)...")

        try:
            res = davinci_timeline_exporter.generate_davinci_timeline_xml(
                audio_file_paths=selected_files,
                output_xml_path=out_xml,
                timeline_name=f"{ch} {target_skin} Seçilen Replikler",
                gap_seconds=0.2,
                fps=60
            )
            self.append_log(f"✨ DaVinci Timeline Hazır: {os.path.basename(out_xml)} ({res['total_audio_count']} ses, {res['total_duration_formatted']})")
        except Exception as e:
            self.append_log(f"❌ DaVinci Hatası: {e}")

    def start_scan(self):
        curr_item = self.champ_list.currentItem()
        if not curr_item:
            return
        ch = curr_item.data(Qt.UserRole)
        target_skin = self.skin_combo.currentData() if self.skin_combo.count() > 0 else "ALL"

        self.scan_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.log_text.clear()
        skin_msg = f" ({target_skin})" if target_skin != 'ALL' else ""
        self.log_text.append(f"🎯 [{ch.upper()}]{skin_msg} için tüm LoL şampiyon atıf taraması başlatıldı...\n")

        self.worker = ReferenceDetectorWorker(ch, target_skin=target_skin)
        self.worker.progress_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.on_scan_finished)
        self.worker.start()

    def append_log(self, text):
        self.log_text.append(text)
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_scan_finished(self, success, message):
        self.scan_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.log_text.append(f"\n{message}\n")
        
        curr_item = self.champ_list.currentItem()
        if curr_item:
            ch = curr_item.data(Qt.UserRole)
            self.refresh_references_tree(ch)

