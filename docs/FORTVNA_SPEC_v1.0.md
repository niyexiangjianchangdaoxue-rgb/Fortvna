# Fortvna 量化交易系统项目企划与技术规范书 v1.0

| 项 | 值 |
|---|---|
| 文档状态 | Accepted(工程宪法,对所有人类与 AI 参与者具有强制约束力) |
| 生效日期 | 2026-07-15 |
| 时区基准 | 业务日 = Asia/Shanghai (UTC+8);存储 = UTC 毫秒时间戳 |
| 修订机制 | 任何修改必须以 ADR(附录 B 模板)形式提交,经用户批准后合入,禁止静默修改 |
| 单点真相 | 本文档 + Git 历史。任何 AI Agent 行动前必须读取二者,无文件绝不臆断 |

---

## 第 0 章 决策台账(Locked Decisions)

以下决策已经用户逐条确认,任何后续产出与之冲突即视为缺陷,直接打回。

| ID | 决策 | 内容 | 状态 |
|----|------|------|------|
| D-001 | 员工控制语义 | 三档:PAUSE / FLATTEN / FREEZE(定义见第 8 章) | 已锁定 |
| D-002 | 时区基准 | 业务日 UTC+8;所有持久化时间戳一律 UTC 毫秒;展示层转换 | 已锁定 |
| D-003 | 部署目标 | 本地 macOS 开发机为主,Docker Compose 单机编排;云端仅预留迁移路径 | 已锁定 |
| D-004 | Minisha 语言 | Python 3.13 + asyncio/uvloop,全系统单语言;Rust 仅为 Phase 2 热路径备选(论证见附录 C-1) | 已锁定 |
| D-005 | 回测引擎(精算层) | OPEN:nautilus_trader 两日评估 spike(验收标准见附录 C-2)后定夺;spike 失败则回退最小化自研(bar 级起步) | 待定 |
| D-006 | 实盘路径 | 不强制 OKX 模拟盘;以"影子模式 + 小资金阶梯"作为工程门禁(第 13 章) | 已锁定 |
| D-007 | 初始资金 | < 1000 USDT。全部风控默认值按此量级设计,并触发第 10 章"小资金现实约束" | 已锁定 |
| D-008 | 控制通道 | 双通道:Cosmos 面板主通道 + 本地应急通道(第 8 章) | 已锁定 |
| D-009 | 粗筛回测工具 | vectorbt 限定于评估沙箱,Pandas 不得渗入 factor_zoo 核心(附录 C-3) | 已锁定 |
| D-010 | TradingView 定位 | 仅限人工看图核对,永远不得作为“已验证/有效”的证据来源(附录 C-3) | 已锁定 |
| D-011 | 密钥与代理存放 | 全部密钥 + 代理配置集中于仓库目录之外的单一隐藏文件 `~/.fortvna/secrets.env`(chmod 600),物理上永不可能入库(第 5.4 条) | 已锁定 |

---

## 第 1 章 全局愿景与双层交易拓扑

### 1.1 愿景

Fortvna 是一个全网开源的、模拟现代资管公司权力层级的加密货币量化交易系统。它以物理隔离的三子系统实现"研发—治理—执行"分权,以强制的统计验证门禁对抗过拟合与自欺,以小资金实盘阶梯对抗理论与现实的鸿沟。

Fortvna 不承诺盈利。它承诺的是:每一笔资金暴露都可追溯、可熔断、可审计;每一个"有效"的宣称背后都有统计证据。

### 1.2 双层交易拓扑

```
                    ┌──────────────────────────────┐
                    │        factor_zoo(兵工厂)     │
                    │  纯函数因子库 / IC·IR 评估      │
                    │  无状态·无密钥·永不下单         │
                    └──────┬───────────────┬───────┘
                     因子/信号研究          因子/信号研究
                           ▼               ▼
   ┌───────────────────────────┐   ┌───────────────────────────┐
   │  Cosmos(董事长/中长线)     │   │  Minisha(短线交易部门)     │
   │  宏观层:日/周级             │   │  微观层:1m 级              │
   │  · 全局唯一账本             │──▶│  · 部门总监(调度)          │
   │  · 风险预算下发/熔断         │指令│  · Employee A / B(策略)   │
   │  · 长线自营(独立 API Key)  │◀──│  · 独立 API Key            │
   └────────────┬──────────────┘心跳└─────────────┬─────────────┘
                │                                │
                ▼                                ▼
         OKX V5 API(Key-C)               OKX V5 API(Key-M)
```

### 1.3 权力与资金流向铁律

