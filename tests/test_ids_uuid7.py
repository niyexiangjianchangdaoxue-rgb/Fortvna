"""UUIDv7 (ids) 单元测试 (RFC 9562, SPEC 第 8.3/11.2 条)。"""

from __future__ import annotations

import uuid

import pytest

from fortvna_core import ids


def test_uuid7_deterministic():
    a = ids.uuid7(1_752_547_200_000, 0xABC, 0x123456789ABCDEF)
    b = ids.uuid7(1_752_547_200_000, 0xABC, 0x123456789ABCDEF)
    assert a == b  # 相同输入逐比特相同 (第 6.2 条)


def test_uuid7_rfc9562_appendix_b2_known_answer():
    # 用 RFC 9562 Appendix B.2 参考 UUID 反解字段后重建, 必须逐比特复现 —— 守护位布局
    ref = uuid.UUID("017F22E2-79B0-7CC3-98C4-DC0C0C07398F")
    ts = ref.int >> 80
    rand_a = (ref.int >> 64) & 0xFFF
    rand_b = ref.int & ((1 << 62) - 1)
    assert ids.uuid7(ts, rand_a, rand_b) == ref
    assert ref.version == 7


def test_uuid7_max_fields_isolate_version_variant():
    # 满位 rand_a/rand_b 不得溢出污染 version/variant 位 (捕捉移位/掩码错误)
    u = ids.uuid7((1 << 48) - 1, (1 << 12) - 1, (1 << 62) - 1)
    assert u.version == 7
    assert (u.int >> 62) & 0b11 == 0b10
    assert ids.uuid7_timestamp_ms(u) == (1 << 48) - 1


def test_uuid7_version_and_variant_bits():
    u = ids.uuid7(1_752_547_200_000, 0xABC, 0x123456789ABCDEF)
    assert u.version == 7
    # RFC 4122/9562 variant = 0b10xx
    assert (u.int >> 62) & 0b11 == 0b10


def test_uuid7_timestamp_roundtrip():
    ts = 1_752_547_200_123
    u = ids.uuid7(ts, 0, 0)
    assert ids.uuid7_timestamp_ms(u) == ts


def test_uuid7_timestamp_rejects_non_v7():
    with pytest.raises(ValueError, match="非 UUIDv7"):
        ids.uuid7_timestamp_ms(uuid.uuid4())


def test_uuid7_time_ordering():
    earlier = ids.uuid7(1_752_547_200_000, 0, 0)
    later = ids.uuid7(1_752_547_200_001, 0, 0)
    # 时间靠前 → 整数值更小 (时间有序性,高 48bit 主导)
    assert earlier.int < later.int


@pytest.mark.parametrize(
    "ts,ra,rb",
    [
        (-1, 0, 0),
        (1 << 48, 0, 0),
        (0, 1 << 12, 0),
        (0, 0, 1 << 62),
        (0, -1, 0),
    ],
)
def test_uuid7_rejects_out_of_range(ts, ra, rb):
    with pytest.raises(ValueError):
        ids.uuid7(ts, ra, rb)


def test_generate_uuid7_injected():
    class FakeClock:
        def now_utc_ms(self) -> int:
            return 1_752_547_200_000

    class FakeRng(ids.Rng):
        def rand_a(self) -> int:
            return 0xABC

        def rand_b(self) -> int:
            return 0x123456789ABCDEF

    u = ids.generate_uuid7(FakeClock(), FakeRng())
    assert u == ids.uuid7(1_752_547_200_000, 0xABC, 0x123456789ABCDEF)


def test_secrets_rng_within_range():
    rng = ids.SecretsRng()
    for _ in range(1000):
        assert 0 <= rng.rand_a() <= (1 << 12) - 1
        assert 0 <= rng.rand_b() <= (1 << 62) - 1
