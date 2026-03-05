# AIRD Framework · Knowledge Root（common/knowledge/）

`common/knowledge/` 是 AIRD 框架里所有「知识/案例资产」的统一根目录，避免在 `kb`、`cases`、`taxonomy` 等多处来回跳转。

## 目录约定

- `spec/`：规范知识（**必须稳定、可版本化**）
  - `spec/taxonomy`：分类学（symptom/trigger 标签）
  - `spec/invariants`：不变量库（detection_hints、known_issues、路由索引）
  - `spec/skills`：SOP 与工具链规范（含 `sop_library.yaml`）
- `library/`：运行时知识库（**可检索成品**）
  - `library/bugcards/`：BugCard（YAML，供检索/RAG）
  - `library/bugfull/`：BugFull（Markdown，完整调试报告）
  - `library/bugcard_index.yaml`、`library/cross_device_fingerprint_graph.yaml`：索引与指纹图（可选）
- `traces/`：调试过程记录（**会话产物**）
  - `traces/action_chains/`：Action Chains（用于复盘与 SOP 抽取）
- `templates/`：模板与示例（**写作辅助，不直接入库**）
  - `templates/bugcards/`、`templates/bugfulls/`

## 路径使用（动态加载）

Agent prompt 中的「动态加载声明」统一使用**相对于 `common/`** 的路径，例如：

- `knowledge/spec/taxonomy/symptom_taxonomy.yaml`
- `knowledge/spec/invariants/invariant_library.yaml`
- `knowledge/spec/skills/sop_library.yaml`

## 迁移提示

旧目录已收敛进本目录（不保留兼容层）：

- `common/kb` → `common/knowledge/library`
- `common/cases` → `common/knowledge/traces` / `common/knowledge/templates`
- `common/taxonomy` / `common/invariants` / `common/skills` → `common/knowledge/spec/...`
