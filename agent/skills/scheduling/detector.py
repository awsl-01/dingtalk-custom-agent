"""
冲突检测模块

检测和报告排课中的冲突：
- 教师时间冲突
- 班级时间冲突
- 教室时间冲突
- 软约束违反
"""
from enum import Enum
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .models import (
    TimeSlot, Teacher, Classroom, Course, ClassGroup,
    ScheduleEntry, Schedule, Weekday,
)


class ConflictType(Enum):
    """冲突类型"""
    TEACHER_TIME = "教师时间冲突"
    CLASS_TIME = "班级时间冲突"
    CLASSROOM_TIME = "教室时间冲突"
    TEACHER_AVAILABILITY = "教师不可用"
    ROOM_CAPACITY = "教室容量不足"
    EQUIPMENT_MISSING = "设备缺失"
    SOFT_CONSTRAINT = "软约束违反"


@dataclass
class Conflict:
    """冲突记录"""
    type: ConflictType
    severity: str  # "error" 或 "warning"
    message: str
    entry1_id: str
    entry2_id: Optional[str] = None
    time_slot: Optional[TimeSlot] = None
    suggestion: str = ""


class ConflictDetector:
    """
    冲突检测器

    检测排课中的各种冲突并提供修复建议
    """

    def __init__(self):
        self.conflicts: List[Conflict] = []

    def detect_all(self, schedule: Schedule,
                   teachers: Dict[str, Teacher],
                   classrooms: Dict[str, Classroom],
                   courses: Dict[str, Course],
                   classes: Dict[str, ClassGroup]) -> List[Conflict]:
        """
        检测所有冲突

        返回:
            冲突列表
        """
        self.conflicts = []

        # 检测硬约束冲突
        self._detect_teacher_conflicts(schedule, teachers)
        self._detect_class_conflicts(schedule)
        self._detect_classroom_conflicts(schedule)
        self._detect_teacher_availability(schedule, teachers)
        self._detect_room_capacity(schedule, classrooms, classes)
        self._detect_equipment(schedule, classrooms, courses)

        return self.conflicts

    def _detect_teacher_conflicts(self, schedule: Schedule,
                                  teachers: Dict[str, Teacher]):
        """检测教师时间冲突"""
        teacher_slots: Dict[str, Dict[TimeSlot, List[ScheduleEntry]]] = {}

        for entry in schedule.entries:
            if entry.teacher_id not in teacher_slots:
                teacher_slots[entry.teacher_id] = {}
            if entry.time_slot not in teacher_slots[entry.teacher_id]:
                teacher_slots[entry.teacher_id][entry.time_slot] = []
            teacher_slots[entry.teacher_id][entry.time_slot].append(entry)

        for teacher_id, slots in teacher_slots.items():
            teacher = teachers.get(teacher_id)
            teacher_name = teacher.name if teacher else teacher_id

            for slot, entries in slots.items():
                if len(entries) > 1:
                    for i in range(len(entries)):
                        for j in range(i + 1, len(entries)):
                            self.conflicts.append(Conflict(
                                type=ConflictType.TEACHER_TIME,
                                severity="error",
                                message=f"教师 {teacher_name} 在 {slot} 有 {len(entries)} 节课冲突",
                                entry1_id=entries[i].id,
                                entry2_id=entries[j].id,
                                time_slot=slot,
                                suggestion=f"请调整其中一门课程的时间",
                            ))

    def _detect_class_conflicts(self, schedule: Schedule):
        """检测班级时间冲突"""
        class_slots: Dict[str, Dict[TimeSlot, List[ScheduleEntry]]] = {}

        for entry in schedule.entries:
            if entry.class_id not in class_slots:
                class_slots[entry.class_id] = {}
            if entry.time_slot not in class_slots[entry.class_id]:
                class_slots[entry.class_id][entry.time_slot] = []
            class_slots[entry.class_id][entry.time_slot].append(entry)

        for class_id, slots in class_slots.items():
            for slot, entries in slots.items():
                if len(entries) > 1:
                    for i in range(len(entries)):
                        for j in range(i + 1, len(entries)):
                            self.conflicts.append(Conflict(
                                type=ConflictType.CLASS_TIME,
                                severity="error",
                                message=f"班级 {class_id} 在 {slot} 有 {len(entries)} 节课冲突",
                                entry1_id=entries[i].id,
                                entry2_id=entries[j].id,
                                time_slot=slot,
                                suggestion=f"请调整其中一门课程的时间",
                            ))

    def _detect_classroom_conflicts(self, schedule: Schedule):
        """检测教室时间冲突"""
        room_slots: Dict[str, Dict[TimeSlot, List[ScheduleEntry]]] = {}

        for entry in schedule.entries:
            if entry.classroom_id not in room_slots:
                room_slots[entry.classroom_id] = {}
            if entry.time_slot not in room_slots[entry.classroom_id]:
                room_slots[entry.classroom_id][entry.time_slot] = []
            room_slots[entry.classroom_id][entry.time_slot].append(entry)

        for room_id, slots in room_slots.items():
            for slot, entries in slots.items():
                if len(entries) > 1:
                    for i in range(len(entries)):
                        for j in range(i + 1, len(entries)):
                            self.conflicts.append(Conflict(
                                type=ConflictType.CLASSROOM_TIME,
                                severity="error",
                                message=f"教室 {room_id} 在 {slot} 有 {len(entries)} 节课冲突",
                                entry1_id=entries[i].id,
                                entry2_id=entries[j].id,
                                time_slot=slot,
                                suggestion=f"请更换教室或调整时间",
                            ))

    def _detect_teacher_availability(self, schedule: Schedule,
                                     teachers: Dict[str, Teacher]):
        """检测教师可用性"""
        for entry in schedule.entries:
            teacher = teachers.get(entry.teacher_id)
            if not teacher:
                continue

            if not teacher.is_available(entry.time_slot):
                self.conflicts.append(Conflict(
                    type=ConflictType.TEACHER_AVAILABILITY,
                    severity="error",
                    message=f"教师 {teacher.name} 在 {entry.time_slot} 不可用",
                    entry1_id=entry.id,
                    time_slot=entry.time_slot,
                    suggestion=f"请将此课程调整到教师的可用时间段",
                ))

    def _detect_room_capacity(self, schedule: Schedule,
                              classrooms: Dict[str, Classroom],
                              classes: Dict[str, ClassGroup]):
        """检测教室容量"""
        for entry in schedule.entries:
            classroom = classrooms.get(entry.classroom_id)
            class_group = classes.get(entry.class_id)

            if not classroom or not class_group:
                continue

            if classroom.capacity < class_group.student_count:
                self.conflicts.append(Conflict(
                    type=ConflictType.ROOM_CAPACITY,
                    severity="warning",
                    message=f"教室 {classroom.name} 容量({classroom.capacity}) "
                            f"小于班级 {class_group.name} 人数({class_group.student_count})",
                    entry1_id=entry.id,
                    suggestion=f"建议更换容量更大的教室",
                ))

    def _detect_equipment(self, schedule: Schedule,
                          classrooms: Dict[str, Classroom],
                          courses: Dict[str, Course]):
        """检测设备需求"""
        for entry in schedule.entries:
            classroom = classrooms.get(entry.classroom_id)
            course = courses.get(entry.course_id)

            if not classroom or not course:
                continue

            for equipment in course.required_equipment:
                if not classroom.has_equipment(equipment):
                    self.conflicts.append(Conflict(
                        type=ConflictType.EQUIPMENT_MISSING,
                        severity="warning",
                        message=f"课程 {course.name} 需要 {equipment}，"
                                f"但教室 {classroom.name} 没有该设备",
                        entry1_id=entry.id,
                        suggestion=f"建议更换到有 {equipment} 的教室",
                    ))

    def get_summary(self) -> Dict:
        """获取冲突摘要"""
        summary = {
            "total": len(self.conflicts),
            "errors": 0,
            "warnings": 0,
            "by_type": {},
        }

        for conflict in self.conflicts:
            if conflict.severity == "error":
                summary["errors"] += 1
            else:
                summary["warnings"] += 1

            type_name = conflict.type.value
            if type_name not in summary["by_type"]:
                summary["by_type"][type_name] = 0
            summary["by_type"][type_name] += 1

        return summary

    def format_report(self, teachers: Dict[str, Teacher] = None,
                      courses: Dict[str, Course] = None) -> str:
        """
        格式化冲突报告

        返回:
            可读的冲突报告文本
        """
        if not self.conflicts:
            return "✅ 未检测到任何冲突！"

        summary = self.get_summary()
        lines = [
            f"⚠️ 冲突检测报告",
            f"",
            f"总计: {summary['total']} 个冲突",
            f"  - 错误: {summary['errors']} 个（必须修复）",
            f"  - 警告: {summary['warnings']} 个（建议修复）",
            f"",
            f"冲突详情:",
        ]

        # 按类型分组显示
        for type_name, count in summary["by_type"].items():
            lines.append(f"\n【{type_name}】({count}个)")
            for conflict in self.conflicts:
                if conflict.type.value == type_name:
                    lines.append(f"  • {conflict.message}")
                    if conflict.suggestion:
                        lines.append(f"    💡 {conflict.suggestion}")

        return "\n".join(lines)

    def get_fixable_conflicts(self) -> List[Tuple[Conflict, str]]:
        """
        获取可自动修复的冲突

        返回:
            (冲突, 修复建议) 元组列表
        """
        fixable = []
        for conflict in self.conflicts:
            if conflict.type == ConflictType.TEACHER_TIME:
                fixable.append((conflict, "swap_time"))
            elif conflict.type == ConflictType.CLASS_TIME:
                fixable.append((conflict, "swap_time"))
            elif conflict.type == ConflictType.CLASSROOM_TIME:
                fixable.append((conflict, "swap_room"))
        return fixable
