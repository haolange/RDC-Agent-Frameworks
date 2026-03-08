# AGENTS.md

## Scope

本仓库是 `RDC-Agent Frameworks` 的上层框架仓库，重点是用清晰、可审计、可演进的方式组织 Agent 使用 RenderDoc/RDC 平台 tools。

## Hard Rules

- 不要把历史实现名、过时目录名、旧平台路径提升为框架概念。
- 平台工具接入、catalog 路径、启动命令属于 adapter/config 层，不属于 framework 真相。
- 任何用户面向文案都必须明确：Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。
- 不要把 skill 写成狭窄的“知识载入提示”；主 skill 必须覆盖任务目标、模式选择、工具边界和关键约束。
- 写给用户和 Agent 的文档内容应以中文为主，但 RenderDoc、RDC、MCP、CLI、hook、skill、agent、session、artifact、tool contract、tool catalog、prompt、plugin、workspace 等专业名词保留英文。

## No Legacy Rule

这是本仓库的铁律：**不要在工程里留下 legacy、deprecated、transitional、兼容层双轨残留。**

具体要求：

- 当新结构替代旧结构后，旧目录、旧文件、旧 skill、旧平台适配必须在同一轮改动中删除。
- 不允许保留“deprecated but kept for transition”这类目录作为长期存在物。
- 不允许为了避免修改引用而保留旧路径镜像。
- 不允许同时维护新旧两套路径、两套 skill 名、两套平台目录。
- 若确实因外部宿主限制无法立即删除，必须在交付说明中明确列出残留项、阻塞原因和删除条件；默认情况下一律删除。

## Platform Expectations

- `code-buddy/` 是当前最高完成度参考实现，应保持 `plugin + agents + hooks + skills + MCP` 的完整形态，并把角色模型与协作元数据落实到宿主入口。
- `claude-code/`、`copilot-cli/`、`copilot-ide/` 应按各自宿主的最佳能力实现，不要退化成纯 prompt 镜像。
- `claude-desktop/` 与 `manus/` 若能力不足，应明确标注为次优适配，而不是伪装成满配实现。

## Model Routing

- 角色到模型偏好以 `debugger/common/config/model_routing.json` 为 SSOT。
- 平台支持 per-agent model 时按映射落地。
- 平台不支持时，只允许降级模型绑定方式，不允许改写角色分工。

## Validation

完成平台或文档改动后，至少检查：

- `python debugger/scripts/sync_platform_scaffolds.py --check`
- `python debugger/scripts/validate_tool_contract.py --strict`
- 搜索是否仍残留旧目录名、旧 skill 名、deprecated 文案或双轨路径
