# RenderDoc/RDC GPU Debug Workflow

## 目标

在低能力宿主中，用 workflow 方式完成 RenderDoc/RDC GPU Debug 的最小闭环。正常任务 intake 仍由 	eam_lead / orchestrator 语义承担。

## 阶段

1. 	ools preflight
 - 校验 platform_adapter.json 与 	ools_root
2. 	eam_lead intake
 - 接收用户请求，决定 triage / capture / specialist 的推进顺序
3. 	riage
 - 结构化现象、触发条件、可能的 SOP 入口
4. capture/session
 - 确认 .rdc、session、frame、event anchor
5. specialist analysis
 - 从 pipeline、forensics、shader、driver 四个方向收集证据
6. skeptic
 - 复核证据链是否足以支持结论
7. curation
 - 生成 BugFull / BugCard，写入 session artifacts

## workflow 约束

- Manus 不承担 custom agents / per-agent model 的宿主能力。
- 	ools_root 未配置或校验失败时必须立即停止。
- workflow 的每一阶段都必须引用共享 artifact contract。
- workflow_stage 是该平台的协作上限，不模拟 team-agent 实时协作。
- remote 阶段由单一 runtime owner 顺序完成 
d.remote.connect -> rd.remote.ping -> rd.capture.open_file -> rd.capture.open_replay -> re-anchor -> collect evidence。
- 若需要跨轮次继续调查，必须依赖可重建的 
untime_baton，不得凭记忆续跑 live runtime。
- 如需动态 tool discovery，应停止 workflow 并切回支持 MCP 的平台。
- 在 workflow 平台上，只有 rtifacts/run_compliance.yaml 为 status=passed 时，结案才算合规。
