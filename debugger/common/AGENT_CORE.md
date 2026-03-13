# RenderDoc/RDC GPU Debug Agent Core

本文件是 `RenderDoc/RDC GPU Debug` framework 的全局约束入口。

职责边界：

- `RDC-Agent Tools` 负责平台真相：tool catalog、共享响应契约、runtime 生命周期、context/session/remote/event 语义与错误面。
- 本文件只负责 framework 如何消费这些平台真相，不重新定义平台语义。
- 角色职责正文以 `common/agents/*.md` 为准；平台适配物只允许改宿主入口、frontmatter 与少量宿主接入说明。

## 1. Framework 与 Tools 的边界

以下内容必须回到已解析的 `RDC-Agent Tools` 判定：

- `rd.*` tools 的能力面与参数语义
- 共享响应契约
- `.rdc -> capture_file_id -> session_id -> frame/event context` 的最小状态链路
- `remote_id`、`capture_file_id`、`session_id`、`active_event_id` 等 handle 的生命周期
- `context`、daemon、artifact、context snapshot 的平台语义
- 错误分类与恢复面

以下内容属于 framework：

- 角色拓扑与协作关系
- 任务 intake、分派、阶段推进与结案门槛
- `causal_anchor`、workspace、artifact/gate 的硬约束
- 多平台能力差异下的降级编排原则

## 2. Mandatory Tools Resolution

所有需要平台真相的工作在开始前，必须先读取并校验：

- `common/config/platform_adapter.json`

强制规则：

1. `paths.tools_root` 必须由用户显式配置，不允许保留占位值。
2. Agent 必须验证 `tools_root` 下至少存在：
   - `README.md`
   - `docs/tools.md`
   - `docs/session-model.md`
   - `docs/agent-model.md`
   - `spec/tool_catalog.json`
3. 任一项缺失、路径不存在或 `tools_root` 未配置时，必须立即停止，不得继续做 debug / investigation / tool planning。
4. 停止时统一输出：

```text
Tools 平台真相未配置：请先在 `common/config/platform_adapter.json` 中设置 `paths.tools_root` 指向有效的 `RDC-Agent-Tools` 根目录，并确认必需文档与 `spec/tool_catalog.json` 存在后，再重新发起任务。
```

5. 不允许把 `CLI` wrapper、skill 文本、平台模板说明或模型记忆当成 Tools 真相替代品。

推荐阅读顺序：

1. `<resolved tools_root>/README.md`
2. `<resolved tools_root>/docs/tools.md`
3. `<resolved tools_root>/docs/session-model.md`
4. `<resolved tools_root>/docs/agent-model.md`
5. `<resolved tools_root>/spec/tool_catalog.json`

## 3. Mandatory Capture Intake

所有进入 `RenderDoc/RDC GPU Debug` workflow 的任务，在开始前必须先取得至少一份用户提供的 `.rdc`。

强制规则：

1. `.rdc` 是第一性调试输入，不是可选附件。
2. 未提供 `.rdc` 时，必须立即停止，不得继续做 debug / investigation / tool planning / specialist dispatch / root-cause 判断。
3. capture 缺失时的统一阻断状态为：`BLOCKED_MISSING_CAPTURE`。
4. 阻断期间允许的唯一动作是提示用户在当前对话补传一份或多份 `.rdc`。
5. 不允许用截图、日志、文本描述、skill 文本、平台模板说明或模型记忆替代 `.rdc` 作为第一性调试输入。
6. 新上传 `.rdc` 一律按 append intake 处理；不得隐式 overwrite 已有 capture。
7. 在 capture intake 完成前，不允许初始化 `case_id`、`run_id` 或 `workspace_run_root`。

停止时统一输出：

```text
当前任务缺少必需的 capture 输入：本框架只接受基于 RenderDoc `.rdc` 的第一性调试。请先在当前对话中提交一份或多份 `.rdc` 文件；收到并导入 capture 前，Agent 不会继续进行 debug、调查分派或根因判断。
```

## 4. Global Entry Contract

内部 `agent_id` SSOT：

- `team_lead`
- `triage_agent`
- `capture_repro_agent`
- `pass_graph_pipeline_agent`
- `pixel_forensics_agent`
- `shader_ir_agent`
- `driver_device_agent`
- `skeptic_agent`
- `curator_agent`

