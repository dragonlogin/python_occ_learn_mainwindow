"""
panels/shapes_panel.py  ── 形体管理面板（Tab 1）

职责：添加体素 / 导入文件 / 列表展示 / 显隐 / 删除
扩展指引：新增导入格式时只需更新 core/importer.py，此面板无需修改。
"""

import os
from typing import List

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem,
    QGridLayout, QFileDialog,
)

from core.shape_item  import ShapeItem
from core.importer    import supported_filter
from utils.helpers    import make_divider, make_section_label


class ShapesPanel(QWidget):
    """
    Signals:
        sig_add_primitive (str)   体素名称（Box / Sphere / Cylinder / Cone）
        sig_import_file   (str)   选择的文件路径
        sig_delete        (int)   待删除的 shape 索引
        sig_toggle        (int)   待切换可见性的 shape 索引
        sig_select        (int)   列表选中的 shape 索引
    """

    sig_add_primitive = pyqtSignal(str)
    sig_import_file   = pyqtSignal(str)
    sig_delete        = pyqtSignal(int)
    sig_toggle        = pyqtSignal(int)
    sig_select        = pyqtSignal(int)

    _PRIMITIVES = [
        ("Box",      "□  立方体"),
        ("Sphere",   "○  球体"),
        ("Cylinder", "◎  圆柱体"),
        ("Cone",     "△  圆锥体"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(6)

        # 基础体素
        lay.addWidget(make_section_label("基础形体"))
        grid = QGridLayout()
        grid.setSpacing(5)
        for idx, (name, label) in enumerate(self._PRIMITIVES):
            btn = QPushButton(label)
            btn.setObjectName("add")
            btn.clicked.connect(lambda _, n=name: self.sig_add_primitive.emit(n))
            grid.addWidget(btn, idx // 2, idx % 2)
        lay.addLayout(grid)

        lay.addWidget(make_divider())

        # 文件导入
        lay.addWidget(make_section_label("导入文件"))
        btn_imp = QPushButton("📂  导入 STEP / IGES / BREP")
        btn_imp.setObjectName("imp")
        btn_imp.clicked.connect(self._on_import)
        lay.addWidget(btn_imp)

        lay.addWidget(make_divider())

        # 场景形体列表
        lay.addWidget(make_section_label("场景形体"))
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.sig_select)
        lay.addWidget(self.list_widget, stretch=1)

        # 操作行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(5)
        btn_vis = QPushButton("👁  显示/隐藏")
        btn_vis.setObjectName("vis")
        btn_vis.clicked.connect(self._on_toggle)
        btn_del = QPushButton("✕  删除")
        btn_del.setObjectName("del")
        btn_del.clicked.connect(self._on_delete)
        btn_row.addWidget(btn_vis)
        btn_row.addWidget(btn_del)
        lay.addLayout(btn_row)

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开 CAD 文件", "", supported_filter()
        )
        if path:
            self.sig_import_file.emit(path)

    def _on_toggle(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.sig_toggle.emit(row)

    def _on_delete(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.sig_delete.emit(row)

    def refresh(self, items: List[ShapeItem]):
        cur = self.list_widget.currentRow()
        self.list_widget.clear()
        for it in items:
            icon = "●" if it.visible else "○"
            lwi  = QListWidgetItem(f"  {icon}  {it.name}")
            r, g, b = it.color
            lwi.setForeground(QColor(int(r * 255), int(g * 255), int(b * 255)))
            self.list_widget.addItem(lwi)
        if 0 <= cur < self.list_widget.count():
            self.list_widget.setCurrentRow(cur)

    def select_row(self, idx: int):
        if 0 <= idx < self.list_widget.count():
            self.list_widget.setCurrentRow(idx)
