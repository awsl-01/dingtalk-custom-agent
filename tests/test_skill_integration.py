"""
测试技能集成 - 验证 LLM 意图识别与技能系统的集成
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.intent_router import intent_router


async def test_inspection_integration():
    """测试巡检技能集成"""
    print("=" * 60)
    print("Test: Inspection Skill Integration")
    print("=" * 60)

    from agent.skills.inspection_skill import InspectionSkill

    skill = InspectionSkill()
    context = {
        'user_id': 'test_user_001',
        'sender_nick': '张老师',
        'conversation_id': 'test_conv_001',
        'corp_id': 'test_corp',
    }

    test_cases = [
        # (消息, 期望的action)
        ("查看昨天的巡检记录", "list_records"),
        ("帮我打卡教学楼A", "check_in"),
        ("巡检统计", "stats"),
        ("上报问题 教学楼走廊灯管损坏", "report_issue"),
    ]

    for text, expected_action in test_cases:
        print(f"\nInput: {text}")

        # 1. LLM 识别意图
        intent = await intent_router.classify(text, context)
        print(f"Intent: {intent.type}/{intent.action} (confidence: {intent.confidence:.2f})")
        print(f"Params: {intent.params}")

        # 2. 将 intent 传递给技能
        context['intent'] = intent

        # 3. 提取信息（使用技能的 extract_info）
        info = skill.extract_info(text)
        print(f"Extracted info: {info}")

        # 4. 检查是否匹配
        if intent.type == "inspection":
            print(f"[PASS] Intent matched inspection skill")
        else:
            print(f"[FAIL] Intent did not match inspection skill")


async def test_asset_integration():
    """测试资产技能集成"""
    print("\n" + "=" * 60)
    print("Test: Asset Skill Integration")
    print("=" * 60)

    from agent.skills.asset_skill import AssetSkill

    skill = AssetSkill()
    context = {
        'user_id': 'test_user_001',
        'sender_nick': '张老师',
        'conversation_id': 'test_conv_001',
        'corp_id': 'test_corp',
    }

    test_cases = [
        ("录入资产 投影仪 教学设备 3个 301教室", "add"),
        ("查询资产 投影仪", "query"),
        ("资产统计", "stats"),
        ("借用设备 投影仪", "borrow"),
    ]

    for text, expected_action in test_cases:
        print(f"\nInput: {text}")

        # 1. LLM 识别意图
        intent = await intent_router.classify(text, context)
        print(f"Intent: {intent.type}/{intent.action} (confidence: {intent.confidence:.2f})")
        print(f"Params: {intent.params}")

        # 2. 提取信息
        info = skill.extract_info(text)
        print(f"Extracted info: {info}")

        # 3. 检查是否匹配
        if intent.type == "asset":
            print(f"[PASS] Intent matched asset skill")
        else:
            print(f"[FAIL] Intent did not match asset skill")


async def test_schedule_integration():
    """测试课表技能集成"""
    print("\n" + "=" * 60)
    print("Test: Schedule Skill Integration")
    print("=" * 60)

    from agent.skills.schedule_skill import ScheduleSkill

    skill = ScheduleSkill()
    context = {
        'user_id': 'test_user_001',
        'sender_nick': '张老师',
        'conversation_id': 'test_conv_001',
        'corp_id': 'test_corp',
    }

    test_cases = [
        ("查询课表", "query"),
        ("计算机2301班周一有什么课", "query"),
        ("调课 周一上午和周二上午", "swap"),
    ]

    for text, expected_action in test_cases:
        print(f"\nInput: {text}")

        # 1. LLM 识别意图
        intent = await intent_router.classify(text, context)
        print(f"Intent: {intent.type}/{intent.action} (confidence: {intent.confidence:.2f})")
        print(f"Params: {intent.params}")

        # 2. 提取信息
        info = skill.extract_info(text)
        print(f"Extracted info: {info}")

        # 3. 检查是否匹配
        if intent.type == "schedule":
            print(f"[PASS] Intent matched schedule skill")
        else:
            print(f"[FAIL] Intent did not match schedule skill")


async def test_parameter_extraction():
    """测试参数提取"""
    print("\n" + "=" * 60)
    print("Test: Parameter Extraction")
    print("=" * 60)

    test_cases = [
        # 巡检参数
        ("查看昨天的巡检记录", ["time"]),
        ("张三今天打卡了吗", ["time", "person_name"]),
        ("帮我打卡教学楼A", ["point_name"]),
        ("操场看台的巡检照片", ["point_name"]),

        # PPT参数
        ("生成一个关于春天的课件", ["topic"]),
        ("做一个15页的演示文稿", ["page_count"]),
        ("数学课件 高中一年级", ["subject", "grade"]),

        # 资产参数
        ("录入资产 投影仪 3个 301教室", ["asset_name", "quantity", "location"]),
        ("查询资产 教学设备", ["asset_type"]),

        # 课表参数
        ("计算机2301班周一有什么课", ["class_name", "day_of_week"]),
        ("张老师周三的课表", ["teacher_name", "day_of_week"]),
    ]

    for text, expected_params in test_cases:
        print(f"\nInput: {text}")
        print(f"Expected params: {expected_params}")

        intent = await intent_router.classify(text)
        print(f"Intent: {intent.type}/{intent.action}")
        print(f"Actual params: {intent.params}")

        # 检查是否包含期望的参数
        missing_params = []
        for param in expected_params:
            if param not in intent.params:
                missing_params.append(param)

        if not missing_params:
            print(f"[PASS] All expected params found")
        else:
            print(f"[FAIL] Missing params: {missing_params}")


async def main():
    """运行所有测试"""
    await test_inspection_integration()
    await test_asset_integration()
    await test_schedule_integration()
    await test_parameter_extraction()

    print("\n" + "=" * 60)
    print("All integration tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
