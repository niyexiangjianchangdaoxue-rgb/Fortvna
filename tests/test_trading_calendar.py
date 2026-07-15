"""trading_calendar 单元测试 (SPEC 第 12 章)。确定性,无网络无密钥。"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from fortvna_core import trading_calendar as tc


def test_roundtrip_utc_ms() -> None:
    dt = datetime(2026, 7, 15, 3, 30, 0, tzinfo=UTC)
    ms = tc.to_utc_ms(dt)
    assert tc.from_utc_ms(ms) == dt


def test_require_aware_rejects_naive() -> None:
    with pytest.raises(ValueError, match="naive"):
        tc.require_aware(datetime(2026, 7, 15, 0, 0, 0))  # noqa: DTZ001  故意构造 naive
    with pytest.raises(ValueError):
        tc.to_utc_ms(datetime(2026, 7, 15, 0, 0, 0))  # noqa: DTZ001  故意构造 naive


def test_business_day_boundary_utc8() -> None:
    # 2026-07-15 00:00 UTC+8 == 2026-07-14 16:00 UTC
    start_ms = tc.business_day_start_utc_ms(date(2026, 7, 15))
    assert tc.from_utc_ms(start_ms) == datetime(2026, 7, 14, 16, 0, 0, tzinfo=UTC)
    # 恰在边界 → 属于 2026-07-15 业务日
    assert tc.business_day_of(start_ms) == date(2026, 7, 15)
    # 边界前 1ms → 仍属前一业务日
    assert tc.business_day_of(start_ms - 1) == date(2026, 7, 14)


def test_business_day_of_afternoon_utc_crosses_local_date() -> None:
    # 2026-07-15 20:00 UTC == 2026-07-16 04:00 UTC+8 → 业务日 07-16
    ms = tc.to_utc_ms(datetime(2026, 7, 15, 20, 0, 0, tzinfo=UTC))
    assert tc.business_day_of(ms) == date(2026, 7, 16)


def test_next_reset_strictly_after() -> None:
    # 业务日中段 → 下一边界是次日 00:00 UTC+8
    mid = tc.to_utc_ms(datetime(2026, 7, 15, 6, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai")))
    nxt = tc.next_reset_utc_ms(mid)
    assert tc.business_day_of(nxt) == date(2026, 7, 16)
    assert tc.from_utc_ms(nxt).astimezone(tc.BUSINESS_TZ).hour == 0


def test_next_reset_on_exact_boundary_advances() -> None:
    # 恰在边界 → strictly after 语义:返回下一日边界,不原地返回
    start = tc.business_day_start_utc_ms(date(2026, 7, 15))
    nxt = tc.next_reset_utc_ms(start)
    assert nxt == tc.business_day_start_utc_ms(date(2026, 7, 16))
    assert nxt > start


def test_previous_reset_is_business_day_start() -> None:
    ms = tc.to_utc_ms(datetime(2026, 7, 15, 6, 0, 0, tzinfo=tc.BUSINESS_TZ))
    prev = tc.previous_reset_utc_ms(ms)
    assert prev == tc.business_day_start_utc_ms(date(2026, 7, 15))
    assert prev <= ms < tc.next_reset_utc_ms(ms)


def test_reset_interval_is_one_day() -> None:
    ms = tc.to_utc_ms(datetime(2026, 7, 15, 6, 0, 0, tzinfo=tc.BUSINESS_TZ))
    assert tc.next_reset_utc_ms(ms) - tc.previous_reset_utc_ms(ms) == 86_400_000


def test_funding_settlement_utc_hours() -> None:
    for hour in (0, 8, 16):
        ms = tc.to_utc_ms(datetime(2026, 7, 15, hour, 0, 0, tzinfo=UTC))
        assert tc.is_funding_settlement(ms)
    # 非结算时刻
    ms = tc.to_utc_ms(datetime(2026, 7, 15, 3, 0, 0, tzinfo=UTC))
    assert not tc.is_funding_settlement(ms)


def test_funding_settlement_tolerance() -> None:
    ms = tc.to_utc_ms(datetime(2026, 7, 15, 8, 0, 0, tzinfo=UTC)) + 200
    assert not tc.is_funding_settlement(ms)
    assert tc.is_funding_settlement(ms, tolerance_ms=500)


def test_funding_settlement_tolerance_symmetric_across_midnight() -> None:
    # 回归: 容差窗口在 UTC 午夜两侧必须对称 (曾因按日历日枚举而单边漏判)
    midnight = tc.to_utc_ms(datetime(2026, 7, 16, 0, 0, 0, tzinfo=UTC))
    before = midnight - 300  # 2026-07-15 23:59:59.700, 距 07-16 00:00 结算 300ms
    after = midnight + 300
    assert tc.is_funding_settlement(before, tolerance_ms=500)
    assert tc.is_funding_settlement(after, tolerance_ms=500)
    assert not tc.is_funding_settlement(before, tolerance_ms=200)


@pytest.mark.parametrize(
    "dt",
    [
        # 回归: to_utc_ms 浮点截断丢 1ms 的历史波段 (2004/2038/2039), 整数域换算必须逐比特精确
        datetime(2004, 8, 24, 0, 4, 8, 649000, tzinfo=UTC),
        datetime(2038, 6, 22, 21, 6, 31, 160000, tzinfo=UTC),
        datetime(2039, 1, 1, 0, 0, 0, 1000, tzinfo=UTC),
        datetime(2026, 7, 15, 3, 30, 0, 123000, tzinfo=UTC),
    ],
)
def test_whole_ms_roundtrip_bit_exact(dt: datetime) -> None:
    ms = tc.to_utc_ms(dt)
    # datetime → ms 不得丢毫秒
    assert ms == (dt - datetime(1970, 1, 1, tzinfo=UTC)) // timedelta(milliseconds=1)
    # ms → datetime → ms 往返恒等 (第 12.1 / 6.2 条)
    assert tc.to_utc_ms(tc.from_utc_ms(ms)) == ms
    assert tc.from_utc_ms(ms) == dt


def test_sub_ms_floors_deterministically() -> None:
    # 亚毫秒向下取整, 确定且可复现
    dt = datetime(2026, 7, 15, 0, 0, 0, 123999, tzinfo=UTC)  # 123.999 ms
    assert tc.to_utc_ms(dt) == tc.to_utc_ms(datetime(2026, 7, 15, 0, 0, 0, 123000, tzinfo=UTC))


def test_now_utc_ms_injectable_clock() -> None:
    class FakeClock:
        def now_utc_ms(self) -> int:
            return 1_752_547_200_000

    assert tc.now_utc_ms(FakeClock()) == 1_752_547_200_000
