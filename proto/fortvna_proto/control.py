"""control: 员工状态、控制命令与合法转换表 (SPEC 第 8 章 / D-001)。

契约单点真相 (v1 进程内命令总线)。此处只定义**契约与合法性判据**(数据 + 纯函数);
实际的命令队列/优先级仲裁执行引擎属于 Minisha 运行时,后续切片实现。

员工四状态 (第 8.1 条):
  ACTIVE     正常执行 (可开仓/管理持仓/撤单)
  PAUSED     停止进攻,防守逻辑照常,持仓自然了结 (禁开仓,存量管理继续)
  FLATTENING 过渡态:立即市价平仓 + 撤全部挂单,完成后自动进入 FLAT
  FLAT       空仓的 PAUSED (FLATTENING 的终态)
  FROZEN     人工完全接管,系统只读 (不开/不平/不撤)
"""

from __future__ import annotations

from enum import IntEnum, StrEnum

from pydantic import BaseModel, ConfigDict, Field

from fortvna_core.ids import UUID7

__all__ = [
    "ACTION_PRIORITY",
    "GLOBAL_TARGET",
    "LEGAL_TRANSITIONS",
    "ControlAction",
    "ControlCommand",
    "EmployeeState",
    "is_legal_transition",
]

# 全局命令 target 哨兵 (EMERGENCY_STOP 面向全体, 非单一员工)。
GLOBAL_TARGET = "*"


class EmployeeState(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    FLATTENING = "FLATTENING"
    FLAT = "FLAT"
    FROZEN = "FROZEN"


class ControlAction(StrEnum):
    RESUME = "RESUME"
    PAUSE = "PAUSE"
    FLATTEN = "FLATTEN"
    FREEZE = "FREEZE"
    EMERGENCY_STOP = "EMERGENCY_STOP"  # 全局最高优先级 (第 8.1 / 附录 A)


class _Priority(IntEnum):
    """命令优先级 (第 8.1 条): FREEZE > FLATTEN > PAUSE > RESUME;EMERGENCY_STOP > 一切员工级。"""

    RESUME = 1
    PAUSE = 2
    FLATTEN = 3
    FREEZE = 4
    EMERGENCY_STOP = 100


ACTION_PRIORITY: dict[ControlAction, int] = {
    ControlAction.RESUME: _Priority.RESUME,
    ControlAction.PAUSE: _Priority.PAUSE,
    ControlAction.FLATTEN: _Priority.FLATTEN,
    ControlAction.FREEZE: _Priority.FREEZE,
    ControlAction.EMERGENCY_STOP: _Priority.EMERGENCY_STOP,
}


# 合法状态转换 (第 8.1 条转换矩阵):
#   ACTIVE ⇄ PAUSED
#   {ACTIVE, PAUSED} → FLATTENING → FLAT
#   任意状态 → FROZEN
#   FROZEN 解除 → 人工二次确认并指定目标状态 (ACTIVE/PAUSED/FLAT)
#   FLAT 是空仓的 PAUSED,可被 RESUME 回 ACTIVE 或再度 PAUSED
LEGAL_TRANSITIONS: frozenset[tuple[EmployeeState, EmployeeState]] = frozenset(
    {
        (EmployeeState.ACTIVE, EmployeeState.PAUSED),
        (EmployeeState.PAUSED, EmployeeState.ACTIVE),
        (EmployeeState.ACTIVE, EmployeeState.FLATTENING),
        (EmployeeState.PAUSED, EmployeeState.FLATTENING),
        (EmployeeState.FLATTENING, EmployeeState.FLAT),
        (EmployeeState.FLAT, EmployeeState.ACTIVE),
        (EmployeeState.FLAT, EmployeeState.PAUSED),
        # 任意状态 → FROZEN
        (EmployeeState.ACTIVE, EmployeeState.FROZEN),
        (EmployeeState.PAUSED, EmployeeState.FROZEN),
        (EmployeeState.FLATTENING, EmployeeState.FROZEN),
        (EmployeeState.FLAT, EmployeeState.FROZEN),
        # FROZEN 解除 (人工指定目标态)
        (EmployeeState.FROZEN, EmployeeState.ACTIVE),
        (EmployeeState.FROZEN, EmployeeState.PAUSED),
        (EmployeeState.FROZEN, EmployeeState.FLAT),
    }
)


def is_legal_transition(src: EmployeeState, dst: EmployeeState) -> bool:
    """判断状态转换是否合法 (第 8.1 条)。同态自转 (src==dst) 视为幂等合法 no-op。"""
    if src == dst:
        return True
    return (src, dst) in LEGAL_TRANSITIONS


class ControlCommand(BaseModel):
    """控制命令 (第 8.3 条)。幂等:同 command_id 重放不产生二次动作 (由执行引擎据此去重)。

    全字段 strict + frozen:契约不可变,类型不放宽 (第 3.2 条)。
    """

    model_config = ConfigDict(strict=True, frozen=True)

    command_id: UUID7  # UUIDv7 强制 (第 8.3 条),经 fortvna_core.ids.generate_uuid7 生成
    target: str = Field(description="员工 ID;全局命令用 GLOBAL_TARGET ('*')")
    action: ControlAction
    issued_by: str = Field(description="发起方标识 (面板用户 / minisha-ctl / cosmos)")
    ts_utc: int = Field(description="UTC 毫秒时间戳 (第 12.1 条)")

    @property
    def priority(self) -> int:
        return ACTION_PRIORITY[self.action]

    @property
    def is_global(self) -> bool:
        return self.action == ControlAction.EMERGENCY_STOP or self.target == GLOBAL_TARGET
