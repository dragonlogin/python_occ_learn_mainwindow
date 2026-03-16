"""
core/command_stack.py  ── 通用撤销 / 重做栈

完全与业务无关，只管理 Command 对象的生命周期。

使用方式：
    stack = CommandStack()
    stack.sig_stack_changed.connect(update_ui)
    stack.push(SomeCommand(...))
    stack.undo()
    stack.redo()

扩展指引：
    - 限制历史长度：修改 MAX_HISTORY。
    - 分组命令（宏）：用 MacroCommand 包装多条子命令后 push 一次。
    - 持久化：遍历 _undo_stack 序列化每条命令的参数即可。
"""

from __future__ import annotations
from collections import deque
from typing import Deque, Optional

from PyQt5.QtCore import QObject, pyqtSignal

from core.commands import Command


class CommandStack(QObject):
    """
    Signals:
        sig_stack_changed()  每次 push / undo / redo / clear 后发射，
                             供 UI 刷新按钮可用状态和文字提示。
    """

    sig_stack_changed = pyqtSignal()

    #: 最大历史步数，超出后丢弃最旧的记录
    MAX_HISTORY: int = 100

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._undo_stack: Deque[Command] = deque()
        self._redo_stack: Deque[Command] = deque()

    # ── 公开 API ──────────────────────────────────────────────────────────────

    def push(self, cmd: Command) -> None:
        """执行命令并压入撤销栈；清空重做栈。"""
        cmd.execute()
        self._undo_stack.append(cmd)
        self._redo_stack.clear()
        # 超出上限时丢弃最旧一条
        if len(self._undo_stack) > self.MAX_HISTORY:
            self._undo_stack.popleft()
        self.sig_stack_changed.emit()

    def undo(self) -> None:
        """撤销最近一步操作。"""
        if not self._undo_stack:
            return
        cmd = self._undo_stack.pop()
        cmd.undo()
        self._redo_stack.append(cmd)
        self.sig_stack_changed.emit()

    def redo(self) -> None:
        """重做最近一步被撤销的操作。"""
        if not self._redo_stack:
            return
        cmd = self._redo_stack.pop()
        cmd.execute()
        self._undo_stack.append(cmd)
        self.sig_stack_changed.emit()

    def clear(self) -> None:
        """清空整个历史（例如打开新文件时调用）。"""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.sig_stack_changed.emit()

    # ── 状态查询 ──────────────────────────────────────────────────────────────

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    @property
    def undo_text(self) -> str:
        """下一步撤销的操作描述，用于按钮 tooltip。"""
        if self._undo_stack:
            return f"撤销：{self._undo_stack[-1].description}"
        return "无可撤销操作"

    @property
    def redo_text(self) -> str:
        """下一步重做的操作描述，用于按钮 tooltip。"""
        if self._redo_stack:
            return f"重做：{self._redo_stack[-1].description}"
        return "无可重做操作"

    @property
    def undo_stack_descriptions(self) -> list[str]:
        """返回完整撤销历史描述列表（最新在末尾），供调试或历史面板使用。"""
        return [cmd.description for cmd in self._undo_stack]

    @property
    def redo_stack_descriptions(self) -> list[str]:
        return [cmd.description for cmd in self._redo_stack]
