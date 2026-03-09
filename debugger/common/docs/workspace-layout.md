# Workspace Layout

本文定义 Debugger 框架的运行时 `workspace/` 合同。

Agent 的目标始终是使用 RenderDoc/RDC platform tools 调试 GPU 渲染问题；`workspace/` 只负责承载这次调试的运行现场和对外交付，不负责保存 framework 真相。

## 1. 基本分层

- `common/`：唯一共享真相
  - agents
  - config
  - docs
  - hooks
  - knowledge/spec
  - knowledge/library
- `workspace/`：运行区
  - case/run 工作现场
  - 第二层图文报告与 HTML summary

硬规则：

- 不把运行期截图、capture、日志直接写回 `common/`。
- 不把共享 spec、agent 职责、平台 config 写进 `workspace/`。
- 第二层 deliverables 只能派生自第一层证据，不得反向改写第一层真相。

## 2. 平台本地相对路径

用户会把顶层 `debugger/common/` 拷贝到目标平台模板根目录的 `common/` 后再使用。运行时 `workspace/` 不是仓库根目录的一部分，而是每个平台模板根目录预生成的 sibling 占位骨架。

因此，shared prompt / skill / docs 中引用运行区时，统一使用：

- `../workspace`

含义：

- 平台模板里：`platform-root/common/../workspace`

它始终解析到当前平台根目录下、与 `common/` 同级的 `workspace/`。

## 3. case/run 模型

目录约定：

```text
workspace/
  cases/
    <case_id>/
      case.yaml
      runs/
        <run_id>/
          run.yaml
          artifacts/
          logs/
          notes/
          captures/
          screenshots/
          reports/
```

语义：

- `case_id`：需求线程/问题实例
- `run_id`：某一次调试轮次；承担 debug version

最小规则：

- 同一 case 只允许一个 `current_run`
- `reports/` 只放 `report.md` 与 `visual_report.html`
- 图片默认复用 `screenshots/`
- 第一层 gate artifacts 不复制到 `workspace/`，只在 `run.yaml` 中记录引用

## 4. 写权限边界

### 第一层：Curator + Knowledge

可直接维护：

- `common/knowledge/library/bugcards/`
- `common/knowledge/library/bugfull/`
- `common/knowledge/library/sessions/`
- `common/knowledge/library/bugcard_index.yaml`
- `common/knowledge/library/cross_device_fingerprint_graph.yaml`
- `common/knowledge/proposals/`

不得直接改写：

- `common/agents/`
- `common/config/`
- `common/knowledge/spec/`

### 第二层：Stakeholder-facing Report

可直接维护：

- `../workspace/cases/<case_id>/runs/<run_id>/reports/report.md`
- `../workspace/cases/<case_id>/runs/<run_id>/reports/visual_report.html`
- `../workspace/cases/<case_id>/runs/<run_id>/screenshots/`
- `../workspace/cases/<case_id>/runs/<run_id>/notes/`
- `../workspace/cases/<case_id>/runs/<run_id>/artifacts/`
- `../workspace/cases/<case_id>/runs/<run_id>/logs/`
- `../workspace/cases/<case_id>/runs/<run_id>/captures/`

第二层额外规则：

- derived deliverables，不是 source of truth
- 不得创造第一层不存在的新事实
- 不得为了展示效果反写 `BugFull`、`BugCard`、session artifacts
