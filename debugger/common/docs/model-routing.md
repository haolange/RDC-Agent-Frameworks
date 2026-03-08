# 模型路由

本文定义平台无关的角色模型意图，以及脚本如何把它们渲染成宿主原生配置。

## 统一原则

- 角色只声明“需要什么能力层级”，不在共享正文里硬编码宿主私有模型字符串。
- `common/config/model_routing.json` 负责抽象 profile 与宿主映射。
- `common/config/role_policy.json` 负责 reasoning / verbosity 等执行风格。
- `debugger/scripts/sync_platform_scaffolds.py` 负责把它们渲染到各平台的 alias、frontmatter、plugin 或 role config。

## 当前 profile

- `orchestrator`
  - 目标：深度规划、分派与裁决门槛控制
- `investigator`
  - 目标：证据优先、多轮调查、成本可控
- `verifier`
  - 目标：对抗性审查与反事实压力测试
- `reporter`
  - 目标：结构化报告与知识沉淀

## 平台渲染规则

- `code-buddy`
  - 使用显式模型字符串。
- `claude-code`
  - 使用 `opus` / `sonnet` alias。
- `copilot-cli`
  - 没有稳定的 per-agent model 渲染面时，统一降级为 `inherit`。
- `copilot-ide`
  - 用 preferred model 渲染；宿主忽略时不改角色边界。
- `claude-desktop`
  - Claude Desktop 不提供 per-agent model；只保留 `inherit` 级语义，不伪造精细模型控制。
- `manus`
  - 只保留 workflow 语义，不声明 per-agent model。
- `codex`
  - 渲染到 `.codex/config.toml` 与 `.codex/agents/*.toml`，通过 role config 绑定 per-role model / reasoning / verbosity。

## 约束

- 不允许在平台 agent 文件里手工散落模型策略。
- 不允许为某个平台改写角色分工来“适配模型限制”。
- 宿主若忽略某个模型字段，只允许降级绑定方式，不允许改写 role graph。

权威配置文件：

- `common/config/model_routing.json`
- `common/config/role_policy.json`
