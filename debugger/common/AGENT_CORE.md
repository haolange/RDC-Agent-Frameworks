# RenderDoc/RDC GPU Debug Agent Core（框架核心约束）

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
- intake、规范化、分派、阶段推进与结案门槛
- `case_input.yaml`、`reference_contract`、`fix_verification.yaml` 的合同
- `causal_anchor`、workspace、artifact/gate 的硬约束
- 多平台能力差异下的降级编排原则

## 2. Mandatory Setup Verification

所有需要平台真相的工作在开始前，必须先验证以下两项均已就绪：

**检查 1：`common/` 已正确覆盖**

- 验证 `common/AGENT_CORE.md` 是否存在。
- 不存在则说明 `common/` 仍为占位目录，尚未从 `debugger/common/` 整包覆盖。

**检查 2：`tools/` 已正确覆盖**

- 验证 `tools/spec/tool_catalog.json` 是否存在。
- 不存在则说明 `tools/` 仍为占位目录，尚未从 RDC-Agent-Tools 整包覆盖。
- `tools/` 下应至少包含：
  - `README.md`
  - `docs/tools.md`
  - `docs/session-model.md`
  - `docs/agent-model.md`
  - `spec/tool_catalog.json`

强制规则：

1. 任一检查失败，必须立即停止，不得继续做 debug / investigation / tool planning。
2. 停止时统一输出：

```text
前置环境未就绪：请确认 (1) 已将 debugger/common/ 整包覆盖到平台根 common/；(2) 已将 RDC-Agent-Tools 整包覆盖到平台根 tools/；(3) 在平台根目录运行 python common/config/validate_binding.py --strict 通过后，再重新发起任务。
```

3. 不允许把 `CLI` wrapper、skill 文本、平台模板说明或模型记忆当成 Tools 真相替代品。
4. 不允许尝试搜索替代工具路径、降级处理或用其他方式绕过本检查。

## 3. Mandatory Capture Intake

所有进入 `RenderDoc/RDC GPU Debug` workflow 的任务，在开始前必须先取得至少一份用户提供的 `.rdc`。

强制规则：

1. `.rdc` 是第一性调试输入，不是可选附件。
2. 未提供 `.rdc` 时，必须立即停止，不得继续做 debug / investigation / tool planning / specialist dispatch / root-cause 判断。
3. capture 缺失时的统一阻断状态为：`BLOCKED_MISSING_CAPTURE`。
4. 阻断期间允许的唯一动作是提示用户在当前对话补传一份或多份 `.rdc`。
5. 不允许用截图、日志、文本描述、skill 文本、平台模板说明或模型记忆替代 `.rdc` 作为第一性调试输入。
6. 新上传 `.rdc` 一律按 append intake 处理；不得隐式 overwrite 已有 capture。
7. 在 capture intake 完成前，不允许初始化 `case_id`、`run_id`、`workspace_run_root` 或 `case_input.yaml`。

停止时统一输出：

```text
当前任务缺少必需的 capture 输入：本框架只接受基于 RenderDoc `.rdc` 的第一性调试。请先在当前对话中提交一份或多份 `.rdc` 文件；收到并导入 capture 前，Agent 不会继续进行 debug、调查分派或根因判断。
```

## 4. Mandatory Intake Normalization

用户可以用自由语言描述问题，但 framework 只承认七段式 intake 被规范化后的 `case_input.yaml`。

固定模型：

- 用户层
  - `§ SESSION`
  - `§ SYMPTOM`
  - `§ CAPTURES`
  - `§ ENVIRONMENT`
  - `§ REFERENCE`
  - `§ HINTS`
  - `§ PROJECT`
- 系统层
  - `../workspace/cases/<case_id>/case_input.yaml`

硬规则：

- `team_lead` 是唯一 intake 规范化者
- specialist 不得绕过 `case_input.yaml` 直接消费原始 prose prompt 作为系统真相
- `case_input.yaml` 必须包含：
  - `session`
  - `symptom`
  - `captures`
  - `environment`
  - `reference_contract`
  - `hints`
  - `project`
- `§ CAPTURES` 只描述 replayable `.rdc`
- `§ REFERENCE` 只描述语义验收合同，不等同于某个 capture
- `visual_comparison` 只能作为 fallback/report-only 模式，不得单独支撑 `fix_verified=true`

模式约束：

- `single`
  - 必须有 `role=anomalous` capture
  - 必须有 `reference_contract`
  - 若无量化 probe 或 baseline capture，则只能 `fallback_only`
