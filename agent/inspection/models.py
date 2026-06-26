"""
巡检数据模型

定义巡检相关的枚举和数据结构
"""
import json
import time
import logging
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# ==================== 枚举定义 ====================

class AreaType(str, Enum):
    """区域类型"""
    TEACHING = "teaching"          # 教学区
    DORMITORY = "dormitory"        # 宿舍区
    CANTEEN = "canteen"            # 食堂
    PLAYGROUND = "playground"      # 操场
    FIRE_FACILITY = "fire"         # 消防设施
    PUBLIC_AREA = "public"         # 公共区域
    OTHER = "other"                # 其他


class CheckCategory(str, Enum):
    """检查大类（四大类）"""
    SAFETY = "safety"              # 安全
    HYGIENE = "hygiene"            # 卫生
    FACILITY = "facility"          # 设施
    DISCIPLINE = "discipline"      # 纪律


class IssueCategory(str, Enum):
    """问题分类"""
    SAFETY_HAZARD = "safety_hazard"          # 安全隐患
    HYGIENE_ISSUE = "hygiene_issue"          # 卫生问题
    FACILITY_DAMAGE = "facility_damage"      # 设施损坏
    DISCIPLINE_VIOLATION = "discipline_violation"  # 纪律违规
    FIRE_SAFETY = "fire_safety"              # 消防安全
    OTHER = "other"                          # 其他


class IssueStatus(str, Enum):
    """问题/工单状态"""
    PENDING = "pending"              # 待处理
    ASSIGNED = "assigned"            # 已派单
    IN_PROGRESS = "in_progress"      # 整改中
    PENDING_REVIEW = "pending_review"  # 待复查
    RESOLVED = "resolved"            # 已解决
    CLOSED = "closed"               # 已关闭
    REJECTED = "rejected"           # 已驳回


class PlanStatus(str, Enum):
    """计划状态"""
    DRAFT = "draft"                  # 草稿
    ACTIVE = "active"               # 进行中
    COMPLETED = "completed"         # 已完成
    CANCELLED = "cancelled"         # 已取消


class CheckFrequency(str, Enum):
    """巡检频率"""
    DAILY = "daily"                  # 每天
    WEEKLY = "weekly"               # 每周
    MONTHLY = "monthly"             # 每月
    CUSTOM = "custom"               # 自定义


# ==================== 数据类 ====================

@dataclass
class InspectionPlan:
    """巡检计划"""
    plan_id: str
    plan_name: str
    area_type: str               # AreaType 的值
    check_category: str          # CheckCategory 的值
    frequency: str               # CheckFrequency 的值
    assigned_inspectors: list = field(default_factory=list)  # 巡检员 user_id 列表
    assigned_areas: list = field(default_factory=list)       # 巡检区域列表
    check_items: list = field(default_factory=list)          # 检查项列表
    status: str = "draft"        # PlanStatus 的值
    start_date: str = ""
    end_date: str = ""
    created_by: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    description: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()
        if not self.updated_at:
            self.updated_at = time.time()


@dataclass
class InspectionPoint:
    """巡检点位"""
    point_id: str
    point_name: str
    area_type: str               # AreaType 的值
    location: str                # 位置描述
    latitude: float = 0.0        # 纬度（可选，用于地图定位）
    longitude: float = 0.0       # 经度（可选）
    check_items: list = field(default_factory=list)  # 该点位的检查项
    qr_code: str = ""            # 二维码（可选，用于扫码打卡）
    requires_photo: bool = True  # 是否要求拍照
    requires_location: bool = False  # 是否要求定位
    is_active: bool = True
    created_at: float = 0.0
    metadata: dict = field(default_factory=dict)
    # 负责人信息（用于问题上报后自动派单）
    assigned_to: str = ""        # 负责人 user_id
    assigned_to_name: str = ""   # 负责人姓名
    assigned_to_phone: str = ""  # 负责人联系电话（可选）

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()


@dataclass
class CheckItem:
    """检查项"""
    item_id: str
    item_name: str
    category: str                # CheckCategory 的值
    description: str = ""        # 检查标准/说明
    is_required: bool = True     # 是否必检项
    sort_order: int = 0


@dataclass
class InspectionRecord:
    """巡检打卡记录"""
    record_id: str
    plan_id: str
    point_id: str
    inspector_id: str            # 巡检员 user_id
    inspector_name: str = ""
    check_in_time: float = 0.0   # 打卡时间
    check_out_time: float = 0.0  # 离开时间（可选）
    latitude: float = 0.0
    longitude: float = 0.0
    location_verified: bool = False  # 定位是否验证通过
    photo_urls: list = field(default_factory=list)  # 现场照片
    check_results: list = field(default_factory=list)  # 检查结果列表
    notes: str = ""              # 备注
    overall_status: str = "normal"  # normal/has_issues
    created_at: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()
        if not self.check_in_time:
            self.check_in_time = time.time()


@dataclass
class CheckResult:
    """单项检查结果"""
    item_id: str
    item_name: str
    status: str                  # pass/warn/fail
    photo_url: str = ""          # 问题照片
    description: str = ""        # 问题描述


@dataclass
class InspectionIssue:
    """巡检问题"""
    issue_id: str
    record_id: str               # 关联的巡检记录
    plan_id: str
    point_id: str
    category: str                # IssueCategory 的值
    point_name: str = ""
    title: str = ""
    description: str = ""
    photo_urls: list = field(default_factory=list)
    reported_by: str = ""        # 上报人 user_id
    reported_by_name: str = ""
    reported_at: float = 0.0
    status: str = "pending"      # IssueStatus 的值
    severity: str = "medium"     # low/medium/high/critical
    # 整改相关
    assigned_to: str = ""        # 整改负责人 user_id
    assigned_to_name: str = ""
    assigned_at: float = 0.0
    deadline: float = 0.0        # 整改截止时间
    # 整改反馈
    rectification_photos: list = field(default_factory=list)
    rectification_notes: str = ""
    rectified_at: float = 0.0
    # 复查相关
    reviewer_id: str = ""
    review_result: str = ""      # pass/reject
    review_notes: str = ""
    reviewed_at: float = 0.0
    created_at: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()
        if not self.reported_at:
            self.reported_at = time.time()


@dataclass
class WorkOrder:
    """工单"""
    order_id: str
    issue_id: str
    order_type: str = "rectification"  # rectification/review
    status: str = "pending"      # IssueStatus 的值
    assigned_by: str = ""
    assigned_to: str = ""
    assigned_to_name: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    deadline: float = 0.0
    # 操作记录
    operations: list = field(default_factory=list)  # 操作日志

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()
        if not self.updated_at:
            self.updated_at = time.time()


@dataclass
class InspectionStats:
    """巡检统计"""
    total_plans: int = 0
    active_plans: int = 0
    total_points: int = 0
    total_records_today: int = 0
    total_records_week: int = 0
    total_issues: int = 0
    pending_issues: int = 0
    resolved_issues: int = 0
    total_orders: int = 0
    pending_orders: int = 0
    by_area: dict = field(default_factory=dict)        # 按区域统计
    by_category: dict = field(default_factory=dict)    # 按检查类统计
    by_severity: dict = field(default_factory=dict)    # 按严重程度统计