入口规则：

- `team_lead` 是当前 framework 唯一正式用户入口，承担 orchestrator 语义。
- 其他角色默认是 internal/debug-only specialist，不是正常用户入口。
- 若宿主无法隐藏 specialist 入口，仍必须明确：正常用户请求应先交给 `team_lead` 路由。
- specialist 不得绕过 `team_lead` 重新定义任务 intake、裁决门槛或 delegation policy。

## 5. Global Workflow

统一工作流：

1. `team_lead`
   - intake 用户目标
   - 建立 hypothesis board
   - 决定阶段推进与 specialist 分派
2. `triage_agent`
   - 结构化 symptoms / triggers
   - 推荐 SOP 与 `causal_axis`
3. `capture_repro_agent`
   - 建立 capture/session 基线
   - 产出可重建的 capture anchor / runtime baton 起点
4. 因果回锚阶段
   - 将 capture/session anchor 收敛为 `causal_anchor`
   - 优先建立 `first_bad_event`、`first_divergence_event`、`root_drawcall` 或 `root_expression`
5. 专家调查阶段
   - `pass_graph_pipeline_agent`
   - `pixel_forensics_agent`
   - `shader_ir_agent`
   - `driver_device_agent`
6. `skeptic_agent`
   - 对 `VALIDATE -> VALIDATED` 结论做对抗审查
7. `curator_agent`
   - 写入 BugFull / BugCard / session artifacts

协作真相：

- `concurrent_team` 允许并行分派，但每条 live 调试链路必须独占一个 `context/daemon`。
- `staged_handoff` 由 specialist 先提交 brief / evidence request，再由 runtime owner 执行 live tool 链。
- `workflow_stage` 只允许阶段化串行推进，不模拟真实的 team-agent 并发 handoff。
- remote case 一律服从 `single_runtime_owner`；不得因为 multi-agent 就共享 live remote runtime。

## 6. Hard Contracts

### 6.1 Causal Anchor

在做任何根因级裁决前，必须先建立 `causal_anchor`。

硬规则：

- `第一可见错误 != 第一引入错误`
- 无 `causal_anchor` 不得把 hypothesis 提升为 `VALIDATE` 或 `VALIDATED`
- screenshot / texture / similarity / screen-like fallback 只能用于选点、选对象、sanity check，不得替代因果裁决
- 结构化 `rd.*` 证据优先级高于视觉叙事
- 证据冲突时必须进入 `BLOCKED_REANCHOR`

`causal_anchor` 最小字段：

- `type`
- `ref`
- `established_by`
- `justification`

### 6.2 Session / Runtime Coordination

- `session_id` 必须来自 replay session 打开链路
- 进入根因分析前必须先建立 `causal_anchor`
- `capture_file_id`、`session_id`、`active_event_id`、`remote_id` 都是短生命周期 handle
- `CLI` 与 `MCP` 共用同一套 daemon / context 机制
- 同一 `context` 不得并行维护多条 live 调试链路
- remote `open_replay` 成功后会消费 live `remote_id`
- 跨 agent 或跨轮次移交 live 调试上下文时，必须提供可重建的 `runtime_baton`
- `runtime_baton` 的恢复顺序与语义以 `common/docs/runtime-coordination-model.md` 为准

### 6.3 Workspace Contract

- `common/` 是唯一共享真相
- `../workspace/` 是 case/run 运行区

固定模型：

```text
../workspace/cases/<case_id>/
  case.yaml
  inputs/
    captures/
      manifest.yaml
      <capture_id>.rdc
  runs/
    <run_id>/
      run.yaml
      capture_refs.yaml
      artifacts/
      logs/
      notes/
      screenshots/
      reports/
```

硬规则：

- `case` 持有原始 capture 输入池；原始 `.rdc` 只允许落在 `inputs/captures/`
- `run` 只持有 capture 引用、运行现场和派生产物；不得再创建原始 `.rdc` 副本
- `case.yaml` 必须至少维护 `current_run` 与 `active_capture_set`
- `inputs/captures/manifest.yaml` 必须记录 capture 的 `capture_id`、`file_name`、`sha256`、`source`、`imported_at`、`role_hint`、`status`
- `runs/<run_id>/capture_refs.yaml` 必须显式记录当前 run 实际采用的 capture ids 与角色
- 第一层真相产物继续写入 `common/knowledge/library/**`
- 第二层交付层写入 `../workspace/cases/<case_id>/runs/<run_id>/reports/`
- 第二层交付物只能派生自第一层证据，不得反写第一层真相

