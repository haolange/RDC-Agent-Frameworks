#!/usr/bin/env python3
"""
Skeptic 签署状态检查器 — Debugger Framework M4 Quality Hooks

检查 Skeptic Agent 是否已对当前假设或 BugCard 完成签署，
且所有质疑项均已被回应（status: addressed）。

用法：
  python3 skeptic_signoff_checker.py <skeptic_output.yaml>
  python3 skeptic_signoff_checker.py <skeptic_output.yaml> --mode bugcard

返回码：
  0 — 签署完整，可以继续
  1 — 签署不完整（输出未解决的质疑项）
  2 — 文件解析错误
"""

from __future__ import annotations

import argparse
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
ANSI_CYAN   = "\033[96m"
ANSI_RESET  = "\033[0m"

FIVE_BLADES = [
    "刀1: 相关性刀",
    "刀2: 覆盖性刀",
    "刀3: 反事实刀",
    "刀4: 工具证据刀",
    "刀5: 替代假设刀",
]


def _is_nonempty_str(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _fmt_loc(i: int | None) -> str:
    return f"[record#{i}] " if i is not None else ""


def _require_fields(obj: dict, fields: list[str], prefix: str) -> list[str]:
    issues: list[str] = []
    for f in fields:
        if f not in obj:
            issues.append(f"{prefix}缺失字段: {f}")
    return issues


def _validate_blade_review(blade_review, prefix: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(blade_review, list) or not blade_review:
        return [f"{prefix}blade_review 必须是非空列表"]

    reviewed_blades: list[str] = []
    for idx, item in enumerate(blade_review, start=1):
        if not isinstance(item, dict):
            issues.append(f"{prefix}blade_review[{idx}] 必须为对象")
            continue
        for f in ("blade", "result", "note"):
            if f not in item:
                issues.append(f"{prefix}blade_review[{idx}] 缺失字段: {f}")
        blade = item.get("blade", "")
        if isinstance(blade, str):
            reviewed_blades.append(blade)
        result = item.get("result")
        if result not in ("pass", "fail"):
            issues.append(f"{prefix}blade_review[{idx}].result 必须为 'pass' 或 'fail'")

    # 五把刀覆盖检查（支持部分匹配）
    for blade in FIVE_BLADES:
        blade_key = blade.split(": ", 1)[1]  # 如 "相关性刀"
        found = any(isinstance(rb, str) and (blade_key in rb) for rb in reviewed_blades)
        if not found:
            issues.append(f"{prefix}[五把刀] '{blade}' 未被检验")

    return issues


def _validate_sign_off(sign_off, prefix: str) -> list[str]:
    if not isinstance(sign_off, dict):
        return [f"{prefix}sign_off 必须为对象"]
    if "signed" not in sign_off:
        return [f"{prefix}sign_off 缺失字段: signed"]
    if not isinstance(sign_off.get("signed"), bool):
        return [f"{prefix}sign_off.signed 必须为 boolean（true/false）"]
    return []


def _validate_record(record: dict, idx: int | None, *, mode: str) -> tuple[list[str], dict]:
    """Validate record structure and return (issues, summary)."""
    prefix = _fmt_loc(idx)
    issues: list[str] = []
    summary: dict = {
        "message_type": record.get("message_type"),
        "target_hypothesis": record.get("target_hypothesis"),
    }

    msg_type = record.get("message_type", "")
    if msg_type not in ("SKEPTIC_SIGN_OFF", "SKEPTIC_CHALLENGE"):
        return [f"{prefix}未知的 message_type：'{msg_type}'，期望 SKEPTIC_SIGN_OFF 或 SKEPTIC_CHALLENGE"], summary

    if msg_type == "SKEPTIC_SIGN_OFF":
        issues.extend(
            _require_fields(
                record,
                ["message_type", "from", "to", "target_hypothesis", "blade_review", "sign_off"],
                prefix,
            ),
        )
        if not _is_nonempty_str(record.get("from")):
            issues.append(f"{prefix}from 必须为非空字符串")
        if record.get("from") != "skeptic_agent":
            issues.append(f"{prefix}from 必须为 'skeptic_agent'")
        if not _is_nonempty_str(record.get("to")):
            issues.append(f"{prefix}to 必须为非空字符串")
        if record.get("to") not in ("team_lead", "curator_agent"):
            issues.append(f"{prefix}to 必须为 'team_lead' 或 'curator_agent'")
        if not _is_nonempty_str(record.get("target_hypothesis")):
            issues.append(f"{prefix}target_hypothesis 必须为非空字符串")

        issues.extend(_validate_blade_review(record.get("blade_review"), prefix))
        issues.extend(_validate_sign_off(record.get("sign_off"), prefix))

        sign_off = record.get("sign_off") if isinstance(record.get("sign_off"), dict) else {}
        signed = sign_off.get("signed")
        if isinstance(signed, bool):
            if signed:
                # signed==true 必须全 pass + 必须有 declaration
                blade_review = record.get("blade_review") if isinstance(record.get("blade_review"), list) else []
                failed = [b for b in blade_review if isinstance(b, dict) and b.get("result") != "pass"]
                if failed:
                    issues.append(f"{prefix}sign_off.signed=true 时，blade_review 中所有 result 必须为 pass")
                if not _is_nonempty_str(sign_off.get("declaration")):
                    issues.append(f"{prefix}sign_off.signed=true 时，必须提供 sign_off.declaration")
            else:
                blade_review = record.get("blade_review") if isinstance(record.get("blade_review"), list) else []
                has_fail = any(isinstance(b, dict) and b.get("result") == "fail" for b in blade_review)
                if not has_fail:
                    issues.append(f"{prefix}sign_off.signed=false 时，blade_review 中必须至少包含一条 result=='fail'")

        # BugCard signoff convention
        if record.get("target_hypothesis") == "bugcard" and sign_off.get("signed") is True:
            if record.get("bugcard_skeptic_signed") is not True:
                issues.append(f"{prefix}target_hypothesis=bugcard 且 signed=true 时，bugcard_skeptic_signed 必须为 true")

        return issues, summary

    # msg_type == "SKEPTIC_CHALLENGE"
    issues.extend(
        _require_fields(
            record,
            ["message_type", "from", "to", "target_hypothesis", "challenges", "sign_off"],
            prefix,
        ),
    )
    if record.get("from") != "skeptic_agent":
        issues.append(f"{prefix}from 必须为 'skeptic_agent'")
    if record.get("to") not in ("team_lead", "curator_agent"):
        issues.append(f"{prefix}to 必须为 'team_lead' 或 'curator_agent'")
    if not _is_nonempty_str(record.get("target_hypothesis")):
        issues.append(f"{prefix}target_hypothesis 必须为非空字符串")

    issues.extend(_validate_sign_off(record.get("sign_off"), prefix))
    sign_off = record.get("sign_off") if isinstance(record.get("sign_off"), dict) else {}
    if sign_off.get("signed") is not False:
        issues.append(f"{prefix}SKEPTIC_CHALLENGE 中 sign_off.signed 必须为 false")

    challenges = record.get("challenges", [])
    if not isinstance(challenges, list) or not challenges:
        issues.append(f"{prefix}challenges 必须是非空列表")
        return issues, summary

    for cidx, c in enumerate(challenges, start=1):
        if not isinstance(c, dict):
            issues.append(f"{prefix}challenges[{cidx}] 必须为对象")
            continue
        for f in ("challenge_id", "blade", "target_evidence", "challenge", "required_action", "status"):
            if f not in c:
                issues.append(f"{prefix}challenges[{cidx}] 缺失字段: {f}")
        status = c.get("status")
        if status not in ("open", "addressed"):
            issues.append(f"{prefix}challenges[{cidx}].status 必须为 'open' 或 'addressed'")

    return issues, summary


def check_signoff(data, mode: str = "hypothesis") -> tuple[bool, list[str], dict]:
    """
    检查 Skeptic signoff artifact。

    mode:
      - format: 只校验结构/字段/取值合法性（允许 open challenge）
      - hypothesis: 假设签署 gate（必须存在签署，且无 open challenge）
      - bugcard: BugCard 签署 gate（必须存在 bugcard 签署，且无 open challenge）

    Returns (ok, issues, details)
    """
    issues: list[str] = []

    if isinstance(data, dict):
        records = [data]
    elif isinstance(data, list):
        records = data
    else:
        return False, ["文件必须是 YAML 对象或对象列表"], {"records": 0}

    if not records:
        return False, ["signoff artifact 为空（至少包含 1 条记录）"], {"records": 0}

    normalized: list[dict] = []
    for i, rec in enumerate(records, start=1):
        if not isinstance(rec, dict):
            issues.append(f"[record#{i}] 记录必须为对象")
            continue
        normalized.append(rec)

    # Track challenges by id, so append-only logs can update a challenge status
    # in a later record without being permanently blocked by an earlier "open".
    challenge_status: dict[str, str] = {}
    has_signed_hypothesis = False
    has_signed_bugcard = False
    signed_hypothesis_targets: list[str] = []
    signed_bugcard_targets: list[str] = []

    # Structural validation
    for i, rec in enumerate(normalized, start=1):
        rec_issues, summary = _validate_record(rec, i, mode=mode)
        issues.extend(rec_issues)

        if rec.get("message_type") == "SKEPTIC_CHALLENGE":
            challenges = rec.get("challenges", [])
            if isinstance(challenges, list):
                for cidx, c in enumerate(challenges, start=1):
                    if not isinstance(c, dict):
                        continue
                    cid = str(c.get("challenge_id", "")).strip()
                    if not cid:
                        cid = f"record{i}_challenge{cidx}"
                    status = c.get("status")
                    if status in ("open", "addressed"):
                        challenge_status[cid] = status

        if rec.get("message_type") == "SKEPTIC_SIGN_OFF":
            sign_off = rec.get("sign_off", {}) if isinstance(rec.get("sign_off"), dict) else {}
            if sign_off.get("signed") is True:
                target = str(rec.get("target_hypothesis", "")).strip()
                if target == "bugcard":
                    if rec.get("bugcard_skeptic_signed") is True:
                        has_signed_bugcard = True
                        signed_bugcard_targets.append(target)
                else:
                    has_signed_hypothesis = True
                    signed_hypothesis_targets.append(target or "?")

    open_challenge_ids = sorted([cid for cid, st in challenge_status.items() if st == "open"])
    open_challenge_count = len(open_challenge_ids)

    details = {
        "records": len(normalized),
        "open_challenges": open_challenge_count,
        "open_challenge_ids": open_challenge_ids,
        "signed_hypothesis_targets": signed_hypothesis_targets,
        "signed_bugcard_targets": signed_bugcard_targets,
    }

    if issues:
        return False, issues, details

    if mode == "format":
        return True, [], details

    if open_challenge_count > 0:
        if open_challenge_ids:
            ids = ", ".join(open_challenge_ids[:12])
            suffix = "" if len(open_challenge_ids) <= 12 else f" ...(+{len(open_challenge_ids)-12})"
            return False, [f"存在 {open_challenge_count} 个未回应的质疑项（status: open）：{ids}{suffix}"], details
        return False, [f"存在 {open_challenge_count} 个未回应的质疑项（status: open）"], details

    if mode == "hypothesis":
        if not has_signed_hypothesis:
            return False, ["未找到任何已签署的假设记录（需要至少一条 SKEPTIC_SIGN_OFF 且 signed=true，target_hypothesis!=bugcard）"], details
        return True, [], details

    if mode == "bugcard":
        if not has_signed_bugcard:
            return False, ["未找到 BugCard 的有效签署记录（需要 target_hypothesis=bugcard 且 signed=true 且 bugcard_skeptic_signed=true）"], details
        return True, [], details

    return False, [f"未知 mode: {mode}"], details


def main():
    parser = argparse.ArgumentParser(
        description="Debugger Skeptic signoff checker (format validation and gating)",
    )
    parser.add_argument("file", help="Path to skeptic_signoff.yaml")
    parser.add_argument(
        "--mode",
        default="hypothesis",
        choices=["format", "hypothesis", "bugcard"],
        help="format|hypothesis|bugcard",
    )
    args = parser.parse_args()

    path = Path(args.file)
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
        if not isinstance(data, list):
            print(f"{ANSI_RED}错误：文件必须是 YAML 对象或对象列表{ANSI_RESET}")
            sys.exit(2)

    mode = args.mode
    mode_label = "结构校验" if mode == "format" else ("假设签署" if mode == "hypothesis" else "BugCard 签署")
    print(f"\n{'═'*55}")
    print(f"  Debugger Skeptic 签署检查器 — {mode_label}模式")
    print(f"  文件：{path.name}")
    print(f"{'═'*55}")

    ok, issues, details = check_signoff(data, mode=mode)

    if ok:
        print(f"\n{ANSI_GREEN}✅ Skeptic 签署完整 — 可以继续下一阶段{ANSI_RESET}")
        print(f"  records={details.get('records', 0)} open_challenges={details.get('open_challenges', 0)}")
        sys.exit(0)
    else:
        print(f"\n{ANSI_RED}❌ Skeptic 签署不完整 — 不得继续{ANSI_RESET}\n")
        for issue in issues:
            print(f"  • {issue}")
        print(f"\n{ANSI_YELLOW}⚠  请先解决以上质疑项，再由 Skeptic Agent 重新签署。{ANSI_RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
