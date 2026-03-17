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

"""
ui/main_window.py  ── 主窗口（含 Undo / Redo）
"""

import os
from typing import List

import numpy as np

from OCC.Core.AIS        import AIS_Shape, AIS_TextLabel
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
    QShortcut,
)
from PyQt5.QtGui import QKeySequence

from core.shape_item import ShapeItem
from core.importer   import import_file
from core.analysis   import DistanceResult, CollisionEntry
from core.commands   import (
    AppContext, AddShapeCommand, DeleteShapeCommand,
    ToggleVisibilityCommand, LineboxUpdateCommand, ChangeFontCommand,
)
from core.command_stack import CommandStack
from viewer.occ_viewer      import OCCViewer
from panels.shapes_panel    import ShapesPanel
from panels.distance_panel  import DistancePanel
from panels.collision_panel import CollisionPanel
from panels.measure_panel   import MeasurePanel
from panels.line_box_panel  import LineBoxPanel
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

_FACE_COLORS = [
    (1.0,0.3,0.3),(0.3,1.0,0.4),(0.3,0.5,1.0),
    (1.0,0.9,0.2),(1.0,0.3,0.9),(0.2,0.9,0.9),(0.7,0.7,0.7),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OCC Analyzer  v1.0")
        self.resize(1300, 820)

        self._items: List[ShapeItem] = []
        self._color_idx = 0
        self._linebox_extra_ais: list = []
        self._linebox_items: List[ShapeItem] = []
        self._last_linebox_lines: list = []
        self._connect_faces: bool = True
        self._show_labels:   bool = True

        # 从本地配置读取上次保存的字体大小，默认 12
        self._settings = QSettings("OCCAnalyzer", "Preferences")
        self._font_size = int(self._settings.value("font_size", 12))

        self.cmd_stack = CommandStack(self)
        self.cmd_stack.sig_stack_changed.connect(self._on_stack_changed)

        self._build_ui()
        self._build_ctx()
        self._build_shortcuts()

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
        self.ribbon.sig_undo.connect(self.cmd_stack.undo)
        self.ribbon.sig_redo.connect(self.cmd_stack.redo)
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
        self.panel_linebox.sig_connect_mode_changed.connect(self._on_connect_mode_changed)
        self.panel_linebox.sig_label_visible_changed.connect(self._on_label_visible_changed)
        self.panel_settings.sig_font_changed.connect(self._on_font_changed)

        return sidebar

    # ── 视口 ─────────────────────────────────────────────────────────────────

    def _build_viewport(self) -> QWidget:
        right = QWidget()
        lay   = QVBoxLayout(right)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.status_bar = QLabel(
            "就绪  ·  左键点击选中/拖拽  ·  右键旋转  ·  中键平移  ·  滚轮缩放")
        self.status_bar.setFixedHeight(30)
        self.status_bar.setStyleSheet(
            "background:#0d0d1c; color:#404070; font-size:11px;"
            "padding:0 14px; border-bottom:1px solid #1a1a30;")
        lay.addWidget(self.status_bar)

        self.viewer = OCCViewer(right)
        self.viewer.sig_distance.connect(self._on_distance)
        self.viewer.sig_collision.connect(self._on_collision)
        self.viewer.sig_selected.connect(self._on_viewer_select)
        self.viewer.sig_linebox_hovered.connect(self.panel_linebox.highlight_line)
        lay.addWidget(self.viewer, stretch=1)
        return right

    def _build_ctx(self):
        def _set_linebox_lines(lines):
            self.panel_linebox._lines = list(lines)
            self.panel_linebox._refresh_list()

        self.ctx = AppContext(
            items             = self._items,
            display_item      = self._display_item,
            hide_item         = self._hide_item,
            toggle_item       = self._do_toggle_item,
            refresh_all       = self._refresh_all,
            fit_all           = lambda: self.viewer._display.FitAll(),
            set_status        = self._set_status,
            render_linebox    = self._render_linebox,
            set_linebox_lines = _set_linebox_lines,
            apply_font        = self._apply_font,
            sync_font_panel   = lambda s: self.panel_settings._apply_size(s, silent=True),
            make_item         = self._make_item,
        )

    def _build_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.cmd_stack.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self).activated.connect(self.cmd_stack.redo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self).activated.connect(self.cmd_stack.redo)

    # ── 初始场景 ──────────────────────────────────────────────────────────────

    def _init_scene(self):
        self.viewer.InitDriver()
        self.viewer._display.set_bg_gradient_color([10, 10, 20], [22, 22, 45])
        self._refresh_all()

    # ── 低级渲染原语 ──────────────────────────────────────────────────────────

    def _display_item(self, item: ShapeItem):
        ctx = self.viewer._display.Context
        ctx.Display(item.ais, False)
        ctx.SetTransparency(item.ais, 0.25, False)
        item.apply_offset(ctx)
        ctx.UpdateCurrentViewer()
        self.viewer.set_items(self._items)

    def _hide_item(self, item: ShapeItem):
        ctx = self.viewer._display.Context
        ctx.Remove(item.ais, False)
        if self.viewer._dist_line_ais:
            ctx.Remove(self.viewer._dist_line_ais, False)
            self.viewer._dist_line_ais = None
        ctx.UpdateCurrentViewer()
        self.viewer.set_items(self._items)

    def _do_toggle_item(self, item: ShapeItem):
        item.visible = not item.visible
        ctx = self.viewer._display.Context
        if item.visible:
            ctx.Display(item.ais, True)
        else:
            ctx.Erase(item.ais, True)
        self.panel_shapes.refresh(self._items)

    # ── 形体工厂 ──────────────────────────────────────────────────────────────

    def _make_item(self, topo: TopoDS_Shape, name: str) -> ShapeItem:
        r, g, b = _COLORS[self._color_idx % len(_COLORS)]
        self._color_idx += 1
        ais = AIS_Shape(topo)
        ais.SetColor(qty_color(r, g, b))
        return ShapeItem(name=name, ais=ais, topo=topo, color=(r, g, b))

    # ── 操作 → 命令 ───────────────────────────────────────────────────────────

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
        self.cmd_stack.push(AddShapeCommand(self.ctx, item))

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
        self.cmd_stack.push(AddShapeCommand(self.ctx, item))

    def _delete_shape(self, idx: int):
        if not (0 <= idx < len(self._items)):
            return
        item = self._items[idx]
        self.cmd_stack.push(DeleteShapeCommand(self.ctx, item, idx))

    def _toggle_shape(self, idx: int):
        if not (0 <= idx < len(self._items)):
            return
        self.cmd_stack.push(ToggleVisibilityCommand(self.ctx, self._items[idx]))

    def _on_font_changed(self, new_size: int):
        self.cmd_stack.push(ChangeFontCommand(self.ctx, self._font_size, new_size))

    # ── 线框 ─────────────────────────────────────────────────────────────────

    def _on_linebox_changed(self, new_lines: list):
        old_lines = list(self._last_linebox_lines)
        self._last_linebox_lines = list(new_lines)
        self.cmd_stack.push(LineboxUpdateCommand(self.ctx, old_lines, new_lines))

    def _on_connect_mode_changed(self, connect: bool):
        self._connect_faces = connect
        self._render_linebox(self._last_linebox_lines)

    def _on_label_visible_changed(self, visible: bool):
        self._show_labels = visible
        self._render_linebox(self._last_linebox_lines)

    def _clear_linebox_render(self):
        ctx = self.viewer._display.Context
        for ais in self._linebox_extra_ais:
            ctx.Remove(ais, False)
        self._linebox_extra_ais.clear()
        self.viewer.set_linebox_hover_map([])
        for item in self._linebox_items:
            ctx.Remove(item.ais, False)
            if item in self._items:
                self._items.remove(item)
        self._linebox_items.clear()
        ctx.UpdateCurrentViewer()

    def _render_linebox(self, lines: list):
        self._clear_linebox_render()
        if not lines:
            self._refresh_all()
            return

        ctx = self.viewer._display.Context

        col_line = qty_color(1.0, 1.0, 1.0)          # 线段：白
        col_n1   = qty_color(0.25, 0.90, 0.45)        # 法向1：绿
        col_n2   = qty_color(1.00, 0.60, 0.20)        # 法向2：橙
        col_lbl_seg = qty_color(1.0, 1.0, 0.25)       # 标签：亮黄（线段）
        col_lbl_n1  = qty_color(0.40, 1.0, 0.40)      # 标签：亮绿（法向1）
        col_lbl_n2  = qty_color(1.0, 0.80, 0.20)      # 标签：亮橙（法向2）

        def _normal_len(line) -> float:
            seg_len = float(np.linalg.norm(line.end - line.start))
            return max(1.0, min(5.0, seg_len * 0.3))

        def _make_label(pos: gp_Pnt, text: str, color, height: float = 12.0) -> AIS_TextLabel:
            lbl = AIS_TextLabel()
            lbl.SetText(text)
            lbl.SetPosition(pos)
            lbl.SetColor(color)
            lbl.SetHeight(height)
            return lbl

        # hover 映射：(AIS_Shape边, 线段索引)
        hover_map = []

        for i, line in enumerate(lines):
            # ── 线段本体（保持激活以支持 hover 检测）──
            ea = AIS_Shape(BRepBuilderAPI_MakeEdge(
                gp_Pnt(float(line.start[0]), float(line.start[1]), float(line.start[2])),
                gp_Pnt(float(line.end[0]),   float(line.end[1]),   float(line.end[2])),
            ).Edge())
            ea.SetColor(col_line)
            ea.SetWidth(2.5)
            ctx.Display(ea, False)
            # 不调用 Deactivate —— 保留 hover 探测
            self._linebox_extra_ais.append(ea)
            hover_map.append((ea, i))

            # ── 法向箭头（deactivate，减少拾取噪声）──
            mid  = (line.start + line.end) / 2.0
            nlen = _normal_len(line)
            for normal_arr, col in (
                (np.array(line.normal1, dtype=float), col_n1),
                (np.array(line.normal2, dtype=float), col_n2),
            ):
                mag = np.linalg.norm(normal_arr)
                if mag < 1e-9:
                    continue
                tip = mid + normal_arr / mag * nlen
                na = AIS_Shape(BRepBuilderAPI_MakeEdge(
                    gp_Pnt(float(mid[0]), float(mid[1]), float(mid[2])),
                    gp_Pnt(float(tip[0]), float(tip[1]), float(tip[2])),
                ).Edge())
                na.SetColor(col)
                na.SetWidth(1.5)
                ctx.Display(na, False)
                ctx.Deactivate(na)
                self._linebox_extra_ais.append(na)

            # ── 标签（可通过 checkbox 控制，用 AIS_TextLabel 管理）──
            if self._show_labels:
                seg_len = float(np.linalg.norm(line.end - line.start))

                # 线段起点、终点、长度
                for pos, text in (
                    (gp_Pnt(float(line.start[0]), float(line.start[1]), float(line.start[2])),
                     f"S{i+1}({line.start[0]:.1f},{line.start[1]:.1f},{line.start[2]:.1f})"),
                    (gp_Pnt(float(line.end[0]), float(line.end[1]), float(line.end[2])),
                     f"E{i+1}({line.end[0]:.1f},{line.end[1]:.1f},{line.end[2]:.1f})"),
                    (gp_Pnt(float(mid[0] + 0.15), float(mid[1] + 0.15), float(mid[2])),
                     f"Len:{seg_len:.2f}"),
                ):
                    lbl = _make_label(pos, text, col_lbl_seg)
                    ctx.Display(lbl, False)
                    ctx.Deactivate(lbl)
                    self._linebox_extra_ais.append(lbl)

                # 法向1 标签
                n1_arr = np.array(line.normal1, dtype=float)
                mag1 = np.linalg.norm(n1_arr)
                if mag1 > 1e-9:
                    n1_tip = mid + n1_arr / mag1 * nlen
                    for pos, text in (
                        (gp_Pnt(float(mid[0] - 0.15), float(mid[1]), float(mid[2] + 0.15)),
                         f"N1({line.normal1[0]:.2f},{line.normal1[1]:.2f},{line.normal1[2]:.2f})"),
                        (gp_Pnt(float(n1_tip[0]), float(n1_tip[1]), float(n1_tip[2])),
                         "N1"),
                    ):
                        lbl = _make_label(pos, text, col_lbl_n1)
                        ctx.Display(lbl, False)
                        ctx.Deactivate(lbl)
                        self._linebox_extra_ais.append(lbl)

                # 法向2 标签
                n2_arr = np.array(line.normal2, dtype=float)
                mag2 = np.linalg.norm(n2_arr)
                if mag2 > 1e-9:
                    n2_tip = mid + n2_arr / mag2 * nlen
                    for pos, text in (
                        (gp_Pnt(float(mid[0] + 0.15), float(mid[1] - 0.15), float(mid[2] + 0.15)),
                         f"N2({line.normal2[0]:.2f},{line.normal2[1]:.2f},{line.normal2[2]:.2f})"),
                        (gp_Pnt(float(n2_tip[0]), float(n2_tip[1]), float(n2_tip[2])),
                         "N2"),
                    ):
                        lbl = _make_label(pos, text, col_lbl_n2)
                        ctx.Display(lbl, False)
                        ctx.Deactivate(lbl)
                        self._linebox_extra_ais.append(lbl)

        # 传递 hover 映射给 viewer
        self.viewer.set_linebox_hover_map(hover_map)

        # 连接面模式：有 ≥2 条线时生成面
        if self._connect_faces and len(lines) >= 2:
            try:
                faces = process_multiple_lines(lines)
            except Exception as e:
                QMessageBox.critical(self, "生成错误", str(e))
                ctx.UpdateCurrentViewer()
                self._refresh_all()
                return

            if not faces:
                self.panel_linebox._set_status("⚠ 无法生成有效面", "#ff7766")
            else:
                for i, fi in enumerate(faces):
                    r, g, b = _FACE_COLORS[i % len(_FACE_COLORS)]
                    color = Quantity_Color(r, g, b, Quantity_TOC_RGB)
                    name  = f"Face_{len(self._items) + 1}"
                    item  = self._make_item(fi['face'], name)
                    item.color = (r, g, b); item.ais.SetColor(color)
                    self._items.append(item)
                    self._display_item(item)
                    self._linebox_items.append(item)
                    nv = AIS_Shape(fi['normal_vector'])
                    nv.SetColor(color)
                    nv.SetWidth(1.5)
                    ctx.Display(nv, False)
                    ctx.Deactivate(nv)
                    self._linebox_extra_ais.append(nv)

                n = len(faces)
                self.panel_linebox._set_status(f"✓ 已生成 {n} 个面", "#88ffcc")
                self._set_status(
                    f"✓ 线框：{len(lines)} 条 → {n} 个面", "#44ddcc")
        else:
            if not self._connect_faces:
                self.panel_linebox._set_status(
                    f"预览模式：{len(lines)} 条线段（未连面）", "#a0c8ff")
            else:
                self.panel_linebox._set_status(
                    f"已添加 {len(lines)} 条（需 ≥2 条才连面）", "#a0c8ff")

        ctx.UpdateCurrentViewer()
        self.viewer._display.FitAll()
        self._refresh_all()

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

    def _on_stack_changed(self):
        self.ribbon.update_undo_redo(
            self.cmd_stack.can_undo,
            self.cmd_stack.can_redo,
            self.cmd_stack.undo_text,
            self.cmd_stack.redo_text,
        )

    def _on_tab_changed(self, idx: int):
        self.stack.setCurrentIndex(idx)

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
