# RenderDoc/RDC GPU Debug · Knowledge Library（knowledge/library/）

本目录用于存放调试过程中沉淀的知识与会话产物（可选但推荐）：

- `bugcards/`：可全文检索的 BugCard（YAML，供 rg/grep/IDE 搜索或 RAG 使用）
- `bugfull/`：面向工程师阅读的 BugFull（Markdown，10 章结构）
- `bugcard_index.yaml`：BugCard 索引（可选，用于去重/快速定位）
- `cross_device_fingerprint_graph.yaml`：跨设备指纹图（可选，用于关联同类问题）
- `sessions/`：live session 级 gate artifacts（`.current_session`、`session_evidence.yaml`、`skeptic_signoff.yaml`、`action_chain.jsonl`）

示例、教学样例与测试夹具已迁到 `../examples/`，不得继续放在 `library/sessions/` 下。

> 注意：本仓库仅提供空结构与规范示例。真实项目的知识沉淀请按团队流程生成与维护。

与 `workspace/` 的分工：

- `knowledge/library/`：第一层真相沉淀；供 hook、validator、检索与复盘使用
- `../workspace/cases/<case_id>/runs/<run_id>/reports/`：第二层交付层；供需求方/协作者快速阅读

第二层规则：

- `report.md` 与 `visual_report.html` 只能引用这里已经成立的证据与结论
- 不得为了展示效果回写或篡改本目录中的真相产物

