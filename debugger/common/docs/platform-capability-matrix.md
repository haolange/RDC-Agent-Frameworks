# 平台能力矩阵

当前 `debugger` 只承认一套平台 contract：

| Platform | Coordination | Orchestration | Live Runtime Policy | Hook SSOT | Default Entry | Allowed Entry Modes | Backends |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Claude Code | `staged_handoff` | `multi_agent` | `single_runtime_single_context` | `shared_harness` | `CLI` | `CLI, MCP` | `local, remote` |
| Code Buddy | `staged_handoff` | `multi_agent` | `single_runtime_single_context` | `shared_harness` | `CLI` | `CLI, MCP` | `local, remote` |
| Codex | `staged_handoff` | `multi_agent` | `single_runtime_single_context` | `shared_harness` | `CLI` | `CLI, MCP` | `local, remote` |
| Copilot CLI | `staged_handoff` | `multi_agent` | `single_runtime_single_context` | `shared_harness` | `CLI` | `CLI, MCP` | `local, remote` |

补充说明：

- shared harness / broker 是唯一 enforcement SSOT。
- 平台 hooks / runtime guard 只负责接入、转发、注入环境，不定义第二套运行规则。
- local / remote 不再分化为多 context 模型。