"""
资产管理模板功能测试脚本

测试内容：
1. 模板下载功能
2. Excel 模板生成
3. CSV 模板生成
"""
import sys
import os

# 添加项目根目录到 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from agent.skills.registry import skill_registry
from agent.skills.loader import load_skills


def print_separator(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


async def test_template_download():
    """测试模板下载功能"""
    print_separator("测试1：模板下载功能")

    asset_skill = skill_registry.get_skill("资产管理")
    if not asset_skill:
        print("[FAIL] 资产管理技能未注册")
        return False

    test_corp = "test_template"
    context = {"corp_id": test_corp, "sender_nick": "测试用户"}

    # 测试资产录入模板
    print("\n--- 测试资产录入模板 ---")
    result = await asset_skill.execute("资产录入模板", context)
    print(result)

    # 检查文件是否生成
    if "_file_to_send" in context:
        filepath = context["_file_to_send"]
        if os.path.exists(filepath):
            print(f"\n[OK] 模板文件已生成: {filepath}")
            print(f"[OK] 文件名: {context.get('_file_name')}")
            print(f"[OK] 文件大小: {os.path.getsize(filepath)} 字节")
        else:
            print(f"\n[FAIL] 模板文件未生成: {filepath}")
            return False
    else:
        print("\n[FAIL] 未找到文件发送信息")
        return False

    # 测试资产盘点模板
    print("\n--- 测试资产盘点模板 ---")
    context2 = {"corp_id": test_corp, "sender_nick": "测试用户"}
    result = await asset_skill.execute("资产盘点模板", context2)
    print(result)

    if "_file_to_send" in context2:
        filepath2 = context2["_file_to_send"]
        if os.path.exists(filepath2):
            print(f"\n[OK] 盘点模板文件已生成: {filepath2}")
        else:
            print(f"\n[FAIL] 盘点模板文件未生成: {filepath2}")
            return False
    else:
        print("\n[FAIL] 未找到文件发送信息")
        return False

    return True


async def test_help_with_template():
    """测试帮助信息包含模板说明"""
    print_separator("测试2：帮助信息")

    asset_skill = skill_registry.get_skill("资产管理")
    if not asset_skill:
        print("[FAIL] 资产管理技能未注册")
        return False

    # 获取帮助信息
    help_text = asset_skill._get_help()

    # 检查是否包含模板相关说明
    template_keywords = ["资产录入模板", "资产盘点模板", "批量导入"]
    all_found = True
    for keyword in template_keywords:
        if keyword in help_text:
            print(f"[OK] 帮助信息包含: {keyword}")
        else:
            print(f"[FAIL] 帮助信息缺少: {keyword}")
            all_found = False

    return all_found


async def test_intent_recognition():
    """测试模板意图识别"""
    print_separator("测试3：模板意图识别")

    asset_skill = skill_registry.get_skill("资产管理")
    if not asset_skill:
        print("[FAIL] 资产管理技能未注册")
        return False

    test_cases = [
        ("资产录入模板", "template", "import"),
        ("资产盘点模板", "template", "inventory"),
        ("批量导入模板", "template", "import"),
        ("导入资产", "batch_import", None),
    ]

    all_passed = True
    for text, expected_action, expected_template_type in test_cases:
        info = asset_skill.extract_info(text)
        actual_action = info.get("action")
        actual_template_type = info.get("template_type")

        action_ok = actual_action == expected_action
        template_type_ok = actual_template_type == expected_template_type

        if action_ok and template_type_ok:
            print(f"[OK] '{text}' -> action={actual_action}, template_type={actual_template_type}")
        else:
            print(f"[FAIL] '{text}'")
            print(f"      期望: action={expected_action}, template_type={expected_template_type}")
            print(f"      实际: action={actual_action}, template_type={actual_template_type}")
            all_passed = False

    return all_passed


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("  资产管理模板功能测试")
    print("=" * 60)

    # 加载技能
    print("\n加载技能模块...")
    load_skills()

    results = []

    # 运行测试
    results.append(("模板下载功能", await test_template_download()))
    results.append(("帮助信息", await test_help_with_template()))
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
        print("\n所有测试通过！模板功能正常工作。")
    else:
        print("\n部分测试失败，请检查上述输出。")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
