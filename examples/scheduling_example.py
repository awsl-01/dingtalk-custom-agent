"""
排课系统使用示例

展示如何使用排课系统进行自动排课
"""
import sys
import os
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.skills.scheduling import (
    Teacher, Classroom, Course, ClassGroup,
    ScheduleAlgorithm, SchedulingTask, ConstraintManager,
    Schedule, TimeSlot, Weekday,
    generate_template, parse_scheduling_excel,
)


def example_basic():
    """基础排课示例"""
    print("=" * 50)
    print("基础排课示例")
    print("=" * 50)
    print()

    # 1. 创建教师数据
    teachers = {
        't1': Teacher(
            id='t1',
            name='张老师',
            subjects=['数学'],
            max_hours_per_day=4,
            max_hours_per_week=20,
        ),
        't2': Teacher(
            id='t2',
            name='李老师',
            subjects=['语文'],
            max_hours_per_day=4,
            max_hours_per_week=20,
        ),
        't3': Teacher(
            id='t3',
            name='王老师',
            subjects=['英语'],
            max_hours_per_day=4,
            max_hours_per_week=20,
        ),
        't4': Teacher(
            id='t4',
            name='赵老师',
            subjects=['物理'],
            max_hours_per_day=3,
            max_hours_per_week=15,
        ),
    }

    # 2. 创建教室数据
    classrooms = {
        'r1': Classroom(id='r1', name='101教室', capacity=50, equipment=['多媒体']),
        'r2': Classroom(id='r2', name='102教室', capacity=50, equipment=['多媒体']),
        'r3': Classroom(id='r3', name='实验室1', capacity=50, equipment=['实验设备', '多媒体']),
    }

    # 3. 创建课程数据
    courses = {
        'math': Course(
            id='math',
            name='数学',
            subject='数学',
            hours_per_week=5,
            is_main_subject=True,
        ),
        'chinese': Course(
            id='chinese',
            name='语文',
            subject='语文',
            hours_per_week=5,
            is_main_subject=True,
        ),
        'english': Course(
            id='english',
            name='英语',
            subject='英语',
            hours_per_week=5,
            is_main_subject=True,
        ),
        'physics': Course(
            id='physics',
            name='物理',
            subject='物理',
            hours_per_week=3,
        ),
    }

    # 4. 创建班级数据
    classes = {
        'c1': ClassGroup(
            id='c1',
            name='高一(1)班',
            grade='高一',
            student_count=45,
            courses=['math', 'chinese', 'english', 'physics'],
            homeroom_teacher='t1',
        ),
        'c2': ClassGroup(
            id='c2',
            name='高一(2)班',
            grade='高一',
            student_count=46,
            courses=['math', 'chinese', 'english', 'physics'],
            homeroom_teacher='t2',
        ),
    }

    # 5. 创建约束管理器
    constraints = ConstraintManager()
    constraints.update_config({
        "max_consecutive_hours": 3,
        "main_subject_prefer_morning": True,
        "max_daily_hours_per_teacher": 4,
        "course_even_distribution": True,
    })

    # 6. 创建排课任务
    task = SchedulingTask(
        classes=classes,
        teachers=teachers,
        classrooms=classrooms,
        courses=courses,
        constraints=constraints,
    )

    # 7. 执行排课
    print("开始排课...")
    algorithm = ScheduleAlgorithm()
    result = algorithm.schedule(task)

    print(f"\n排课结果: {'成功' if result.success else '失败'}")
    print(f"冲突数: {result.conflicts}")
    print()

    # 8. 显示课表
    if result.success:
        for class_id, class_group in classes.items():
            print(f"\n{class_group.name} 课表:")
            print("-" * 50)
            table = result.schedule.to_table(class_id, classes, courses, teachers)
            print(table)

        # 9. 导出数据
        output_file = "schedule_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.schedule.to_json())
        print(f"\n课表已导出到: {output_file}")

    return result


def example_excel_template():
    """生成 Excel 模板示例"""
    print("\n" + "=" * 50)
    print("生成 Excel 模板")
    print("=" * 50)
    print()

    output_file = "scheduling_template.xlsx"
    success = generate_template(output_file)

    if success:
        print(f"[OK] Excel 模板已生成: {output_file}")
        print("\n请填写模板后，使用「排课」命令进行自动排课。")
    else:
        print("[ERROR] 生成模板失败，请确保已安装 openpyxl: pip install openpyxl")


def example_multi_class():
    """多班级排课示例"""
    print("\n" + "=" * 50)
    print("多班级排课示例")
    print("=" * 50)
    print()

    # 共享教师资源
    teachers = {
        't1': Teacher(id='t1', name='张老师', subjects=['数学']),
        't2': Teacher(id='t2', name='李老师', subjects=['语文']),
        't3': Teacher(id='t3', name='王老师', subjects=['英语']),
        't4': Teacher(id='t4', name='赵老师', subjects=['物理', '化学']),
    }

    classrooms = {
        'r1': Classroom(id='r1', name='101教室', capacity=50),
        'r2': Classroom(id='r2', name='102教室', capacity=50),
        'r3': Classroom(id='r3', name='103教室', capacity=50),
    }

    courses = {
        'math': Course(id='math', name='数学', subject='数学', hours_per_week=5, is_main_subject=True),
        'chinese': Course(id='chinese', name='语文', subject='语文', hours_per_week=5, is_main_subject=True),
        'english': Course(id='english', name='英语', subject='英语', hours_per_week=5, is_main_subject=True),
        'physics': Course(id='physics', name='物理', subject='物理', hours_per_week=3),
    }

    # 3个班级
    classes = {}
    for i in range(1, 4):
        classes[f'c{i}'] = ClassGroup(
            id=f'c{i}',
            name=f'高一({i})班',
            grade='高一',
            student_count=45 + i,
            courses=['math', 'chinese', 'english', 'physics'],
        )

    constraints = ConstraintManager()

    task = SchedulingTask(
        classes=classes,
        teachers=teachers,
        classrooms=classrooms,
        courses=courses,
        constraints=constraints,
    )

    print(f"排课规模: {len(classes)} 班级, {len(teachers)} 教师, {len(courses)} 课程")
    print()

    algorithm = ScheduleAlgorithm()
    result = algorithm.schedule(task)

    print(f"排课结果: {'成功' if result.success else '失败'}")
    print(f"冲突数: {result.conflicts}")

    if result.success:
        for class_id, class_group in classes.items():
            entries = result.schedule.get_class_schedule(class_id)
            print(f"  {class_group.name}: {len(entries)} 节课")

    return result


if __name__ == "__main__":
    # 运行基础示例
    example_basic()

    # 生成 Excel 模板
    example_excel_template()

    # 运行多班级示例
    example_multi_class()
