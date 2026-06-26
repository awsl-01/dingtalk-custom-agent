"""
模板PPT生成器使用示例
"""
import os
import sys
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.template_design_ppt import generate_template_ppt

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")

    # 模板路径
    template_path = "templates/default_template.pptx"

    # 检查模板是否存在
    if not os.path.exists(template_path):
        print(f"错误：模板文件不存在: {template_path}")
        print("请先运行 create_template.py 创建默认模板")
        return

    # 用户消息
    user_message = "生成一个关于人工智能发展趋势的PPT，包含：1. AI发展历程 2. 当前热点技术 3. 未来展望 4. 行业应用案例"

    # 输出目录
    output_dir = "projects"
    os.makedirs(output_dir, exist_ok=True)

    try:
        # 生成PPT
        output_path, title = generate_template_ppt(
            user_message=user_message,
            template_path=template_path,
            output_dir=output_dir
        )

        print(f"✓ PPT生成成功")
        print(f"  文件路径: {output_path}")
        print(f"  标题: {title}")
        print(f"  文件大小: {os.path.getsize(output_path) / 1024:.2f} KB")

    except Exception as e:
        print(f"✗ 生成失败: {e}")
        import traceback
        traceback.print_exc()


def example_custom_template():
    """自定义模板示例"""
    print("\n=== 自定义模板示例 ===")

    # 假设用户有自己的模板
    custom_template = "my_template.pptx"

    if not os.path.exists(custom_template):
        print(f"自定义模板不存在: {custom_template}")
        print("请提供您自己的.pptx模板文件")
        return

    user_message = "生成一个季度工作总结PPT"

    try:
        output_path, title = generate_template_ppt(
            user_message=user_message,
            template_path=custom_template,
            output_dir="output"
        )

        print(f"✓ 使用自定义模板生成成功")
        print(f"  文件路径: {output_path}")

    except Exception as e:
        print(f"✗ 生成失败: {e}")


def example_batch_generation():
    """批量生成示例"""
    print("\n=== 批量生成示例 ===")

    template_path = "templates/default_template.pptx"

    if not os.path.exists(template_path):
        print(f"模板文件不存在: {template_path}")
        return

    # 多个主题
    topics = [
        "2026年市场营销策略",
        "新产品发布计划",
        "团队建设活动方案",
        "财务年度报告"
    ]

    output_dir = "batch_output"
    os.makedirs(output_dir, exist_ok=True)

    for topic in topics:
        try:
            user_message = f"生成一个关于{topic}的PPT"
            output_path, title = generate_template_ppt(
                user_message=user_message,
                template_path=template_path,
                output_dir=output_dir
            )
            print(f"✓ {topic}: {output_path}")

        except Exception as e:
            print(f"✗ {topic}: {e}")


if __name__ == "__main__":
    print("模板PPT生成器使用示例")
    print("=" * 50)

    # 运行示例
    example_basic_usage()

    # 其他示例需要自定义模板或API配置
    # example_custom_template()
    # example_batch_generation()

    print("\n" + "=" * 50)
    print("示例完成")
