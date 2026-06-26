"""
排课系统数据模型

定义排课所需的所有数据结构：
- TimeSlot: 时间段
- Teacher: 教师
- Classroom: 教室
- Course: 课程
- ClassGroup: 班级
- ScheduleEntry: 排课记录
- Schedule: 完整课表
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum
import json


class Weekday(Enum):
    """星期"""
    MONDAY = "周一"
    TUESDAY = "周二"
    WEDNESDAY = "周三"
    THURSDAY = "周四"
    FRIDAY = "周五"
    SATURDAY = "周六"
    SUNDAY = "周日"


class PeriodType(Enum):
    """节次类型"""
    MORNING = "上午"
    AFTERNOON = "下午"
    EVENING = "晚上"


@dataclass
class TimeSlot:
    """
    时间段

    表示一周中的某个具体时间段
    """
    weekday: Weekday
    period: int  # 第几节课（1-10）
    period_type: PeriodType = None

    def __post_init__(self):
        """自动计算节次类型"""
        if self.period_type is None:
            if self.period <= 4:
                self.period_type = PeriodType.MORNING
            elif self.period <= 8:
                self.period_type = PeriodType.AFTERNOON
            else:
                self.period_type = PeriodType.EVENING

    def __str__(self):
        return f"{self.weekday.value}第{self.period}节"

    def __hash__(self):
        return hash((self.weekday, self.period))

    def __eq__(self, other):
        if not isinstance(other, TimeSlot):
            return False
        return self.weekday == other.weekday and self.period == other.period

    def to_dict(self):
        return {
            "weekday": self.weekday.value,
            "period": self.period,
            "period_type": self.period_type.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TimeSlot':
        weekday_map = {
            "周一": Weekday.MONDAY,
            "周二": Weekday.TUESDAY,
            "周三": Weekday.WEDNESDAY,
            "周四": Weekday.THURSDAY,
            "周五": Weekday.FRIDAY,
            "周六": Weekday.SATURDAY,
            "周日": Weekday.SUNDAY,
        }
        return cls(
            weekday=weekday_map.get(data["weekday"], Weekday.MONDAY),
            period=data["period"],
        )


@dataclass
class Teacher:
    """
    教师信息

    属性:
        id: 教师唯一标识
        name: 教师姓名
        subjects: 可教授的科目列表
        available_slots: 可用时间段集合
        max_hours_per_day: 每天最大课时数
        max_hours_per_week: 每周最大课时数
        preferred_slots: 偏好时间段（软约束）
        unavailable_slots: 不可用时间段
    """
    id: str
    name: str
    subjects: List[str] = field(default_factory=list)
    available_slots: Set[TimeSlot] = field(default_factory=set)
    max_hours_per_day: int = 4
    max_hours_per_week: int = 20
    preferred_slots: Set[TimeSlot] = field(default_factory=set)
    unavailable_slots: Set[TimeSlot] = field(default_factory=set)

    def is_available(self, slot: TimeSlot) -> bool:
        """检查教师在指定时间段是否可用"""
        if slot in self.unavailable_slots:
            return False
        if not self.available_slots:  # 如果没有设置可用时间，默认都可用
            return True
        return slot in self.available_slots

    def can_teach(self, subject: str) -> bool:
        """检查教师是否能教授指定科目"""
        return subject in self.subjects

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "subjects": self.subjects,
            "max_hours_per_day": self.max_hours_per_day,
            "max_hours_per_week": self.max_hours_per_week,
            "available_slots": [s.to_dict() for s in self.available_slots],
            "preferred_slots": [s.to_dict() for s in self.preferred_slots],
            "unavailable_slots": [s.to_dict() for s in self.unavailable_slots],
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Teacher':
        teacher = cls(
            id=data["id"],
            name=data["name"],
            subjects=data.get("subjects", []),
            max_hours_per_day=data.get("max_hours_per_day", 4),
            max_hours_per_week=data.get("max_hours_per_week", 20),
        )
        teacher.available_slots = {TimeSlot.from_dict(s) for s in data.get("available_slots", [])}
        teacher.preferred_slots = {TimeSlot.from_dict(s) for s in data.get("preferred_slots", [])}
        teacher.unavailable_slots = {TimeSlot.from_dict(s) for s in data.get("unavailable_slots", [])}
        return teacher


@dataclass
class Classroom:
    """
    教室信息

    属性:
        id: 教室唯一标识
        name: 教室名称
        capacity: 教室容量
        equipment: 设备列表（多媒体、实验室等）
        building: 所在教学楼
    """
    id: str
    name: str
    capacity: int = 50
    equipment: List[str] = field(default_factory=list)
    building: str = ""

    def has_equipment(self, required: str) -> bool:
        """检查教室是否有指定设备（支持名称匹配）"""
        # 1. 检查设备列表
        if required in self.equipment:
            return True
        # 2. 检查教室名称是否包含所需设备关键词
        #    例如：课程需要"实验室"，教室名称是"实验室1" → 匹配
        if required in self.name:
            return True
        # 3. 检查设备列表中的项是否包含所需关键词
        for equip in self.equipment:
            if required in equip or equip in required:
                return True
        return False

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "capacity": self.capacity,
            "equipment": self.equipment,
            "building": self.building,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Classroom':
        return cls(
            id=data["id"],
            name=data["name"],
            capacity=data.get("capacity", 50),
            equipment=data.get("equipment", []),
            building=data.get("building", ""),
        )


@dataclass
class Course:
    """
    课程信息

    属性:
        id: 课程唯一标识
        name: 课程名称
        subject: 学科
        hours_per_week: 每周课时数
        needs_consecutive: 是否需要连排（两节连上）
        consecutive_hours: 连排节数（2=两节连排，3=三节连排）
        required_equipment: 所需设备
        is_main_subject: 是否主课（语数外等）
        grade: 年级
        weight: 课程权重（用于排序，越高越优先）
        max_per_day: 单日最大节数
        room_type: 专属教室类型（如"实验室"、"多媒体"，空表示普通教室）
    """
    id: str
    name: str
    subject: str
    hours_per_week: int = 2
    needs_consecutive: bool = False
    consecutive_hours: int = 2  # 连排节数
    required_equipment: List[str] = field(default_factory=list)
    is_main_subject: bool = False
    grade: str = ""
    weight: int = 0  # 课程权重，主课自动设为100+
    max_per_day: int = 2  # 单日最大节数
    room_type: str = ""  # 专属教室类型

    def __post_init__(self):
        """自动计算权重"""
        if self.weight == 0:
            # 主课基础权重100，副课50，再加周课时数作为细粒度权重
            base = 100 if self.is_main_subject else 50
            self.weight = base + self.hours_per_week

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "subject": self.subject,
            "hours_per_week": self.hours_per_week,
            "needs_consecutive": self.needs_consecutive,
            "consecutive_hours": self.consecutive_hours,
            "required_equipment": self.required_equipment,
            "is_main_subject": self.is_main_subject,
            "grade": self.grade,
            "weight": self.weight,
            "max_per_day": self.max_per_day,
            "room_type": self.room_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Course':
        return cls(
            id=data["id"],
            name=data["name"],
            subject=data["subject"],
            hours_per_week=data.get("hours_per_week", 2),
            needs_consecutive=data.get("needs_consecutive", False),
            consecutive_hours=data.get("consecutive_hours", 2),
            required_equipment=data.get("required_equipment", []),
            is_main_subject=data.get("is_main_subject", False),
            grade=data.get("grade", ""),
            weight=data.get("weight", 0),
            max_per_day=data.get("max_per_day", 2),
            room_type=data.get("room_type", ""),
        )


@dataclass
class ClassGroup:
    """
    班级信息

    属性:
        id: 班级唯一标识
        name: 班级名称
        grade: 年级
        student_count: 学生人数
        courses: 需要上的课程列表
        homeroom_teacher: 班主任
        assigned_classrooms: 固定教室列表（如 ["101教室", "102教室"]）
    """
    id: str
    name: str
    grade: str = ""
    student_count: int = 45
    courses: List[str] = field(default_factory=list)  # 课程ID列表
    homeroom_teacher: str = ""
    assigned_classrooms: List[str] = field(default_factory=list)  # 固定教室名称列表

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "grade": self.grade,
            "student_count": self.student_count,
            "courses": self.courses,
            "homeroom_teacher": self.homeroom_teacher,
            "assigned_classrooms": self.assigned_classrooms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ClassGroup':
        return cls(
            id=data["id"],
            name=data["name"],
            grade=data.get("grade", ""),
            student_count=data.get("student_count", 45),
            courses=data.get("courses", []),
            homeroom_teacher=data.get("homeroom_teacher", ""),
            assigned_classrooms=data.get("assigned_classrooms", []),
        )


@dataclass
class ScheduleEntry:
    """
    排课记录

    表示一节课的安排
    """
    id: str
    class_id: str      # 班级ID
    course_id: str      # 课程ID
    teacher_id: str     # 教师ID
    classroom_id: str   # 教室ID
    time_slot: TimeSlot # 时间段
    is_fixed: bool = False  # 是否固定（不可调课）

    def to_dict(self):
        return {
            "id": self.id,
            "class_id": self.class_id,
            "course_id": self.course_id,
            "teacher_id": self.teacher_id,
            "classroom_id": self.classroom_id,
            "time_slot": self.time_slot.to_dict(),
            "is_fixed": self.is_fixed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ScheduleEntry':
        return cls(
            id=data["id"],
            class_id=data["class_id"],
            course_id=data["course_id"],
            teacher_id=data["teacher_id"],
            classroom_id=data["classroom_id"],
            time_slot=TimeSlot.from_dict(data["time_slot"]),
            is_fixed=data.get("is_fixed", False),
        )


class Schedule:
    """
    完整课表

    管理所有排课记录，提供查询和操作方法
    """

    def __init__(self):
        self.entries: List[ScheduleEntry] = []
        self._index_by_class: Dict[str, List[ScheduleEntry]] = {}
        self._index_by_teacher: Dict[str, List[ScheduleEntry]] = {}
        self._index_by_classroom: Dict[str, List[ScheduleEntry]] = {}
        self._index_by_slot: Dict[TimeSlot, List[ScheduleEntry]] = {}

    def add_entry(self, entry: ScheduleEntry):
        """添加排课记录"""
        self.entries.append(entry)
        self._update_indexes(entry)

    def remove_entry(self, entry_id: str):
        """移除排课记录"""
        self.entries = [e for e in self.entries if e.id != entry_id]
        self._rebuild_indexes()

    def _update_indexes(self, entry: ScheduleEntry):
        """更新索引"""
        # 按班级索引
        if entry.class_id not in self._index_by_class:
            self._index_by_class[entry.class_id] = []
        self._index_by_class[entry.class_id].append(entry)

        # 按教师索引
        if entry.teacher_id not in self._index_by_teacher:
            self._index_by_teacher[entry.teacher_id] = []
        self._index_by_teacher[entry.teacher_id].append(entry)

        # 按教室索引
        if entry.classroom_id not in self._index_by_classroom:
            self._index_by_classroom[entry.classroom_id] = []
        self._index_by_classroom[entry.classroom_id].append(entry)

        # 按时间段索引
        if entry.time_slot not in self._index_by_slot:
            self._index_by_slot[entry.time_slot] = []
        self._index_by_slot[entry.time_slot].append(entry)

    def _rebuild_indexes(self):
        """重建所有索引"""
        self._index_by_class.clear()
        self._index_by_teacher.clear()
        self._index_by_classroom.clear()
        self._index_by_slot.clear()
        for entry in self.entries:
            self._update_indexes(entry)

    def get_class_schedule(self, class_id: str) -> List[ScheduleEntry]:
        """获取班级课表"""
        return self._index_by_class.get(class_id, [])

    def get_teacher_schedule(self, teacher_id: str) -> List[ScheduleEntry]:
        """获取教师课表"""
        return self._index_by_teacher.get(teacher_id, [])

    def get_classroom_schedule(self, classroom_id: str) -> List[ScheduleEntry]:
        """获取教室使用情况"""
        return self._index_by_classroom.get(classroom_id, [])

    def get_slot_entries(self, slot: TimeSlot) -> List[ScheduleEntry]:
        """获取指定时间段的所有安排"""
        return self._index_by_slot.get(slot, [])

    def is_class_busy(self, class_id: str, slot: TimeSlot) -> bool:
        """检查班级在指定时间段是否有课"""
        for entry in self.get_class_schedule(class_id):
            if entry.time_slot == slot:
                return True
        return False

    def is_teacher_busy(self, teacher_id: str, slot: TimeSlot) -> bool:
        """检查教师在指定时间段是否有课"""
        for entry in self.get_teacher_schedule(teacher_id):
            if entry.time_slot == slot:
                return True
        return False

    def is_classroom_busy(self, classroom_id: str, slot: TimeSlot) -> bool:
        """检查教室在指定时间段是否被占用"""
        for entry in self.get_classroom_schedule(classroom_id):
            if entry.time_slot == slot:
                return True
        return False

    def get_teacher_daily_hours(self, teacher_id: str, weekday: Weekday) -> int:
        """获取教师某天的课时数"""
        count = 0
        for entry in self.get_teacher_schedule(teacher_id):
            if entry.time_slot.weekday == weekday:
                count += 1
        return count

    def swap_entries(self, entry_id1: str, entry_id2: str) -> bool:
        """交换两个排课记录的时间段"""
        entry1 = None
        entry2 = None
        for e in self.entries:
            if e.id == entry_id1:
                entry1 = e
            elif e.id == entry_id2:
                entry2 = e

        if not entry1 or not entry2:
            return False

        # 交换时间段
        entry1.time_slot, entry2.time_slot = entry2.time_slot, entry1.time_slot
        self._rebuild_indexes()
        return True

    def to_dict(self):
        return {
            "entries": [e.to_dict() for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Schedule':
        schedule = cls()
        for entry_data in data.get("entries", []):
            schedule.add_entry(ScheduleEntry.from_dict(entry_data))
        return schedule

    def to_json(self) -> str:
        """导出为JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'Schedule':
        """从JSON导入"""
        return cls.from_dict(json.loads(json_str))

    def to_table(self, class_id: str, classes: Dict[str, ClassGroup],
                 courses: Dict[str, Course], teachers: Dict[str, Teacher],
                 classrooms: Dict[str, 'Classroom'] = None) -> str:
        """
        生成班级课表的文本表格（按单节显示）

        格式：
        | 节次 | 周一 | 周二 | 周三 | 周四 | 周五 |
        |-----|------|------|------|------|------|
        | 第1节 | 数学(张老师)@101教室 | ... | ... | ... | ... |
        | 第2节 | ... | ... | ... | ... | ... |
        """
        weekdays = [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY,
                    Weekday.THURSDAY, Weekday.FRIDAY]
        # 按单节显示：第1节到第8节
        periods = list(range(1, 9))

        # 构建时间表
        table = {}
        for entry in self.get_class_schedule(class_id):
            slot = entry.time_slot
            key = (slot.weekday, slot.period)  # 直接使用节次
            course = courses.get(entry.course_id)
            teacher = teachers.get(entry.teacher_id)
            classroom = classrooms.get(entry.classroom_id) if classrooms else None
            if course and teacher:
                # 格式：课程(教师)@教室
                cell = f"{course.name}({teacher.name})"
                if classroom:
                    cell += f"@{classroom.name}"
                table[key] = cell

        # 生成表格
        lines = []
        header = "| 节次 | " + " | ".join([w.value for w in weekdays]) + " |"
        separator = "|------|" + "|".join(["------" for _ in weekdays]) + "|"
        lines.append(header)
        lines.append(separator)

        for period in periods:
            row = f"| 第{period}节 |"
            for weekday in weekdays:
                cell = table.get((weekday, period), "  ")
                row += f" {cell} |"
            lines.append(row)

        return "\n".join(lines)

    def filter_by_subject(self, class_id: str, subject: str,
                          classes: Dict[str, ClassGroup],
                          courses: Dict[str, Course],
                          teachers: Dict[str, Teacher],
                          classrooms: Dict[str, 'Classroom'] = None) -> str:
        """
        按科目筛选课表，只返回指定科目的课程安排

        参数:
            class_id: 班级ID
            subject: 科目名称（如"英语"）
            classes: 班级字典
            courses: 课程字典
            teachers: 教师字典
            classrooms: 教室字典

        返回:
            筛选后的课表文本
        """
        weekdays = [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY,
                    Weekday.THURSDAY, Weekday.FRIDAY]
        day_names = ["周一", "周二", "周三", "周四", "周五"]

        # 收集该科目的所有课程
        results = []
        for entry in self.get_class_schedule(class_id):
            course = courses.get(entry.course_id)
            if course and subject in course.subject:
                teacher = teachers.get(entry.teacher_id)
                classroom = classrooms.get(entry.classroom_id) if classrooms else None

                weekday = entry.time_slot.weekday
                period = entry.time_slot.period

                day_idx = weekdays.index(weekday) if weekday in weekdays else -1
                day_name = day_names[day_idx] if day_idx >= 0 else str(weekday.value)

                info = f"  📅 {day_name} 第{period}节"
                if teacher:
                    info += f" - {teacher.name}"
                if classroom:
                    info += f" ({classroom.name})"

                results.append((day_idx, period, info))

        if not results:
            return ""

        # 按星期和节次排序
        results.sort(key=lambda x: (x[0], x[1]))

        lines = []
        for _, _, info in results:
            lines.append(info)

        return "\n".join(lines)

    def filter_by_day(self, class_id: str, day: str,
                      classes: Dict[str, ClassGroup],
                      courses: Dict[str, Course],
                      teachers: Dict[str, Teacher],
                      classrooms: Dict[str, 'Classroom'] = None) -> str:
        """
        按日期筛选课表，只返回指定日期的课程安排

        参数:
            class_id: 班级ID
            day: 日期（如"周一"、"周二"）
            classes: 班级字典
            courses: 课程字典
            teachers: 教师字典
            classrooms: 教室字典

        返回:
            筛选后的课表文本
        """
        weekdays = [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY,
                    Weekday.THURSDAY, Weekday.FRIDAY]
        day_names = ["周一", "周二", "周三", "周四", "周五"]

        # 找到对应的weekday
        weekday = None
        for i, name in enumerate(day_names):
            if day in name or name in day:
                weekday = weekdays[i]
                break

        if not weekday:
            return ""

        # 收集该日期的所有课程
        results = []
        for entry in self.get_class_schedule(class_id):
            if entry.time_slot.weekday == weekday:
                course = courses.get(entry.course_id)
                teacher = teachers.get(entry.teacher_id)
                classroom = classrooms.get(entry.classroom_id) if classrooms else None

                period = entry.time_slot.period

                info = f"  📅 第{period}节"
                if course:
                    info += f" - {course.name}"
                if teacher:
                    info += f" ({teacher.name})"
                if classroom:
                    info += f" @ {classroom.name}"

                results.append((period, info))

        if not results:
            return ""

        # 按节次排序
        results.sort(key=lambda x: x[0])

        lines = []
        for _, info in results:
            lines.append(info)

        return "\n".join(lines)

    def filter_by_teacher(self, text: str,
                          classes: Dict[str, ClassGroup],
                          courses: Dict[str, Course],
                          teachers: Dict[str, Teacher],
                          classrooms: Dict[str, 'Classroom'] = None) -> str:
        """
        按教师筛选课表，返回指定教师的所有课程安排

        参数:
            text: 查询文本（包含教师名和日期）
            classes: 班级字典
            courses: 课程字典
            teachers: 教师字典
            classrooms: 教室字典

        返回:
            筛选后的课表文本
        """
        import re

        weekdays = [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY,
                    Weekday.THURSDAY, Weekday.FRIDAY]
        day_names = ["周一", "周二", "周三", "周四", "周五"]

        # 提取教师名
        teacher_matches = re.findall(r'([一-龥]{1,4})(教授|老师|教师)', text)
        teacher_name = ""
        for name, title in teacher_matches:
            clean_name = name.lstrip("班")
            if clean_name and len(clean_name) >= 1:
                teacher_name = clean_name
                break

        if not teacher_name:
            return ""

        # 提取日期
        query_day = None
        for i, name in enumerate(day_names):
            if name in text:
                query_day = weekdays[i]
                break

        # 查找匹配的教师ID
        matched_teacher_id = None
        for teacher_id, teacher in teachers.items():
            if teacher_name in teacher.name:
                matched_teacher_id = teacher_id
                break

        if not matched_teacher_id:
            return ""

        # 收集该教师的所有课程
        results = []
        for class_id, class_group in classes.items():
            for entry in self.get_class_schedule(class_id):
                if entry.teacher_id == matched_teacher_id:
                    # 如果指定了日期，只返回该日期的课程
                    if query_day and entry.time_slot.weekday != query_day:
                        continue

                    course = courses.get(entry.course_id)
                    classroom = classrooms.get(entry.classroom_id) if classrooms else None

                    weekday = entry.time_slot.weekday
                    period = entry.time_slot.period

                    day_idx = weekdays.index(weekday) if weekday in weekdays else -1
                    day_name = day_names[day_idx] if day_idx >= 0 else str(weekday.value)

                    info = f"  📅 {class_group.name} {day_name} 第{period}节"
                    if course:
                        info += f" - {course.name}"
                    if classroom:
                        info += f" @ {classroom.name}"

                    results.append((day_idx, period, info))

        if not results:
            return ""

        # 按星期和节次排序
        results.sort(key=lambda x: (x[0], x[1]))

        lines = []
        for _, _, info in results:
            lines.append(info)

        return "\n".join(lines)

    def filter_by_classroom(self, classroom_name: str,
                           classes: Dict[str, ClassGroup],
                           courses: Dict[str, Course],
                           teachers: Dict[str, Teacher],
                           classrooms: Dict[str, 'Classroom'] = None) -> str:
        """
        按教室筛选课表，返回指定教室的所有课程安排

        参数:
            classroom_name: 教室名称（如"102教室"、"实验室1"）
            classes: 班级字典
            courses: 课程字典
            teachers: 教师字典
            classrooms: 教室字典

        返回:
            筛选后的课表文本
        """
        weekdays = [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY,
                    Weekday.THURSDAY, Weekday.FRIDAY]
        day_names = ["周一", "周二", "周三", "周四", "周五"]

        if not classrooms:
            return ""

        # 查找匹配的教室ID（支持模糊匹配）
        matched_classroom_ids = []
        for classroom_id, classroom in classrooms.items():
            if classroom_name in classroom.name or classroom.name in classroom_name:
                matched_classroom_ids.append(classroom_id)

        if not matched_classroom_ids:
            return ""

        # 收集该教室的所有课程
        results = []
        for entry in self.entries:
            if entry.classroom_id not in matched_classroom_ids:
                continue

            class_group = classes.get(entry.class_id)
            course = courses.get(entry.course_id)
            teacher = teachers.get(entry.teacher_id)
            classroom = classrooms.get(entry.classroom_id)

            weekday = entry.time_slot.weekday
            period = entry.time_slot.period

            day_idx = weekdays.index(weekday) if weekday in weekdays else -1
            day_name = day_names[day_idx] if day_idx >= 0 else str(weekday.value)

            info = f"  📅 {day_name} 第{period}节"
            if class_group:
                info += f" - {class_group.name}"
            if course:
                info += f" {course.name}"
            if teacher:
                info += f" ({teacher.name})"

            results.append((day_idx, period, info))

        if not results:
            return ""

        # 按星期和节次排序
        results.sort(key=lambda x: (x[0], x[1]))

        lines = []
        for _, _, info in results:
            lines.append(info)

        return "\n".join(lines)

    def to_image(self, class_id: str, classes: Dict[str, ClassGroup],
                 courses: Dict[str, Course], teachers: Dict[str, Teacher],
                 output_path: str, classrooms: Dict[str, 'Classroom'] = None) -> bool:
        """
        生成班级课表图片（融合优化版）

        返回: 是否成功
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            import os
        except ImportError:
            return False

        weekdays = [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY,
                    Weekday.THURSDAY, Weekday.FRIDAY]
        periods = list(range(1, 9))
        period_labels = [f"第{i}节" for i in periods]

        # 获取班级名称
        class_group = classes.get(class_id)
        class_name = class_group.name if class_group else class_id

        # 构建时间表数据
        table = {}
        for entry in self.get_class_schedule(class_id):
            slot = entry.time_slot
            period = slot.period
            course = courses.get(entry.course_id)
            teacher = teachers.get(entry.teacher_id)
            classroom = classrooms.get(entry.classroom_id) if classrooms else None
            if course and teacher:
                key = (slot.weekday, period)
                table[key] = {
                    "course": course.name,
                    "teacher": teacher.name,
                    "is_main": course.is_main_subject,
                    "subject": course.subject,
                    "classroom": classroom.name if classroom else "",
                }

        # ── 统一配置（融合优化版）──
        COL_WIDTH = 150
        ROW_HEIGHT = 85
        HEADER_HEIGHT = 55
        TITLE_HEIGHT = 65
        LEFT_COL_WIDTH = 65

        num_cols = len(weekdays)
        MARGIN = 15
        img_width = MARGIN * 2 + LEFT_COL_WIDTH + num_cols * COL_WIDTH
        img_height = MARGIN + TITLE_HEIGHT + HEADER_HEIGHT + len(periods) * ROW_HEIGHT + MARGIN

        # ── 统一颜色方案（融合优化版）──
        BG_COLOR = (255, 255, 255)
        TITLE_BG = (55, 95, 155)
        TITLE_FG = (255, 255, 255)
        HEADER_BG = (75, 125, 190)
        HEADER_FG = (255, 255, 255)

        # 统一的行背景色（节次列和课程列使用相同的基础色）
        ROW_BG_1 = (245, 248, 252)
        ROW_BG_2 = (250, 252, 255)

        # 节次列使用和表头同色系的浅色
        PERIOD_COL_BG = (235, 242, 252)

        GRID_COLOR = (195, 205, 220)
        CELL_FG = (45, 45, 55)
        TEACHER_FG = (95, 95, 110)
        CLASSROOM_FG = (130, 130, 145)
        EMPTY_BG = (248, 248, 252)
        EMPTY_FG = (175, 175, 185)

        # 学科颜色映射（柔和统一的色系）
        SUBJECT_COLORS = {
            "语文": (252, 245, 245),
            "数学": (245, 248, 252),
            "英语": (245, 252, 248),
            "物理": (248, 245, 252),
            "化学": (252, 250, 242),
            "生物": (242, 252, 248),
            "历史": (252, 248, 245),
            "地理": (245, 252, 248),
            "政治": (248, 248, 252),
            "体育": (252, 245, 245),
            "音乐": (252, 248, 252),
            "美术": (248, 252, 250),
            "信息技术": (245, 250, 255),
            "通用技术": (248, 252, 255),
            "自习": (242, 242, 248),
            "班会": (252, 248, 242),
        }

        # 加载字体
        def load_font(size, bold=False):
            font_paths = [
                "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/simhei.ttf",
                "C:/Windows/Fonts/simsun.ttc",
            ]
            for path in font_paths:
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
            return ImageFont.load_default()

        font_title = load_font(22, bold=True)
        font_header = load_font(15, bold=True)
        font_period = load_font(14, bold=True)
        font_course = load_font(15, bold=True)
        font_teacher = load_font(12)
        font_classroom = load_font(11)

        # 创建画布
        img = Image.new("RGB", (img_width, img_height), BG_COLOR)
        draw = ImageDraw.Draw(img)

        # ── 绘制标题栏 ──
        draw.rectangle(
            [(MARGIN, MARGIN), (img_width - MARGIN, MARGIN + TITLE_HEIGHT)],
            fill=TITLE_BG,
        )
        title_text = f"{class_name} 课程表"
        bbox = draw.textbbox((0, 0), title_text, font=font_title)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            (MARGIN + (img_width - 2 * MARGIN - tw) // 2,
             MARGIN + (TITLE_HEIGHT - th) // 2),
            title_text, fill=TITLE_FG, font=font_title,
        )

        y_offset = MARGIN + TITLE_HEIGHT

        # ── 绘制表头（统一风格）──
        # 表头背景
        draw.rectangle(
            [(MARGIN, y_offset), (img_width - MARGIN, y_offset + HEADER_HEIGHT)],
            fill=HEADER_BG,
        )

        # 节次列表头（和其他列表头统一）
        period_header_text = "节次"
        bbox_ph = draw.textbbox((0, 0), period_header_text, font=font_header)
        pw = bbox_ph[2] - bbox_ph[0]
        ph = bbox_ph[3] - bbox_ph[1]
        draw.text(
            (MARGIN + (LEFT_COL_WIDTH - pw) // 2, y_offset + (HEADER_HEIGHT - ph) // 2),
            period_header_text, fill=HEADER_FG, font=font_header,
        )

        # 星期列表头
        for col_idx, weekday in enumerate(weekdays):
            x = MARGIN + LEFT_COL_WIDTH + col_idx * COL_WIDTH
            text = weekday.value
            bbox = draw.textbbox((0, 0), text, font=font_header)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text(
                (x + (COL_WIDTH - tw) // 2, y_offset + (HEADER_HEIGHT - th) // 2),
                text, fill=HEADER_FG, font=font_header,
            )

        # 表头底线
        draw.line(
            [(MARGIN, y_offset + HEADER_HEIGHT), (img_width - MARGIN, y_offset + HEADER_HEIGHT)],
            fill=GRID_COLOR, width=1,
        )

        y_offset += HEADER_HEIGHT

        # ── 绘制数据行（统一融合）──
        for row_idx, (period_label, period) in enumerate(zip(period_labels, periods)):
            # 统一的行背景色
            row_bg = ROW_BG_1 if row_idx % 2 == 0 else ROW_BG_2
            y_top = y_offset + row_idx * ROW_HEIGHT
            y_bottom = y_top + ROW_HEIGHT

            # 节次列（使用统一的浅色背景）
            draw.rectangle(
                [(MARGIN, y_top), (MARGIN + LEFT_COL_WIDTH, y_bottom)],
                fill=PERIOD_COL_BG,
            )
            # 节次文字（垂直水平居中）
            bbox = draw.textbbox((0, 0), period_label, font=font_period)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text(
                (MARGIN + (LEFT_COL_WIDTH - tw) // 2,
                 y_top + (ROW_HEIGHT - th) // 2),
                period_label, fill=(65, 65, 85), font=font_period,
            )

            # 课程格子
            for col_idx, weekday in enumerate(weekdays):
                x_left = MARGIN + LEFT_COL_WIDTH + col_idx * COL_WIDTH
                x_right = x_left + COL_WIDTH
                key = (weekday, period)
                cell = table.get(key)

                if cell:
                    # 用学科颜色做背景
                    bg = SUBJECT_COLORS.get(cell["subject"], row_bg)
                    draw.rectangle(
                        [(x_left, y_top), (x_right, y_bottom)],
                        fill=bg,
                    )

                    # 计算文字整体高度，实现垂直居中
                    # 课程名 + 教师名 + 教室名
                    course_text = cell["course"]
                    teacher_text = cell["teacher"]
                    classroom_text = cell.get("classroom", "")

                    bbox_c = draw.textbbox((0, 0), course_text, font=font_course)
                    ch = bbox_c[3] - bbox_c[1]
                    bbox_t = draw.textbbox((0, 0), teacher_text, font=font_teacher)
                    tt_h = bbox_t[3] - bbox_t[1]

                    total_text_height = ch + 6 + tt_h
                    if classroom_text:
                        short_classroom = classroom_text.replace("教室", "")
                        bbox_r = draw.textbbox((0, 0), short_classroom, font=font_classroom)
                        rh = bbox_r[3] - bbox_r[1]
                        total_text_height += 5 + rh

                    # 起始Y坐标（垂直居中）
                    start_y = y_top + (ROW_HEIGHT - total_text_height) // 2

                    # 课程名（加粗，主信息）
                    bbox_c = draw.textbbox((0, 0), course_text, font=font_course)
                    cw = bbox_c[2] - bbox_c[0]
                    draw.text(
                        (x_left + (COL_WIDTH - cw) // 2, start_y),
                        course_text, fill=CELL_FG, font=font_course,
                    )

                    # 教师名（小号灰色）
                    bbox_t = draw.textbbox((0, 0), teacher_text, font=font_teacher)
                    tw = bbox_t[2] - bbox_t[0]
                    draw.text(
                        (x_left + (COL_WIDTH - tw) // 2, start_y + ch + 6),
                        teacher_text, fill=TEACHER_FG, font=font_teacher,
                    )

                    # 教室名（更小号灰色，底部）
                    if classroom_text:
                        short_classroom = classroom_text.replace("教室", "")
                        bbox_r = draw.textbbox((0, 0), short_classroom, font=font_classroom)
                        rw = bbox_r[2] - bbox_r[0]
                        draw.text(
                            (x_left + (COL_WIDTH - rw) // 2, start_y + ch + 6 + tt_h + 5),
                            short_classroom, fill=CLASSROOM_FG, font=font_classroom,
                        )
                else:
                    # 空课单元格（保持和其他单元格一致的样式）
                    draw.rectangle(
                        [(x_left, y_top), (x_right, y_bottom)],
                        fill=EMPTY_BG,
                    )

            # 行底线
            draw.line(
                [(MARGIN, y_bottom), (img_width - MARGIN, y_bottom)],
                fill=GRID_COLOR, width=1,
            )

        # ── 绘制竖线（统一风格）──
        # 节次列右侧竖线
        draw.line(
            [(MARGIN + LEFT_COL_WIDTH, MARGIN + TITLE_HEIGHT),
             (MARGIN + LEFT_COL_WIDTH, y_offset + len(periods) * ROW_HEIGHT)],
            fill=GRID_COLOR, width=1,
        )

        # 课程列之间的竖线
        for col_idx in range(num_cols + 1):
            x = MARGIN + LEFT_COL_WIDTH + col_idx * COL_WIDTH
            draw.line(
                [(x, MARGIN + TITLE_HEIGHT), (x, y_offset + len(periods) * ROW_HEIGHT)],
                fill=GRID_COLOR, width=1,
            )

        # ── 外边框（统一细线）──
        draw.rectangle(
            [(MARGIN, MARGIN), (img_width - MARGIN, img_height - MARGIN)],
            outline=GRID_COLOR, width=1,
        )

        # 保存
        img.save(output_path, "PNG", quality=95)
        return True
