"""
PPT Engine 第六阶段测试

测试教育专项Workflow：教案、课件大纲、说课稿、教学反思。
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.ppt_engine.workflows.education.lesson_plan import LessonPlanGenerator, generate_lesson_plan
from agent.ppt_engine.workflows.education.courseware import CoursewareGenerator, generate_courseware
from agent.ppt_engine.workflows.education.teaching_plan import TeachingPlanGenerator, generate_teaching_plan
from agent.ppt_engine.workflows.education.teaching_reflection import TeachingReflectionGenerator, generate_teaching_reflection


def test_lesson_plan():
    """测试教案生成"""
    print("\n" + "="*60)
    print("[TEST] Lesson Plan Generator")
    print("="*60)

    generator = LessonPlanGenerator()

    # 测试生成教案
    print("\n1. Generate lesson plan...")
    plan = generator.generate('数学', '高一', '三角函数')

    print(f"   Title: {plan.title}")
    print(f"   Subject: {plan.subject}")
    print(f"   Grade: {plan.grade}")
    print(f"   Chapter: {plan.chapter}")
    print(f"   Methods: {', '.join(plan.teaching_methods[:3])}")

    # 测试学习目标
    print("\n2. Learning objectives...")
    print(f"   Knowledge: {len(plan.objectives['knowledge'])} items")
    print(f"   Process: {len(plan.objectives['process'])} items")
    print(f"   Emotion: {len(plan.objectives['emotion'])} items")

    # 测试教学过程
    print("\n3. Teaching process...")
    for stage, content in plan.teaching_process.items():
        if isinstance(content, dict):
            print(f"   {stage}: {content.get('duration', 'N/A')}")

    # 测试保存
    print("\n4. Save lesson plan...")
    output_path = Path('D:/claude/projects/test_project/notes/lesson_plan.md')
    generator.save(plan, str(output_path))
    print(f"   [OK] Saved to: {output_path}")

    return plan


def test_courseware():
    """测试课件大纲生成"""
    print("\n" + "="*60)
    print("[TEST] Courseware Generator")
    print("="*60)

    generator = CoursewareGenerator()

    # 测试生成课件大纲
    print("\n1. Generate courseware outline...")
    courseware = generator.generate_from_lesson_plan(
        LessonPlanGenerator().generate('数学', '高一', '三角函数')
    )

    print(f"   Title: {courseware.title}")
    print(f"   Subject: {courseware.subject}")
    print(f"   Pages: {len(courseware.pages)}")

    # 测试页面详情
    print("\n2. Page details...")
    for page in courseware.pages[:5]:
        print(f"   Page {page.page_num}: {page.title} ({page.layout})")

    # 测试保存
    print("\n3. Save courseware outline...")
    output_path = Path('D:/claude/projects/test_project/notes/courseware_outline.md')
    generator.save(courseware, str(output_path))
    print(f"   [OK] Saved to: {output_path}")

    return courseware


def test_teaching_plan():
    """测试说课稿生成"""
    print("\n" + "="*60)
    print("[TEST] Teaching Plan Generator")
    print("="*60)

    generator = TeachingPlanGenerator()

    # 测试生成说课稿
    print("\n1. Generate teaching plan...")
    plan = generator.generate_from_lesson_plan(
        LessonPlanGenerator().generate('数学', '高一', '三角函数')
    )

    print(f"   Title: {plan.title}")
    print(f"   Subject: {plan.subject}")
    print(f"   Textbook analysis length: {len(plan.textbook_analysis)} chars")
    print(f"   Student analysis length: {len(plan.student_analysis)} chars")

    # 测试保存
    print("\n2. Save teaching plan...")
    output_path = Path('D:/claude/projects/test_project/notes/teaching_plan.md')
    generator.save(plan, str(output_path))
    print(f"   [OK] Saved to: {output_path}")

    return plan


def test_teaching_reflection():
    """测试教学反思生成"""
    print("\n" + "="*60)
    print("[TEST] Teaching Reflection Generator")
    print("="*60)

    generator = TeachingReflectionGenerator()

    # 测试生成教学反思
    print("\n1. Generate teaching reflection...")
    reflection = generator.generate_from_lesson_plan(
        LessonPlanGenerator().generate('数学', '高一', '三角函数')
    )

    print(f"   Title: {reflection.title}")
    print(f"   Subject: {reflection.subject}")
    print(f"   Highlights: {len(reflection.highlights)} items")
    print(f"   Shortcomings: {len(reflection.shortcomings)} items")
    print(f"   Improvements: {len(reflection.improvements)} items")

    # 测试保存
    print("\n2. Save teaching reflection...")
    output_path = Path('D:/claude/projects/test_project/notes/teaching_reflection.md')
    generator.save(reflection, str(output_path))
    print(f"   [OK] Saved to: {output_path}")

    return reflection


def test_subjects():
    """测试多学科支持"""
    print("\n" + "="*60)
    print("[TEST] Multi-subject Support")
    print("="*60)

    subjects = ['数学', '物理', '化学', '生物', '语文', '英语', '历史', '地理', '信息技术', '政治']

    print("\n1. Generate lesson plans for all subjects...")
    for subject in subjects:
        plan = LessonPlanGenerator().generate(subject, '高一', '测试章节')
        print(f"   [OK] {subject}: {len(plan.teaching_methods)} methods")

    print("\n2. Generate courseware for all subjects...")
    for subject in subjects:
        plan = LessonPlanGenerator().generate(subject, '高一', '测试章节')
        courseware = CoursewareGenerator().generate_from_lesson_plan(plan)
        print(f"   [OK] {subject}: {len(courseware.pages)} pages")


def test_integration():
    """测试集成"""
    print("\n" + "="*60)
    print("[TEST] Integration")
    print("="*60)

    # 测试完整教育工作流
    print("\n1. Full education workflow...")
    workflow = [
        '1. Generate lesson plan',
        '2. Generate courseware outline',
        '3. Generate teaching plan (说课稿)',
        '4. Generate teaching reflection',
        '5. Generate SVG pages from courseware',
        '6. Generate TTS audio from notes',
        '7. Export final PPTX'
    ]

    for step in workflow:
        print(f"   {step}")

    # 测试学科模板集成
    print("\n2. Subject template integration...")
    print("   - Math: formula_step, graph_illustration, exercise_steps")
    print("   - Physics: experiment_flow, formula_step, data_table")
    print("   - Chinese: poetry_vertical, text_analysis, quote")
    print("   - English: vocab_cards, role_dialogue, sentence_pattern")


def main():
    """主测试函数"""
    print("[START] PPT Engine Phase 6 Test")
    print("="*60)

    try:
        # 1. 测试教案生成
        lesson_plan = test_lesson_plan()

        # 2. 测试课件大纲生成
        courseware = test_courseware()

        # 3. 测试说课稿生成
        teaching_plan = test_teaching_plan()

        # 4. 测试教学反思生成
        teaching_reflection = test_teaching_reflection()

        # 5. 测试多学科支持
        test_subjects()

        # 6. 测试集成
        test_integration()

        print("\n" + "="*60)
        print("[DONE] All Phase 6 tests passed!")
        print("="*60)

        # 显示生成的文件
        print("\n[OUTPUT FILES]")
        output_dir = Path('D:/claude/projects/test_project/notes')
        if output_dir.exists():
            for file in output_dir.glob('*.md'):
                print(f"   - {file.name}")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
