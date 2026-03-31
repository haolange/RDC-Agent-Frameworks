# Manus Entrypoints（宿主入口说明）

当前目录只提供宿主入口提示；运行时共享文档统一从当前平台根目录的 `common/` 读取。

先阅读：

1. AGENTS.md
2. common/docs/platform-capability-model.md

未先将顶层 `debugger/common/` 拷入当前平台根目录的 `common/` 之前，不允许在宿主中使用当前平台模板。

- 当前平台属于 `no-hooks` tier；宿主不支持 custom agents、native lifecycle hooks 与 per-agent model control，但当前模板提供 wrapper skills 来统一入口语义。
- 当前宿主按 `workflow_stage` 降级运行；最终仍必须生成 `artifacts/run_compliance.yaml` 才算合规结案。
- 不得在该宿主上模拟实时 multi-agent handoff。
- 当前平台只允许 `MCP` 作为工具入口，不允许尝试 `CLI`。
- 开始任何平台真相相关工作前，必须先完成 MCP preflight；若 MCP server 未配置完成，必须直接阻断。
- 若任务需要更高阶 remote 多轮会诊、多 live owners 或 per-agent model routing，必须切回更高能力平台。
运行时工作区固定为平台根目录下的 `workspace/`
