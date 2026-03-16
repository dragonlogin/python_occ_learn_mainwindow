"""
panels/settings_panel.py  ── 软件设置面板（Tab 6）

职责：
  - 字体大小快捷切换（小 / 中 / 大）
  - "自定义…" 按钮弹出 FontSizeDialog，精确设置 8‥20 pt
  - 发射 sig_font_changed(int) 信号，主窗口监听后刷新全局 QSS
"""

from PyQt5.QtCore    import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QDialog, QDialogButtonBox,
    QSlider, QSpinBox, QFrame,
)
from utils.helpers import make_divider, make_section_label


# ─────────────────────────────────────────────────────────────────────────────
#  自定义字体大小弹窗
# ─────────────────────────────────────────────────────────────────────────────

class FontSizeDialog(QDialog):
    """
    弹出一个独立窗口：
      - 滑条 + 数字输入框双向联动
      - 实时预览文字
      - OK / 取消
    """

    def __init__(self, current_size: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("自定义字体大小")
        self.setFixedSize(360, 240)
        self.setWindowFlags(
            Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint
        )
        self.setStyleSheet("""
            QDialog {
                background: #13132a;
                border: 1px solid #252548;
                border-radius: 10px;
            }
            QLabel {
                color: #c0c0e0;
                font-size: 12px;
            }
            QSlider::groove:horizontal {
                background: #252548;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #7eb8f7;
                width: 16px; height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #7eb8f7;
                border-radius: 2px;
            }
            QSpinBox {
                background: #1e1e3a;
                border: 1px solid #303060;
                border-radius: 5px;
                color: #c0c0e0;
                padding: 4px 8px;
                font-size: 13px;
                min-width: 54px;
            }
            QDialogButtonBox QPushButton {
                background: #1e1e3a;
                color: #b0b0d0;
                border: 1px solid #303060;
                border-radius: 6px;
                padding: 6px 22px;
                font-size: 12px;
                min-width: 72px;
            }
            QDialogButtonBox QPushButton:hover {
                background: #282850;
                color: #ffffff;
                border-color: #5055aa;
            }
            QDialogButtonBox QPushButton:default {
                background: #1a3060;
                border-color: #3060cc;
                color: #7eb8f7;
            }
            QDialogButtonBox QPushButton:default:hover {
                background: #1e408a;
                color: #aad4ff;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(14)

        # 标题行
        title = QLabel("字体大小")
        title.setStyleSheet(
            "color:#7eb8f7; font-size:14px; font-weight:700; letter-spacing:0.5px;")
        root.addWidget(title)

        # 滑条 + 数字 行
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(12)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(8, 20)
        self._slider.setValue(current_size)
        self._slider.setTickInterval(1)

        self._spin = QSpinBox()
        self._spin.setRange(8, 20)
        self._spin.setValue(current_size)
        self._spin.setSuffix(" pt")

        ctrl_row.addWidget(self._slider, stretch=1)
        ctrl_row.addWidget(self._spin)
        root.addLayout(ctrl_row)

        # 范围标注
        range_row = QHBoxLayout()
        lbl_min = QLabel("8 pt")
        lbl_min.setStyleSheet("color:#404070; font-size:10px;")
        lbl_max = QLabel("20 pt")
        lbl_max.setStyleSheet("color:#404070; font-size:10px;")
        lbl_max.setAlignment(Qt.AlignRight)
        range_row.addWidget(lbl_min)
        range_row.addWidget(lbl_max)
        root.addLayout(range_row)

        # 分隔线
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#252548;")
        root.addWidget(sep)

        # 预览文字
        self._preview = QLabel("预览：OCC Analyzer  形体  距离  碰撞  测量")
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setStyleSheet(
            f"color:#e0e0ff; font-size:{current_size}px; padding:6px 0;")
        root.addWidget(self._preview)

        # OK / 取消
        btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        # 联动
        self._slider.valueChanged.connect(self._on_slider)
        self._spin.valueChanged.connect(self._on_spin)

    # ── 联动 ──────────────────────────────────────────────────────────────────

    def _on_slider(self, v: int):
        self._spin.blockSignals(True)
        self._spin.setValue(v)
        self._spin.blockSignals(False)
        self._update_preview(v)

    def _on_spin(self, v: int):
        self._slider.blockSignals(True)
        self._slider.setValue(v)
        self._slider.blockSignals(False)
        self._update_preview(v)

    def _update_preview(self, size: int):
        self._preview.setStyleSheet(
            f"color:#e0e0ff; font-size:{size}px; padding:6px 0;")

    def selected_size(self) -> int:
        return self._spin.value()


# ─────────────────────────────────────────────────────────────────────────────
#  设置面板
# ─────────────────────────────────────────────────────────────────────────────

_PRESETS = [
    ("小",   11),
    ("中",   13),
    ("大",   15),
]


class SettingsPanel(QWidget):
    """
    Signals:
        sig_font_changed (int)  新字体大小（px）
    """

    sig_font_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_size = 12
        self._build_ui()

    # ── UI 构建 ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(6)

        # ── 字体大小 ──────────────────────────────────────────────────────────
        lay.addWidget(make_section_label("字体大小"))

        # 三个快捷档位
        preset_grid = QGridLayout()
        preset_grid.setSpacing(5)
        self._preset_btns = []
        for idx, (label, size) in enumerate(_PRESETS):
            btn = QPushButton(f"{label}（{size} pt）")
            btn.setObjectName("add")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, s=size: self._apply_size(s))
            preset_grid.addWidget(btn, 0, idx)
            self._preset_btns.append((btn, size))
        lay.addLayout(preset_grid)

        # 自定义按钮
        btn_custom = QPushButton("✎  自定义大小…")
        btn_custom.setObjectName("imp")
        btn_custom.clicked.connect(self._open_custom_dialog)
        lay.addWidget(btn_custom)

        # 当前值显示
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("当前："))
        self._lbl_cur = QLabel(f"{self._current_size} pt")
        self._lbl_cur.setStyleSheet(
            "color:#e0e0ff; font-size:13px; font-weight:600;")
        size_row.addWidget(self._lbl_cur)
        size_row.addStretch()
        lay.addLayout(size_row)

        lay.addWidget(make_divider())

        # ── 界面 ──────────────────────────────────────────────────────────────
        lay.addWidget(make_section_label("界面"))

        btn_reset = QPushButton("↺  恢复默认设置")
        btn_reset.clicked.connect(self._reset_defaults)
        lay.addWidget(btn_reset)

        lay.addStretch()

        # 初始高亮中档
        self._apply_size(12, silent=True)

    # ── 内部操作 ──────────────────────────────────────────────────────────────

    def _apply_size(self, size: int, silent: bool = False):
        self._current_size = size
        self._lbl_cur.setText(f"{size} pt")
        # 更新按钮选中状态
        for btn, s in self._preset_btns:
            btn.setChecked(s == size)
        if not silent:
            self.sig_font_changed.emit(size)

    def _open_custom_dialog(self):
        dlg = FontSizeDialog(self._current_size, parent=self)
        # 居中于主窗口
        if self.window():
            geo = self.window().geometry()
            dlg.move(
                geo.x() + (geo.width()  - dlg.width())  // 2,
                geo.y() + (geo.height() - dlg.height()) // 2,
            )
        if dlg.exec_() == QDialog.Accepted:
            self._apply_size(dlg.selected_size())

    def _reset_defaults(self):
        self._apply_size(12)
