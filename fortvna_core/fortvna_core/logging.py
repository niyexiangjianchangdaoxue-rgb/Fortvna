"""logging: structlog 结构化日志 (JSON) 的唯一配置入口 (SPEC 第 3.2 条)。

全系统 Phase 0 可观测基座:JSON 行日志,便于后续 (Phase 1) 接入 Grafana/OTel。
时间戳以 UTC ISO8601 输出 (与第 12.1 条 UTC 基准一致)。
"""

from __future__ import annotations

import logging

import structlog

__all__ = ["configure_logging", "get_logger"]


def configure_logging(*, level: int = logging.INFO, json_output: bool = True) -> None:
    """进程启动时调用一次。json_output=False 时用彩色控制台渲染 (仅本地调试)。"""
    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """获取绑定 logger。name 通常传 __name__。"""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
