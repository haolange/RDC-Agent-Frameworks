# Debugger Knowledge Skill

## 描述

Debugger Framework 调试知识技能包。当执行任何渲染 Bug 调试任务时自动加载。提供以下知识资源的动态索引：

- **不变量库**：23 个形式化渲染不变量（NaN 传播、精度约束、深度写入规则等）
- **症状分类学**：37 个标准化症状标签及其与不变量的映射
- **触发条件分类学**：GPU 型号 / 驱动版本 / API 的已知问题索引
- **SOP 库**：7 个标准调试流程（含工具链和不变量覆盖声明）

## 加载指令

当执行渲染调试任务时，按以下路径加载知识文件（路径相对于 `debugger/` 根目录）：

```
common/knowledge/spec/invariants/invariant_library.yaml    ← 不变量库（必须加载）
common/knowledge/spec/taxonomy/symptom_taxonomy.yaml       ← 症状分类学（分类阶段加载）
common/knowledge/spec/taxonomy/trigger_taxonomy.yaml       ← 触发条件分类学（设备分析阶段加载）
common/knowledge/spec/skills/sop_library.yaml              ← SOP 库（选定调试流程后加载）
```

## 关键知识结构

### 不变量（invariant_library.yaml）

每条不变量包含：
- `id`：唯一标识（如 `I-NAN-01`）
- `symptom_tags`：关联症状标签
- `typical_root_causes`：常见根因
- `fix_patterns`：修复模式
- `linked_sop`：对应 SOP ID
- `detection_tools`：推荐使用的 RenderDoc 工具

### 症状标签（symptom_taxonomy.yaml）

映射关系：`symptom_tag → likely_invariants → priority_order`

查询示例（Python 一行）：
```python
next(s for s in yaml.safe_load(open('common/knowledge/spec/taxonomy/symptom_taxonomy.yaml'))['symptoms'] if s['tag'] == 'white_spot')
```

### SOP（sop_library.yaml）

每条 SOP 包含：
- `trigger_conditions`：何时激活该 SOP
- `target_invariants`：覆盖哪些不变量
- `tool_chain`：具体工具调用序列
- `termination`：完成标准（阶段/流程的退出条件）

## 项目知识扩展

若项目存在 Plugin 文件，额外加载：
```
common/project_plugin/<project_name>.yaml   ← 项目特定不变量和材质模块信息
```

## 历史案例

已记录的调试案例位于：
```
common/knowledge/templates/bugcards/    ← BugCard 知识卡（快速索引）
common/knowledge/templates/bugfulls/    ← BugFull 完整报告（详细参考）
common/knowledge/traces/action_chains/  ← Action Chain 调试过程记录
```

实际调试过程中沉淀的知识库（可选但推荐）位于：
```
common/knowledge/library/               ← BugCard 入库与 BugFull 输出目录
```
