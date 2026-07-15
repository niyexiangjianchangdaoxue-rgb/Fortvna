"""trading_calendar: 时区与业务日的唯一实现 (SPEC 第 12 章 / D-002).

铁律:
- 存储层:一切持久化时间戳 = UTC 毫秒整数 (第 12.1 条)。禁止 naive datetime。
- 业务层:业务日 = Asia/Shanghai 日历日;每日重置 (盈利熔断、"今日不再开仓"解锁、
  对账) 发生于 00:00 UTC+8 (第 12.2 条)。
- 单点:业务代码禁止散落 now() 与手写日界计算 (第 12.3 条);读取"当前时刻"的唯一
  合法入口是本模块的 now_utc_ms()。

本模块除 now_utc_ms()/SystemClock 外全部为纯函数:给定 ts 输入,输出逐比特确定。
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

__all__ = [
    "BUSINESS_TZ",
    "FUNDING_SETTLEMENT_UTC_HOURS",
    "Clock",
    "SystemClock",
    "business_day_of",
    "business_day_start_utc_ms",
    "from_utc_ms",
    "funding_settlement_business_day",
    "is_funding_settlement",
    "next_reset_utc_ms",
    "now_utc_ms",
    "previous_reset_utc_ms",
    "require_aware",
    "to_utc_ms",
]

# 业务日时区 (第 12.2 条)。中国自 1991 年起无夏令时,固定 UTC+8;仍用 zoneinfo 以历史正确。
BUSINESS_TZ = ZoneInfo("Asia/Shanghai")

# UTC 纪元。所有 ms 转换在整数域进行, 严禁浮点中转 (第 12.1 条: 毫秒精度不得丢失)。
_EPOCH_UTC = datetime(1970, 1, 1, tzinfo=UTC)

# OKX 资金费率结算 UTC 固定时刻 (第 12.4 条: 北京 08:00/16:00/24:00 = UTC 00:00/08:00/16:00)。
# 这三个时刻恰是自纪元起的 8 小时网格点 (一天 = 3×8h), 故"是否结算"= ts 是否落在 8h 网格上。
FUNDING_SETTLEMENT_UTC_HOURS: tuple[int, ...] = (0, 8, 16)
_FUNDING_GRID_MS = 8 * 3_600_000


class Clock(Protocol):
    """可注入时钟。测试与纯逻辑禁止直接 datetime.now();通过 Clock 注入。"""

    def now_utc_ms(self) -> int: ...


class SystemClock:
    """读取真实系统时钟的唯一合法实现 (依赖第 4.3 条 NTP 同步)。"""

    def now_utc_ms(self) -> int:
        return to_utc_ms(datetime.now(tz=UTC))


def now_utc_ms(clock: Clock | None = None) -> int:
    """读取"当前时刻"的唯一合法入口 (第 12.3 条)。默认 SystemClock,测试注入假时钟。"""
    return (clock or SystemClock()).now_utc_ms()


def require_aware(dt: datetime) -> datetime:
    """拒绝 naive datetime (第 12.1 条红线)。返回原值以便链式调用。"""
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(f"naive datetime 被禁止 (第 12.1 条): {dt!r}")
    return dt


def to_utc_ms(dt: datetime) -> int:
    """tz-aware datetime → UTC 毫秒整数。naive 输入拒绝。

    整数域换算 (第 12.1 条): 严禁 int(timestamp()*1000) —— 浮点乘积会落在整数下方
    (如 ...648.9999) 被 int() 截断丢 1ms。用 (dt-纪元)//1ms 的 timedelta 整除, 逐比特精确;
    对亚毫秒部分向下取整 (floor, 归入其所在毫秒), 确定且可复现。
    """
    require_aware(dt)
    return (dt.astimezone(UTC) - _EPOCH_UTC) // timedelta(milliseconds=1)


def from_utc_ms(ts_utc_ms: int) -> datetime:
    """UTC 毫秒整数 → tz-aware UTC datetime。整数域构造, 不经浮点。"""
    return _EPOCH_UTC + timedelta(milliseconds=ts_utc_ms)


def business_day_of(ts_utc_ms: int) -> date:
    """给定 UTC 毫秒时间戳,返回其归属的业务日 (Asia/Shanghai 日历日, 第 12.2 条)。"""
    return from_utc_ms(ts_utc_ms).astimezone(BUSINESS_TZ).date()


def business_day_start_utc_ms(business_day: date) -> int:
    """业务日 00:00 UTC+8 对应的 UTC 毫秒时间戳 (当日重置时刻)。"""
    start_local = datetime(
        business_day.year, business_day.month, business_day.day, 0, 0, 0, tzinfo=BUSINESS_TZ
    )
    return to_utc_ms(start_local)


def next_reset_utc_ms(ts_utc_ms: int) -> int:
    """严格晚于 ts 的下一个业务日边界 (00:00 UTC+8) 的 UTC 毫秒时间戳。

    用于盈利熔断计数重置、"今日不再开仓"解锁 (第 10.3 / 7.2 / 12.2 条)。
    'strictly after' 语义:恰好落在边界上时返回下一日边界,保证边界不被跳过或重复触发。
    """
    today = business_day_of(ts_utc_ms)
    today_start = business_day_start_utc_ms(today)
    if ts_utc_ms < today_start:
        # ts 早于本业务日起点 (仅当 DST/历史偏移导致;中国现无 DST) → 本日起点即下一边界。
        return today_start
    return business_day_start_utc_ms(today + timedelta(days=1))


def previous_reset_utc_ms(ts_utc_ms: int) -> int:
    """晚于等于该边界且不晚于 ts 的最近业务日边界 (即 ts 所属业务日的 00:00 UTC+8)。"""
    return business_day_start_utc_ms(business_day_of(ts_utc_ms))


def is_funding_settlement(ts_utc_ms: int, *, tolerance_ms: int = 0) -> bool:
    """ts 是否落在资金费率结算时刻 (UTC 00:00/08:00/16:00, 第 12.4 条)。

    tolerance_ms 允许结算时刻附近的容差窗口 (成交/记账时钟抖动)。默认精确匹配。
    结算时刻 = 自纪元起的 8h 网格点, 故取 ts 到最近网格点的距离即可 —— 该距离在 UTC
    午夜(00:00)两侧天然对称, 修复了按日历日枚举时"午夜前 ts 只与本日 00:00 比较"的单边漏判。
    """
    rem = ts_utc_ms % _FUNDING_GRID_MS  # Python % 对负 ts 亦返回非负余数
    distance = min(rem, _FUNDING_GRID_MS - rem)
    return distance <= tolerance_ms


def funding_settlement_business_day(ts_utc_ms: int) -> date:
    """资金费率事件的统计归属业务日 (第 12.4 条: 按业务日换算,原值仍按 UTC 存储)。"""
    return business_day_of(ts_utc_ms)
