# CLAUDE.md — Fortvna 工作约定

> 单点真相是 `docs/FORTVNA_SPEC_v1.0.md`(工程宪法)+ Git 历史。本文件只提炼**每次动手前必须遵守**的铁律,冲突时以 SPEC 为准。

## 角色分工(第 14.1 条,强制)

- **Codex = 实现**:一切业务代码由 Codex 写(GPT-5.x,**推理强度按任务难度分档**)。
- **Claude Code / Opus 4.8(我)= 代码审查**:我**不写业务代码**,只做审查、纠偏、脚手架与环境。
- **Fable 5 = 架构大脑**:决策、拆解、审查,不写业务代码。
- 产出物跨角色流转必须经 **`docs/CODEX_HANDOFF.md`**。
- 落实流程:起草 CODEX_HANDOFF 交接 → 委派 Codex 实现(`codex:rescue` skill / `codex:codex-rescue` agent)→ 我审查。
- **例外**(我可直接做):纯脚手架/配置/环境(justfile、docker-compose、pyproject、CI、.pre-commit)、文档、ADR、审查本身。

## 零信任与单点真相(第 14.2 条)

- 任何行动前先读:SPEC + `docs/DECISIONS/` + 真实 `git log`/`git diff`(不凭记忆);无文件绝不臆断。
- 禁止覆盖用户的无关改动;提交前 `git status` 核对触碰范围。

## 术语红线(第 14.4 条,不得含糊)

- **已实现** = 有代码;**已验证** = 有测试通过且可复跑;**有效** = 有统计证据(链接到具体实验目录)。
- 测试受限(网络/密钥不可用)必须明说,禁止伪造测试结论。涉及杠杆/滑点/爆仓必须如实陈述风险。

## 安全红线(第 5 章)

- 密钥/代理地址/端口/真实资金量 = 敏感物,出现在被 Git 追踪的文件中即 P0 事故。
- 真实密钥只在仓库外 `~/.fortvna/secrets.env`(chmod 600);仓库内只有 `secrets.env.example`(假值)。

## 阶段纪律(第 3 章)

- 按 Phase 0/1/2 引入组件,跳阶段引入视为架构违规。当前:**Phase 0**。

## 其他

- 时间:存储一律 UTC 毫秒;业务日 = Asia/Shanghai;跨日逻辑只走 `fortvna_core.trading_calendar`(第 12 章)。
- 提交:Conventional Commits;一次提交只做一件事;涉及决策的提交引用 ADR 编号(第 14.6 条)。
- 命令入口:`just`(setup/check/lint/typecheck/test/up/down/doctor)。