1. 风险预算单向下行:Cosmos → Minisha 总监 → 员工。下级永远无权自行扩大预算。
2. 利润单向上行沉淀:Minisha 定期向 Cosmos 上缴利润。Cosmos 永不自动向下再注资;任何向下划转必须由人工在管理面板显式发起并通过第 11 章划转协议。
3. 熔断权单向下压:Cosmos 可熔断 Minisha 任意员工或整个部门;Minisha 无权反向影响 Cosmos。
4. 全系统最高优先级指令:人工"今日不再开仓"按钮,覆盖一切自动逻辑。

---

## 第 2 章 三子系统职责边界(权力拓扑)

| 子系统 | 角色 | 职责 | 明令禁止 |
|--------|------|------|----------|
| factor_zoo | 兵工厂 | 因子定义、计算、IC/IR/衰减评估;统一数据获取抽象层 | 持有任何 API Key 的交易/划转权限;持有状态;下单;读取账本 |
| Cosmos | 董事长兼中长线基金经理 | 全局唯一账本;宏观趋势判断;风险预算分配与熔断;长线自营交易;资金划转发起方 | 参与 1m 级短线;将凯利公式结论下放给 Minisha 作杠杆合理化依据 |
| Minisha | 短线部门(总监 + 员工) | 1m 级执行;微观结构判断;员工调度与休市决策 | 宏观判断;使用凯利公式;发起资金划转;超出 Cosmos 下发预算;持有提币权限 |

边界判据(出现争议时的仲裁规则):任何涉及"钱从哪来、给谁、给多少"的逻辑属于 Cosmos;任何涉及"这一分钟买还是卖"的逻辑属于 Minisha;任何"信号本身是否有预测力"的逻辑属于 factor_zoo。一段代码若同时命中两条,说明模块划分错误,必须拆分而非注释说明。

---

## 第 3 章 技术栈清单与分阶段引入时机

### 3.1 总原则

单人 + AI 团队的首要死因不是策略失效,而是基础设施债务。目标态技术栈(3.2)全部保留,但按 Phase 0/1/2 强制排序引入。跳阶段引入组件视为架构违规。

### 3.2 目标态技术栈总表

| 层 | 组件 | 归属 | 引入阶段 |
|----|------|------|----------|
| 语言核心 | Python 3.13(uv 管理)— 全系统核心地位 | factor_zoo / Cosmos | Phase 0 |
| 语言核心 | Python 3.13 + asyncio + uvloop(附录 C-1) | Minisha | Phase 0 |
| 服务契约 | proto 消息定义(v1 进程内命令总线,保留跨进程拆分能力) | Cosmos↔Minisha | Phase 0 |
| 回测·粗筛 | vectorbt(评估沙箱内,D-009) | factor_zoo | Phase 1 |
| 回测·精算 | nautilus_trader(候选)或最小化自研 —— 待 spike(附录 C-2)定夺 | Minisha | Phase 0–1 |
| 性能备选 | Rust + PyO3/maturin(仅当 profiling 证明 Python 热路径成瓶颈) | Minisha | Phase 2 |
| 数据计算 | Polars(彻底替代 Pandas,禁止 Pandas 入库) | factor_zoo | Phase 0 |
| 数据存储 | Parquet 文件 + DuckDB(本地时序查询) | factor_zoo | Phase 0 |
| 数据存储 | ClickHouse(时序仓库,数据量 > 单机 Parquet 舒适区后) | factor_zoo | Phase 1 |
| 离线对象存储 | MinIO / S3 | factor_zoo | Phase 2 |
| 关系账本 | PostgreSQL 16(Docker Compose 内) | Cosmos | Phase 0 |
| 状态缓存 | Redis 7 | Cosmos | Phase 0 |
| 服务框架 | FastAPI + Pydantic v2(100% 强类型,`model_config = ConfigDict(strict=True)`) | Cosmos | Phase 0 |
| 编排调度 | cron / 简单守护进程 → Dagster 或 Prefect | factor_zoo | Phase 2 |
| 实验追踪 | 本地 JSON/Parquet 实验记录 → MLflow | factor_zoo | Phase 1 |
| 可观测 | structlog 结构化日志(JSON) | 全系统 | Phase 0 |
| 可观测 | Prometheus + Grafana + OpenTelemetry 全链路 | 全系统 | Phase 1 |
| 密钥管理 | `~/.fortvna/secrets.env`(仓库外隐藏文件)+ direnv 加载 | 全系统 | Phase 0 |
| 密钥管理 | HashiCorp Vault | 生产 | Phase 2 |
| CI/CD | GitHub Actions:ruff + mypy(strict)+ pytest + gitleaks | 全系统 | Phase 0 |
| 本地钩子 | pre-commit:ruff、mypy、gitleaks、禁止大文件 | 全系统 | Phase 0 |
| 容器编排 | Docker Compose(postgres、redis;后续 clickhouse、grafana) | 全系统 | Phase 0 |
| 属性测试 | hypothesis | 全系统 | Phase 1 |
| 交易接口 | OKX V5 REST + WebSocket(公共行情 + 私有订单频道) | Cosmos / Minisha | Phase 0 |

