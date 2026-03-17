"""
viewer/occ_viewer.py  ── 3D 视口

继承 qtViewer3d，重写鼠标事件实现：
  - 左键拖拽移动选中 ShapeItem
  - 拖拽过程中发射 sig_distance / sig_collision / sig_selected 信号
  - 实时绘制最近点连线

扩展指引：
  - 支持旋转拖拽：右键拖拽时在 mouseMoveEvent 中更新 ShapeItem.rotation。
  - 支持多选：维护 _selected_items: List[ShapeItem] 并批量移动。
  - 支持撤销：每次 mouseReleaseEvent 将前一 offset 压栈。
"""

from typing import List, Optional, Tuple, Dict

from OCC.Core.AIS import AIS_Shape
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCC.Core.gp import gp_Pnt, gp_Vec

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget

from OCC.Display.qtDisplay import qtViewer3d

from core.shape_item import ShapeItem
from core.analysis   import (
    DistanceResult, CollisionEntry,
    compute_distance, compute_all_collisions,
)
from utils.helpers import qty_color

from OCC.Core.AIS import AIS_Trihedron, AIS_ViewCube
from OCC.Core.Geom import Geom_Axis2Placement
from OCC.Core.gp  import gp_Ax2, gp_Pnt, gp_Dir
from OCC.Core.Prs3d import Prs3d_DatumParts
from OCC.Core.V3d import V3d_ZBUFFER


# 碰撞判定阈值（仅用于连线着色）
_NEAR_THRESHOLD = 0.01


