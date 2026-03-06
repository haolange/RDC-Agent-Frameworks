# RenderDoc/RDC GPU Debug CLI Mode Reference

本文只在用户明确要求 `CLI` 模式时使用。
目的不是让 Agent 自行探索 `CLI`，而是给出一份受约束、可直接依赖的接口说明。

## 使用原则

- `CLI` 模式下，禁止通过 `--help`、枚举命令、随机试跑、观察式试错来发现能力面。
- Agent 只能依赖本文已声明的命令族、状态名、最小链路和读取原则。
- 如果任务需要的能力不在本文覆盖范围内，应停止自行探索，转为：
  - 请求切回 `MCP` 模式，或
  - 请求用户确认平台文档/入口

## 会话最小链路

`CLI` 模式下，允许假定存在一条最小顺序链路：

1. 打开 `.rdc`
2. 建立 session
3. 选择 frame
4. 读取事件列表或状态
5. 在必要时读取 event 级上下文

在当前平台默认实现里，这类动作通常由以下命令族承担：

- `capture open`
- `capture status`
- `call rd.event.get_actions`
- `daemon status`

## 关键状态名

- `capture_file_id`
- `session_id`
- `frame_index`
- `active_event_id`
- `context`

这些值都应被视为短生命周期运行时句柄，不应当作长期稳定主键。

## 输出读取原则

- 优先读取结构化字段，不依赖人类描述性输出推断平台语义。
- 遇到共享响应契约输出时，优先检查：
  - `ok`
  - `error_message`
- 遇到 session 相关输出时，优先抽取：
  - `capture_file_id`
  - `session_id`
  - `active_event_id`

## 何时必须停止

出现以下情况时，停止继续试错：

- 本文未覆盖所需命令族
- 命令输出不能稳定映射为已知状态对象
- 需要通过反复试跑不同命令来猜能力边界
- 需要靠 `--help`、命令枚举、目录穷举来摸清平台能力

这时应改为：

- 切换到 `MCP` 模式并进行 tool discovery，或
- 请求用户提供更明确的 `CLI` 入口信息
