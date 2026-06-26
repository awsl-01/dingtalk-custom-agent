"""
PPT 生成调试脚本
用于分析 PPT 生成过程中的问题
"""
import sys
import os
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def test_import():
    """测试模块导入"""
    logger.info("=== 测试模块导入 ===")
    try:
        from agent.ppt_master_integration import (
            generate_ppt_with_master,
            validate_svg,
            validate_svg_strict,
            repair_svg,
            clean_svg_output,
        )
        logger.info("✓ PPT 模块导入成功")
        return True
    except Exception as e:
        logger.error(f"✗ PPT 模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_svg_validation():
    """测试 SVG 验证功能"""
    logger.info("=== 测试 SVG 验证 ===")

    from agent.ppt_master_integration import validate_svg, validate_svg_strict, repair_svg

    # 测试用例 1: 有效的 SVG
    valid_svg = '''<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg">
        <rect width="1280" height="720" fill="#FFFFFF"/>
        <text x="640" y="360" text-anchor="middle" font-size="24" fill="#333">测试页面</text>
    </svg>'''

    is_valid, error = validate_svg(valid_svg)
    logger.info(f"有效 SVG 验证: {'✓' if is_valid else '✗'} - {error}")

    is_valid_strict, error_strict = validate_svg_strict(valid_svg)
    logger.info(f"严格验证: {'✓' if is_valid_strict else '✗'} - {error_strict}")

    # 测试用例 2: 包含 HTML 实体的 SVG
    svg_with_entities = '''<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg">
        <rect width="1280" height="720" fill="#FFFFFF"/>
        <text x="640" y="360" text-anchor="middle" font-size="24" fill="#333">测试 &mdash; 页面</text>
    </svg>'''

    is_valid2, error2 = validate_svg(svg_with_entities)
    logger.info(f"包含实体的 SVG: {'✓' if is_valid2 else '✗'} - {error2}")

    # 测试修复功能
    repaired = repair_svg(svg_with_entities, {'title': '测试'}, {'primary': '#1A5276'})
    is_valid3, error3 = validate_svg(repaired)
    logger.info(f"修复后的 SVG: {'✓' if is_valid3 else '✗'} - {error3}")

    # 测试用例 3: 无效的 SVG（缺少闭合标签）
    invalid_svg = '''<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg">
        <rect width="1280" height="720" fill="#FFFFFF"/>
    '''

    is_valid4, error4 = validate_svg(invalid_svg)
    logger.info(f"无效 SVG 检测: {'✓' if not is_valid4 else '✗'} - {error4}")

    return True


def test_simple_ppt_generation():
    """测试简单的 PPT 生成（使用最小配置）"""
    logger.info("=== 测试简单 PPT 生成 ===")

    try:
        from agent.ppt_master_integration import (
            create_project,
            generate_design_spec,
            generate_spec_lock,
            plan_pages_with_ai,
        )

        # 创建测试项目
        project_name = "test_debug_project"
        project_path = create_project(project_name)
        logger.info(f"项目路径: {project_path}")

        # 测试 AI 页面规划
        topic = "测试主题"
        subject = "数学"
        grade = "初中"

        logger.info("测试 AI 页面规划...")
        page_specs = plan_pages_with_ai(topic, subject, grade, "", "", 3)
        logger.info(f"规划了 {len(page_specs)} 页")

        for i, spec in enumerate(page_specs, 1):
            logger.info(f"  第 {i} 页: {spec.get('title', '未知')} ({spec.get('layout', '未知')})")

        return True

    except Exception as e:
        logger.error(f"PPT 生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    logger.info("开始 PPT 生成调试测试")

    results = []

    # 测试 1: 模块导入
    results.append(("模块导入", test_import()))

    # 测试 2: SVG 验证
    results.append(("SVG 验证", test_svg_validation()))

    # 测试 3: 简单 PPT 生成
    results.append(("简单 PPT 生成", test_simple_ppt_generation()))

    # 输出结果汇总
    logger.info("\n=== 测试结果汇总 ===")
    for name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        logger.info(f"{name}: {status}")

    all_passed = all(success for _, success in results)
    logger.info(f"\n总体结果: {'✓ 全部通过' if all_passed else '✗ 存在失败'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
