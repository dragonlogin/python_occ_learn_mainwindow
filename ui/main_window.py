"""
ui/main_window.py  ── 主窗口

布局：
  ┌─── RibbonTabBar（38px，全宽）────────────────────────────────────┐
  │  OCC Analyzer  v1.0  │ [形体] [距离] [碰撞] [测量] [线框] [设置]  │
  ├─── sidebar（280px）──┬── viewport ──────────────────────────────┤
  │  QStackedWidget      │  状态栏（30px）                           │
  │  ← 当前 Tab 的面板   │  3D View                                  │
  └──────────────────────┴──────────────────────────────────────────┘

扩展：
  - 新增 Tab：在 _build_sidebar() 向 stack 添加页面，并在
    ribbon_tab_bar.py 的 _TAB_LABELS 添加名称。
  - 新增体素：在 _PRIMITIVES_FACTORIES 注册工厂函数。
"""

import os
from typing import List

from OCC.Core.AIS        import AIS_Shape
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCC.Core.BRepPrimAPI import (
    BRepPrimAPI_MakeBox, BRepPrimAPI_MakeSphere,
    BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeCone,
)
from OCC.Core.TopoDS  import TopoDS_Shape
from OCC.Core.gp      import gp_Pnt, gp_Vec
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

from PyQt5.QtCore    import QTimer, Qt, QSettings
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QSizePolicy, QMessageBox, QStackedWidget,
)

from core.shape_item import ShapeItem
from core.importer   import import_file
from core.analysis   import DistanceResult, CollisionEntry
from viewer.occ_viewer      import OCCViewer
from panels.shapes_panel    import ShapesPanel
from panels.distance_panel  import DistancePanel
from panels.collision_panel import CollisionPanel
from panels.measure_panel   import MeasurePanel
from panels.line_box_panel  import LineBoxPanel
from typing import List as _List  # avoid shadowing below
from panels.settings_panel  import SettingsPanel
from ui.ribbon_tab_bar      import RibbonTabBar
from utils.helpers   import qty_color
from ui.styles       import build_qss

try:
    from create_box import process_multiple_lines
except ImportError:
    from core.create_box import process_multiple_lines

