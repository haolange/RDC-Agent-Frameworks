# Workspace Cases Placeholder

当前目录用于承载运行时 case。

目录约定：

```text
cases/
  <case_id>/
    case.yaml
    inputs/
      captures/
        manifest.yaml
        <capture_id>.rdc
    runs/
      <run_id>/
        run.yaml
        capture_refs.yaml
        artifacts/
        logs/
        notes/
        screenshots/
        reports/
```

规则：

- `.rdc` 是创建 case 的硬前置条件；未提供 capture 时不得初始化 case/run
- `case_id` 是问题实例/需求线程的稳定标识。
- `run_id` 承担 debug version。
- 原始 `.rdc` 只允许落在 `inputs/captures/`；run 只保留 capture 引用与派生产物。
- 第一层 session artifacts 仍写入同级 `common/knowledge/library/sessions/`；`workspace/` 不复制 gate 真相。
