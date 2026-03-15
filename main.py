"""
main.py  ── 程序入口

用法：
    python main.py

依赖：
    pip install pythonocc-core PyQt5
    或：conda install -c conda-forge pythonocc-core pyqt
"""

import sys

# ── Qt 后端自动探测 ───────────────────────────────────────────────────────────
from OCC.Display.backend import load_backend
_loaded = False
for _backend in ["pyqt5", "pyqt6", "pyside2", "pyside6"]:
    try:
        load_backend(_backend)
        _loaded = True
        break
    except Exception:
        pass

if not _loaded:
    print(
        "[错误] 未找到可用的 Qt 后端。\n"
        "请运行以下命令之一：\n"
        "  pip install PyQt5\n"
        "  conda install -c conda-forge pyqt\n"
    )
    sys.exit(1)

from PyQt5.QtWidgets import QApplication
from ui.main_window  import MainWindow
from ui.styles       import QSS


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)

    win = MainWindow()
    win.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
