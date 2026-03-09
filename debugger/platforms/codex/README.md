# Codex Template

当前目录是 Codex 的 workspace-native 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

使用方式：

1. 将仓库根目录 debugger/common/ 整体拷贝到当前平台根目录的 common/，覆盖占位内容。
2. 在 common/config/platform_adapter.json 中配置 paths.tools_root。
3. 确认 alidation.required_paths 在 <resolved tools_root>/ 下全部存在。
4. 使用当前平台根目录同级的 workspace/ 作为运行区。
5. 完成覆盖后，打开当前目录作为 Codex workspace root。
6. 正常用户请求从 	eam_lead 发起；其他 specialist 默认是 internal/debug-only。
7. AGENTS.md、.agents/skills/、.codex/config.toml 与 .codex/agents/*.toml 只允许引用当前平台根目录的 common/。

约束：

- common/ 默认只保留一个占位文件；正式共享正文仍由顶层 debugger/common/ 提供，并由用户显式拷入。
- 未完成 debugger/common/ 覆盖前，当前平台模板不可用。
- 未完成 platform_adapter.json 配置或 	ools_root 校验前，Agent 必须拒绝执行依赖平台真相的工作。
- workspace/ 预生成空骨架；真实运行产物在平台使用阶段按 case/run 写入。
- multi_agent 当前按 experimental / CLI-first 理解，但共享规则与 role config 已完整生成。
- 当前宿主没有 native hooks；只有生成 rtifacts/run_compliance.yaml 且 status=passed 后，结案才算合规。
