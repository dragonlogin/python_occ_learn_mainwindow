"""
ui/main_window.py  ── 主窗口

负责：
  1. 组装侧边栏 Tabs 与 3D 视口
  2. 连接所有 Panel 信号
  3. 管理 ShapeItem 列表（增 / 删 / 隐）
  4. 创建初始场景

扩展指引：
  - 新增 Tab：在 _build_sidebar() 中 addTab 即可，无需改动其他模块。
  - 新增体素：在 _PRIMITIVES_FACTORIES 字典中注册工厂函数。
  - 支持撤销：在 _add_item / _delete_shape 前后维护 command stack。
"""

import os
from typing import List, Optional

from OCC.Core.AIS import AIS_Shape
from OCC.Core.BRepPrimAPI import (
    BRepPrimAPI_MakeBox, BRepPrimAPI_MakeSphere,
    BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeCone,
)
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.gp import gp_Vec

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QFrame, QTabWidget, QSizePolicy, QMessageBox,
)

from core.shape_item import ShapeItem
from core.importer   import import_file
from core.analysis   import DistanceResult, CollisionEntry
from viewer.occ_viewer import OCCViewer
from panels.shapes_panel    import ShapesPanel
from panels.distance_panel  import DistancePanel
from panels.collision_panel import CollisionPanel
from panels.measure_panel   import MeasurePanel
from utils.helpers import qty_color

# ── 体素颜色池 ────────────────────────────────────────────────────────────────
_COLORS = [
    (0.30, 0.60, 1.00), (1.00, 0.50, 0.20),
    (0.25, 0.85, 0.45), (0.90, 0.30, 0.55),
    (0.85, 0.80, 0.20), (0.60, 0.30, 0.90),
    (0.20, 0.80, 0.90), (0.90, 0.50, 0.10),
]