### 3.3 Phase 0 替代论证(ADR 摘要)

ClickHouse → Parquet + DuckDB:< 1000 USDT 资金量级对应的数据规模(单币种 1m + tick),单机列式文件完全够用,且 DuckDB 可直接查询 Parquet、零运维。迁移路径:表结构从第一天起按 ClickHouse 兼容的宽表设计,迁移时仅重放 Parquet。

Dagster/MLflow 延后:Phase 0 的实验数量由人工驱动,一个约定目录结构(`experiments/{date}_{name}/`,内含 config.json + metrics.parquet + report.md)足以保证可追溯。当实验并发量或调度依赖复杂到人工不可维护时,再引入,届时目录结构可直接被 MLflow 收编。

Rust → Python(附录 C-1):1m 级策略的端到端延迟由网络与交易所主导(数十毫秒量级),语言层的微秒级差异不可测量;单人 + AI 协作下,Rust 的代码返工率与双语言维护税是真实成本,换来的延迟收益是想象的。Rust 保留为 Phase 2 热路径升级选项,触发条件 = profiling 实测证明 Python 成为瓶颈。

Vault 延后:本地单机开发,仓库外密钥文件 + macOS 全盘加密 + OKX API Key 权限最小化(第 5 章)的组合风险敞口可控。Vault 在迁移云端时同步引入。

---

## 第 4 章 macOS 开发环境配置规范

### 4.1 基础工具链(一次性)

```bash
# 1. Homebrew(若未装)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 核心工具
brew install uv direnv just gitleaks pre-commit

# 3. 容器运行时(二选一;Apple Silicon 推荐 OrbStack,更省资源)
brew install --cask orbstack        # 或 docker

# 4. Python 3.13 由 uv 托管,不污染系统
uv python install 3.13
```

### 4.2 仓库初始化约定

```
fortvna/
├── justfile                  # 唯一命令入口:just setup / test / lint / up / down
├── docker-compose.yml        # postgres:16, redis:7(Phase 1 追加 clickhouse, grafana)
├── secrets.env.example       # 全部变量名 + 假值,入库(真实密钥文件在仓库外,见 5.4)
├── .envrc                    # direnv:dotenv ~/.fortvna/secrets.env
├── .pre-commit-config.yaml   # ruff / mypy / gitleaks / check-added-large-files
├── pyproject.toml            # uv workspace 根
├── factor_zoo/               # Python 包
├── cosmos/                   # Python 包(FastAPI)
├── minisha/                  # Python 包(asyncio 执行服务)
├── proto/                    # 服务消息契约单点真相(v1 进程内使用)
├── docs/
│   ├── FORTVNA_SPEC_v1.0.md  # 本文档
│   ├── DECISIONS/            # ADR,每决策一文件
│   ├── CODEX_HANDOFF.md
│   └── SESSION_LOG.md
└── experiments/              # gitignore 大文件,报告 md 入库
```

### 4.3 macOS 专项注意

1. Apple Silicon:全 Python 栈下无交叉编译问题;Phase 2 若引入 PyO3 扩展,CI 必须同时构建 aarch64 与 amd64 两种架构的 wheel,防止"本机能跑、云端崩溃"。
2. 时钟同步:交易系统时间戳依赖本机时钟。强制开启系统 NTP,并在 Minisha 启动自检中比对 OKX 服务器时间(`/api/v5/public/time`),偏差 > 500ms 拒绝启动。
3. 休眠陷阱:macOS 合盖休眠会挂起进程,导致 WebSocket 断流与持仓无人看管。实盘运行期间强制 `caffeinate` 或在系统设置中禁用休眠;Minisha 必须实现断线自动重连 + 重连后全量对账(REST 拉取当前持仓与挂单,与本地状态比对,不一致即告警并进入 PAUSED)。

### 4.4 网络代理规范(强制)

本机对 OKX 的全部访问(REST 与 WebSocket)必须经由本地代理,代理地址与端口不写死在任何代码或仓库文件中,统一从 `~/.fortvna/secrets.env` 读取:

```dotenv
FORTVNA_PROXY=http://127.0.0.1:1082      # 本地代理(如 Shadowrocket HTTP 端口)
```

1. 单点读取:唯一的 `net` 模块负责构造带代理的 HTTP/WS 客户端;业务代码禁止自行创建连接或散落读取代理配置。
2. 启动自检:经代理请求 OKX `public/time`,失败即拒绝启动;运行期代理健康探测周期化执行。
3. 代理失联处置:行情断流即意味着持仓失明,全体员工立即自动 PAUSED + 持续告警;代理恢复后先全量对账再允许 RESUME。
4. 延迟如实陈述:代理链路为往返增加数十毫秒量级延迟,在 1m 级别可接受,但必须纳入滑点统计口径,不得假装它不存在。

