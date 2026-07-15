# AGENTS.md — Fortvna Agent 工作约定

## 单点真相与改动边界

- 动手前阅读 `docs/FORTVNA_SPEC_v1.0.md`、`docs/DECISIONS/`、`CLAUDE.md`、真实 `git log`
  和 `git diff`。
- 保留用户的无关改动；不顺手重构、格式化或清理任务外代码。
- Python 环境、Ruff、mypy 和 pytest 统一由 `uv`/`uv.lock` 管理。

## Python 严格类型规范

- 所有函数和方法必须有完整的入参与返回值类型；测试函数也必须显式声明
  `-> None`。
- pytest fixture 参数必须声明具体类型，例如：
  - `tmp_path: pathlib.Path`
  - `monkeypatch: pytest.MonkeyPatch`
  - `capsys: pytest.CaptureFixture[str]`
  - `caplog: pytest.LogCaptureFixture`
- 测试内辅助函数必须有完整签名；不得用 `Any` 或宽泛忽略来规避严格检查。
- 故意传入错误类型以验证运行时校验时，只能使用精确错误码并说明原因，例如：
  `# type: ignore[arg-type]  # intentional runtime validation`。
- `pytest.mark.parametrize` 注入的参数也必须在测试函数签名中标注类型。

## Definition of Done

- 开发中先运行最小相关测试；任务完成前必须运行 `just check`。
- `just check` 会执行 Ruff lint/format check、全仓 `mypy --strict`、pytest 和 gitleaks。
- 任一门禁失败时不得宣称“已验证”，也不得创建 commit。
- 需要自动修复 Ruff 问题时显式运行 `just fmt`，pre-commit 本身不静默改写代码。
- 提交前再次检查 `git status` 和 `git diff`，确认只包含本任务改动。
