# BugFull 模板（Markdown）

> 建议输出路径：`common/knowledge/library/bugfull/BUG-XXX-001_full.md`
>
> 目标：让工程师可读、让证据可追溯、让结论可复现。

---

## 1. 问题概述

- 一句话摘要（设备 + 症状 + 复现条件）
- 症状截图/录屏（如有）
- 影响范围与严重性（用户可感知程度、回归风险）

## 2. 复现环境

- 异常侧（A）：设备 / OS / GPU / 驱动 / API / 分辨率 / 关键渲染开关
- 基准侧（B）：同上
- 复现率：必现 / 偶发（给出百分比与触发条件）

## 3. 调试时间线

按时间顺序记录关键节点（建议列出 event_id / Pass 名称 / 输出结论）：

- Triage：symptom_tags / trigger_tags / recommended_sop
- Capture：A/B capture 路径与 anchor
- Forensics：first_bad_event 与异常像素值
- Pipeline：发散点与资源链
- Shader/IR：可疑表达式与指纹
- Driver：API Trace / ISA 差异与归因

## 4. 假设板历程

附上 Hypothesis Board（或节选），并说明每条假设为何被推进/否决：

- H-001：ACTIVE → VALIDATE → VALIDATED（证据与反事实）
- H-002：ACTIVE → REFUTED（反驳证据）

## 5. 完整证据链

每条关键断言都必须能追溯到工具输出或制品路径（禁止“感觉像”）：

- E-001：截图对比（路径 / 坐标）
- E-002：Pixel History（event_id / first_bad_event）
- E-003：Shader Debug/IR 证据（表达式/装饰/寄存器）
- E-004：API Trace/Barrier/State diff（定量差异）

## 6. 反事实验证记录（强制）

反事实必须满足：
- 改变且仅改变关键变量
- 结果量化（像素值/误差/频率），禁止“看起来更好”

反事实验证记录建议写入 `common/knowledge/library/sessions/<session_id>/session_evidence.yaml`（evidence 列表中包含 `type: counterfactual_test`），并在结案前运行 `counterfactual_validator.py` 校验。

## 7. Skeptic 审查记录

- SKEPTIC_SIGN_OFF / SKEPTIC_CHALLENGE 的原文或摘要
- 未解质疑（如有）与回应路径

## 8. 根因结论

- 被违反的不变量：`I-XXX-YY`
- 精确根因描述：必须包含代码位置或驱动版本或 API 调用
- 归因层级：应用逻辑 / Shader / 编译器 / 驱动 / 硬件

## 9. 修复方案

- 最小修复（Minimal Patch）说明
- Patch diff（如可提供）
- 修复验证：A/B 对比、回归点、量化数据（像素 before/after）

## 10. 知识沉淀

- 生成 BugCard：路径 `common/knowledge/library/bugcards/bugcard_<BUG-ID>.yaml`
- 指纹：用于在 bugcards/ 与源码中全文检索的 pattern
- SOP 改进建议：如发现 SOP 缺漏，写入 `sop_improvement_notes`

---

## 附：BugCard（YAML 示例骨架）

```yaml
bugcard_id: BUG-XXX-001
title: "一句话描述"
symptom_tags: []
trigger_tags: []
violated_invariants: []
recommended_sop: SOP-XXX-01
root_cause_summary: >
  ...
fingerprint:
  pattern: "..."
  risk_category: "..."
  shader_stage: PS
fix_verified: true
fix_verification_data:
  pixel_before: {x: 0, y: 0, rgba: [0.0, 0.0, 0.0, 1.0]}
  pixel_after:  {x: 0, y: 0, rgba: [0.0, 0.0, 0.0, 1.0]}
skeptic_signed: true
bugcard_skeptic_signed: true
```

## 11. Session Artifacts（强制合同）

结案前必须将本次 session 的关键产出物落盘（供 Hook 校验、审计与复用）。

- `common/knowledge/library/sessions/<session_id>/session_evidence.yaml`
- `common/knowledge/library/sessions/<session_id>/skeptic_signoff.yaml`
- `common/knowledge/library/sessions/<session_id>/action_chain.jsonl`
- `common/knowledge/library/sessions/.current_session`（文件内容为当前 `session_id`）

Stop Hook 会通过 `common/hooks/utils/resolve_session_artifact.py` 读取 `.current_session` 并解析 artifacts 路径；缺失/不合法会阻断结案。