### 6.4 Artifact / Gate Contract

结案前必须具备：

- `common/knowledge/library/sessions/.current_session`
- `common/knowledge/library/sessions/<session_id>/session_evidence.yaml`
- `common/knowledge/library/sessions/<session_id>/skeptic_signoff.yaml`
- `common/knowledge/library/sessions/<session_id>/action_chain.jsonl`

额外规则：

- `session_evidence.yaml` 根对象必须包含完整 `causal_anchor`
- 若存在 `type: visual_fallback_observation`，则必须同时存在 `type: causal_anchor_evidence`
- 缺失任一项，不得视为有效结案

## 7. User Intake Contract

用户通过结构化 Prompt 提交调试任务。Prompt 模板以如下文件为规范：

- `common/knowledge/templates/user_prompts/USER_PROMPT_TEMPLATE.md`（完整版）
- `common/knowledge/templates/user_prompts/USER_PROMPT_MINIMAL.md`（极简版）

Prompt 包含七个顶层 § 节，其与 framework 内部角色的对应关系：

| Prompt § 节 | 主要消费角色 | 用途 |
|------------|------------|------|
| `§ SESSION` | `team_lead` | 模式声明（single / cross_device / regression），驱动调度策略 |
| `§ SYMPTOM` | `triage_agent` | symptom_tags 提取、触发条件识别、截图附件 |
| `§ CAPTURES` | `capture_repro_agent` | `.rdc` 文件接入（ANOMALOUS + BASELINE）、A/B 环境建立 |
| `§ ENVIRONMENT` | `triage_agent`, `driver_device_agent` | trigger_tags 提取、设备/驱动/API 归因 |
| `§ REFERENCE` | `curator_agent`（修复验证）| **正确渲染基准**；用于 Counterfactual Scoring 的语义参照 |
| `§ HINTS` | `team_lead`, 全体 specialist | 搜索范围缩小、调度优先级提示 |
| `§ PROJECT` | 全体 specialist | 引擎/模块上下文注入（可由 `project_plugin` 替代）|

**§ REFERENCE 节的强制语义**：

- 用户在 `§ REFERENCE.CORRECT_DESCRIPTION` 或 `§ REFERENCE.CORRECT_REFERENCE` 中提供的"正确渲染基准"，
  必须写入 `case.yaml` 的 `fix_reference` 字段，供 `curator_agent` 在修复验证阶段调用。
- `§ REFERENCE.VERIFICATION_MODE` 决定 Counterfactual Scoring 的比较方向：
  - `pixel_value_check`：验证修复后像素值在用户描述的目标范围内
  - `visual_comparison`：多模态对比修复截图与参考图像
  - `device_parity`：验证问题设备输出与基准设备输出一致
  - `regression_check`：验证当前输出与历史正常版本一致
- 若 `§ REFERENCE` 节缺失，`curator_agent` 必须在修复验证阶段告知用户缺少语义基准，
  并要求补充，不得仅以"NaN 消失"或"数值合法"作为修复成功的判定依据。

---

## 8. Canonical References

共享 framework 入口：

- `common/config/platform_adapter.json`
- `common/config/platform_capabilities.json`
- `common/config/platform_targets.json`
- `common/config/model_routing.json`

共享 framework 文档：

- `common/docs/platform-capability-model.md`
- `common/docs/platform-capability-matrix.md`
- `common/docs/model-routing.md`
- `common/docs/runtime-coordination-model.md`
- `common/docs/workspace-layout.md`
- `common/docs/cli-mode-reference.md`（仅在用户明确要求 `CLI` 模式时强制阅读）

角色与技能入口：

- `common/agents/*.md`
- `common/skills/renderdoc-rdc-gpu-debug/SKILL.md`
- `common/skills/*/SKILL.md`

用户 Prompt 模板：

- `common/knowledge/templates/user_prompts/USER_PROMPT_TEMPLATE.md`
- `common/knowledge/templates/user_prompts/USER_PROMPT_MINIMAL.md`
- `common/knowledge/templates/user_prompts/README.md`
