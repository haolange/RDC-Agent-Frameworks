# Debugger 共享内核

`debugger/common/` 是 `debugger` framework 的唯一共享执行内核与真相源。
它不是平台占位目录，也不是平台模板说明页。用户把顶层 `debugger/common/` 覆盖到某个平台根目录的 `common/` 后，当前 README 就成为该平台运行时 `common/` 的正式入口说明。

## 目录职责

- `AGENT_CORE.md`：框架级硬约束、流程边界与运行原则。
- `agents/`：共享角色正文与分工定义。
- `config/`：共享合同与运行配置。`platform_capabilities.json` 描述目标合同，`adapter_readiness.json` 单独描述当前 adapter 完成度与 strict readiness，不得混写。
- `docs/`：共享运行时文档与实现说明。
- `hooks/`：共享 gate、validator、runtime guard、audit 与 fail-closed 控制逻辑。
- `knowledge/`：共享 session/library 真相与提案存储。
- `skills/`：共享主技能与角色技能正文。

## Common-First 原则

- `common/` + package-local `tools/` 是唯一执行内核；`platforms/*` 只承载宿主 adapter 壳。
- 平台 README / AGENTS / hooks / skills / agents 可以描述宿主接入方式，但不能把目标合同、prompt 规则或 wrapper 行为写成宿主原生 enforcement。
- 严格执行必须依赖 shared harness、runtime lock、freeze state、artifact gate、finalization receipt 等硬控制面，而不是文案提醒。
- `platform_capabilities.json` 是目标合同，不直接代表当前 strict 完成度。
- `adapter_readiness.json` 是当前 adapter 状态出口；只有它和验证结果一起才能支撑 strict readiness 宣称。

## 使用要求

- `platforms/<platform>/common/README.md` 在模板阶段只是占位说明，不是运行时正文。
- 完成覆盖后，平台根目录的 `common/README.md` 必须是当前文件，而不是 placeholder。
- 平台内所有 agent、skill、hook、config 只允许引用当前平台根目录的 `common/`，不得跨级回指仓库源路径。
- 覆盖 `common/` 与 `tools/` 后，必须在平台根目录运行 `python common/config/validate_binding.py --strict`，确认 package-local 绑定、生效路径与 zero-install runtime 全部就绪。
