"""
最终测试：验证课表查询功能
"""
import asyncio
import json
import os
import sys

# 强制使用 UTF-8 编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.skills.schedule_skill import ScheduleSkill


async def test_schedule_final():
    """最终测试课表查询功能"""

    skill = ScheduleSkill()

    # 测试查询
    test_cases = [
        ("高一(1)班周一数学课", 0.8),
        ("高一(1)班课程表", 0.8),
        ("高一(1)班周一有什么课", 0.8),
        ("高一(1)班有什么课", 0.8),
        ("查询课表", 0.7),
        ("帮我查一下高一(1)班的课表", 0.8),
    ]

    print("=" * 60)
    print("[INFO] 测试课表管理技能的 can_handle 方法")
    print("=" * 60)

    for text, expected_confidence in test_cases:
        confidence = skill.can_handle(text)
        status = "✓" if confidence >= 0.7 else "✗"
        print(f"{status} '{text}' -> 置信度: {confidence:.2f} (期望 >= 0.7)")

    print("\n" + "=" * 60)
    print("[INFO] 测试课表查询逻辑")
    print("=" * 60)

    # 模拟上下文
    from agent.school_config import school_manager
    school_config = school_manager.get_school("ding3f80869f26d4bb44a39a90f97fcb1e09")

    context = {
        "sender_nick": "测试用户",
        "user_id": "test_user",
        "conversation_id": "test_conv",
        "corp_id": "ding3f80869f26d4bb44a39a90f97fcb1e09",
        "school_config": school_config,
    }

    # 测试查询
    test_queries = [
        "高一(1)班周一数学课",
        "高一(1)班周一有什么课",
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"[查询] {query}")
        print('='*60)

        try:
            result = await skill.execute(query, context)
            print(f"[结果]\n{result[:500]}...")
        except Exception as e:
            print(f"[ERROR] {e}")


if __name__ == "__main__":
    asyncio.run(test_schedule_final())
