"""
LLM 优化测试脚本

测试知识库接入大模型后的优化效果：
1. 智能分类
2. 智能过滤
3. 意图理解
4. 意图驱动检索
5. 灵活回答生成
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.llm_utils import call_llm, call_llm_json
from agent.knowledge_base_v2 import (
    classify_text,
    classify_text_with_llm,
    smart_classify,
    should_skip_message,
    should_skip_message_with_llm,
    smart_should_skip,
)
from agent.search.intent import recognize_intent, IntentRecognizer


async def test_llm_utils():
    """测试 LLM 工具模块"""
    print("\n" + "=" * 60)
    print("测试 1: LLM 工具模块")
    print("=" * 60)

    # 测试文本调用
    print("\n1.1 测试文本调用:")
    response = await call_llm("请用一句话介绍自己", max_tokens=100)
    print(f"   响应: {response[:100]}...")

    # 测试 JSON 调用
    print("\n1.2 测试 JSON 调用:")
    result = await call_llm_json(
        '{"name": "测试", "value": 123}',
        max_tokens=100
    )
    print(f"   结果: {result}")

    print("\n✅ LLM 工具模块测试完成")


async def test_smart_classify():
    """测试智能分类"""
    print("\n" + "=" * 60)
    print("测试 2: 智能分类")
    print("=" * 60)

    test_cases = [
        # 明确的分类
        ("计算机2301班周一上午有数学课", "schedule"),
        ("下周一期中考试安排", "exam"),
        ("张教授的电话是138xxxx", "contact"),
        ("今天的作业是第三章习题", "homework"),
        ("明天放假通知", "notice"),
        ("这是第三章的教案", "teaching"),
        ("学生名单已更新", "student"),

        # 边界情况（需要 LLM 判断）
        ("食堂菜单更新了", "other"),
        ("校园网密码修改方法", "other"),
        ("图书馆开放时间调整", "notice"),
    ]

    for text, expected in test_cases:
        # 关键词匹配
        keyword_result = classify_text(text)
        # 智能分类
        smart_result = await smart_classify(text)

        status = "✅" if smart_result == expected else "❌"
        print(f"\n{status} 文本: {text[:30]}...")
        print(f"   期望: {expected}")
        print(f"   关键词: {keyword_result}")
        print(f"   智能: {smart_result}")

    print("\n✅ 智能分类测试完成")


async def test_smart_should_skip():
    """测试智能过滤"""
    print("\n" + "=" * 60)
    print("测试 3: 智能过滤")
    print("=" * 60)

    test_cases = [
        # 应该跳过
        ("好的", True),
        ("谢谢", True),
        ("666", True),
        ("帮我查一下课表", True),

        # 应该保留
        ("计算机2301班周一上午有数学课", False),
        ("张教授的电话是138xxxx", False),
        ("下周一期中考试安排", False),

        # 边界情况（需要 LLM 判断）
        ("张教授的课表是什么", True),  # 问题，应该跳过
        ("明天放假", False),  # 通知，应该保留
        ("这个作业怎么做", True),  # 问题，应该跳过
    ]

    for text, expected in test_cases:
        # 关键词匹配
        keyword_result = should_skip_message(text)
        # 智能过滤
        smart_result = await smart_should_skip(text)

        status = "✅" if smart_result == expected else "❌"
        print(f"\n{status} 文本: {text[:30]}...")
        print(f"   期望: {'跳过' if expected else '保留'}")
        print(f"   关键词: {'跳过' if keyword_result else '保留'}")
        print(f"   智能: {'跳过' if smart_result else '保留'}")

    print("\n✅ 智能过滤测试完成")


async def test_intent_recognition():
    """测试意图识别"""
    print("\n" + "=" * 60)
    print("测试 4: 意图识别")
    print("=" * 60)

    test_cases = [
        # 人物信息
        ("张教授是谁", "person_info"),
        ("介绍一下李老师", "person_info"),
        ("张教授的联系方式", "contact"),

        # 课表
        ("课表", "schedule"),
        ("周一有什么课", "schedule"),
        ("计算机2301班的课表", "schedule"),

        # 考试
        ("考试安排", "exam"),
        ("成绩查询", "exam"),

        # 通知
        ("放假通知", "notice"),
        ("活动安排", "notice"),
    ]

    recognizer = IntentRecognizer()

    for query, expected_type in test_cases:
        intent = await recognizer.recognize(query)

        status = "✅" if intent.type == expected_type else "❌"
        print(f"\n{status} 查询: {query}")
        print(f"   期望类型: {expected_type}")
        print(f"   识别类型: {intent.type} (置信度: {intent.confidence:.2f})")
        print(f"   提取实体: {intent.entities}")
        print(f"   建议关键词: {intent.suggested_keywords[:3]}")

    print("\n✅ 意图识别测试完成")


async def main():
    """主测试函数"""
    print("=" * 60)
    print("  LLM 优化测试")
    print("=" * 60)

    try:
        await test_llm_utils()
        await test_smart_classify()
        await test_smart_should_skip()
        await test_intent_recognition()

        print("\n" + "=" * 60)
        print("  所有测试完成")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
