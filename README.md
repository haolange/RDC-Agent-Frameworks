# RDC-Agent Frameworks

本仓库包含多个面向 RenderDoc/RDC 工作流的 Agent 框架实现与骨架，用于将复杂工程任务拆解为可复用、可审计、可演进的多 Agent 协作流程。

## 目录

- `debugger/`：Debugger Framework，面向 GPU 渲染 Bug 的多 Agent 调试框架（主驱动：正确性不变量）。
  - 入口：`debugger/README.md`
- `analyzer/`：Analyzer（骨架），面向“把未知系统结构化为可解释模型”的分析/还原类任务框架占位。
  - 入口：`analyzer/README.md`
- `optimizer/`：Optimizer（骨架），面向“可量化瓶颈归因 + 实验闭环”的性能优化类任务框架占位。
  - 入口：`optimizer/README.md`

## 约定（对齐 debugger 的关键原则）

- 将平台/工具的适配层与平台无关的核心 Prompt 分离；优先建立单一真相来源（SSOT）。
- 保持目录结构清晰可扩展：核心定义、平台适配、知识库/产物、质量门槛/校验等分层组织。