"""
core/importer.py  ── CAD 文件导入

支持格式：STEP · IGES · BREP
扩展指引：新增格式只需实现同签名函数并注册到 IMPORTERS 字典。
"""

import os
from typing import Optional

from OCC.Core.BRep import BRep_Builder
from OCC.Core.BRepTools import breptools
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.IGESControl import IGESControl_Reader
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.TopoDS import TopoDS_Shape


# ── 各格式导入函数 ────────────────────────────────────────────────────────────

def import_step(path: str) -> Optional[TopoDS_Shape]:
    """导入 STEP 文件（.step / .stp）。"""
    reader = STEPControl_Reader()
    if reader.ReadFile(path) != IFSelect_RetDone:
        return None
    reader.TransferRoots()
    shape = reader.OneShape()
    return shape if not shape.IsNull() else None


def import_iges(path: str) -> Optional[TopoDS_Shape]:
    """导入 IGES 文件（.iges / .igs）。"""
    reader = IGESControl_Reader()
    if reader.ReadFile(path) != IFSelect_RetDone:
        return None
    reader.TransferRoots()
    shape = reader.OneShape()
    return shape if not shape.IsNull() else None


def import_brep(path: str) -> Optional[TopoDS_Shape]:
    """导入 BREP 文件（.brep）。"""
    builder = BRep_Builder()
    shape   = TopoDS_Shape()
    try:
        breptools.Read(shape, path, builder)
    except Exception:
        return None
    return shape if not shape.IsNull() else None


# ── 扩展注册表：ext → 导入函数 ────────────────────────────────────────────────
IMPORTERS = {
    ".step": import_step,
    ".stp":  import_step,
    ".iges": import_iges,
    ".igs":  import_iges,
    ".brep": import_brep,
}


def import_file(path: str) -> Optional[TopoDS_Shape]:
    """
    统一入口：根据文件扩展名自动选择导入器。

    Returns:
        TopoDS_Shape 或 None（格式不支持 / 读取失败）。
    """
    ext = os.path.splitext(path)[1].lower()
    importer = IMPORTERS.get(ext)
    if importer is None:
        raise ValueError(f"不支持的文件格式: {ext}")
    return importer(path)


def supported_filter() -> str:
    """返回 QFileDialog 用的文件过滤字符串。"""
    return "CAD 文件 (*.step *.stp *.iges *.igs *.brep);;所有文件 (*)"
