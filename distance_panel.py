"""
panels/distance_panel.py  ── 实时距离面板（Tab 2）
"""

from typing import List

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
)

from core.shape_item import ShapeItem
from core.analysis   import DistanceResult
from utils.helpers   import make_divider, make_section_label, make_value_label

_CONTACT_THRESHOLD = 0.01


class DistancePanel(QWidget):
    """
    Signals:
        sig_pair_changed (int, int)  用户切换了形体对
    """

    sig_pair_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)

        lay.addWidget(make_section_label("选择形体对"))
        row = QHBoxLayout()
        row.setSpacing(6)
        self.cb_a = QComboBox()
        self.cb_b = QComboBox()
        arrow = QLabel("↔")
        arrow.setAlignment(Qt.AlignCenter)
        arrow.setStyleSheet("color:#7eb8f7; font-size:14px;")
        self.cb_a.currentIndexChanged.connect(self._emit_pair)
        self.cb_b.currentIndexChanged.connect(self._emit_pair)
        row.addWidget(self.cb_a)
        row.addWidget(arrow)
        row.addWidget(self.cb_b)
        lay.addLayout(row)

        lay.addWidget(make_divider())
        lay.addWidget(make_section_label("最小距离"))
        self.lbl_dist = make_value_label()
        lay.addWidget(self.lbl_dist)

        lay.addWidget(make_divider())
        lay.addWidget(make_section_label("形体 A 最近点"))
        self.lbl_pt1 = make_value_label()
        self.lbl_pt1.setWordWrap(True)
        lay.addWidget(self.lbl_pt1)

        lay.addWidget(make_section_label("形体 B 最近点"))
        self.lbl_pt2 = make_value_label()
        self.lbl_pt2.setWordWrap(True)
        lay.addWidget(self.lbl_pt2)

        lay.addStretch()

    def _emit_pair(self):
        self.sig_pair_changed.emit(self.cb_a.currentIndex(),
                                   self.cb_b.currentIndex())

    def refresh_combos(self, items: List[ShapeItem]):
        ia = self.cb_a.currentIndex()
        ib = self.cb_b.currentIndex()
        self.cb_a.blockSignals(True)
        self.cb_b.blockSignals(True)
        self.cb_a.clear()
        self.cb_b.clear()
        for it in items:
            self.cb_a.addItem(it.name)
            self.cb_b.addItem(it.name)
        n = len(items)
        self.cb_a.setCurrentIndex(max(0, min(ia, n - 1)))
        new_b = max(0, min(ib, n - 1))
        if new_b == self.cb_a.currentIndex() and n > 1:
            new_b = 1
        self.cb_b.setCurrentIndex(new_b)
        self.cb_a.blockSignals(False)
        self.cb_b.blockSignals(False)

    def update_result(self, result: DistanceResult):
        d = result.distance
        if d < _CONTACT_THRESHOLD:
            self.lbl_dist.setText("接触 / 重叠")
            self.lbl_dist.setStyleSheet(
                "color:#ff5544; font-size:14px; font-weight:700;")
        else:
            self.lbl_dist.setText(f"{d:.6f}")
            self.lbl_dist.setStyleSheet(
                "color:#e0e0ff; font-size:14px; font-weight:600;")

        fmt = "({:.3f},  {:.3f},  {:.3f})"
        self.lbl_pt1.setText(fmt.format(
            result.point_a.X(), result.point_a.Y(), result.point_a.Z()))
        self.lbl_pt2.setText(fmt.format(
            result.point_b.X(), result.point_b.Y(), result.point_b.Z()))