# ── 体素颜色池 ────────────────────────────────────────────────────────────────
_COLORS = [
    (0.30, 0.60, 1.00), (1.00, 0.50, 0.20),
    (0.25, 0.85, 0.45), (0.90, 0.30, 0.55),
    (0.85, 0.80, 0.20), (0.60, 0.30, 0.90),
    (0.20, 0.80, 0.90), (0.90, 0.50, 0.10),
]

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
        self._linebox_extra_ais: list = []
        self._linebox_items: List[ShapeItem] = []

        # 从本地配置读取上次保存的字体大小，默认 12
        self._settings = QSettings("OCCAnalyzer", "Preferences")
        self._font_size = int(self._settings.value("font_size", 12))

        self._build_ui()
        # 用持久化的字体大小初始化（同时同步设置面板的选中状态）
        self._apply_font(self._font_size, silent=True)
        self.panel_settings._apply_size(self._font_size, silent=True)
        QTimer.singleShot(50, self._init_scene)

    # ── UI 构建 ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 1. 顶部 Ribbon Tab 条（全宽）
        self.ribbon = RibbonTabBar()
        self.ribbon.sig_tab_changed.connect(self._on_tab_changed)
        root.addWidget(self.ribbon)

        # 2. 主体（sidebar + viewport 横向）
        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)
        body_lay.addWidget(self._build_sidebar())
        body_lay.addWidget(self._build_viewport(), stretch=1)
        root.addWidget(body, stretch=1)

    # ── 侧边栏（QStackedWidget 承载各面板）───────────────────────────────────

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── 构建各面板 ──────────────────────────────────────────────────────
        self.panel_shapes    = ShapesPanel()
        self.panel_distance  = DistancePanel()
        self.panel_collision = CollisionPanel()
        self.panel_measure   = MeasurePanel()
        self.panel_linebox   = LineBoxPanel()
        self.panel_settings  = SettingsPanel()

        # ── QStackedWidget ──────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.setObjectName("sidebar")   # 继承 sidebar 背景样式
        for panel in (
            self.panel_shapes,
            self.panel_distance,
            self.panel_collision,
            self.panel_measure,
            self.panel_linebox,
            self.panel_settings,
        ):
            self.stack.addWidget(panel)

        lay.addWidget(self.stack)

        # ── 信号连接 ──────────────────────────────────────────────────────
        self.panel_shapes.sig_add_primitive.connect(self._add_primitive)
        self.panel_shapes.sig_import_file.connect(self._import_file)
        self.panel_shapes.sig_delete.connect(self._delete_shape)
        self.panel_shapes.sig_toggle.connect(self._toggle_shape)
        self.panel_shapes.sig_select.connect(self.panel_measure.select_item)

        self.panel_distance.sig_pair_changed.connect(self._on_pair_changed)
        self.panel_collision.spin.valueChanged.connect(
            lambda _: self.viewer.run_analysis()
        )
        self.panel_linebox.sig_lines_changed.connect(self._on_linebox_changed)
        self.panel_settings.sig_font_changed.connect(self._apply_font)

        return sidebar

    # ── 视口 ─────────────────────────────────────────────────────────────────

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

    # ── Tab 切换 ──────────────────────────────────────────────────────────────

    def _on_tab_changed(self, idx: int):
        self.stack.setCurrentIndex(idx)

    # ── 初始场景 ──────────────────────────────────────────────────────────────

    def _init_scene(self):
        self.viewer.InitDriver()
        self.viewer._display.set_bg_gradient_color([10, 10, 20], [22, 22, 45])
        self._refresh_all()

    # ── 形体管理 ──────────────────────────────────────────────────────────────

    def _make_item(self, topo: TopoDS_Shape, name: str) -> ShapeItem:
        r, g, b = _COLORS[self._color_idx % len(_COLORS)]
        self._color_idx += 1
        ais = AIS_Shape(topo)
        ais.SetColor(qty_color(r, g, b))
        return ShapeItem(name=name, ais=ais, topo=topo, color=(r, g, b))

    def _register_item(self, item: ShapeItem):
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
            QMessageBox.warning(self, "不支持的格式", str(e)); return
        except Exception as e:
            QMessageBox.critical(self, "导入错误", str(e)); return
        if topo is None:
            QMessageBox.warning(self, "导入失败", f"文件读取失败:\n{path}"); return
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

    # ── 线框渲染管理 ──────────────────────────────────────────────────────────

    def _clear_linebox_render(self):
        """移除上一次线框生成的所有 AIS 对象（面 + 法向量 + 原始线段）。"""
        ctx = self.viewer._display.Context

        # 1. 移除法向量箭头和原始线段（不在 _items 中）
        for ais in self._linebox_extra_ais:
            ctx.Remove(ais, False)
        self._linebox_extra_ais.clear()

        # 2. 移除线框生成的面（在 _items 中，需同步删除）
        for item in self._linebox_items:
            ctx.Remove(item.ais, False)
            if item in self._items:
                self._items.remove(item)
        self._linebox_items.clear()

        ctx.UpdateCurrentViewer()

    def _on_linebox_changed(self, lines: list):
        """线段列表变化时调用：先清空旧渲染，再按新列表重建。"""
        # 总是先清空
        self._clear_linebox_render()

        # 线段不足 2 条时只清空，不生成
        if len(lines) < 2:
            self._refresh_all()
            if not lines:
                self.panel_linebox._set_status("已清空", "#ffaa66")
            return

        # 生成新几何体
        try:
            faces = process_multiple_lines(lines)
        except Exception as e:
            QMessageBox.critical(self, "生成错误", str(e))
            return

        if not faces:
            self.panel_linebox._set_status("⚠ 无法生成有效面，请检查法向量", "#ff7766")
            self._refresh_all()
            return

        ctx = self.viewer._display.Context
        face_colors = [
            (1.0,0.3,0.3),(0.3,1.0,0.4),(0.3,0.5,1.0),
            (1.0,0.9,0.2),(1.0,0.3,0.9),(0.2,0.9,0.9),(0.7,0.7,0.7),
        ]

        for i, fi in enumerate(faces):
            r, g, b = face_colors[i % len(face_colors)]
            color = Quantity_Color(r, g, b, Quantity_TOC_RGB)

            # 面 → ShapeItem，加入 _items 和 _linebox_items
            name = f"Face_{len(self._items) + 1}"
            item = self._make_item(fi['face'], name)
            item.color = (r, g, b)
            item.ais.SetColor(color)
            self._register_item(item)
            self._linebox_items.append(item)   # ← 记录，便于下次清除

            # 法向量箭头 → extra AIS
            nv = AIS_Shape(fi['normal_vector'])
            nv.SetColor(color)
            ctx.Display(nv, False)
            self._linebox_extra_ais.append(nv)  # ← 记录

        # 原始线段（白色） → extra AIS
        white = Quantity_Color(1, 1, 1, Quantity_TOC_RGB)
        for line in lines:
            edge = BRepBuilderAPI_MakeEdge(
                gp_Pnt(float(line.start[0]), float(line.start[1]), float(line.start[2])),
                gp_Pnt(float(line.end[0]),   float(line.end[1]),   float(line.end[2])),
            ).Edge()
            ea = AIS_Shape(edge)
            ea.SetColor(white)
            ctx.Display(ea, False)
            self._linebox_extra_ais.append(ea)  # ← 记录

        ctx.UpdateCurrentViewer()
        self.viewer._display.FitAll()
        self._refresh_all()

        msg = f"✓ 已生成 {len(faces)} 个面"
        self.panel_linebox._set_status(msg, "#88ffcc")
        self._set_status(f"✓ 线框：{len(lines)} 条线段 → {len(faces)} 个面", "#44ddcc")

    # ── 字体 ─────────────────────────────────────────────────────────────────

    def _apply_font(self, size: int, silent: bool = False):
        self._font_size = size
        self.setStyleSheet(build_qss(size))
        if not silent:
            self._settings.setValue("font_size", size)

    # ── 刷新 ─────────────────────────────────────────────────────────────────

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
        # 视口点击时跳回形体 Tab
        self.ribbon.set_tab(0)
        self.stack.setCurrentIndex(0)

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
