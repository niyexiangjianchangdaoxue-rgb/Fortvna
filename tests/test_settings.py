"""settings 测试 (SPEC 第 5.3 条)。不触碰真实 ~/.fortvna/secrets.env。"""

from __future__ import annotations

from decimal import Decimal

import pytest

from fortvna_core import settings as st


def _write_secrets(path, mode=0o600):
    path.write_text("OKX_C_API_KEY=x\n")
    path.chmod(mode)
    return path


def test_missing_file_rejected(tmp_path):
    with pytest.raises(RuntimeError, match="缺失"):
        st.assert_secrets_file_secure(tmp_path / "nope.env")


def test_wrong_permissions_rejected(tmp_path):
    p = _write_secrets(tmp_path / "secrets.env", mode=0o644)
    with pytest.raises(RuntimeError, match="权限"):
        st.assert_secrets_file_secure(p)


def test_correct_permissions_pass(tmp_path):
    p = _write_secrets(tmp_path / "secrets.env", mode=0o600)
    st.assert_secrets_file_secure(p)  # 不抛异常


def test_load_settings_reads_env_and_redacts(tmp_path, monkeypatch):
    env = {
        "OKX_C_API_KEY": "ck",
        "OKX_C_SECRET": "cs",
        "OKX_C_PASSPHRASE": "cp",
        "OKX_M_API_KEY": "mk",
        "OKX_M_SECRET": "ms",
        "OKX_M_PASSPHRASE": "mp",
        "POSTGRES_PASSWORD": "pg",
        "REDIS_PASSWORD": "rd",
        "FORTVNA_PROXY": "http://127.0.0.1:1082",
        "TRANSFER_MAX_SINGLE_USDT": "100.10",
        "TRANSFER_MAX_DAILY_USDT": "500",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    cfg = st.load_settings(check_permissions=False)
    assert cfg.okx_c_api_key.get_secret_value() == "ck"
    assert cfg.fortvna_proxy.get_secret_value() == "http://127.0.0.1:1082"
    # 金额=Decimal 精确解析: 恰等上限的边界比较不得因浮点误判 (第 7.2/11.3 条)
    assert cfg.transfer_max_single_usdt == Decimal("100.10")
    assert Decimal("100.10") <= cfg.transfer_max_single_usdt  # 等额上限划转不被误拒
    # 敏感物脱敏:代理与密钥不得出现在 repr 中 (第 5.1 条)
    assert "127.0.0.1" not in repr(cfg)
    assert "ck" not in repr(cfg)


def test_load_settings_permission_gate(tmp_path, monkeypatch):
    # check_permissions=True 且文件缺失 → 拒绝
    monkeypatch.delenv("OKX_C_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        st.load_settings(secrets_path=tmp_path / "nope.env", check_permissions=True)
