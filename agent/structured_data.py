"""
结构化数据处理模块
负责课表、考试安排、通讯录等半结构化数据的解析和查询
"""
import json
import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict

from openai import OpenAI

import config

logger = logging.getLogger(__name__)


@dataclass
class ScheduleEntry:
    """课表条目"""
    weekday: str        # 星期几
    period: str         # 第几节（如 "1-2节" 或 "上午第1节"）
    course: str         # 课程名
    teacher: str = ""   # 教师
    classroom: str = "" # 教室
    weeks: str = ""     # 周次（如 "1-16周"）


@dataclass
class ExamEntry:
    """考试安排条目"""
    course: str         # 课程名
    exam_type: str      # 考试类型（期中/期末/随堂）
    date: str           # 日期
    time: str           # 时间
    classroom: str = "" # 教室
    seat: str = ""      # 座位号
    note: str = ""      # 备注


@dataclass
class ContactEntry:
    """通讯录条目"""
    name: str           # 姓名
    title: str = ""     # 职务
    department: str = "" # 部门
    phone: str = ""     # 电话
    email: str = ""     # 邮箱
    note: str = ""      # 备注


WEEKDAY_MAP = {
    "周一": 1, "星期一": 1, "Monday": 1, "Mon": 1,
    "周二": 2, "星期二": 2, "Tuesday": 2, "Tue": 2,
    "周三": 3, "星期三": 3, "Wednesday": 3, "Wed": 3,
    "周四": 4, "星期四": 4, "Thursday": 4, "Thu": 4,
    "周五": 5, "星期五": 5, "Friday": 5, "Fri": 5,
    "周六": 6, "星期六": 6, "Saturday": 6, "Sat": 6,
    "周日": 7, "星期日": 7, "周天": 7, "Sunday": 7, "Sun": 7,
}


class ScheduleParser:
    """课表解析器"""

    @staticmethod
    async def parse_from_text(text: str) -> List[ScheduleEntry]:
        """
        使用LLM从文本中提取课表结构

        参数:
            text: 课表的文本内容（可能是OCR提取的）

        返回:
            课表条目列表
        """
        try:
            client = OpenAI(
                api_key=config.OPENAI_API_KEY,
                base_url=config.OPENAI_BASE_URL,
            )

            system_prompt = """你是一个课表解析助手。请从用户提供的文本中提取课表信息。

输出要求：
1. 返回JSON数组格式
2. 每个条目包含以下字段：
   - weekday: 星期几（周一/周二/.../周日）
   - period: 节次（如"第1-2节"、"上午第3节"）
   - course: 课程名称
   - teacher: 教师姓名（如果有）
   - classroom: 教室（如果有）
   - weeks: 周次范围（如果有，如"1-16周"）
3. 如果信息不完整，留空对应字段
4. 只输出JSON数组，不要添加任何解释

示例输出：
[
  {"weekday": "周一", "period": "第1-2节", "course": "高等数学", "teacher": "张老师", "classroom": "教二楼301", "weeks": "1-16周"},
  {"weekday": "周三", "period": "第3-4节", "course": "大学英语", "teacher": "李老师", "classroom": "外语楼201", "weeks": "1-16周"}
]"""

            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请从以下文本中提取课表信息：\n\n{text}"},
                ],
            )

            content = response.choices[0].message.content

            # 提取JSON部分
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                entries_data = json.loads(json_match.group())
                return [ScheduleEntry(**entry) for entry in entries_data]

            logger.warning("LLM未能返回有效的课表JSON")
            return []

        except Exception as e:
            logger.error(f"解析课表失败: {e}")
            return []

    @staticmethod
    def query_schedule(entries: List[ScheduleEntry], query: str) -> str:
        """
        根据查询返回课表信息

        参数:
            entries: 课表条目列表
            query: 用户查询（如"周三下午"、"周一第几节"）

        返回:
            格式化的回答
        """
        if not entries:
            return "暂无课表信息，请先上传课表。"

        query_lower = query.lower()

        # 提取查询中的星期
        target_weekday = None
        for wd, wd_num in WEEKDAY_MAP.items():
            if wd in query:
                target_weekday = wd
                break

        # 提取查询中的节次
        period_match = re.search(r'第?\s*(\d+)\s*[-到至]?\s*(\d+)?\s*节?', query)
        target_period = None
        if period_match:
            target_period = period_match.group(1)

        # 提取上午/下午
        is_morning = "上午" in query
        is_afternoon = "下午" in query

        # 过滤匹配的条目
        matched = []
        for entry in entries:
            if target_weekday and entry.weekday != target_weekday:
                continue
            if target_period and target_period not in entry.period:
                continue
            if is_morning:
                period_num = _extract_period_number(entry.period)
                if period_num and period_num > 4:
                    continue
            if is_afternoon:
                period_num = _extract_period_number(entry.period)
                if period_num and period_num <= 4:
                    continue
            matched.append(entry)

        if not matched:
            if target_weekday:
                return f"{target_weekday}没有找到课程安排。"
            return "没有找到匹配的课程安排。"

        # 格式化输出
        lines = []
        for entry in matched:
            line = f"{entry.weekday} {entry.period}，{entry.course}"
            if entry.classroom:
                line += f"，{entry.classroom}"
            if entry.teacher:
                line += f"（{entry.teacher}）"
            if entry.weeks:
                line += f" [{entry.weeks}]"
            lines.append(line)

        return "\n".join(lines)


