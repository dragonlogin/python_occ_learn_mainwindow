"""
ui/styles.py  ── 全局 Qt 样式表

扩展指引：
  - 主题切换：改为 ThemeManager 类，提供 dark_theme() / light_theme()。
  - 字体大小：调用 build_qss(font_size) 动态生成，默认 12px。
"""


def build_qss(font_size: int = 12) -> str:
    """生成带有指定字体大小的全局 QSS。"""
    fs      = font_size          # 正文字号
    fs_sm   = max(fs - 1, 9)     # 小字号（标签、版本号等）
    fs_tab  = max(fs - 1, 9)     # Tab 字号

    return f"""
* {{ font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; font-size: {fs}px; }}
QMainWindow {{ background: #111120; }}

QWidget#sidebar {{
    background: #181830;
    border-right: 1px solid #252548;
    min-width: 280px;
    max-width: 280px;
}}

QTabWidget::pane  {{ border: none; background: #181830; }}
QTabBar::tab {{
    background: #111120; color: #505080;
    padding: 10px 0; min-width: 56px;
    font-size: {fs_tab}px; border: none;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected          {{ color: #7eb8f7; border-bottom: 2px solid #7eb8f7; background: #181830; }}
QTabBar::tab:hover:!selected   {{ color: #9090bb; }}

QPushButton {{
    background: #1e1e3a; color: #b0b0d0;
    border: 1px solid #303060; border-radius: 6px;
    padding: 7px 10px; font-size: {fs}px; text-align: left;
}}
QPushButton:hover   {{ background: #282850; color: #ffffff; border-color: #5055aa; }}
QPushButton:pressed {{ background: #7eb8f7; color: #111120; border-color: #7eb8f7; }}
QPushButton:checked {{ background: #1a3060; border-color: #3060cc; color: #7eb8f7; }}
QPushButton#add {{ background:#1a2e1a; border-color:#2a4e2a; color:#66cc66; }}
QPushButton#add:hover {{ background:#224422; color:#aaffaa; }}
QPushButton#add:checked {{ background:#1a3a2a; border-color:#2a6040; color:#44ffaa; }}
QPushButton#imp {{ background:#1a1e2e; border-color:#2a2e5e; color:#6688ff; }}
QPushButton#imp:hover {{ background:#222650; color:#aabbff; }}
QPushButton#del {{ background:#2e1a1a; border-color:#5e2a2a; color:#ee6666; }}
QPushButton#del:hover {{ background:#4a2020; color:#ffaaaa; }}
QPushButton#vis {{ background:#1e2a1e; border-color:#2a4a2a; color:#88bb88; }}
QPushButton#vis:hover {{ background:#2a3e2a; color:#bbffbb; }}

QListWidget {{
    background: #0f0f1e; border: 1px solid #252548;
    border-radius: 6px; color: #c0c0e0; font-size: {fs}px; outline: none;
}}
QListWidget::item              {{ padding: 8px 10px; border-bottom: 1px solid #1a1a30; }}
QListWidget::item:selected     {{ background: #1e2050; color: #7eb8f7; }}
QListWidget::item:hover:!selected {{ background: #161630; }}

QComboBox {{
    background: #1e1e3a; border: 1px solid #303060; border-radius: 5px;
    color: #c0c0e0; padding: 5px 8px; font-size: {fs}px; min-height: 26px;
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: #181830; color: #c0c0e0;
    selection-background-color: #252550; border: 1px solid #303060;
}}

QDoubleSpinBox, QSpinBox {{
    background: #1e1e3a; border: 1px solid #303060; border-radius: 5px;
    color: #c0c0e0; padding: 4px 8px; font-size: {fs}px;
}}

QScrollBar:vertical               {{ background: #0f0f1e; width: 5px; }}
QScrollBar::handle:vertical       {{ background: #303060; border-radius: 2px; min-height: 20px; }}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical     {{ height: 0; }}

QTableWidget {{
    background: #0f0f1e; border: 1px solid #252548;
    border-radius: 6px; color: #c0c0e0; font-size: {fs_sm}px;
    gridline-color: #1a1a30;
}}
QTableWidget::item          {{ padding: 5px 8px; border: none; }}
QTableWidget::item:selected {{ background: #1e2050; }}
QHeaderView::section {{
    background: #181830; color: #7eb8f7; border: none;
    border-bottom: 1px solid #252548; padding: 6px 8px; font-size: {fs_sm}px;
}}

QLabel {{ color: #707098; font-size: {fs}px; }}

QSlider::groove:horizontal {{
    background: #252548; height: 4px; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: #7eb8f7; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: #3060aa; border-radius: 2px;
}}
"""


# 向后兼容：保留原 QSS 常量
QSS = build_qss(12)
