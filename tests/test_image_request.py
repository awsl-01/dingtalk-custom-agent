"""
测试图片请求处理

模拟用户发送"排好课的照片发给我"的场景
"""
import sys
import os
import json
import logging

# 强制使用 UTF-8 编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def test_image_request():
    """测试图片请求"""
    from agent.skills.schedule_skill import ScheduleSkill
    from agent.school_config import SchoolConfig

    print("=" * 60)
    print("📸 测试图片请求处理")
    print("=" * 60)

    # 创建模拟的学校配置
    knowledge_dir = os.path.join(os.path.dirname(__file__), "..", "test_output", "knowledge")
    school_config = SchoolConfig(
        corp_id="test_corp_001",
        name="测试学校",
        knowledge_dir=knowledge_dir
    )

    # 创建模拟的 context
    context = {
        "sender_nick": "张老师",
        "user_id": "teacher_001",
        "user_role": "admin",
        "conversation_id": "conv_001",
        "corp_id": "test_corp_001",
        "school_config": school_config,
    }

    # 测试不同的请求
    test_cases = [
        "排好课的照片发给我",
        "课表图片",
        "把课表截图发给我",
        "发送课程表照片",
    ]

    skill = ScheduleSkill()

    for test_text in test_cases:
        print(f"\n{'─' * 60}")
        print(f"📝 测试请求：{test_text}")

        # 测试 can_handle
        confidence = skill.can_handle(test_text)
        print(f"  • 匹配置信度：{confidence:.2f}")

        # 清空之前的 context
        context.pop("_file_to_send", None)
        context.pop("_file_name", None)
        context.pop("_file_type", None)

        # 执行技能
        result = await skill.execute(test_text, context)

        print(f"\n📤 返回结果：")
        # 只显示前500字符
        if len(result) > 500:
            print(f"{result[:500]}...")
        else:
            print(result)

        # 检查是否生成了图片
        file_to_send = context.get("_file_to_send")
        if file_to_send and os.path.exists(file_to_send):
            size = os.path.getsize(file_to_send)
            print(f"\n✅ 已生成图片：{context.get('_file_name')} ({size:,} bytes)")
        else:
            print(f"\n⚠️ 未生成图片")

    print(f"\n{'=' * 60}")
    print("✅ 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_image_request())
