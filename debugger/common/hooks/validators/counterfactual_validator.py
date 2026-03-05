#!/usr/bin/env python3
"""
反事实验证记录检查器 — Debugger Framework M4 Quality Hooks

检查调试 session 的 evidence 集合中是否存在有效的反事实验证记录。

用法：
  python3 counterfactual_validator.py <session_evidence.yaml>

返回码：
  0 — 反事实验证记录存在且有效
  1 — 缺少有效的反事实验证记录（输出详细原因）
  2 — 文件解析错误
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

try:
    import yaml
except ModuleNotFoundError:
    req = Path(__file__).resolve().parents[1] / "requirements.txt"
    print("错误：缺少依赖 'PyYAML'，无法解析 YAML。")
    print(f"请先安装依赖：python3 -m pip install -r {req}")
    sys.exit(2)

ANSI_RED    = "\033[91m"
ANSI_GREEN  = "\033[92m"
ANSI_YELLOW = "\033[93m"
ANSI_RESET  = "\033[0m"


def _has_nonempty_field(record: dict, key: str) -> bool:
    if key not in record:
        return False
    value = record.get(key)
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def validate_counterfactual(evidence_list: list) -> tuple:
    """
    检查 evidence 列表中是否有合格的反事实验证记录。
    返回 (passed: bool, issues: list[str])
    """
    issues = []

    # 找所有 type: counterfactual_test 的记录
    cf_records = [e for e in evidence_list if isinstance(e, dict) and e.get("type") == "counterfactual_test"]

    if not cf_records:
        issues.append("evidence 列表中不存在任何 type: counterfactual_test 的记录")
        issues.append("必须补充反事实验证：修改假设中的关键变量，观察症状是否消失")
        return False, issues

    # 找 result: passed 的记录
    passed_records = [r for r in cf_records if r.get("result") == "passed"]

    if not passed_records:
        issues.append(f"找到 {len(cf_records)} 条反事实验证记录，但均未通过（result != 'passed'）")
        for r in cf_records:
            rid = r.get("evidence_id", "?")
            result = r.get("result", "?")
            issues.append(f"  - {rid}: result={result}")
        return False, issues

    # 检查通过的记录是否有量化数据
    quality_issues = []
    for r in passed_records:
        rid = r.get("evidence_id", "?")
        # 必须有 before/after 对比数据
        if not (_has_nonempty_field(r, "before_value") or _has_nonempty_field(r, "pixel_before")):
            quality_issues.append(f"  - {rid}: 缺少 before_value 或 pixel_before（需量化对比数据）")
        if not (_has_nonempty_field(r, "after_value") or _has_nonempty_field(r, "pixel_after")):
            quality_issues.append(f"  - {rid}: 缺少 after_value 或 pixel_after（需量化对比数据）")
        # 不得有主观描述替代量化数据
        description = str(r.get("description", ""))
        subjective_keywords = ["看起来", "感觉", "好多了", "seems", "looks better"]
        for kw in subjective_keywords:
            if kw in description:
                quality_issues.append(f"  - {rid}: description 包含主观描述 '{kw}'，必须用量化数值替代")
                break

    if quality_issues:
        issues.append(f"找到 {len(passed_records)} 条通过的反事实验证，但存在质量问题：")
        issues.extend(quality_issues)
        return False, issues

    return True, []


def main():
    if len(sys.argv) < 2:
        print("用法：python3 counterfactual_validator.py <session_evidence.yaml>")
        sys.exit(2)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"{ANSI_RED}错误：文件不存在 — {path}{ANSI_RESET}")
        sys.exit(2)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"{ANSI_RED}错误：YAML 解析失败 — {e}{ANSI_RESET}")
        sys.exit(2)

    # 支持两种格式：直接的 evidence 列表，或包含 evidence 键的对象
    if isinstance(data, list):
        evidence_list = data
    elif isinstance(data, dict):
        evidence_list = data.get("evidence", data.get("evidence_chain", []))
    else:
        print(f"{ANSI_RED}错误：无法识别的文件格式{ANSI_RESET}")
        sys.exit(2)

    print(f"\n{'═'*55}")
    print(f"  Debugger 反事实验证检查器 — {path.name}")
    print(f"  evidence 条目总数：{len(evidence_list)}")
    print(f"{'═'*55}")

    passed, issues = validate_counterfactual(evidence_list)

    if passed:
        cf_ok = [e for e in evidence_list if isinstance(e, dict)
                 and e.get("type") == "counterfactual_test" and e.get("result") == "passed"]
        print(f"\n{ANSI_GREEN}✅ 反事实验证通过 — 找到 {len(cf_ok)} 条有效记录{ANSI_RESET}")
        for r in cf_ok:
            print(f"   - {r.get('evidence_id', '?')}: {r.get('description', '')[:60]}")
        sys.exit(0)
    else:
        print(f"\n{ANSI_RED}❌ 反事实验证不足 — 无法结案{ANSI_RESET}\n")
        for issue in issues:
            print(f"  • {issue}")
        print(f"\n{ANSI_YELLOW}⚠  请补充反事实验证后再提交裁决。{ANSI_RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
