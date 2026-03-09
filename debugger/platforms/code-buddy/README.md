# Code Buddy Template

当前目录是 Code Buddy 的 platform-local 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

使用方式：

1. 将仓库根目录 debugger/common/ 整体拷贝到当前平台根目录的 common/，覆盖占位内容。
2. 在当前平台根目录的 common/config/platform_adapter.json 中配置 paths.tools_root。
3. 确认 alidation.required_paths 在 <resolved tools_root>/ 下全部存在。
4. 使用当前平台根目录同级的 workspace/ 作为运行区。
5. 完成覆盖后，再在对应宿主中打开当前平台根目录。
6. 正常用户请求从 	eam_lead 发起；其他 specialist 默认是 internal/debug-only。

约束：

- common/ 默认只保留一个占位文件；正式共享正文仍由顶层 debugger/common/ 提供，并由用户显式拷入。
- 未完成 debugger/common/ 覆盖前，当前平台模板不可用。
- 未完成 platform_adapter.json 配置或 	ools_root 校验前，Agent 必须拒绝执行依赖平台真相的工作。
- workspace/ 预生成空骨架；真实运行产物在平台使用阶段按 case/run 写入。
- 维护者若重跑 scaffold，必须继续产出 platform-local common/ 最小占位目录，不得回退到跨级引用。
- native hooks 会阻断未通过 gate 的结案；同时仍要求生成 rtifacts/run_compliance.yaml 作为统一合规裁决。
