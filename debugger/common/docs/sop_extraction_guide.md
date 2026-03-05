# SOP 提取指南：从 Action Chain 到 SOP 草稿

本文档说明如何从已记录的 Action Chain（`.jsonl` 文件）半自动提取 SOP 草稿，并通过人工审核将其合并到 `sop_library.yaml`。

---

## 提取流程概览

```
Action Chains (.jsonl)
       │
       ▼
Step 1: 按不变量聚类
       │
       ▼
Step 2: 提取共同工具调用序列
       │
       ▼
Step 3: 生成 SOP 草稿（YAML）
       │
       ▼
Step 4: 人工审核（添加终止条件 / 补充反事实规范）
       │
       ▼
Step 5: 合并到 sop_library.yaml
```

---

## Step 1：按不变量聚类

从 Action Chain 文件中筛选出 `outcome.root_cause_invariant` 相同的 session：

```python
import json
from collections import defaultdict
from pathlib import Path

def cluster_by_invariant(chains_dir: str) -> dict:
    clusters = defaultdict(list)
    for f in Path(chains_dir).glob("*.jsonl"):
        for line in open(f):
            record = json.loads(line)
            invariant = record.get("outcome", {}).get("root_cause_invariant")
            if invariant:
                clusters[invariant].append(record)
    return clusters

# 使用示例
clusters = cluster_by_invariant("common/knowledge/traces/action_chains/")
# clusters["I-PREC-01"] → 所有因精度问题导致 Bug 的 session 列表
```

**聚类阈值：** 至少 **3 个** 相同不变量的 session 才启动 SOP 提取（样本不足时结论不可靠）。

---

## Step 2：提取共同工具调用序列

在同一聚类中，找出在 **≥ 2/3 的 session** 中都出现的工具调用（按顺序）：

```python
def extract_common_tool_chain(sessions: list, threshold: float = 0.67) -> list:
    """
    提取在 threshold 比例以上 session 中都出现的工具调用序列。
    返回有序的工具列表，可直接作为 SOP tool_chain 候选。
    """
    tool_sequences = []
    for session in sessions:
        tools = [
            step["tool"]
            for step in session.get("steps", [])
            if step.get("action_type") == "tool_call" and step.get("tool")
        ]
        tool_sequences.append(tools)
    
    # 找公共子序列（基于频率统计）
    from collections import Counter
    all_tools = [tool for seq in tool_sequences for tool in set(seq)]
    tool_counts = Counter(all_tools)
    min_count = int(len(sessions) * threshold)
    
    common_tools = {t for t, c in tool_counts.items() if c >= min_count}
    
    # 保持第一个 session 中的工具顺序作为模板
    template_seq = tool_sequences[0] if tool_sequences else []
    return [t for t in template_seq if t in common_tools]
```

---

## Step 3：生成 SOP 草稿

将提取的工具链转换为 `sop_library.yaml` 格式的草稿：

```python
def generate_sop_draft(
    invariant_id: str,
    common_tools: list,
    sessions: list,
    sop_id: str
) -> dict:
    """生成 SOP 草稿（需人工补充终止条件和 counterfactual_spec）。"""
    
    # 从 session 中收集 symptom_tags 和 trigger_tags
    all_symptom_tags = set()
    all_trigger_tags = set()
    for s in sessions:
        triage = s.get("triage_result", {})
        all_symptom_tags.update(triage.get("symptom_tags", []))
        all_trigger_tags.update(triage.get("trigger_tags", []))
    
    # 按阶段分组工具
    stages = []
    for i, tool in enumerate(common_tools, 1):
        stages.append({
            "stage_id": i,
            "objective": f"[待人工填写：第 {i} 阶段目标]",
            "tools": [tool],
            "termination": "[待人工填写：何时进入下一阶段]",
            "output_artifacts": [f"[待人工填写：stage_{i}_output]"]
        })
    
    return {
        "id": sop_id,
        "status": "DRAFT_AUTO_EXTRACTED",  # 人工审核后改为 ACTIVE
        "source_sessions": len(sessions),
        "target_invariants": [invariant_id],
        "trigger_conditions": {
            "symptom_tags": list(all_symptom_tags),
            "trigger_tags": list(all_trigger_tags)
        },
        "tool_chain": stages,
        "output_requirements": {
            "mandatory": ["[待人工填写]"],
        },
        "counterfactual_spec": {
            "method": "[待人工填写：反事实验证方法]",
            "success_criterion": "[待人工填写：量化成功标准]"
        },
        "human_review_required": True,
        "auto_extraction_date": "2026-02-27"
    }
```

---

## Step 4：人工审核检查清单

生成的 SOP 草稿状态为 `DRAFT_AUTO_EXTRACTED`，**人工审核者必须完成以下工作：**

```
□ 1. 填写每个 stage 的 objective（调查目的）
□ 2. 填写每个 stage 的 termination（进入下一阶段的条件）
□ 3. 填写每个 stage 的 output_artifacts（必须产出的内容）
□ 4. 填写 output_requirements.mandatory（BugCard 入库前的最终产出要求）
□ 5. 填写 counterfactual_spec.method 和 success_criterion（量化验证标准）
□ 6. 检查 tool_chain 顺序是否符合实际调试逻辑（自动提取可能有顺序错误）
□ 7. 将 status 从 DRAFT_AUTO_EXTRACTED 改为 ACTIVE
□ 8. 将 human_review_required 改为 false
□ 9. 将 SOP 合并到 sop_library.yaml 并更新版本号
```

---

## Step 5：合并到 sop_library.yaml

```python
import yaml

def merge_sop_draft(sop_draft: dict, sop_library_path: str):
    """将审核通过的 SOP 草稿合并到 sop_library.yaml。"""
    with open(sop_library_path, "r") as f:
        library = yaml.safe_load(f)
    
    # 检查是否已存在相同 ID
    existing_ids = {s["id"] for s in library.get("sops", [])}
    if sop_draft["id"] in existing_ids:
        raise ValueError(f"SOP ID {sop_draft['id']} 已存在，请先手动处理冲突")
    
    library["sops"].append(sop_draft)
    
    with open(sop_library_path, "w") as f:
        yaml.dump(library, f, allow_unicode=True, sort_keys=False)
    
    print(f"✅ SOP {sop_draft['id']} 已合并到 {sop_library_path}")
```

---

## SOP 提取质量指标

提取完成后，计算以下指标评估 SOP 质量：

| 指标 | 计算方式 | 健康阈值 |
|------|---------|---------|
| 工具链覆盖率 | 提取的工具 / 所有 session 工具的并集 | ≥ 0.7 |
| 顺序一致性 | Kendall-τ 相关系数（各 session 工具顺序的一致性） | ≥ 0.6 |
| 样本量 | 用于提取的 session 数 | ≥ 3 |
| SOP 遵循度均值 | `outcome.sop_adherence_score` 的均值 | ≥ 0.75 |

---

## 相关文件

- `action_chain_schema.yaml` — Action Chain 记录格式定义
- `common/knowledge/traces/action_chains/` — 已记录的 Action Chain 文件目录
- `common/knowledge/spec/skills/sop_library.yaml` — SOP 知识库（合并目标）
