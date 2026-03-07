# RenderDoc/RDC GPU Debug Runtime Coordination Model

本文把 framework 的协作编排与 `rdx-tools` 的 runtime 真相拆开描述。

目标不是改写 `RDC-Agent Tools` 的平台定义，而是把这些已确认约束上升为 framework 的显式规则。

## 1. 两层能力必须分开理解

### 宿主能力

宿主能力回答“平台能不能表达 team / handoff / skill / MCP”：

- `custom_agents`
- `skills`
- `hooks`
- `mcp`
- `per_agent_model`
- `handoffs`
- `coordination_mode`

这些能力记录在：

- `common/config/platform_capabilities.json`

### runtime 约束

runtime 约束回答“RenderDoc/RDC live 调试链路怎样才是安全的”：

- `context` 只有一套当前 runtime 状态槽
- `CLI` 与 `MCP` 共用 daemon / context 机制
- local 并行依赖多 `context` / 多 daemon
- remote `remote_id` 是单次消费句柄
- remote 协作必须收敛为 `single_runtime_owner`

这些约束同样记录在：

- `common/config/platform_capabilities.json.runtime_contract`

## 2. `context` 的真实含义

`context` 是 live runtime 隔离单元，不是“多 agent 共用黑板”。

硬规则：

- 同一 `context` 下只允许维护一条当前 live 调试链路。
- 同一 `context` 不允许并行保有多套当前 `session_id` / `capture_file_id` / `active_event_id`。
- 若需要 local 并行调查，必须为每条 live 链路分配独立 `context/daemon`。

因此：

- `full-capability` 平台可以并行分工。
- 但并行分工不等于“多个 agent 共享同一个 live session 并发操作”。

## 3. 统一协作拓扑

framework 只使用以下三种 `coordination_mode`：

### `concurrent_team`

适用：高能力宿主，本地链路可并行。

规则：

- Team Lead 可以把不同专家任务分派到不同 `context/daemon`。
- 每个 live investigator 自己独占一个 `context`。
- 若任务进入 remote 路径，仍然必须降级到 `single_runtime_owner`。

### `staged_handoff`

适用：宿主能表达 agent/handoff，但不适合多 live owners。

规则：

- sub agents 先提交 `investigation brief`、证据需求与下一轮目标。
- 当前 runtime owner 负责实际调用 `rd.*` 工具并回填证据。
- 任何轮次都不得让多个 agent 同时持有同一条 live 调试链路。

### `workflow_stage`

适用：仅支持 workflow 的降级宿主。

规则：

- 只允许阶段化串行推进。
- 不模拟实时 team handoff。
- 若任务需要动态 discovery 或多 live owners，必须切回更高能力平台。

## 4. Remote 统一规则

remote 一律采用：

- `remote_coordination_mode = single_runtime_owner`

含义：

- 任一时刻只有一个 live remote session owner 可以执行 `rd.*`。
- 其他专家角色只能提交 brief / question / evidence request。
- framework 不设计 remote 多 live session 并发协作流程。

注意：

- 这不是声称 `rdx-tools` 全局绝对无法存在多个 remote session。
- 这是 framework 为 correctness 选择的协作约束。
- 原因是 remote `open_replay` 成功后会消费 `remote_id`，而且 `context` 只保存一套当前 remote/runtime 状态。

## 5. `runtime_baton` 合同

跨 agent、跨轮次、跨重连传递 live 调查上下文时，必须使用 `runtime_baton`。

固定字段：

```yaml
runtime_baton:
  coordination_mode: concurrent_team | staged_handoff | workflow_stage
  runtime_owner: team_lead | capture_repro_agent | <agent_id>
  context_id: "<live context id>"
  backend: local | remote
  capture_ref:
    rdc_path: "<path>"
    capture_file_id: "<optional short-lived handle>"
    session_id: "<optional short-lived handle>"
  rehydrate:
    required: true
    remote_connect:
      transport: renderdoc | adb_android
      host: "<host>"
      port: <port>
      options_ref: "<where bootstrap options are recorded>"
    frame_index: <int>
    active_event_id: <canonical event id or 0>
    causal_anchor_ref: "<event/draw/expression ref>"
    focus:
      pixel: "<optional>"
      resource_id: "<optional>"
      shader_id: "<optional>"
  evidence_refs:
    - "<session_evidence / action_chain / artifact ref>"
  task_goal: "<what the next executor must prove or falsify>"
```

硬规则：

- `capture_file_id`、`session_id`、`remote_id` 都只能当短生命周期提示。
- 它们不得成为 baton 的唯一真相源。
- baton 缺少 `task_goal`、`context_id`、`capture_ref.rdc_path` 或 `rehydrate.required=true` 时，不得视为可执行 baton。

## 6. Baton 的权威恢复来源

baton 的恢复真相源顺序固定为：

1. `causal_anchor` 与 `evidence_refs`
2. `action_chain.jsonl`、`session_evidence.yaml` 等 session artifacts
3. `rd.session.get_context` 快照

补充规则：

- `rd.session.get_context` 只作为恢复辅助，不是根因证据源。
- `rd.session.update_context` 只允许恢复 `focus.pixel`、`focus.resource_id`、`focus.shader_id`、`notes` 等 user-owned 字段。
- 禁止使用 `rd.session.update_context` 伪造 `session_id`、`capture_file_id`、`active_event_id` 或 `remote_id`。

## 7. Remote Rehydrate 顺序

remote baton 的完备恢复顺序固定如下：

1. 读取 baton 中的 `task_goal`、`evidence_refs`、`causal_anchor_ref`
2. `rd.remote.connect`
3. `rd.remote.ping`
4. `rd.capture.open_file`
5. `rd.capture.open_replay(options.remote_id=...)`
6. `rd.replay.set_frame`
7. 若 baton 中存在 canonical `active_event_id`，执行 `rd.event.set_active`
8. 使用 `rd.session.update_context` 恢复 `focus.pixel`、`focus.resource_id`、`focus.shader_id`、`notes`
9. 执行本轮调查，并把新增 evidence 回填到 artifacts 与 hypothesis board

默认规则：

- remote 下不做“专家各自重连抢 owner”。
- owner 可以跨轮次重建 session。
- 但 owner 身份在整个 remote case 内应保持稳定。

## 8. 失败语义

若 baton 不能安全恢复，必须显式阻塞，而不是依赖模型记忆继续工作。

允许的阻塞语义：

- `BLOCKED_REANCHOR`
- `BLOCKED_RUNTIME_REHYDRATE`

典型触发条件：

- baton 缺少可复位的 `causal_anchor_ref`
- remote 无法重新建立 live endpoint
- `active_event_id` 不再可 round-trip
- evidence refs 与当前 session 重建结果冲突

此时必须：

- 回报 Team Lead
- 补充缺失 artifact / evidence
- 或重新建立新的 anchor 与新的 baton
