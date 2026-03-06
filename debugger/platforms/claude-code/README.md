# Claude Code Adaptation

这是面向 Claude Code 的真实平台适配，不是 prompt 镜像目录。

## 完成态

- `agents/`：9 个角色镜像
- `skills/renderdoc-rdc-gpu-debug/`：主 skill 与 `CLI` reference
- `.claude/settings.json`：hooks 与 MCP 入口

## 模型策略

- `team_lead` 走 `opus`
- 6 个 investigator 走 `sonnet`
- `skeptic_agent` 与 `curator_agent` 在 Claude Code 中无法精确表达你指定的外部模型版本，因此回退到高能力 family alias，并在角色分工上保持不变

## 使用边界

- `MCP` 模式允许 discovery
- `CLI` 模式必须先阅读 skill 中的 `cli-mode-reference.md`
- 不允许靠 `--help` 或随机试跑来摸索平台能力
