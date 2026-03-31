# RenderDoc/RDC GPU Debug · Knowledge Library（共享知识库）

本目录存放共享知识沉淀与 live session 真相。

## 目录说明

- `bugcards/`
  - 可检索的 BugCard YAML
- `bugfull/`
  - 面向工程师的完整调试报告
- `bugcard_index.yaml`
  - BugCard 索引
- `cross_device_fingerprint_graph.yaml`
  - 跨设备指纹图
- `sessions/`
  - live session 级 artifacts
  - 允许的结构固定为：
    - `.current_session`
    - `<session_id>/action_chain.jsonl`
    - `<session_id>/session_evidence.yaml`
    - `<session_id>/skeptic_signoff.yaml`

## Session Artifact 角色

- `action_chain.jsonl`
  - append-only ledger，记录事实事件
- `session_evidence.yaml`
  - adjudicated snapshot，记录当前裁决
- `skeptic_signoff.yaml`
  - Skeptic 审查与签署记录

`run_compliance.yaml` 不落在本目录下；它属于 run 工作区的审计派生产物。

## 与 `workspace/` 的分工

- `knowledge/library/`：第一层真相沉淀，供 hook、validator、检索与复盘使用
- `../workspace/cases/<case_id>/runs/<run_id>/reports/`：第二层交付层，供需求方/协作者阅读

规则：

- report 只能引用已经存在的 event / snapshot / proposal
- 不得为了展示效果回写或篡改本目录中的真相产物
- 示例与夹具只允许放在 `../examples/`，不得混入 `library/sessions/`
