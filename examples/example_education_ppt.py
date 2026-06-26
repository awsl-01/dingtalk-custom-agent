"""
教育PPT生成示例
演示如何使用教育PPT生成功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.education_ppt_generator import (
    generate_education_ppt,
    generate_lesson_plan,
    generate_slide_outline,
    generate_lesson_speech,
    generate_teaching_reflection,
    create_lesson_plan_ppt,
    create_slide_outline_ppt,
    create_lesson_speech_ppt,
    create_teaching_reflection_ppt
)


def example_1_basic_lesson_plan():
    """示例1：生成基础教案"""
    print("=== 示例1：生成基础教案 ===")

    user_message = "请为高中数学《导数的概念》生成一份教案，难度中等，学生是理科班学生，基础较好"

    try:
        path, title = generate_education_ppt(user_message)
        print(f"✅ 教案生成成功！")
        print(f"   文件路径：{path}")
        print(f"   教案标题：{title}")
    except Exception as e:
        print(f"❌ 生成失败：{e}")

    print()


def example_2_slide_outline():
    """示例2：生成课件大纲"""
    print("=== 示例2：生成课件大纲 ===")

    user_message = "请为初中英语《一般过去时》生成课件大纲，风格活泼"

    try:
        path, title = generate_education_ppt(user_message)
        print(f"✅ 课件大纲生成成功！")
        print(f"   文件路径：{path}")
        print(f"   课件标题：{title}")
    except Exception as e:
        print(f"❌ 生成失败：{e}")

    print()


def example_3_lesson_speech():
    """示例3：生成说课稿"""
    print("=== 示例3：生成说课稿 ===")

    user_message = "请为小学语文《草船借箭》生成说课稿"

    try:
        path, title = generate_education_ppt(user_message)
        print(f"✅ 说课稿生成成功！")
        print(f"   文件路径：{path}")
        print(f"   说课稿标题：{title}")
    except Exception as e:
        print(f"❌ 生成失败：{e}")

    print()


def example_4_teaching_reflection():
    """示例4：生成教学反思"""
    print("=== 示例4：生成教学反思 ===")

    user_message = "请为高中物理《牛顿第二定律》生成教学反思"

    try:
        path, title = generate_education_ppt(user_message)
        print(f"✅ 教学反思生成成功！")
        print(f"   文件路径：{path}")
        print(f"   反思标题：{title}")
    except Exception as e:
        print(f"❌ 生成失败：{e}")

    print()


def example_5_difficulty_levels():
    """示例5：不同难度级别"""
    print("=== 示例5：不同难度级别 ===")

    difficulties = ["基础", "中等", "提高", "拓展"]

    for difficulty in difficulties:
        user_message = f"请为初中数学《一元二次方程》生成教案，难度{difficulty}"
        print(f"\n尝试生成难度：{difficulty}")

        try:
            path, title = generate_education_ppt(user_message)
            print(f"  ✅ {difficulty}难度教案生成成功！")
            print(f"     文件路径：{path}")
        except Exception as e:
            print(f"  ❌ 生成失败：{e}")

    print()


def example_6_custom_student_info():
    """示例6：自定义学情信息"""
    print("=== 示例6：自定义学情信息 ===")

    user_message = """请为小学数学《分数的初步认识》生成教案
学情：学生是三年级学生，刚接触分数概念，对整数运算比较熟悉
难度：基础
需要更多直观教具和动手操作活动"""

    try:
        path, title = generate_education_ppt(user_message)
        print(f"✅ 教案生成成功！")
        print(f"   文件路径：{path}")
        print(f"   教案标题：{title}")
    except Exception as e:
        print(f"❌ 生成失败：{e}")

    print()


def example_7_step_by_step():
    """示例7：分步骤生成"""
    print("=== 示例7：分步骤生成（高级用法） ===")

    try:
        # 步骤1：生成教案
        print("步骤1：生成教案...")
        lesson_plan = generate_lesson_plan(
            "高中化学《氧化还原反应》",
            "提高",
            "学生是重点班学生，化学基础扎实"
        )
        print(f"  ✅ 教案数据生成完成")

        # 步骤2：基于教案生成课件大纲
        print("步骤2：生成课件大纲...")
        slide_outline = generate_slide_outline(lesson_plan, "学术")
        print(f"  ✅ 课件大纲生成完成")

        # 步骤3：基于教案生成说课稿
        print("步骤3：生成说课稿...")
        lesson_speech = generate_lesson_speech(lesson_plan)
        print(f"  ✅ 说课稿生成完成")

        # 步骤4：基于教案生成教学反思
        print("步骤4：生成教学反思...")
        teaching_reflection = generate_teaching_reflection(lesson_plan)
        print(f"  ✅ 教学反思生成完成")

        # 步骤5：创建PPT文件
        print("步骤5：创建PPT文件...")

        # 创建教案PPT
        create_lesson_plan_ppt(lesson_plan, "projects/教案_氧化还原反应.pptx")
        print(f"  ✅ 教案PPT创建完成")

        # 创建课件大纲PPT
        create_slide_outline_ppt(slide_outline, "projects/课件大纲_氧化还原反应.pptx")
        print(f"  ✅ 课件大纲PPT创建完成")

        # 创建说课稿PPT
        create_lesson_speech_ppt(lesson_speech, "projects/说课稿_氧化还原反应.pptx")
        print(f"  ✅ 说课稿PPT创建完成")

        # 创建教学反思PPT
        create_teaching_reflection_ppt(teaching_reflection, "projects/教学反思_氧化还原反应.pptx")
        print(f"  ✅ 教学反思PPT创建完成")

        print(f"\n🎉 所有教学材料生成完成！")

    except Exception as e:
        print(f"❌ 生成失败：{e}")

    print()


def main():
    """主函数"""
    print("=" * 60)
    print("教育PPT生成示例程序")
    print("=" * 60)
    print()

    # 注意：以下示例需要配置正确的API密钥才能运行
    # 请确保.env文件中配置了OPENAI_API_KEY和OPENAI_BASE_URL

    print("提示：请确保已配置API密钥（.env文件）")
    print()

    # 运行示例
    # 取消注释以下行来运行相应的示例

    # example_1_basic_lesson_plan()
    # example_2_slide_outline()
    # example_3_lesson_speech()
    # example_4_teaching_reflection()
    # example_5_difficulty_levels()
    # example_6_custom_student_info()
    # example_7_step_by_step()

    print("=" * 60)
    print("使用说明：")
    print("=" * 60)
    print()
    print("1. 通过钉钉机器人使用：")
    print("   直接发送包含关键词的消息，例如：")
    print("   - '请为高中数学《导数的概念》生成教案'")
    print("   - '请为初中英语《一般过去时》生成课件'")
    print("   - '请为小学语文《草船借箭》生成说课稿'")
    print("   - '请为高中物理《牛顿第二定律》生成教学反思'")
    print()
    print("2. 通过Python代码使用：")
    print("   from agent.education_ppt_generator import generate_education_ppt")
    print("   path, title = generate_education_ppt('生成教案...')")
    print()
    print("3. 支持的难度级别：")
    print("   - 基础：面向学习困难学生")
    print("   - 中等：面向中等水平学生（默认）")
    print("   - 提高：面向学有余力学生")
    print("   - 拓展：面向学科特长生")
    print()
    print("4. 支持的功能类型：")
    print("   - 教案生成：包含完整教学设计")
    print("   - 课件大纲：课件内容框架")
    print("   - 说课稿：说课演讲稿")
    print("   - 教学反思：多维度反思分析")
    print()


if __name__ == "__main__":
    main()
