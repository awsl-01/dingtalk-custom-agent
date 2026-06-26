"""
调课流程管理器

实现多步骤调课工作流：
1. 发起调课 → 查询空闲教师
2. 选定对象 → 对方确认
3. 对方同意 → 上级审批
4. 审批通过 → 执行调课
"""
import os
import json
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class SwapStatus(Enum):
    """调课状态"""
    PENDING_TYPE = "pending_type"  # 等待选择调课类型（永久/临时）
    SELECTING = "selecting"        # 等待发起人选择调换对象
    CONFIRMING = "confirming"      # 等待对方教师确认
    APPROVING = "approving"        # 等待上级审批
    EXECUTING = "executing"        # 执行中
    COMPLETED = "completed"        # 已完成
    REJECTED = "rejected"          # 被拒绝
    CANCELLED = "cancelled"        # 已取消
    EXPIRED = "expired"            # 已过期


@dataclass
class SwapRequest:
    """调课请求"""
    swap_id: str              # 唯一ID
    requester_id: str         # 发起人ID
    requester_nick: str       # 发起人昵称
    conversation_id: str      # 会话ID
    corp_id: str              # 企业ID
    # 调课信息
    class_name: str           # 班级名称
    class_id: str = ""        # 班级ID
    day1: str = ""            # 第一天（周一~周五）
    period1: int = 0          # 第一节次
    day2: str = ""            # 第二天
    period2: int = 0          # 第二节次
    course1_name: str = ""    # 第一天课程名
    course1_teacher: str = "" # 第一天教师
    course2_name: str = ""    # 第二天课程名
    course2_teacher: str = "" # 第二天教师
    entry1_id: str = ""       # 第一个课程条目ID
    entry2_id: str = ""       # 第二个课程条目ID
    permanent: bool = True    # 是否永久调课
    reason: str = ""          # 调课原因
    # 流程状态
    status: str = SwapStatus.SELECTING.value
    target_teacher_id: str = ""    # 对方教师ID
    target_teacher_nick: str = ""  # 对方教师昵称
    approver_id: str = ""          # 审批人ID
    approver_nick: str = ""        # 审批人昵称
    # 时间戳
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: float = 0.0       # 过期时间