---

## 第 5 章 开源安全隔离规范(第一红线)

### 5.1 密钥与敏感物清单(永不入库)

以下内容出现在任何被 Git 追踪的文件中,即为 P0 级事故:OKX API Key / Secret / Passphrase;数据库与 Redis 密码;真实账户 UID;真实资金量与成交明细;**代理地址、端口及任何网络拓扑信息**;私有策略参数的实盘取值(参数搜索空间可开源,实盘选定值按敏感物处理,一并存放于密钥文件)。

### 5.2 双 Key 权限最小化矩阵

| | Key-C(Cosmos) | Key-M(Minisha) |
|---|---|---|
| 读取行情/账户 | 允许 | 允许 |
| 交易(下单/撤单) | 允许 | 允许 |
| 资金划转 | 允许(唯一划转发起方) | **禁止(创建 Key 时不勾选)** |
| 提币 | **禁止** | **禁止** |
| IP 白名单 | 强制绑定 | 强制绑定 |

两把 Key 对应 OKX 账户内相互隔离的资金账户/子账户结构,保证 Minisha 爆仓的最大损失被物理限制在其被分配的预算内。

### 5.3 工程强制手段

1. pre-commit 阶段 gitleaks 全量扫描,CI 阶段二次扫描,双保险。
2. `secrets.env.example` 维护全部变量名与假值;新增配置项未同步该文件即 CI 失败。
3. 密钥文件权限自检:程序启动时校验 `~/.fortvna/secrets.env` 存在且权限为 600,否则拒绝启动并提示修复命令。
4. 泄漏应急预案(写入 runbook):任何疑似泄漏 → 立即在 OKX 后台吊销该 Key → 轮换 → 审计泄漏窗口内全部账户流水 → 在 SESSION_LOG.md 记录事故复盘。历史提交中出现过的密钥即视为已泄漏,吊销而非改写历史了事。

### 5.4 密钥与代理的统一存放(D-011)

一切密钥与代理配置集中于**仓库目录之外**的单一隐藏文件:

```
~/.fortvna/secrets.env    # chmod 600,包含:
  OKX_C_API_KEY / OKX_C_SECRET / OKX_C_PASSPHRASE      # Cosmos 通道
  OKX_M_API_KEY / OKX_M_SECRET / OKX_M_PASSPHRASE      # Minisha 通道
  POSTGRES_PASSWORD / REDIS_PASSWORD
  FORTVNA_PROXY
```

设计依据:gitignore 是一道可被误操作绕过的软防线(`git add -f`、规则改坏、换机器忘配),而**文件物理上不在仓库目录内,则任何 git 操作都不可能将其纳入追踪**——这是"永远不要提交"的最强保证。仓库内的 `secrets.env.example` 只含变量名与假值;gitleaks 与 `.gitignore` 中的 `*.env` 规则作为纵深防御保留。换机迁移 = 手工复制该文件 + 重设 600 权限,不走任何同步盘。

---

## 第 6 章 factor_zoo 因子体系与纯函数开发规约

### 6.1 因子分层

| 层 | 定义 | 示例 |
|----|------|------|
| L0 原始特征 | 对行情的无参/低参变换 | 收益率、成交量 z-score、EMA 族 |
| L1 复合因子 | L0 的有假设组合 | 实体穿透强度、R_decay、插针形态分 |
| L2 信号 | 带阈值与方向的可交易判定 | Employee A/B 的入场信号 |

L2 信号是 factor_zoo 的最终产品,经统计门禁(第 13 章)后方可被 Minisha 消费。Minisha 内不允许出现任何未在 factor_zoo 注册与验证过的信号逻辑。

### 6.2 纯函数规约(违反任一条即打回)

1. 统一签名:`def factor_xxx(df: pl.DataFrame, params: XxxParams) -> pl.Series`,`XxxParams` 为 frozen Pydantic 模型。
2. 禁止一切 IO、网络、全局可变状态、`datetime.now()`、随机数(需要随机性必须显式传入 seed)。
3. 相同输入必须逐比特相同输出;每个因子必须附带一条以固定 fixture 验证确定性的测试。
4. 未来函数三查:不得使用当根未收盘数据;滚动窗口一律右对齐;任何 shift 方向错误按 P0 缺陷处理。
5. 数据获取与因子计算物理分层:`okx_client` 等数据抽象层单独成包,因子函数只见 DataFrame,不知数据来源。
6. 注册制:`@register_factor` 装饰器 + 自动发现工厂(自建 FactorPlugin 体系);每个因子入库必须同时提交 Rank IC、IR、衰减分析报告,且全部指标以扣除费率后口径计算。

---

## 第 7 章 Cosmos 双重状态机设计

