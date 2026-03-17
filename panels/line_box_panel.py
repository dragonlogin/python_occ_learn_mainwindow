"""
panels/line_box_panel.py  ── 线框生成面板

信号：
  sig_lines_changed(list[LineWithNormals])
      每次线段列表发生变化（添加 / 删除 / 清空 / 载入预设）时发射，
      主窗口收到后先清空上一次的渲染，再重新生成。
      列表为空时主窗口只做清空，不生成任何几何体。
"""

import re
from typing import List

import numpy as np
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication,
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem,
    QCheckBox, QDoubleSpinBox, QLabel, QScrollArea,
)

from utils.helpers import make_divider, make_section_label

try:
    from create_box import LineWithNormals
except ImportError:
    from core.create_box import LineWithNormals


# ── XYZ 输入组 ────────────────────────────────────────────────────────────────

class XYZInput(QWidget):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)

        lbl = QLabel(label)
        lbl.setFixedWidth(52)
        lbl.setStyleSheet("color:#9090cc; font-size:11px; font-weight:600;")
        lay.addWidget(lbl)

        self._spins = []
        for axis in ("X", "Y", "Z"):
            sp = QDoubleSpinBox()
            sp.setRange(-9999.0, 9999.0)
            sp.setDecimals(2)
            sp.setValue(0.0)
            sp.setSingleStep(1.0)
            sp.setFixedWidth(55)
            sp.setToolTip(f"{label} {axis}")
            sp.setStyleSheet(
                "QDoubleSpinBox{background:#1e1e3a;border:1px solid #303060;"
                "border-radius:4px;color:#c0e0ff;font-size:11px;padding:2px 4px;}"
                "QDoubleSpinBox:focus{border-color:#7eb8f7;}"
            )
            lay.addWidget(sp)
            self._spins.append(sp)

    def value(self) -> List[float]:
        return [s.value() for s in self._spins]

    def set_value(self, x: float, y: float, z: float):
        for sp, v in zip(self._spins, (x, y, z)):
            sp.setValue(v)


# ── 面板主体 ──────────────────────────────────────────────────────────────────

