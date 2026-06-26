"""
周期性提醒器

根据知识内容与当前时间主动触发提醒
例如："明天有数学期中考试"、"本周三下午体育课停课"
"""
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class Reminder:
    """提醒"""
    reminder_id: str
    reminder_type: str  # exam_tomorrow/schedule_change/homework_due/notice_deadline
    title: str
    message: str
    details: dict = field(default_factory=dict)
    scheduled_time: str = ""  # 计划提醒时间
    sent: bool = False
    created_at: str = ""


class PeriodicReminder:
    """
    周期性提醒器

    功能：
    1. 检查明天的考试
    2. 检查今日课程变更
    3. 检查即将截止的作业
    4. 检查即将过期的通知
    """

    def __init__(self, kb=None, notifier=None):
        self.kb = kb
        self.notifier = notifier
        self._reminder_history: List[Reminder] = []

    def set_knowledge_base(self, kb):
        """设置知识库实例"""
        self.kb = kb

    def set_notifier(self, notifier):
        """设置通知器实例"""
        self.notifier = notifier

    async def check_reminders(self) -> List[Reminder]:
        """
        检查需要提醒的知识

        返回:
            提醒列表
        """
        if not self.kb:
            logger.warning("知识库未设置，无法检查提醒")
            return []

        reminders = []

        # 1. 检查明天的考试
        tomorrow_exams = await self._get_exams_by_date(
            datetime.now() + timedelta(days=1)
        )
        for exam in tomorrow_exams:
            reminders.append(Reminder(
                reminder_id=f"rem_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(reminders)}",
                reminder_type="exam_tomorrow",
                title=f"明日考试提醒 - {exam.get('course', '')}",
                message=f"明天有 {exam.get('course', '')} {exam.get('exam_type', '')}，时间：{exam.get('time', '')}，地点：{exam.get('classroom', '')}",
                details=exam,
                created_at=datetime.now().isoformat(),
            ))

        # 2. 检查今日课程变更
        today_changes = self._get_today_changes()
        for change in today_changes:
            reminders.append(Reminder(
                reminder_id=f"rem_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(reminders)}",
                reminder_type="schedule_change",
                title="今日课程变更",
                message=f"今日课程变更：{change.get('description', '')}",
                details=change,
                created_at=datetime.now().isoformat(),
            ))

        # 3. 检查即将截止的作业（3天内）
        upcoming_homework = self._get_upcoming_homework(days=3)
        for hw in upcoming_homework:
            days_left = hw.get('days_left', 0)
            if days_left == 0:
                time_str = "今天"
            elif days_left == 1:
                time_str = "明天"
            else:
                time_str = f"{days_left}天后"

            reminders.append(Reminder(
                reminder_id=f"rem_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(reminders)}",
                reminder_type="homework_due",
                title=f"作业即将截止 - {hw.get('title', '')}",
                message=f"作业「{hw.get('title', '')}」将在{time_str}截止",
                details=hw,
                created_at=datetime.now().isoformat(),
            ))

        # 4. 检查即将过期的通知（7天内）
        expiring_notices = self._get_expiring_notices(days=7)
        for notice in expiring_notices:
            days_left = notice.get('days_left', 0)
            reminders.append(Reminder(
                reminder_id=f"rem_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(reminders)}",
                reminder_type="notice_deadline",
                title=f"通知即将过期 - {notice.get('title', '')}",
                message=f"通知「{notice.get('title', '')}」将在{days_left}天后过期",
                details=notice,
                created_at=datetime.now().isoformat(),
            ))

        # 记录提醒历史
        self._reminder_history.extend(reminders)

        return reminders

    async def _get_exams_by_date(self, date: datetime) -> List[dict]:
        """获取指定日期的考试"""
        if not self.kb:
            return []

        exams = self.kb.get_structured_data("exams")
        target_date = date.strftime("%Y-%m-%d")

        matched = []
        for exam in exams:
            exam_date = exam.get("date", "")
            if exam_date == target_date:
                matched.append(exam)

        return matched

    def _get_today_changes(self) -> List[dict]:
        """获取今日变更"""
        if not self.kb:
            return []

        today = datetime.now().date()
        changes = []

        # 从操作日志中查找今日的课表变更
        try:
            logs = self.kb.query_operation_logs(
                start_time=today.isoformat(),
                operation="update_schedule",
                limit=100
            )
            for log in logs:
                changes.append({
                    "description": log.details,
                    "timestamp": log.timestamp,
                })
        except Exception as e:
            logger.error(f"获取今日变更失败: {e}")

        return changes

    def _get_upcoming_homework(self, days: int = 3) -> List[dict]:
        """获取即将截止的作业"""
        if not self.kb:
            return []

        now = datetime.now()
        cutoff = now + timedelta(days=days)

        # 从知识库中查找作业类别的内容
        homework_chunks = [
            chunk for chunk in self.kb._chunks
            if chunk.category == "homework" and not chunk.is_expired
        ]

        upcoming = []
        for chunk in homework_chunks:
            # 尝试从过期时间判断
            if chunk.expires_at > 0:
                expiry_date = datetime.fromtimestamp(chunk.expires_at)
                if now < expiry_date <= cutoff:
                    days_left = (expiry_date.date() - now.date()).days
                    upcoming.append({
                        "title": chunk.summary or chunk.text[:50],
                        "text": chunk.text[:200],
                        "expires_at": expiry_date.isoformat(),
                        "days_left": days_left,
                        "chunk_id": chunk.chunk_id,
                    })

        return upcoming

    def _get_expiring_notices(self, days: int = 7) -> List[dict]:
        """获取即将过期的通知"""
        if not self.kb:
            return []

        now = datetime.now()
        cutoff = now + timedelta(days=days)

        # 从知识库中查找通知类别的内容
        notice_chunks = [
            chunk for chunk in self.kb._chunks
            if chunk.category == "notice" and not chunk.is_expired
        ]

        expiring = []
        for chunk in notice_chunks:
            if chunk.expires_at > 0:
                expiry_date = datetime.fromtimestamp(chunk.expires_at)
                if now < expiry_date <= cutoff:
                    days_left = (expiry_date.date() - now.date()).days
                    expiring.append({
                        "title": chunk.summary or chunk.text[:50],
                        "text": chunk.text[:200],
                        "expires_at": expiry_date.isoformat(),
                        "days_left": days_left,
                        "chunk_id": chunk.chunk_id,
                    })

        return expiring

    async def send_reminders(self, reminders: List[Reminder] = None):
        """
        发送提醒

        参数:
            reminders: 提醒列表（如果为None，则先检查提醒）
        """
        if reminders is None:
            reminders = await self.check_reminders()

        if not reminders:
            logger.info("没有需要发送的提醒")
            return

        if not self.notifier:
            logger.warning("通知器未设置，无法发送提醒")
            return

        # 按类型分组
        by_type = {}
        for r in reminders:
            if r.reminder_type not in by_type:
                by_type[r.reminder_type] = []
            by_type[r.reminder_type].append(r)

        # 生成摘要消息
        summary_lines = [
            f"📅 每日知识提醒 ({datetime.now().strftime('%Y-%m-%d')})",
            "",
        ]

        if "exam_tomorrow" in by_type:
            summary_lines.append("📝 明日考试：")
            for r in by_type["exam_tomorrow"]:
                summary_lines.append(f"  • {r.message}")
            summary_lines.append("")

        if "schedule_change" in by_type:
            summary_lines.append("📚 今日课程变更：")
            for r in by_type["schedule_change"]:
                summary_lines.append(f"  • {r.message}")
            summary_lines.append("")

        if "homework_due" in by_type:
            summary_lines.append("✏️ 即将截止的作业：")
            for r in by_type["homework_due"]:
                summary_lines.append(f"  • {r.message}")
            summary_lines.append("")

        if "notice_deadline" in by_type:
            summary_lines.append("📢 即将过期的通知：")
            for r in by_type["notice_deadline"]:
                summary_lines.append(f"  • {r.message}")
            summary_lines.append("")

        summary_message = "\n".join(summary_lines)

        # 发送给所有订阅者
        for sub in self.notifier.get_subscribers():
            for channel in sub.channels:
                callback = self.notifier._notification_callbacks.get(channel)
                if callback:
                    try:
                        await callback(
                            user_id=sub.user_id,
                            title="每日知识提醒",
                            message=summary_message,
                            details={"reminders": [asdict(r) for r in reminders]},
                            conversation_id=sub.conversation_id,
                        )
                        # 标记为已发送
                        for r in reminders:
                            r.sent = True
                    except Exception as e:
                        logger.error(f"发送提醒失败: {e}")

    def get_reminder_history(self, limit: int = 100,
                              reminder_type: str = None) -> List[dict]:
        """
        获取提醒历史

        参数:
            limit: 返回数量限制
            reminder_type: 提醒类型过滤

        返回:
            提醒历史列表
        """
        reminders = self._reminder_history

        if reminder_type:
            reminders = [r for r in reminders if r.reminder_type == reminder_type]

        # 按时间倒序
        reminders.sort(key=lambda x: x.created_at, reverse=True)

        return [asdict(r) for r in reminders[:limit]]

    def get_stats(self) -> dict:
        """获取提醒统计"""
        total = len(self._reminder_history)
        by_type = {}
        sent_count = 0

        for r in self._reminder_history:
            by_type[r.reminder_type] = by_type.get(r.reminder_type, 0) + 1
            if r.sent:
                sent_count += 1

        return {
            "total_reminders": total,
            "sent": sent_count,
            "pending": total - sent_count,
            "by_type": by_type,
        }


# 全局提醒器实例
_reminder: Optional[PeriodicReminder] = None


def get_reminder(kb=None, notifier=None) -> PeriodicReminder:
    """获取全局提醒器实例"""
    global _reminder
    if _reminder is None:
        _reminder = PeriodicReminder(kb, notifier)
    return _reminder
