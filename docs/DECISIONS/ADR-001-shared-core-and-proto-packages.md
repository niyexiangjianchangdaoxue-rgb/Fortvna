# ADR-001: 跨子系统共享包 fortvna_core 与契约包 fortvna_proto
Status: Accepted   Date: 2026-07-15   Decider: 用户(经 Claude Code 提请)

## Context
SPEC 第 12.3 条要求"唯一的 `trading_calendar` 模块"、第 4.4 条要求"唯一的 `net` 模块"、
第 5 章要求统一密钥加载、第 3.2 条要求 structlog 单点配置。这些是被 factor_zoo / Cosmos /
Minisha 三子系统共同依赖的横切"单点真相"模块,但 SPEC 第 4.2 条目录布局只列出了三个业务包与
`proto/`,未指定这些横切模块的归属包。若散落进三个业务包中任意一个,会制造隐性跨包依赖并违背
"单点"原则。

SPEC 第 3.2 条同时列出"proto 消息定义(v1 进程内命令总线,保留跨进程拆分能力)"作为
Cosmos↔Minisha 契约,第 4.2 条将 `proto/` 列为独立顶层目录("服务消息契约单点真相")。

## Decision
1. 新增 workspace 成员包 **`fortvna_core`**,承载横切单点真相模块:
   `settings`(密钥/代理加载 + 600 权限自检)、`logging`(structlog JSON 单点配置)、
   `trading_calendar`(第 12 章)、`ids`(UUIDv7,第 8.3/11.2 条);后续 `net`(第 4.4 条)入此包。
2. 将 `proto/` 落地为 workspace 成员包 **`fortvna_proto`**,以 **Pydantic v2 strict/frozen 模型**
   表达 v1 进程内契约(`ControlCommand` / `BudgetGrant` / `Heartbeat` 及状态/动作枚举与合法转换表)。
3. 依赖方向单向:`fortvna_proto → fortvna_core`;业务包(cosmos/minisha)→ 两者。
   `factor_zoo` 暂不依赖 core,以维持其"无状态、纯函数"最小内核(第 6 章)。

## Options(被否决的备选及理由)
- **横切模块塞进 cosmos 包**:Minisha/factor_zoo 反向依赖 cosmos,污染权力拓扑(第 2 章),否决。
- **每个业务包各自实现 trading_calendar**:直接违反第 12.3 条"单点",且必然产生日界计算分叉,否决。
- **proto/ 用 protobuf `.proto` + 代码生成**:v1 为进程内单进程(第 3.2 条),protobuf 的
  IDL/编译链在此阶段是纯负担;Pydantic 模型已满足强类型契约且可直接被 FastAPI 复用。
  跨进程拆分时再引入 protobuf,契约字段一一对应可平滑迁移。暂缓。

## Consequences
- 变容易:三子系统共享同一份时区/ID/密钥/日志实现,消灭日界与时间戳分叉。
- 变困难:新增两个包带来 workspace 依赖图复杂度(可接受,uv workspace 原生支持)。
- 需回访:Cosmos/Minisha 拆分为独立进程时(第 8.2 条预告),`fortvna_proto` 需评估是否升级为
  protobuf + 跨进程序列化;`net` 模块并入 `fortvna_core` 后需复核代理配置读取仍为单点。
