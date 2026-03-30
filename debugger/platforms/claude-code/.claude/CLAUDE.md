# Claude Code 入口说明

@../AGENTS.md
@../common/AGENT_CORE.md
@../common/docs/platform-capability-model.md
@../common/docs/model-routing.md

当前目录是面向 `RenderDoc/RDC GPU debugger framework` 的 Claude Code platform-local 模板。

入口约束：

- 启动后保持普通对话态，不自动进入 debugger framework
- public main skill 为 `.claude/skills/rdc-debugger/`
- 只有用户显式调用 `rdc-debugger` 时，才进入 debugger framework
- 默认入口模式是 local-first `CLI`
- 只有用户明确要求 `MCP` 时，才切换到 `MCP`
- 已配置的 `MCP` server 只是可选接入面，不是默认 live-access 前提

运行时约束：

- 单独执行 `tools/rdx.bat --non-interactive cli ...`，或维护态 `python ...run_cli.py ...`，都只会建立 tools-layer session state
- 独立的 tools-layer session bootstrap 不会创建 framework `workspace/case/run`
- 只有手动触发且被 `rdc-debugger` 接受的 intake，才允许初始化 framework workspace state
- 运行时 workspace 固定在 platform-root `workspace/`

前置条件：

- 在将顶层 `debugger/common/` 拷贝到 platform-root `common/` 之前，不得使用当前模板
