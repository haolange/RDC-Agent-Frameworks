# BugFull 模板（Markdown）

> 建议输出路径：`common/knowledge/library/bugfull/BUG-XXX-001_full.md`

## 1. 问题概述

- 一句话摘要
- 症状截图/录屏
- 影响范围与严重性

## 2. Intake 合同

- `case_input.yaml` 路径
- `session.mode`
- `reference_contract` 摘要
- strict / fallback 语义验证等级

## 3. 复现环境

- 异常侧（A）
- 基准侧（B）
- 复现率

## 4. 调试时间线

- Triage
- Capture
- Forensics
- Pipeline
- Shader/IR
- Driver
- Fix Verification

## 5. 完整证据链

- E-001：capture/session anchor
- E-002：Pixel History
- E-003：Shader / IR
- E-004：API Trace / ISA
- E-005：fix_verification.yaml

## 6. 反事实验证记录

- `reference_contract_ref`
- `verification_mode`
- `baseline_source`
- probe 级量化结果

## 7. Skeptic 审查记录

- 结构修复判定
- 语义修复判定
- strict / fallback 结论

## 8. 根因结论

- 被违反的不变量
- 精确根因描述
- 归因层级

## 9. 修复方案

- 最小修复说明
- 修复验证：
  - `structural_verification`
  - `semantic_verification`
  - `overall_result`

## 10. 知识沉淀

- BugCard 路径
- 指纹
- SOP 改进建议
