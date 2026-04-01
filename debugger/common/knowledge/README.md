# RenderDoc/RDC GPU Debug · Knowledge Root（知识根目录）

`common/knowledge/` 是 Debugger framework 的知识真相根目录。

这里固定分成三层：

- `spec/`
  - 正式生效的 versioned knowledge store
- `library/`
  - run/session 沉淀的共享真相与检索资产
- `proposals/`
  - 正式 candidate 对象

运行现场仍位于 `../workspace/`，不与 `common/knowledge/` 混写。

## Session 真相分工

session 级真相固定拆成四层：

- `library/sessions/<session_id>/action_chain.jsonl`
- `library/sessions/<session_id>/session_evidence.yaml`
- `spec/registry/active_manifest.yaml`
- `../workspace/cases/<case_id>/runs/<run_id>/artifacts/run_compliance.yaml`

## 新 run 与历史召回

- 每个 `run` 都是独立 session 审计单元
- reopen / reconnect 产生新的 `session_id` 属于正常行为
- 新 run 复用的是历史 `action_chain` / `session_evidence` / BugCard / BugFull / reports
- 历史召回不复用 live handle，不建立第二套 session 镜像结构

## 自动演化流程

知识演进流程固定为：

`compliant run -> auto candidate -> replay validation -> shadow observation -> active / rolled_back`

自动演化只允许使用结构化真相：

- `action_chain.jsonl`
- `session_evidence.yaml`
- BugCard / BugFull
- approved counterfactual reviews

`report.md` 和 `visual_report.html` 不是知识晋升真相源。
