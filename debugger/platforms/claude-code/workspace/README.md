# Platform Local Workspace Placeholder

当前目录是平台本地 `workspace/` 运行区骨架。

用途：

- 存放 capture-first 的 `case_id/run_id` 级运行现场
- 承载 case 级 `inputs/captures/`、run 级 `screenshots/`、`artifacts/`、`logs/`、`notes/`
- 承载第二层交付物 `reports/report.md` 与 `reports/visual_report.html`

约束：

- 这里不是共享真相；共享真相仍由同级 `common/` 提供。
- `common/` 中的 shared prompt / skill / docs 应通过 `../workspace` 引用当前目录。
- 原始 `.rdc` 只允许落在 `cases/<case_id>/inputs/captures/`，不得落在 `runs/<run_id>/`
- 模板仓库只保留占位骨架，不提交真实运行产物。