class ExamParser:
    """考试安排解析器"""

    @staticmethod
    async def parse_from_text(text: str) -> List[ExamEntry]:
        """使用LLM从文本中提取考试安排"""
        try:
            client = OpenAI(
                api_key=config.OPENAI_API_KEY,
                base_url=config.OPENAI_BASE_URL,
            )

            system_prompt = """你是一个考试安排解析助手。请从用户提供的文本中提取考试信息。

输出要求：
1. 返回JSON数组格式
2. 每个条目包含：course(课程名), exam_type(考试类型), date(日期), time(时间), classroom(教室), seat(座位号), note(备注)
3. 只输出JSON数组，不要添加任何解释"""

            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请从以下文本中提取考试安排：\n\n{text}"},
                ],
            )

            content = response.choices[0].message.content
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                entries_data = json.loads(json_match.group())
                return [ExamEntry(**entry) for entry in entries_data]
            return []

        except Exception as e:
            logger.error(f"解析考试安排失败: {e}")
            return []

    @staticmethod
    def query_exams(entries: List[ExamEntry], query: str) -> str:
        """查询考试安排"""
        if not entries:
            return "暂无考试安排信息，请先上传考试安排表。"

        query_lower = query.lower()

        # 按课程名或日期过滤
        matched = []
        for entry in entries:
            if entry.course and entry.course.lower() in query_lower:
                matched.append(entry)
            elif entry.date and entry.date in query:
                matched.append(entry)
            elif "期末" in query and "期末" in entry.exam_type:
                matched.append(entry)
            elif "期中" in query and "期中" in entry.exam_type:
                matched.append(entry)

        if not matched:
            matched = entries  # 没有精确匹配则返回全部

        lines = []
        for entry in matched:
            line = f"【{entry.course}】{entry.exam_type}"
            if entry.date:
                line += f" | {entry.date}"
            if entry.time:
                line += f" {entry.time}"
            if entry.classroom:
                line += f" | {entry.classroom}"
            if entry.seat:
                line += f" | 座位：{entry.seat}"
            if entry.note:
                line += f" | {entry.note}"
            lines.append(line)

        return "\n".join(lines)


