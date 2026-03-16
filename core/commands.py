"""
core/commands.py  ── 命令基类 + 所有具体命令

设计原则：
  - 每条命令只依赖 AppContext，不直接引用 MainWindow。
  - execute() / undo() 必须是互逆的，且可重复调用。
  - description 属性用于 Tooltip 和历史面板显示。

扩展指引（添加新命令只需 3 步）：
  1. 继承 Command，实现 execute() / undo() / description。
  2. 在 __init__ 里保存执行前的状态快照，供 undo() 恢复。
  3. 在 main_window.py 对应操作处 self.cmd_stack.push(NewCommand(ctx, ...))。
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, List

if TYPE_CHECKING:
    from core.shape_item import ShapeItem


@dataclass
class AppContext:
    items:              List["ShapeItem"]
    display_item:       Callable[["ShapeItem"], None]
    hide_item:          Callable[["ShapeItem"], None]
    toggle_item:        Callable[["ShapeItem"], None]
    refresh_all:        Callable[[], None]
    fit_all:            Callable[[], None]
    set_status:         Callable[[str, str], None]
    render_linebox:     Callable[[list], None]
    set_linebox_lines:  Callable[[list], None]
    apply_font:         Callable[[int], None]
    sync_font_panel:    Callable[[int], None]
    make_item:          Callable[..., "ShapeItem"]


class Command(ABC):
    @property
    @abstractmethod
    def description(self) -> str: ...
    @abstractmethod
    def execute(self) -> None: ...
    @abstractmethod
    def undo(self) -> None: ...
    def __repr__(self):
        return f"<{type(self).__name__}: {self.description}>"


class MacroCommand(Command):
    """将多条子命令打包成单步撤销/重做。"""
    def __init__(self, desc: str, commands: List[Command]):
        self._desc = desc
        self._commands = list(commands)
    @property
    def description(self): return self._desc
    def execute(self):
        for c in self._commands: c.execute()
    def undo(self):
        for c in reversed(self._commands): c.undo()


class AddShapeCommand(Command):
    def __init__(self, ctx: AppContext, item: "ShapeItem"):
        self._ctx = ctx; self._item = item
    @property
    def description(self): return f"添加 {self._item.name}"
    def execute(self):
        if self._item not in self._ctx.items:
            self._ctx.items.append(self._item)
        self._ctx.display_item(self._item)
        self._ctx.fit_all()
        self._ctx.refresh_all()
        self._ctx.set_status(f"✓ 已添加 {self._item.name}", "#88ee88")
    def undo(self):
        if self._item in self._ctx.items:
            self._ctx.items.remove(self._item)
        self._ctx.hide_item(self._item)
        self._ctx.refresh_all()
        self._ctx.set_status(f"↩ 撤销添加：{self._item.name}", "#ffaa44")


class DeleteShapeCommand(Command):
    def __init__(self, ctx: AppContext, item: "ShapeItem", index: int):
        self._ctx = ctx; self._item = item; self._index = index
    @property
    def description(self): return f"删除 {self._item.name}"
    def execute(self):
        if self._item in self._ctx.items:
            self._ctx.items.remove(self._item)
        self._ctx.hide_item(self._item)
        self._ctx.refresh_all()
        self._ctx.set_status(f"已删除 {self._item.name}", "#ffaa44")
    def undo(self):
        idx = min(self._index, len(self._ctx.items))
        if self._item not in self._ctx.items:
            self._ctx.items.insert(idx, self._item)
        self._ctx.display_item(self._item)
        self._ctx.refresh_all()
        self._ctx.set_status(f"↩ 撤销删除：{self._item.name}", "#88ee88")


class ToggleVisibilityCommand(Command):
    def __init__(self, ctx: AppContext, item: "ShapeItem"):
        self._ctx = ctx; self._item = item
        self._was_visible = item.visible
    @property
    def description(self):
        return f"{'隐藏' if self._was_visible else '显示'} {self._item.name}"
    def execute(self): self._ctx.toggle_item(self._item)
    def undo(self):    self._ctx.toggle_item(self._item)


class LineboxUpdateCommand(Command):
    def __init__(self, ctx: AppContext, old_lines: list, new_lines: list):
        self._ctx = ctx
        self._old = list(old_lines)
        self._new = list(new_lines)
    @property
    def description(self):
        n = len(self._new)
        if n == 0: return "清空线框线段"
        d = n - len(self._old)
        if d > 0: return f"添加线段（共 {n} 条）"
        if d < 0: return f"删除线段（剩余 {n} 条）"
        return f"更新线框（{n} 条）"
    def execute(self):
        self._ctx.set_linebox_lines(self._new)
        self._ctx.render_linebox(self._new)
    def undo(self):
        self._ctx.set_linebox_lines(self._old)
        self._ctx.render_linebox(self._old)


class ChangeFontCommand(Command):
    def __init__(self, ctx: AppContext, old_size: int, new_size: int):
        self._ctx = ctx; self._old = old_size; self._new = new_size
    @property
    def description(self): return f"字体大小 {self._old}→{self._new} pt"
    def execute(self):
        self._ctx.apply_font(self._new)
        self._ctx.sync_font_panel(self._new)
    def undo(self):
        self._ctx.apply_font(self._old)
        self._ctx.sync_font_panel(self._old)