### 7.1 状态机 A:长线自营交易

```
IDLE ──宏观信号确认──▶ ACCUMULATING ──目标仓位达成──▶ HOLDING
 ▲                                                      │
 │◀──清仓完成── REDUCING ◀──减仓/离场信号或风控触发────────┘
```

约束:分数凯利(上限 0.25 倍全凯利)**只存在于此状态机**,输入为 Cosmos 自身的长线胜率/赔率估计,输出为自营仓位与全局风险预算。方法论对齐《击败庄家》的资金管理思想:优势不确定时下注归零,优势确定时也只下分数注。状态转换全部落审计日志(PostgreSQL append-only 表)。

### 7.2 状态机 B:对 Minisha 的宏观风控

```
NORMAL ──宏观恶化──▶ RESTRICTED(预算↓)──继续恶化──▶ HALTED(预算=0,禁新开仓)
   ▲                      │                            │
   └──────宏观修复─────────┘        人工按钮或极端风险 ──▶ EMERGENCY_STOP
                                                (全员 FLATTEN,当日锁死)
```

1. 预算下发协议:命令总线消息 `BudgetGrant{employee_id, budget_usdt, valid_until, grant_id}`,带有效期,过期未续期自动视为预算归零——失联即收权。
2. 心跳:Minisha 每 5s 上报;Cosmos 连续 3 次未收到即将该部门标记 STALE 并告警;Minisha 侧对称地在失去 Cosmos 心跳 30s 后自动进入全员 PAUSED(自我保护,不平仓,等待人工)。
3. `EMERGENCY_STOP` = "今日不再开仓"按钮的系统实现,优先级高于一切自动逻辑,解除只能由人工在次一业务日(UTC+8)之后操作。

### 7.3 全局账本

复式记账最小实现:`ledger_entries(entry_id, ts_utc, account, direction, amount, currency, ref_type, ref_id)`,任何资金事件(成交、手续费、资金费率、划转)必须成对入账,每日 00:00(UTC+8)对账任务比对内部账本与 OKX REST 账户快照,差异超阈值即告警并冻结划转功能。

---

## 第 8 章 Minisha 员工状态机与运行时控制按钮(D-001/D-008)

### 8.1 员工四状态机

| 状态 | 新开仓 | 存量持仓管理(止盈/止损/TimeStop) | 撤单 | 语义 |
|------|--------|----------------------------------|------|------|
| ACTIVE | 允许 | 运行 | 允许 | 正常执行 |
| PAUSED | **禁止** | **继续运行** | 允许 | 停止进攻,防守逻辑照常,持仓自然了结 |
| FLATTENING | 禁止 | 立即市价平仓 + 撤销全部挂单 | 强制 | 过渡态,完成后自动进入 FLAT(空仓的 PAUSED) |
| FROZEN | 禁止 | **全部停止(不开、不平、不撤)** | 禁止 | 人工完全接管,系统只读 |

转换矩阵:ACTIVE ⇄ PAUSED;{ACTIVE, PAUSED} → FLATTENING → FLAT;任意状态 → FROZEN;FROZEN 解除必须人工二次确认并指定目标状态。命令优先级:FREEZE > FLATTEN > PAUSE > RESUME;`EMERGENCY_STOP`(全局)> 一切员工级命令。

FROZEN 高危警告(强制实现):冻结意味着持仓暴露在 5 倍杠杆市场中且无任何程序化保护。进入 FROZEN 需在 UI 上二次确认(输入员工 ID 全名);冻结期间系统每 60s 发出一次持续告警(日志 + 面板红色横幅 + 未来可接 Telegram),直至解除。FROZEN 是给"程序行为已不可信,任何自动动作都可能更糟"的场景准备的,不是日常操作。

### 8.2 双通道控制架构

```
[主通道] Cosmos FastAPI 面板 ──HTTP──▶ Cosmos ──命令总线 ControlCommand──▶ Minisha 总监 ──▶ 员工
[应急通道] 本地 CLI: minisha-ctl ──Unix Domain Socket(仅本机)──▶ Minisha 管理端口 ──▶ 员工
```

1. 主通道:面板上每个员工一行,显示状态灯(绿 ACTIVE / 黄 PAUSED / 橙 FLATTENING / 红 FROZEN)、当前持仓、当日盈亏、剩余预算,以及 PAUSE / FLATTEN / FREEZE / RESUME 四按钮。FLATTEN 与 FREEZE 需二次确认弹窗。
2. 应急通道:`minisha-ctl flatten employee_a` 直连执行服务的本地管理 socket,**绕过面板与 HTTP 层**。存在理由:Web 面板、浏览器、API 层任何一环故障时,控制权不得丢失;未来 Cosmos/Minisha 拆分为独立进程后,该通道自动升级为跨进程兜底。仅监听 Unix socket,不开 TCP 端口,天然限制为本机操作。
3. 命令协议:`ControlCommand{command_id(UUIDv7), target, action, issued_by, ts_utc}`。幂等:同 command_id 重放不产生二次动作。全部命令与执行结果写审计日志。两通道命令在 Minisha 内汇聚为单一命令队列,按优先级 + 时间序处理,不存在双写竞态。
4. 执行时限:PAUSE 生效 ≤ 1 个事件循环;FLATTEN 从受理到全部市价单发出 ≤ 2s(超时即告警并升级 FROZEN 待人工)。

