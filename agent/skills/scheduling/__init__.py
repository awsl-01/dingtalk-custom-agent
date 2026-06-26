"""
排课系统模块

提供自动排课、冲突检测、课表优化等功能。

主要组件：
- models: 数据模型（班级、教师、课程、教室、时间段）
- constraints: 约束条件管理
- detector: 冲突检测
- algorithm: 排课算法
- excel_handler: Excel 数据导入导出
"""

from .models import (
    TimeSlot,
    Teacher,
    Classroom,
    Course,
    ClassGroup,
    ScheduleEntry,
    Schedule,
    Weekday,
    PeriodType,
)
from .constraints import ConstraintManager, ConstraintType
from .detector import ConflictDetector, ConflictType
from .algorithm import ScheduleAlgorithm, SchedulingTask, SchedulingResult
from .excel_handler import (
    generate_template,
    parse_scheduling_excel,
    export_schedule_to_excel,
)
from .swap_manager import SwapManager, SwapRequest, SwapStatus

__all__ = [
    # 数据模型
    'TimeSlot',
    'Teacher',
    'Classroom',
    'Course',
    'ClassGroup',
    'ScheduleEntry',
    'Schedule',
    # 约束管理
    'ConstraintManager',
    'ConstraintType',
    # 冲突检测
    'ConflictDetector',
    'ConflictType',
    # 排课算法
    'ScheduleAlgorithm',
    'SchedulingTask',
    'SchedulingResult',
    # Excel 处理
    'generate_template',
    'parse_scheduling_excel',
    'export_schedule_to_excel',
    # 调课流程
    'SwapManager',
    'SwapRequest',
    'SwapStatus',
]
