# Copilot IDE Entrypoints（宿主入口说明）

当前目录只提供宿主入口提示；运行时共享文档统一从当前平台根目录的 `common/` 读取。

先阅读：

1. AGENTS.md
2. common/docs/platform-capability-model.md

未先将顶层 `debugger/common/` 拷入当前平台根目录的 `common/` 之前，不允许在宿主中使用当前平台模板。

- 当前平台按 `pseudo-hooks` 处理；只有生成 `artifacts/run_compliance.yaml` 且 `status=passed` 后，结案才算合规。
运行时工作区固定为平台根目录下的 `workspace/`