- `cross_device`
  - 必须有 `anomalous + baseline`
  - `reference_contract.source_kind` 必须为 `capture_baseline`
  - `reference_contract.source_refs` 必须包含 `capture:baseline`
- `regression`
  - 必须有 `anomalous + baseline`
  - `baseline.source` 必须为 `historical_good`
  - `baseline.provenance` 必须包含 known-good build 或 revision

## 5. Global Entry Contract

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

- `team_lead` 是当前 framework 唯一正式用户入口，承担 orchestrator + intake normalizer 语义。
- 其他角色默认是 internal/debug-only specialist，不是正常用户入口。
- 若宿主无法隐藏 specialist 入口，仍必须明确：正常用户请求应先交给 `team_lead` 路由。
- specialist 不得绕过 `team_lead` 重新定义任务 intake、验证等级、裁决门槛或 delegation policy。

## 6. Global Workflow

统一工作流：

1. `team_lead`
   - 检查 `.rdc` intake
   - 规范化七段式用户输入为 `case_input.yaml`
   - 建立 hypothesis board
   - 决定阶段推进与 specialist 分派
2. `triage_agent`
   - 结构化 symptoms / triggers
   - 推荐 SOP 与 `causal_axis`
3. `capture_repro_agent`
   - 归一化 `anomalous | baseline | fixed` capture 角色
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
6. 修复验证阶段
   - 产出 `runs/<run_id>/artifacts/fix_verification.yaml`
   - 明确区分 `structural_verification` 与 `semantic_verification`
7. `skeptic_agent`
   - 对 `VALIDATE -> VALIDATED` 结论做对抗审查
   - 结构通过但语义只到 fallback 时，不得严格签署
8. `curator_agent`
   - 写入 BugFull / BugCard / session artifacts

协作真相：

- `concurrent_team` 允许并行分派，但每条 live 调试链路必须独占一个 `context/daemon`
- `staged_handoff` 由 specialist 先提交 brief / evidence request，再由 runtime owner 执行 live tool 链
- `workflow_stage` 只允许阶段化串行推进，不模拟真实的 team-agent 并发 handoff
- remote case 一律服从 `single_runtime_owner`；不得因为 multi-agent 就共享 live remote runtime

## 7. Hard Contracts

### 7.1 Causal Anchor

在做任何根因级裁决前，必须先建立 `causal_anchor`。

硬规则：

- `第一可见错误 != 第一引入错误`
- 无 `causal_anchor` 不得把 hypothesis 提升为 `VALIDATE` 或 `VALIDATED`
- screenshot / texture / similarity / screen-like fallback 只能用于选点、选对象、sanity check，不得替代因果裁决
- 结构化 `rd.*` 证据优先级高于视觉叙事
- 证据冲突时必须进入 `BLOCKED_REANCHOR`

### 7.2 Reference Contract

`reference_contract` 是语义修复验证的唯一合同。

最小字段：

- `source_kind`
- `source_refs`
- `verification_mode`
- `probe_set`
- `acceptance`

硬规则：

- `reference_contract` 不是自由文本备注；必须是结构化对象
- `source_refs` 只允许指向 `capture:<role>` 或 `reference:<id>`
- `probe_set` 缺失时，只允许 fallback 级语义验证
- `visual_comparison` 不得单独产生 strict semantic pass

### 7.3 Session / Runtime Coordination

- `session_id` 必须来自 replay session 打开链路
- 进入根因分析前必须先建立 `causal_anchor`
- `capture_file_id`、`session_id`、`active_event_id`、`remote_id` 都是短生命周期 handle
- `CLI` 与 `MCP` 共用同一套 daemon / context 机制
- 同一 `context` 不得并行维护多条 live 调试链路
- 同一 `context` 可以保留多条本地 session 记录，但这只表示持久化 / 恢复能力，不表示允许多个 owner 并发共享 live runtime
- remote `open_replay` 成功后会消费 live `remote_id`
- 跨 agent 或跨轮次移交 live 调试上下文时，必须提供可重建的 `runtime_baton`
- `runtime_baton` 的恢复顺序与语义以 `common/docs/runtime-coordination-model.md` 为准

### 7.4 Workspace Contract

- `common/` 是唯一共享真相
- `../workspace/` 是 case/run 运行区

固定模型：

