"""
权限管理模块
支持多组织架构的用户权限管理和审批流程
"""
import os
import json
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class AccessLevel(Enum):
    """访问级别"""
    PUBLIC = "public"           # 公开内容
    INTERNAL = "internal"       # 内部内容
    CONFIDENTIAL = "confidential"  # 机密内容


class ApprovalStatus(Enum):
    """审批状态"""
    PENDING = "pending"         # 待审批
    APPROVED = "approved"       # 已批准
    REJECTED = "rejected"       # 已拒绝
    EXPIRED = "expired"         # 已过期


@dataclass
class UserInfo:
    """用户信息"""
    user_id: str
    name: str
    role: str = "teacher"       # 角色：admin, principal, director, teacher, student
    department: str = ""        # 部门
    manager_id: str = ""        # 上级用户ID
    permissions: List[str] = field(default_factory=lambda: ["public", "internal"])
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalRequest:
    """审批请求"""
    request_id: str
    user_id: str
    user_name: str
    user_department: str
    manager_id: str
    query: str                  # 查询内容
    access_level: str           # 申请访问的级别
    status: str = "pending"     # pending, approved, rejected, expired
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    approver_id: str = ""
    approve_time: float = 0
    reject_reason: str = ""


# 默认角色配置
DEFAULT_ROLES_CONFIG = {
    "admin": {
        "name": "管理员",
        "search_permissions": ["*"],
        "need_approval": False
    },
    "principal": {
        "name": "校长",
        "search_permissions": ["*"],
        "need_approval": False
    },
    "director": {
        "name": "主任",
        "search_permissions": ["public", "internal", "confidential"],
        "need_approval": False
    },
    "teacher": {
        "name": "教师",
        "search_permissions": ["public", "internal"],
        "need_approval": True,
        "approval_for": ["confidential"]
    },
    "student": {
        "name": "学生",
        "search_permissions": ["public"],
        "need_approval": True,
        "approval_for": ["internal", "confidential"]
    }
}


