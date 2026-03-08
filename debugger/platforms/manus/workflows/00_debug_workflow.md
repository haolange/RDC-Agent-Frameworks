# RenderDoc/RDC GPU Debug Workflow

## 目标

在低能力宿主中，用 workflow 方式完成 RenderDoc/RDC GPU Debug 的最小闭环。

## 阶段

1. `triage`
   - 结构化现象、触发条件、可能的 SOP 入口
2. `capture/session`
   - 确认 `.rdc`、session、frame、event anchor
3. `specialist analysis`
   - 从 pipeline、forensics、shader、driver 四个方向收集证据
4. `skeptic`
   - 复核证据链是否足以支持结论
5. `curation`
   - 生成 BugFull / BugCard，写入 session artifacts

## workflow 约束

- Manus 不承担 custom agents / per-agent model 的宿主能力。
- workflow 的每一阶段都必须引用共享 artifact contract。
- `workflow_stage` 是该平台的协作上限，不模拟 team-agent 实时协作。
- remote 阶段由单一 runtime owner 顺序完成 `rd.remote.connect -> rd.remote.ping -> rd.capture.open_file -> rd.capture.open_replay -> re-anchor -> collect evidence`。
- 若需要跨轮次继续调查，必须依赖可重建的 `runtime_baton`，不得凭记忆续跑 live runtime。
- 如需动态 tool discovery，应停止 workflow 并切回支持 `MCP` 的平台。