class OCCViewer(qtViewer3d):
    """
    3D 视口，支持拖拽移动与实时分析。

    Signals:
        sig_distance  (DistanceResult)      选定对的最新距离结果
        sig_collision (List[CollisionEntry]) 所有对的碰撞结果
        sig_selected  (int)                 用户在视口中选中形体的索引
    """

    sig_distance  = pyqtSignal(object)   # DistanceResult
    sig_collision = pyqtSignal(list)     # List[CollisionEntry]
    sig_selected  = pyqtSignal(int)      # shape index
    sig_linebox_hovered = pyqtSignal(int)  # line index (-1 = none)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._items: List[ShapeItem] = []
        self.dist_pair: Tuple[int, int] = (0, 1)   # 当前距离计算对

        # 拖拽状态
        self._dragging:      bool                  = False
        self._drag_item:     Optional[ShapeItem]   = None
        self._drag_ref_pnt:  Optional[gp_Pnt]      = None
        self._drag_wstart:   Optional[gp_Pnt]      = None
        self._drag_off_base: Optional[gp_Vec]      = None

        # 距离连线 AIS（每帧重建）
        self._dist_line_ais: Optional[AIS_Shape] = None

        # linebox hover 映射：List[(AIS_Shape, line_index)]
        self._linebox_hover_list: list = []
        self._last_hovered_line_idx: int = -1
        

    # ── 外部接口 ──────────────────────────────────────────────────────────────

    def set_items(self, items: List[ShapeItem]) -> None:
        self._items = items

    def set_linebox_hover_map(self, hover_list: list) -> None:
        """设置 linebox hover 映射：List[(AIS_Shape, line_index)]"""
        self._linebox_hover_list = hover_list
        self._last_hovered_line_idx = -1

    def run_analysis(self) -> None:
        """外部调用：立即执行一次分析并发射信号。"""
        self._run_analysis()

    # ── 坐标转换 ──────────────────────────────────────────────────────────────

    def _screen_to_world(self, sx: int, sy: int,
                          ref: Optional[gp_Pnt] = None) -> gp_Pnt:
        """
        屏幕像素 → 世界坐标。
        投影到过 ref 点且垂直于视线的平面；ref=None 时投影到 Z=0 平面。
        使用 ConvertWithProj 兼容新版 pythonocc（Convert 仅返回 2 个值）。
        """
        view = self._display.GetView()
        px, py, pz, dx, dy, dz = view.ConvertWithProj(sx, sy)

        if ref is not None:
            ox = ref.X() - px
            oy = ref.Y() - py
            oz = ref.Z() - pz
            denom = dx * dx + dy * dy + dz * dz
            t = (ox * dx + oy * dy + oz * dz) / denom if abs(denom) > 1e-10 else 0.0
        else:
            t = -pz / dz if abs(dz) > 1e-10 else 1000.0

        return gp_Pnt(px + t * dx, py + t * dy, pz + t * dz)

    # ── 辅助：找到 AIS 对应的 ShapeItem ──────────────────────────────────────

    def _find_item(self, ais_obj) -> Optional[ShapeItem]:
        for it in self._items:
            if it.ais == ais_obj:
                return it
        return None

    # ── 鼠标事件 ──────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            sx, sy = event.x(), event.y()
            ctx    = self._display.Context
            view   = self._display.GetView()

            # 先移动检测，不 Select
            ctx.MoveTo(sx, sy, view, True)

            # ← 检查光标下的对象，ViewCube 在这里能检测到
            if ctx.HasDetected():
                detected = ctx.DetectedInteractive()
                if detected.DynamicType().Name() == "AIS_ViewCube":
                    super().mousePressEvent(event)
                    return

            # 普通形体走原来的 Select 流程
            ctx.Select(True)
            ctx.InitSelected()

            if ctx.MoreSelected():
                ais_obj = ctx.SelectedInteractive()
                item    = self._find_item(ais_obj)
                if item and item.visible:
                    self._dragging      = True
                    self._drag_item     = item
                    self._drag_ref_pnt  = item.center()
                    self._drag_wstart   = self._screen_to_world(sx, sy, self._drag_ref_pnt)
                    self._drag_off_base = item.offset

                    idx = self._items.index(item)
                    self.sig_selected.emit(idx)
                    event.accept()
                    return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and self._drag_item:
            sx, sy  = event.x(), event.y()
            cur_pnt = self._screen_to_world(sx, sy, self._drag_ref_pnt)
            delta   = gp_Vec(self._drag_wstart, cur_pnt)

            self._drag_item.offset = gp_Vec(
                self._drag_off_base.X() + delta.X(),
                self._drag_off_base.Y() + delta.Y(),
                self._drag_off_base.Z() + delta.Z(),
            )
            self._drag_item.apply_offset(self._display.Context)
            self._display.Context.CurrentViewer().Redraw()
            self._run_analysis()
            event.accept()
            return

        # 非拖拽：高亮探测
        ctx = self._display.Context
        ctx.MoveTo(event.x(), event.y(), self._display.GetView(), True)

        # linebox hover 联动
        if self._linebox_hover_list:
            hovered_idx = -1
            if ctx.HasDetected():
                detected = ctx.DetectedInteractive()
                det_ptr = detected.this
                for ais_obj, line_idx in self._linebox_hover_list:
                    if det_ptr == ais_obj.this:
                        hovered_idx = line_idx
                        break
            if hovered_idx != self._last_hovered_line_idx:
                self._last_hovered_line_idx = hovered_idx
                self.sig_linebox_hovered.emit(hovered_idx)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging    = False
            self._drag_item   = None
            self._drag_wstart = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # ── 分析 ──────────────────────────────────────────────────────────────────

    def _run_analysis(self) -> None:
        n = len(self._items)
        if n < 2:
            return

        # 1. 选定对的距离
        i, j = self.dist_pair
        if 0 <= i < n and 0 <= j < n and i != j:
            result = compute_distance(self._items[i], self._items[j])
            if result:
                self.sig_distance.emit(result)
                self._draw_dist_line(result)

        # 2. 全部形体对碰撞
        entries = compute_all_collisions(self._items)
        self.sig_collision.emit(entries)

    # ── 距离连线绘制 ──────────────────────────────────────────────────────────

    def _draw_dist_line(self, result: DistanceResult) -> None:
        ctx = self._display.Context

        if self._dist_line_ais:
            ctx.Remove(self._dist_line_ais, False)
            self._dist_line_ais = None

        if result.distance < 1e-6:
            ctx.CurrentViewer().Redraw()
            return

        edge = BRepBuilderAPI_MakeEdge(result.point_a, result.point_b).Edge()
        ae   = AIS_Shape(edge)

        d = result.distance
        if d < _NEAR_THRESHOLD * 10:
            r, g, b = 0.95, 0.15, 0.15     # 红：危险
        elif d < 50:
            r, g, b = 0.95, 0.58, 0.10     # 橙：警告
        else:
            r, g, b = 0.20, 0.90, 0.40     # 绿：安全

        ae.SetColor(qty_color(r, g, b))
        ae.SetWidth(2.5)
        ctx.Display(ae, False)
        ctx.Deactivate(ae)                  # 不参与鼠标拾取
        ctx.CurrentViewer().Redraw()
        self._dist_line_ais = ae

    def add_trihedron(self, size: float = 50.0, trans: float = 0.08) -> None:
        """在世界原点添加 XYZ 坐标轴。"""
        axis = Geom_Axis2Placement(
            gp_Ax2(gp_Pnt(0, 0, 0),
                gp_Dir(0, 0, 1),
                gp_Dir(1, 0, 0))
        )
        tri = AIS_Trihedron(axis)
        tri.SetSize(size)
         # 分轴设置颜色：箭头 + 轴线各自独立
        dp = Prs3d_DatumParts
        tri.SetDatumPartColor(dp.Prs3d_DP_XAxis,  qty_color(1.0, 0.2, 0.2))
        tri.SetDatumPartColor(dp.Prs3d_DP_XArrow, qty_color(1.0, 0.2, 0.2))
        tri.SetDatumPartColor(dp.Prs3d_DP_YAxis,  qty_color(0.2, 1.0, 0.2))
        tri.SetDatumPartColor(dp.Prs3d_DP_YArrow, qty_color(0.2, 1.0, 0.2))
        tri.SetDatumPartColor(dp.Prs3d_DP_ZAxis,  qty_color(0.2, 0.5, 1.0))
        tri.SetDatumPartColor(dp.Prs3d_DP_ZArrow, qty_color(0.2, 0.5, 1.0))
        ctx = self._display.Context
        ctx.Display(tri, False)
        ctx.Deactivate(tri)   # 不参与鼠标拾取
        ctx.UpdateCurrentViewer()
        self._trihedron = tri

        """右下角固定坐标系，使用视图原生 TriedronDisplay。"""
        from OCC.Core.Aspect import Aspect_TOTP_RIGHT_LOWER
        view = self._display.GetView()
        view.TriedronDisplay(
            Aspect_TOTP_RIGHT_LOWER,   # 右下角
            qty_color(1.0, 1.0, 1.0), # 文字颜色
            trans,                      # 相对视图大小，0.08 = 8%
            V3d_ZBUFFER,               # 渲染模式
        )
        view.Redraw()

    def add_view_cube(self) -> None:
        from OCC.Core.Graphic3d import (
            Graphic3d_TransformPers,
            Graphic3d_TMF_TriedronPers,
            Graphic3d_Vec2i,
        )
        from OCC.Core.Aspect import Aspect_TOTP_RIGHT_UPPER

        cube = AIS_ViewCube()
        cube.SetSize(60)
        cube.SetFontHeight(10)
        cube.SetFixedAnimationLoop(True)
        
        # 点击 ViewCube 旋转视角时，不自动执行 FitAll（避免视角放大/缩小）
        if hasattr(cube, "SetResetCamera"):
            cube.SetResetCamera(False)
        
        # 如果需要，也可以设置不自动适应选中对象
        if hasattr(cube, "SetFitSelected"):
            cube.SetFitSelected(False)

        trsf = Graphic3d_TransformPers(
            Graphic3d_TMF_TriedronPers,
            Aspect_TOTP_RIGHT_UPPER,
            Graphic3d_Vec2i(80, 80),
        )
        cube.SetTransformPersistence(trsf)

        ctx = self._display.Context
        ctx.Display(cube, False)
        ctx.UpdateCurrentViewer()
        self._view_cube = cube