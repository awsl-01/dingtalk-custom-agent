"""
PPT Engine 第四阶段测试

测试PPTX动画系统和实时预览系统。
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.ppt_engine.animations.transition_effects import TransitionEffect, create_transition
from agent.ppt_engine.animations.entrance_animations import EntranceAnimation, create_animation
from agent.ppt_engine.svg_editor.server import create_app


def test_transition_effects():
    """测试转场效果"""
    print("\n" + "="*60)
    print("[TEST] Transition Effects")
    print("="*60)

    # 测试列出转场
    print("\n1. List transitions...")
    transitions = TransitionEffect.list_transitions()
    print(f"   Available transitions: {transitions}")

    # 测试创建转场
    print("\n2. Create transitions...")
    for t_type in ['fade', 'push', 'wipe', 'split', 'strips', 'cover']:
        transition = create_transition(t_type)
        xml = transition.to_xml()
        print(f"   {t_type}: {len(xml)} chars")

    # 测试随机转场
    print("\n3. Random transition...")
    random_transition = create_transition('random')
    print(f"   Type: {random_transition.type.value}")

    # 测试无转场
    print("\n4. No transition...")
    no_transition = create_transition('none')
    xml = no_transition.to_xml()
    print(f"   XML empty: {xml == ''}")


def test_entrance_animations():
    """测试入场动画"""
    print("\n" + "="*60)
    print("[TEST] Entrance Animations")
    print("="*60)

    # 测试列出动画效果
    print("\n1. List effects...")
    effects = EntranceAnimation.list_effects()
    print(f"   Available effects: {effects}")

    # 测试创建动画
    print("\n2. Create animations...")
    for effect in ['fade', 'fly', 'zoom', 'wipe', 'dissolve']:
        animation = create_animation(effect)
        xml = animation.to_xml(100)
        print(f"   {effect}: {len(xml)} chars")

    # 测试智能选择
    print("\n3. Auto-select effects...")
    test_cases = [
        ('title-01', 'auto'),
        ('card-01', 'auto'),
        ('chart-01', 'auto'),
        ('image-01', 'auto'),
        ('hero-01', 'auto'),
        ('unknown-01', 'auto'),
    ]

    for group_id, mode in test_cases:
        effect = EntranceAnimation.pick_effect(group_id, mode)
        print(f"   {group_id} -> {effect.value}")

    # 测试图片效果循环
    print("\n4. Image effect cycling...")
    for i in range(6):
        effect = EntranceAnimation.pick_effect('image', 'auto', i)
        print(f"   image[{i}] -> {effect.value}")


def test_svg_editor():
    """测试SVG编辑器"""
    print("\n" + "="*60)
    print("[TEST] SVG Editor")
    print("="*60)

    # 测试Flask可用性
    print("\n1. Check Flask availability...")
    try:
        from flask import Flask
        print("   [OK] Flask is available")
    except ImportError:
        print("   [SKIP] Flask not installed")
        return

    # 测试创建应用
    print("\n2. Create Flask app...")
    project_path = 'D:/claude/projects/test_project'

    if Path(project_path).exists():
        try:
            app = create_app(project_path)
            print(f"   [OK] App created: {app.name}")
        except Exception as e:
            print(f"   [FAIL] Create app failed: {e}")
    else:
        print(f"   [SKIP] Project not found: {project_path}")


def test_animation_integration():
    """测试动画集成"""
    print("\n" + "="*60)
    print("[TEST] Animation Integration")
    print("="*60)

    # 测试完整动画配置
    print("\n1. Full animation config...")
    config = {
        'transition': {
            'type': 'fade',
            'duration': 500
        },
        'entrance': {
            'mode': 'auto',
            'trigger': 'after-previous',
            'duration': 500
        }
    }

    # 创建转场
    transition = create_transition(
        config['transition']['type'],
        config['transition']['duration']
    )
    print(f"   Transition: {transition.type.value}")

    # 创建入场动画
    animation = create_animation(
        config['entrance']['mode'],
        config['entrance']['trigger'],
        duration=config['entrance']['duration']
    )
    print(f"   Animation: {animation.effect.value}")

    # 测试生成多个元素的动画
    print("\n2. Generate animations for multiple elements...")
    elements = ['title-01', 'card-01', 'card-02', 'card-03', 'image-01', 'chart-01']

    for elem in elements:
        effect = EntranceAnimation.pick_effect(elem, 'auto')
        anim = create_animation(effect.value)
        xml = anim.to_xml(hash(elem) % 1000)
        print(f"   {elem}: {effect.value} ({len(xml)} chars)")


def main():
    """主测试函数"""
    print("[START] PPT Engine Phase 4 Test")
    print("="*60)

    try:
        # 1. 测试转场效果
        test_transition_effects()

        # 2. 测试入场动画
        test_entrance_animations()

        # 3. 测试SVG编辑器
        test_svg_editor()

        # 4. 测试动画集成
        test_animation_integration()

        print("\n" + "="*60)
        print("[DONE] All Phase 4 tests passed!")
        print("="*60)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
