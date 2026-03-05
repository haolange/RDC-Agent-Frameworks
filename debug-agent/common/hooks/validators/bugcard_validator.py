#!/usr/bin/env python3
"""
BugCard 完整性验证器 — AIRD Framework M4 Quality Hooks

用法：
  python3 bugcard_validator.py <bugcard.yaml>
  python3 bugcard_validator.py <bugcard.yaml> --strict

返回码：
  0 — 验证通过
  1 — 验证失败（输出缺失/不合规字段列表）
  2 — 文件解析错误
"""

import sys
import re
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

# ── 必填字段规则 ────────────────────────────────────────────────
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "bugcard_required_fields.yaml"

ANSI_RED   = "\033[91m"
ANSI_GREEN = "\033[92m"
ANSI_YELLOW = "\033[93m"
ANSI_RESET = "\033[0m"

ALLOWED_SHADER_STAGES = {"VS", "PS", "CS", "GS", "HS", "DS", "MS", "TS"}


def _load_yaml(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def _load_schema() -> dict:
    schema = _load_yaml(SCHEMA_PATH)
    return schema if isinstance(schema, dict) else {}


def _load_reference_sets():
    """
    加载跨文件引用集合（用于 --strict 校验）。
    返回 dict[str, set[str]]
    """
    root = Path(__file__).resolve().parents[3]  # debug-agent/
    symptom = _load_yaml(root / "common" / "knowledge" / "spec" / "taxonomy" / "symptom_taxonomy.yaml") or {}
    trigger = _load_yaml(root / "common" / "knowledge" / "spec" / "taxonomy" / "trigger_taxonomy.yaml") or {}
    inv = _load_yaml(root / "common" / "knowledge" / "spec" / "invariants" / "invariant_library.yaml") or {}
    sop = _load_yaml(root / "common" / "knowledge" / "spec" / "skills" / "sop_library.yaml") or {}

    symptoms = {s.get("tag") for s in (symptom.get("symptoms") or []) if isinstance(s, dict)}
    triggers = {t.get("tag") for t in (trigger.get("triggers") or []) if isinstance(t, dict)}
    invariants = {i.get("id") for i in (inv.get("invariants") or []) if isinstance(i, dict)}
    sops = {s.get("id") for s in (sop.get("sops") or []) if isinstance(s, dict)}

    return {
        "symptom_tags": {x for x in symptoms if x},
        "trigger_tags": {x for x in triggers if x},
        "violated_invariants": {x for x in invariants if x},
        "recommended_sop": {x for x in sops if x},
    }


def _eval_condition(condition: str, data: dict) -> tuple[bool, str | None]:
    """
    Evaluate a very small condition language used by bugcard_required_fields.yaml.
    Currently supports:
      - "<field> == true"
      - "<field> == false"
    Returns (ok, error_message).
    """
    cond = str(condition or "").strip()
    m = re.match(r"^([A-Za-z0-9_]+)\s*==\s*(true|false)$", cond)
    if not m:
        return False, f"不支持的 condition 表达式：{cond!r}"
    field, lit = m.group(1), m.group(2)
    expected = lit == "true"
    actual = data.get(field)
    if not isinstance(actual, bool):
        return False, f"condition 依赖字段 '{field}' 必须为 boolean（当前类型：{type(actual)}）"
    return actual is expected, None


def _is_nonempty_str(x) -> bool:
    return isinstance(x, str) and bool(x.strip())


def _check_required_fields_from_schema(schema: dict, data: dict) -> list[str]:
    errors: list[str] = []
    required = schema.get("required_fields", [])
    if not isinstance(required, list) or not required:
        return [f"[schema] 无法加载必填字段清单：{SCHEMA_PATH}"]

    for item in required:
        if not isinstance(item, dict):
            errors.append("[schema] required_fields 中存在非对象条目")
            continue
        field = str(item.get("field", "")).strip()
        if not field:
            errors.append("[schema] required_fields 中存在缺少 field 的条目")
            continue

        cond = item.get("condition")
        if cond:
            cond_ok, cond_err = _eval_condition(str(cond), data)
            if cond_err:
                errors.append(f"[schema] {field}: {cond_err}")
                continue
            if not cond_ok:
                continue  # condition not met -> not required

        if field not in data or data[field] is None:
            errors.append(f"[缺失] 必填字段 '{field}' 不存在或为空")

    return errors


def _validate_field_against_rule(field: str, rule: dict, data: dict) -> list[str]:
    errors: list[str] = []
    if field not in data or data[field] is None:
        return errors  # presence handled elsewhere

    val = data.get(field)
    expected_type = str(rule.get("type", "")).strip().lower()

    if expected_type == "string":
        if not isinstance(val, str):
            return [f"[类型] '{field}' 必须为 string"]
        if "min_length" in rule and len(val) < int(rule["min_length"]):
            errors.append(f"[长度] {field} 过短（{len(val)} 字），至少需要 {int(rule['min_length'])} 字")
        if "max_length" in rule and len(val) > int(rule["max_length"]):
            errors.append(f"[长度] {field} 过长（{len(val)} 字），最多 {int(rule['max_length'])} 字")
        pattern = rule.get("pattern")
        if pattern:
            try:
                rx = re.compile(str(pattern))
            except re.error as exc:
                errors.append(f"[schema] {field}: pattern 正则非法：{exc}")
            else:
                if not rx.match(val):
                    errors.append(f"[格式] {field} '{val}' 不符合 pattern {pattern!r}")
        disallow = rule.get("disallow_patterns")
        if isinstance(disallow, list):
            for token in disallow:
                if token and str(token) in val:
                    errors.append(f"[质量] {field} 包含禁止表述 {str(token)!r}")
                    break

    elif expected_type == "boolean":
        if not isinstance(val, bool):
            return [f"[类型] {field} 必须为 boolean（true/false）"]
        if "must_be" in rule and val is not bool(rule.get("must_be")):
            errors.append(f"[签署] {field} 必须为 {bool(rule.get('must_be'))}")

    elif expected_type == "list":
        if not isinstance(val, list):
            return [f"[类型] '{field}' 必须是列表"]
        min_items = rule.get("min_items")
        if min_items is not None and len(val) < int(min_items):
            errors.append(f"[类型] '{field}' 必须是非空列表（至少 {int(min_items)} 项）")
        # For required list fields in BugCard, enforce string elements.
        if field in {"symptom_tags", "trigger_tags", "violated_invariants"}:
            if any((not _is_nonempty_str(x)) for x in val):
                errors.append(f"[类型] '{field}' 列表元素必须为非空字符串")

    elif expected_type == "object":
        if not isinstance(val, dict):
            return [f"[类型] {field} 必须为对象"]
        sub = rule.get("required_subfields")
        if isinstance(sub, list):
            for sf in sub:
                sfs = str(sf).strip()
                if not sfs:
                    continue
                if sfs not in val or val.get(sfs) in (None, "", [], {}):
                    errors.append(f"[缺失] {field}.{sfs} 不存在或为空")

    else:
        errors.append(f"[schema] {field}: 未支持的 type={expected_type!r}")

    return errors


def validate_bugcard(data: dict, strict: bool = False) -> list:
    """验证 BugCard 数据，返回错误列表（空列表表示通过）。"""
    errors = []

    schema = _load_schema()

    # 1. 必填字段存在性检查（以 schema 为唯一真值）
    errors.extend(_check_required_fields_from_schema(schema, data))

    if errors:
        return errors  # 字段缺失时不继续深度检查

    # 2. 深度字段校验（以 schema 为准，覆盖 pattern/min/max/disallow/condition 等）
    required = schema.get("required_fields", [])
    if isinstance(required, list):
        for rule in required:
            if not isinstance(rule, dict):
                continue
            field = str(rule.get("field", "")).strip()
            if not field:
                continue
            cond = rule.get("condition")
            if cond:
                cond_ok, cond_err = _eval_condition(str(cond), data)
                if cond_err:
                    errors.append(f"[schema] {field}: {cond_err}")
                    continue
                if not cond_ok:
                    continue
            errors.extend(_validate_field_against_rule(field, rule, data))
    else:
        errors.append(f"[schema] required_fields 解析失败：{SCHEMA_PATH}")

    # 3. 补充一致性检查（保持历史行为）
    fp = data.get("fingerprint")
    if isinstance(fp, dict):
        stage = str(fp.get("shader_stage", "")).strip()
        if stage and stage not in ALLOWED_SHADER_STAGES:
            errors.append(f"[格式] fingerprint.shader_stage '{stage}' 非法，允许值：{sorted(ALLOWED_SHADER_STAGES)}")

    # 10. --strict：跨文件引用一致性检查
    if strict and not errors:
        ref = _load_reference_sets()

        for tag in data.get("symptom_tags", []):
            if tag not in ref["symptom_tags"]:
                errors.append(f"[引用] symptom_tags 中包含未知 tag：'{tag}'（不在 symptom_taxonomy.yaml）")

        for tag in data.get("trigger_tags", []):
            if tag not in ref["trigger_tags"]:
                errors.append(f"[引用] trigger_tags 中包含未知 tag：'{tag}'（不在 trigger_taxonomy.yaml）")

        for inv in data.get("violated_invariants", []):
            if inv not in ref["violated_invariants"]:
                errors.append(f"[引用] violated_invariants 中包含未知 id：'{inv}'（不在 invariant_library.yaml）")

        sop = str(data.get("recommended_sop", "")).strip()
        if sop and sop not in ref["recommended_sop"]:
            errors.append(f"[引用] recommended_sop '{sop}' 不存在于 sop_library.yaml")

    return errors


def main():
    strict = "--strict" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args:
        print("用法：python3 bugcard_validator.py <bugcard.yaml> [--strict]")
        sys.exit(2)

    path = Path(args[0])
    if not path.exists():
        print(f"{ANSI_RED}错误：文件不存在 — {path}{ANSI_RESET}")
        sys.exit(2)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"{ANSI_RED}错误：YAML 解析失败 — {e}{ANSI_RESET}")
        sys.exit(2)

    if not isinstance(data, dict):
        print(f"{ANSI_RED}错误：BugCard 必须是 YAML 对象，当前类型：{type(data)}{ANSI_RESET}")
        sys.exit(2)

    errors = validate_bugcard(data, strict=strict)

    print(f"\n{'═'*55}")
    print(f"  AIRD BugCard 验证器 — {path.name}")
    print(f"{'═'*55}")

    if not errors:
        print(f"\n{ANSI_GREEN}✅ 验证通过 — BugCard 符合所有必填字段规范{ANSI_RESET}")
        print(f"   bugcard_id : {data.get('bugcard_id')}")
        print(f"   title      : {data.get('title', '')[:60]}")
        print(f"   skeptic    : {'✅ 已签署' if data.get('skeptic_signed') else '❌ 未签署'}")
        sys.exit(0)
    else:
        print(f"\n{ANSI_RED}❌ 验证失败 — 发现 {len(errors)} 个问题：{ANSI_RESET}\n")
        for i, err in enumerate(errors, 1):
            print(f"  {i:2d}. {err}")
        print(f"\n{ANSI_YELLOW}⚠  BugCard 不得入库，请修复以上问题后重新验证。{ANSI_RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
