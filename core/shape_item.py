"""
core/shape_item.py  ── 场景中每个形体的数据容器

扩展指引：
  - 若需支持旋转，在 offset 旁增加 rotation: gp_Quaternion 字段，
    并在 apply_transform() 中合成旋转 + 平移。
  - 若需颜色可变，暴露 set_color(r,g,b) 并调用 ctx.SetColor()。
"""

import math
from dataclasses import dataclass, field
from typing import Tuple

from OCC.Core.AIS import AIS_Shape
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.GProp import GProp_GProps
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.gp import gp_Trsf, gp_Vec, gp_Pnt, gp_Ax1, gp_Dir


@dataclass
class ShapeItem:
    """
    封装一个场景形体的所有数据与操作。

    Attributes:
        name    : 显示名称
        ais     : AIS_Shape，用于 OCC 渲染上下文
        topo    : 原始 TopoDS_Shape（未移动）
        offset  : 当前累计平移向量 (x, y, z)
        rpy     : 旋转角 (roll, pitch, yaw)，单位度，ZYX 外旋顺序
        color   : RGB 颜色元组，0‥1
        visible : 是否可见
    """
    name:    str
    ais:     AIS_Shape
    topo:    TopoDS_Shape
    offset:  gp_Vec                      = field(default_factory=lambda: gp_Vec(0, 0, 0))
    rpy:     Tuple[float, float, float]  = (0.0, 0.0, 0.0)
    color:   Tuple[float, float, float]  = (0.3, 0.6, 1.0)
    visible: bool                        = True

    # ── 变换 ────────────────────────────────────────────────────────────────

    def _make_transform(self) -> gp_Trsf:
        """组合 RPY 旋转（ZYX 外旋）+ 平移，返回 gp_Trsf。"""
        roll_r  = math.radians(self.rpy[0])
        pitch_r = math.radians(self.rpy[1])
        yaw_r   = math.radians(self.rpy[2])

        o = gp_Pnt(0, 0, 0)
        tr = gp_Trsf(); tr.SetRotation(gp_Ax1(o, gp_Dir(1, 0, 0)), roll_r)
        tp = gp_Trsf(); tp.SetRotation(gp_Ax1(o, gp_Dir(0, 1, 0)), pitch_r)
        ty = gp_Trsf(); ty.SetRotation(gp_Ax1(o, gp_Dir(0, 0, 1)), yaw_r)
        # ZYX 外旋：先 yaw，再 pitch，再 roll
        rot = tr.Multiplied(tp).Multiplied(ty)

        tt = gp_Trsf()
        tt.SetTranslation(self.offset)
        return tt.Multiplied(rot)   # 先旋转再平移

    def apply_offset(self, ctx) -> None:
        """将当前变换（旋转 + 平移）应用到 AIS 对象。"""
        ctx.SetLocation(self.ais, TopLoc_Location(self._make_transform()))

    # ── 几何查询（均作用于 Located Shape）──────────────────────────────────

    def located_shape(self) -> TopoDS_Shape:
        """返回已附加 Location 的 TopoDS_Shape，供 BRepExtrema 等使用。"""
        return self.topo.Located(TopLoc_Location(self._make_transform()))

    def center(self) -> gp_Pnt:
        """返回包围盒中心（世界坐标）。"""
        xmin, ymin, zmin, xmax, ymax, zmax = self.bbox()
        return gp_Pnt(
            (xmin + xmax) / 2,
            (ymin + ymax) / 2,
            (zmin + zmax) / 2,
        )

    def bbox(self) -> Tuple[float, float, float, float, float, float]:
        """返回 (xmin, ymin, zmin, xmax, ymax, zmax)。"""
        bb = Bnd_Box()
        brepbndlib.Add(self.located_shape(), bb)
        return bb.Get()

    def bbox_size(self) -> Tuple[float, float, float]:
        """返回包围盒三轴尺寸 (dx, dy, dz)。"""
        xmin, ymin, zmin, xmax, ymax, zmax = self.bbox()
        return xmax - xmin, ymax - ymin, zmax - zmin

    def bbox_diagonal(self) -> float:
        dx, dy, dz = self.bbox_size()
        return math.sqrt(dx**2 + dy**2 + dz**2)

    def volume(self) -> float:
        """体积（实体）。"""
        props = GProp_GProps()
        try:
            brepgprop.VolumeProperties(self.located_shape(), props)
            return abs(props.Mass())
        except Exception:
            return 0.0

    def surface_area(self) -> float:
        """表面积。"""
        props = GProp_GProps()
        try:
            brepgprop.SurfaceProperties(self.located_shape(), props)
            return abs(props.Mass())
        except Exception:
            return 0.0