# ── 体素工厂（扩展：在此注册新体素）────────────────────────────────────────────
_PRIMITIVES_FACTORIES = {
    "Box":      lambda: BRepPrimAPI_MakeBox(40, 30, 20).Shape(),
    "Sphere":   lambda: BRepPrimAPI_MakeSphere(20).Shape(),
    "Cylinder": lambda: BRepPrimAPI_MakeCylinder(15, 40).Shape(),
    "Cone":     lambda: BRepPrimAPI_MakeCone(15, 5, 40).Shape(),
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OCC Analyzer  v1.0")
        self.resize(1300, 820)

        self._items: List[ShapeItem] = []
        self._color_idx = 0

        self._build_ui()
        QTimer.singleShot(50, self._init_scene)

    # ── UI 构建 ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_viewport(), stretch=1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # App 标题栏
        title_bar = QWidget()
        title_bar.setFixedHeight(48)
        title_bar.setStyleSheet(
            "background:#0d0d1c; border-bottom:1px solid #202040;")
        tbl = QHBoxLayout(title_bar)
        tbl.setContentsMargins(14, 0, 14, 0)
        app_title = QLabel("OCC Analyzer")
        app_title.setStyleSheet(
            "color:#7eb8f7; font-size:15px; font-weight:700; letter-spacing:1px;")
        ver = QLabel("v1.0")
        ver.setStyleSheet("color:#404070; font-size:11px;")
        tbl.addWidget(app_title)
        tbl.addStretch()
        tbl.addWidget(ver)
        lay.addWidget(title_bar)

        # Tabs
        self.tabs = QTabWidget()
        self.panel_shapes    = ShapesPanel()
        self.panel_distance  = DistancePanel()
        self.panel_collision = CollisionPanel()
        self.panel_measure   = MeasurePanel()
        self.tabs.addTab(self.panel_shapes,    "形体")
        self.tabs.addTab(self.panel_distance,  "距离")
        self.tabs.addTab(self.panel_collision, "碰撞")
        self.tabs.addTab(self.panel_measure,   "测量")
        lay.addWidget(self.tabs)

        # 信号
        self.panel_shapes.sig_add_primitive.connect(self._add_primitive)
        self.panel_shapes.sig_import_file.connect(self._import_file)
        self.panel_shapes.sig_delete.connect(self._delete_shape)
        self.panel_shapes.sig_toggle.connect(self._toggle_shape)
        self.panel_shapes.sig_select.connect(self.panel_measure.select_item)

        self.panel_distance.sig_pair_changed.connect(self._on_pair_changed)
        self.panel_collision.spin.valueChanged.connect(
            lambda _: self.viewer.run_analysis()
        )
        return sidebar

    def _build_viewport(self) -> QWidget:
        right = QWidget()
        lay   = QVBoxLayout(right)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.status_bar = QLabel(
            "就绪  ·  左键 点击选中 / 拖拽移动  ·  右键 旋转  ·  中键 平移  ·  滚轮 缩放")
        self.status_bar.setFixedHeight(30)
        self.status_bar.setStyleSheet(
            "background:#0d0d1c; color:#404070; font-size:11px;"
            "padding:0 14px; border-bottom:1px solid #1a1a30;")
        lay.addWidget(self.status_bar)

        self.viewer = OCCViewer(right)
        self.viewer.sig_distance.connect(self._on_distance)
        self.viewer.sig_collision.connect(self._on_collision)
        self.viewer.sig_selected.connect(self._on_viewer_select)
        lay.addWidget(self.viewer, stretch=1)
        return right

    # ── 初始场景 ──────────────────────────────────────────────────────────────

    def _init_scene(self):
        self.viewer.InitDriver()
        self.viewer._display.set_bg_gradient_color([10, 10, 20], [22, 22, 45])

        box_topo = BRepPrimAPI_MakeBox(40, 30, 20).Shape()
        box_item = self._make_item(box_topo, "Box_1")

        sph_topo = BRepPrimAPI_MakeSphere(18).Shape()
        sph_item = self._make_item(sph_topo, "Sphere_1")
        sph_item.offset = gp_Vec(110, 0, 0)

        for it in [box_item, sph_item]:
            self._register_item(it)

        self.viewer._display.FitAll()
        self._refresh_all()

    # ── 形体管理 ──────────────────────────────────────────────────────────────

    def _make_item(self, topo: TopoDS_Shape, name: str) -> ShapeItem:
        r, g, b = _COLORS[self._color_idx % len(_COLORS)]
        self._color_idx += 1
        ais = AIS_Shape(topo)
        ais.SetColor(qty_color(r, g, b))
        return ShapeItem(name=name, ais=ais, topo=topo, color=(r, g, b))

    def _register_item(self, item: ShapeItem):
        """将 ShapeItem 显示到视口并加入列表。"""
        ctx = self.viewer._display.Context
        ctx.Display(item.ais, False)
        ctx.SetTransparency(item.ais, 0.25, False)
        item.apply_offset(ctx)
        self._items.append(item)
        ctx.UpdateCurrentViewer()
        self.viewer.set_items(self._items)

    def _add_primitive(self, prim: str):
        factory = _PRIMITIVES_FACTORIES.get(prim)
        if not factory:
            return
        try:
            topo = factory()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"创建形体失败:\n{e}")
            return

        name = f"{prim}_{len(self._items) + 1}"
        item = self._make_item(topo, name)
        item.offset = gp_Vec(len(self._items) * 70, 0, 0)
        self._register_item(item)
        self.viewer._display.FitAll()
        self._refresh_all()
        self._set_status(f"✓ 已添加 {name}", "#88ee88")

    def _import_file(self, path: str):
        try:
            topo = import_file(path)
        except ValueError as e:
            QMessageBox.warning(self, "不支持的格式", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "导入错误", str(e))
            return

        if topo is None:
            QMessageBox.warning(self, "导入失败",
                                f"文件读取失败，请检查文件格式:\n{path}")
            return

        name = os.path.splitext(os.path.basename(path))[0]
        item = self._make_item(topo, name)
        self._register_item(item)
        self.viewer._display.FitAll()
        self._refresh_all()
        self._set_status(f"✓ 已导入: {name}", "#88ee88")

    def _delete_shape(self, idx: int):
        if not (0 <= idx < len(self._items)):
            return
        item = self._items.pop(idx)
        ctx  = self.viewer._display.Context
        ctx.Remove(item.ais, False)
        if self.viewer._dist_line_ais:
            ctx.Remove(self.viewer._dist_line_ais, False)
            self.viewer._dist_line_ais = None
        ctx.UpdateCurrentViewer()
        self.viewer.set_items(self._items)
        self._refresh_all()
        self._set_status(f"已删除: {item.name}", "#ffaa44")

    def _toggle_shape(self, idx: int):
        if not (0 <= idx < len(self._items)):
            return
        item = self._items[idx]
        ctx  = self.viewer._display.Context
        item.visible = not item.visible
        if item.visible:
            ctx.Display(item.ais, True)
        else:
            ctx.Erase(item.ais, True)
        self.panel_shapes.refresh(self._items)

    # ── 刷新所有面板 ──────────────────────────────────────────────────────────

    def _refresh_all(self):
        self.panel_shapes.refresh(self._items)
        self.panel_distance.refresh_combos(self._items)
        self.panel_collision.update_collisions([], self._items)
        self.panel_measure.refresh_combos(self._items)
        self.viewer.run_analysis()

    # ── 信号处理 ──────────────────────────────────────────────────────────────

    def _on_distance(self, result: DistanceResult):
        self.panel_distance.update_result(result)
        d = result.distance
        if d < 0.01:
            self._set_status("⚠  距离: 接触 / 重叠", "#ff5544")
        else:
            self._set_status(f"距离: {d:.5f}", "#88ee88")

    def _on_collision(self, entries: List[CollisionEntry]):
        self.panel_collision.update_collisions(entries, self._items)

    def _on_viewer_select(self, idx: int):
        self.panel_shapes.select_row(idx)
        self.panel_measure.select_item(idx)
        self.tabs.setCurrentIndex(0)

    def _on_pair_changed(self, i: int, j: int):
        if i != j:
            self.viewer.dist_pair = (i, j)
            self.viewer.run_analysis()

    def _set_status(self, text: str, color: str = "#404070"):
        self.status_bar.setText(text)
        self.status_bar.setStyleSheet(
            f"background:#0d0d1c; color:{color}; font-size:11px;"
            f"padding:0 14px; border-bottom:1px solid #1a1a30;"
        )
