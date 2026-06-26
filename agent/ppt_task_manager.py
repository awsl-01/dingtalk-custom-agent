"""
PPT生成任务管理器

将PPT生成放到线程池中执行，避免阻塞主事件循环。
"""
import os
import time
import logging
import asyncio
import concurrent.futures
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PPTTaskStatus(Enum):
    """PPT任务状态"""
    PENDING = "pending"          # 等待执行
    RUNNING = "running"          # 执行中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 已取消


@dataclass
class PPTTask:
    """PPT生成任务"""
    task_id: str
    user_id: str
    user_nick: str
    conversation_id: str
    corp_id: str
    topic: str
    status: PPTTaskStatus = PPTTaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: float = 0
    completed_at: float = 0
    result_path: str = ""
    result_title: str = ""
    error_message: str = ""
    progress: int = 0  # 进度百分比


class PPTTaskManager:
    """PPT生成任务管理器"""

    def __init__(self, max_workers: int = 5):
        """
        初始化任务管理器

        参数:
            max_workers: 最大并发数（同时生成的PPT数量）
                - 2: 适合小型服务器（4核8G）
                - 5: 适合中型服务器（8核16G）推荐
                - 10: 适合大型服务器（16核32G）
        """
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.tasks: Dict[str, PPTTask] = {}
        self.futures: Dict[str, concurrent.futures.Future] = {}

        # 回调函数：任务完成后调用
        self._on_complete_callbacks: Dict[str, Callable] = {}

        # 队列管理：历史生成时间（秒），用于计算预计等待时间
        self._generation_times: list = []
        self._max_history = 20  # 保留最近20次生成时间

        logger.info(f"PPT任务管理器初始化，最大并发数: {max_workers}")

    def submit_task(
        self,
        task_id: str,
        user_id: str,
        user_nick: str,
        conversation_id: str,
        corp_id: str,
        topic: str,
        func: Callable,
        *args,
        **kwargs
    ) -> PPTTask:
        """
        提交PPT生成任务

        参数:
            task_id: 任务ID
            user_id: 用户ID
            user_nick: 用户昵称
            conversation_id: 会话ID
            corp_id: 企业ID
            topic: PPT主题
            func: 要执行的函数
            *args, **kwargs: 函数参数

        返回:
            PPTTask对象
        """
        # 创建任务
        task = PPTTask(
            task_id=task_id,
            user_id=user_id,
            user_nick=user_nick,
            conversation_id=conversation_id,
            corp_id=corp_id,
            topic=topic,
        )
        self.tasks[task_id] = task

        # 包装函数，添加完成回调
        def wrapped_func():
            task.status = PPTTaskStatus.RUNNING
            task.started_at = time.time()
            logger.info(f"PPT任务开始执行: {task_id} - {topic}")

            try:
                # 将 topic 作为第一个位置参数传递给 func
                result = func(topic, *args, **kwargs)

                # 解析结果
                if isinstance(result, tuple) and len(result) == 2:
                    task.result_path, task.result_title = result
                else:
                    task.result_path = str(result)
                    task.result_title = topic

                task.status = PPTTaskStatus.COMPLETED
                task.completed_at = time.time()
                task.progress = 100

                elapsed = task.completed_at - task.started_at
                logger.info(f"PPT任务完成: {task_id} - {topic}, 耗时: {elapsed:.1f}秒")

                # 记录生成时间，用于计算平均等待时间
                self._record_generation_time(elapsed)

            except Exception as e:
                task.status = PPTTaskStatus.FAILED
                task.error_message = str(e)
                task.completed_at = time.time()
                logger.error(f"PPT任务失败: {task_id} - {topic}, 错误: {e}")

            # 调用完成回调
            if task_id in self._on_complete_callbacks:
                try:
                    self._on_complete_callbacks[task_id](task)
                except Exception as e:
                    logger.error(f"完成回调执行失败: {e}")

            return task

        # 提交到线程池
        future = self.executor.submit(wrapped_func)
        self.futures[task_id] = future

        logger.info(f"PPT任务已提交: {task_id} - {topic}")

        # 返回排队信息
        return self.get_queue_info(task_id)

    def get_task(self, task_id: str) -> Optional[PPTTask]:
        """获取任务信息"""
        return self.tasks.get(task_id)

    def get_user_tasks(self, user_id: str) -> list:
        """获取用户的任务列表"""
        return [t for t in self.tasks.values() if t.user_id == user_id]

    def get_pending_tasks(self) -> list:
        """获取等待执行的任务"""
        return [t for t in self.tasks.values() if t.status == PPTTaskStatus.PENDING]

    def get_running_tasks(self) -> list:
        """获取正在执行的任务"""
        return [t for t in self.tasks.values() if t.status == PPTTaskStatus.RUNNING]

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id not in self.futures:
            return False

        future = self.futures[task_id]
        if future.done():
            return False

        # 尝试取消
        success = future.cancel()
        if success:
            task = self.tasks[task_id]
            task.status = PPTTaskStatus.CANCELLED
            task.completed_at = time.time()
            logger.info(f"PPT任务已取消: {task_id}")

        return success

    def on_complete(self, task_id: str, callback: Callable):
        """注册任务完成回调"""
        self._on_complete_callbacks[task_id] = callback

    def cleanup_completed(self, max_age_seconds: int = 3600):
        """清理已完成的任务（默认1小时）"""
        now = time.time()
        to_remove = []

        for task_id, task in self.tasks.items():
            if task.status in [PPTTaskStatus.COMPLETED, PPTTaskStatus.FAILED, PPTTaskStatus.CANCELLED]:
                if now - task.completed_at > max_age_seconds:
                    to_remove.append(task_id)

        for task_id in to_remove:
            del self.tasks[task_id]
            if task_id in self.futures:
                del self.futures[task_id]
            if task_id in self._on_complete_callbacks:
                del self._on_complete_callbacks[task_id]

        if to_remove:
            logger.info(f"清理了 {len(to_remove)} 个已完成的任务")

    def get_stats(self) -> dict:
        """获取任务统计"""
        stats = {
            "total": len(self.tasks),
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
        }
        for task in self.tasks.values():
            stats[task.status.value] = stats.get(task.status.value, 0) + 1
        return stats

    # ─────────────────── 队列管理功能 ───────────────────

    def get_queue_position(self, task_id: str) -> int:
        """
        获取任务在队列中的位置

        返回:
            排队位置（从1开始），0表示不在队列中
        """
        if task_id not in self.tasks:
            return 0

        task = self.tasks[task_id]
        if task.status != PPTTaskStatus.PENDING:
            return 0  # 已在执行或已完成，不在排队中

        # 统计排在前面的等待任务数
        position = 1
        for t in self.tasks.values():
            if t.status == PPTTaskStatus.PENDING and t.created_at < task.created_at:
                position += 1

        return position

    def get_estimated_wait_time(self, task_id: str) -> int:
        """
        获取预计等待时间（秒）

        计算逻辑：
        1. 排队位置 × 平均生成时间
        2. 如果没有历史数据，使用默认值120秒
        """
        if task_id not in self.tasks:
            return 0

        task = self.tasks[task_id]
        if task.status != PPTTaskStatus.PENDING:
            return 0

        # 获取平均生成时间
        avg_time = self._get_average_generation_time()

        # 当前正在执行的任务数
        running_count = len(self.get_running_tasks())

        # 排队位置
        queue_position = self.get_queue_position(task_id)

        # 预计等待 = (排队位置 / 并发数) × 平均生成时间
        # 如果有空闲线程，等待时间会更短
        concurrent_slots = min(queue_position, self.executor._max_workers - running_count)
        wait_time = int((queue_position / self.executor._max_workers) * avg_time)

        return max(wait_time, 30)  # 最少30秒

    def _get_average_generation_time(self) -> float:
        """获取平均生成时间（秒）"""
        if not self._generation_times:
            return 120.0  # 默认2分钟

        # 返回最近几次的平均值
        recent = self._generation_times[-10:]  # 最近10次
        return sum(recent) / len(recent)

    def _record_generation_time(self, duration: float):
        """记录生成时间"""
        self._generation_times.append(duration)
        if len(self._generation_times) > self._max_history:
            self._generation_times.pop(0)  # 移除最旧的记录

    def get_queue_info(self, task_id: str) -> dict:
        """
        获取完整的队列信息

        返回:
            {
                "task_id": "ppt_xxx",
                "status": "pending",
                "queue_position": 2,
                "total_in_queue": 5,
                "estimated_wait_seconds": 180,
                "estimated_wait_display": "约3分钟",
                "running_count": 3,
                "available_slots": 2
            }
        """
        if task_id not in self.tasks:
            return {"error": "任务不存在"}

        task = self.tasks[task_id]
        queue_position = self.get_queue_position(task_id)
        estimated_wait = self.get_estimated_wait_time(task_id)
        running_count = len(self.get_running_tasks())
        pending_count = len(self.get_pending_tasks())

        # 计算可用线程槽位
        available_slots = max(0, self.executor._max_workers - running_count)

        # 格式化等待时间显示
        if estimated_wait < 60:
            wait_display = f"约{estimated_wait}秒"
        elif estimated_wait < 3600:
            minutes = estimated_wait // 60
            wait_display = f"约{minutes}分钟"
        else:
            hours = estimated_wait // 3600
            minutes = (estimated_wait % 3600) // 60
            wait_display = f"约{hours}小时{minutes}分钟"

        return {
            "task_id": task_id,
            "status": task.status.value,
            "queue_position": queue_position,
            "total_in_queue": pending_count,
            "estimated_wait_seconds": estimated_wait,
            "estimated_wait_display": wait_display,
            "running_count": running_count,
            "available_slots": available_slots,
        }

    def get_all_queue_status(self) -> dict:
        """
        获取所有任务的队列状态

        返回:
            {
                "concurrency": {
                    "max": 5,
                    "running": 3,
                    "available": 2
                },
                "queue": [
                    {"task_id": "xxx", "position": 1, "topic": "...", "estimated_wait": "约2分钟"},
                    ...
                ],
                "stats": {...}
            }
        """
        running_count = len(self.get_running_tasks())
        pending_tasks = self.get_pending_tasks()
        pending_tasks.sort(key=lambda t: t.created_at)  # 按创建时间排序

        queue_list = []
        for i, task in enumerate(pending_tasks, 1):
            estimated_wait = self.get_estimated_wait_time(task.task_id)
            if estimated_wait < 60:
                wait_display = f"约{estimated_wait}秒"
            elif estimated_wait < 3600:
                minutes = estimated_wait // 60
                wait_display = f"约{minutes}分钟"
            else:
                hours = estimated_wait // 3600
                wait_display = f"约{hours}小时"

            queue_list.append({
                "task_id": task.task_id,
                "position": i,
                "user_nick": task.user_nick,
                "topic": task.topic,
                "created_at": task.created_at,
                "estimated_wait_seconds": estimated_wait,
                "estimated_wait_display": wait_display,
            })

        return {
            "concurrency": {
                "max": self.executor._max_workers,
                "running": running_count,
                "available": max(0, self.executor._max_workers - running_count),
            },
            "queue": queue_list,
            "stats": self.get_stats(),
            "avg_generation_time": int(self._get_average_generation_time()),
        }


# 全局任务管理器实例
_ppt_task_manager: Optional[PPTTaskManager] = None


def get_ppt_task_manager(max_workers: int = 5) -> PPTTaskManager:
    """获取全局PPT任务管理器"""
    global _ppt_task_manager
    if _ppt_task_manager is None:
        _ppt_task_manager = PPTTaskManager(max_workers=max_workers)
    return _ppt_task_manager
