# Platform Adapter Config

本目录保存框架到具体平台工具实现的默认接入配置。

原则：

- 这里描述“默认实现如何接上平台工具仓库”。
- 这里不定义框架概念本身。
- `rd.*` 能力面、共享响应契约、session 生命周期等第一性约束，仍由平台能力层和上层框架文档描述。

当前文件：

- `platform_capabilities.json`
  - `runtime_contract`: 与宿主无关的 live runtime 约束。
  - `platforms.*.handoffs`: 宿主有没有 handoff 能力。
  - `platforms.*.coordination_mode`: framework 在该宿主上的实际协作拓扑。
- `platform_adapter.json`
  - `paths.tools_root`: 平台工具工作区根目录默认值。
  - `paths.catalog_path`: tool catalog 默认位置。
  - `mcp.server_name`: 平台 `MCP` 适配名称。
  - `mcp.launch_command`: 默认 `MCP` 启动入口。
  - `cli.launcher`: 默认 `CLI` 启动入口。
  - `cli.reference_doc`: 用户要求 `CLI` 模式时应优先阅读的附属说明。

约束：

- 这里允许绑定当前环境中的具体实现默认值。
- 其他文档和 Prompt 不应把这些路径或名字当成框架真相。

