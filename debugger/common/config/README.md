# Platform Adapter Config

本目录保存 framework 到 RenderDoc/RDC platform tools 的共享接入真相，以及平台渲染所需的控制面 SSOT。

约束：

- `debugger/common/` 是唯一长期维护来源。
- `debugger/platforms/*` 全部视为生成产物，只做 direct-reference，不再复制 `common/`。
- 平台模板里的 agents / skills / hooks / MCP / model / handoff 都必须来自本目录的共享配置和 `common/` 正文。
- 平台 tools 的真实路径、catalog、MCP/CLI 启动命令仍属于 adapter/config 层，不是 framework 真相。

当前文件：

- `role_manifest.json`：角色清单、共享 prompt 源和各平台文件名映射。
- `role_policy.json`：角色模型意图、reasoning/verbosity、delegation 与 tool/hook policy。
- `model_routing.json`：抽象模型策略与各宿主渲染映射。
- `mcp_servers.json`：逻辑 MCP server 定义。
- `platform_capabilities.json`：宿主能力真相、降级方式与必需入口。
- `platform_targets.json`：平台生成目标、目录布局和渲染面。
- `platform_adapter.json`：环境相关 adapter 默认值。

不允许在平台模板中手工散落第二份模型路由、handoff 图、hooks 规则或路径真相。
