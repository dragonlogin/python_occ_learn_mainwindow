"""
utils/helpers.py  ── 通用工具函数
"""
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from PyQt5.QtWidgets import QLabel, QFrame


def qty_color(r: float, g: float, b: float) -> Quantity_Color:
    """构造 OCC Quantity_Color（RGB 0‥1）"""
    return Quantity_Color(r, g, b, Quantity_TOC_RGB)


def make_divider() -> QFrame:
    """1px 水平分隔线"""
    f = QFrame()
    f.setFixedHeight(1)
    f.setStyleSheet("background: #252548;")
    return f


def make_section_label(text: str) -> QLabel:
    """侧边栏蓝色小节标题"""
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "color: #7eb8f7; font-size: 11px; font-weight: 700;"
        "letter-spacing: 1px; padding: 6px 0 2px 0;"
    )
    return lbl


def make_value_label(text: str = "—") -> QLabel:
    """侧边栏数值显示标签"""
    lbl = QLabel(text)
    lbl.setStyleSheet("color: #e0e0ff; font-size: 13px; font-weight: 600;")
    return lbl
