#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试排课算法修复效果
"""
import sys
import os
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.skills.scheduling import (
    ScheduleAlgorithm, SchedulingTask,
    ConstraintManager, Teacher, Classroom, Course, ClassGroup,
)

def test_scheduling():
    """测试排课算法"""
    print("=" * 60)
    print("测试排课算法修复效果")
    print("=" * 60)

    # 加载排课数据
    data_file = "knowledge/ding3f80869f26d4bb44a39a90f97fcb1e09/scheduling/scheduling_data.json"
    if not os.path.exists(data_file):
        print(f"未找到排课数据文件: {data_file}")
        return

    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"加载排课数据:")
    print(f"  - 班级: {len(data.get('classes', []))} 个")
    print(f"  - 教师: {len(data.get('teachers', []))} 人")
    print(f"  - 课程: {len(data.get('courses', []))} 门")
    print(f"  - 教室: {len(data.get('classrooms', []))} 间")
    print()

    # 构建排课任务
    teachers = {t["id"]: Teacher.from_dict(t) for t in data.get("teachers", [])}
    classrooms = {c["id"]: Classroom.from_dict(c) for c in data.get("classrooms", [])}
    courses = {c["id"]: Course.from_dict(c) for c in data.get("courses", [])}
    classes = {c["id"]: ClassGroup.from_dict(c) for c in data.get("classes", [])}

    constraints = ConstraintManager()
    if "constraints" in data:
        constraints.update_config(data["constraints"])

    task = SchedulingTask(
        classes=classes,
        teachers=teachers,
        classrooms=classrooms,
        courses=courses,
        constraints=constraints,
    )

    # 计算总课时
    total_lessons = 0
    for class_group in classes.values():
        for course_id in class_group.courses:
            course = courses.get(course_id)
            if course:
                total_lessons += course.hours_per_week

    print(f"原始课程总课时: {total_lessons} 节")
    print()

    # 执行排课
    print("正在执行排课算法...")
    algorithm = ScheduleAlgorithm()
    result = algorithm.schedule(task)

    # 检查自动补充课程后的总课时
    total_lessons_after = 0
    for class_group in task.classes.values():
        for course_id in class_group.courses:
            course = task.courses.get(course_id)
            if course:
                total_lessons_after += course.hours_per_week

    print(f"自动补充课程后总课时: {total_lessons_after} 节")
    print()

    # 显示结果
    print()
    print("=" * 60)
    print("排课结果")
    print("=" * 60)

    if result.success:
        print("排课成功！所有课程已安排。")
    else:
        print(f"排课部分完成: {result.message}")
        print(f"  - 冲突数: {result.conflicts}")

    # 统计各班级课时
    print()
    print("各班级课时统计:")
    for class_id, class_group in classes.items():
        class_entries = result.schedule.get_class_schedule(class_id)
        print(f"  - {class_group.name}: {len(class_entries)} 节课")

    # 统计教师工作量
    print()
    print("教师工作量统计:")
    for teacher_id, teacher in teachers.items():
        teacher_entries = result.schedule.get_teacher_schedule(teacher_id)
        print(f"  - {teacher.name}: {len(teacher_entries)} 节课")

    # 保存结果
    result_file = "knowledge/ding3f80869f26d4bb44a39a90f97fcb1e09/scheduling/schedule_result_fixed.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write(result.schedule.to_json())

    print()
    print(f"修复后的排课结果已保存到: {result_file}")

    # 显示第一个班级的课表预览
    if classes:
        first_class_id = list(classes.keys())[0]
        first_class = classes[first_class_id]
        print()
        print(f"{first_class.name} 课表预览:")
        table = result.schedule.to_table(
            first_class_id, classes, courses, teachers, classrooms
        )
        print(table)

if __name__ == "__main__":
    test_scheduling()
