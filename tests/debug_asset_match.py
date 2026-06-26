"""
调试资产管理技能匹配
"""
import sys
import os

# 添加项目根目录到 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.skills.registry import skill_registry
from agent.skills.loader import load_skills

# 加载技能
print("加载技能模块...")
loaded = load_skills()
print(f"已加载: {loaded}")

# 检查资产管理技能
asset_skill = skill_registry.get_skill("资产管理")
if asset_skill:
    print(f"\n资产管理技能已注册")
    print(f"优先级: {asset_skill.priority}")
else:
    print("\n[ERROR] 资产管理技能未注册")

# 测试匹配
test_texts = [
    "资产录入模板",
    "资产盘点模板",
    "批量导入模板",
    "录入资产 投影仪 教学设备 301教室",
    "查询资产 投影仪",
]

print("\n" + "=" * 60)
print("  测试技能匹配")
print("=" * 60)

for text in test_texts:
    print(f"\n输入: '{text}'")

    # 匹配所有技能
    matches = skill_registry.match_all(text)

    if matches:
        for match in matches:
            print(f"  - {match.skill.name}: 置信度={match.confidence:.2f}, 优先级={match.skill.priority}")
    else:
        print("  - 无匹配")

    # 单独检查资产管理技能
    if asset_skill:
        confidence = asset_skill.can_handle(text)
        info = asset_skill.extract_info(text)
        print(f"  资产管理技能: 置信度={confidence:.2f}, action={info.get('action')}, template_type={info.get('template_type')}")