class PermissionManager:
    """权限管理器"""

    def __init__(self, knowledge_dir: str, corp_id: str):
        """
        初始化权限管理器

        参数:
            knowledge_dir: 知识库目录路径
            corp_id: 企业/组织ID
        """
        self.knowledge_dir = knowledge_dir
        self.corp_id = corp_id
        self._users_file = os.path.join(knowledge_dir, "structured", "users.json")
        self._approval_file = os.path.join(knowledge_dir, "structured", "approvals.json")
        self._meta_file = os.path.join(knowledge_dir, "meta.json")

        # 加载数据
        self._users: List[UserInfo] = self._load_users()
        self._approvals: List[ApprovalRequest] = self._load_approvals()
        self._roles_config = self._load_roles_config()

    def _load_users(self) -> List[UserInfo]:
        """加载用户信息"""
        if not os.path.exists(self._users_file):
            return []

        try:
            with open(self._users_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [UserInfo(**user) for user in data]
        except Exception as e:
            logger.error(f"加载用户信息失败: {e}")
            return []

    def _save_users(self):
        """保存用户信息"""
        try:
            os.makedirs(os.path.dirname(self._users_file), exist_ok=True)
            with open(self._users_file, "w", encoding="utf-8") as f:
                json.dump([asdict(u) for u in self._users], f,
                         ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存用户信息失败: {e}")

    def _load_approvals(self) -> List[ApprovalRequest]:
        """加载审批请求"""
        if not os.path.exists(self._approval_file):
            return []

        try:
            with open(self._approval_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [ApprovalRequest(**req) for req in data]
        except Exception as e:
            logger.error(f"加载审批请求失败: {e}")
            return []

    def _save_approvals(self):
        """保存审批请求"""
        try:
            os.makedirs(os.path.dirname(self._approval_file), exist_ok=True)
            with open(self._approval_file, "w", encoding="utf-8") as f:
                json.dump([asdict(r) for r in self._approvals], f,
                         ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存审批请求失败: {e}")

    def _load_roles_config(self) -> dict:
        """加载角色配置"""
        if not os.path.exists(self._meta_file):
            return DEFAULT_ROLES_CONFIG

        try:
            with open(self._meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            return meta.get("roles", DEFAULT_ROLES_CONFIG)
        except Exception as e:
            logger.error(f"加载角色配置失败: {e}")
            return DEFAULT_ROLES_CONFIG

    # ==================== 用户管理 ====================

    def get_user(self, user_id: str) -> Optional[UserInfo]:
        """获取用户信息"""
        for user in self._users:
            if user.user_id == user_id:
                return user
        return None

    def get_user_role(self, user_id: str) -> str:
        """获取用户角色，默认为 teacher"""
        user = self.get_user(user_id)
        return user.role if user else "teacher"

    def get_user_name(self, user_id: str) -> str:
        """获取用户名称"""
        user = self.get_user(user_id)
        return user.name if user else "未知用户"

    def get_manager(self, user_id: str) -> Optional[UserInfo]:
        """获取用户的上级"""
        user = self.get_user(user_id)
        if not user or not user.manager_id:
            return None
        return self.get_user(user.manager_id)

    def add_user(self, user: UserInfo) -> bool:
        """添加用户"""
        # 检查是否已存在
        if self.get_user(user.user_id):
            logger.warning(f"用户 {user.user_id} 已存在")
            return False

        self._users.append(user)
        self._save_users()
        logger.info(f"添加用户: {user.name} ({user.user_id})")
        return True

    def update_user(self, user_id: str, **kwargs) -> bool:
        """更新用户信息"""
        user = self.get_user(user_id)
        if not user:
            return False

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        self._save_users()
        return True

    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        self._users = [u for u in self._users if u.user_id != user_id]
        self._save_users()
        return True

    def list_users(self) -> List[UserInfo]:
        """列出所有用户"""
        return self._users.copy()

    # ==================== 权限检查 ====================

    def get_allowed_access_levels(self, user_id: str) -> List[str]:
        """获取用户允许访问的内容级别"""
        user = self.get_user(user_id)
        if not user:
            return ["public"]  # 未知用户只能访问公开内容

        role_config = self._roles_config.get(user.role, {})
        permissions = role_config.get("search_permissions", ["public"])

        # 如果是通配符，返回所有级别
        if "*" in permissions:
            return [level.value for level in AccessLevel]

        return permissions

    def check_permission(self, user_id: str, access_level: str) -> bool:
        """检查用户是否有权限访问指定级别的内容"""
        allowed_levels = self.get_allowed_access_levels(user_id)
        return access_level in allowed_levels

    def need_approval(self, user_id: str, access_level: str) -> bool:
        """检查访问指定级别是否需要审批"""
        user = self.get_user(user_id)
        if not user:
            return True  # 未知用户需要审批

        role_config = self._roles_config.get(user.role, {})

        # 如果角色不需要审批
        if not role_config.get("need_approval", False):
            return False

        # 检查该级别是否在需要审批的列表中
        approval_for = role_config.get("approval_for", [])
        return access_level in approval_for

    def filter_results_by_permission(self, user_id: str,
                                      results: List[Any]) -> List[Any]:
        """根据权限过滤搜索结果"""
        allowed_levels = self.get_allowed_access_levels(user_id)

        filtered = []
        for result in results:
            # 获取知识块的访问级别，默认为 public
            access_level = getattr(result.chunk, 'access_level', 'public')
            if access_level in allowed_levels:
                filtered.append(result)

        return filtered

    # ==================== 审批流程 ====================

    def create_approval_request(self, user_id: str, query: str,
                                 access_level: str) -> Optional[ApprovalRequest]:
        """创建审批请求"""
        user = self.get_user(user_id)
        if not user:
            logger.error(f"用户 {user_id} 不存在，无法创建审批请求")
            return None

        manager = self.get_manager(user_id)
        if not manager:
            logger.error(f"用户 {user_id} 没有上级，无法创建审批请求")
            return None

        request_id = f"approval_{int(time.time() * 1000)}"
        request = ApprovalRequest(
            request_id=request_id,
            user_id=user_id,
            user_name=user.name,
            user_department=user.department,
            manager_id=manager.user_id,
            query=query,
            access_level=access_level,
            status=ApprovalStatus.PENDING.value
        )

        self._approvals.append(request)
        self._save_approvals()

        logger.info(f"创建审批请求: {request_id}, 用户: {user.name}, 查询: {query}")
        return request

    def get_pending_approvals(self, manager_id: str) -> List[ApprovalRequest]:
        """获取待审批的请求"""
        return [
            req for req in self._approvals
            if req.manager_id == manager_id and req.status == ApprovalStatus.PENDING.value
        ]

    def get_approval_by_id(self, request_id: str) -> Optional[ApprovalRequest]:
        """根据ID获取审批请求"""
        for req in self._approvals:
            if req.request_id == request_id:
                return req
        return None

    def approve_request(self, request_id: str, approver_id: str) -> bool:
        """批准审批请求"""
        request = self.get_approval_by_id(request_id)
        if not request:
            return False

        request.status = ApprovalStatus.APPROVED.value
        request.approver_id = approver_id
        request.approve_time = time.time()
        request.updated_at = time.time()

        self._save_approvals()
        logger.info(f"审批请求 {request_id} 已批准")
        return True

    def reject_request(self, request_id: str, approver_id: str,
                        reason: str = "") -> bool:
        """拒绝审批请求"""
        request = self.get_approval_by_id(request_id)
        if not request:
            return False

        request.status = ApprovalStatus.REJECTED.value
        request.approver_id = approver_id
        request.approve_time = time.time()
        request.reject_reason = reason
        request.updated_at = time.time()

        self._save_approvals()
        logger.info(f"审批请求 {request_id} 已拒绝")
        return True

    def get_user_pending_request(self, user_id: str,
                                  access_level: str) -> Optional[ApprovalRequest]:
        """获取用户指定级别的待审批请求"""
        for req in self._approvals:
            if (req.user_id == user_id and
                req.access_level == access_level and
                req.status == ApprovalStatus.PENDING.value):
                return req
        return None

    # ==================== 工具方法 ====================

    def get_role_name(self, role: str) -> str:
        """获取角色显示名称"""
        role_config = self._roles_config.get(role, {})
        return role_config.get("name", role)

    def get_access_level_name(self, level: str) -> str:
        """获取访问级别显示名称"""
        names = {
            "public": "公开",
            "internal": "内部",
            "confidential": "机密"
        }
        return names.get(level, level)


# ==================== 全局实例管理 ====================

_permission_managers: Dict[str, PermissionManager] = {}


def get_permission_manager(knowledge_dir: str,
                            corp_id: str) -> PermissionManager:
    """获取权限管理器实例（单例模式）"""
    if corp_id not in _permission_managers:
        _permission_managers[corp_id] = PermissionManager(knowledge_dir, corp_id)
    return _permission_managers[corp_id]
