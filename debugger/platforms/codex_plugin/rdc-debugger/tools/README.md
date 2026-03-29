# 平台本地 `tools/` 占位说明

当前目录是平台本地 `tools/` 的最小占位目录，不是正式运行时内容。

使用方式：

1. 选择一个 `debugger/platforms/<platform>/` 模板。
2. 将 RDC-Agent-Tools 根目录整包拷贝到该平台根目录的 `tools/`，覆盖当前目录。
3. 完成覆盖后，运行 `python common/config/validate_binding.py --strict` 确认绑定有效。
4. 确认通过后，再在对应宿主中打开该平台根目录使用。

约束：

- 平台内所有 agent / skill / config 引用工具时，只允许引用当前平台根目录的 `tools/` source payload。
- `tools/` 只表示 source payload；live runtime 由 daemon-owned worker 物化到独立 cache 后再加载。
- 未完成覆盖前，当前平台模板不可用。
- 不为未覆盖状态提供伪完整 placeholder 文件；正式工具真相只来自 RDC-Agent-Tools。
