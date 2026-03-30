# Codex Workspace Instructions（工作区约束）

当前目录是 Codex 的 platform-local 模板。所有角色在进入 role-specific 行为前，都必须先服从本文件与共享 `common/` 约束。

## 前置检查（必须先于任何其他步骤执行）

在执行任何工作前，必须验证以下两项均已就绪：

1. `common/` 已正确覆盖：检查 `common/AGENT_CORE.md` 是否存在。
2. `tools/` 已正确覆盖：检查 `tools/spec/tool_catalog.json` 与 `tools/rdx.bat` 是否存在。

任一文件不存在时：

- 立即停止，不得继续任何工作。
- 不得降级处理、搜索替代工具路径、使用模型记忆或以其他方式绕过本检查。
- 向用户输出：

```
前置环境未就绪：请确认 (1) 已将 debugger/common/ 整包覆盖到平台根 common/；(2) 已将 RDC-Agent-Tools 整包覆盖到平台根 tools/；(3) 在平台根目录运行 python common/config/validate_binding.py --strict 通过后，再重新发起任务。
```

验证通过后，按顺序阅读：

1. common/AGENT_CORE.md
2. common/config/platform_adapter.json
3. common/skills/rdc-debugger/SKILL.md
4. common/docs/platform-capability-model.md
5. common/docs/model-routing.md

强制规则：

- 平台启动后默认保持普通对话态；只有用户手动召唤 `rdc-debugger`，才进入 RenderDoc/RDC GPU Debug 调试框架
- 除 `rdc-debugger` 之外，其他 specialist 默认都是 internal/debug-only，只能由 `rdc-debugger` 在框架内分派
- 用户尚未提供可导入的 `.rdc` 时，必须以 `BLOCKED_MISSING_CAPTURE` 停止，不得初始化 case/run 或继续做 debug、investigation、tool planning
- `codex` 的 `local_support` / `remote_support` / `enforcement_layer` 以 `common/config/platform_capabilities.json` 当前行与 `runtime_mode_truth.snapshot.json` 为准

未先将 `debugger/common/` 整包覆盖到平台根 `common/`、且将 RDC-Agent-Tools 整包覆盖到平台根 `tools/` 之前，不允许在宿主中使用当前平台模板。

运行时工作区固定为平台根目录下的 `workspace/`
- OpenAI Codex 当前原生支持 `AGENTS.md` 分层与 `.codex/agents/*.toml` custom agents；当前模板继续使用这两类 native surface。
- OpenAI Codex Hooks 当前只提供有限 guardrail，不足以为本框架的 native `rd.*` / specialist dispatch 提供可靠 host-side enforcement；因此当前 workspace-native 路径不引入 `.codex/hooks.json`，并按 `pseudo-hooks` 平台处理，而不是 hooks-based 平台。
- 当前平台的 enforcement 机制固定为 `runtime_owner + shared harness guard + audit artifacts`；`.codex/runtime_guard.py` 只是薄包装，唯一权威实现位于 `common/hooks/utils/harness_guard.py`。
- Codex 的执行门禁固定为：
  1. `.codex/runtime_guard.py preflight`
  2. `intent_gate`
  3. `.codex/runtime_guard.py accept-intake`：内部顺序执行 `entry-gate -> capture import + case/run bootstrap -> intake-gate -> runtime-topology`
  4. `.codex/runtime_guard.py dispatch-readiness` / `.codex/runtime_guard.py dispatch-specialist` / `.codex/runtime_guard.py specialist-feedback`
  5. `staged_handoff`
  6. `.codex/runtime_guard.py final-audit` → `artifacts/run_compliance.yaml` pass
  7. `.codex/runtime_guard.py render-user-verdict`
- `accept-intake` 成功后必须已经落盘 `artifacts/entry_gate.yaml`、`artifacts/intake_gate.yaml` 与 `artifacts/runtime_topology.yaml`，否则不得进入 handoff。
- 在 `artifacts/intake_gate.yaml` 通过前，不得执行 specialist dispatch 或 live `rd.*` 调试。

## Sub-Agent 协调约束

当前平台的 coordination_mode 为 `staged_handoff`。Codex sub-agents 之间**不具备直接通信能力**（no peer-to-peer channel）。

规则：

- 当前平台的 `sub_agent_mode = puppet_sub_agents`，不是 `team_agents`。
- remote 一律服从 `single_runtime_owner`；Codex 不支持多 specialist 共享同一条 live remote runtime。
- `rdc-debugger` 在 accepted intake 后必须先写出 `inputs/captures/manifest.yaml`、`capture_refs.yaml`、`notes/hypothesis_board.yaml`、`artifacts/intake_gate.yaml` 与 `artifacts/runtime_topology.yaml`。
- `staged_handoff` 在当前平台上是 hub-and-spoke 多轮接力，不是单 agent 串行切换。
- local 下允许 specialist 各持独立 context，形成 `multi_context_orchestrated`；跨 context 的 live transfer / resume 必须使用 `runtime_baton`。
- 当前平台固定声明 `specialist_dispatch_requirement = required`、`host_delegation_policy = platform_managed`、`host_delegation_fallback = none`。
- 默认 `orchestration_mode = multi_agent`；只有用户显式要求不要 multi-agent context 时，才允许 `single_agent_by_user`。
- `single_agent_by_user` 必须显式记录 `single_agent_reason = user_requested`，且主 agent 必须先向用户说明当前不分派 specialist。
- specialist dispatch 后，主 agent 必须进入 `waiting_for_specialist_brief` 并持续汇总阶段回报；短时 silence 不得触发 orchestrator 抢活。
- 超过框架预算仍未收到阶段回报时，应进入 `BLOCKED_SPECIALIST_FEEDBACK_TIMEOUT` 或等价阻断状态。
- direct RenderDoc Python fallback 只允许 local backend；若走直连路径，必须记录 `fallback_execution_mode=local_renderdoc_python` 与 `WRAPPER_DEGRADED_LOCAL_DIRECT`。
- Specialist sub-agents 只能通过 workspace artifacts 传递调查结果，不得直接调用或消息通知其他 specialist。
- 所有跨 agent 信息传递路径：sub-agent 将结果写入 `workspace/cases/<case_id>/runs/<run_id>/` 指定位置 → `rdc-debugger` 汇总与裁决 → 下一轮分派。
- Specialist handoff 结果必须落在 `workspace/cases/<case_id>/runs/<run_id>/notes/**` 或 `capture_refs.yaml`。
- Specialist 不得直接分派其他 specialist，所有分派必须经由 `rdc-debugger`。
- 标准分派顺序：`rdc-debugger` → `triage_agent` → `capture_repro_agent` → 专家 specialists（`pixel_forensics`、`pass_graph_pipeline`、`shader_ir`、`driver_device`）→ `skeptic_agent` → `curator_agent`。
- `curator_agent` 在 `multi_agent` 下仍是 finalization-required；`single_agent_by_user` 下由 `rdc-debugger` 自行输出最终报告，但必须显式记录该模式。

权威规范：参见 `common/docs/runtime-coordination-model.md` 中 `staged_handoff` 模式定义。
