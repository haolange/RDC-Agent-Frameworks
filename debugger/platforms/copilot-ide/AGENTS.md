# Copilot IDE Workspace Instructions（工作区约束）

当前目录是 Copilot IDE 的 platform-local 模板。所有角色在进入 role-specific 行为前，都必须先服从本文件与共享 `common/` 约束。

## 前置检查（必须先于任何其他步骤执行）

在执行任何工作前，必须验证以下两项均已就绪：

1. `common/` 已正确覆盖：检查 `common/AGENT_CORE.md` 是否存在。
2. `tools/` 已正确覆盖：检查 `tools/spec/tool_catalog.json` 是否存在。

任一文件不存在时：

- 立即停止，不得继续任何工作。
- 不得降级处理、搜索替代工具路径、使用模型记忆或以其他方式绕过本检查。
- 向用户输出：

```
前置环境未就绪：请确认 (1) 已将 debugger/common/ 整包覆盖到平台根 common/；(2) 已将 RDC-Agent-Tools 整包覆盖到平台根 tools/；(3) 在平台根目录运行 python common/config/validate_binding.py --strict 通过后，再重新发起任务。
```

验证通过后，按顺序阅读：

1. common/AGENT_CORE.md
2. common/config/platform_adapter.json
3. common/skills/renderdoc-rdc-gpu-debug/SKILL.md
4. common/docs/platform-capability-model.md
5. common/docs/model-routing.md

强制规则：

- 正常用户入口只有 `team_lead`
- 其他 specialist 默认是 internal/debug-only，由 `team_lead` 决定是否分派
- 用户未提交 `.rdc` 时，必须以 `BLOCKED_MISSING_CAPTURE` 停止，不得初始化 case/run 或继续做 debug、investigation、tool planning

未先将 `debugger/common/` 整包覆盖到平台根 `common/`、且将 RDC-Agent-Tools 整包覆盖到平台根 `tools/` 之前，不允许在宿主中使用当前平台模板。

运行时工作区固定为：`../workspace`
- 当前宿主没有 native hooks；只有生成 `artifacts/run_compliance.yaml` 且 `status=passed` 后，结案才算合规。