```text
../workspace/cases/<case_id>/
  case.yaml
  case_input.yaml
  inputs/
    captures/
      manifest.yaml
      <capture_id>.rdc
    references/
      manifest.yaml
      <reference_id>.png|.jpg|.md|.txt
  runs/
    <run_id>/
      run.yaml
      capture_refs.yaml
      artifacts/
        fix_verification.yaml
      logs/
      notes/
      screenshots/
      reports/
```

硬规则：

- `case` 持有原始输入池；run 只持有引用、运行现场和派生产物
- `case_input.yaml` 只允许存在于 `case` 根
- `inputs/captures/` 与 `inputs/references/` 分层，不得混放
- `runs/<run_id>/capture_refs.yaml` 必须显式记录 `capture_role` 与 provenance
- `runs/<run_id>/artifacts/fix_verification.yaml` 是 run 级修复验证唯一权威 artifact
- 第一层真相产物继续写入 `common/knowledge/library/**`
- 第二层交付层写入 `../workspace/cases/<case_id>/runs/<run_id>/reports/`

角色写入边界（write scopes）：

- `workspace_control`
  - `case.yaml`
  - `case_input.yaml`
  - capture/reference manifests
  - `run.yaml`
  - `capture_refs.yaml`
  - `notes/hypothesis_board.yaml`
- `workspace_notes`
  - `runs/<run_id>/artifacts/`
  - `runs/<run_id>/notes/`
  - `runs/<run_id>/screenshots/`
- `session_signoff`
  - `common/knowledge/library/sessions/<session_id>/skeptic_signoff.yaml`
- `workspace_reports`
  - `reports/report.md`
  - `reports/visual_report.html`
- `session_artifacts`
  - `.current_session`
  - `session_evidence.yaml`
  - `action_chain.jsonl`
- `knowledge_library`
  - `bugcards/`
  - `bugfull/`
  - `bugcard_index.yaml`
  - `cross_device_fingerprint_graph.yaml`
  - `proposals/`

角色分工约束：

- `team_lead` 只允许写 `workspace_control` 范围，不直接执行 live `rd.*`，也不写最终报告或知识对象
- `triage_agent`、`capture_repro_agent`、`pass_graph_pipeline_agent`、`pixel_forensics_agent`、`shader_ir_agent`、`driver_device_agent` 只允许写 `workspace_notes` 范围
- `skeptic_agent` 只允许写 `session_signoff`
- `curator_agent` 负责 `workspace_reports`、`session_artifacts` 与 `knowledge_library`

### 7.5 Artifact / Gate Contract

结案前必须具备：

- `common/knowledge/library/sessions/.current_session`
- `common/knowledge/library/sessions/<session_id>/session_evidence.yaml`
- `common/knowledge/library/sessions/<session_id>/skeptic_signoff.yaml`
- `common/knowledge/library/sessions/<session_id>/action_chain.jsonl`
- `../workspace/cases/<case_id>/case_input.yaml`
- `../workspace/cases/<case_id>/inputs/references/manifest.yaml`
- `../workspace/cases/<case_id>/runs/<run_id>/artifacts/fix_verification.yaml`

额外规则：

- `session_evidence.yaml` 根对象必须包含完整 `causal_anchor`
- `session_evidence.yaml` 必须包含 `reference_contract` 摘要与 `fix_verification` 摘要
- `fix_verification.yaml` 必须同时包含：
  - `structural_verification`
  - `semantic_verification`
  - `overall_result`
- `overall_result` 只能由 `structural=passed && semantic=passed` 派生
- `semantic_verification.status=fallback_only` 时，严格结案无效

## 8. Canonical References

共享 framework 入口：

- `common/config/platform_adapter.json`
- `common/config/platform_capabilities.json`
- `common/config/platform_targets.json`
- `common/config/model_routing.json`

共享 framework 文档：

- `common/docs/intake/README.md`
- `common/docs/cli-mode-reference.md`
- `common/docs/model-routing.md`
- `common/docs/platform-capability-matrix.md`
- `common/docs/platform-capability-model.md`
- `common/docs/runtime-coordination-model.md`
- `common/docs/truth_store_contract.md`
- `common/docs/workspace-layout.md`
- `common/docs/action_chain_schema.yaml`
- `common/docs/counterfactual_scoring_spec.md`

角色与技能入口：

- `common/agents/*.md`
- `common/skills/renderdoc-rdc-gpu-debug/SKILL.md`
- `common/skills/*/SKILL.md`
