# Fortvna

全网开源的加密货币量化交易系统,以物理隔离的三子系统实现"研发—治理—执行"分权。
工程宪法见 [`docs/FORTVNA_SPEC_v1.0.md`](docs/FORTVNA_SPEC_v1.0.md) —— 任何行动前必读。

> Fortvna 不承诺盈利。它承诺:每一笔资金暴露都可追溯、可熔断、可审计。

## 快速开始 (macOS, 第 4 章)

```bash
# 1. 工具链 (一次性)
brew install uv direnv just gitleaks pre-commit
brew install --cask orbstack        # 容器运行时

# 2. 密钥文件 (仓库外, D-011) —— 复制模板后填真实值
mkdir -p ~/.fortvna && cp secrets.env.example ~/.fortvna/secrets.env
chmod 600 ~/.fortvna/secrets.env

# 3. 加载环境 + 安装依赖与钩子
direnv allow
just setup

# 4. 自检 + 启动基础设施
just doctor
just up          # postgres:16 + redis:7
```

## 命令入口 (`just`)
`setup` 装依赖+钩子 · `check` 全门禁 · `lint` · `typecheck` · `test` · `up`/`down` 基础设施 · `doctor` 环境自检 · `secrets-scan` gitleaks

## 子系统
- **factor_zoo/** — 兵工厂:纯函数因子库,无状态、无密钥、永不下单
- **cosmos/** — 董事长兼中长线:全局账本、风险预算、熔断、划转发起 (FastAPI)
- **minisha/** — 短线部门:1m 级执行 (asyncio + uvloop)
