# 平台本地 `common/` 占位说明

当前目录是平台本地 `common/` 的最小占位目录，不是正式运行时内容。

使用方式：

1. 选择一个 `debugger/platforms/<platform>/` 模板。
2. 将仓库根目录 `debugger/common/` 整体拷贝到该平台根目录的 `common/`，覆盖当前目录。
3. 完成覆盖后，再在对应宿主中打开该平台根目录使用。

约束：

- 平台内所有 skill、hooks、agents、config 只允许引用当前平台根目录的 `common/`。
- 平台内运行时工作区固定为当前平台根目录下、与 `common/` 和 `tools/` 并列的 `workspace/`。
- 未完成覆盖前，当前平台模板不可用。
- 不为未覆盖状态提供伪完整 placeholder 文件；正式共享正文只来自顶层 `debugger/common/`。
