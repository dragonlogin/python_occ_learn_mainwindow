"""
ui/ribbon_tab_bar.py  ── 顶部 Ribbon Tab 条（标题 + 切换按钮 + 撤销/重做）

高度固定 38px，横跨全部宽度。
"""

from PyQt5.QtCore    import pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton


_TAB_ACTIVE = """
QPushButton {
    background: #181830;
    color: #7eb8f7;
    border: none;
    border-bottom: 2px solid #7eb8f7;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 0 18px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.3px;
}
"""

_TAB_INACTIVE = """
QPushButton {
    background: transparent;
    color: #505080;
    border: none;
    border-bottom: 2px solid transparent;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 0 18px;
    font-size: 12px;
    font-weight: 400;
}
QPushButton:hover {
    color: #9090bb;
    background: #141428;
}
"""

_ICON_BTN = """
QPushButton {
    background: transparent;
    color: #505080;
    border: none;
    border-radius: 4px;
    padding: 0 8px;
    font-size: 13px;
    min-width: 28px;
}
QPushButton:hover:enabled  { color: #aabbff; background: #1a1a38; }
QPushButton:pressed:enabled { color: #7eb8f7; }
QPushButton:disabled        { color: #2a2a48; }
"""

_TAB_LABELS = ["形体", "距离", "碰撞", "测量", "线框", "⚙ 设置"]


class RibbonTabBar(QWidget):
    """
    Signals:
        sig_tab_changed(int)  Tab 切换
        sig_undo()            点击撤销按钮
        sig_redo()            点击重做按钮
    """

    sig_tab_changed = pyqtSignal(int)
    sig_undo        = pyqtSignal()
    sig_redo        = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self.setObjectName("ribbonTabBar")
        self.setStyleSheet(
            "#ribbonTabBar {"
            "  background: #0d0d1c;"
            "  border-bottom: 1px solid #252548;"
            "}"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(0)

        # 标题
        title = QLabel("OCC Analyzer")
        title.setStyleSheet(
            "color:#7eb8f7; font-size:13px; font-weight:700; letter-spacing:1px;")
        ver = QLabel(" v1.0")
        ver.setStyleSheet("color:#303060; font-size:10px;")
        lay.addWidget(title)
        lay.addWidget(ver)
        lay.addSpacing(16)

        # 竖分隔线
        sep1 = QWidget(); sep1.setFixedSize(1, 20)
        sep1.setStyleSheet("background:#252548;")
        lay.addWidget(sep1)
        lay.addSpacing(4)

        # ── 撤销 / 重做按钮 ────────────────────────────────────────────────
        self.btn_undo = QPushButton("↩")
        self.btn_undo.setFixedHeight(38)
        self.btn_undo.setStyleSheet(_ICON_BTN)
        self.btn_undo.setToolTip("撤销  Ctrl+Z")
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(self.sig_undo)
        lay.addWidget(self.btn_undo)

        self.btn_redo = QPushButton("↪")
        self.btn_redo.setFixedHeight(38)
        self.btn_redo.setStyleSheet(_ICON_BTN)
        self.btn_redo.setToolTip("重做  Ctrl+Y")
        self.btn_redo.setEnabled(False)
        self.btn_redo.clicked.connect(self.sig_redo)
        lay.addWidget(self.btn_redo)

        lay.addSpacing(4)
        sep2 = QWidget(); sep2.setFixedSize(1, 20)
        sep2.setStyleSheet("background:#252548;")
        lay.addWidget(sep2)
        lay.addSpacing(8)

        # Tab 按钮
        self._btns: list[QPushButton] = []
        for i, name in enumerate(_TAB_LABELS):
            btn = QPushButton(name)
            btn.setFixedHeight(38)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._on_click(idx))
            self._btns.append(btn)
            lay.addWidget(btn)

        lay.addStretch()
        self._set_active(0)

    def _on_click(self, idx: int):
        self._set_active(idx)
        self.sig_tab_changed.emit(idx)

    def _set_active(self, idx: int):
        for i, btn in enumerate(self._btns):
            btn.setStyleSheet(_TAB_ACTIVE if i == idx else _TAB_INACTIVE)

    def set_tab(self, idx: int):
        self._set_active(idx)

    def update_undo_redo(self, can_undo: bool, can_redo: bool,
                         undo_text: str = "", redo_text: str = ""):
        """由主窗口在 sig_stack_changed 后调用，刷新按钮状态。"""
        self.btn_undo.setEnabled(can_undo)
        self.btn_redo.setEnabled(can_redo)
        self.btn_undo.setToolTip(f"{undo_text}  (Ctrl+Z)" if undo_text else "撤销  Ctrl+Z")
        self.btn_redo.setToolTip(f"{redo_text}  (Ctrl+Y)" if redo_text else "重做  Ctrl+Y")
