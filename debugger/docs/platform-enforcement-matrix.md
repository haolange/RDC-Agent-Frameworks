# Platform Enforcement Matrix

本文是 `debugger/` 唯一权威的平台 enforcement 口径。

目标不是描述“平台大概能做什么”，而是明确：哪些宿主可以把 guard 接到 native lifecycle hooks；哪些只能通过 wrapper / rules / workflow 伪造严格 hooks；哪些必须完全退化成无 hooks 的 external harness。

## 统一原则

- 共享 harness 状态机是唯一真相源：`preflight -> entry_gate -> accept_intake -> runtime_topology -> dispatch_readiness -> specialist_feedback -> final_audit -> user_verdict`。
- 平台原生 hooks 只负责拦截和触发共享 guard，不承载业务规则。
- `rdc-debugger` 是所有平台唯一 public entrypoint；其它 specialist 默认 internal-only。
- 没有 `artifacts/run_compliance.yaml(status=passed)`，任何平台都不得宣布结案。
- 对 pseudo-hooks / no-hooks 平台，不允许把 prompt、rules、workflow 文案误写成“原生严格执行”。

## 分级矩阵

| 平台 | enforcement tier | guard 注入点 | public entrypoints | 说明 |
|---|---|---|---|---|
| `claude-code` | `native-hooks` | `session_start` / `pre_tool_use` / `post_tool_use` / `stop` | `rdc-debugger` | 原生 hooks 只调用共享 harness |
| `copilot-cli` | `native-hooks` | `session_start` / `pre_tool_use` / `post_tool_use` / `stop` | `rdc-debugger` | 原生 hooks 只调用共享 harness |
| `codex` | `pseudo-hooks` | `pre_tool_use` / `post_tool_use` / `stop` | `rdc-debugger` | 正式 enforcement 是 `runtime_guard` wrapper，不把 Bash guardrail 记成通用 hooks |
| `code-buddy` | `pseudo-hooks` | `session_start` / `pre_tool_use` / `post_tool_use` / `stop` | `rdc-debugger` | 按 wrapper-dispatched pseudo-hooks 处理，不声称宿主 native lifecycle truth |
| `cursor` | `pseudo-hooks` | `post_tool_use` / `stop` | `rdc-debugger` | `.cursor/rules/rdc-debugger.mdc` / `hooks.json` 只是 wrapper 触发面，不是 native hooks |
| `copilot-ide` | `pseudo-hooks` | `post_tool_use` / `stop` | `rdc-debugger` | instructions / skills / MCP + shared harness |
| `claude-desktop` | `no-hooks` | `stop` | `rdc-debugger` | 依赖 workflow/audit，不模拟 native hooks |
| `manus` | `no-hooks` | `stop` | `rdc-debugger` | 依赖 workflow/audit，不模拟 native hooks |
| `codex_plugin` | `no-hooks` | `stop` | `rdc-debugger` | 插件提供入口，不提供宿主级严格 hooks |

## 平台行为要求

### `native-hooks`

- hooks 只调用 `common/hooks/utils/harness_guard.py` 或共享 `codebuddy_hook_dispatch.py`。
- 必须把 `session_start`、`pre_tool_use`、`post_tool_use`、`stop` 四类拦截点接到共享 guard。
- 平台 README 只能说“native hooks 触发共享 harness”，不能暗示规则定义在平台私有 hook 脚本里。

### `pseudo-hooks`

- 不得把 wrapper / rules / Bash guardrail / IDE 规则系统写成 native lifecycle hooks。
- 所有关键跃迁仍必须走共享 harness：`accept_intake`、`dispatch_specialist`、`final_audit`、`render_user_verdict`。
- 若宿主不能可靠阻断 direct tool use，应进一步退化为 single-entry harness。

### `no-hooks`

- 不尝试伪造 host-side strict interception。
- 只允许通过 shared harness + final audit 控制流程收口。
- workflow 串行平台不得模拟实时 multi-agent handoff 或 peer-to-peer specialist coordination。

## 文档治理

- `common/config/platform_capabilities.json` 和 `common/config/framework_compliance.json` 必须与本文一致。
- 平台 README、rules、hooks README、entrypoints 引导文档只能引用本文，不得再发明第二套 enforcement 口径。
- 若未来平台能力发生变化，必须先改本文，再改平台模板；不得先在单个平台 README 中偷跑新口径。
