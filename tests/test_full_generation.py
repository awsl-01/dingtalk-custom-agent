"""
完整测试模板PPT生成功能
"""
import os
import sys
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.template_design_ppt import generate_template_ppt

# 强制使用UTF-8编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


def test_full_generation():
    """测试完整PPT生成流程"""
    template_path = "templates/default_template.pptx"
    output_dir = "test_output"

    if not os.path.exists(template_path):
        print(f"错误：模板文件不存在: {template_path}")
        return

    print("=== 测试完整PPT生成 ===")

    # 测试内容
    test_cases = [
        {
            "name": "商业PPT",
            "message": "生成一个关于2026年市场营销策略的PPT，包含以下内容：1. 市场分析 2. 目标客户 3. 营销渠道 4. 预算规划 5. 预期效果"
        },
        {
            "name": "教育PPT",
            "message": "生成一个关于初中物理《力与运动》的课件PPT，包含：1. 力的概念 2. 力的三要素 3. 牛顿第一定律 4. 实验演示 5. 课堂练习"
        }
    ]

    for test_case in test_cases:
        print(f"\n--- 测试: {test_case['name']} ---")
        try:
            output_path, title = generate_template_ppt(
                user_message=test_case['message'],
                template_path=template_path,
                output_dir=output_dir
            )
            print(f"✓ 生成成功: {output_path}")
            print(f"  标题: {title}")

            # 验证生成的文件
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"  文件大小: {file_size / 1024:.2f} KB")
            else:
                print(f"✗ 文件不存在")

        except Exception as e:
            print(f"✗ 生成失败: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    # 创建输出目录
    os.makedirs("test_output", exist_ok=True)

    # 运行测试
    test_full_generation()

    print("\n=== 测试完成 ===")
