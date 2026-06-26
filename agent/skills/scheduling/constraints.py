"""
约束条件管理模块

管理排课的硬约束和软约束：
- 硬约束：必须满足的条件（如教师时间冲突）
- 软约束：尽量满足的条件（如课程均匀分布）
"""
from enum import Enum
from typing import List, Dict, Set, Callable, Optional
from dataclasses import dataclass

from .models import (
    TimeSlot, Teacher, Classroom, Course, ClassGroup,
    ScheduleEntry, Schedule, Weekday, PeriodType,
)


class ConstraintType(Enum):
    """约束类型"""
    HARD = "硬约束"  # 必须满足
    SOFT = "软约束"  # 尽量满足


@dataclass
class ConstraintResult:
    """约束检查结果"""
    passed: bool
    constraint_name: str
    constraint_type: ConstraintType
    message: str = ""
    penalty: int = 0  # 软约束的惩罚分数


class ConstraintManager:
    """
    约束条件管理器

    管理和检查所有排课约束条件
    """

    def __init__(self):
        self.hard_constraints: List[Callable] = []
        self.soft_constraints: List[Callable] = []
        self.config = {
            "max_consecutive_hours": 3,  # 最大连排课时
            "main_subject_prefer_morning": True,  # 主课优先上午
            "min_course_interval_days": 1,  # 同课程最小间隔天数
            "max_daily_hours_per_teacher": 4,  # 教师每天最大课时
            "course_even_distribution": True,  # 课程均匀分布
            "max_same_subject_per_day": 2,  # 同科目单日最多节数
            # 软约束惩罚分值配置
            "penalty_main_subject_afternoon": 10,  # 主课安排在下午的惩罚
            "penalty_consecutive_over_limit": 5,  # 超过连排上限的惩罚（每节）
            "penalty_teacher_daily_over": 8,  # 教师每日课时超限惩罚
            "penalty_same_course_same_day": 6,  # 同课程同一天重复惩罚
            "penalty_same_subject_over_limit": 4,  # 同科目超过单日上限惩罚
        }
        self._register_default_constraints()

    def _register_default_constraints(self):
        """注册默认约束条件"""
        # 硬约束
        self.hard_constraints = [
            self._check_teacher_conflict,
            self._check_class_conflict,
            self._check_classroom_conflict,
            self._check_teacher_availability,
        ]

        # 软约束
        self.soft_constraints = [
            self._check_main_subject_morning,
            self._check_consecutive_hours,
            self._check_teacher_daily_limit,
            self._check_course_distribution,
        ]

    def update_config(self, config: dict):
        """更新约束配置"""
        self.config.update(config)

    def check_all(self, entry: ScheduleEntry, schedule: Schedule,
                  teachers: Dict[str, Teacher],
                  classrooms: Dict[str, Classroom],
                  courses: Dict[str, Course]) -> List[ConstraintResult]:
        """
        检查所有约束条件

        返回:
            所有约束检查结果列表
        """
        results = []

        # 检查硬约束
        for constraint_func in self.hard_constraints:
            result = constraint_func(entry, schedule, teachers, classrooms, courses)
            results.append(result)

        # 检查软约束
        for constraint_func in self.soft_constraints:
            result = constraint_func(entry, schedule, teachers, classrooms, courses)
            results.append(result)

        return results

    def check_hard_constraints(self, entry: ScheduleEntry, schedule: Schedule,
                               teachers: Dict[str, Teacher],
                               classrooms: Dict[str, Classroom],
                               courses: Dict[str, Course]) -> bool:
        """
        检查是否满足所有硬约束

        返回:
            True 表示满足所有硬约束
        """
        for constraint_func in self.hard_constraints:
            result = constraint_func(entry, schedule, teachers, classrooms, courses)
            if not result.passed:
                return False
        return True

    def calculate_penalty(self, entry: ScheduleEntry, schedule: Schedule,
                          teachers: Dict[str, Teacher],
                          classrooms: Dict[str, Classroom],
                          courses: Dict[str, Course]) -> int:
        """
        计算软约束的总惩罚分数

        返回:
            惩罚分数（越低越好）
        """
        total_penalty = 0
        for constraint_func in self.soft_constraints:
            result = constraint_func(entry, schedule, teachers, classrooms, courses)
            total_penalty += result.penalty
        return total_penalty

    # ========== 硬约束检查 ==========

    def _check_teacher_conflict(self, entry: ScheduleEntry, schedule: Schedule,
                                teachers: Dict[str, Teacher],
                                classrooms: Dict[str, Classroom],
                                courses: Dict[str, Course]) -> ConstraintResult:
        """检查教师时间冲突"""
        if schedule.is_teacher_busy(entry.teacher_id, entry.time_slot):
            return ConstraintResult(
                passed=False,
                constraint_name="教师时间冲突",
                constraint_type=ConstraintType.HARD,
                message=f"教师在 {entry.time_slot} 已有其他课程",
            )
        return ConstraintResult(
            passed=True,
            constraint_name="教师时间冲突",
            constraint_type=ConstraintType.HARD,
        )

    def _check_class_conflict(self, entry: ScheduleEntry, schedule: Schedule,
                              teachers: Dict[str, Teacher],
                              classrooms: Dict[str, Classroom],
                              courses: Dict[str, Course]) -> ConstraintResult:
        """检查班级时间冲突"""
        if schedule.is_class_busy(entry.class_id, entry.time_slot):
            return ConstraintResult(
                passed=False,
                constraint_name="班级时间冲突",
                constraint_type=ConstraintType.HARD,
                message=f"班级在 {entry.time_slot} 已有其他课程",
            )
        return ConstraintResult(
            passed=True,
            constraint_name="班级时间冲突",
            constraint_type=ConstraintType.HARD,
        )

    def _check_classroom_conflict(self, entry: ScheduleEntry, schedule: Schedule,
                                  teachers: Dict[str, Teacher],
                                  classrooms: Dict[str, Classroom],
                                  courses: Dict[str, Course]) -> ConstraintResult:
        """检查教室时间冲突"""
        if schedule.is_classroom_busy(entry.classroom_id, entry.time_slot):
            return ConstraintResult(
                passed=False,
                constraint_name="教室时间冲突",
                constraint_type=ConstraintType.HARD,
                message=f"教室在 {entry.time_slot} 已被占用",
            )
        return ConstraintResult(
            passed=True,
            constraint_name="教室时间冲突",
            constraint_type=ConstraintType.HARD,
        )

    def _check_teacher_availability(self, entry: ScheduleEntry, schedule: Schedule,
                                    teachers: Dict[str, Teacher],
                                    classrooms: Dict[str, Classroom],
                                    courses: Dict[str, Course]) -> ConstraintResult:
        """检查教师可用性"""
        teacher = teachers.get(entry.teacher_id)
        if not teacher:
            return ConstraintResult(
                passed=False,
                constraint_name="教师可用性",
                constraint_type=ConstraintType.HARD,
                message="教师不存在",
            )

        if not teacher.is_available(entry.time_slot):
            return ConstraintResult(
                passed=False,
                constraint_name="教师可用性",
                constraint_type=ConstraintType.HARD,
                message=f"教师在 {entry.time_slot} 不可用",
            )
        return ConstraintResult(
            passed=True,
            constraint_name="教师可用性",
            constraint_type=ConstraintType.HARD,
        )

    # ========== 软约束检查 ==========

    def _check_main_subject_morning(self, entry: ScheduleEntry, schedule: Schedule,
                                    teachers: Dict[str, Teacher],
                                    classrooms: Dict[str, Classroom],
                                    courses: Dict[str, Course]) -> ConstraintResult:
        """检查主课是否在上午"""
        if not self.config.get("main_subject_prefer_morning", True):
            return ConstraintResult(
                passed=True,
                constraint_name="主课优先上午",
                constraint_type=ConstraintType.SOFT,
            )

        course = courses.get(entry.course_id)
        if not course:
            return ConstraintResult(
                passed=True,
                constraint_name="主课优先上午",
                constraint_type=ConstraintType.SOFT,
            )

        if course.is_main_subject and entry.time_slot.period_type != PeriodType.MORNING:
            penalty = self.config.get("penalty_main_subject_afternoon", 10)
            return ConstraintResult(
                passed=False,
                constraint_name="主课优先上午",
                constraint_type=ConstraintType.SOFT,
                message=f"主课 {course.name} 建议安排在上午",
                penalty=penalty,
            )
        return ConstraintResult(
            passed=True,
            constraint_name="主课优先上午",
            constraint_type=ConstraintType.SOFT,
        )

    def _check_consecutive_hours(self, entry: ScheduleEntry, schedule: Schedule,
                                 teachers: Dict[str, Teacher],
                                 classrooms: Dict[str, Classroom],
                                 courses: Dict[str, Course]) -> ConstraintResult:
        """检查连排课时限制"""
        max_consecutive = self.config.get("max_consecutive_hours", 3)
        teacher = teachers.get(entry.teacher_id)

        if not teacher:
            return ConstraintResult(
                passed=True,
                constraint_name="连排课时限制",
                constraint_type=ConstraintType.SOFT,
            )

        # 检查教师当天的连续课时
        teacher_schedule = schedule.get_teacher_schedule(entry.teacher_id)
        day_entries = [e for e in teacher_schedule
                      if e.time_slot.weekday == entry.time_slot.weekday]

        if not day_entries:
            return ConstraintResult(
                passed=True,
                constraint_name="连排课时限制",
                constraint_type=ConstraintType.SOFT,
            )

        # 计算连续课时
        periods = sorted([e.time_slot.period for e in day_entries] + [entry.time_slot.period])
        max_consecutive_found = 1
        current_consecutive = 1
        for i in range(1, len(periods)):
            if periods[i] == periods[i-1] + 1:
                current_consecutive += 1
                max_consecutive_found = max(max_consecutive_found, current_consecutive)
            else:
                current_consecutive = 1

        if max_consecutive_found > max_consecutive:
            penalty_per_over = self.config.get("penalty_consecutive_over_limit", 5)
            return ConstraintResult(
                passed=False,
                constraint_name="连排课时限制",
                constraint_type=ConstraintType.SOFT,
                message=f"连续课时超过 {max_consecutive} 节",
                penalty=penalty_per_over * (max_consecutive_found - max_consecutive),
            )
        return ConstraintResult(
            passed=True,
            constraint_name="连排课时限制",
            constraint_type=ConstraintType.SOFT,
        )

    def _check_teacher_daily_limit(self, entry: ScheduleEntry, schedule: Schedule,
                                   teachers: Dict[str, Teacher],
                                   classrooms: Dict[str, Classroom],
                                   courses: Dict[str, Course]) -> ConstraintResult:
        """检查教师每日课时限制"""
        teacher = teachers.get(entry.teacher_id)
        if not teacher:
            return ConstraintResult(
                passed=True,
                constraint_name="教师每日课时限制",
                constraint_type=ConstraintType.SOFT,
            )

        daily_hours = schedule.get_teacher_daily_hours(entry.teacher_id, entry.time_slot.weekday)
        if daily_hours >= teacher.max_hours_per_day:
            penalty = self.config.get("penalty_teacher_daily_over", 8)
            return ConstraintResult(
                passed=False,
                constraint_name="教师每日课时限制",
                constraint_type=ConstraintType.SOFT,
                message=f"教师当天课时已达上限 {teacher.max_hours_per_day}",
                penalty=penalty,
            )
        return ConstraintResult(
            passed=True,
            constraint_name="教师每日课时限制",
            constraint_type=ConstraintType.SOFT,
        )

    def _check_course_distribution(self, entry: ScheduleEntry, schedule: Schedule,
                                   teachers: Dict[str, Teacher],
                                   classrooms: Dict[str, Classroom],
                                   courses: Dict[str, Course]) -> ConstraintResult:
        """检查课程分布均匀性"""
        if not self.config.get("course_even_distribution", True):
            return ConstraintResult(
                passed=True,
                constraint_name="课程分布均匀",
                constraint_type=ConstraintType.SOFT,
            )

        # 检查同一班级同一课程是否在同一天重复
        class_schedule = schedule.get_class_schedule(entry.class_id)
        same_course_same_day = [
            e for e in class_schedule
            if e.course_id == entry.course_id
            and e.time_slot.weekday == entry.time_slot.weekday
        ]

        if same_course_same_day:
            penalty = self.config.get("penalty_same_course_same_day", 6)
            return ConstraintResult(
                passed=False,
                constraint_name="课程分布均匀",
                constraint_type=ConstraintType.SOFT,
                message="同一课程在同一天重复",
                penalty=penalty,
            )

        # 检查同科目单日上限
        course = courses.get(entry.course_id)
        if course:
            max_same = self.config.get("max_same_subject_per_day", 2)
            same_subject_count = sum(
                1 for e in class_schedule
                if e.time_slot.weekday == entry.time_slot.weekday
                and courses.get(e.course_id, Course(id="", name="", subject="")).subject == course.subject
            )
            if same_subject_count >= max_same:
                penalty = self.config.get("penalty_same_subject_over_limit", 4)
                return ConstraintResult(
                    passed=False,
                    constraint_name="同科目单日上限",
                    constraint_type=ConstraintType.SOFT,
                    message=f"同科目 {course.subject} 当天已达上限 {max_same} 节",
                    penalty=penalty,
                )

        return ConstraintResult(
            passed=True,
            constraint_name="课程分布均匀",
            constraint_type=ConstraintType.SOFT,
        )
