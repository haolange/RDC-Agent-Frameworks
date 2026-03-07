# RenderDoc/RDC GPU Debug
## Invariant-Driven Rendering Debugger

`RenderDoc/RDC GPU Debug` 是构建在 RenderDoc/RDC 平台能力之上的多 Agent GPU Debug framework。

它的主驱动不是“多试几次工具”，而是：

- 用不变量把现象转成可裁决约束
- 用证据链把猜测推进到可验证结论
- 用反事实验证阻止“看起来像”的误判
- 用 BugCard / BugFull / Action Chain 沉淀可复用知识
- 用 `causal_anchor` 把“首次可见”与“首次引入”分开，禁止靠 screen-like 观察直接做根因裁决

## 当前成熟度

- `debugger/` 已具备完整框架基础，可作为当前仓库的主入口。
- `analyzer/` 与 `optimizer/` 仍是骨架，不应被误读为同等成熟度的 framework。

## 阅读顺序

1. `common/AGENT_CORE.md`
2. `docs/platform-capability-model.md`
3. `docs/runtime-coordination-model.md`
4. `docs/platform-capability-matrix.md`
5. `docs/model-routing.md`
6. `docs/cli-mode-reference.md`
7. `common/agents/*.md`
8. `common/knowledge/spec/*`

## 平台完成标准

- `code-buddy/`：满配基线，保持 `plugin + agents + hooks + skills + MCP`
- `claude-code/`：真实的 Claude Code 适配，具备 `agents + skill + hooks config + MCP config`
- `copilot-cli/`：真实的 CLI plugin 适配，具备 `plugin + agents + hooks + skills + MCP`
- `copilot-ide/`：IDE custom agents 适配，具备 `.github/agents + MCP + preferred model + 边界说明`
- `claude-work/`、`manus/`：可信降级适配，不伪装成满配实现

## 平台接入原则

框架层只依赖这些第一性平台能力：

- 规范化的 `rd.*` tool 能力面
- 共享响应契约
- `.rdc -> capture handle -> session handle -> frame/event context` 的最小状态链路
- `context`、daemon、artifact、failure surface

具体实现路径、catalog 位置、`MCP`/`CLI` 启动入口属于 adapter/config 层，集中定义在：

- `common/config/platform_adapter.json`
- `common/config/platform_capabilities.json`
- `common/config/model_routing.json`

其中：

- `platform_capabilities.json` 同时记录宿主能力与 runtime 合同
- `docs/runtime-coordination-model.md` 记录多 Agent 协作时的 live runtime 约束、`runtime_baton` 与 remote rehydrate 规则

## `MCP` 与 `CLI`

### `MCP` 模式

- 允许 tool discovery。
- 适合上层 Agent 动态编排。

### `CLI` 模式

- 不允许 discovery-by-trial-and-error。
- 用户明确要求 `CLI` 模式时，先读 `docs/cli-mode-reference.md`。

## 维护入口

### 校验 tool contract

```bash
python debugger/scripts/validate_tool_contract.py --strict
```

### 校验平台布局

```bash
python debugger/scripts/validate_platform_layout.py --strict
```

### 同步平台 prompt 镜像

```bash
python debugger/scripts/sync_platform_agents.py
```



