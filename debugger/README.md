# RenderDoc/RDC GPU Debug（调试框架）

`debugger/` 是 `RDC-Agent-Frameworks` 中面向 RenderDoc/RDC GPU 调试场景的专属 framework 根目录。

当前目标态收敛为单一公开入口、双阶段内部流程：

- 唯一协作模式是 `staged_handoff`
- 唯一编排模式是 `multi_agent`
- local / remote 统一遵守 `single_runtime_single_context`
- live tools process 由 shared broker/coordinator 直接持有
- specialist 只通过 broker action + ownership lease 消费 live runtime
- `session_id`、`context_id`、`active_event_id` 等 runtime id 只属于 broker runtime view，不作为跨阶段稳定主键传播
- 临时 Python / PowerShell / shell wrapper 封装 live CLI 一律视为流程偏差

`rdc-debugger` 继续是唯一 public entrypoint，但内部固定拆成两段：

1. `Plan / Intake Phase`
   - 兼容宿主 Plan Mode
   - 默认通过轻量 sub-agent 收敛用户自然语言、补料与 reference contract
   - 唯一正式输出是 `debug_plan`
   - 不创建 case/run，不写 run/session 审计产物，不接触 live runtime
2. `Audited Execution Phase`
   - 从 `entry_gate` 开始进入严格链
   - 固定流程为：`entry_gate -> accept_intake / intake_gate -> triage -> dispatch/specialist loop -> skeptic -> curator -> final_audit / user_verdict`

Plan 阶段只负责把用户事实转换为可执行 contract；严格执行链和 broker-owned runtime 控制面仍维持现有模型。

## 使用前提

开始使用 `debugger/` 之前，必须先完成：

1. 将仓库根目录 `debugger/common/` 整体拷贝到目标平台根目录的 `common/`
2. 将 `RDC-Agent-Tools` 根目录整包拷贝到目标平台根目录的 `tools/`
3. 运行 `python common/config/validate_binding.py --strict`，确认 package-local `tools/`、zero-install runtime、snapshot 与宿主入口文件全部对齐
4. 提供至少一份可导入 `.rdc`
5. 提供足以让 Plan 阶段生成 `strict_ready reference_contract` 的事实和参考材料

未完成以上前置条件前：

- 缺少 `.rdc` 时必须以 `BLOCKED_MISSING_CAPTURE` 阻断
- 参考材料不足以生成 `strict_ready reference_contract` 时，必须以 `BLOCKED_MISSING_FIX_REFERENCE` 阻断 execution
- 不得初始化 case/run，不得进入 live 调查

## 文档边界

- `common/AGENT_CORE.md`：`debugger` framework 的硬约束与运行原则
- `common/docs/`：唯一运行时共享文档入口
- `common/hooks/`：shared harness / broker / audit enforcement
- `docs/`：仅服务维护者的模板与 scaffold 说明，不是运行时共享资料区

## 平台模板使用方式

平台模板位于 `platforms/<platform>/`。标准用户工作流：

1. 选择目标平台模板目录
2. 覆盖 `common/`
3. 覆盖 `tools/`
4. 运行 `python common/config/validate_binding.py --strict`
5. 在对应宿主中打开该平台根目录
6. 统一从 `rdc-debugger` 发起请求；其他角色默认是 internal/debug-only specialist

说明：

- 宿主若支持 Plan Mode，应先把用户请求收敛为 `debug_plan`，再由 `rdc-debugger` 进入 execution
- `CLI` / `MCP` 只表示工具入口模式，不改变 `staged_handoff + multi_agent + single_runtime_single_context` 的统一协作 contract
- shared harness 是唯一 enforcement SSOT；平台 hooks/runtime guard 只负责接入与转发
- accepted intake 后由 agent 创建 case/run，并导入 `.rdc` 到 `workspace/cases/<case_id>/inputs/captures/`