class ContactParser:
    """通讯录解析器"""

    @staticmethod
    async def parse_from_text(text: str) -> List[ContactEntry]:
        """使用LLM从文本中提取通讯录信息"""
        try:
            client = OpenAI(
                api_key=config.OPENAI_API_KEY,
                base_url=config.OPENAI_BASE_URL,
            )

            system_prompt = """你是一个通讯录解析助手。请从用户提供的文本中提取联系人信息。

输出要求：
1. 返回JSON数组格式
2. 每个条目包含：name(姓名), title(职务), department(部门), phone(电话), email(邮箱), note(备注)
3. 只输出JSON数组，不要添加任何解释"""

            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请从以下文本中提取通讯录信息：\n\n{text}"},
                ],
            )

            content = response.choices[0].message.content
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                entries_data = json.loads(json_match.group())
                return [ContactEntry(**entry) for entry in entries_data]
            return []

        except Exception as e:
            logger.error(f"解析通讯录失败: {e}")
            return []

    @staticmethod
    def query_contacts(entries: List[ContactEntry], query: str) -> str:
        """查询通讯录"""
        if not entries:
            return "暂无通讯录信息，请先上传通讯录。"

        query_lower = query.lower()

        # 按姓名或部门过滤
        matched = []
        for entry in entries:
            if entry.name and entry.name in query:
                matched.append(entry)
            elif entry.department and entry.department in query:
                matched.append(entry)
            elif entry.title and entry.title in query:
                matched.append(entry)

        if not matched:
            # 尝试模糊匹配
            for entry in entries:
                if any(c in query for c in entry.name):
                    matched.append(entry)

        if not matched:
            return "没有找到匹配的联系人。"

        lines = []
        for entry in matched:
            line = f"【{entry.name}】"
            if entry.title:
                line += f" {entry.title}"
            if entry.department:
                line += f" | {entry.department}"
            if entry.phone:
                line += f" | 电话：{entry.phone}"
            if entry.email:
                line += f" | 邮箱：{entry.email}"
            if entry.note:
                line += f" | {entry.note}"
            lines.append(line)

        return "\n".join(lines)


def _extract_period_number(period_str: str) -> Optional[int]:
    """从节次字符串中提取起始节数"""
    match = re.search(r'(\d+)', period_str)
    if match:
        return int(match.group(1))
    return None


def detect_data_type(text: str) -> str:
    """
    检测文本中包含的结构化数据类型

    返回: "schedule" / "exam" / "contact" / "unknown"
    """
    text_lower = text.lower()

    # 课表特征
    schedule_keywords = ["课表", "课程表", "上课时间", "节次", "星期一", "星期二",
                         "周一", "周二", "第1节", "第2节", "上午", "下午"]
    schedule_score = sum(1 for kw in schedule_keywords if kw in text)

    # 考试特征
    exam_keywords = ["考试", "期末", "期中", "测验", "考场", "座位号", "考试时间"]
    exam_score = sum(1 for kw in exam_keywords if kw in text)

    # 通讯录特征
    contact_keywords = ["通讯录", "联系电话", "手机号", "邮箱", "办公室", "职务"]
    contact_score = sum(1 for kw in contact_keywords if kw in text)

    scores = {
        "schedule": schedule_score,
        "exam": exam_score,
        "contact": contact_score,
    }

    max_type = max(scores, key=scores.get)
    if scores[max_type] >= 2:
        return max_type

    return "unknown"


# ========== 冲突检测模块 ==========
@dataclass
class Conflict:
    """冲突记录"""
    conflict_type: str      # 冲突类型：schedule/exam
    severity: str           # 严重程度：error/warning
    message: str            # 冲突描述
    details: dict           # 冲突详情
    detected_at: str = ""   # 检测时间


