# Platform Adapter Config（平台适配配置）

本目录保存的是连接 `debugger` framework 与生成后平台模板的共享配置真相。

## 规则

- `debugger/common/` 是唯一长期存在的共享源目录。
- `debugger/platforms/*` 是生成后的平台产物。
- 只有在共享正文被拷入后，平台本地 wrapper 才允许引用平台本地的 `common/` 目录。
- `platform_adapter.json` 中的 `paths.tools_source_root` 固定为 `tools`；它只表示 package-local source payload，不代表 live runtime 目录。
- `platform_adapter.json` 中的 `runtime.mode` 固定为 `worker_staged`；live runtime 由 daemon-owned worker 物化到独立 cache 后再加载。
- `RDC-Agent-Tools` 必须以 package-local 目录形式复制到平台根的 `tools/`，而不是通过绝对路径或用户自定义路径接线。
- 当前 `Tools` 的正式用户入口固定为 `tools/rdx.bat`；`MCP` opt-in 通过 `cmd /c tools/rdx.bat --non-interactive mcp` 或等价包装接线，不以系统 `Python` 为正式前提。

## 文件说明

- `platform_adapter.json`
  - package-local `tools/` 绑定、required paths、zero-install runtime 必需文件与 CLI launcher 入口的共享 contract。
- `role_manifest.json`
  - 角色清单、共享 prompt 映射、共享 skill 映射与平台文件名。
- `role_policy.json`
  - reasoning effort、verbosity、tool policy、hook policy 与 delegation。
  - 不得包含按平台拆分的模型路由。
- `model_routing.json`
  - 模型能力要求、平台分类和角色到平台模型路由的唯一来源。
- `mcp_servers.json`
  - 逻辑 MCP server 定义；默认通过 `cmd /c tools/rdx.bat --non-interactive mcp` 接线。
- `platform_capabilities.json`
  - 宿主能力真相、降级语义与生成后的必需路径。
- `platform_targets.json`
  - 生成目标、目录布局与渲染面定义。

## 使用方式

1. 将 `debugger/common/` 覆盖到目标平台根目录的 `common/`。
2. 将 `RDC-Agent-Tools` 整包复制到目标平台根目录的 `tools/`。
3. 运行 `python common/config/validate_binding.py --strict`，确认 `tools/rdx.bat`、bundled runtime、snapshot 与宿主入口配置全部对齐。
4. 校验失败时拒绝执行 `debugger`。
5. 模型路由只允许维护在 `model_routing.json` 中。

生成后的 wrapper、插件文件和角色配置都应从本目录重新同步，不应在平台产物上手工打补丁。
