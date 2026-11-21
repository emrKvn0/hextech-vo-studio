"""
⚡ Hextech Neo-Glass & Tailwind Design System for PySide6
League of Legends Voice & Media Automation Studio
"""

HEXTECH_PALETTE = {
    # Dark & Glass Backgrounds
    "bg_base": "#040810",
    "bg_surface": "#09121E",
    "bg_card": "#0F1C2E",
    "bg_card_hover": "#172A42",
    "bg_card_selected": "#1C3350",
    "bg_input": "#070E18",
    "bg_input_focus": "#0C1827",
    
    # Hextech Gold Accents
    "gold_bright": "#F4E0A8",
    "gold_primary": "#D4AC58",
    "gold_hover": "#F0C872",
    "gold_dim": "#8A6C32",
    "gold_border": "#4A3B22",
    
    # Zaun & Piltover Cyan / Neon Accents
    "cyan_neon": "#00F2DE",
    "cyan_primary": "#0AC8B9",
    "cyan_hover": "#36EBDD",
    "cyan_dark": "#063A38",
    "cyan_border": "#0E5A57",
    "cyan_glow": "rgba(0, 242, 222, 0.25)",
    
    # Text Hierarchy
    "text_primary": "#F3F7FA",
    "text_secondary": "#A2B4C7",
    "text_muted": "#576A80",
    
    # Border & Line Tokens
    "border_subtle": "#16273B",
    "border_medium": "#233A54",
    "border_highlight": "#3A5C82",
    
    # Functional Colors
    "danger": "#FF4655",
    "danger_bg": "rgba(255, 70, 85, 0.15)",
    "success": "#10B981",
    "success_bg": "rgba(16, 185, 129, 0.15)",
    "warning": "#F59E0B"
}

