"""
panels/collision_panel.py  ── 碰撞检测面板（Tab 3）
"""

from typing import List

from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QDoubleSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
)

from core.shape_item import ShapeItem
from core.analysis   import CollisionEntry
from utils.helpers   import make_divider, make_section_label

DEFAULT_THRESHOLD = 0.01


class CollisionPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)

        # 阈值
        lay.addWidget(make_section_label("碰撞阈值"))
        row = QHBoxLayout()
        row.addWidget(QLabel("距离 <"))
        self.spin = QDoubleSpinBox()
        self.spin.setRange(0.0001, 9999.0)
        self.spin.setValue(DEFAULT_THRESHOLD)
        self.spin.setDecimals(4)
        self.spin.setSingleStep(0.01)
        row.addWidget(self.spin)
        row.addStretch()
        lay.addLayout(row)

        lay.addWidget(make_divider())

        # 全局状态
        self.lbl_status = QLabel("暂无数据")
        self.lbl_status.setStyleSheet(
            "color:#ffaa44; font-size:13px; font-weight:600;")
        lay.addWidget(self.lbl_status)

        # 表格
        lay.addWidget(make_section_label("所有形体对"))
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["形体 A", "形体 B", "距离"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        lay.addWidget(self.table, stretch=1)

    @property
    def threshold(self) -> float:
        return self.spin.value()

    def update_collisions(self, entries: List[CollisionEntry],
                          items: List[ShapeItem]):
        thresh = self.threshold
        self.table.setRowCount(0)

        if len(items) < 2:
            self.lbl_status.setText("场景中少于 2 个形体")
            self.lbl_status.setStyleSheet(
                "color:#ffaa44; font-size:13px; font-weight:600;")
            return

        any_hit = False
        for e in entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            dist_str = "接触" if e.distance < 1e-6 else f"{e.distance:.5f}"
            hit = e.is_colliding(thresh)
            for col, txt in enumerate([e.name_a, e.name_b, dist_str]):
                cell = QTableWidgetItem(txt)
                if hit:
                    cell.setForeground(QColor("#ff6655"))
                    cell.setBackground(QColor("#2a1218"))
                self.table.setItem(row, col, cell)
            if hit:
                any_hit = True

        if any_hit:
            self.lbl_status.setText("⚠  检测到碰撞！")
            self.lbl_status.setStyleSheet(
                "color:#ff5544; font-size:13px; font-weight:700;")
        else:
            self.lbl_status.setText("✓  无碰撞")
            self.lbl_status.setStyleSheet(
                "color:#44dd88; font-size:13px; font-weight:700;")
