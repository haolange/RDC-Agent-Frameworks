# 平台本地 `workspace/` 占位说明

当前目录是平台本地 `workspace/` 运行区骨架。

用途：

- 存放通过 `rdc-debugger` intake 之后的 `case_id/run_id` 级运行现场
- 承载 case 级 `inputs/captures/`、run 级 `screenshots/`、`artifacts/`、`logs/`、`notes/`
- 承载第二层交付物 `reports/report.md` 与 `reports/visual_report.html`

约束：

- 这里不是共享真相；共享真相仍由同级 `common/` 提供。
- `workspace/` 是 Agent 运行区，不要求用户手工把 `.rdc` 预放到这里。
- 平台包装层中涉及运行区时，应统一把它表述为当前平台根目录下的 `workspace/`。
- 导入后的原始 `.rdc` 只允许落在 `cases/<case_id>/inputs/captures/`，不得落在 `runs/<run_id>/`
- standalone `capture open` 只建立 tools-layer session state，不会创建这里的 `case/run`
- 这里的 `case/run` 只由已通过的 `rdc-debugger` intake 流程初始化
- 模板仓库只保留占位骨架，不提交真实运行产物。
