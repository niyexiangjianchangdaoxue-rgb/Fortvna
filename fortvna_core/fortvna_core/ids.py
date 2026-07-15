"""ids: UUIDv7 的唯一实现 (RFC 9562)。

SPEC 强制 command_id (第 8.3 条) 与 transfer_id (第 11.2 条) 使用 UUIDv7:
时间有序 + 幂等去重键。Python 3.13 stdlib 尚无 uuid7,故此处按 RFC 9562 自实现,
且拆分为"纯构造"与"注入式生成"两层,保证可确定性测试 (第 6.2 条: 需要随机性必须显式传入)。

RFC 9562 UUIDv7 位布局 (128 bit):
  | 48 bit unix_ts_ms | 4 bit ver=0b0111 | 12 bit rand_a | 2 bit var=0b10 | 62 bit rand_b |
"""

from __future__ import annotations

import secrets
import uuid
from typing import Annotated

from pydantic import AfterValidator

from .trading_calendar import Clock, SystemClock

__all__ = ["UUID7", "Rng", "SecretsRng", "generate_uuid7", "uuid7", "uuid7_timestamp_ms"]

_UUID7_VERSION = 0x7
_UUID7_VARIANT = 0b10
_MAX_48 = (1 << 48) - 1
_MAX_12 = (1 << 12) - 1
_MAX_62 = (1 << 62) - 1


class Rng:
    """可注入随机源。测试注入确定性桩;生产用 SecretsRng。"""

    def rand_a(self) -> int:  # 12 bit
        raise NotImplementedError

    def rand_b(self) -> int:  # 62 bit
        raise NotImplementedError


class SecretsRng(Rng):
    """密码学随机源 (secrets)。"""

    def rand_a(self) -> int:
        return secrets.randbits(12)

    def rand_b(self) -> int:
        return secrets.randbits(62)


def uuid7(ts_ms: int, rand_a: int, rand_b: int) -> uuid.UUID:
    """纯构造:给定 (ms 时间戳, 12bit rand_a, 62bit rand_b) → 确定的 UUIDv7。

    相同输入逐比特相同输出 (第 6.2 条)。越界输入直接拒绝,避免静默截断污染 ID 空间。
    """
    if not 0 <= ts_ms <= _MAX_48:
        raise ValueError(f"ts_ms 超出 48-bit 范围: {ts_ms}")
    if not 0 <= rand_a <= _MAX_12:
        raise ValueError(f"rand_a 超出 12-bit 范围: {rand_a}")
    if not 0 <= rand_b <= _MAX_62:
        raise ValueError(f"rand_b 超出 62-bit 范围: {rand_b}")

    value = ts_ms << 80
    value |= _UUID7_VERSION << 76
    value |= rand_a << 64
    value |= _UUID7_VARIANT << 62
    value |= rand_b
    return uuid.UUID(int=value)


def generate_uuid7(clock: Clock | None = None, rng: Rng | None = None) -> uuid.UUID:
    """注入式生成:唯一读取时钟+随机源的入口。默认系统时钟 + 密码学随机。"""
    ts_ms = (clock or SystemClock()).now_utc_ms()
    r = rng or SecretsRng()
    return uuid7(ts_ms, r.rand_a(), r.rand_b())


def uuid7_timestamp_ms(u: uuid.UUID) -> int:
    """从 UUIDv7 提取毫秒时间戳 (高 48 bit)。校验版本号,拒绝非 v7。"""
    if u.version != 7:
        raise ValueError(f"非 UUIDv7 (version={u.version}): {u}")
    return u.int >> 80


def _assert_uuid7(u: uuid.UUID) -> uuid.UUID:
    if u.version != 7:
        raise ValueError(f"契约要求 UUIDv7 (第 8.3/11.2 条), 收到 version={u.version}: {u}")
    return u


# 契约字段类型: 强制 UUIDv7。拒绝外部注入的 v4 等非 v7 ID, 守护时间有序 + 幂等去重前提。
UUID7 = Annotated[uuid.UUID, AfterValidator(_assert_uuid7)]
