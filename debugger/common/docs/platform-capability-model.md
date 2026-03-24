# Platform Capability Model（平台能力模型）

本文说明 Debugger framework 如何把宿主能力真相与路由策略拆开表达。

配置 SSOT 规则：

- `common/config/platform_capabilities.json` 是平台能力与 required paths 的唯一权威源。
- `common/config/framework_compliance.json` 是 platform-level enforcement / coordination 的唯一权威源。
- `common/config/model_routing.json` 与 `common/config/role_manifest.json` 共同定义角色路由与平台文件映射。
- 本文与 `platform-capability-matrix.md` 只负责解释或镜像，不再独立定义事实。
- 平台默认入口与允许入口集合也只定义在 `platform_capabilities.json` 的 `default_entry_mode` / `allowed_entry_modes`。

## 能力层

framework 依赖两个彼此独立的层次：

- 宿主能力层
  - `custom_agents`
  - `skills`
  - `hooks`
  - `mcp`
  - `handoffs`
  - `per_agent_model`
- runtime 合同层
  - `context_state_model`
  - `local_parallelism`
  - `remote_handle_lifecycle`
  - `remote_coordination_mode`
  - `rehydration_contract`

宿主能力回答的是“宿主能表达什么”，runtime 合同回答的是“驱动 live RenderDoc/RDC 状态时什么是安全的”。

## 入口选择规则

framework 文档必须把 `CLI`、daemon 和 `MCP` 当作不同层次的概念：

- `CLI`
  - 适用于可直接访问本地进程、文件系统与 daemon 的宿主，是 local-first 执行入口。
- daemon
  - 负责跨命令、跨轮次的长生命周期 runtime/context 持有。
- `MCP`
  - 适用于无法直接进入本地环境的宿主，或用户明确要求使用 `MCP` 的协议桥接入口。

framework 不得把 `MCP` 写成所有 agent 的默认入口。正确的决策边界只有两条：

- 宿主是否能直接访问本地环境；
- 任务是否需要长生命周期的 runtime/context owner。

宿主能直达本地环境时，framework 默认 `CLI` / local-first；不能直达时，framework 默认 `MCP`。

补充说明：

- `CLI` / `MCP` 是工具入口模式，不是 `custom_agents`、`skills`、`hooks` 这类宿主 surface 的别名。
- inherit-only 只表示模型控制降级，不等于“不支持 `MCP`”。

## 路由策略与宿主能力的分工

- `model_routing.json` 定义每个平台上各角色希望使用的模型族。
- `platform_capabilities.json` 定义宿主能否原生、部分或仅以 downgrade 语义表达该路由。
- 即使宿主发生模型控制降级，生成后的平台 wrapper 也必须保持角色边界。
- Markdown 文档不得新增 JSON 中不存在的平台能力、surface 或 required path 事实。

## 本仓使用的平台分类

- 显式 per-agent routing
  - `code-buddy`、`cursor`、`copilot-cli`、`copilot-ide`
- 宿主受限的 per-agent routing
  - `claude-code`
- inherit-only
  - `claude-desktop`、`manus`
- 单一批准模型族
  - `codex`

## 当前入口模式分组

当前仓库的入口模式分组固定如下：

- 默认 `CLI`，允许 `CLI` / `MCP`
  - `code-buddy`
  - `claude-code`
  - `copilot-cli`
  - `copilot-ide`
  - `codex`
  - `cursor`
- 默认 `MCP`，且只允许 `MCP`
  - `claude-desktop`
  - `manus`

其中 `manus` 仍是 `workflow_stage` 宿主，但工具入口只允许 `MCP`，不得误写成 CLI-first 或 MCP-not-supported。

## 必需的降级行为

- 显式 per-agent 平台
  - 必须为每个角色渲染路由后的模型。
- 宿主受限的 per-agent 平台
  - 可以把路由后的角色映射到最接近的宿主原生模型族或 alias。
  - 若宿主存在 host-required bootstrap agent，它只能承担 bootstrap / orchestration 语义；public user entry 仍应落在 main skill。
- inherit-only 平台
  - 不得宣称支持 per-agent model control。
  - 必须把全部角色路由为 `inherit`。
- 单一批准模型族平台
  - 可以保留 per-agent 配置文件，但路由后的模型族应有意统一。

## Experimental Remote 规则

- remote / live bridge / runtime rehydrate 相关流程当前只保留为 `experimental` 协作合同。
- 除非某个平台 README 显式声明该实验路径已验证，否则它不属于当前保证能力。
- `platform-capability-matrix.md`、平台 README 与 required paths 不得把 experimental remote 写成当前正式支持面。

## 哪些内容不属于 framework 真相

以下内容仍然属于 adapter/config 细节，而不是 framework 概念：

- 实际的 tools 仓库路径
- 实际的 MCP 命令行
- 实际的 CLI convenience wrapper
- 宿主插件包命名

这些细节应写在 `platform_adapter.json`、`mcp_servers.json` 或生成后的宿主打包产物中，而不是角色 prompt 或路由策略 prose 里。

不过，framework 仍必须要求在执行开始前满足入口前置条件：

- local-first 路径需要有效的 `tools_source_root` source payload 与 `runtime.mode=worker_staged`
- `MCP` 路径需要目标宿主预先配置好 MCP server
- agent 在进入依赖平台真相的工作前必须向用户说明当前使用的入口模式
- agent 在判断调用序列是否合法时，应优先参考 catalog `prerequisites`，而不是依赖 prompt memory
