"""
排课系统完整测试脚本

测试流程：
1. 创建测试数据
2. 执行自动排课
3. 查看排课结果
4. 生成课表图片
"""
import sys
import os
import json
import logging

# 强制使用 UTF-8 编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def test_scheduling():
    """测试完整排课流程"""
    from agent.skills.scheduling import (
        ScheduleAlgorithm, SchedulingTask,
        ConstraintManager, Teacher, Classroom, Course, ClassGroup,
        Schedule, Weekday, TimeSlot,
    )

    print("=" * 60)
    print("📚 排课系统完整测试")
    print("=" * 60)

    # ── 1. 创建测试数据 ──
    print("\n【步骤 1】创建测试数据...")

    # 班级
    classes = {
        "class_01": ClassGroup(
            id="class_01",
            name="高一(1)班",
            grade="高一",
            student_count=45,
            courses=["course_math", "course_chinese", "course_english",
                     "course_physics", "course_chemistry", "course_history",
                     "course_geography", "course_pe", "course_music"]
        ),
        "class_02": ClassGroup(
            id="class_02",
            name="高一(2)班",
            grade="高一",
            student_count=45,
            courses=["course_math", "course_chinese", "course_english",
                     "course_physics", "course_chemistry", "course_history",
                     "course_geography", "course_pe", "course_music"]
        ),
    }

    # 教师
    teachers = {
        "teacher_01": Teacher(id="teacher_01", name="张老师", subjects=["数学"], max_hours_per_day=6, max_hours_per_week=20),
        "teacher_02": Teacher(id="teacher_02", name="李老师", subjects=["语文"], max_hours_per_day=6, max_hours_per_week=20),
        "teacher_03": Teacher(id="teacher_03", name="王老师", subjects=["英语"], max_hours_per_day=6, max_hours_per_week=20),
        "teacher_04": Teacher(id="teacher_04", name="赵老师", subjects=["物理"], max_hours_per_day=6, max_hours_per_week=16),
        "teacher_05": Teacher(id="teacher_05", name="钱老师", subjects=["化学"], max_hours_per_day=6, max_hours_per_week=16),
        "teacher_06": Teacher(id="teacher_06", name="孙老师", subjects=["历史"], max_hours_per_day=6, max_hours_per_week=14),
        "teacher_07": Teacher(id="teacher_07", name="周老师", subjects=["地理"], max_hours_per_day=6, max_hours_per_week=14),
        "teacher_08": Teacher(id="teacher_08", name="吴老师", subjects=["体育"], max_hours_per_day=4, max_hours_per_week=12),
        "teacher_09": Teacher(id="teacher_09", name="郑老师", subjects=["音乐"], max_hours_per_day=4, max_hours_per_week=10),
    }

    # 课程
    courses = {
        "course_math": Course(id="course_math", name="数学", subject="数学", hours_per_week=5, is_main_subject=True, weight=105),
        "course_chinese": Course(id="course_chinese", name="语文", subject="语文", hours_per_week=5, is_main_subject=True, weight=105),
        "course_english": Course(id="course_english", name="英语", subject="英语", hours_per_week=5, is_main_subject=True, weight=105),
        "course_physics": Course(id="course_physics", name="物理", subject="物理", hours_per_week=3, is_main_subject=False, weight=53),
        "course_chemistry": Course(id="course_chemistry", name="化学", subject="化学", hours_per_week=3, is_main_subject=False, weight=53),
        "course_history": Course(id="course_history", name="历史", subject="历史", hours_per_week=2, is_main_subject=False, weight=52),
        "course_geography": Course(id="course_geography", name="地理", subject="地理", hours_per_week=2, is_main_subject=False, weight=52),
        "course_pe": Course(id="course_pe", name="体育", subject="体育", hours_per_week=2, is_main_subject=False, weight=52),
        "course_music": Course(id="course_music", name="音乐", subject="音乐", hours_per_week=1, is_main_subject=False, weight=51),
    }

    # 教室
    classrooms = {
        f"room_{i:02d}": Classroom(id=f"room_{i:02d}", name=f"{100+i}教室", capacity=50, equipment=["多媒体"])
        for i in range(1, 11)
    }

    # 约束配置
    constraints = ConstraintManager()
    constraints.update_config({
        "max_consecutive_hours": 4,
        "main_subject_prefer_morning": True,
        "max_daily_hours_per_teacher": 8,
        "penalty_main_subject_afternoon": 10,
        "penalty_consecutive_over_limit": 5,
    })

    print(f"  ✓ 班级: {len(classes)} 个")
    print(f"  ✓ 教师: {len(teachers)} 人")
    print(f"  ✓ 课程: {len(courses)} 门")
    print(f"  ✓ 教室: {len(classrooms)} 间")

    # ── 2. 构建排课任务 ──
    print("\n【步骤 2】构建排课任务...")
    task = SchedulingTask(
        classes=classes,
        teachers=teachers,
        classrooms=classrooms,
        courses=courses,
        constraints=constraints,
    )
    print(f"  ✓ 任务构建完成")

    # ── 3. 执行排课 ──
    print("\n【步骤 3】执行自动排课...")
    algorithm = ScheduleAlgorithm()
    result = algorithm.schedule(task)

    if result.success:
        print(f"  ✅ 排课成功!")
        print(f"  • 排课记录数: {len(result.schedule.entries)}")
        print(f"  • 冲突数: {result.conflicts}")
    else:
        print(f"  ⚠️ 排课部分完成: {result.message}")
        print(f"  • 冲突数: {result.conflicts}")

    # ── 4. 生成文本课表 ──
    print("\n【步骤 4】生成文本课表...")
    for class_id, class_group in classes.items():
        table = result.schedule.to_table(class_id, classes, courses, teachers, classrooms)
        print(f"\n📅 {class_group.name} 课表:")
        print(table)

    # ── 5. 生成课表图片 ──
    print("\n【步骤 5】生成课表图片...")
    output_dir = os.path.join(os.path.dirname(__file__), "..", "test_output")
    os.makedirs(output_dir, exist_ok=True)

    for class_id, class_group in classes.items():
        img_path = os.path.join(output_dir, f"课表_{class_group.name}.png")
        success = result.schedule.to_image(class_id, classes, courses, teachers, img_path, classrooms)
        if success:
            print(f"  ✅ {class_group.name} 课表图片已生成: {img_path}")
        else:
            print(f"  ❌ {class_group.name} 课表图片生成失败")

    # ── 6. 保存排课结果 ──
    print("\n【步骤 6】保存排课结果...")
    result_file = os.path.join(output_dir, "schedule_result.json")
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write(result.schedule.to_json())
    print(f"  ✓ 排课结果已保存: {result_file}")

    # ── 7. 测试教师课表查询 ──
    print("\n【步骤 7】教师课表查询...")
    teacher_schedule = result.schedule.get_teacher_schedule("teacher_01")
    print(f"  📅 张老师（数学）本周有 {len(teacher_schedule)} 节课:")
    for entry in teacher_schedule[:5]:  # 只显示前5条
        print(f"    • {entry.time_slot}")
    if len(teacher_schedule) > 5:
        print(f"    ... 还有 {len(teacher_schedule) - 5} 节课")

    # ── 8. 统计信息 ──
    print("\n【步骤 8】统计信息...")
    print(f"  • 总排课记录: {len(result.schedule.entries)}")
    print(f"  • 班级数量: {len(classes)}")
    print(f"  • 教师数量: {len(teachers)}")

    # 计算每个教师的课时
    print("\n  👨‍🏫 教师课时统计:")
    for teacher_id, teacher in teachers.items():
        schedule_entries = result.schedule.get_teacher_schedule(teacher_id)
        total_hours = len(schedule_entries)
        daily_hours = {}
        for entry in schedule_entries:
            day = entry.time_slot.weekday.value
            daily_hours[day] = daily_hours.get(day, 0) + 1
        max_daily = max(daily_hours.values()) if daily_hours else 0
        print(f"    • {teacher.name}（{', '.join(teacher.subjects)}）: 总{total_hours}节, 日最多{max_daily}节")

    print("\n" + "=" * 60)
    print("✅ 排课系统测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    test_scheduling()
