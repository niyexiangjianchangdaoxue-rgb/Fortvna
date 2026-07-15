"""settings: 密钥与代理配置的唯一加载入口 (SPEC 第 5 章 / 第 4.4 条 / D-011)。

铁律:
- 真实密钥物理上位于仓库外 `~/.fortvna/secrets.env` (chmod 600, 第 5.4 条),由 direnv
  加载进进程环境后被本模块读取;本模块本身不写死任何密钥或代理地址。
- 启动自检:校验密钥文件存在且权限为 600,否则拒绝启动并给出修复命令 (第 5.3 条)。
- 代理为敏感物 (第 5.1 条):FORTVNA_PROXY 用 SecretStr 承载,repr/日志中一律脱敏。

加载是显式函数 (load_settings),不在 import 期产生副作用 —— 使 CI / 测试 (无密钥文件)
可安全导入本模块。权限自检是独立函数 (assert_secrets_file_secure),由应用启动时显式调用。
"""

from __future__ import annotations

import stat
from decimal import Decimal
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = [
    "DEFAULT_SECRETS_PATH",
    "FortvnaSettings",
    "assert_secrets_file_secure",
    "load_settings",
]

# 仓库外单一隐藏密钥文件 (D-011)。展开为绝对路径。
DEFAULT_SECRETS_PATH = Path.home() / ".fortvna" / "secrets.env"


class FortvnaSettings(BaseSettings):
    """从进程环境读取的强类型配置。密钥字段一律 SecretStr,禁止明文泄漏。"""

    model_config = SettingsConfigDict(
        extra="ignore",
        case_sensitive=True,
        frozen=True,
    )

    # Cosmos 通道 (Key-C)
    okx_c_api_key: SecretStr = Field(alias="OKX_C_API_KEY")
    okx_c_secret: SecretStr = Field(alias="OKX_C_SECRET")
    okx_c_passphrase: SecretStr = Field(alias="OKX_C_PASSPHRASE")

    # Minisha 通道 (Key-M: 交易所层面无划转/提币权限, 第 5.2 条)
    okx_m_api_key: SecretStr = Field(alias="OKX_M_API_KEY")
    okx_m_secret: SecretStr = Field(alias="OKX_M_SECRET")
    okx_m_passphrase: SecretStr = Field(alias="OKX_M_PASSPHRASE")

    # 基础设施
    postgres_password: SecretStr = Field(alias="POSTGRES_PASSWORD")
    redis_password: SecretStr = Field(alias="REDIS_PASSWORD")

    # 本地代理 (第 4.4 条, 敏感物 → SecretStr)
    fortvna_proxy: SecretStr = Field(alias="FORTVNA_PROXY")

    # 划转限额 (第 11.3 条)。金额=Decimal, 禁 float: 从字符串环境变量精确解析, 与账本/
    # BudgetGrant 同口径, 保证等额上限的边界比较逐比特精确 (第 6.2/7.2/7.3 条)。
    transfer_max_single_usdt: Decimal = Field(alias="TRANSFER_MAX_SINGLE_USDT")
    transfer_max_daily_usdt: Decimal = Field(alias="TRANSFER_MAX_DAILY_USDT")


def assert_secrets_file_secure(path: Path = DEFAULT_SECRETS_PATH) -> None:
    """启动自检:密钥文件必须存在且权限恰为 600 (第 5.3 条)。否则拒绝启动。"""
    if not path.exists():
        raise RuntimeError(
            f"密钥文件缺失: {path}\n"
            f"修复: mkdir -p {path.parent} && cp secrets.env.example {path} "
            f"&& chmod 600 {path}"
        )
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != 0o600:
        raise RuntimeError(
            f"密钥文件权限不安全: {path} 当前为 {oct(mode)}, 要求 600 (第 5.3 条)。\n"
            f"修复: chmod 600 {path}"
        )


def load_settings(
    *, secrets_path: Path = DEFAULT_SECRETS_PATH, check_permissions: bool = True
) -> FortvnaSettings:
    """应用启动时的唯一配置加载入口。

    check_permissions=True (生产默认) 先执行 600 权限自检;测试可关闭。
    环境变量由 direnv 从 secrets_path 预先加载 (第 4.2 条),本函数读取 os.environ。
    """
    if check_permissions:
        assert_secrets_file_secure(secrets_path)
    # pydantic-settings 自动从进程环境 (direnv 已加载) 按 alias 读取,无需手动传入。
    return FortvnaSettings()
