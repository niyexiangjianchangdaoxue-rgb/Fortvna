# SESSION_LOG

工作会话与事故复盘台账 (第 5.3 / 14 章)。倒序追加。

## 2026-07-15 — Phase 0 bedrock 切片 + 对抗性审查

**背景**: OrbStack 已装、密钥已填, `docker compose up` 起 postgres/redis 实测通过 (pg_isready / redis PONG)。

**实现** (fortvna_core + fortvna_proto, 结构决策见 ADR-001):
- `trading_calendar` (第 12 章)、`ids` UUIDv7 (第 8.3/11.2)、`settings`+600 自检 (第 5.3)、`logging` (第 3.2);
  `control` 状态机契约/优先级 (第 8.1)、`budget` 预算+心跳 (第 7.2)。

**流程纠偏 (重要)**: 本切片由 Claude Code 直接实现, 违反第 14.1 条 (实现应归 Codex, 我只审查)。
用户裁决: **本切片 grandfather 沿用, 下一切片起严格 Codex-first**。已写入 CLAUDE.md 与持久记忆。

**审查 = 一次对抗性验证工作流** (4 lens finder → 逐条独立裁决 → 完备性评审, 10 agents)。确认并已修复:
- **P1 · 第 12.1 红线**: `to_utc_ms` 浮点截断丢 1ms (2004/2038/2039 波段 16-24% 丢失; 2026 恰安全故 CI 未抓)。
  → 改整数域换算 `(dt-纪元)//timedelta(ms)`, 加 2004/2038/2039 回归测试。
- **P2 · 第 7.2/11.3**: 划转限额用 float, 等额上限划转被误拒。→ 改 Decimal, 与账本同口径。
- **P3 · 第 12.4**: `is_funding_settlement` 容差在 UTC 午夜单边失效。→ 改 8h 网格距离, 对称。
- **P3 · 第 8.3/11.2**: 契约静默接受非 v7 UUID。→ 新增 `UUID7` 强制类型, command_id/grant_id 拒绝 v4。
- **P3 · 第 7.2**: 心跳失联仅裸常量。→ 补 `is_cosmos_stale`/`should_minisha_self_pause` 纯函数+边界测试。
- 裁决 REFUTED: FLAT→ACTIVE/PAUSED 出边 (SPEC 明定 FLAT=空仓的 PAUSED, 实现忠实, 无需 ADR)。

**术语状态**: bedrock "已验证" —— ruff/ruff-format/mypy(strict,11 files)/pytest(**57 passed**) 全绿;
P1/P3 修复另经原始失败输入 (2004/2038 whole-ms、午夜前 300ms) 直接复验通过。

## 2026-07-15 — Phase 0 开发环境初始化
- 按第 4 章配置 macOS 开发环境:
  - 工具链: uv / homebrew python@3.13 已在; 新装 direnv / just / gitleaks / pre-commit。
  - ⚠️ `uv python install 3.13` 官方构建下载被网络阻断 (需代理); 当前 workspace 复用 Homebrew python@3.13.13。
  - ⚠️ 容器运行时 (OrbStack/Docker) 尚未安装 —— `just up` 前需 `brew install --cask orbstack`。
- 仓库脚手架 (第 4.2 条): justfile / docker-compose.yml / pyproject.toml(uv workspace) /
  三包 factor_zoo·cosmos·minisha / proto / docs / experiments / tests /
  .pre-commit-config.yaml / .envrc / .gitignore / secrets.env.example / .github/workflows/ci.yml。
- 密钥文件 (D-011): `~/.fortvna/secrets.env` 已创建, chmod 600, 仓库外, 含全部变量名占位。
- 术语状态: 环境脚手架"已实现"(有文件); 依赖尚未 `uv sync`, 钩子尚未 `pre-commit install`。
