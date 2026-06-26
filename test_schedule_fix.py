#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试课表查询修复
验证"高一（1）班，语文课在什么时候"不再误触发调课流程
"""
import sys
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, 'D:/claude')

from agent.skills.schedule_skill import ScheduleSkill

def test_can_handle():
    """测试can_handle方法"""
    skill = ScheduleSkill()

    test_cases = [
        ("高一（1）班，语文课在什么时候", 0.8, "课表查询"),
        ("计算机2301班周一有什么课？", 0.7, "课表查询"),
        ("张老师周一和周二调课", 0.9, "调课请求"),
        ("同意", 0, "调课确认"),
        ("拒绝", 0, "调课确认"),
        ("取消", 0, "调课取消"),
    ]

    print("=" * 60)
    print("测试 can_handle 方法")
    print("=" * 60)

    all_passed = True
    for text, expected_min, desc in test_cases:
        confidence = skill.can_handle(text)
        status = "[PASS]" if confidence >= expected_min else "[FAIL]"
        if confidence < expected_min:
            all_passed = False
        print(f"{status} {desc}: '{text}' -> 置信度: {confidence:.2f} (期望: >= {expected_min})")

    print("=" * 60)
    return all_passed


def test_extract_info():
    """测试extract_info方法"""
    skill = ScheduleSkill()

    test_cases = [
        "高一（1）班，语文课在什么时候",
        "高一(1)班周一有什么课",
        "计算机2301班的课表",
    ]

    print("\n" + "=" * 60)
    print("测试 extract_info 方法")
    print("=" * 60)

    all_passed = True
    for text in test_cases:
        info = skill.extract_info(text)
        has_class = bool(info.get("class_name"))
        is_query = info.get("action") == "query"

        status = "[PASS]" if has_class and is_query else "[FAIL]"
        if not (has_class and is_query):
            all_passed = False

        print(f"{status} '{text}'")
        print(f"   班级: {info.get('class_name', '未提取')}")
        print(f"   动作: {info.get('action', '未提取')}")
        print()

    print("=" * 60)
    return all_passed


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("课表查询修复测试")
    print("=" * 60 + "\n")

    passed = 0
    total = 2

    if test_can_handle():
        passed += 1

    if test_extract_info():
        passed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{total} 通过")
    print("=" * 60)

    if passed == total:
        print("\n[PASS] 所有测试通过！")
        return 0
    else:
        print("\n[FAIL] 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
