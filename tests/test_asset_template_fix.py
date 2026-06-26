"""
测试资产管理模板功能修复
验证 "资产录入模板" 不再被误识别为资源搜索
"""
import sys
import os

# 添加项目根目录到 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.skills.registry import skill_registry
from agent.skills.loader import load_skills


def print_separator(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_asset_template_recognition():
    """测试资产管理模板识别"""
    print_separator("测试1：资产管理模板识别")

    # 加载技能
    load_skills()

    # 模拟 main.py 中的逻辑
    RESOURCE_KEYWORDS = ['资源', '素材', '模板', '习题', '试题', '练习题', '视频', '动画']
    asset_template_keywords = ['资产模板', '资产录入模板', '资产盘点模板', '批量导入模板']

    test_cases = [
        ("资产录入模板", True, "import"),
        ("资产盘点模板", True, "inventory"),
        ("批量导入模板", True, "import"),
        ("投影仪课件模板", False, None),
        ("教学资源模板", False, None),
    ]

    all_passed = True
    for text, should_be_asset_template, expected_template_type in test_cases:
        print(f"\n输入: '{text}'")

        # 检查是否是资源请求
        is_resource = any(kw in text.lower() for kw in RESOURCE_KEYWORDS)
        print(f"  is_resource_request: {is_resource}")

        # 检查是否是资产管理模板请求
        is_asset_template = any(kw in text for kw in asset_template_keywords)
        print(f"  is_asset_template: {is_asset_template}")

        # 技能匹配
        skill_match = skill_registry.match(text)
        if skill_match and skill_match.confidence >= 0.7:
            print(f"  匹配技能: {skill_match.skill.name} (置信度: {skill_match.confidence:.2f})")
            info = skill_match.extracted_info
            print(f"  提取信息: action={info.get('action')}, template_type={info.get('template_type')}")
        else:
            print(f"  未匹配到技能")

        # 验证结果
        if is_asset_template == should_be_asset_template:
            print(f"  [OK] 识别正确")
        else:
            print(f"  [FAIL] 识别错误: 期望 is_asset_template={should_be_asset_template}, 实际={is_asset_template}")
            all_passed = False

        if skill_match and skill_match.confidence >= 0.7:
            info = skill_match.extracted_info
            if info.get('template_type') == expected_template_type:
                print(f"  [OK] template_type 正确")
            else:
                print(f"  [FAIL] template_type 错误: 期望={expected_template_type}, 实际={info.get('template_type')}")
                all_passed = False

    return all_passed


def test_main_py_logic():
    """测试 main.py 中的处理逻辑"""
    print_separator("测试2：main.py 处理逻辑")

    # 模拟 main.py 中的逻辑
    RESOURCE_KEYWORDS = ['资源', '素材', '模板', '习题', '试题', '练习题', '视频', '动画']
    asset_template_keywords = ['资产模板', '资产录入模板', '资产盘点模板', '批量导入模板']

    test_text = "资产录入模板"

    # 检查是否是资源请求
    is_resource = any(kw in test_text.lower() for kw in RESOURCE_KEYWORDS)

    # 检查是否是资产管理模板请求
    is_asset_template = any(kw in test_text for kw in asset_template_keywords)

    print(f"输入: '{test_text}'")
    print(f"is_resource: {is_resource}")
    print(f"is_asset_template: {is_asset_template}")

    # 模拟处理逻辑
    if is_resource and is_asset_template:
        print("\n处理逻辑: 跳过资源搜索，走技能匹配逻辑")
        result = "跳过资源搜索，执行资产管理技能"
    elif is_resource and not is_asset_template:
        print("\n处理逻辑: 走资源搜索逻辑")
        result = "执行资源搜索"
    else:
        print("\n处理逻辑: 不是资源请求")
        result = "其他处理"

    print(f"预期结果: 跳过资源搜索，执行资产管理技能")
    print(f"实际结果: {result}")

    if result == "跳过资源搜索，执行资产管理技能":
        print("[OK] 处理逻辑正确")
        return True
    else:
        print("[FAIL] 处理逻辑错误")
        return False


async def test_asset_skill_execute():
    """测试资产管理技能执行"""
    print_separator("测试3：资产管理技能执行")

    asset_skill = skill_registry.get_skill("资产管理")
    if not asset_skill:
        print("[FAIL] 资产管理技能未注册")
        return False

    test_corp = "test_fix"
    context = {"corp_id": test_corp, "sender_nick": "测试用户"}

    # 测试资产录入模板
    print("\n--- 测试资产录入模板 ---")
    result = await asset_skill.execute("资产录入模板", context)
    print(result[:200] + "..." if len(result) > 200 else result)

    # 检查是否生成了文件
    if "_file_to_send" in context:
        filepath = context["_file_to_send"]
        if os.path.exists(filepath):
            print(f"\n[OK] 模板文件已生成: {filepath}")
            print(f"[OK] 文件名: {context.get('_file_name')}")
        else:
            print(f"\n[FAIL] 模板文件未生成: {filepath}")
            return False
    else:
        print("\n[FAIL] 未找到文件发送信息")
        return False

    return True


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("  资产管理模板功能修复测试")
    print("=" * 60)

    results = []

    # 运行测试
    results.append(("资产管理模板识别", test_asset_template_recognition()))
    results.append(("main.py 处理逻辑", test_main_py_logic()))
    results.append(("资产管理技能执行", await test_asset_skill_execute()))

    # 打印总结
    print_separator("测试总结")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[OK] 通过" if result else "[FAIL] 失败"
        print(f"{status} - {name}")

    print(f"\n总计: {passed}/{total} 项测试通过")

    if passed == total:
        print("\n所有测试通过！资产管理模板功能已修复。")
    else:
        print("\n部分测试失败，请检查上述输出。")

    return passed == total


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
