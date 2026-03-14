"""
panels/measure_panel.py  ── 几何测量面板（Tab 4）
"""

from typing import List

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox

from core.shape_item import ShapeItem
from utils.helpers   import make_divider, make_section_label, make_value_label


class MeasurePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[ShapeItem] = []
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(4)

        lay.addWidget(make_section_label("选择形体"))
        self.cb = QComboBox()
        self.cb.currentIndexChanged.connect(self._on_select)
        lay.addWidget(self.cb)

        lay.addWidget(make_divider())
        lay.addWidget(make_section_label("几何属性"))

        def row(label):
            lay.addWidget(make_section_label(label))
            lbl = make_value_label()
            lbl.setWordWrap(True)
            lay.addSpacing(1)
            lay.addWidget(lbl)
            lay.addSpacing(4)
            return lbl

        self.lbl_vol  = row("体积")
        self.lbl_area = row("表面积")

        lay.addWidget(make_divider())
        lay.addWidget(make_section_label("包围盒"))
        self.lbl_size = row("尺寸  (ΔX × ΔY × ΔZ)")
        self.lbl_ctr  = row("中心坐标")
        self.lbl_diag = row("对角线长度")
        lay.addStretch()

    def refresh_combos(self, items: List[ShapeItem]):
        self._items = items
        cur = self.cb.currentIndex()
        self.cb.blockSignals(True)
        self.cb.clear()
        for it in items:
            self.cb.addItem(it.name)
        self.cb.setCurrentIndex(max(0, min(cur, len(items) - 1)))
        self.cb.blockSignals(False)
        if items:
            self._update(items[self.cb.currentIndex()])

    def select_item(self, idx: int):
        if 0 <= idx < self.cb.count():
            self.cb.setCurrentIndex(idx)

    def _on_select(self, idx: int):
        if 0 <= idx < len(self._items):
            self._update(self._items[idx])

    def _update(self, item: ShapeItem):
        self.lbl_vol.setText(f"{item.volume():.4f}")
        self.lbl_area.setText(f"{item.surface_area():.4f}")
        try:
            dx, dy, dz = item.bbox_size()
            cx, cy, cz = (c for c in [item.center().X(),
                                       item.center().Y(),
                                       item.center().Z()])
            self.lbl_size.setText(f"{dx:.3f}  ×  {dy:.3f}  ×  {dz:.3f}")
            self.lbl_ctr.setText(f"({cx:.3f},  {cy:.3f},  {cz:.3f})")
            self.lbl_diag.setText(f"{item.bbox_diagonal():.4f}")
        except Exception:
            for lbl in (self.lbl_size, self.lbl_ctr, self.lbl_diag):
                lbl.setText("—")
