# Cursor Template

当前目录是 Cursor 的 platform-local 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

使用方式：

1. 将仓库根目录 `debugger/common/` 整体拷贝到当前平台根目录的 `common/`，覆盖占位内容。
2. 在当前平台根目录的 `common/config/platform_adapter.json` 中配置 `paths.tools_root`。
3. 确认 `validation.required_paths` 在 `<resolved tools_root>/` 下全部存在。
4. 正式发起 debug 前，用户必须在当前对话提交至少一份 `.rdc`。
5. 使用当前平台根目录同级的 `workspace/` 作为运行区。
6. 完成覆盖后，再在 Cursor 中打开当前平台根目录。
7. 正常用户请求从 `team_lead` 发起；其他 specialist 默认是 internal/debug-only。

约束：

- `common/` 默认只保留一个占位文件；正式共享正文仍由顶层 `debugger/common/` 提供，并由用户显式拷入。
- 未完成 `debugger/common/` 覆盖前，当前平台模板不可用。
- 未完成 `platform_adapter.json` 配置或 `tools_root` 校验前，Agent 必须拒绝执行依赖平台真相的工作。
- 未提供 `.rdc` 时，Agent 必须以 `BLOCKED_MISSING_CAPTURE` 直接阻断，不得初始化 case/run 或继续 triage、investigation、planning。
- `workspace/` 预生成空骨架；真实运行产物在平台使用阶段按 case/run 写入。
- 维护者若重跑 scaffold，必须继续产出 platform-local `common/` 最小占位目录，不得回退到跨级引用。
- native hooks 会阻断未通过 gate 的结案；同时仍要求生成 `artifacts/run_compliance.yaml` 作为统一合规裁决。

## Cursor 特有配置

- `.cursorrules`：项目级 AI 行为规则，定义工作模式、约束和质量门槛
- `.cursor/settings.json`：Cursor IDE 设置，包含 MCP 服务器配置和 Hooks

## 质量门槛检查清单

结案前必须确认：

- [ ] BugCard 完整性（12 项字段检查通过）
- [ ] Skeptic 五把刀签署全部通过
- [ ] 反事实验证记录存在且测试通过
- [ ] 因果锚点已确立并有证据支持
- [ ] `run_compliance.yaml` 已生成且状态为 passed
