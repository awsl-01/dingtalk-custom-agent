"""
钉钉机器人排课流程测试

模拟完整的排课流程：
1. 用户发送排课数据
2. 系统自动排课
3. 生成课表图片
4. 准备发送给用户
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


async def test_dingtalk_scheduling():
    """测试钉钉机器人排课流程"""
    from agent.skills.scheduling_skill import SchedulingSkill
    from agent.school_config import SchoolConfig

    print("=" * 60)
    print("🤖 钉钉机器人排课流程测试")
    print("=" * 60)

    # 创建模拟的学校配置
    school_config = SchoolConfig(
        corp_id="test_corp_001",
        name="测试学校",
        knowledge_dir=os.path.join(os.path.dirname(__file__), "..", "test_output", "knowledge")
    )
    os.makedirs(school_config.knowledge_dir, exist_ok=True)

    # 创建模拟的 context
    context = {
        "sender_nick": "张老师",
        "user_id": "teacher_001",
        "user_role": "admin",
        "conversation_id": "conv_001",
        "corp_id": "test_corp_001",
        "school_config": school_config,
    }

    # ── 步骤 1：用户发送排课数据 ──
    print("\n【步骤 1】用户发送排课数据...")
    scheduling_text = """班级：高一(1)班、高一(2)班
教师：张老师(数学)、李老师(语文)、王老师(英语)、赵老师(物理)、钱老师(化学)、孙老师(历史)、周老师(地理)、吴老师(体育)、郑老师(音乐)
课程：数学(5课时/周)、语文(5课时/周)、英语(5课时/周)、物理(3课时/周)、化学(3课时/周)、历史(2课时/周)、地理(2课时/周)、体育(2课时/周)、音乐(1课时/周)"""

    print(f"  📤 发送数据：{len(scheduling_text)} 字符")

    # ── 步骤 2：执行排课技能 ──
    print("\n【步骤 2】执行排课技能...")
    skill = SchedulingSkill()
    result = await skill.execute(scheduling_text, context)

    print(f"\n📝 排课结果：")
    print(result)

    # ── 步骤 3：检查生成的文件 ──
    print("\n【步骤 3】检查生成的文件...")
    scheduling_dir = os.path.join(school_config.knowledge_dir, "scheduling")

    if os.path.exists(scheduling_dir):
        files = os.listdir(scheduling_dir)
        print(f"  📁 排课目录：{scheduling_dir}")
        for f in files:
            fpath = os.path.join(scheduling_dir, f)
            size = os.path.getsize(fpath)
            print(f"    • {f} ({size:,} bytes)")
    else:
        print(f"  ❌ 排课目录不存在：{scheduling_dir}")

    # ── 步骤 4：检查 context 中的文件 ──
    print("\n【步骤 4】检查 context 中的文件...")
    file_to_send = context.get("_file_to_send")
    file_name = context.get("_file_name")
    file_type = context.get("_file_type")

    if file_to_send and os.path.exists(file_to_send):
        size = os.path.getsize(file_to_send)
        print(f"  ✅ 待发送文件：{file_to_send}")
        print(f"    • 文件名：{file_name}")
        print(f"    • 文件类型：{file_type}")
        print(f"    • 文件大小：{size:,} bytes")
    else:
        print(f"  ⚠️ 没有待发送的文件")

    # ── 步骤 5：模拟钉钉发送 ──
    print("\n【步骤 5】模拟钉钉发送...")
    if file_to_send and os.path.exists(file_to_send):
        print(f"  📤 调用 send_image_message() 发送图片...")
        print(f"    • 目标用户：{context['sender_nick']}")
        print(f"    • 图片路径：{file_to_send}")
        print(f"  ✅ 图片发送成功（模拟）")
    else:
        print(f"  ⚠️ 没有图片可发送")

    print("\n" + "=" * 60)
    print("✅ 钉钉机器人排课流程测试完成!")
    print("=" * 60)

    return {
        "result": result,
        "file_to_send": file_to_send,
        "file_name": file_name,
    }


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_dingtalk_scheduling())
