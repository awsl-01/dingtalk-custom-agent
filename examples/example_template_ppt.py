"""
模板PPT生成示例
展示如何使用模板设计基因生成风格统一的PPT
"""
import os
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.template_design_ppt import generate_template_ppt


def main():
    """主函数"""
    # 检查模板文件
    template_path = "templates/default_template.pptx"
    if not os.path.exists(template_path):
        print(f"错误：模板文件不存在: {template_path}")
        print("请先运行 create_template.py 创建默认模板")
        return

    # 示例1：生成商业PPT
    print("=== 示例1：生成商业PPT ===")
    try:
        output_path, title = generate_template_ppt(
            user_message="生成一个关于2026年市场营销策略的PPT，包含以下内容：1. 市场分析 2. 目标客户 3. 营销渠道 4. 预算规划 5. 预期效果",
            template_path=template_path,
            output_dir="projects"
        )
        print(f"✓ 生成成功: {output_path}")
        print(f"  标题: {title}")
    except Exception as e:
        print(f"✗ 生成失败: {e}")

    print()

    # 示例2：生成教育PPT
    print("=== 示例2：生成教育PPT ===")
    try:
        output_path, title = generate_template_ppt(
            user_message="生成一个关于初中物理《力与运动》的课件PPT，包含：1. 力的概念 2. 力的三要素 3. 牛顿第一定律 4. 实验演示 5. 课堂练习",
            template_path=template_path,
            output_dir="projects"
        )
        print(f"✓ 生成成功: {output_path}")
        print(f"  标题: {title}")
    except Exception as e:
        print(f"✗ 生成失败: {e}")

    print()

    # 示例3：生成技术分享PPT
    print("=== 示例3：生成技术分享PPT ===")
    try:
        output_path, title = generate_template_ppt(
            user_message="生成一个关于Python异步编程的技术分享PPT，包含：1. 异步编程概念 2. asyncio基础 3. 常用模式 4. 性能优化 5. 实际案例",
            template_path=template_path,
            output_dir="projects"
        )
        print(f"✓ 生成成功: {output_path}")
        print(f"  标题: {title}")
    except Exception as e:
        print(f"✗ 生成失败: {e}")


if __name__ == "__main__":
    # 创建输出目录
    os.makedirs("projects", exist_ok=True)

    # 运行示例
    main()

    print()
    print("=== 所有示例完成 ===")
    print("生成的PPT文件位于 projects 目录")
