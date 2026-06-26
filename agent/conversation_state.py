"""
对话状态管理模块
用于跟踪用户的待确认任务状态
"""

import time
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class TaskType(Enum):
    """任务类型"""
    PPT_GENERATION = "ppt_generation"
    EDUCATION_PPT = "education_ppt"
    SEARCH = "search"
    OTHER = "other"


class TaskStatus(Enum):
    """任务状态"""
    PENDING_OUTLINE = "pending_outline"  # 等待大纲确认
    PENDING_TEMPLATE = "pending_template"  # 等待模板选择
    CONFIRMED = "confirmed"  # 已确认，可以生成
    GENERATING = "generating"  # PPT生成中（防止重复触发）
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消


@dataclass
class TaskState:
    """任务状态"""
    task_id: str
    task_type: TaskType
    status: TaskStatus
    user_id: str
    conversation_id: str
    original_request: str
    outline_markdown: str = ""
    outline_data: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


class ConversationStateManager:
    """对话状态管理器"""

    def __init__(self, expiry_seconds: int = 600):
        """
        初始化状态管理器

        参数:
            expiry_seconds: 任务过期时间（秒），默认10分钟
        """
        self._states: Dict[str, TaskState] = {}
        self._expiry_seconds = expiry_seconds

    def _cleanup_expired(self):
        """清理过期的任务"""
        current_time = time.time()
        expired_keys = [
            key for key, state in self._states.items()
            if current_time - state.updated_at > self._expiry_seconds
        ]
        for key in expired_keys:
            del self._states[key]

    def _get_key(self, user_id: str, conversation_id: str = "",
                 corp_id: str = "") -> str:
        """生成状态键（包含corp_id维度以支持多学校隔离）"""
        parts = []
        if corp_id:
            parts.append(corp_id)
        parts.append(user_id)
        if conversation_id:
            parts.append(conversation_id)
        return ":".join(parts)

    def create_task(
        self,
        user_id: str,
        conversation_id: str,
        task_type: TaskType,
        original_request: str,
        outline_markdown: str = "",
        outline_data: dict = None,
        corp_id: str = "",
        **metadata
    ) -> TaskState:
        """创建新任务"""
        self._cleanup_expired()

        key = self._get_key(user_id, conversation_id, corp_id)
        task_id = f"task_{int(time.time() * 1000)}"

        state = TaskState(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING_OUTLINE,
            user_id=user_id,
            conversation_id=conversation_id,
            original_request=original_request,
            outline_markdown=outline_markdown,
            outline_data=outline_data or {},
            metadata=metadata
        )

        self._states[key] = state
        return state

    def get_task(self, user_id: str, conversation_id: str = "",
                 corp_id: str = "") -> Optional[TaskState]:
        """获取当前任务状态"""
        self._cleanup_expired()

        key = self._get_key(user_id, conversation_id, corp_id)
        return self._states.get(key)

    def update_task(
        self,
        user_id: str,
        conversation_id: str,
        corp_id: str = "",
        **updates
    ) -> Optional[TaskState]:
        """更新任务状态"""
        key = self._get_key(user_id, conversation_id, corp_id)
        state = self._states.get(key)

        if state:
            for field_name, value in updates.items():
                if hasattr(state, field_name):
                    setattr(state, field_name, value)
            state.updated_at = time.time()

        return state

    def complete_task(self, user_id: str, conversation_id: str,
                      corp_id: str = "") -> Optional[TaskState]:
        """标记任务完成"""
        return self.update_task(
            user_id, conversation_id, corp_id,
            status=TaskStatus.COMPLETED
        )

    def cancel_task(self, user_id: str, conversation_id: str,
                    corp_id: str = "") -> Optional[TaskState]:
        """取消任务"""
        return self.update_task(
            user_id, conversation_id, corp_id,
            status=TaskStatus.CANCELLED
        )

    def has_pending_task(self, user_id: str, conversation_id: str = "",
                         corp_id: str = "") -> bool:
        """检查是否有待处理的任务"""
        state = self.get_task(user_id, conversation_id, corp_id)
        return state is not None and state.status in [
            TaskStatus.PENDING_OUTLINE,
            TaskStatus.PENDING_TEMPLATE,
            TaskStatus.CONFIRMED,
            TaskStatus.GENERATING
        ]

    def get_pending_task(self, user_id: str, conversation_id: str = "",
                         corp_id: str = "") -> Optional[TaskState]:
        """获取待处理的任务"""
        state = self.get_task(user_id, conversation_id, corp_id)
        if state and state.status in [TaskStatus.PENDING_OUTLINE, TaskStatus.PENDING_TEMPLATE, TaskStatus.CONFIRMED, TaskStatus.GENERATING]:
            return state
        return None


# 全局状态管理器实例
state_manager = ConversationStateManager()