class ConflictDetector:
    """
    冲突检测器

    支持：
    - 课表冲突检测：同一班级同一时间段有多门课
    - 考试冲突检测：同一学生同一时间有多场考试
    - 跨班级教室冲突检测：同一教室同一时间有不同班级的课
    """

    @staticmethod
    def detect_schedule_conflicts(schedules: list) -> List[Conflict]:
        """
        检测课表冲突

        检测项：
        1. 同一班级同一时间段有多门课
        2. 同一教师同一时间段有多门课
        3. 同一教室同一时间段有多门课

        参数:
            schedules: 课表列表

        返回:
            冲突列表
        """
        conflicts = []

        for schedule in schedules:
            class_name = schedule.get("class", "未知班级")
            schedule_data = schedule.get("schedule", {})

            if not schedule_data:
                continue

            # 收集所有时间段的课程
            time_slots: Dict[str, List[dict]] = {}

            for day, day_data in schedule_data.items():
                if not isinstance(day_data, (dict, list)):
                    continue

                if isinstance(day_data, dict):
                    for period, course in day_data.items():
                        if course and course.strip():
                            slot_key = f"{day}_{period}"
                            if slot_key not in time_slots:
                                time_slots[slot_key] = []
                            time_slots[slot_key].append({
                                "day": day,
                                "period": period,
                                "course": course,
                                "class": class_name,
                            })
                elif isinstance(day_data, list):
                    for i, course in enumerate(day_data):
                        if course and course.strip():
                            period = f"第{i+1}节"
                            slot_key = f"{day}_{period}"
                            if slot_key not in time_slots:
                                time_slots[slot_key] = []
                            time_slots[slot_key].append({
                                "day": day,
                                "period": period,
                                "course": course,
                                "class": class_name,
                            })

            # 检测冲突
            for slot_key, entries in time_slots.items():
                if len(entries) > 1:
                    # 同一时间段有多门课
                    courses = [e["course"] for e in entries]
                    day = entries[0]["day"]
                    period = entries[0]["period"]

                    conflicts.append(Conflict(
                        conflict_type="schedule",
                        severity="error",
                        message=f"【课表冲突】{class_name} {day}{period} 有多门课程：{', '.join(courses)}",
                        details={
                            "class": class_name,
                            "day": day,
                            "period": period,
                            "courses": courses,
                        },
                        detected_at=datetime.now().isoformat(),
                    ))

        # 检测跨班级教室冲突
        classroom_slots: Dict[str, List[dict]] = {}
        for schedule in schedules:
            class_name = schedule.get("class", "未知班级")
            schedule_data = schedule.get("schedule", {})

            for day, day_data in schedule_data.items():
                if not isinstance(day_data, dict):
                    continue

                for period, course in day_data.items():
                    # 尝试提取教室信息（如果课程名包含教室）
                    # 这里简化处理，实际可能需要更复杂的解析
                    pass

        return conflicts

    @staticmethod
    def detect_exam_conflicts(exams: list) -> List[Conflict]:
        """
        检测考试冲突

        检测项：
        1. 同一学生同一时间有多场考试
        2. 同一教室同一时间有多场考试

        参数:
            exams: 考试安排列表

        返回:
            冲突列表
        """
        conflicts = []

        # 按日期+时间分组
        time_slots: Dict[str, List[dict]] = {}

        for exam in exams:
            date = exam.get("date", "")
            time_str = exam.get("time", "")
            course = exam.get("course", "")
            classroom = exam.get("classroom", "")
            exam_type = exam.get("exam_type", "")

            if not date:
                continue

            # 构建时间段键
            slot_key = f"{date}_{time_str}"

            if slot_key not in time_slots:
                time_slots[slot_key] = []
            time_slots[slot_key].append({
                "date": date,
                "time": time_str,
                "course": course,
                "classroom": classroom,
                "exam_type": exam_type,
            })

        # 检测时间冲突
        for slot_key, entries in time_slots.items():
            if len(entries) > 1:
                courses = [e["course"] for e in entries]
                date = entries[0]["date"]
                time_str = entries[0]["time"]

                conflicts.append(Conflict(
                    conflict_type="exam",
                    severity="error",
                    message=f"【考试冲突】{date} {time_str} 有多场考试：{', '.join(courses)}",
                    details={
                        "date": date,
                        "time": time_str,
                        "courses": courses,
                        "count": len(entries),
                    },
                    detected_at=datetime.now().isoformat(),
                ))

        # 检测教室冲突
        classroom_slots: Dict[str, List[dict]] = {}
        for exam in exams:
            date = exam.get("date", "")
            time_str = exam.get("time", "")
            classroom = exam.get("classroom", "")
            course = exam.get("course", "")

            if not classroom or not date:
                continue

            slot_key = f"{classroom}_{date}_{time_str}"
            if slot_key not in classroom_slots:
                classroom_slots[slot_key] = []
            classroom_slots[slot_key].append({
                "date": date,
                "time": time_str,
                "course": course,
                "classroom": classroom,
            })

        for slot_key, entries in classroom_slots.items():
            if len(entries) > 1:
                courses = [e["course"] for e in entries]
                classroom = entries[0]["classroom"]
                date = entries[0]["date"]
                time_str = entries[0]["time"]

                conflicts.append(Conflict(
                    conflict_type="exam",
                    severity="warning",
                    message=f"【教室冲突】{classroom} 在 {date} {time_str} 有多场考试：{', '.join(courses)}",
                    details={
                        "classroom": classroom,
                        "date": date,
                        "time": time_str,
                        "courses": courses,
                    },
                    detected_at=datetime.now().isoformat(),
                ))

        return conflicts

    @staticmethod
    def check_schedule_exam_overlap(schedules: list, exams: list) -> List[Conflict]:
        """
        检测课表与考试的时间重叠

        参数:
            schedules: 课表列表
            exams: 考试安排列表

        返回:
            冲突列表
        """
        conflicts = []

        # 这个功能需要更复杂的日期解析
        # 简化实现：检查考试时间是否与上课时间重叠

        for exam in exams:
            exam_date = exam.get("date", "")
            exam_time = exam.get("time", "")
            exam_course = exam.get("course", "")

            if not exam_date or not exam_time:
                continue

            # 解析考试日期是星期几
            try:
                from datetime import datetime as dt
                exam_dt = dt.strptime(exam_date, "%Y-%m-%d")
                weekday_num = exam_dt.weekday()
                weekday_map = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
                exam_weekday = weekday_map.get(weekday_num, "")
            except (ValueError, ImportError):
                continue

            # 检查是否有课表在同一时间段
            for schedule in schedules:
                schedule_data = schedule.get("schedule", {})
                class_name = schedule.get("class", "")

                if exam_weekday in schedule_data:
                    day_data = schedule_data[exam_weekday]
                    if isinstance(day_data, dict):
                        for period, course in day_data.items():
                            if course and course.strip():
                                # 简化判断：如果考试时间和上课时间有重叠
                                conflicts.append(Conflict(
                                    conflict_type="overlap",
                                    severity="warning",
                                    message=f"【时间重叠】{class_name} {exam_weekday} 有课（{course}），同时有考试（{exam_course}）",
                                    details={
                                        "class": class_name,
                                        "weekday": exam_weekday,
                                        "course": course,
                                        "exam_course": exam_course,
                                        "exam_date": exam_date,
                                        "exam_time": exam_time,
                                    },
                                    detected_at=datetime.now().isoformat(),
                                ))

        return conflicts

    @staticmethod
    def format_conflicts_report(conflicts: List[Conflict]) -> str:
        """
        格式化冲突报告

        参数:
            conflicts: 冲突列表

        返回:
            格式化的报告文本
        """
        if not conflicts:
            return "✅ 未发现任何冲突"

        error_count = sum(1 for c in conflicts if c.severity == "error")
        warning_count = sum(1 for c in conflicts if c.severity == "warning")

        lines = [
            f"⚠️ 发现 {len(conflicts)} 个冲突（{error_count} 个错误，{warning_count} 个警告）",
            "",
        ]

        # 按类型分组
        schedule_conflicts = [c for c in conflicts if c.conflict_type == "schedule"]
        exam_conflicts = [c for c in conflicts if c.conflict_type == "exam"]
        overlap_conflicts = [c for c in conflicts if c.conflict_type == "overlap"]

        if schedule_conflicts:
            lines.append("📚 课表冲突：")
            for c in schedule_conflicts:
                icon = "❌" if c.severity == "error" else "⚠️"
                lines.append(f"  {icon} {c.message}")
            lines.append("")

        if exam_conflicts:
            lines.append("📝 考试冲突：")
            for c in exam_conflicts:
                icon = "❌" if c.severity == "error" else "⚠️"
                lines.append(f"  {icon} {c.message}")
            lines.append("")

        if overlap_conflicts:
            lines.append("⏰ 时间重叠：")
            for c in overlap_conflicts:
                icon = "❌" if c.severity == "error" else "⚠️"
                lines.append(f"  {icon} {c.message}")
            lines.append("")

        return "\n".join(lines)
