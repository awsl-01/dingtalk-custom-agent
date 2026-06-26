"""
PPT Engine 第二阶段测试

测试设计规范系统、模板系统和布局模板库。
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.ppt_engine.design_spec.strategist import Strategist, DesignSpec, create_design_spec
from agent.ppt_engine.design_spec.spec_lock_generator import SpecLockGenerator, generate_spec_lock
from agent.ppt_engine.templates.brand_manager import BrandManager, Brand
from agent.ppt_engine.templates.layout_manager import LayoutManager, Layout
from agent.ppt_engine.templates.deck_manager import DeckManager, Deck


def test_strategist():
    """测试设计策略师"""
    print("\n" + "="*60)
    print("[TEST] Strategist")
    print("="*60)

    project_path = Path('D:/claude/projects/test_phase2')
    project_path.mkdir(parents=True, exist_ok=True)

    # 测试创建设计规范
    print("\n1. Create design spec...")
    content = {
        'title': 'Math Lesson: Quadratic Functions',
        'subtitle': 'High School Mathematics',
        'subject': 'math',
        'audience': 'student',
        'style': 'education',
        'canvas_format': 'ppt169',
        'page_count': 10,
        'pages': [
            {'title': 'Cover', 'layout': 'cover', 'rhythm': 'anchor'},
            {'title': 'Objectives', 'layout': 'content', 'rhythm': 'dense'},
            {'title': 'Definition', 'layout': 'formula_step', 'rhythm': 'dense'},
            {'title': 'Graph', 'layout': 'graph_illustration', 'rhythm': 'dense'},
            {'title': 'Examples', 'layout': 'exercise_steps', 'rhythm': 'dense'},
            {'title': 'Practice', 'layout': 'exercise_steps', 'rhythm': 'dense'},
            {'title': 'Summary', 'layout': 'content', 'rhythm': 'dense'},
            {'title': 'End', 'layout': 'ending', 'rhythm': 'breathing'},
        ]
    }

    spec = create_design_spec(str(project_path), content)
    print(f"   Title: {spec.title}")
    print(f"   Canvas: {spec.canvas_format} ({spec.width}x{spec.height})")
    print(f"   Pages: {len(spec.pages)}")
    print(f"   Colors: {spec.colors.primary}")

    # 测试生成spec_lock
    print("\n2. Generate spec_lock...")
    spec_lock_path = generate_spec_lock(str(project_path), spec)
    print(f"   Path: {spec_lock_path}")

    return project_path


def test_brand_manager():
    """测试品牌管理器"""
    print("\n" + "="*60)
    print("[TEST] Brand Manager")
    print("="*60)

    manager = BrandManager()

    # 测试列出品牌
    print("\n1. List brands...")
    brands = manager.list_brands()
    print(f"   Total brands: {len(brands)}")

    # 显示预设品牌
    preset_brands = [b for b in brands if b['type'] == 'preset']
    print(f"   Preset brands: {len(preset_brands)}")
    for b in preset_brands[:3]:
        print(f"     - {b['id']}: {b['name']}")

    # 显示学科品牌
    subject_brands = [b for b in brands if b['type'] == 'subject']
    print(f"   Subject brands: {len(subject_brands)}")
    for b in subject_brands[:3]:
        print(f"     - {b['id']}: {b['name']}")

    # 测试获取品牌
    print("\n2. Get brand...")
    math_brand = manager.get_brand('math')
    if math_brand:
        print(f"   Brand: {math_brand.name}")
        print(f"   Primary: {math_brand.colors['primary']}")
        print(f"   Accent: {math_brand.colors['accent']}")

    # 测试融合品牌
    print("\n3. Fuse brands...")
    fused = manager.fuse_brands('math', 'education')
    print(f"   Fused: {fused.name}")
    print(f"   Primary: {fused.colors['primary']}")

    return manager


def test_layout_manager():
    """测试布局管理器"""
    print("\n" + "="*60)
    print("[TEST] Layout Manager")
    print("="*60)

    manager = LayoutManager()

    # 测试列出布局
    print("\n1. List layouts...")
    layouts = manager.list_layouts()
    print(f"   Total layouts: {len(layouts)}")

    # 显示通用布局
    general_layouts = [l for l in layouts if l['category'] == 'general']
    print(f"   General layouts: {len(general_layouts)}")
    for l in general_layouts[:3]:
        print(f"     - {l['id']}: {l['name']}")

    # 显示学科布局
    subject_layouts = [l for l in layouts if l['category'] == 'subject']
    print(f"   Subject layouts: {len(subject_layouts)}")

    # 测试获取布局
    print("\n2. Get layout...")
    formula_layout = manager.get_layout('formula_step')
    if formula_layout:
        print(f"   Layout: {formula_layout.name}")
        print(f"   Subjects: {formula_layout.subjects}")
        print(f"   Page types: {formula_layout.page_types}")

    # 测试学科布局
    print("\n3. Get subject layouts (math)...")
    math_layouts = manager.get_subject_layouts('math')
    print(f"   Math layouts: {len(math_layouts)}")
    for l in math_layouts:
        print(f"     - {l.id}: {l.name}")

    return manager


def test_deck_manager():
    """测试套牌管理器"""
    print("\n" + "="*60)
    print("[TEST] Deck Manager")
    print("="*60)

    manager = DeckManager()

    # 测试列出套牌
    print("\n1. List decks...")
    decks = manager.list_decks()
    print(f"   Total decks: {len(decks)}")

    for d in decks:
        print(f"     - {d['id']}: {d['name']}")

    # 测试获取套牌
    print("\n2. Get deck...")
    math_deck = manager.get_deck('education_math')
    if math_deck:
        print(f"   Deck: {math_deck.name}")
        print(f"   Brand: {math_deck.brand.name if math_deck.brand else 'None'}")
        print(f"   Layouts: {len(math_deck.layouts)}")
        print(f"   Pages: {len(math_deck.page_structure)}")

    # 测试从内容创建套牌
    print("\n3. Create deck from content...")
    content = {
        'id': 'custom_math',
        'name': 'Custom Math Deck',
        'subject': 'math',
        'brand_id': 'math',
        'layout_ids': ['cover', 'toc', 'formula_step', 'exercise_steps', 'ending']
    }

    custom_deck = manager.create_deck_from_content(content)
    print(f"   Deck: {custom_deck.name}")
    print(f"   Brand: {custom_deck.brand.name if custom_deck.brand else 'None'}")
    print(f"   Layouts: {len(custom_deck.layouts)}")

    return manager


def main():
    """主测试函数"""
    print("[START] PPT Engine Phase 2 Test")
    print("="*60)

    try:
        # 1. 测试设计策略师
        project_path = test_strategist()

        # 2. 测试品牌管理器
        brand_manager = test_brand_manager()

        # 3. 测试布局管理器
        layout_manager = test_layout_manager()

        # 4. 测试套牌管理器
        deck_manager = test_deck_manager()

        print("\n" + "="*60)
        print("[DONE] All Phase 2 tests passed!")
        print("="*60)

        print(f"\n[PATH] Test project: {project_path}")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