MAIN_STYLE_QSS = f"""
/* =========================================================================
   GLOBAL RESET & TYPOGRAPHY
   ========================================================================= */
QMainWindow {{
    background-color: {HEXTECH_PALETTE['bg_base']};
    color: {HEXTECH_PALETTE['text_primary']};
}}

QWidget {{
    font-family: 'Segoe UI', 'Inter', 'SF Pro Display', -apple-system, sans-serif;
    font-size: 13px;
    color: {HEXTECH_PALETTE['text_primary']};
    selection-background-color: {HEXTECH_PALETTE['cyan_dark']};
    selection-color: {HEXTECH_PALETTE['cyan_neon']};
}}

/* =========================================================================
   SIDEBAR & MODERN NAVIGATION
   ========================================================================= */
#Sidebar {{
    background-color: {HEXTECH_PALETTE['bg_surface']};
    border-right: 1px solid {HEXTECH_PALETTE['border_subtle']};
    min-width: 240px;
    max-width: 240px;
}}

#SidebarHeader {{
    padding: 24px 20px 16px 20px;
    border-bottom: 1px solid {HEXTECH_PALETTE['border_subtle']};
}}

#SidebarTitle {{
    font-size: 15px;
    font-weight: 800;
    color: {HEXTECH_PALETTE['gold_primary']};
    letter-spacing: 0.5px;
}}

#SidebarSubtitle {{
    font-size: 11px;
    font-weight: 600;
    color: {HEXTECH_PALETTE['cyan_primary']};
    letter-spacing: 1.5px;
    text-transform: uppercase;
}}

#NavButton {{
    background-color: transparent;
    border: none;
    border-left: 3px solid transparent;
    color: {HEXTECH_PALETTE['text_secondary']};
    font-size: 13px;
    font-weight: 600;
    text-align: left;
    padding: 13px 20px;
    margin: 2px 8px;
    border-radius: 6px;
}}

#NavButton:hover {{
    background-color: {HEXTECH_PALETTE['bg_card']};
    color: {HEXTECH_PALETTE['text_primary']};
    border-left: 3px solid {HEXTECH_PALETTE['gold_primary']};
}}

#NavButton:checked {{
    background-color: {HEXTECH_PALETTE['bg_card_hover']};
    color: {HEXTECH_PALETTE['cyan_neon']};
    font-weight: 700;
    border-left: 3px solid {HEXTECH_PALETTE['cyan_neon']};
}}

/* =========================================================================
   CARDS, PANELS & GLASS SURFACES
   ========================================================================= */
QFrame#GlassCard {{
    background-color: {HEXTECH_PALETTE['bg_surface']};
    border: 1px solid {HEXTECH_PALETTE['border_subtle']};
    border-radius: 10px;
    padding: 12px;
}}

QFrame#GlassCard:hover {{
    border: 1px solid {HEXTECH_PALETTE['border_medium']};
}}

QFrame#AccentCard {{
    background-color: {HEXTECH_PALETTE['bg_card']};
    border: 1px solid {HEXTECH_PALETTE['border_medium']};
    border-radius: 10px;
    padding: 14px;
}}

QFrame#PlayerCard {{
    background-color: {HEXTECH_PALETTE['bg_surface']};
    border: 1px solid {HEXTECH_PALETTE['cyan_border']};
    border-radius: 12px;
    padding: 16px;
}}

/* =========================================================================
   BUTTONS (TAILWIND STYLE SHADOW & HOVER)
   ========================================================================= */
QPushButton {{
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-weight: 600;
    border-radius: 7px;
    padding: 9px 18px;
    font-size: 13px;
    border: 1px solid transparent;
}}

/* Primary Gold Action Button */
QPushButton#PrimaryGoldButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E5B95F, stop:1 #C49A3E);
    color: #040810;
    font-weight: 700;
    border: 1px solid {HEXTECH_PALETTE['gold_bright']};
}}

QPushButton#PrimaryGoldButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F5CF78, stop:1 #D9AE4D);
    border: 1px solid #FFFFFF;
}}

QPushButton#PrimaryGoldButton:pressed {{
    background: #A07828;
}}

QPushButton#PrimaryGoldButton:disabled {{
    background: #1C2735;
    color: #4A5B6E;
    border: 1px solid #233446;
}}

/* Cyan Accent Button */
QPushButton#CyanActionButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #092F36, stop:1 #062228);
    border: 1px solid {HEXTECH_PALETTE['cyan_primary']};
    color: {HEXTECH_PALETTE['cyan_neon']};
    font-weight: 700;
}}

QPushButton#CyanActionButton:hover {{
    background: {HEXTECH_PALETTE['cyan_primary']};
    color: #020B12;
    border: 1px solid {HEXTECH_PALETTE['cyan_neon']};
}}

QPushButton#CyanActionButton:pressed {{
    background: {HEXTECH_PALETTE['cyan_dark']};
    color: {HEXTECH_PALETTE['cyan_neon']};
}}

QPushButton#CyanActionButton:disabled {{
    background: #0D1C28;
    color: #385065;
    border: 1px solid #162B3D;
}}

/* Ghost / Secondary Button */
QPushButton#GhostButton {{
    background-color: {HEXTECH_PALETTE['bg_card']};
    border: 1px solid {HEXTECH_PALETTE['border_subtle']};
    color: {HEXTECH_PALETTE['text_secondary']};
}}

QPushButton#GhostButton:hover {{
    background-color: {HEXTECH_PALETTE['bg_card_hover']};
    border: 1px solid {HEXTECH_PALETTE['border_highlight']};
    color: {HEXTECH_PALETTE['text_primary']};
}}

/* =========================================================================
   INPUTS & SEARCH BOXES
   ========================================================================= */
QLineEdit {{
    background-color: {HEXTECH_PALETTE['bg_input']};
    border: 1px solid {HEXTECH_PALETTE['border_subtle']};
    border-radius: 7px;
    color: {HEXTECH_PALETTE['text_primary']};
    padding: 8px 14px;
    font-size: 13px;
}}

QLineEdit:hover {{
    border: 1px solid {HEXTECH_PALETTE['border_medium']};
}}

QLineEdit:focus {{
    background-color: {HEXTECH_PALETTE['bg_input_focus']};
    border: 1px solid {HEXTECH_PALETTE['cyan_primary']};
}}

/* =========================================================================
   LISTS & TREE EXPLORER
   ========================================================================= */
QListWidget, QTreeWidget {{
    background-color: {HEXTECH_PALETTE['bg_input']};
    border: 1px solid {HEXTECH_PALETTE['border_subtle']};
    border-radius: 8px;
    padding: 4px;
    outline: none;
}}

QListWidget::item, QTreeWidget::item {{
    padding: 7px 10px;
    border-radius: 6px;
    margin: 1px 0px;
}}

QListWidget::item:hover, QTreeWidget::item:hover {{
    background-color: {HEXTECH_PALETTE['bg_card_hover']};
    color: {HEXTECH_PALETTE['text_primary']};
}}

QListWidget::item:selected, QTreeWidget::item:selected {{
    background-color: {HEXTECH_PALETTE['bg_card_selected']};
    border-left: 3px solid {HEXTECH_PALETTE['cyan_neon']};
    color: {HEXTECH_PALETTE['cyan_neon']};
    font-weight: 600;
}}

QTreeWidget::branch:has-children:!has-siblings:closed,
QTreeWidget::branch:closed:has-children:has-siblings {{
    image: none;
}}

/* =========================================================================
   TERMINAL & LOG CONSOLE
   ========================================================================= */
QTextEdit#ConsoleView {{
    background-color: #03070E;
    border: 1px solid {HEXTECH_PALETTE['border_subtle']};
    border-radius: 8px;
    color: {HEXTECH_PALETTE['text_secondary']};
    font-family: 'Consolas', 'Cascadia Code', 'Fira Code', monospace;
    font-size: 11.5px;
    padding: 10px;
    line-height: 1.4;
}}

/* =========================================================================
   SLIDERS & PROGRESS BARS
   ========================================================================= */
QSlider::groove:horizontal {{
    background: {HEXTECH_PALETTE['bg_input']};
    height: 6px;
    border-radius: 3px;
    border: 1px solid {HEXTECH_PALETTE['border_subtle']};
}}

QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {HEXTECH_PALETTE['cyan_primary']}, stop:1 {HEXTECH_PALETTE['cyan_neon']});
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: {HEXTECH_PALETTE['gold_primary']};
    border: 2px solid #FFFFFF;
    width: 14px;
    height: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background: {HEXTECH_PALETTE['gold_bright']};
    transform: scale(1.2);
}}

QProgressBar {{
    background-color: {HEXTECH_PALETTE['bg_input']};
    border: 1px solid {HEXTECH_PALETTE['border_subtle']};
    border-radius: 5px;
    text-align: center;
    color: {HEXTECH_PALETTE['text_primary']};
    font-size: 11px;
    font-weight: bold;
    height: 12px;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {HEXTECH_PALETTE['gold_primary']}, stop:1 {HEXTECH_PALETTE['cyan_neon']});
    border-radius: 4px;
}}

/* =========================================================================
   SCROLLBARS (MODERN ULTRA SLIM)
   ========================================================================= */
QScrollBar:vertical {{
    background: {HEXTECH_PALETTE['bg_base']};
    width: 7px;
    border-radius: 3.5px;
    margin: 2px 0px;
}}

QScrollBar::handle:vertical {{
    background: {HEXTECH_PALETTE['border_highlight']};
    min-height: 25px;
    border-radius: 3.5px;
}}

QScrollBar::handle:vertical:hover {{
    background: {HEXTECH_PALETTE['gold_dim']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: {HEXTECH_PALETTE['bg_base']};
    height: 7px;
    border-radius: 3.5px;
}}

QScrollBar::handle:horizontal {{
    background: {HEXTECH_PALETTE['border_highlight']};
    min-width: 25px;
    border-radius: 3.5px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* =========================================================================
   SPLITTER & HEADERS
   ========================================================================= */
QSplitter::handle {{
    background-color: {HEXTECH_PALETTE['border_subtle']};
    width: 2px;
}}

QSplitter::handle:hover {{
    background-color: {HEXTECH_PALETTE['cyan_primary']};
}}

QHeaderView::section {{
    background-color: {HEXTECH_PALETTE['bg_card']};
    color: {HEXTECH_PALETTE['gold_primary']};
    font-weight: 700;
    font-size: 12px;
    padding: 6px 10px;
    border: none;
    border-bottom: 1px solid {HEXTECH_PALETTE['border_medium']};
}}
"""
