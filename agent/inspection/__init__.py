"""
学校区域巡检模块

覆盖教学区、宿舍、食堂、操场、消防设施、公共区域等
包含安全、卫生、设施、纪律四大类检查项

核心流程：
巡检计划下发 → 现场点位打卡 → 问题图文上报 → 自动派单整改 → 复查验收 → 数据统计可视化
"""

from .models import (
    InspectionPlan, InspectionPoint, InspectionRecord,
    InspectionIssue, WorkOrder, IssueCategory, IssueStatus,
    AreaType, CheckCategory,
)
from .service import InspectionService

__all__ = [
    "InspectionPlan",
    "InspectionPoint",
    "InspectionRecord",
    "InspectionIssue",
    "WorkOrder",
    "IssueCategory",
    "IssueStatus",
    "AreaType",
    "CheckCategory",
    "InspectionService",
]
