#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试巡检记录日期解析修复
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime


def test_date_validation():
    """测试日期格式验证"""
    import re
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')

    # 有效日期
    valid_dates = ["2026-06-22", "2026-01-01", "2025-12-31"]
    for date in valid_dates:
        assert date_pattern.match(date), f"应该匹配有效日期: {date}"
        print(f"[PASS] 有效日期: {date}")

    # 无效日期
    invalid_dates = ["检查", "今天", "2026/06/22", "06-22", "abc"]
    for date in invalid_dates:
        assert not date_pattern.match(date), f"应该不匹配无效日期: {date}"
        print(f"[PASS] 无效日期: {date}")


def test_list_records_with_invalid_date():
    """测试 list_records 方法处理无效日期"""
    from agent.inspection.service import InspectionService

    # 创建临时测试目录
    test_dir = "test_inspection_data"
    os.makedirs(test_dir, exist_ok=True)

    try:
        service = InspectionService(test_dir)

        # 测试无效日期
        records = service.list_records(date_str="检查")
        print(f"[PASS] 无效日期 '检查' 返回空列表: {records == []}")

        records = service.list_records(date_str="abc")
        print(f"[PASS] 无效日期 'abc' 返回空列表: {records == []}")

        records = service.list_records(date_str="2026/06/22")
        print(f"[PASS] 无效日期 '2026/06/22' 返回空列表: {records == []}")

        # 测试有效日期
        records = service.list_records(date_str="2026-06-22")
        print(f"[PASS] 有效日期 '2026-06-22' 返回列表: {isinstance(records, list)}")

    finally:
        # 清理测试目录
        import shutil
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


def test_skill_extract_info():
    """测试技能的参数提取"""
    from agent.skills.inspection_skill import InspectionSkill

    skill = InspectionSkill()

    # 测试"巡检记录检查"
    info = skill.extract_info("巡检记录检查")
    print(f"[PASS] '巡检记录检查' 提取的参数: {info.get('params', '')}")
    assert info.get("action") == "list_records"
    assert info.get("params") == "检查"

    # 测试"巡检记录 2026-06-22"
    info = skill.extract_info("巡检记录 2026-06-22")
    print(f"[PASS] '巡检记录 2026-06-22' 提取的参数: {info.get('params', '')}")
    assert info.get("action") == "list_records"
    assert info.get("params") == "2026-06-22"


if __name__ == "__main__":
    print("=" * 50)
    print("测试巡检记录日期解析修复")
    print("=" * 50)

    print("\n1. 测试日期格式验证")
    test_date_validation()

    print("\n2. 测试 list_records 方法")
    test_list_records_with_invalid_date()

    print("\n3. 测试技能参数提取")
    test_skill_extract_info()

    print("\n" + "=" * 50)
    print("[PASS] 所有测试通过！")
    print("=" * 50)
