"""
测试教育PPT生成功能
"""

import os
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.education_ppt_generator import (
    generate_education_ppt,
    generate_lesson_plan,
    create_lesson_plan_ppt
)


def test_basic_generation():
    """测试基础生成功能"""
    print("Testing basic generation...")

    # 测试教案生成
    test_message = "请为高中数学《导数的概念》生成教案，难度中等"

    try:
        # 生成教案数据
        lesson_plan = generate_lesson_plan(test_message, "中等")
        print(f"Lesson plan generated successfully")
        print(f"Title: {lesson_plan.get('title', 'N/A')}")
        print(f"Subject: {lesson_plan.get('subject', 'N/A')}")
        print(f"Grade: {lesson_plan.get('grade', 'N/A')}")

        # 创建测试输出目录
        os.makedirs("test_output", exist_ok=True)

        # 生成PPT
        output_path = "test_output/test_lesson_plan.pptx"
        create_lesson_plan_ppt(lesson_plan, output_path)

        print(f"PPT created successfully: {output_path}")
        print(f"File size: {os.path.getsize(output_path)} bytes")

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False


def test_difficulty_levels():
    """测试不同难度级别"""
    print("\nTesting difficulty levels...")

    difficulties = ["基础", "中等", "提高", "拓展"]

    for difficulty in difficulties:
        print(f"\nTesting difficulty: {difficulty}")

        try:
            lesson_plan = generate_lesson_plan(
                f"初中数学《一元二次方程》难度{difficulty}",
                difficulty
            )

            print(f"  Title: {lesson_plan.get('title', 'N/A')}")
            print(f"  Difficulty: {lesson_plan.get('difficulty_level', 'N/A')}")

            # 检查学情分析
            student_analysis = lesson_plan.get('student_analysis', {})
            print(f"  Student level: {student_analysis.get('level', 'N/A')[:50]}...")

        except Exception as e:
            print(f"  Error: {e}")


def test_complete_flow():
    """测试完整流程"""
    print("\nTesting complete flow...")

    test_message = "请为小学语文《草船借箭》生成教案，难度基础，学生是三年级学生"

    try:
        path, title = generate_education_ppt(test_message, "test_output")
        print(f"Complete generation successful!")
        print(f"Path: {path}")
        print(f"Title: {title}")
        print(f"File exists: {os.path.exists(path)}")

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("Education PPT Generation Test")
    print("=" * 60)

    # 运行测试
    test1 = test_basic_generation()
    test2 = test_complete_flow()

    print("\n" + "=" * 60)
    print("Test Results:")
    print(f"  Basic generation: {'PASS' if test1 else 'FAIL'}")
    print(f"  Complete flow: {'PASS' if test2 else 'FAIL'}")
    print("=" * 60)

    # 清理测试文件
    print("\nCleaning up test files...")
    import shutil
    if os.path.exists("test_output"):
        shutil.rmtree("test_output")
        print("Test files cleaned up")


if __name__ == "__main__":
    main()
