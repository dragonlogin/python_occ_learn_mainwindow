"""
core/analysis.py  ── 几何分析算法（距离 / 碰撞）

所有函数均为纯函数，不依赖 Qt，便于单元测试和复用。
扩展指引：
  - 新增干涉体积分析：基于 BRepAlgoAPI_Common 实现 interference_volume()。
  - 新增最小间隙报告：封装为 GapReport dataclass 返回更多字段。
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from OCC.Core.BRepExtrema import BRepExtrema_DistShapeShape
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.gp import gp_Pnt

from .shape_item import ShapeItem


# ── 数据类 ────────────────────────────────────────────────────────────────────

@dataclass
class DistanceResult:
    """两形体间最小距离的计算结果。"""
    shape_a:  str           # 形体名称
    shape_b:  str
    distance: float
    point_a:  gp_Pnt        # 形体 A 上的最近点
    point_b:  gp_Pnt        # 形体 B 上的最近点


@dataclass
class CollisionEntry:
    """一对形体的碰撞检测条目。"""
    index_a:  int
    index_b:  int
    name_a:   str
    name_b:   str
    distance: float

    def is_colliding(self, threshold: float) -> bool:
        return self.distance < threshold


# ── 核心算法 ──────────────────────────────────────────────────────────────────

def compute_distance(item_a: ShapeItem, item_b: ShapeItem) -> Optional[DistanceResult]:
    """
    计算两个 ShapeItem 之间的最小距离。

    Returns:
        DistanceResult，或 None（计算失败）。
    """
    calc = BRepExtrema_DistShapeShape(
        item_a.located_shape(),
        item_b.located_shape(),
    )
    if not calc.IsDone():
        return None
    return DistanceResult(
        shape_a  = item_a.name,
        shape_b  = item_b.name,
        distance = calc.Value(),
        point_a  = calc.PointOnShape1(1),
        point_b  = calc.PointOnShape2(1),
    )


def compute_all_collisions(items: List[ShapeItem]) -> List[CollisionEntry]:
    """
    对场景中所有形体对进行碰撞检测。

    Returns:
        按距离升序排列的 CollisionEntry 列表。
    """
    results: List[CollisionEntry] = []
    n = len(items)
    for i in range(n):
        for j in range(i + 1, n):
            calc = BRepExtrema_DistShapeShape(
                items[i].located_shape(),
                items[j].located_shape(),
            )
            if calc.IsDone():
                results.append(CollisionEntry(
                    index_a  = i,
                    index_b  = j,
                    name_a   = items[i].name,
                    name_b   = items[j].name,
                    distance = calc.Value(),
                ))
    results.sort(key=lambda e: e.distance)
    return results
