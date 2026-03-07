# RenderDoc/RDC GPU Debug Platform Capability Model

本文描述 `RenderDoc/RDC GPU Debug` 与底层平台能力层的关系，只使用第一性抽象，不把任何历史实现名当成框架概念。

## 1. Framework 依赖什么

`RenderDoc/RDC GPU Debug` 只依赖以下平台能力：

- 规范化的 `rd.*` tool 能力面
- 共享响应契约
- `.rdc -> capture handle -> session handle -> frame/event context` 的最小状态链路
- `context`、daemon、artifact、failure surface 这些平台级概念

这些能力共同构成 framework 的平台前提，但不要求平台必须以某个特定仓库名或启动方式出现。

为了避免把“宿主能不能 handoff”与“live runtime 能不能安全并行”混为一谈，框架还要求显式区分：

- 宿主能力
  - `custom_agents`、`skills`、`hooks`、`mcp`、`handoffs`、`per_agent_model`
- runtime 合同
  - `context_state_model`
  - `local_parallelism`
  - `remote_handle_lifecycle`
  - `remote_coordination_mode`
  - `rehydration_contract`

其中：

- 宿主能力回答“平台能表达什么协作壳子”
- runtime 合同回答“RenderDoc/RDC live 调试链路怎样才是安全的”

## 2. 什么不是框架真相

以下内容都属于 adapter/config 层：

- 平台工具仓库实际目录
- catalog 文件实际路径
- `MCP` 启动命令
- `CLI` 启动命令
- 平台插件里的 server 名称

它们可以有默认值，但这些默认值不是 framework 的概念定义。

## 3. 平台约束优先级

上层 Agent 在判断平台定义时，应按以下顺序理解：

1. tool catalog / tool contract
2. runtime-observed behavior
3. `CLI` convenience wrapper

这意味着：

- 工具能力面与参数语义以 catalog 和共享契约为准。
- runtime 行为是平台真相的运行时体现。
- `CLI` 只是受约束的人类与自动化入口，不是完整规范源。

## 4. `MCP` 与 `CLI` 的边界

### `MCP` 模式

- 允许 tool discovery。
- 允许 Agent 先发现工具，再决定调用编排。
- 适合作为上层多步推理与动态决策的主接口。

### `CLI` 模式

- 不允许把 `CLI` 当成 discovery 载体。
- 不允许靠 `--help`、枚举命令、随机试跑、观察式试错来反推能力面。
- 只能依赖预先文档化的命令族、状态对象和最小链路。

用户明确要求 `CLI` 模式时，Agent 应先阅读 `cli-mode-reference.md`，再开始任务。

## 5. 上层框架的固定责任

`RenderDoc/RDC GPU Debug` 负责：

- 定义任务级角色与协作边界
- 定义质量门槛与 artifact 合同
- 定义知识库沉淀方式
- 定义 `MCP` / `CLI` 两种接入模式下的使用约束

平台能力层负责：

- 暴露 `rd.*` 工具能力
- 提供会话生命周期
- 提供错误面与运行时状态语义

## 6. 实现默认值的存放位置

默认接入值集中记录在：

- `common/config/platform_adapter.json`

平台协作拓扑与 runtime 协作硬规则集中记录在：

- `common/config/platform_capabilities.json`
- `docs/runtime-coordination-model.md`

需要绑定到当前环境时，应修改该配置，而不是在主文档、Prompt、脚本和插件配置里重复硬编码。



