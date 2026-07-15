"""logging 配置冒烟测试 (SPEC 第 3.2 条)。"""

from __future__ import annotations

import json
import logging

import pytest

from fortvna_core.logging import configure_logging, get_logger


def test_json_logging_emits_valid_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level=logging.INFO, json_output=True)
    log = get_logger("test")
    log.info("hello", employee="employee_a", pnl=1)
    out = capsys.readouterr().out.strip()
    record = json.loads(out)  # 必须是合法 JSON 行
    assert record["event"] == "hello"
    assert record["employee"] == "employee_a"
    assert record["level"] == "info"
    assert "timestamp" in record


def test_level_filtering(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(level=logging.WARNING, json_output=True)
    log = get_logger("test")
    log.info("suppressed")
    assert capsys.readouterr().out.strip() == ""
