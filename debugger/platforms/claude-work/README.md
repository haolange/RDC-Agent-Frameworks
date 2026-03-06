# Claude Work Adaptation

这是面向 `Claude Work` 的本地契约降级适配，不是满配平台实现。

## 提供内容

- `plugin.json`
- `agents/`
- `references/entrypoints.md`

## 明确缺失

- 不提供一等 skill 目录
- 不宣称 hooks 完整支持
- 不承诺 per-agent model 精确控制

## 使用边界

- 保留角色分工和证据门槛
- 若任务依赖完整 hooks / rich MCP orchestration，应优先切回 `code-buddy`、`claude-code` 或 `copilot-cli`