---

## 第 9 章 首批员工策略:信号流打分模型与执行流

### 9.0 诚实前置(术语红线适用)

截至本文档签发,Employee A 与 Employee B 的全部信号假设**证据状态为零**:既无肯定证据,也无否定证据。两策略当前状态均为"**已定义**"——既非"已实现",更非"已验证"或"有效"。任何文档、commit message、交接说明中对二者使用"有效"一词而无统计证据链接,按契约违规处理。

### 9.1 参数寻优的多目标打分函数

对每组候选参数 θ,在 Walk-Forward 训练窗内计算(全部口径扣除 taker 费率与保守滑点假设):

```
S(θ) = w1·WinRate + w2·CalmarVariant − w3·MaxConsecLossPenalty − w4·HoldTimePenalty
CalmarVariant = 年化收益 / max(最大回撤, floor)     # floor 防止零回撤除法爆炸
MaxConsecLossPenalty = f(最大连亏次数)              # 凸惩罚,连亏越长惩罚增速越快
HoldTimePenalty = g(平均持仓分钟数)                 # 短线部门,持仓时间本身是风险
```

权重 w1..w4 本身属于敏感参数,搜索空间入库、实盘取值不入库(第 5.1 条)。样本内最优 θ 无任何地位,只有验证窗存活的 θ 才进入下一轮。

### 9.2 Employee A:微观动量突破

信号条件(全部满足才触发,factor_zoo L2 注册):单根或连续两根 1m K 线**实体**(非影线)自下而上/自上而下穿透 EMA5/10/20 三线;同期成交量异动 Z_vol(待建 `z_vol` 因子)突破阈值 Z*;方向与穿透方向一致。

执行流:信号 → 总监核验(员工 ACTIVE?预算充足?全局无 HALTED?)→ 按第 10 章三取小定量 → 限价追单或市价(由滑点统计决定)→ 挂硬止损 → TimeStop 计时开始 → 触发止损/止盈/TimeStop 任一即离场。TimeStop 为无条件强制平仓,不接受"再等一根"。

### 9.3 Employee B:衰竭均值回归

环境门控:4h 级别判定为震荡(ADX 低于阈值或布林带宽收敛,具体由 factor_zoo 验证择一);趋势环境下该员工整体休眠。

信号条件:1m 级极端插针暴跌(振幅与下影线比例双阈值)→ **等待二底确认**(第二次探底不创显著新低)→ 成交量衰减比 R_decay < 0.5(第二底量能 / 第一底量能)→ 三者齐备才入场做多。

执行流:入场 → 止盈目标 = 中位 EMA(EMA10)修复位 → 硬止损 = 结构性破位(二底最低点下方缓冲带)→ 止损一经挂出不得下移(继承"止损不可变"铁律)。

---

## 第 10 章 仓位管理与杠杆铁律

1. 开仓量公式(Minisha 每笔):`size = MIN(Cosmos 下发预算派生量, 全仓 5 倍杠杆物理上限派生量, 员工剩余预算)`。凯利公式的任何形式**禁止**出现在 Minisha 代码中;5 倍杠杆是物理上限而非目标,严禁以凯利结论为其作事后合理化。
2. 小资金现实约束(D-007,< 1000 USDT):
   - 合约规格预检:Minisha 启动时拉取目标合约 `instruments` 元数据(ctVal / minSz / lotSz / tickSz),若三取小结果 < 交易所最小下单量,**拒绝开仓并记录**,严禁向上凑整到最小单量——凑整即变相突破预算。
   - 费率现实:OKX 永续 taker 双边费率合计约 0.1% 量级,1m 级策略单笔预期毛利往往与之同数量级。统计验证与打分一律以净费率口径进行;净口径期望为负的参数组直接淘汰,无论毛口径多漂亮。
   - 全损承受声明:该资金量级应视为"可全损的学费"。这一定位写入文档,不写入侥幸。
3. 每日盈利熔断:当日(UTC+8 业务日)已实现盈利达标 → 自动停止新开仓,存量按防守逻辑了结;与人工 EMERGENCY_STOP 相互独立、互不解除。

---

## 第 11 章 资金划转协议(Cosmos ⇄ Minisha)

