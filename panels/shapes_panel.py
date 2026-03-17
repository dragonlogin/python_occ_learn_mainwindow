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
    QDialog, QFormLayout, QDoubleSpinBox,
    QDialogButtonBox, QLabel,
)

from core.shape_item  import ShapeItem
from core.importer    import supported_filter
from utils.helpers    import make_divider, make_section_label


# 每种体素的参数定义：(显示名, key, 默认值, 最小值, 最大值)
_PRIM_PARAMS = {
    "Box": [
        ("宽 (X)", "dx", 40.0, 0.01, 9999.0),
        ("深 (Y)", "dy", 30.0, 0.01, 9999.0),
        ("高 (Z)", "dz", 20.0, 0.01, 9999.0),
    ],
    "Sphere": [
        ("半径",   "r",  20.0, 0.01, 9999.0),
    ],
    "Cylinder": [
        ("半径",   "r",  15.0, 0.01, 9999.0),
        ("高",     "h",  40.0, 0.01, 9999.0),
    ],
    "Cone": [
        ("底半径", "r1", 15.0, 0.01, 9999.0),
        ("顶半径", "r2",  5.0, 0.00, 9999.0),
        ("高",     "h",  40.0, 0.01, 9999.0),
    ],
}

_STYLE = """
QDialog {
    background: #1a2030;
}
QLabel {
    color: #a0b8d0;
    font-size: 12px;
}
QDoubleSpinBox {
    background: #0d1525;
    color: #d0e8ff;
    border: 1px solid #2a3a50;
    border-radius: 4px;
    padding: 3px 6px;
    font-size: 12px;
}
QDoubleSpinBox:focus {
    border-color: #4a90d0;
}
QPushButton {
    background: #2a3a55;
    color: #c0d8f0;
    border: 1px solid #3a5070;
    border-radius: 4px;
    padding: 5px 14px;
    font-size: 12px;
    min-width: 64px;
}
QPushButton:hover  { background: #3a5070; }
QPushButton:pressed{ background: #1a2540; }
"""


_XYZ_PARAMS = [
    ("X", "x", 0.0, -99999.0, 99999.0),
    ("Y", "y", 0.0, -99999.0, 99999.0),
    ("Z", "z", 0.0, -99999.0, 99999.0),
]
_RPY_PARAMS = [
    ("Roll  (°)",  "roll",  0.0, -360.0, 360.0),
    ("Pitch (°)",  "pitch", 0.0, -360.0, 360.0),
    ("Yaw   (°)",  "yaw",   0.0, -360.0, 360.0),
]

_SEC_STYLE = "color:#6a90b8;font-size:11px;font-weight:bold;padding-top:6px;"


class _PrimDialog(QDialog):
    """通用体素参数输入对话框（形体尺寸 + 位置 XYZ + 旋转 RPY）"""

    def __init__(self, title: str, param_defs: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"新建 {title}")
        self.setModal(True)
        self.setStyleSheet(_STYLE)

        self._spins: dict = {}
        root = QVBoxLayout(self)
        root.setSpacing(4)
        root.setContentsMargins(16, 12, 16, 10)

        def _add_section(label_text: str, defs: list):
            hdr = QLabel(label_text)
            hdr.setStyleSheet(_SEC_STYLE)
            root.addWidget(hdr)
            form = QFormLayout()
            form.setSpacing(6)
            form.setContentsMargins(0, 0, 0, 0)
            form.setLabelAlignment(Qt.AlignRight)
            for lbl, key, default, vmin, vmax in defs:
                spin = QDoubleSpinBox()
                spin.setRange(vmin, vmax)
                spin.setDecimals(2)
                spin.setValue(default)
                spin.setSingleStep(1.0)
                spin.setFixedWidth(110)
                self._spins[key] = spin
                form.addRow(QLabel(lbl), spin)
            root.addLayout(form)

        if param_defs:
            _add_section("── 形体参数 ──", param_defs)
        _add_section("── 位置 ──", _XYZ_PARAMS)
        _add_section("── 旋转 ──", _RPY_PARAMS)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addSpacing(6)
        root.addWidget(btns)

    def values(self) -> dict:
        return {k: spin.value() for k, spin in self._spins.items()}


class ShapesPanel(QWidget):
    """
    Signals:
        sig_add_primitive (str, dict)  体素名称 + 参数字典
        sig_import_file   (str)        选择的文件路径
        sig_delete        (int)        待删除的 shape 索引
        sig_toggle        (int)        待切换可见性的 shape 索引
        sig_select        (int)        列表选中的 shape 索引
    """

    sig_add_primitive = pyqtSignal(str, dict)
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

    def _on_prim_clicked(self, name: str):
        param_defs = _PRIM_PARAMS.get(name, [])
        if not param_defs:
            self.sig_add_primitive.emit(name, {})
            return
        dlg = _PrimDialog(name, param_defs, self)
        if dlg.exec_() == QDialog.Accepted:
            self.sig_add_primitive.emit(name, dlg.values())

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
            btn.clicked.connect(lambda _, n=name: self._on_prim_clicked(n))
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
