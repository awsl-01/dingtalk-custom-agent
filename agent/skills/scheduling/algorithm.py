"""
排课算法模块 v3

优化版排课算法：
1. 增加班会、自习、选修课等副科
2. 优化下午课程分布，确保每天下午都有课
3. 保持文理穿插、教师休息等约束
"""
import random
import logging
from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass

from .models import (
    TimeSlot, Teacher, Classroom, Course, ClassGroup,
    ScheduleEntry, Schedule, Weekday, PeriodType,
)
from .constraints import ConstraintManager
from .detector import ConflictDetector, ConflictType

logger = logging.getLogger(__name__)


# 学科分类
SUBJECT_GROUPS = {
    "理科": ["数学", "物理", "化学", "生物"],
    "文科": ["语文", "英语", "历史", "地理", "政治"],
    "体艺": ["体育", "音乐", "美术", "信息技术", "心理健康"],
    "活动": ["班会", "自习", "选修", "综合实践"],
}


def get_subject_group(subject: str) -> str:
    """获取学科所属组"""
    for group, subjects in SUBJECT_GROUPS.items():
        if subject in subjects:
            return group
    return "其他"


# 自动添加的课程配置
AUTO_COURSES = {
    "班会": {"hours_per_week": 1, "is_main": False, "weight": 30, "group": "活动"},
    "自习": {"hours_per_week": 2, "is_main": False, "weight": 20, "group": "活动"},
    "选修": {"hours_per_week": 1, "is_main": False, "weight": 25, "group": "活动"},
}


@dataclass
class SchedulingTask:
    """排课任务"""
    classes: Dict[str, ClassGroup]
    teachers: Dict[str, Teacher]
    classrooms: Dict[str, Classroom]
    courses: Dict[str, Course]
    constraints: ConstraintManager


@dataclass
class SchedulingResult:
    """排课结果"""
    success: bool
    schedule: Schedule
    message: str
    conflicts: int = 0
    iterations: int = 0