1. 唯一发起方 Cosmos(Key-M 无划转权限,交易所层面物理保证)。
2. 幂等:`transfer_id`(UUIDv7)作为 OKX clOrdId 级去重键;重放同 id 不产生第二次划转。
3. 限额:单笔上限与业务日累计上限为密钥文件配置项,超限拒绝且告警。
4. 状态机:`REQUESTED → SUBMITTED → CONFIRMED / FAILED → (FAILED 时) ROLLBACK_CHECKED`。SUBMITTED 后网络超时不得盲目重试,必须先以 REST 查询划转状态再决策——"不确定成功与否"时的重试是重复划转事故的头号来源。
5. 审计:全生命周期事件写 append-only 审计表,并在复式账本成对入账;每日对账(第 7.3 条)覆盖划转科目。

---

## 第 12 章 时区规范(D-002,红线解除条件)

1. 存储层:一切持久化时间戳 = UTC 毫秒整数(或带 tz 的 UTC datetime)。禁止 naive datetime,CI 中以 ruff 自定义规则/代码审查双重把关。
2. 业务层:业务日 = Asia/Shanghai 日历日;每日重置(盈利熔断计数、"今日不再开仓"解锁、对账)发生于 00:00 UTC+8。
3. 单点实现:唯一的 `trading_calendar` Python 模块提供 `current_business_day()` / `next_reset_ts()`;业务代码禁止散落 `now()` 与手写日界计算。
4. 外部事件注记:OKX 资金费率结算为 UTC 固定时刻(对应北京时间 08:00 / 16:00 / 24:00);资金费率事件入账时间一律按 UTC 原值存储,统计归属日按业务日换算。
5. 红线解除声明:本章即"时区基准定义"。自本文档签发起,跨日逻辑允许开发,但任何绕过 `trading_calendar` 的私自实现仍属违规。

---

## 第 13 章 测试、Walk-Forward 与实盘迭代规程

### 13.1 测试金字塔

单元测试(纯函数因子、状态机转换矩阵全覆盖、划转幂等)→ 属性测试(hypothesis:任意输入下状态机不可达非法状态、账本恒等式)→ 集成测试(命令总线契约、OKX client 对录制 fixture 回放)→ 回测。CI 全绿是合并的必要条件,不是充分条件。

### 13.2 回测三防

未来函数(第 6.2 条三查 + 专项审查清单)、幸存者偏差(标的选择须记录选择时点的可得信息)、过拟合(参数搜索必须报告搜索空间大小与验证窗存活率;只报最优组=造假)。

### 13.3 Walk-Forward 规程

窗口每 6.5 天滚动;训练窗与验证窗物理隔离,验证窗数据在寻优过程中不可见;统计门槛:验证窗信号收益 t 检验 p < 0.05 **且**样本量 ≥ 100 笔,二者缺一即判定"证据不足",禁止措辞升级。参数更新为原子发布:新参数写入版本化配置,员工在空仓时点热切换,持仓中不换参。

### 13.4 实盘阶梯(D-006 的工程门禁)

用户已选择小资金直接实盘,系统据此设置如下不可跳过的阶梯,以代码层 flag 强制:

| 阶段 | 条件 | 内容 |
|------|------|------|
| S0 影子模式 | WF 统计门槛通过 | 接实时行情、完整跑信号与虚拟成交,**不发真实订单**,≥ 5 个业务日;虚拟成交与盘口对照估计真实滑点 |
| S1 最小实盘 | S0 净口径为正 | 单员工、交易所最小下单量、预算上限极低;≥ 5 个业务日 |
| S2 预算爬坡 | S1 净口径为正且回撤达标 | 按预设阶梯提升预算;任一阶段回撤超阈值自动降回上一阶段 |

未通过统计门禁的策略在代码上不具备接入实盘通道的能力(编译期/启动期 flag,而非口头约定)。

---

## 第 14 章 AI 团队协同开发硬性契约

1. 角色分工:Fable 5 = 架构大脑(决策、拆解、审查、纠偏,**不写业务代码**);Claude Code / Opus 4.8 = 代码审查;Codex = 实现。产出物跨角色流转必须经 `docs/CODEX_HANDOFF.md`。
2. 零信任与单点真相:任何 Agent 行动前必须读取本文档 + `docs/DECISIONS/` + 真实 Git 历史(`git log`/`git diff`,不凭记忆);无文件绝不臆断;禁止覆盖用户的无关改动(提交前 `git status` 核对触碰范围)。
3. 歧义阻断:凡歧义可能改变交易语义、资金风险或测试结论 → 停止,向用户提问,拿到答复并记入决策台账后再动。
4. 术语红线:"已实现"=有代码;"已验证"=有测试通过且可复跑;"有效"=有统计证据(链接到具体实验目录)。测试受限(如网络、密钥不可用)必须明说,禁止以任何形式伪造测试结论。
5. 风险披露:涉及杠杆、滑点、资金费率、爆仓的产出必须如实陈述风险,禁止以乐观措辞稀释。
6. 提交规范:Conventional Commits;一次提交只做一件事;涉及决策的提交必须引用 ADR 编号。

