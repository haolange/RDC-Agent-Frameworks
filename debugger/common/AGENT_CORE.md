# RenderDoc/RDC GPU Debug Agent Core

本文件是 `RenderDoc/RDC GPU Debug` 的核心 SSOT。

约束：

- Agent 角色职责以 `common/agents/*.md` 为准。
- 平台适配物只允许修改 frontmatter、宿主所需引用和少量宿主专属接入说明。
- 不得在平台镜像中改写角色职责、质量门槛、artifact 合同或工作流逻辑。

## 1. Framework 与平台能力层的关系

`RenderDoc/RDC GPU Debug` 只依赖以下第一性平台能力：

- 规范化的 `rd.*` tool 能力面
- 共享响应契约
- `.rdc -> capture handle -> session handle -> frame/event context` 的最小状态链路
- `context`、daemon、artifact、failure surface

具体实现路径、catalog 文件位置、`MCP` / `CLI` 启动命令属于 adapter/config 层，不是 framework 真相。

默认实现接入配置位于：

- `common/config/platform_adapter.json`
- `common/config/platform_capabilities.json`
- `common/config/model_routing.json`

## 2. 接入模式规则

### `MCP` 模式

- 允许 tool discovery。
- 允许 Agent 在任务编排前先发现能力面。

### `CLI` 模式

- 禁止 discovery-by-trial-and-error。
- 禁止靠 `--help`、命令枚举、随机试跑或观察式探索来猜能力面。
- 用户明确要求 `CLI` 模式时，先阅读：
  - `docs/cli-mode-reference.md`
  - `docs/platform-capability-model.md`

## 3. Agent Identity SSOT

内部协议统一使用 `agent_id`：

- `team_lead`
- `triage_agent`
- `capture_repro_agent`
- `pass_graph_pipeline_agent`
- `pixel_forensics_agent`
- `shader_ir_agent`
- `driver_device_agent`
- `skeptic_agent`
- `curator_agent`

`plugin.json` 或宿主 UI 中的显示名只用于展示，不得参与路由和校验。

## 4. Core Workflow

统一工作流：

1. `team_lead`
   - 创建 hypothesis board
   - 分派任务
   - 维护裁决门槛
2. `triage_agent`
   - 结构化症状与触发条件
   - 推荐 SOP
   - 输出 `causal_axis` 与 `disallowed_shortcuts`
3. `capture_repro_agent`
   - 建立可复用 capture/session 基线
   - 提供 capture/session anchor
4. 因果锚点收敛阶段
   - 将 capture/session anchor 收敛为可复查的 `causal_anchor`
   - 优先建立 `first_bad_event`、`first_divergence_event`、`root_drawcall` 或 `root_expression`
5. 专家分析阶段
   - `pass_graph_pipeline_agent`
   - `pixel_forensics_agent`
   - `shader_ir_agent`
   - `driver_device_agent`
6. `skeptic_agent`
   - 对 `VALIDATE -> VALIDATED` 结论进行对抗审查
7. `curator_agent`
   - 生成 BugFull / BugCard
   - 写入 session artifacts
   - 推进知识沉淀

## 5. Causal Anchor Contract

上层框架在做任何根因级裁决前，必须先建立 `causal_anchor`。

硬规则：

- `第一可见错误 != 第一引入错误`。任何“某阶段首次明显可见”的观察，都不得直接提升为根因结论。
- `无 causal_anchor 不得裁决`。没有 `causal_anchor` 时，禁止把 hypothesis 提升为 `VALIDATE` 或 `VALIDATED`。
- `fallback 只能回锚，不得替代`。texture / screenshot / image similarity / screen-like 枚举只允许用于现象定位、像素选点和 sanity check，不得单独支撑根因判断。
- `结构化证据优先级高于视觉证据`。event / pixel / shader / debug / IR 的直接 `rd.*` 输出优先于截图、图像差异和视觉叙事。
- `证据冲突时进入 BLOCKED_REANCHOR`。若 event/pipeline/shader 与视觉 fallback 结论冲突，必须回到 re-anchor，而不是继续讲一个“更像”的故事。

`causal_anchor` 最小字段：

- `type`: `first_bad_event | first_divergence_event | root_drawcall | root_expression`
- `ref`: 具体 event / drawcall / expression 引用
- `established_by`: 建立该锚点的 agent
- `justification`: 一句话说明为什么该锚点足以承载后续根因分析

如果当前只有截图、texture 或 similarity 证据，允许继续调查，但 hypothesis 只能保持 `ACTIVE` 或进入 `BLOCKED_REANCHOR`。

## 6. Session Contract

上层框架必须遵守这些平台级最小约束：

- `session_id` 必须来自 replay session 打开链路。
- 在调用 event/pipeline/resource/shader/debug/export 等依赖上下文的能力前，必须先确保 event 上下文正确。
- 在进入根因分析前，必须先建立 `causal_anchor`；capture/session anchor 本身不足以直接承载根因裁决。
- `capture_file_id`、`session_id`、`active_event_id` 都是短生命周期运行时句柄，不得假设长期稳定。

## 7. Artifact Contract

结案前必须具备：

- `common/knowledge/library/sessions/.current_session`
- `common/knowledge/library/sessions/<session_id>/session_evidence.yaml`
- `common/knowledge/library/sessions/<session_id>/skeptic_signoff.yaml`
- `common/knowledge/library/sessions/<session_id>/action_chain.jsonl`

其中，`session_evidence.yaml` 根对象必须包含 `causal_anchor`，且至少包含一条 `type: causal_anchor_evidence` 的直接工具证据。
如果 evidence 中存在 `type: visual_fallback_observation`，但没有 `causal_anchor` 或 `causal_anchor_evidence`，则不得视为有效结案。

缺失任一项，不得视为有效结案。

## 8. Tool Contract Rules

- 所有 prompt / traces 中的 `rd.*` 工具引用必须以平台 catalog / contract 为准。
- 禁止自造工具名。
- 禁止沿用过期参数名。
- 调用方必须优先检查共享响应契约中的：
  - `ok`
  - `error_message`

## 9. Platform Mirrors

当前平台镜像来源：

- `platforms/claude-code/agents/`
- `platforms/code-buddy/agents/`
- `platforms/copilot-cli/agents/`
- `platforms/copilot-ide/.github/agents/`
- `platforms/claude-work/agents/`

镜像同步命令：

```bash
python debugger/scripts/sync_platform_agents.py
```

tool contract 校验命令：

```bash
python debugger/scripts/validate_tool_contract.py --strict
```

平台布局校验命令：

```bash
python debugger/scripts/validate_platform_layout.py --strict
```
