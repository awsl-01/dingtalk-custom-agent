"""
测试模板PPT生成功能
"""
import os
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.template_design_ppt import (
    TemplateDesignExtractor,
    TemplateDesignPPTGenerator,
    DesignGene,
    SlideLayoutType
)


def test_design_extraction():
    """测试设计基因提取"""
    template_path = "templates/default_template.pptx"

    if not os.path.exists(template_path):
        print(f"模板文件不存在: {template_path}")
        return

    print("=== 测试设计基因提取 ===")
    extractor = TemplateDesignExtractor(template_path)
    gene = extractor.extract()

    print(f"背景颜色: {gene.background_color}")
    print(f"标题字体: {gene.title_font_name}")
    print(f"标题字号: {gene.title_font_size}")
    print(f"标题颜色: {gene.title_font_color}")
    print(f"正文字体: {gene.body_font_name}")
    print(f"正文字号: {gene.body_font_size}")
    print(f"正文颜色: {gene.body_font_color}")
    print(f"强调色: {gene.accent_color}")
    print(f"有装饰线: {gene.has_accent_line}")
    print(f"有页码: {gene.has_page_number}")
    print()


def test_ppt_generation():
    """测试PPT生成"""
    template_path = "templates/default_template.pptx"
    output_dir = "test_output"

    if not os.path.exists(template_path):
        print(f"模板文件不存在: {template_path}")
        return

    print("=== 测试PPT生成 ===")
    generator = TemplateDesignPPTGenerator(template_path)

    # 测试内容
    test_content = "生成一个关于人工智能发展趋势的PPT，包含以下内容：1. AI发展历程 2. 当前热点技术 3. 未来展望 4. 行业应用案例"

    try:
        output_path, title = generator.generate(test_content, output_dir)
        print(f"PPT生成成功: {output_path}")
        print(f"标题: {title}")
    except Exception as e:
        print(f"生成失败: {e}")
        import traceback
        traceback.print_exc()


def test_layout_diversity():
    """测试版式多样性检查"""
    from agent.template_design_ppt import LayoutDiversityChecker, SlideContent

    print("=== 测试版式多样性检查 ===")
    checker = LayoutDiversityChecker()

    # 模拟连续3个相同版式
    layouts = ["content", "content", "content"]
    for i, layout in enumerate(layouts):
        content = SlideContent(title=f"第{i+1}页", content=["测试内容"])
        result = checker.check_and_fix_layout(layout, content)
        print(f"原始版式: {layout} -> 调整后: {result}")


def test_text_overflow():
    """测试文字溢出检查"""
    from agent.template_design_ppt import TextOverflowChecker, DesignGene

    print("=== 测试文字溢出检查 ===")
    gene = DesignGene()
    checker = TextOverflowChecker(gene)

    # 测试内容
    short_text = "这是一个简短的测试"
    long_text = "这是一段非常长的测试内容，用于验证文字溢出检查功能是否正常工作。" * 10

    print(f"短文本预计行数: {len(short_text) // 30 + 1}")
    print(f"长文本预计行数: {len(long_text) // 30 + 1}")


if __name__ == "__main__":
    # 创建输出目录
    os.makedirs("test_output", exist_ok=True)

    # 运行测试
    test_design_extraction()
    print()
    test_layout_diversity()
    print()
    test_text_overflow()
    print()

    # 注意：PPT生成测试需要配置API密钥
    # test_ppt_generation()

    print("=== 测试完成 ===")
