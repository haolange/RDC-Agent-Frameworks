# RenderDoc/RDC GPU Debug Workflow（工作流说明）

## 目标

在低能力宿主中，用 workflow 方式完成 RenderDoc/RDC GPU Debug 的最小闭环。正常用户入口仍由 `rdc-debugger` 承担，正式 intake normalization 则由 `team_lead` / orchestrator 语义承担。

## 阶段

1. `tools preflight`
 - 校验 `platform_adapter.json`、`tools_source_root` 与 `runtime.mode`
2. `team_lead intake`
 - 先检查用户是否已提供可导入的 `.rdc`；可在当前对话上传，或提供宿主当前会话可访问的文件路径；若缺失则以 `BLOCKED_MISSING_CAPTURE` 直接阻断
3. `triage`
 - 仅在 capture intake 完成后，结构化现象、触发条件、可能的 SOP 入口
4. `capture/session`
 - 确认 case 级 capture 输入池中的 `.rdc`、session、frame、event anchor
5. `specialist analysis`
 - 从 pipeline、forensics、shader、driver 四个方向收集证据
6. `skeptic`
 - 复核证据链是否足以支持结论
7. `curation`
 - 生成 BugFull / BugCard，写入 session artifacts

## workflow 约束

- Manus 不承担 custom agents / per-agent model 的宿主能力。
- Manus 的工具入口只允许 `MCP`；workflow stage 不得改写成 CLI-first。
- 开始任何阶段前，必须先完成 MCP preflight；若 MCP server 未配置完成，必须立即停止。
- `tools_source_root` 未配置、source payload 校验失败或 `runtime.mode` 不是 `worker_staged` 时必须立即停止。
- 用户尚未提供可导入的 `.rdc` 时必须以 `BLOCKED_MISSING_CAPTURE` 立即停止。
- workflow 的每一阶段都必须引用共享 artifact contract。
- `workflow_stage` 是该平台的协作上限，不模拟 team-agent 实时协作。
- 若需要跨轮次继续调查，必须依赖可重建的 `runtime_baton`，不得凭记忆续跑 live runtime。
- experimental remote rehydrate 不属于当前正式支持能力；若任务依赖 remote live bridge，应停止 workflow 并切回已验证该路径的平台。
- 如需动态 tool discovery、多 live owners 或 per-agent model routing，应停止 workflow 并切回更高能力平台。
- 在 workflow 平台上，只有 `artifacts/run_compliance.yaml` 为 `status=passed` 时，结案才算合规。
