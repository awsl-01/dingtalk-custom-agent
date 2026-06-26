"""
测试 filter_by_subject 方法
"""
import json
import os
import sys

# 强制使用 UTF-8 编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.skills.scheduling import Schedule, ClassGroup, Course, Teacher, Classroom


def test_filter_by_subject():
    """测试 filter_by_subject 方法"""

    # 学校配置
    school_dir = "D:/claude/knowledge/ding3f80869f26d4bb44a39a90f97fcb1e09"

    # 加载排课数据
    schedule_file = os.path.join(school_dir, "scheduling", "schedule_result.json")
    data_file = os.path.join(school_dir, "scheduling", "scheduling_data.json")

    with open(schedule_file, 'r', encoding='utf-8') as f:
        schedule_data = json.load(f)

    with open(data_file, 'r', encoding='utf-8') as f:
        scheduling_data = json.load(f)

    print("=" * 60)
    print("[INFO] 加载排课数据")
    print("=" * 60)
    print(f"排课结果: {len(schedule_data.get('entries', []))} 条")
    print(f"班级: {len(scheduling_data.get('classes', []))} 个")
    print(f"课程: {len(scheduling_data.get('courses', []))} 门")
    print(f"教师: {len(scheduling_data.get('teachers', []))} 人")

    # 创建 Schedule 对象
    schedule = Schedule.from_json(json.dumps(schedule_data))
    classes = {c["id"]: ClassGroup.from_dict(c) for c in scheduling_data.get("classes", [])}
    courses = {c["id"]: Course.from_dict(c) for c in scheduling_data.get("courses", [])}
    teachers = {t["id"]: Teacher.from_dict(t) for t in scheduling_data.get("teachers", [])}
    classrooms = {c["id"]: Classroom.from_dict(c) for c in scheduling_data.get("classrooms", [])}

    # 测试查询
    class_id = "class_01"
    subject = "数学"

    print(f"\n{'='*60}")
    print(f"[查询] {classes[class_id].name} {subject}课")
    print('='*60)

    result = schedule.filter_by_subject(
        class_id, subject, classes, courses, teachers, classrooms
    )

    if result:
        print(f"[OK] 找到 {subject} 课:")
        print(result)
    else:
        print(f"[WARNING] 未找到 {subject} 课")

    # 测试查询周一数学课
    print(f"\n{'='*60}")
    print(f"[查询] {classes[class_id].name} 周一 {subject}课")
    print('='*60)

    # 先获取该班级的所有课程
    class_schedule = schedule.get_class_schedule(class_id)
    print(f"该班级总课程数: {len(class_schedule)}")

    # 查找周一的数学课
    monday_math = []
    for entry in class_schedule:
        course = courses.get(entry.course_id)
        if course and subject in course.subject and entry.time_slot.weekday.value == "周一":
            teacher = teachers.get(entry.teacher_id)
            classroom = classrooms.get(entry.classroom_id)
            monday_math.append({
                "period": entry.time_slot.period,
                "course": course.name,
                "teacher": teacher.name if teacher else "",
                "classroom": classroom.name if classroom else "",
            })

    if monday_math:
        print(f"[OK] 周一 {subject} 课:")
        for item in monday_math:
            print(f"  第{item['period']}节: {item['course']} ({item['teacher']}@{item['classroom']})")
    else:
        print(f"[WARNING] 周一没有 {subject} 课")


if __name__ == "__main__":
    test_filter_by_subject()
