"""
测试 LLM 意图路由器
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.intent_router import intent_router, UserIntent


async def test_intent_router():
    """测试意图路由器"""
    test_cases = [
        # 巡检相关 - 只检查意图类型，不检查具体操作
        ("查看昨天的巡检记录", "inspection"),
        ("张三今天打卡了吗", "inspection"),
        ("帮我打卡教学楼A", "inspection"),
        ("巡检统计", "inspection"),
        ("操场看台的巡检照片", "inspection"),

        # PPT相关
        ("帮我做个PPT", "ppt"),
        ("生成一个关于春天的课件", "ppt"),
        ("做一个15页的演示文稿", "ppt"),

        # 资产相关
        ("录入资产 投影仪 3个", "asset"),
        ("查询资产", "asset"),
        ("借用设备", "asset"),

        # 课表相关
        ("查询课表", "schedule"),
        ("调课", "schedule"),

        # 搜索相关
        ("搜索北京天气", "search"),
        ("查找教学资源", "search"),
        ("最近有什么新闻", "search"),

        # 普通对话
        ("你好", "chat"),
        ("你是谁", "chat"),
    ]

    print("=" * 60)
    print("LLM intent router test")
    print("=" * 60)

    passed = 0
    failed = 0

    for text, expected_intent in test_cases:
        try:
            intent = await intent_router.classify(text)

            # 只检查意图类型
            intent_match = intent.type == expected_intent

            status = "[PASS]" if intent_match else "[FAIL]"

            if intent_match:
                passed += 1
            else:
                failed += 1

            print(f"\n{status} Input: {text}")
            print(f"   Expected: {expected_intent}")
            print(f"   Actual: {intent.type}/{intent.action} (confidence: {intent.confidence:.2f})")
            if intent.params:
                print(f"   Params: {intent.params}")

        except Exception as e:
            print(f"\n[ERROR] Input: {text}")
            print(f"   Error: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Test result: {passed} passed, {failed} failed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_intent_router())