---

## 第 15 章 风险披露(如实陈述,永久有效)

1. 杠杆与爆仓:全仓 5 倍杠杆下,不利方向约 20% 的价格波动(未计费用与资金费率)即可击穿保证金;加密货币 1m 级别出现该幅度波动并不罕见。
2. 资金费率:永续合约持仓跨结算时点将支付/收取资金费率,对短线策略是噪声、对隔夜持仓可能是显著成本。
3. 滑点与流动性:小市值或新上线合约盘口稀薄,市价平仓(FLATTEN)在极端行情下的实际成交价可能显著劣于预期;FLATTEN 是止血手段,不是无损开关。
4. 信号风险:截至签发日,系统内不存在任何被证明有效的信号;全部策略假设的证据状态为零,待验证。
5. 开源风险:策略逻辑公开意味着可被复制与针对;当前资金量级下影响有限,但实盘参数取值按敏感物隔离(第 5.1 条)。
6. 系统风险:单机部署存在断电、休眠、网络中断导致持仓失管的风险;第 4.3 与第 8 章的对账、双通道、自动 PAUSED 机制是缓解而非消除。
7. 代理链路:全部交易所连接经由本地代理,代理进程或上游节点故障即行情与下单双中断;自动 PAUSED 是缓解而非消除,断联期间持仓无保护。代理是单点,必须纳入监控。
8. 本文档为工程规范,不构成投资建议;系统的存在不改变"多数短线交易者亏损"这一基础事实。

---

## 附录 A 术语表

| 术语 | 定义 |
|------|------|
| 业务日 | Asia/Shanghai (UTC+8) 日历日,一切"每日"逻辑的基准 |
| 三取小 | Minisha 开仓量 = MIN(预算派生量, 5x 物理上限, 员工剩余预算) |
| 影子模式 | 实时数据 + 完整决策链 + 虚拟成交、零真实订单的运行模式 |
| 员工 | Minisha 内一个策略实例(Employee A/B...),独立状态机与预算 |
| EMERGENCY_STOP | 全系统最高优先级人工指令:今日不再开仓 + 全员 FLATTEN |

## 附录 B ADR 模板

```markdown
# ADR-NNN: <标题>
Status: Proposed | Accepted | Superseded   Date: YYYY-MM-DD   Decider: 用户
## Context   <背景与约束>
## Decision  <决定内容>
## Options   <被否决的备选及理由>
## Consequences <变容易的事 / 变困难的事 / 需回访的时点>
```

## 附录 C 关键选型论证摘要

**C-1 Minisha 实现语言 = Python 3.13(Rust 落选)**:1m 级策略端到端延迟由网络与交易所主导(经代理数十毫秒量级),语言层微秒级差异不可测量;单人 + AI 协作下 Rust 的返工率与双语言维护税(双 CI、跨语言契约测试)是真实成本,而延迟收益是想象的。Rust 保留为 Phase 2 热路径升级选项,唯一触发条件 = profiling 实测证明 Python 成为瓶颈。

**C-2 精算层回测引擎 spike 验收标准(nautilus_trader,两个工作日封顶)**:① 本机安装与 OKX 永续适配可用(含资金费率、合约面值、全仓保证金);② Employee A 最小实现跑通回测并产出成交明细;③ paper/影子模式跑通;④ 员工状态机与预算三取小约束可在其模型内表达;⑤ 学习曲线主观可承受。任一硬性项不达标 → 回退最小化自研(bar 级事件驱动起步,严禁一步到位 tick 级)。选择 nautilus_trader 的核心动机:回测与实盘共用同一份策略代码,消灭"回测的和实盘跑的不是同一个策略"这一头号暗坑。

**C-3 回测工具分层**:粗筛层(factor_zoo)负责回答"信号有无预测力"——vectorbt 可用于参数网格快速扫描,但限定于评估沙箱,Pandas 依赖不得渗入 factor_zoo 核心,且其理想化成交模型的产出不得用于盈利性结论;精算层(Minisha)负责回答"该策略净费率口径能否存活",由 C-2 结论决定实现。TradingView 永久定位为人工看图核对工具,其任何输出不得作为"已验证/有效"的证据引用——闭源、不可编程提取、成交模型不可信、且要求策略在 Pine 中二次实现从而违反单点真相。

---

*Fortvna SPEC v1.0 — 签发即生效。本项目为全新起点:任何存在于本仓库与本文档之外的历史资产、结论与既往口头约定,一律不具有效力。*
