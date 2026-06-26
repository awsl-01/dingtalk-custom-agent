"""
PPT Engine 第一阶段测试

测试项目管理、源文件处理、SVG生成、SVG转PPTX功能。
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.ppt_engine.project_manager import (
    init_project, import_sources, validate_project, get_project_info,
    CANVAS_FORMATS
)
from agent.ppt_engine.source_converter.source_to_md import SourceToMarkdown, convert_source
from agent.ppt_engine.svg_generator.page_builder import PageBuilder, build_page
from agent.ppt_engine.svg_to_pptx.pptx_builder import PPTXBuilder
from agent.ppt_engine.quality.svg_quality_checker import SVGQualityChecker
from agent.ppt_engine.animations.animation_config import AnimationConfig, TransitionType


def test_project_manager():
    """测试项目管理模块"""
    print("\n" + "="*60)
    print("[TEST] Project Manager")
    print("="*60)

    # 测试创建项目
    print("\n1. Create project...")
    project_dir = init_project('test_project', 'ppt169')
    print(f"   Path: {project_dir}")

    # 验证项目结构
    print("\n2. Validate project...")
    result = validate_project(str(project_dir))
    if result['valid']:
        print("   [OK] Validation passed")
    else:
        print(f"   [FAIL] Validation failed: {result['issues']}")

    # 获取项目信息
    print("\n3. Get project info...")
    info = get_project_info(str(project_dir))
    print(f"   Name: {info['name']}")
    print(f"   Canvas: {info['canvas']['name']}")
    print(f"   Size: {info['canvas']['width']}x{info['canvas']['height']}")

    return project_dir


def test_svg_generator(project_path: str):
    """测试SVG生成模块"""
    print("\n" + "="*60)
    print("[TEST] SVG Generator")
    print("="*60)

    # 测试生成封面页
    print("\n1. Generate cover page...")
    cover_content = {
        'title': 'PPT Engine Test',
        'subtitle': 'Phase 1 Verification',
        'layout': 'cover',
        'author': 'School AI Assistant',
        'date': '2026-06-04'
    }

    page = build_page(project_path, 1, cover_content)
    print(f"   Page: {page.page_num}")
    print(f"   Layout: {page.layout}")
    print(f"   SVG length: {len(page.svg_content)} chars")

    # 测试生成内容页
    print("\n2. Generate content page...")
    content_page = {
        'title': 'Feature Overview',
        'layout': 'three_card',
        'cards': [
            {'title': 'Project Manager', 'content': 'Create and manage PPT projects'},
            {'title': 'Source Converter', 'content': 'Support PDF/DOCX/HTML formats'},
            {'title': 'SVG Generator', 'content': 'Hand-write SVG per page'}
        ]
    }

    page2 = build_page(project_path, 2, content_page)
    print(f"   Page: {page2.page_num}")
    print(f"   Layout: {page2.layout}")

    # 保存SVG
    print("\n3. Save SVG files...")
    svg_dir = Path(project_path) / 'svg_output'
    svg_dir.mkdir(parents=True, exist_ok=True)

    page.save(str(svg_dir))
    page2.save(str(svg_dir))

    print(f"   Directory: {svg_dir}")
    print(f"   SVG count: {len(list(svg_dir.glob('*.svg')))}")

    return svg_dir


def test_quality_checker(project_path: str):
    """测试质量检查模块"""
    print("\n" + "="*60)
    print("[TEST] Quality Checker")
    print("="*60)

    svg_dir = Path(project_path) / 'svg_output'
    spec_lock = Path(project_path) / 'spec_lock.md'

    checker = SVGQualityChecker(str(spec_lock))

    print("\n1. Check SVG files...")
    issues = checker.check_directory(str(svg_dir))

    summary = checker.get_summary(issues)
    print(f"   Total issues: {summary['total']}")
    print(f"   Errors: {summary['errors']}")
    print(f"   Warnings: {summary['warnings']}")
    print(f"   Info: {summary['info']}")
    print(f"   Passed: {'Yes' if summary['passed'] else 'No'}")

    if issues:
        print("\n2. Issue details:")
        for issue in issues[:5]:  # 只显示前5个
            print(f"   {issue}")


def test_pptx_builder(project_path: str):
    """测试PPTX构建模块"""
    print("\n" + "="*60)
    print("[TEST] PPTX Builder")
    print("="*60)

    svg_dir = Path(project_path) / 'svg_output'

    print("\n1. Create PPTX builder...")
    builder = PPTXBuilder('ppt169')

    print("\n2. Add SVG slides...")
    svg_files = sorted(svg_dir.glob('*.svg'))

    for svg_file in svg_files:
        success = builder.add_svg_slide(str(svg_file))
        print(f"   {'[OK]' if success else '[FAIL]'} {svg_file.name}")

    # 保存PPTX
    print("\n3. Save PPTX file...")
    exports_dir = Path(project_path) / 'exports'
    exports_dir.mkdir(parents=True, exist_ok=True)

    output_path = exports_dir / 'test_output.pptx'
    builder.save(str(output_path))

    print(f"   Output: {output_path}")
    print(f"   Size: {output_path.stat().st_size / 1024:.1f} KB")


def test_animation_config():
    """测试动画配置模块"""
    print("\n" + "="*60)
    print("[TEST] Animation Config")
    print("="*60)

    print("\n1. Test animation effect selection...")
    test_cases = [
        ('title-01', 'auto'),
        ('card-01', 'auto'),
        ('chart-01', 'auto'),
        ('image-01', 'auto'),
        ('hero-01', 'auto'),
    ]

    for group_id, mode in test_cases:
        effect = AnimationConfig.pick_effect(group_id, mode)
        print(f"   {group_id} -> {effect.value}")

    print("\n2. Test transition effects...")
    for t_type in ['fade', 'push', 'wipe', 'split']:
        transition = AnimationConfig.create_transition(t_type)
        print(f"   {t_type} -> {transition.type.value}")


def main():
    """主测试函数"""
    print("[START] PPT Engine Phase 1 Test")
    print("="*60)

    try:
        # 1. 测试项目管理
        project_dir = test_project_manager()

        # 2. 测试SVG生成
        svg_dir = test_svg_generator(str(project_dir))

        # 3. 测试质量检查
        test_quality_checker(str(project_dir))

        # 4. 测试PPTX构建
        test_pptx_builder(str(project_dir))

        # 5. 测试动画配置
        test_animation_config()

        print("\n" + "="*60)
        print("[DONE] All tests passed!")
        print("="*60)

        print(f"\n[PATH] Test project: {project_dir}")
        print(f"[PATH] SVG files: {svg_dir}")
        print(f"[PATH] PPTX files: {Path(project_dir) / 'exports'}")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
