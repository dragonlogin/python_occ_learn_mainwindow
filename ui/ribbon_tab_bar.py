"""
ui/ribbon_tab_bar.py  ── 顶部 Ribbon Tab 条（仅标题 + 切换按钮）

高度固定 38px，横跨全部宽度。
点击 Tab 按钮后发射 sig_tab_changed(int)，主窗口据此切换左侧 QStackedWidget。
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


_TAB_LABELS = ["形体", "距离", "碰撞", "测量", "线框", "⚙ 设置"]


class RibbonTabBar(QWidget):
    """
    Signals:
        sig_tab_changed(int)  用户点击的 Tab 索引
    """

    sig_tab_changed = pyqtSignal(int)

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
        lay.addSpacing(24)

        # 竖分隔线
        sep = QWidget()
        sep.setFixedSize(1, 20)
        sep.setStyleSheet("background:#252548;")
        lay.addWidget(sep)
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

        # 默认选中第 0 个
        self._set_active(0)

    def _on_click(self, idx: int):
        self._set_active(idx)
        self.sig_tab_changed.emit(idx)

    def _set_active(self, idx: int):
        for i, btn in enumerate(self._btns):
            btn.setStyleSheet(_TAB_ACTIVE if i == idx else _TAB_INACTIVE)

    def set_tab(self, idx: int):
        """从外部切换（不发射信号）。"""
        self._set_active(idx)
