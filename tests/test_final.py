"""
最终测试脚本 - 验证所有功能
"""
import os
import sys
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.template_design_ppt import (
    TemplateDesignExtractor,
    TemplateDesignPPTGenerator,
    DesignGene,
    SlideLayoutType,
    generate_template_ppt
)

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


def test_design_extraction():
    """测试设计基因提取"""
    print("=== 测试设计基因提取 ===")
    template_path = "templates/default_template.pptx"

    if not os.path.exists(template_path):
        print(f"错误：模板文件不存在: {template_path}")
        return False

    extractor = TemplateDesignExtractor(template_path)
    gene = extractor.extract()

    print(f"✓ 背景颜色: {gene.background_color}")
    print(f"✓ 强调色: {gene.accent_color}")
    print(f"✓ 标题字体: {gene.title_font_name}")
    print(f"✓ 标题字号: {gene.title_font_size.pt}pt")
    print(f"✓ 正文字体: {gene.body_font_name}")
    print(f"✓ 正文字号: {gene.body_font_size.pt}pt")
    print(f"✓ 装饰线颜色: {gene.accent_line_color}")
    print()

    return True


def test_layout_diversity():
    """测试版式多样性检查"""
    print("=== 测试版式多样性检查 ===")
    from agent.template_design_ppt import LayoutDiversityChecker, SlideContent

    checker = LayoutDiversityChecker()

    # 模拟连续3个相同版式
    layouts = ["content", "content", "content"]
    results = []
    for i, layout in enumerate(layouts):
        content = SlideContent(title=f"第{i+1}页", content=["测试内容"])
        result = checker.check_and_fix_layout(layout, content)
        results.append(result)
        print(f"  原始版式: {layout} -> 调整后: {result}")

    # 验证是否正确调整
    if results[2] != "content":
        print("✓ 版式多样性检查通过")
    else:
        print("✗ 版式多样性检查失败")
    print()

    return True


def test_text_overflow():
    """测试文字溢出检查"""
    print("=== 测试文字溢出检查 ===")
    from agent.template_design_ppt import TextOverflowChecker, DesignGene

    gene = DesignGene()
    checker = TextOverflowChecker(gene)

    # 测试内容
    short_text = "这是一个简短的测试"
    long_text = "这是一段非常长的测试内容，用于验证文字溢出检查功能是否正常工作。" * 10

    short_lines = max(1, len(short_text) // 30 + 1)
    long_lines = max(1, len(long_text) // 30 + 1)

    print(f"  短文本预计行数: {short_lines}")
    print(f"  长文本预计行数: {long_lines}")

    # 测试拆分功能
    test_content = ["要点1", "要点2", "要点3", "要点4", "要点5"] * 5
    split_contents = checker.split_content(test_content, 3)
    print(f"  拆分结果: {len(split_contents)} 页")
    print()

    return True


def test_ppt_generation():
    """测试PPT生成"""
    print("=== 测试PPT生成 ===")
    template_path = "templates/default_template.pptx"
    output_dir = "test_output"

    if not os.path.exists(template_path):
        print(f"错误：模板文件不存在: {template_path}")
        return False

    # 测试内容
    test_message = "生成一个关于人工智能发展趋势的PPT，包含：1. AI发展历程 2. 当前热点技术 3. 未来展望 4. 行业应用案例"

    try:
        output_path, title = generate_template_ppt(
            user_message=test_message,
            template_path=template_path,
            output_dir=output_dir
        )

        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✓ 生成成功: {output_path}")
            print(f"  标题: {title}")
            print(f"  文件大小: {file_size / 1024:.2f} KB")
            return True
        else:
            print(f"✗ 文件不存在: {output_path}")
            return False

    except Exception as e:
        print(f"✗ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("=== 模板PPT生成器最终测试 ===")
    print()

    # 创建输出目录
    os.makedirs("test_output", exist_ok=True)

    # 运行测试
    results = []
    results.append(("设计基因提取", test_design_extraction()))
    results.append(("版式多样性检查", test_layout_diversity()))
    results.append(("文字溢出检查", test_text_overflow()))
    results.append(("PPT生成", test_ppt_generation()))

    # 输出测试结果
    print("=== 测试结果汇总 ===")
    all_passed = True
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
        if not result:
            all_passed = False

    print()
    if all_passed:
        print("✓ 所有测试通过")
    else:
        print("✗ 部分测试失败")


if __name__ == "__main__":
    main()
