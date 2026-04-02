# Platform Enforcement Matrix

本文是 `debugger/` 唯一权威的 platform enforcement 入口。

目标不是描述“平台大概能做什么”，而是明确：哪些宿主可以把 guard 接到 native lifecycle hooks，哪些只能通过 wrapper / rules / workflow 伪装成 hooks，哪些只能退化成 external harness。

## 统一原则

- `rdc-debugger` 是所有平台唯一 public entrypoint，但内部固定为 `Plan / Intake Phase -> Audited Execution Phase` 两段。
- 宿主若支持 Plan Mode，应先把用户请求收敛为 `debug_plan`；严格执行链从 `entry_gate` 开始，而不是从第一次唤起 skill 开始。
- 共享 harness 状态机是唯一真相源：`preflight -> entry_gate -> accept_intake -> dispatch_readiness -> dispatch_specialist -> specialist_feedback -> final_audit -> user_verdict`。
- `accept_intake` 内部负责 `capture import -> case/run bootstrap -> intake_gate -> broker startup`，并产出 `runtime_session.yaml`、`runtime_snapshot.yaml`、`ownership_lease.yaml`、`runtime_failure.yaml`。
- 平台原生 hooks 只负责拦截和触发共享 guard，不承载业务规则。
- `rdc-debugger` 是所有平台唯一 public entrypoint；其他 specialist 默认 internal-only。
- 没有 `artifacts/run_compliance.yaml(status=passed)`，任何平台都不得宣布结案。
- 对 `pseudo-hooks` / `no-hooks` 平台，不允许把 prompt、rules、workflow 文案误写成“原生严格执行”。

## 分级矩阵

| 平台 | enforcement tier | guard 注入点 | public entrypoints | 说明 |
|---|---|---|---|---|
| `claude-code` | `native-hooks` | `session_start` / `pre_tool_use` / `post_tool_use` / `stop` | `rdc-debugger` | 原生 hooks 只调共享 harness。 |
| `copilot-cli` | `native-hooks` | `session_start` / `pre_tool_use` / `post_tool_use` / `stop` | `rdc-debugger` | 原生 hooks 只调共享 harness。 |
| `codex` | `pseudo-hooks` | `pre_tool_use` / `post_tool_use` / `stop` | `rdc-debugger` | 正式 enforcement 是 `runtime_guard` wrapper，不把 Bash guardrail 写成通用 hooks。 |
| `code-buddy` | `pseudo-hooks` | `session_start` / `pre_tool_use` / `post_tool_use` / `stop` | `rdc-debugger` | 由 wrapper-dispatched pseudo-hooks 处理，不宣称宿主原生 lifecycle truth。 |

## 平台行为要求

### `native-hooks`

- hooks 只调用 `common/hooks/utils/harness_guard.py` 或共享 `codebuddy_hook_dispatch.py`。
- 必须把 `session_start`、`pre_tool_use`、`post_tool_use`、`stop` 四类拦截点接到共享 guard。
- 平台 `README.md` 只能说“native hooks 触发共享 harness”，不能把规则定义藏进平台私有 hook 脚本。

### `pseudo-hooks`

- 不得把 wrapper、rules、Bash guardrail 或 IDE 规则系统写成 native lifecycle hooks。
- 宿主 Plan Mode 只负责前置规划/澄清容器，不得被描述成已经进入严格 execution。
- 所有关键跃迁仍然必须走共享 harness：`accept_intake`、`dispatch_specialist`、`final_audit`、`render_user_verdict`。
- 不得伪造独立 runtime 所有权；所有 live runtime 访问都要经过 broker-owned session + ownership lease。

### `no-hooks`

- 不尝试伪造 host-side strict interception。
- 只允许通过 workflow gate + audit + broker-owned runtime artifacts 维持最小可信链路。
