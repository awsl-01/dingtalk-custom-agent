"""
资产管理功能测试脚本

测试内容：
1. 技能加载
2. 资产录入
3. 资产查询
4. 资产借用
5. 资产归还
6. 资产统计
"""
import sys
import os

# 添加项目根目录到 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from agent.skills.registry import skill_registry
from agent.skills.loader import load_skills
from agent.skills.asset_storage import (
    load_assets, save_assets, create_asset, get_asset_by_id,
    get_asset_stats, delete_asset
)


def print_separator(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_status(success: bool, message: str):
    """打印状态"""
    status = "[OK]" if success else "[FAIL]"
    print(f"{status} {message}")


async def test_skill_loading():
    """测试技能加载"""
    print_separator("测试1：技能加载")

    # 加载所有技能
    loaded = load_skills()
    print(f"[OK] 已加载技能模块: {loaded}")

    # 检查资产管理技能是否注册
    asset_skill = skill_registry.get_skill("资产管理")
    if asset_skill:
        print(f"[OK] 资产管理技能已注册")
        print(f"   - 名称: {asset_skill.name}")
        print(f"   - 描述: {asset_skill.description}")
        print(f"   - 优先级: {asset_skill.priority}")
        return True
    else:
        print("[FAIL] 资产管理技能未注册")
        return False


async def test_asset_storage():
    """测试数据存储模块"""
    print_separator("测试2：数据存储模块")

    test_corp = "test_corp"

    # 清理测试数据
    save_assets([], test_corp)
    print("[OK] 清理测试数据完成")

    # 测试创建资产
    asset1 = create_asset({
        "name": "投影仪",
        "category": "教学设备",
        "location": "301教室",
        "responsible_user": "张老师",
        "description": "索尼投影仪"
    }, test_corp)
    print(f"[OK] 创建资产: {asset1['id']} - {asset1['name']}")

    asset2 = create_asset({
        "name": "电脑",
        "category": "办公设备",
        "location": "办公室",
        "responsible_user": "李老师",
        "description": "联想台式机"
    }, test_corp)
    print(f"[OK] 创建资产: {asset2['id']} - {asset2['name']}")

    # 测试查询
    found = get_asset_by_id(asset1['id'], test_corp)
    if found:
        print(f"[OK] 查询资产: {found['id']} - {found['name']}")
    else:
        print("[FAIL] 查询资产失败")
        return False

    # 测试统计
    stats = get_asset_stats(test_corp)
    print(f"[OK] 资产统计: 总数={stats['total']}, 状态分布={stats['status_count']}")

    # 清理
    delete_asset(asset1['id'], test_corp)
    delete_asset(asset2['id'], test_corp)
    print("[OK] 清理测试数据完成")

    return True


async def test_asset_skill_execute():
    """测试技能执行"""
    print_separator("测试3：技能执行")

    asset_skill = skill_registry.get_skill("资产管理")
    if not asset_skill:
        print("[FAIL] 资产管理技能未注册")
        return False

    test_corp = "test_execute"
    context = {"corp_id": test_corp, "sender_nick": "测试员"}

    # 清理测试数据
    save_assets([], test_corp)

    # 测试录入资产
    print("\n--- 测试录入资产 ---")
    result = await asset_skill.execute("录入资产 投影仪 教学设备 301教室", context)
    print(result)

    # 测试查询资产
    print("\n--- 测试查询资产 ---")
    result = await asset_skill.execute("查询资产 投影仪", context)
    print(result)

    # 获取创建的资产ID
    assets = load_assets(test_corp)
    if assets:
        asset_id = assets[0]['id']
        print(f"\n获取到资产ID: {asset_id}")

        # 测试借用资产
        print("\n--- 测试借用资产 ---")
        result = await asset_skill.execute(f"借用资产 {asset_id} 李老师", context)
        print(result)

        # 测试归还资产
        print("\n--- 测试归还资产 ---")
        result = await asset_skill.execute(f"归还资产 {asset_id}", context)
        print(result)

    # 测试资产统计
    print("\n--- 测试资产统计 ---")
    result = await asset_skill.execute("资产统计", context)
    print(result)

    # 测试帮助信息
    print("\n--- 测试帮助信息 ---")
    result = await asset_skill.execute("资产管理", context)
    print(result)

    # 清理
    save_assets([], test_corp)
    print("\n[OK] 清理测试数据完成")

    return True


async def test_intent_recognition():
    """测试意图识别"""
    print_separator("测试4：意图识别")

    asset_skill = skill_registry.get_skill("资产管理")
    if not asset_skill:
        print("[FAIL] 资产管理技能未注册")
        return False

    test_cases = [
        ("录入资产 投影仪 教学设备 301教室", "add"),
        ("添加资产 电脑 办公设备", "add"),
        ("查询资产 投影仪", "query"),
        ("查找资产 AST20260618001", "query"),
        ("借用资产 AST20260618001 李老师", "borrow"),
        ("归还资产 AST20260618001", "return"),
        ("资产统计", "stats"),
        ("设备统计", "stats"),
    ]

    all_passed = True
    for text, expected_action in test_cases:
        info = asset_skill.extract_info(text)
        actual_action = info.get("action")
        status = "[OK]" if actual_action == expected_action else "[FAIL]"
        print(f"{status} 输入: '{text}'")
        print(f"   期望: {expected_action}, 实际: {actual_action}")
        if actual_action != expected_action:
            all_passed = False

    return all_passed


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("  资产管理功能测试")
    print("=" * 60)

    results = []

    # 运行测试
    results.append(("技能加载", await test_skill_loading()))
    results.append(("数据存储", await test_asset_storage()))
    results.append(("技能执行", await test_asset_skill_execute()))
    results.append(("意图识别", await test_intent_recognition()))

    # 打印总结
    print_separator("测试总结")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[OK] 通过" if result else "[FAIL] 失败"
        print(f"{status} - {name}")

    print(f"\n总计: {passed}/{total} 项测试通过")

    if passed == total:
        print("\n所有测试通过！资产管理功能正常工作。")
    else:
        print("\n部分测试失败，请检查上述输出。")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
