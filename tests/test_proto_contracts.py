"""fortvna_proto 契约测试 (SPEC 第 7.2 / 8 章)。"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from fortvna_proto.budget import (
    COSMOS_STALE_AFTER_MS,
    MINISHA_SELF_PAUSE_AFTER_MS,
    BudgetGrant,
    Heartbeat,
    is_cosmos_stale,
    should_minisha_self_pause,
)
from fortvna_proto.control import (
    ACTION_PRIORITY,
    GLOBAL_TARGET,
    ControlAction,
    ControlCommand,
    EmployeeState,
    is_legal_transition,
)
from pydantic import ValidationError

from fortvna_core.ids import uuid7

# 合法 UUIDv7 (契约现强制 v7)
V7 = uuid7(1_752_547_200_000, 0xABC, 0x123456789ABCDEF)

# ---- 状态转换矩阵 (第 8.1 条) ----


def test_active_pause_bidirectional():
    assert is_legal_transition(EmployeeState.ACTIVE, EmployeeState.PAUSED)
    assert is_legal_transition(EmployeeState.PAUSED, EmployeeState.ACTIVE)


def test_flattening_path():
    assert is_legal_transition(EmployeeState.ACTIVE, EmployeeState.FLATTENING)
    assert is_legal_transition(EmployeeState.PAUSED, EmployeeState.FLATTENING)
    assert is_legal_transition(EmployeeState.FLATTENING, EmployeeState.FLAT)


def test_any_state_can_freeze():
    for s in (
        EmployeeState.ACTIVE,
        EmployeeState.PAUSED,
        EmployeeState.FLATTENING,
        EmployeeState.FLAT,
    ):
        assert is_legal_transition(s, EmployeeState.FROZEN)


def test_frozen_release_requires_target():
    assert is_legal_transition(EmployeeState.FROZEN, EmployeeState.ACTIVE)
    assert is_legal_transition(EmployeeState.FROZEN, EmployeeState.PAUSED)
    assert is_legal_transition(EmployeeState.FROZEN, EmployeeState.FLAT)


def test_flat_is_paused_variant():
    # FLAT = 空仓的 PAUSED (第 8.1 条): 具备与 PAUSED 相同的出边 (可 RESUME 回 ACTIVE / 再 PAUSED)
    assert is_legal_transition(EmployeeState.FLAT, EmployeeState.ACTIVE)
    assert is_legal_transition(EmployeeState.FLAT, EmployeeState.PAUSED)


def test_illegal_transitions_rejected():
    # 不能从 FLATTENING 直接回 ACTIVE (必须走完 → FLAT)
    assert not is_legal_transition(EmployeeState.FLATTENING, EmployeeState.ACTIVE)
    # 不能从 ACTIVE 直接跳 FLAT (须经 FLATTENING)
    assert not is_legal_transition(EmployeeState.ACTIVE, EmployeeState.FLAT)


def test_self_transition_is_idempotent():
    for s in EmployeeState:
        assert is_legal_transition(s, s)


# ---- 命令优先级 (第 8.1 条: FREEZE > FLATTEN > PAUSE > RESUME; EMERGENCY_STOP > 全部) ----


def test_command_priority_order():
    p = ACTION_PRIORITY
    assert (
        p[ControlAction.FREEZE]
        > p[ControlAction.FLATTEN]
        > p[ControlAction.PAUSE]
        > p[ControlAction.RESUME]
    )
    assert p[ControlAction.EMERGENCY_STOP] > p[ControlAction.FREEZE]


# ---- ControlCommand (第 8.3 条) ----


def test_control_command_frozen_and_strict():
    cmd = ControlCommand(
        command_id=V7,
        target="employee_a",
        action=ControlAction.PAUSE,
        issued_by="panel:user",
        ts_utc=1_752_547_200_000,
    )
    assert cmd.priority == ACTION_PRIORITY[ControlAction.PAUSE]
    assert not cmd.is_global
    with pytest.raises(ValidationError):
        cmd.action = ControlAction.FREEZE  # frozen


def test_control_command_strict_rejects_wrong_type():
    with pytest.raises(ValidationError):
        ControlCommand(
            command_id=V7,
            target="employee_a",
            action=ControlAction.PAUSE,
            issued_by="panel",
            ts_utc="1752547200000",  # strict: str 不是 int
        )


def test_control_command_rejects_non_uuid7():
    # 第 8.3 条: command_id 必须 UUIDv7; 注入 v4 破坏时间有序 + 幂等去重前提, 应拒绝
    with pytest.raises(ValidationError):
        ControlCommand(
            command_id=uuid.uuid4(),
            target="employee_a",
            action=ControlAction.PAUSE,
            issued_by="panel",
            ts_utc=1_752_547_200_000,
        )


def test_emergency_stop_is_global():
    cmd = ControlCommand(
        command_id=V7,
        target=GLOBAL_TARGET,
        action=ControlAction.EMERGENCY_STOP,
        issued_by="panel:user",
        ts_utc=1_752_547_200_000,
    )
    assert cmd.is_global


# ---- BudgetGrant (第 7.2 条) ----


def test_budget_expiry_zeroes_out():
    g = BudgetGrant(
        grant_id=V7,
        employee_id="employee_a",
        budget_usdt=Decimal("100"),
        valid_until=1_752_547_200_000,
    )
    assert g.effective_budget(1_752_547_199_000) == Decimal("100")
    # 恰在 valid_until → 已失效 (失联即收权)
    assert g.is_expired(1_752_547_200_000)
    assert g.effective_budget(1_752_547_200_000) == Decimal(0)
    assert g.effective_budget(1_752_547_201_000) == Decimal(0)


def test_budget_rejects_negative():
    with pytest.raises(ValidationError):
        BudgetGrant(
            grant_id=V7,
            employee_id="e",
            budget_usdt=Decimal("-1"),
            valid_until=1,
        )


def test_budget_rejects_float_in_strict():
    with pytest.raises(ValidationError):
        BudgetGrant(
            grant_id=V7,
            employee_id="e",
            budget_usdt=100.5,  # strict: float 不是 Decimal
            valid_until=1,
        )


def test_budget_rejects_non_uuid7():
    with pytest.raises(ValidationError):
        BudgetGrant(
            grant_id=uuid.uuid4(),
            employee_id="e",
            budget_usdt=Decimal("1"),
            valid_until=1,
        )


def test_heartbeat_contract():
    hb = Heartbeat(source="minisha", seq=42, ts_utc=1_752_547_200_000)
    assert hb.seq == 42
    with pytest.raises(ValidationError):
        Heartbeat(source="minisha", seq=-1, ts_utc=1)  # seq 非负


# ---- 心跳失联判定 (第 7.2 条, 与 is_expired 同一严格边界口径) ----


def test_cosmos_stale_boundary():
    base = 1_752_547_200_000
    assert not is_cosmos_stale(base, base + COSMOS_STALE_AFTER_MS - 1)
    # 恰好 15000ms → STALE (>=)
    assert is_cosmos_stale(base, base + COSMOS_STALE_AFTER_MS)


def test_minisha_self_pause_boundary():
    base = 1_752_547_200_000
    assert not should_minisha_self_pause(base, base + MINISHA_SELF_PAUSE_AFTER_MS - 1)
    # 恰好 30000ms → 自保 PAUSED (>=)
    assert should_minisha_self_pause(base, base + MINISHA_SELF_PAUSE_AFTER_MS)
