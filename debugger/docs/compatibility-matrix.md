# Debugger / Tools 兼容矩阵

本文定义 `RDC-Agent-Frameworks/debugger` 与 `RDC-Agent-Tools` 的推荐配对关系。

## 当前推荐配对

| Frameworks/debugger | Tools | 说明 |
|---|---|---|
| 当前主线 | 当前主线（`tool_count` 必须与 `Tools/spec/tool_catalog.json` 一致） | 必须包含 `rd.vfs.ls` / `rd.vfs.cat` / `rd.vfs.tree` / `rd.vfs.resolve`，并把它们解释为导航层 |

## 最低对齐要求

- `tool_catalog.snapshot.json` 的 `tool_count` 必须等于 `Tools/spec/tool_catalog.json`。
- `tool_catalog.snapshot.json` 的关键 public contract 也必须反映当前正式 tool 语义，不能继续保留旧的返回形状或 mock 成功口径。
- snapshot 中必须包含：
  - `rd.vfs.ls`
  - `rd.vfs.cat`
  - `rd.vfs.tree`
  - `rd.vfs.resolve`
- `debugger` 文档中涉及探索面时，应按“只读 VFS + canonical `rd.*` tools”口径编写，不得把 `rd.vfs.*` 写成第二套平台真相。
- `tabular/tsv` 只能按 projection/support surface 描述，不得写成独立能力面或重要度排序结果。
- `platform_adapter.json` 必须保持 `paths.tools_source_root="tools"` 且 `runtime.mode="worker_staged"`；不再支持手工配置绝对路径、live runtime 目录或占位值替换。
- `Tools` 必须同时携带 `rdx.bat`、`binaries/windows/x64/manifest.runtime.json` 与 bundled `Python` 入口 `binaries/windows/x64/python/python.exe`；这是 `debugger` 当前认定的 zero-install runtime 最低边界。
- `MCP` opt-in 必须通过 `tools/rdx.bat --non-interactive mcp` 或等价 `cmd /c` 包装接线，不再把系统 `Python` 当成正式前置条件。
- 当前已验证的配对范围包括 package-local `tools/` + local-first flow，以及 Android remote-only 的 daemon / `MCP` 最小 bootstrap 主链。
- Android remote-only 的正式复核入口优先使用 `tools/scripts/tool_contract_remote_smoke.py --rdc "<sample.rdc>" --transport daemon|mcp`。
- 完整 remote-only 兼容统计以最新 smoke 报告为准，不得继续把旧的固定 pass/blocker 数值写成当前 truth。

## 接线前必跑

```bat
python common/config/validate_binding.py --strict
python debugger/scripts/validate_tool_contract.py --mode source --strict
```
