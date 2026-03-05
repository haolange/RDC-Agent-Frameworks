# Debugger Framework · Project Plugin 接口规范

Project Plugin 是 Debugger 框架的项目级知识注入接口。它让 Agent 在执行通用调试流程的同时，具备对特定项目的深度感知能力（材质结构、引擎资源路径、项目特有不变量）。

---

## 设计原则

> **框架只规定接口，不规定内容。**
>
> PLUGIN_SPEC 定义了 Plugin 文件必须包含哪些字段、字段的含义和格式约束。
> 但字段的具体内容（材质模块的名称、已知问题的描述）完全由项目团队决定。
> 框架不预设任何关于项目内部结构的假设。

---

## Plugin 文件格式

Plugin 文件为 YAML 格式，存放路径建议：`common/project_plugin/<project_name>.yaml`

### 必填字段

```yaml
# ── 项目基本信息 ──────────────────────────────────────────────
project_name: string          # 项目名称（英文，无空格）
engine: string                # 引擎及版本，如 "UnrealEngine 5.3" / "Unity 2022.3"
plugin_version: string        # Plugin 版本，如 "1.0.0"
debugger_framework_version: string  # 兼容的 Debugger 版本，如 ">=2.0"
```

### 可选字段（按需填写，非必填但强烈推荐）

```yaml
# ── 目标平台 ─────────────────────────────────────────────────
target_platforms:             # 项目支持的 GPU 平台列表
  - string                    # 格式与 trigger_taxonomy.yaml 中的 trigger_tags 一致
# 示例：[Android_Adreno, Android_Mali, iOS_Apple, PC_NVIDIA, PC_AMD]

# ── 材质模块（Material Blocks） ───────────────────────────────
# 将项目的 Shader 结构分解为可被 Agent 引用的逻辑单元
material_blocks:
  - block_id: string          # 模块唯一标识（大写+下划线），如 LIGHTING_BLOCK
    description: string       # 一句话描述模块用途
    hlsl_fingerprint: string  # 代表该模块的 HLSL 代码片段（用于 Shader 搜索）
    engine_asset_path: string # 引擎中的资源路径（用于 project_plugin (local-only) 工具）
    shader_files:             # 相关 Shader 文件列表（相对路径）
      - string
    parameters:               # 该模块的关键 Shader 参数名
      - string
    known_issues:             # 该模块的已知问题
      - invariant: string     # 关联的不变量 ID（来自 invariant_library.yaml）
        trigger: string       # 触发条件描述
        note: string          # 简短说明

# ── 项目特有不变量 ─────────────────────────────────────────────
# 不在 common/knowledge/spec/invariants/ 中，但项目团队认为必须维持的约束
project_invariants:
  - id: string                # 格式：P-<类别>-<序号>，如 P-METAL-01
    description: string       # 不变量描述
    rationale: string         # 为何需要这个约束（美术/性能/平台要求等）
    detection_hint: string    # 如何检测该不变量是否被违反

# ── 资源映射 ─────────────────────────────────────────────────
# 将运行时 resource_id 映射到项目资源名称（加速 Agent 定位问题）
resource_mapping:
  - resource_id_pattern: string  # 正则或前缀，如 "^tex_hair_.*"
    asset_category: string    # 资源类别，如 "角色头发贴图"
    asset_path_prefix: string # 引擎资源路径前缀

# ── 渲染管线特殊配置 ──────────────────────────────────────────
render_pipeline_notes:
  - pass_name: string         # RenderPass 名称
    description: string       # 说明该 Pass 的用途（Agent 定位问题时参考）
    known_issues:
      - string

# ── 联系信息 ─────────────────────────────────────────────────
maintainer: string            # Plugin 维护者（姓名或团队名）
last_updated: string          # ISO 日期，如 "2026-02-27"
```

---

## Agent 使用 Plugin 的方式

### 动态加载声明

Agent 在 prompt 中声明加载 Plugin 文件：
```
# 项目 Plugin（运行时加载）：
# - project_plugin/<project_name>.yaml
```

### `project_plugin`（local-only）

`project_plugin` 不是 MCP 工具；它是一份**本地文件接口约定**：Agent 通过读取
`common/project_plugin/<project_name>.yaml` 获得项目上下文（材质模块、资源映射、
项目不变量），用于更快定位与归因。

使用方式（概念步骤）：

1. 读取 `common/project_plugin/<project_name>.yaml`
2. 按 `block_id` 在 `material_blocks` 中检索模块信息（如 `hlsl_fingerprint` / `engine_asset_path` / `shader_files`）
3. 按 `resource_id_pattern` 在 `resource_mapping` 中匹配运行时 `resource_id`（将其翻译为资产类别/路径前缀）

示例（伪查询）：
```
read common/project_plugin/<project_name>.yaml
  -> material_blocks[block_id == "LIGHTING_BLOCK"]
  -> resource_mapping[resource_id_pattern matches "tex_hair_base_d"]
```

### Triage Agent 增益

当 Plugin 已加载时，Triage Agent 可以额外：
1. 将症状定位到具体的 `material_blocks`（而非泛化的 HLSL 文件）
2. 将 `project_invariants` 加入候选违反不变量列表

---

## Plugin 版本管理规范

| 版本变更类型 | 版本号规则 |
|------------|----------|
| 新增材质模块 / 项目不变量 | 次版本号 +1（如 1.0 → 1.1） |
| 修改已有字段语义 | 主版本号 +1（如 1.x → 2.0） |
| 修正 hlsl_fingerprint / known_issues 描述 | 补丁号 +1（如 1.1.0 → 1.1.1） |

每次更新必须更新 `last_updated` 字段。

---

## 与框架其他组件的关系

| 组件 | Plugin 的贡献 |
|------|-------------|
| `Triage Agent` | 用 material_blocks 的 hlsl_fingerprint 加速症状定位 |
| `Shader & IR Agent` | 用 engine_asset_path 直接定位 Shader 源文件 |
| `Pixel Forensics` | 用 resource_mapping 将 resource_id 翻译为人类可读的资源名称 |
| `Curator Agent` | 在 BugCard 中引用 block_id，使知识卡片具备项目上下文 |
