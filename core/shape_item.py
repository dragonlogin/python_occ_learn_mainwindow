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
from OCC.Core.gp import gp_Trsf, gp_Vec, gp_Pnt


@dataclass
class ShapeItem:
    """
    封装一个场景形体的所有数据与操作。

    Attributes:
        name    : 显示名称
        ais     : AIS_Shape，用于 OCC 渲染上下文
        topo    : 原始 TopoDS_Shape（未移动）
        offset  : 当前累计平移向量
        color   : RGB 颜色元组，0‥1
        visible : 是否可见
    """
    name:    str
    ais:     AIS_Shape
    topo:    TopoDS_Shape
    offset:  gp_Vec                      = field(default_factory=lambda: gp_Vec(0, 0, 0))
    color:   Tuple[float, float, float]  = (0.3, 0.6, 1.0)
    visible: bool                        = True

    # ── 变换 ────────────────────────────────────────────────────────────────

    def apply_offset(self, ctx) -> None:
        """将当前 offset 作为平移变换应用到 AIS 对象。"""
        trsf = gp_Trsf()
        trsf.SetTranslation(self.offset)
        ctx.SetLocation(self.ais, TopLoc_Location(trsf))

    # ── 几何查询（均作用于 Located Shape）──────────────────────────────────

    def located_shape(self) -> TopoDS_Shape:
        """返回已附加 Location 的 TopoDS_Shape，供 BRepExtrema 等使用。"""
        return self.ais.Shape()

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