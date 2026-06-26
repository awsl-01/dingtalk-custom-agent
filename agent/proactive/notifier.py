"""
变更通知器

当考试安排、课表发生冲突或更新时，自动通知相关用户
支持钉钉、微信、邮件等多种通知渠道
"""
import logging
import json
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class Subscriber:
    """订阅者"""
    user_id: str
    user_nick: str = ""
    categories: list = field(default_factory=list)  # 关注的类别
    channels: list = field(default_factory=list)     # 通知渠道
    conversation_id: str = ""  # 会话ID（用于钉钉）


@dataclass
class ChangeNotification:
    """变更通知"""
    notification_id: str
    change_type: str  # update/conflict/expiry
    category: str     # schedule/exam/homework/...
    title: str
    message: str
    details: dict = field(default_factory=dict)
    timestamp: str = ""
    recipients: list = field(default_factory=list)
    sent: bool = False


class ChangeNotifier:
    """
    变更通知器

    功能：
    1. 管理订阅者
    2. 检测变更事件
    3. 发送通知到各渠道
    """

    def __init__(self, storage_dir: str = None):
        self._subscribers: Dict[str, Subscriber] = {}
        self._notification_history: List[ChangeNotification] = []
        self._storage_dir = storage_dir

        # 通知回调函数
        self._notification_callbacks = {
            "dingtalk": None,
            "wechat": None,
            "email": None,
        }

        # 加载订阅者配置
        if storage_dir:
            self._load_subscribers()

    def _load_subscribers(self):
        """加载订阅者配置"""
        import os
        config_file = os.path.join(self._storage_dir, "subscribers.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for sub_data in data:
                    sub = Subscriber(**sub_data)
                    self._subscribers[sub.user_id] = sub
                logger.info(f"加载了 {len(self._subscribers)} 个订阅者")
            except Exception as e:
                logger.error(f"加载订阅者配置失败: {e}")

    def _save_subscribers(self):
        """保存订阅者配置"""
        if not self._storage_dir:
            return

        import os
        os.makedirs(self._storage_dir, exist_ok=True)
        config_file = os.path.join(self._storage_dir, "subscribers.json")

        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(
                    [asdict(sub) for sub in self._subscribers.values()],
                    f, ensure_ascii=False, indent=2
                )
        except Exception as e:
            logger.error(f"保存订阅者配置失败: {e}")

    def register_callback(self, channel: str, callback):
        """
        注册通知回调函数

        参数:
            channel: 通知渠道（dingtalk/wechat/email）
            callback: 回调函数，签名：async def callback(user_id, title, message, details)
        """
        self._notification_callbacks[channel] = callback

    def subscribe(self, user_id: str, categories: list,
                  channels: list = None, user_nick: str = "",
                  conversation_id: str = ""):
        """
        订阅变更通知

        参数:
            user_id: 用户ID
            categories: 关注的类别（schedule/exam/homework/...）
            channels: 通知渠道（dingtalk/wechat/email）
            user_nick: 用户昵称
            conversation_id: 会话ID
        """
        if channels is None:
            channels = ["dingtalk"]

        self._subscribers[user_id] = Subscriber(
            user_id=user_id,
            user_nick=user_nick,
            categories=categories,
            channels=channels,
            conversation_id=conversation_id,
        )

        self._save_subscribers()
        logger.info(f"用户 {user_id} 订阅了 {categories} 的变更通知")

    def unsubscribe(self, user_id: str):
        """取消订阅"""
        if user_id in self._subscribers:
            del self._subscribers[user_id]
            self._save_subscribers()
            logger.info(f"用户 {user_id} 取消了订阅")

    def get_subscribers(self, category: str = None) -> List[Subscriber]:
        """
        获取订阅者

        参数:
            category: 类别过滤

        返回:
            订阅者列表
        """
        if category:
            return [
                sub for sub in self._subscribers.values()
                if category in sub.categories
            ]
        return list(self._subscribers.values())

    async def notify_schedule_update(self, class_name: str,
                                      day: str, period: str,
                                      old_course: str, new_course: str,
                                      updated_by: str = ""):
        """
        通知课表更新

        参数:
            class_name: 班级名称
            day: 星期几
            period: 节次
            old_course: 原课程
            new_course: 新课程
            updated_by: 更新者
        """
        notification = ChangeNotification(
            notification_id=f"notif_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            change_type="update",
            category="schedule",
            title=f"课表变更通知 - {class_name}",
            message=f"{class_name} {day}{period} 课程变更：{old_course} → {new_course}",
            details={
                "class": class_name,
                "day": day,
                "period": period,
                "old_course": old_course,
                "new_course": new_course,
                "updated_by": updated_by,
            },
            timestamp=datetime.now().isoformat(),
        )

        await self._send_notification(notification, category="schedule")

    async def notify_schedule_conflict(self, class_name: str,
                                        day: str, period: str,
                                        courses: list):
        """
        通知课表冲突

        参数:
            class_name: 班级名称
            day: 星期几
            period: 节次
            courses: 冲突的课程列表
        """
        notification = ChangeNotification(
            notification_id=f"notif_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            change_type="conflict",
            category="schedule",
            title=f"⚠️ 课表冲突 - {class_name}",
            message=f"{class_name} {day}{period} 存在冲突：{', '.join(courses)}",
            details={
                "class": class_name,
                "day": day,
                "period": period,
                "courses": courses,
            },
            timestamp=datetime.now().isoformat(),
        )

        await self._send_notification(notification, category="schedule")

    async def notify_exam_update(self, course: str, exam_type: str,
                                  old_date: str, new_date: str,
                                  old_time: str = "", new_time: str = ""):
        """
        通知考试安排更新

        参数:
            course: 课程名称
            exam_type: 考试类型
            old_date: 原日期
            new_date: 新日期
            old_time: 原时间
            new_time: 新时间
        """
        time_info = ""
        if old_time and new_time:
            time_info = f"，时间：{old_time} → {new_time}"

        notification = ChangeNotification(
            notification_id=f"notif_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            change_type="update",
            category="exam",
            title=f"考试安排变更 - {course}",
            message=f"{course}{exam_type}日期变更：{old_date} → {new_date}{time_info}",
            details={
                "course": course,
                "exam_type": exam_type,
                "old_date": old_date,
                "new_date": new_date,
                "old_time": old_time,
                "new_time": new_time,
            },
            timestamp=datetime.now().isoformat(),
        )

        await self._send_notification(notification, category="exam")

    async def notify_exam_conflict(self, date: str, time: str, courses: list):
        """
        通知考试冲突

        参数:
            date: 日期
            time: 时间
            courses: 冲突的课程列表
        """
        notification = ChangeNotification(
            notification_id=f"notif_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            change_type="conflict",
            category="exam",
            title="⚠️ 考试时间冲突",
            message=f"{date} {time} 存在考试冲突：{', '.join(courses)}",
            details={
                "date": date,
                "time": time,
                "courses": courses,
            },
            timestamp=datetime.now().isoformat(),
        )

        await self._send_notification(notification, category="exam")

    async def notify_expiry_warning(self, category: str, entity: str,
                                     expires_at: str, days_left: int):
        """
        通知即将过期

        参数:
            category: 类别
            entity: 实体名称
            expires_at: 过期时间
            days_left: 剩余天数
        """
        notification = ChangeNotification(
            notification_id=f"notif_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            change_type="expiry",
            category=category,
            title=f"即将过期提醒 - {entity}",
            message=f"{entity} 将在 {days_left} 天后过期（{expires_at}）",
            details={
                "entity": entity,
                "expires_at": expires_at,
                "days_left": days_left,
            },
            timestamp=datetime.now().isoformat(),
        )

        await self._send_notification(notification, category=category)

    async def _send_notification(self, notification: ChangeNotification,
                                  category: str):
        """
        发送通知

        参数:
            notification: 通知对象
            category: 类别
        """
        # 获取订阅者
        subscribers = self.get_subscribers(category)

        if not subscribers:
            logger.debug(f"没有订阅 {category} 变更的用户")
            return

        # 记录通知历史
        notification.recipients = [sub.user_id for sub in subscribers]
        self._notification_history.append(notification)

        # 发送通知
        for sub in subscribers:
            for channel in sub.channels:
                callback = self._notification_callbacks.get(channel)
                if callback:
                    try:
                        await callback(
                            user_id=sub.user_id,
                            title=notification.title,
                            message=notification.message,
                            details=notification.details,
                            conversation_id=sub.conversation_id,
                        )
                        logger.info(f"发送通知到 {sub.user_id} ({channel})")
                    except Exception as e:
                        logger.error(f"发送通知失败: {e}")

        notification.sent = True

    async def send_daily_summary(self):
        """发送每日摘要"""
        today = datetime.now().date()
        today_notifications = [
            n for n in self._notification_history
            if n.timestamp.startswith(str(today))
        ]

        if not today_notifications:
            return

        summary_lines = [
            f"📚 知识库每日变更摘要 ({today})",
            "",
            f"今日共 {len(today_notifications)} 条变更：",
        ]

        # 按类别统计
        by_category = {}
        for n in today_notifications:
            cat = n.category
            by_category[cat] = by_category.get(cat, 0) + 1

        category_names = {
            "schedule": "课表",
            "exam": "考试",
            "homework": "作业",
            "notice": "通知",
        }

        for cat, count in by_category.items():
            cat_name = category_names.get(cat, cat)
            summary_lines.append(f"  - {cat_name}: {count} 条")

        # 发送摘要给所有订阅者
        summary_message = "\n".join(summary_lines)
        for sub in self._subscribers.values():
            for channel in sub.channels:
                callback = self._notification_callbacks.get(channel)
                if callback:
                    try:
                        await callback(
                            user_id=sub.user_id,
                            title="知识库每日变更摘要",
                            message=summary_message,
                            details={"date": str(today)},
                            conversation_id=sub.conversation_id,
                        )
                    except Exception as e:
                        logger.error(f"发送每日摘要失败: {e}")

    def get_notification_history(self, limit: int = 100,
                                  category: str = None) -> List[dict]:
        """
        获取通知历史

        参数:
            limit: 返回数量限制
            category: 类别过滤

        返回:
            通知历史列表
        """
        notifications = self._notification_history

        if category:
            notifications = [n for n in notifications if n.category == category]

        # 按时间倒序
        notifications.sort(key=lambda x: x.timestamp, reverse=True)

        return [asdict(n) for n in notifications[:limit]]

    def get_stats(self) -> dict:
        """获取通知统计"""
        total = len(self._notification_history)
        by_type = {}
        by_category = {}

        for n in self._notification_history:
            by_type[n.change_type] = by_type.get(n.change_type, 0) + 1
            by_category[n.category] = by_category.get(n.category, 0) + 1

        return {
            "total_subscribers": len(self._subscribers),
            "total_notifications": total,
            "by_type": by_type,
            "by_category": by_category,
        }


# 全局通知器实例
_notifier: Optional[ChangeNotifier] = None


def get_notifier(storage_dir: str = None) -> ChangeNotifier:
    """获取全局通知器实例"""
    global _notifier
    if _notifier is None:
        _notifier = ChangeNotifier(storage_dir)
    return _notifier
