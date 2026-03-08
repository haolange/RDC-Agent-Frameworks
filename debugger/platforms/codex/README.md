# Codex Template

当前目录是 Codex 的 workspace-native direct-reference 模板。Agent 的目标是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题。

约束：

- 打开当前目录作为 Codex workspace root。
- 宿主入口由 `AGENTS.md`、`.agents/skills/`、`.codex/config.toml` 和 `.codex/agents/*.toml` 共同构成。
- `multi_agent` 当前按 experimental / CLI-first 理解，但共享规则与 role config 已完整生成。
