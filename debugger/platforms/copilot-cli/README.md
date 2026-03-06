# Copilot CLI Adaptation

这是面向 Copilot CLI plugin 的完整适配包。

## 完成态

- `.copilot-plugin.json`
- `agents/`
- `hooks/hooks.json`
- `.mcp.json`
- `skills/renderdoc-rdc-gpu-debug/`

## 使用边界

- `MCP` 模式允许 discovery-first flow
- 用户要求 `CLI` 模式时，必须先阅读 skill 中的 `cli-mode-reference.md`
- 不允许靠 `--help`、枚举命令、随机试跑来猜能力面

## 模型策略

- 当前默认 `inherit`
- 即使宿主不支持 per-agent model，也保留角色分工与证据门槛
