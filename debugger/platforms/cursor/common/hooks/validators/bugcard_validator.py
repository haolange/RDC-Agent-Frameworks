#!/usr/bin/env python3
"""
BugCard Validator

验证BugCard YAML文件的完整性和字段有效性。
作为hooks框架的一部分，接收YAML文件路径并返回适当的退出码。

用法:
    python bugcard_validator.py <yaml_file_path>

退出码:
    0 - 验证通过
    1 - 验证失败（字段缺失或格式错误）
"""

import sys
import os
import argparse


def validate_bugcard(yaml_path: str) -> tuple[bool, list[str]]:
    """
    验证BugCard YAML文件。

    Args:
        yaml_path: YAML文件的路径

    Returns:
        (是否通过, 错误信息列表)
    """
    errors = []

    # 检查文件是否存在
    if not os.path.exists(yaml_path):
        errors.append(f"File not found: {yaml_path}")
        return False, errors

    # 检查文件扩展名
    if not yaml_path.endswith(('.yaml', '.yml')):
        errors.append(f"Not a YAML file: {yaml_path}")
        return False, errors

    # TODO: 实现实际的BugCard字段验证
    # 需要检查的12项字段:
    # - bug_id
    # - title
    # - description
    # - root_cause
    # - symptoms
    # - reproduction_steps
    # - fix_description
    # - verification_method
    # - causal_anchor
    # - counterfactual_tests
    # - skeptic_signoff
    # - session_artifacts

    # 临时实现：仅检查文件可读性
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                errors.append("File is empty")
                return False, errors
    except Exception as e:
        errors.append(f"Failed to read file: {e}")
        return False, errors

    return True, []


def main():
    parser = argparse.ArgumentParser(
        description="Validate BugCard YAML file"
    )
    parser.add_argument(
        'yaml_path',
        help='Path to the BugCard YAML file to validate'
    )

    args = parser.parse_args()

    is_valid, errors = validate_bugcard(args.yaml_path)

    if not is_valid:
        print("BugCard validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)

    print("BugCard validation passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
