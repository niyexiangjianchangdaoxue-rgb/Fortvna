"""budget: 预算下发与心跳契约 (SPEC 第 7.2 条)。

风险预算单向下行 (第 1.3 条铁律1):Cosmos → Minisha 总监 → 员工,下级无权自行扩大。
预算带有效期,过期未续期自动视为归零 —— 失联即收权 (第 7.2 条)。

金额一律 Decimal,禁止 float,避免账本口径漂移 (第 7.3 复式记账)。
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from fortvna_core.ids import UUID7

__all__ = [
    "COSMOS_STALE_AFTER_MS",
    "HEARTBEAT_INTERVAL_MS",
    "MINISHA_SELF_PAUSE_AFTER_MS",
    "BudgetGrant",
    "Heartbeat",
    "is_cosmos_stale",
    "should_minisha_self_pause",
]

# 心跳周期 (第 7.2 条): Minisha 每 5s 上报;Cosmos 连续 3 次 (15s) 未收即标记 STALE;
# Minisha 侧失去 Cosmos 心跳 30s 后自动全员 PAUSED。
HEARTBEAT_INTERVAL_MS = 5_000
COSMOS_STALE_AFTER_MS = 15_000
MINISHA_SELF_PAUSE_AFTER_MS = 30_000


def is_cosmos_stale(last_heartbeat_utc_ms: int, now_utc_ms: int) -> bool:
    """Cosmos 视角: 距最近一次收到 Minisha 心跳是否已达 STALE 阈值 (连续 3 次≈15s, 第 7.2 条)。

    严格边界: 恰好 15000ms 即判 STALE (>=), 与 BudgetGrant.is_expired 同一"失联即收权"口径。
    """
    return now_utc_ms - last_heartbeat_utc_ms >= COSMOS_STALE_AFTER_MS


def should_minisha_self_pause(last_cosmos_heartbeat_utc_ms: int, now_utc_ms: int) -> bool:
    """Minisha 视角: 距最近一次收到 Cosmos 心跳是否已达自保 PAUSED 阈值 (30s, 第 7.2 条)。

    严格边界: 恰好 30000ms 即触发 (>=)。自我保护, 不平仓, 等待人工。
    """
    return now_utc_ms - last_cosmos_heartbeat_utc_ms >= MINISHA_SELF_PAUSE_AFTER_MS


class BudgetGrant(BaseModel):
    """预算下发消息 (第 7.2 条)。过期 (valid_until) 未续期 → 预算归零。"""

    model_config = ConfigDict(strict=True, frozen=True)

    grant_id: UUID7  # UUIDv7 强制 (第 11.2 条 transfer/grant 幂等去重键)
    employee_id: str
    budget_usdt: Decimal = Field(ge=0, description="下发预算 (USDT), 非负")
    valid_until: int = Field(description="有效期截止 UTC 毫秒时间戳 (第 12.1 条)")

    def is_expired(self, now_utc_ms: int) -> bool:
        """严格过期语义:now >= valid_until 即失效 (失联即收权, 第 7.2 条)。"""
        return now_utc_ms >= self.valid_until

    def effective_budget(self, now_utc_ms: int) -> Decimal:
        """当前有效预算:过期即归零 (下级永远无权自行扩大, 第 1.3 条)。"""
        return Decimal(0) if self.is_expired(now_utc_ms) else self.budget_usdt


class Heartbeat(BaseModel):
    """心跳消息 (第 7.2 条)。source 标识发送方 (minisha 总监 / cosmos)。"""

    model_config = ConfigDict(strict=True, frozen=True)

    source: str
    seq: int = Field(ge=0, description="单调递增序号,用于丢包/乱序检测")
    ts_utc: int = Field(description="UTC 毫秒时间戳 (第 12.1 条)")