class LineBoxPanel(QWidget):
    """
    Signals:
        sig_lines_changed(list)   线段列表变化时发射（含空列表表示清空）
    """

    sig_lines_changed = pyqtSignal(list)
    sig_connect_mode_changed = pyqtSignal(bool)
    sig_label_visible_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lines: List[LineWithNormals] = []
        self._build_ui()

    # ── UI 构建 ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(6)

        # 输入区
        hdr_row = QHBoxLayout()
        hdr_row.addWidget(make_section_label("输入线段"))
        hdr_row.addStretch()
        btn_paste = QPushButton("📋 粘贴")
        btn_paste.setToolTip(
            "从剪贴板粘贴12个数字，格式：\n"
            "起点X Y Z  法向1 X Y Z  终点X Y Z  法向2 X Y Z\n"
            "（数字可用空格/逗号/分号分隔）"
        )
        btn_paste.setFixedWidth(70)
        btn_paste.setStyleSheet(
            "QPushButton{background:#1e2a3a;border:1px solid #304060;"
            "border-radius:4px;color:#70b8ff;font-size:11px;padding:2px 6px;}"
            "QPushButton:hover{background:#243244;}"
        )
        btn_paste.clicked.connect(self._paste_values)
        hdr_row.addWidget(btn_paste)
        lay.addLayout(hdr_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(200)
        scroll.setStyleSheet(
            "QScrollArea{border:1px solid #252548;border-radius:6px;background:#0f0f1e;}"
        )
        inp_w = QWidget()
        inp_lay = QVBoxLayout(inp_w)
        inp_lay.setContentsMargins(8, 8, 8, 8)
        inp_lay.setSpacing(6)

        self.inp_start   = XYZInput("起点")
        self.inp_end     = XYZInput("终点")
        self.inp_normal1 = XYZInput("法向1"); self.inp_normal1.set_value(0, 0, 1)
        self.inp_normal2 = XYZInput("法向2"); self.inp_normal2.set_value(1, 0, 0)

        for w in (self.inp_start, self.inp_end, self.inp_normal1, self.inp_normal2):
            inp_lay.addWidget(w)
        inp_lay.addStretch()
        scroll.setWidget(inp_w)
        lay.addWidget(scroll)

        # 预设 + 添加/清空
        btn_preset = QPushButton("↺  载入默认示例（立方体 5 线）")
        btn_preset.setObjectName("imp")
        btn_preset.clicked.connect(self._load_preset)
        lay.addWidget(btn_preset)

        add_row = QHBoxLayout()
        add_row.setSpacing(5)
        btn_add = QPushButton("＋  添加线段")
        btn_add.setObjectName("add")
        btn_add.clicked.connect(self._add_line)
        btn_clr = QPushButton("✕  清空")
        btn_clr.setObjectName("del")
        btn_clr.clicked.connect(self._clear_lines)
        add_row.addWidget(btn_add, stretch=2)
        add_row.addWidget(btn_clr, stretch=1)
        lay.addLayout(add_row)

        # 模式选项
        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        self.chk_connect = QCheckBox("连接面")
        self.chk_connect.setChecked(True)
        self.chk_connect.setToolTip("勾选后，当线段 ≥2 条时自动生成面；\n取消勾选则只显示线段和法向")
        self.chk_connect.setStyleSheet(
            "QCheckBox{color:#a0b8d0;font-size:11px;}"
            "QCheckBox::indicator{width:13px;height:13px;border:1px solid #405060;"
            "border-radius:3px;background:#1a2030;}"
            "QCheckBox::indicator:checked{background:#3a6090;border-color:#70b8ff;}"
        )
        self.chk_connect.toggled.connect(self._on_mode_changed)
        mode_row.addWidget(self.chk_connect)

        self.chk_labels = QCheckBox("显示标签")
        self.chk_labels.setChecked(True)
        self.chk_labels.setToolTip("勾选后在视图中显示线段坐标和法向标签")
        self.chk_labels.setStyleSheet(
            "QCheckBox{color:#a0b8d0;font-size:11px;}"
            "QCheckBox::indicator{width:13px;height:13px;border:1px solid #405060;"
            "border-radius:3px;background:#1a2030;}"
            "QCheckBox::indicator:checked{background:#3a6090;border-color:#70b8ff;}"
        )
        self.chk_labels.toggled.connect(lambda v: self.sig_label_visible_changed.emit(v))
        mode_row.addWidget(self.chk_labels)
        mode_row.addStretch()
        lay.addLayout(mode_row)

        lay.addWidget(make_divider())

        # 线段列表
        lay.addWidget(make_section_label("已添加线段"))
        self.line_list = QListWidget()
        self.line_list.setFixedHeight(130)
        lay.addWidget(self.line_list)

        btn_del = QPushButton("✕  删除选中")
        btn_del.setObjectName("del")
        btn_del.clicked.connect(self._delete_selected)
        lay.addWidget(btn_del)

        lay.addWidget(make_divider())

        # 状态文字（主窗口也会写这里）
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("color:#707098; font-size:11px; padding:2px 0;")
        lay.addWidget(self.lbl_status)

        lay.addStretch()

    # ── 内部操作（每次操作后统一 _commit） ───────────────────────────────────

    def _add_line(self):
        n1 = self.inp_normal1.value()
        n2 = self.inp_normal2.value()
        if np.linalg.norm(n1) < 1e-9 or np.linalg.norm(n2) < 1e-9:
            self._set_status("⚠  法向量不能为零向量", "#ff7766")
            return
        self._lines.append(LineWithNormals(
            start=self.inp_start.value(),
            end=self.inp_end.value(),
            normal1=n1, normal2=n2,
        ))
        self._commit(f"已添加，共 {len(self._lines)} 条线段")

    def _delete_selected(self):
        row = self.line_list.currentRow()
        if 0 <= row < len(self._lines):
            self._lines.pop(row)
            self._commit(f"已删除，剩余 {len(self._lines)} 条")

    def _clear_lines(self):
        self._lines.clear()
        self._commit("已清空", color="#ffaa66")

    def _paste_values(self):
        """从剪贴板解析12个数字填入输入框（起点+法向1+终点+法向2）。"""
        text = QApplication.clipboard().text()
        nums = re.findall(r'-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?', text)
        if len(nums) < 12:
            self._set_status(f"⚠ 需12个数字，当前仅 {len(nums)} 个", "#ff7766")
            return
        try:
            v = [float(x) for x in nums[:12]]
        except ValueError:
            self._set_status("⚠ 数字格式错误", "#ff7766")
            return
        self.inp_start.set_value(v[0], v[1], v[2])
        self.inp_normal1.set_value(v[3], v[4], v[5])
        self.inp_end.set_value(v[6], v[7], v[8])
        self.inp_normal2.set_value(v[9], v[10], v[11])
        self._set_status("✓ 已粘贴", "#88ccaa")

    def _on_mode_changed(self, connect: bool):
        self.sig_connect_mode_changed.emit(connect)

    def _load_preset(self):
        self._lines = [
            LineWithNormals([0,0,0], [0,5,0], [0,0,1], [1,0,0]),
            LineWithNormals([0,0,0], [5,0,0], [0,0,1], [0,1,0]),
            LineWithNormals([0,0,0], [0,0,5], [1,0,0], [0,1,0]),
            LineWithNormals([5,0,0], [5,0,5], [-1,0,0], [0,1,0]),
            LineWithNormals([5,0,0], [5,5,0], [-1,0,0], [0,0,1]),
        ]
        self._commit("已载入默认 5 条线段")

    # ── 统一提交：刷新列表 + 发射信号 ────────────────────────────────────────

    def _commit(self, status_text: str = "", color: str = "#88ccaa"):
        """刷新列表显示，并把最新的线段列表发射给主窗口重新渲染。"""
        self._refresh_list()
        if status_text:
            self._set_status(status_text, color)
        # 发射给主窗口：空列表 → 仅清空；>=2 条 → 清空后重新生成
        self.sig_lines_changed.emit(list(self._lines))

    def _refresh_list(self):
        self.line_list.clear()
        for i, ln in enumerate(self._lines):
            s, e = ln.start, ln.end
            text = (f"L{i+1}  ({s[0]:.1f},{s[1]:.1f},{s[2]:.1f})"
                    f"→({e[0]:.1f},{e[1]:.1f},{e[2]:.1f})")
            item = QListWidgetItem(text)
            item.setToolTip(
                f"起点: {ln.start}\n终点: {ln.end}\n"
                f"法向1: {ln.normal1}\n法向2: {ln.normal2}"
            )
            item.setForeground(QColor("#a0c8ff"))
            self.line_list.addItem(item)

    def highlight_line(self, idx: int):
        """视图 hover 联动：高亮列表中对应行，-1 表示取消高亮。"""
        if idx < 0:
            self.line_list.clearSelection()
            self.line_list.setCurrentRow(-1)
        elif 0 <= idx < self.line_list.count():
            self.line_list.setCurrentRow(idx)

    def _set_status(self, text: str, color: str = "#88ccaa"):
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(f"color:{color}; font-size:11px; padding:2px 0;")
