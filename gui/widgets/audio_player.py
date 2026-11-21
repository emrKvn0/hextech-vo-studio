import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QSlider, QFrame
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from gui.theme import HEXTECH_PALETTE

class AudioPlayerWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PlayerCard")
        self.current_audio_path = None

        # Media Player Setup
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.85)

        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)

        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(10)

        # Header Info Row: Status Badge & Filename
        top_row = QHBoxLayout()
        self.status_badge = QLabel("⚡ SES OYNATICI")
        self.status_badge.setStyleSheet(f"""
            background-color: {HEXTECH_PALETTE['cyan_dark']};
            color: {HEXTECH_PALETTE['cyan_neon']};
            font-size: 10px;
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 4px;
            border: 1px solid {HEXTECH_PALETTE['cyan_border']};
        """)
        
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet(f"color: {HEXTECH_PALETTE['text_secondary']}; font-size: 12px; font-family: monospace;")

        top_row.addWidget(self.status_badge)
        top_row.addStretch(1)
        top_row.addWidget(self.time_label)
        main_layout.addLayout(top_row)

        # Track Title Label
        self.title_label = QLabel("🎵 Dinlemek için listeden bir ses dosyası seçin")
        self.title_label.setStyleSheet(f"font-weight: bold; color: {HEXTECH_PALETTE['text_primary']}; font-size: 14px;")
        self.title_label.setWordWrap(True)
        main_layout.addWidget(self.title_label)

        # Subtitle Text (if transcribed)
        self.subtitle_label = QLabel("")
        self.subtitle_label.setStyleSheet(f"color: {HEXTECH_PALETTE['gold_bright']}; font-size: 12px; font-style: italic;")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setVisible(False)
        main_layout.addWidget(self.subtitle_label)

        # Timeline Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.sliderMoved.connect(self.set_position)
        main_layout.addWidget(self.slider)

        # Bottom Controls Row (Play/Pause, Stop, Volume)
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(10)

        self.play_btn = QPushButton("▶ Oynat")
        self.play_btn.setObjectName("CyanActionButton")
        self.play_btn.setFixedWidth(100)
        self.play_btn.clicked.connect(self.toggle_play)
        ctrl_row.addWidget(self.play_btn)

        self.stop_btn = QPushButton("⏹ Durdur")
        self.stop_btn.setObjectName("GhostButton")
        self.stop_btn.setFixedWidth(90)
        self.stop_btn.clicked.connect(self.stop_audio)
        ctrl_row.addWidget(self.stop_btn)

        ctrl_row.addStretch(1)

        # Volume Controls
        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet(f"color: {HEXTECH_PALETTE['text_muted']}; font-size: 13px;")
        ctrl_row.addWidget(vol_icon)

        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(85)
        self.vol_slider.setFixedWidth(90)
        self.vol_slider.valueChanged.connect(self.set_volume)
        ctrl_row.addWidget(self.vol_slider)

        main_layout.addLayout(ctrl_row)

    def load_audio(self, audio_path):
        self.current_audio_path = audio_path
        fname = os.path.basename(audio_path)
        self.title_label.setText(f"🔊 {fname}")
        
        # Load subtitle if txt exists
        txt_path = audio_path.replace('.wav', '.txt')
        if os.path.exists(txt_path):
            try:
                with open(txt_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        self.subtitle_label.setText(f'💬 "{content}"')
                        self.subtitle_label.setVisible(True)
                    else:
                        self.subtitle_label.setVisible(False)
            except Exception:
                self.subtitle_label.setVisible(False)
        else:
            self.subtitle_label.setVisible(False)

        self.player.setSource(QUrl.fromLocalFile(audio_path))
        self.play()

    def play(self):
        self.player.play()
        self.play_btn.setText("⏸ Duraklat")
        self.status_badge.setText("▶ OYNATILIYOR")

    def pause(self):
        self.player.pause()
        self.play_btn.setText("▶ Oynat")
        self.status_badge.setText("⏸ DURAKLATILDI")

    def stop_audio(self):
        self.player.stop()
        self.play_btn.setText("▶ Oynat")
        self.status_badge.setText("⚡ SES OYNATICI")
        self.slider.setValue(0)
        self.update_time_label(0, self.player.duration())

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.pause()
        else:
            self.play()

    def set_volume(self, value):
        self.audio_output.setVolume(value / 100.0)

    def on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.play_btn.setText("⏸ Duraklat")
            self.status_badge.setText("▶ OYNATILIYOR")
        elif state == QMediaPlayer.StoppedState:
            self.play_btn.setText("▶ Oynat")
            self.status_badge.setText("⚡ SES OYNATICI")
        else:
            self.play_btn.setText("▶ Oynat")
            self.status_badge.setText("⏸ DURAKLATILDI")

    def on_position_changed(self, position):
        if not self.slider.isSliderDown():
            self.slider.setValue(position)
        self.update_time_label(position, self.player.duration())

    def on_duration_changed(self, duration):
        self.slider.setRange(0, duration)
        self.update_time_label(self.player.position(), duration)

    def set_position(self, position):
        self.player.setPosition(position)

    def update_time_label(self, pos, dur):
        p_sec = int(pos // 1000)
        d_sec = int(dur // 1000) if dur > 0 else 0
        self.time_label.setText(f"{p_sec//60:02d}:{p_sec%60:02d} / {d_sec//60:02d}:{d_sec%60:02d}")
