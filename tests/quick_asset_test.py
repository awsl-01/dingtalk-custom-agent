"""
资产管理快速测试脚本

直接在命令行测试资产管理功能
"""
import sys
import os

# 添加项目根目录到 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from agent.skills.registry import skill_registry
from agent.skills.loader import load_skills


async def main():
    """交互式测试"""
    print("=" * 60)
    print("  资产管理功能快速测试")
    print("=" * 60)
    print("\n加载技能模块...")
    load_skills()

    asset_skill = skill_registry.get_skill("资产管理")
    if not asset_skill:
        print("[错误] 资产管理技能未注册")
        return

    print("[成功] 资产管理技能已加载")
    print("\n输入消息测试，输入 'quit' 退出\n")

    context = {"corp_id": "demo_school", "sender_nick": "测试用户"}

    while True:
        try:
            user_input = input("用户> ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("再见！")
                break
            if not user_input:
                continue

            result = await asset_skill.execute(user_input, context)
            print(f"\n机器人> {result}\n")

        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            print(f"\n[错误] {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