class ScheduleAlgorithm:
    """
    排课算法 v3

    优化点：
    1. 自动添加班会、自习、选修等课程
    2. 确保每天下午至少有2节课
    3. 优化文理穿插
    """

    def __init__(self):
        self.conflict_detector = ConflictDetector()
        self.max_iterations = 2000

        # 约束配置
        self.MAX_CONSECUTIVE_SAME_TEACHER = 3
        self.MIN_AFTERNOON_COURSES = 2  # 每天下午最少课程数

    def schedule(self, task: SchedulingTask, slot_config: dict = None) -> SchedulingResult:
        """执行排课"""
        logger.info("开始排课 v3...")

        # 自动补充课程（班会、自习、选修）
        task = self._auto_supplement_courses(task)

        # 生成待排课程列表（每节独立）
        pending_lessons = self._generate_pending_lessons(task)
        total_lessons = len(pending_lessons)
        logger.info(f"需要安排 {total_lessons} 节课")

        # 生成可用时间段
        available_slots = self._generate_available_slots(slot_config)
        logger.info(f"可用时间段: {len(available_slots)} 个")

        # 使用贪心算法生成课表
        schedule = Schedule()
        unplaced = self._greedy_schedule_v3(task, pending_lessons, available_slots, schedule, slot_config)

        # 确保下午有足够课程
        schedule = self._ensure_afternoon_courses(schedule, task, available_slots, slot_config)

        # 局部搜索优化
        schedule = self._local_search_optimize(schedule, task, available_slots, slot_config)

        # 检测冲突
        conflicts = self.conflict_detector.detect_all(
            schedule, task.teachers, task.classrooms, task.courses, task.classes
        )

        result = SchedulingResult(
            success=len(unplaced) == 0,
            schedule=schedule,
            message="排课完成" if not unplaced else f"排课部分完成，{len(unplaced)} 节未安排",
            conflicts=len(conflicts),
        )

        logger.info(f"排课完成: 未安排={len(unplaced)}, 冲突数={len(conflicts)}")
        return result

    def _auto_supplement_courses(self, task: SchedulingTask) -> SchedulingTask:
        """自动补充班会、自习、选修等课程"""
        # 检查是否已有这些课程
        existing_subjects = set()
        for course in task.courses.values():
            existing_subjects.add(course.subject)

        # 计算需要的教师数量
        num_classes = len(task.classes)

        # 添加缺失的课程
        for subject, config in AUTO_COURSES.items():
            if subject not in existing_subjects:
                course_id = f"course_{subject}"
                task.courses[course_id] = Course(
                    id=course_id,
                    name=subject,
                    subject=subject,
                    hours_per_week=config["hours_per_week"],
                    is_main_subject=config["is_main"],
                    weight=config["weight"],
                )
                # 为每个班级添加这门课
                for class_group in task.classes.values():
                    if course_id not in class_group.courses:
                        class_group.courses.append(course_id)

                # 添加足够的教师（如果没有）
                has_teacher = any(subject in t.subjects for t in task.teachers.values())
                if not has_teacher:
                    # 根据班级数量计算需要的教师数
                    # 每个教师每天最多上8节课，每周最多上40节课
                    # 5个班级需要5节课，一个教师足够
                    total_hours_needed = config["hours_per_week"] * num_classes
                    hours_per_teacher = min(40, total_hours_needed)  # 每个教师最多40课时
                    num_teachers_needed = max(1, (total_hours_needed + hours_per_teacher - 1) // hours_per_teacher)

                    for i in range(num_teachers_needed):
                        teacher_id = f"teacher_{subject}_{i+1}"
                        task.teachers[teacher_id] = Teacher(
                            id=teacher_id,
                            name=f"{subject}老师{i+1}" if num_teachers_needed > 1 else f"{subject}老师",
                            subjects=[subject],
                            max_hours_per_day=8,  # 每天最多8节课
                            max_hours_per_week=hours_per_teacher,
                        )

        return task

    def _generate_pending_lessons(self, task: SchedulingTask) -> List[Dict]:
        """生成待排课程列表"""
        lessons = []

        for class_id, class_group in task.classes.items():
            for course_id in class_group.courses:
                course = task.courses.get(course_id)
                if not course:
                    continue

                # 按单节生成
                for i in range(course.hours_per_week):
                    lessons.append({
                        "class_id": class_id,
                        "course_id": course_id,
                        "subject": course.subject,
                        "is_main": course.is_main_subject,
                        "weight": course.weight,
                        "max_per_day": course.max_per_day if course.is_main_subject else 1,
                        "room_type": course.room_type,
                        "required_equipment": course.required_equipment,
                        "lesson_index": i + 1,
                        "group": get_subject_group(course.subject),
                    })

        # 按权重排序
        lessons.sort(key=lambda l: (-l["is_main"], -l["weight"], l["lesson_index"]))
        return lessons

    def _generate_available_slots(self, config: dict = None) -> List[TimeSlot]:
        """生成所有可用时间段"""
        if config is None:
            config = {}

        slots = []
        weekdays = config.get("weekdays", [
            Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY,
            Weekday.THURSDAY, Weekday.FRIDAY,
        ])
        periods_per_day = config.get("periods_per_day", 8)
        forbidden = set(config.get("forbidden_slots", []))

        for weekday in weekdays:
            for period in range(1, periods_per_day + 1):
                if (weekday.value, period) not in forbidden:
                    slots.append(TimeSlot(weekday=weekday, period=period))

        return slots

    def _greedy_schedule_v3(self, task: SchedulingTask,
                             pending_lessons: List[Dict],
                             available_slots: List[TimeSlot],
                             schedule: Schedule,
                             slot_config: dict = None) -> List[Dict]:
        """贪心排课算法 v3"""
        import random

        entry_counter = 0
        unplaced = []

        # 按班级分组
        class_lessons = defaultdict(list)
        for lesson in pending_lessons:
            class_lessons[lesson["class_id"]].append(lesson)

        all_class_ids = list(class_lessons.keys())

        # 按节次顺序排课
        for period in range(1, 9):
            for weekday in [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY,
                          Weekday.THURSDAY, Weekday.FRIDAY]:
                slot = TimeSlot(weekday=weekday, period=period)

                for class_id in all_class_ids:
                    if schedule.is_class_busy(class_id, slot):
                        continue

                    lesson = self._find_best_lesson(
                        task, class_lessons[class_id], slot, schedule, slot_config
                    )

                    if lesson:
                        teacher, classroom = self._find_available_resources(
                            task, lesson, slot, schedule
                        )

                        if teacher and classroom:
                            entry = ScheduleEntry(
                                id=f"entry_{entry_counter}",
                                class_id=class_id,
                                course_id=lesson["course_id"],
                                teacher_id=teacher.id,
                                classroom_id=classroom.id,
                                time_slot=slot,
                            )
                            schedule.add_entry(entry)
                            entry_counter += 1

                            if lesson in class_lessons[class_id]:
                                class_lessons[class_id].remove(lesson)
                        else:
                            unplaced.append(lesson)

        # 处理剩余课程
        for class_id, lessons in class_lessons.items():
            for lesson in lessons:
                placed = self._try_place_lesson(task, lesson, available_slots, schedule, slot_config)
                if not placed:
                    unplaced.append(lesson)

        return unplaced

    def _find_best_lesson(self, task: SchedulingTask, lessons: List[Dict],
                          slot: TimeSlot, schedule: Schedule,
                          slot_config: dict = None) -> Optional[Dict]:
        """找到最适合当前时间段的课程"""
        if not lessons:
            return None

        current_weekday = slot.weekday
        current_period = slot.period
        is_morning = current_period <= 4

        # 获取前一节的学科组
        prev_group = None
        if current_period > 1:
            prev_slot = TimeSlot(weekday=current_weekday, period=current_period - 1)
            prev_entries = schedule.get_slot_entries(prev_slot)
            if prev_entries:
                prev_course = task.courses.get(prev_entries[0].course_id)
                if prev_course:
                    prev_group = get_subject_group(prev_course.subject)

        # 为每个课程评分
        scored_lessons = []
        for lesson in lessons:
            score = 0
            subject = lesson["subject"]
            is_main = lesson["is_main"]
            subject_group = lesson["group"]

            # 检查单日同科目数量
            day_count = self._count_subject_per_day(schedule, lesson["class_id"], subject, current_weekday)
            max_per_day = lesson["max_per_day"]
            if day_count >= max_per_day:
                score -= 100

            # 检查文理穿插
            if prev_group and subject_group == prev_group:
                score -= 30

            # 上午优先排主课
            if is_morning and is_main:
                score += 20
            elif not is_morning and not is_main:
                score += 15
            elif not is_morning and is_main:
                score -= 10

            # 体艺类安排在下午
            if subject_group == "体艺":
                if not is_morning:
                    score += 25
                else:
                    score -= 20

            # 活动类课程（班会、自习、选修）安排在特定时间
            if subject_group == "活动":
                # 活动类课程可以在任何时间安排，给予最高优先级
                score += -41
                if subject == "班会":
                    if current_period == 7:
                        score += 20  # 班会安排在周五第7节额外加分
                elif subject == "自习":
                    if current_period >= 5:
                        score += 15  # 自习安排在下午额外加分
                elif subject == "选修":
                    if not is_morning:
                        score += 15  # 选修安排在下午额外加分

            # 权重
            score += lesson["weight"] * 0.1

            # 随机扰动
            score += random.uniform(-5, 5)

            scored_lessons.append((score, lesson))

        # 按分数排序
        scored_lessons.sort(key=lambda x: -x[0])

        for score, lesson in scored_lessons:
            teacher, classroom = self._find_available_resources(task, lesson, slot, schedule)
            if teacher and classroom:
                return lesson

        return None

    def _count_subject_per_day(self, schedule: Schedule, class_id: str,
                               subject: str, weekday: Weekday) -> int:
        """统计某班某天某科目的节数"""
        count = 0
        for period in range(1, 9):
            slot = TimeSlot(weekday=weekday, period=period)
            entries = schedule.get_slot_entries(slot)
            for entry in entries:
                if entry.class_id == class_id:
                    # 获取课程信息
                    for c in schedule.entries:
                        if c.id == entry.id:
                            # 从课程ID中提取科目信息
                            # 课程ID格式: course_数学, course_语文 等
                            entry_subject = c.course_id.replace("course_", "")
                            if entry_subject == subject:
                                count += 1
                            break
        return count

    def _find_available_resources(self, task: SchedulingTask, lesson: Dict,
                                  slot: TimeSlot, schedule: Schedule) -> Tuple[Optional[Teacher], Optional[Classroom]]:
        """找到可用的教师和教室"""
        course_id = lesson["course_id"]
        course = task.courses.get(course_id)

        if not course:
            return None, None

        # 找能教这门课的教师
        eligible_teachers = [
            t for t in task.teachers.values()
            if t.can_teach(course.subject)
        ]

        # 检查教师是否可用
        available_teachers = []
        for teacher in eligible_teachers:
            if not schedule.is_teacher_busy(teacher.id, slot):
                if self._check_teacher_consecutive(task, teacher, slot, schedule):
                    available_teachers.append(teacher)

        if not available_teachers:
            return None, None

        # 找可用教室
        eligible_classrooms = [
            c for c in task.classrooms.values()
            if not schedule.is_classroom_busy(c.id, slot)
        ]

        if not eligible_classrooms:
            return None, None

        # 选择教师：优先选课时少的
        available_teachers.sort(key=lambda t: len(schedule.get_teacher_schedule(t.id)))
        teacher = available_teachers[0]

        # 根据课程需求选择合适的教室
        course = task.courses.get(lesson["course_id"])

        # 判断课程是否需要专用教室
        required_equipment = []
        if course:
            required_equipment = course.required_equipment or []

        def _classroom_has_equipment(classroom, required):
            """检查教室是否满足设备要求"""
            if not required:
                return True
            classroom_equipment = classroom.equipment or []
            classroom_name = classroom.name
            for equip in required:
                # 检查设备名称是否在教室设备列表或教室名称中
                if equip in classroom_equipment or equip in classroom_name:
                    continue
                return False
            return True

        # 优先使用用户指定的固定教室（但要检查设备兼容性）
        class_group = task.classes.get(lesson["class_id"])
        if class_group and class_group.assigned_classrooms:
            # 查找匹配的教室ID
            assigned_classrooms_list = []
            for classroom in eligible_classrooms:
                if classroom.name in class_group.assigned_classrooms:
                    # 检查设备是否满足课程需求
                    if _classroom_has_equipment(classroom, required_equipment):
                        assigned_classrooms_list.append(classroom)

            if assigned_classrooms_list:
                # 从指定教室中选择使用次数最少的
                classroom_usage = {}
                for c in assigned_classrooms_list:
                    usage = len(schedule.get_classroom_schedule(c.id))
                    classroom_usage[c.id] = usage
                assigned_classrooms_list.sort(key=lambda c: classroom_usage.get(c.id, 0))
                classroom = assigned_classrooms_list[0]
                return teacher, classroom
            # 如果指定教室都不满足设备需求，继续走下面的自动分配逻辑

        if course:
            subject = course.subject

            # 根据学科选择合适的教室类型
            subject_classroom_preference = {
                # 理科实验课程 -> 实验室
                "物理": ["实验室"],
                "化学": ["实验室"],
                "生物": ["实验室"],

                # 体育课 -> 操场
                "体育": ["操场"],

                # 艺术课程 -> 专用教室
                "音乐": ["音乐"],
                "美术": ["美术"],

                # 信息技术课程 -> 微机室
                "信息技术": ["微机"],

                # 通用技术课程 -> 通用技术教室
                "通用技术": ["通用技术"],

                # 其他课程 -> 普通教室（排除专用教室）
                "语文": ["教室"],
                "数学": ["教室"],
                "英语": ["教室"],
                "历史": ["教室"],
                "地理": ["教室"],
                "政治": ["教室"],
                "心理": ["教室"],
                "自习": ["教室"],
                "班会": ["教室"],
            }

            # 获取该学科偏好的教室类型
            preferred_types = subject_classroom_preference.get(subject, ["教室"])

            # 按偏好筛选教室
            preferred_classrooms = []
            for classroom in eligible_classrooms:
                classroom_name = classroom.name
                # 检查教室名称是否包含偏好的关键词
                for preferred_type in preferred_types:
                    if preferred_type in classroom_name:
                        preferred_classrooms.append(classroom)
                        break

            # 如果有偏好教室，从中选择使用次数最少的
            if preferred_classrooms:
                classroom_usage = {}
                for c in preferred_classrooms:
                    usage = len(schedule.get_classroom_schedule(c.id))
                    classroom_usage[c.id] = usage

                preferred_classrooms.sort(key=lambda c: classroom_usage.get(c.id, 0))
                classroom = preferred_classrooms[0]
            else:
                # 如果没有偏好教室，从所有可用教室中选择使用次数最少的
                classroom_usage = {}
                for c in eligible_classrooms:
                    usage = len(schedule.get_classroom_schedule(c.id))
                    classroom_usage[c.id] = usage

                eligible_classrooms.sort(key=lambda c: classroom_usage.get(c.id, 0))
                classroom = eligible_classrooms[0]
        else:
            # 如果没有课程信息，从所有可用教室中选择使用次数最少的
            classroom_usage = {}
            for c in eligible_classrooms:
                usage = len(schedule.get_classroom_schedule(c.id))
                classroom_usage[c.id] = usage

            eligible_classrooms.sort(key=lambda c: classroom_usage.get(c.id, 0))
            classroom = eligible_classrooms[0]

        return teacher, classroom

    def _check_teacher_consecutive(self, task: SchedulingTask, teacher: Teacher,
                                   slot: TimeSlot, schedule: Schedule) -> bool:
        """检查教师是否满足连续上课约束"""
        weekday = slot.weekday
        period = slot.period

        # 检查是否超过教师每天最大课时数
        daily_hours = schedule.get_teacher_daily_hours(teacher.id, weekday)
        if daily_hours >= teacher.max_hours_per_day:
            return False

        # 检查连续上课节数（真正检查连续性）
        consecutive_count = 0
        max_consecutive = 0

        # 从第1节到当前节，统计连续上课情况
        for p in range(1, period + 1):
            check_slot = TimeSlot(weekday=weekday, period=p)
            entries = schedule.get_slot_entries(check_slot)
            has_class = any(entry.teacher_id == teacher.id for entry in entries)

            if has_class:
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count)
            else:
                consecutive_count = 0

        # 检查是否超过最大连续节数
        if max_consecutive >= self.MAX_CONSECUTIVE_SAME_TEACHER:
            return False

        # 检查当前节的前一节是否有课（避免连续）
        if period > 1:
            prev_slot = TimeSlot(weekday=weekday, period=period - 1)
            prev_entries = schedule.get_slot_entries(prev_slot)
            if any(entry.teacher_id == teacher.id for entry in prev_entries):
                # 如果前一节有课，检查是否已经超过连续限制
                if consecutive_count >= self.MAX_CONSECUTIVE_SAME_TEACHER - 1:
                    return False

        return True

    def _try_place_lesson(self, task: SchedulingTask, lesson: Dict,
                          available_slots: List[TimeSlot], schedule: Schedule,
                          slot_config: dict = None) -> bool:
        """尝试将课程安排到其他时间"""
        import random

        slots = list(available_slots)
        random.shuffle(slots)

        for slot in slots:
            if schedule.is_class_busy(lesson["class_id"], slot):
                continue

            teacher, classroom = self._find_available_resources(task, lesson, slot, schedule)
            if teacher and classroom:
                entry = ScheduleEntry(
                    id=f"extra_{len(schedule.entries)}",
                    class_id=lesson["class_id"],
                    course_id=lesson["course_id"],
                    teacher_id=teacher.id,
                    classroom_id=classroom.id,
                    time_slot=slot,
                )
                schedule.add_entry(entry)
                return True

        # 如果找不到教师和教室，尝试只找教师（活动类课程可能不需要特定教室）
        course = task.courses.get(lesson["course_id"])
        if course and not course.is_main_subject:
            for slot in slots:
                if schedule.is_class_busy(lesson["class_id"], slot):
                    continue

                # 找能教这门课的教师
                eligible_teachers = [
                    t for t in task.teachers.values()
                    if t.can_teach(course.subject)
                ]

                for teacher in eligible_teachers:
                    if not schedule.is_teacher_busy(teacher.id, slot):
                        # 找任意可用教室
                        for classroom in task.classrooms.values():
                            if not schedule.is_classroom_busy(classroom.id, slot):
                                entry = ScheduleEntry(
                                    id=f"extra_{len(schedule.entries)}",
                                    class_id=lesson["class_id"],
                                    course_id=lesson["course_id"],
                                    teacher_id=teacher.id,
                                    classroom_id=classroom.id,
                                    time_slot=slot,
                                )
                                schedule.add_entry(entry)
                                return True

        return False

    def _ensure_afternoon_courses(self, schedule: Schedule, task: SchedulingTask,
                                   available_slots: List[TimeSlot],
                                   slot_config: dict = None) -> Schedule:
        """确保每天下午有足够课程"""
        logger.info("检查下午课程分布...")

        for class_id in task.classes.keys():
            for weekday in [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY,
                          Weekday.THURSDAY, Weekday.FRIDAY]:
                # 统计下午课程数
                afternoon_count = 0
                afternoon_slots = []
                for period in range(5, 9):
                    slot = TimeSlot(weekday=weekday, period=period)
                    entries = schedule.get_slot_entries(slot)
                    class_entries = [e for e in entries if e.class_id == class_id]
                    if class_entries:
                        afternoon_count += 1
                    else:
                        afternoon_slots.append(slot)

                # 如果下午课程不足，尝试补充
                if afternoon_count < self.MIN_AFTERNOON_COURSES and afternoon_slots:
                    # 找到这个班级还没安排的课程
                    placed_courses = set()
                    for entry in schedule.get_class_schedule(class_id):
                        placed_courses.add(entry.course_id)

                    for course_id, course in task.courses.items():
                        if course_id not in placed_courses:
                            # 尝试安排到下午
                            for slot in afternoon_slots:
                                if not schedule.is_class_busy(class_id, slot):
                                    teacher, classroom = self._find_available_resources(
                                        task,
                                        {"class_id": class_id, "course_id": course_id},
                                        slot,
                                        schedule
                                    )
                                    if teacher and classroom:
                                        entry = ScheduleEntry(
                                            id=f"afternoon_{len(schedule.entries)}",
                                            class_id=class_id,
                                            course_id=course_id,
                                            teacher_id=teacher.id,
                                            classroom_id=classroom.id,
                                            time_slot=slot,
                                        )
                                        schedule.add_entry(entry)
                                        placed_courses.add(course_id)
                                        afternoon_slots.remove(slot)
                                        afternoon_count += 1
                                        break

                            if afternoon_count >= self.MIN_AFTERNOON_COURSES:
                                break

        return schedule

    def _local_search_optimize(self, schedule: Schedule, task: SchedulingTask,
                               available_slots: List[TimeSlot],
                               slot_config: dict = None) -> Schedule:
        """局部搜索优化课表 - 专门解决冲突"""
        logger.info("开始局部搜索优化...")

        # 首先检测并解决现有冲突
        detector = ConflictDetector()
        conflicts = detector.detect_all(
            schedule, task.teachers, task.classrooms,
            task.courses, task.classes
        )

        if conflicts:
            logger.info(f"发现 {len(conflicts)} 个冲突，尝试解决...")
            schedule = self._resolve_conflicts(schedule, task, conflicts, available_slots)

        # 然后进行常规优化
        best_schedule = schedule
        best_score = self._evaluate_schedule(schedule, task)

        for i in range(self.max_iterations):
            entries = schedule.entries
            if len(entries) < 2:
                break

            idx1, idx2 = random.sample(range(len(entries)), 2)
            entry1 = entries[idx1]
            entry2 = entries[idx2]

            # 保存原始时间
            slot1 = entry1.time_slot
            slot2 = entry2.time_slot

            # 交换
            entry1.time_slot, entry2.time_slot = entry2.time_slot, entry1.time_slot

            # 检查是否会产生新的冲突
            has_conflict = self._check_swap_conflicts(schedule, entry1, entry2)

            if has_conflict:
                # 有冲突，撤销交换
                entry1.time_slot, entry2.time_slot = slot1, slot2
                continue

            # 评估
            new_score = self._evaluate_schedule(schedule, task)

            if new_score > best_score:
                best_score = new_score
                best_schedule = schedule
            else:
                entry1.time_slot, entry2.time_slot = slot1, slot2

        logger.info(f"优化完成，最终得分: {best_score}")
        return best_schedule

    def _check_swap_conflicts(self, schedule: Schedule, entry1: ScheduleEntry, entry2: ScheduleEntry) -> bool:
        """检查交换两个课程时间是否会产生冲突"""
        # 检查教师时间冲突
        for entry in schedule.entries:
            if entry.id == entry1.id or entry.id == entry2.id:
                continue
            if entry.teacher_id == entry1.teacher_id and entry.time_slot == entry1.time_slot:
                return True
            if entry.teacher_id == entry2.teacher_id and entry.time_slot == entry2.time_slot:
                return True

        # 检查班级时间冲突
        for entry in schedule.entries:
            if entry.id == entry1.id or entry.id == entry2.id:
                continue
            if entry.class_id == entry1.class_id and entry.time_slot == entry1.time_slot:
                return True
            if entry.class_id == entry2.class_id and entry.time_slot == entry2.time_slot:
                return True

        # 检查教室时间冲突
        for entry in schedule.entries:
            if entry.id == entry1.id or entry.id == entry2.id:
                continue
            if entry.classroom_id == entry1.classroom_id and entry.time_slot == entry1.time_slot:
                return True
            if entry.classroom_id == entry2.classroom_id and entry.time_slot == entry2.time_slot:
                return True

        return False

    def _resolve_conflicts(self, schedule: Schedule, task: SchedulingTask,
                           conflicts: List, available_slots: List[TimeSlot]) -> Schedule:
        """解决排课冲突"""
        logger.info("尝试解决排课冲突...")

        for conflict in conflicts:
            if conflict.type == ConflictType.TEACHER_TIME:
                # 教师时间冲突
                self._resolve_teacher_conflict(schedule, task, conflict, available_slots)
            elif conflict.type == ConflictType.CLASS_TIME:
                # 班级时间冲突
                self._resolve_class_conflict(schedule, task, conflict, available_slots)
            elif conflict.type == ConflictType.CLASSROOM_TIME:
                # 教室时间冲突
                self._resolve_classroom_conflict(schedule, task, conflict, available_slots)

        return schedule

    def _resolve_teacher_conflict(self, schedule: Schedule, task: SchedulingTask,
                                  conflict, available_slots: List[TimeSlot]):
        """解决教师时间冲突"""
        # 找到冲突的两个课程
        entries_in_slot = [e for e in schedule.entries
                          if e.teacher_id == conflict.entry1_id.split('_')[0]  # 简化处理
                          and e.time_slot == conflict.time_slot]

        if len(entries_in_slot) < 2:
            return

        # 尝试移动其中一个课程到其他时间
        entry_to_move = entries_in_slot[1]  # 移动第二个课程
        original_slot = entry_to_move.time_slot

        for slot in available_slots:
            if slot == original_slot:
                continue

            # 检查新时间段是否可用
            can_move = True
            for entry in schedule.entries:
                if entry.id == entry_to_move.id:
                    continue
                if entry.teacher_id == entry_to_move.teacher_id and entry.time_slot == slot:
                    can_move = False
                    break
                if entry.class_id == entry_to_move.class_id and entry.time_slot == slot:
                    can_move = False
                    break
                if entry.classroom_id == entry_to_move.classroom_id and entry.time_slot == slot:
                    can_move = False
                    break

            if can_move:
                entry_to_move.time_slot = slot
                logger.info(f"移动课程 {entry_to_move.id} 从 {original_slot} 到 {slot}")
                break

    def _resolve_class_conflict(self, schedule: Schedule, task: SchedulingTask,
                                conflict, available_slots: List[TimeSlot]):
        """解决班级时间冲突"""
        # 类似教师时间冲突的解决方法
        pass

    def _resolve_classroom_conflict(self, schedule: Schedule, task: SchedulingTask,
                                    conflict, available_slots: List[TimeSlot]):
        """解决教室时间冲突"""
        # 类似教师时间冲突的解决方法
        pass

    def _evaluate_schedule(self, schedule: Schedule, task: SchedulingTask) -> float:
        """评估课表质量"""
        score = 0

        # 1. 文理穿插得分
        for class_id in task.classes.keys():
            class_schedule = schedule.get_class_schedule(class_id)
            for i in range(len(class_schedule) - 1):
                entry1 = class_schedule[i]
                entry2 = class_schedule[i + 1]

                course1 = task.courses.get(entry1.course_id)
                course2 = task.courses.get(entry2.course_id)

                if course1 and course2:
                    group1 = get_subject_group(course1.subject)
                    group2 = get_subject_group(course2.subject)

                    if group1 != group2:
                        score += 10

        # 2. 教师工作量均衡
        teacher_hours = defaultdict(int)
        for entry in schedule.entries:
            teacher_hours[entry.teacher_id] += 1

        if teacher_hours:
            avg_hours = sum(teacher_hours.values()) / len(teacher_hours)
            variance = sum((h - avg_hours) ** 2 for h in teacher_hours.values()) / len(teacher_hours)
            score -= variance * 0.5

        # 3. 下午课程分布
        for class_id in task.classes.keys():
            for weekday in [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY,
                          Weekday.THURSDAY, Weekday.FRIDAY]:
                afternoon_count = 0
                for period in range(5, 9):
                    slot = TimeSlot(weekday=weekday, period=period)
                    entries = schedule.get_slot_entries(slot)
                    class_entries = [e for e in entries if e.class_id == class_id]
                    afternoon_count += len(class_entries)

                # 下午有课加分
                if afternoon_count >= 2:
                    score += 15
                elif afternoon_count == 1:
                    score += 5
                else:
                    score -= 10  # 下午没课扣分

        # 4. 避免同科目连续
        for class_id in task.classes.keys():
            class_schedule = schedule.get_class_schedule(class_id)
            for i in range(len(class_schedule) - 1):
                entry1 = class_schedule[i]
                entry2 = class_schedule[i + 1]

                if entry1.course_id == entry2.course_id:
                    score -= 20

        # 5. 活动类课程安排合理
        for entry in schedule.entries:
            course = task.courses.get(entry.course_id)
            if course and course.subject == "班会":
                # 班会安排在周五下午
                if entry.time_slot.weekday == Weekday.FRIDAY and entry.time_slot.period >= 7:
                    score += 30

        return score

    def optimize(self, schedule: Schedule, task: SchedulingTask,
                 iterations: int = 100) -> Schedule:
        """优化课表"""
        logger.info(f"开始优化课表，迭代 {iterations} 次...")
        available_slots = self._generate_available_slots()
        return self._local_search_optimize(schedule, task, available_slots)

    def adjust_schedule(self, schedule: Schedule, task: SchedulingTask,
                        entry_id: str, new_slot: TimeSlot) -> Tuple[bool, str]:
        """手动调整课表"""
        target_entry = None
        for entry in schedule.entries:
            if entry.id == entry_id:
                target_entry = entry
                break

        if not target_entry:
            return False, f"未找到记录 {entry_id}"

        old_slot = target_entry.time_slot
        target_entry.time_slot = new_slot

        if not task.constraints.check_hard_constraints(
            target_entry, schedule, task.teachers,
            task.classrooms, task.courses
        ):
            target_entry.time_slot = old_slot
            return False, f"时间段 {new_slot} 有冲突，无法调整"

        return True, f"已将 {entry_id} 调整到 {new_slot}"

    def swap_schedule(self, schedule: Schedule, task: SchedulingTask,
                      entry_id1: str, entry_id2: str) -> Tuple[bool, str]:
        """交换两个排课记录的时间段"""
        entry1 = None
        entry2 = None
        for entry in schedule.entries:
            if entry.id == entry_id1:
                entry1 = entry
            elif entry.id == entry_id2:
                entry2 = entry

        if not entry1 or not entry2:
            return False, "未找到要交换的记录"

        slot1 = entry1.time_slot
        slot2 = entry2.time_slot

        entry1.time_slot = slot2
        entry2.time_slot = slot1

        valid1 = task.constraints.check_hard_constraints(
            entry1, schedule, task.teachers, task.classrooms, task.courses
        )
        valid2 = task.constraints.check_hard_constraints(
            entry2, schedule, task.teachers, task.classrooms, task.courses
        )

        if not valid1 or not valid2:
            entry1.time_slot = slot1
            entry2.time_slot = slot2
            return False, "交换后有冲突，无法执行"

        return True, f"已交换 {entry_id1} 和 {entry_id2} 的时间段"