class SwapManager:
    """调课流程管理器"""

    def __init__(self, scheduling_dir: str):
        """
        参数:
            scheduling_dir: 排课数据目录（如 knowledge/{corp_id}/scheduling/）
        """
        self._dir = scheduling_dir
        self._requests_file = os.path.join(scheduling_dir, "swap_requests.json")
        self._log_file = os.path.join(scheduling_dir, "swap_log.json")
        self._requests: Dict[str, SwapRequest] = {}
        self._load()

    def _load(self):
        """加载待处理的调课请求"""
        if os.path.exists(self._requests_file):
            try:
                with open(self._requests_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for swap_id, req_data in data.items():
                    self._requests[swap_id] = SwapRequest(**req_data)
                logger.info(f"加载 {len(self._requests)} 个待处理调课请求")
            except Exception as e:
                logger.error(f"加载调课请求失败: {e}")

    def _save(self):
        """保存待处理的调课请求"""
        try:
            data = {swap_id: asdict(req) for swap_id, req in self._requests.items()}
            with open(self._requests_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存调课请求失败: {e}")

    def _log_swap(self, request: SwapRequest, action: str, detail: str = ""):
        """记录调课日志"""
        log_entry = {
            "swap_id": request.swap_id,
            "action": action,
            "requester": request.requester_nick,
            "requester_id": request.requester_id,
            "class_name": request.class_name,
            "day1": request.day1,
            "period1": request.period1,
            "day2": request.day2,
            "period2": request.period2,
            "target_teacher": request.target_teacher_nick,
            "approver": request.approver_nick,
            "permanent": request.permanent,
            "reason": request.reason,
            "detail": detail,
            "timestamp": time.time(),
            "created_at": request.created_at,
        }

        logs = []
        if os.path.exists(self._log_file):
            try:
                with open(self._log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                pass

        logs.append(log_entry)

        try:
            with open(self._log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存调课日志失败: {e}")

    def create_request(
        self,
        requester_id: str,
        requester_nick: str,
        conversation_id: str,
        corp_id: str,
        class_name: str,
        day1: str,
        period1: int,
        day2: str,
        period2: int,
        course1_name: str = "",
        course1_teacher: str = "",
        course2_name: str = "",
        course2_teacher: str = "",
        entry1_id: str = "",
        entry2_id: str = "",
        permanent: bool = True,
        reason: str = "",
        class_id: str = "",
    ) -> SwapRequest:
        """创建调课请求"""
        swap_id = f"swap_{int(time.time() * 1000)}"

        request = SwapRequest(
            swap_id=swap_id,
            requester_id=requester_id,
            requester_nick=requester_nick,
            conversation_id=conversation_id,
            corp_id=corp_id,
            class_name=class_name,
            class_id=class_id,
            day1=day1,
            period1=period1,
            day2=day2,
            period2=period2,
            course1_name=course1_name,
            course1_teacher=course1_teacher,
            course2_name=course2_name,
            course2_teacher=course2_teacher,
            entry1_id=entry1_id,
            entry2_id=entry2_id,
            permanent=permanent,
            reason=reason,
            status=SwapStatus.SELECTING.value,
            created_at=time.time(),
            updated_at=time.time(),
            expires_at=time.time() + 3600,  # 1小时过期
        )

        self._requests[swap_id] = request
        self._save()
        self._log_swap(request, "created")

        logger.info(f"创建调课请求: {swap_id} by {requester_nick}")
        return request

    def get_request(self, swap_id: str) -> Optional[SwapRequest]:
        """获取调课请求"""
        return self._requests.get(swap_id)

    def get_requests_by_user(self, user_id: str, status: str = None) -> List[SwapRequest]:
        """获取用户相关的调课请求"""
        results = []
        for req in self._requests.values():
            if req.requester_id == user_id or req.target_teacher_id == user_id:
                if status is None or req.status == status:
                    results.append(req)
        return results

    def get_pending_for_user(self, user_id: str) -> Optional[SwapRequest]:
        """获取用户待处理的调课请求（返回最新的）"""
        latest_req = None
        for req in self._requests.values():
            if req.status == SwapStatus.PENDING_TYPE.value and req.requester_id == user_id:
                if latest_req is None or req.created_at > latest_req.created_at:
                    latest_req = req
            if req.status == SwapStatus.SELECTING.value and req.requester_id == user_id:
                if latest_req is None or req.created_at > latest_req.created_at:
                    latest_req = req
            if req.status == SwapStatus.CONFIRMING.value and (req.target_teacher_id == user_id or req.requester_id == user_id):
                if latest_req is None or req.created_at > latest_req.created_at:
                    latest_req = req
            if req.status == SwapStatus.APPROVING.value and req.approver_id == user_id:
                if latest_req is None or req.created_at > latest_req.created_at:
                    latest_req = req
        return latest_req

    def create_pending_type_request(
        self,
        requester_id: str,
        requester_nick: str,
        conversation_id: str,
        corp_id: str,
        class_name: str,
        day1: str,
        period1: int,
        day2: str,
        period2: int,
        course1_name: str = "",
        course1_teacher: str = "",
        course2_name: str = "",
        course2_teacher: str = "",
        entry1_id: str = "",
        entry2_id: str = "",
        class_id: str = "",
    ) -> SwapRequest:
        """创建等待选择调课类型的请求"""
        swap_id = f"swap_{int(time.time() * 1000)}"

        request = SwapRequest(
            swap_id=swap_id,
            requester_id=requester_id,
            requester_nick=requester_nick,
            conversation_id=conversation_id,
            corp_id=corp_id,
            class_name=class_name,
            class_id=class_id,
            day1=day1,
            period1=period1,
            day2=day2,
            period2=period2,
            course1_name=course1_name,
            course1_teacher=course1_teacher,
            course2_name=course2_name,
            course2_teacher=course2_teacher,
            entry1_id=entry1_id,
            entry2_id=entry2_id,
            permanent=True,  # 默认值，后续会更新
            status=SwapStatus.PENDING_TYPE.value,
            created_at=time.time(),
            updated_at=time.time(),
            expires_at=time.time() + 3600,  # 1小时过期
        )

        self._requests[swap_id] = request
        self._save()
        self._log_swap(request, "created_pending_type")

        logger.info(f"创建等待选择类型的调课请求: {swap_id} by {requester_nick}")
        return request

    def select_type(self, swap_id: str, permanent: bool) -> bool:
        """选择调课类型（永久/临时）"""
        request = self._requests.get(swap_id)
        if not request or request.status != SwapStatus.PENDING_TYPE.value:
            return False

        request.permanent = permanent
        request.status = SwapStatus.SELECTING.value
        request.updated_at = time.time()

        self._save()
        self._log_swap(request, "type_selected", f"类型: {'永久' if permanent else '临时'}")
        return True

    def select_target(self, swap_id: str, target_teacher_id: str, target_teacher_nick: str) -> bool:
        """选择调换对象"""
        request = self._requests.get(swap_id)
        if not request or request.status != SwapStatus.SELECTING.value:
            return False

        request.target_teacher_id = target_teacher_id
        request.target_teacher_nick = target_teacher_nick
        request.status = SwapStatus.CONFIRMING.value
        request.updated_at = time.time()

        self._save()
        self._log_swap(request, "target_selected", f"目标教师: {target_teacher_nick}")
        return True

    def confirm_by_target(self, swap_id: str, confirmer_id: str, approved: bool) -> bool:
        """对方教师确认"""
        request = self._requests.get(swap_id)
        if not request or request.status != SwapStatus.CONFIRMING.value:
            return False
        if request.target_teacher_id != confirmer_id:
            return False

        if not approved:
            request.status = SwapStatus.REJECTED.value
            request.updated_at = time.time()
            self._save()
            self._log_swap(request, "rejected_by_target")
            return True

        request.status = SwapStatus.APPROVING.value
        request.updated_at = time.time()
        self._save()
        self._log_swap(request, "confirmed_by_target")
        return True

    def approve_by_superior(self, swap_id: str, approver_id: str, approver_nick: str, approved: bool) -> bool:
        """上级审批"""
        request = self._requests.get(swap_id)
        if not request or request.status != SwapStatus.APPROVING.value:
            return False
        if request.approver_id and request.approver_id != approver_id:
            return False

        if not approved:
            request.status = SwapStatus.REJECTED.value
            request.updated_at = time.time()
            self._save()
            self._log_swap(request, "rejected_by_superior", f"审批人: {approver_nick}")
            return True

        request.status = SwapStatus.COMPLETED.value
        request.approver_id = approver_id
        request.approver_nick = approver_nick
        request.updated_at = time.time()
        self._save()
        self._log_swap(request, "approved_by_superior", f"审批人: {approver_nick}")
        return True

    def cancel_request(self, swap_id: str, user_id: str) -> bool:
        """取消调课请求"""
        request = self._requests.get(swap_id)
        if not request:
            return False

        # 只有发起人可以取消
        if request.requester_id != user_id:
            return False

        if request.status in [SwapStatus.COMPLETED.value, SwapStatus.CANCELLED.value, SwapStatus.EXPIRED.value]:
            return False

        request.status = SwapStatus.CANCELLED.value
        request.updated_at = time.time()
        self._save()
        self._log_swap(request, "cancelled")
        return True

    def cleanup_expired(self) -> int:
        """清理过期的请求"""
        now = time.time()
        expired_ids = []

        for swap_id, request in self._requests.items():
            if request.expires_at > 0 and now > request.expires_at:
                if request.status not in [SwapStatus.COMPLETED.value, SwapStatus.CANCELLED.value, SwapStatus.EXPIRED.value]:
                    request.status = SwapStatus.EXPIRED.value
                    request.updated_at = now
                    expired_ids.append(swap_id)
                    self._log_swap(request, "expired")

        if expired_ids:
            self._save()
            logger.info(f"清理了 {len(expired_ids)} 个过期调课请求")

        return len(expired_ids)

    def get_stats(self) -> dict:
        """获取调课统计"""
        stats = {
            "total": len(self._requests),
            "by_status": {},
        }
        for req in self._requests.values():
            status = req.status
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        return stats
