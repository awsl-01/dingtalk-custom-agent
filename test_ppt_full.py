"""
PPT 完整生成测试
测试完整的 PPT 生成流程
"""
import sys
import os
import logging
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def test_full_ppt_generation():
    """测试完整的 PPT 生成流程"""
    logger.info("=== 开始完整 PPT 生成测试 ===")

    try:
        from agent.ppt_master_integration import generate_ppt_with_master

        # 测试参数
        topic = "二次函数"
        subject = "数学"
        grade = "初中"
        page_count = 5  # 使用较少的页数进行快速测试

        logger.info(f"主题: {topic}")
        logger.info(f"学科: {subject}")
        logger.info(f"年级: {grade}")
        logger.info(f"页数: {page_count}")

        start_time = time.time()

        # 调用 PPT 生成
        pptx_path, title = generate_ppt_with_master(
            topic=topic,
            subject=subject,
            grade=grade,
            page_count=page_count,
        )

        elapsed = time.time() - start_time
        logger.info(f"PPT 生成完成!")
        logger.info(f"文件路径: {pptx_path}")
        logger.info(f"标题: {title}")
        logger.info(f"耗时: {elapsed:.2f} 秒")

        # 检查文件是否存在
        if os.path.exists(pptx_path):
            file_size = os.path.getsize(pptx_path)
            logger.info(f"文件大小: {file_size} 字节")
            return True, pptx_path
        else:
            logger.error(f"文件不存在: {pptx_path}")
            return False, None

    except Exception as e:
        logger.error(f"PPT 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_svg_generation_only():
    """仅测试 SVG 生成（不进行后处理）"""
    logger.info("=== 测试 SVG 生成 ===")

    try:
        from agent.ppt_master_integration import (
            create_project,
            generate_design_spec,
            generate_spec_lock,
            plan_pages_with_ai,
            generate_svg_with_executor,
            read_spec_files,
            read_template_svgs,
            get_subject_theme,
        )

        # 测试参数
        topic = "二次函数"
        subject = "数学"
        grade = "初中"
        page_count = 3

        # 1. 选择配色
        theme = get_subject_theme(subject)
        logger.info(f"配色主题: {theme['primary']}")

        # 2. AI 规划页面
        logger.info("AI 规划页面...")
        page_specs = plan_pages_with_ai(topic, subject, grade, "", "", page_count)
        logger.info(f"规划了 {len(page_specs)} 页")

        # 3. 创建项目
        project_name = f"svg_test_{subject}_{topic}"
        project_path = create_project(project_name)
        logger.info(f"项目路径: {project_path}")

        # 4. 生成设计规范
        generate_design_spec(project_path, topic, page_specs, theme, subject, grade)
        generate_spec_lock(project_path, topic, page_specs, theme)
        logger.info("设计规范已生成")

        # 5. 读取规范文件
        spec_lock_content, design_spec_content = read_spec_files(project_path)
        template_svgs = read_template_svgs()

        # 6. 测试单页 SVG 生成
        if page_specs:
            test_spec = page_specs[0]
            logger.info(f"测试生成第 1 页: {test_spec.get('title', '未知')}")

            start_time = time.time()
            svg_content = generate_svg_with_executor(
                page_spec=test_spec,
                page_num=1,
                total=len(page_specs),
                spec_lock_content=spec_lock_content,
                design_spec_content=design_spec_content,
                theme=theme,
                topic=topic,
                subject=subject,
                search_context="",
                template_svgs=template_svgs,
                available_images=[],
                previous_svgs=[],
                strict_mode=True,
            )
            elapsed = time.time() - start_time

            logger.info(f"SVG 生成完成!")
            logger.info(f"SVG 长度: {len(svg_content)} 字节")
            logger.info(f"耗时: {elapsed:.2f} 秒")

            # 保存 SVG 文件
            svg_path = Path(project_path) / "test_output.svg"
            svg_path.write_text(svg_content, encoding='utf-8')
            logger.info(f"SVG 已保存到: {svg_path}")

            # 验证 SVG
            from agent.ppt_master_integration import validate_svg_strict
            is_valid, error = validate_svg_strict(svg_content, test_spec, theme)
            logger.info(f"SVG 验证: {'✓ 有效' if is_valid else '✗ 无效'} - {error}")

            return True, str(svg_path)

        return False, None

    except Exception as e:
        logger.error(f"SVG 生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def main():
    """主测试函数"""
    logger.info("开始 PPT 完整生成测试")

    # 测试 1: 仅 SVG 生成
    logger.info("\n" + "="*60)
    svg_success, svg_path = test_svg_generation_only()

    # 测试 2: 完整 PPT 生成
    logger.info("\n" + "="*60)
    ppt_success, ppt_path = test_full_ppt_generation()

    # 输出结果
    logger.info("\n" + "="*60)
    logger.info("=== 测试结果汇总 ===")
    logger.info(f"SVG 生成: {'✓ 通过' if svg_success else '✗ 失败'}")
    logger.info(f"PPT 生成: {'✓ 通过' if ppt_success else '✗ 失败'}")

    if ppt_success:
        logger.info(f"\n生成的 PPT 文件: {ppt_path}")

    return 0 if ppt_success else 1


if __name__ == "__main__":
    sys.exit(main())
