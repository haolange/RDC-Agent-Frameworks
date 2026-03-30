# Codex Plugin Wrapper（外层包装目录）

当前目录是 Codex plugin 的外层包装目录，不是可直接安装或运行的 plugin root。

真正符合 Codex plugin 规范的根目录位于同级 `rdc-debugger/`。

## 目录职责

- `rdc-debugger/`：唯一可安装的 Codex plugin bundle。
- `references/personal-marketplace.sample.json`：个人 marketplace 示例，目标位置是 `~/.agents/plugins/marketplace.json`。
- 当前外层目录只负责包装说明、安装链路与 marketplace 示例；运行时规则仍以 `rdc-debugger/` 与共享 `debugger/common/` 为准。

## 安装链路

1. 将仓库根目录 `debugger/common/` 整体拷贝到 `rdc-debugger/common/`。
2. 将 `RDC-Agent-Tools` 根目录整包拷贝到 `rdc-debugger/tools/`。
3. 在 `rdc-debugger/` 根目录运行 `python common/config/validate_binding.py --strict`。
4. 将 `rdc-debugger/` 同步到 `~/.agents/plugins/rdc-debugger/`。
5. 将 `references/personal-marketplace.sample.json` 合并到 `~/.agents/plugins/marketplace.json`。
6. 在 Codex 中打开 `/plugins`，安装或刷新 `rdc-debugger`。
7. 安装后在新线程中使用 `@RDC Debugger` 或 `$rdc-debugger` 进入框架。

## 约束

- 不要把当前外层目录当作 plugin root。
- `common/` 与 `tools/` 仍然是用户手动覆盖的 package-local payload，不会随插件自动内置。
- Codex 本地插件安装后实际加载的是 cache 副本；每次重新覆盖 `common/` 或 `tools/` 后，都必须重新同步 `~/.agents/plugins/rdc-debugger/`，然后在 `/plugins` 中刷新或重装。
- 当前插件路径按 `no-hooks` 处理：插件只提供入口与安装面，不把宿主插件接口误写成严格 lifecycle hooks enforcement。
