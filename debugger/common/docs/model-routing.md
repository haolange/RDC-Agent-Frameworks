# 模型路由

本文定义 Debugger framework 中角色到模型族的唯一权威路由。

## 权威来源

- `common/config/model_routing.json`
  - 负责模型能力要求、平台分类和按 profile 划分的平台路由。
- `common/config/role_policy.json`
  - 负责 reasoning effort、verbosity、tool policy、hook policy 与 delegation。
- `debugger/scripts/sync_platform_scaffolds.py`
  - 负责把共享真相渲染为宿主原生 wrapper、配置文件和插件 metadata。

任何平台 wrapper 都不得自创模型映射；`role_policy.json` 和生成后的宿主产物中也不得出现第二张 model-routing 表。

## 全局模型要求

所有 Debugger 角色都继承同一组基础模型约束：

- 必须原生支持 multimodal。
- 必须适合处理 texture 与 framebuffer 驱动的视觉分析。
- 必须支持长上下文。
- 当宿主或 provider 支持时，优先选择 1M context window。

之所以有这些约束，是因为 Debugger session 往往会在同一段对话里同时搬运 texture 导出、framebuffer 证据、shader 源码、IR 输出、JSON tool payload 与报告 artifact。

## 角色优先级

- `orchestrator`
  - 优先考虑规划深度、分支控制、想象力和裁决 gate。
- `investigator`
  - 优先考虑证据处理、长证据链和中等延迟下的深度检查。
- `verifier`
  - 优先考虑逻辑严谨性、对抗性审查和反事实施压测试。
- `reporter`
  - 优先考虑写作质量、知识沉淀和面向利益相关方的 web/report 生成能力。

## 平台分类

- 显式 per-agent routing
  - `code-buddy`、`copilot-ide`、`copilot-cli`
- 宿主受限的 per-agent routing
  - `claude-code`
- 仅继承的宿主
  - `claude-desktop`、`manus`
- 单一批准模型族的 per-agent routing
  - `codex`

## 当前路由策略

- `code-buddy`、`copilot-ide`、`copilot-cli`
  - `orchestrator` -> latest Opus
  - `investigator` -> latest Sonnet
  - `verifier` -> latest GPT
  - `reporter` -> latest Gemini
- `claude-code`
  - `orchestrator` -> Opus
  - `investigator` -> Sonnet
  - `verifier` -> Opus
  - `reporter` -> Sonnet
- `claude-desktop`、`manus`
  - 全部角色 -> `inherit`
- `codex`
  - 全部角色 -> latest GPT
  - 角色差异通过 reasoning 与 verbosity 区分，而不是依赖不同模型族。

补充说明：

- `claude-desktop`、`manus` 的 `inherit` 只描述模型控制方式，不表示禁用 `MCP`。
- 当前入口模式仍以 `platform_capabilities.json` 的 `default_entry_mode` / `allowed_entry_modes` 为准，其中 `manus` 是 MCP-only。

## 约束

- 生成后的平台文件必须始终来自 `model_routing.json`。
- inherit-only 平台不得携带失效的显式模型字符串。
- 能渲染 per-agent model 的平台必须显式暴露路由表选中的模型。
- 无法渲染 per-agent model 的平台可以保留角色边界和 workflow 边界，但不得假装支持宿主并不具备的模型控制能力。
