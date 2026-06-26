"""
SQLite 数据模型
存储消息日志、调试记录、巡检数据等
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

from web.config import WEB_DB_PATH

Base = declarative_base()

# 确保目录存在
os.makedirs(os.path.dirname(WEB_DB_PATH), exist_ok=True)

engine = create_engine(f'sqlite:///{WEB_DB_PATH}', echo=False)
SessionLocal = sessionmaker(bind=engine)


class MessageLog(Base):
    """消息日志表"""
    __tablename__ = 'message_logs'

    id = Column(Integer, primary_key=True, index=True)
    msg_id = Column(String(64), unique=True, index=True)
    sender_id = Column(String(64), index=True)
    sender_nick = Column(String(128))
    content = Column(Text)
    message_type = Column(String(32))  # text, picture, file, richText
    conversation_id = Column(String(64))
    corp_id = Column(String(64))
    created_at = Column(DateTime, default=datetime.now, index=True)
    status = Column(String(32))  # success, error, skipped, processing
    error_msg = Column(Text)
    processing_time_ms = Column(Integer)
    skill_used = Column(String(64))  # 使用的技能名称
    kb_results_count = Column(Integer)  # 知识库检索结果数量


class DebugSession(Base):
    """调试会话表"""
    __tablename__ = 'debug_sessions'

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True)
    user_input = Column(Text)
    bot_response = Column(Text)
    processing_steps = Column(Text)  # JSON 格式的处理步骤
    skill_matched = Column(String(64))
    skill_confidence = Column(Float)
    kb_results = Column(Text)  # JSON 格式的知识库结果
    llm_input = Column(Text)
    llm_output = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    processing_time_ms = Column(Integer)
    status = Column(String(32))  # success, error


# ==================== 巡检数据模型 ====================

class InspectionPlanDB(Base):
    """巡检计划表"""
    __tablename__ = 'inspection_plans'

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(String(64), unique=True, index=True)
    plan_name = Column(String(128), nullable=False)
    area_type = Column(String(32), index=True)          # teaching/dormitory/canteen/playground/fire/public
    check_category = Column(String(32), index=True)     # safety/hygiene/facility/discipline
    frequency = Column(String(32))                       # daily/weekly/monthly/custom
    assigned_inspectors = Column(JSON, default=list)     # 巡检员 user_id 列表
    assigned_areas = Column(JSON, default=list)          # 巡检区域列表
    check_items = Column(JSON, default=list)             # 检查项列表
    status = Column(String(32), default='draft')         # draft/active/completed/cancelled
    start_date = Column(String(32))
    end_date = Column(String(32))
    created_by = Column(String(64))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class InspectionPointDB(Base):
    """巡检点位表"""
    __tablename__ = 'inspection_points'

    id = Column(Integer, primary_key=True, index=True)
    point_id = Column(String(64), unique=True, index=True)
    point_name = Column(String(128), nullable=False)
    area_type = Column(String(32), index=True)
    location = Column(String(256))                      # 位置描述
    latitude = Column(Float, default=0.0)
    longitude = Column(Float, default=0.0)
    check_items = Column(JSON, default=list)
    qr_code = Column(String(128))
    requires_photo = Column(Boolean, default=True)
    requires_location = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now, index=True)


class InspectionRecordDB(Base):
    """巡检打卡记录表"""
    __tablename__ = 'inspection_records'

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(String(64), unique=True, index=True)
    plan_id = Column(String(64), index=True)
    point_id = Column(String(64), index=True)
    inspector_id = Column(String(64), index=True)
    inspector_name = Column(String(128))
    check_in_time = Column(DateTime, index=True)
    check_out_time = Column(DateTime)
    latitude = Column(Float, default=0.0)
    longitude = Column(Float, default=0.0)
    location_verified = Column(Boolean, default=False)
    photo_urls = Column(JSON, default=list)
    check_results = Column(JSON, default=list)
    notes = Column(Text)
    overall_status = Column(String(32), default='normal')  # normal/has_issues
    created_at = Column(DateTime, default=datetime.now, index=True)


class InspectionIssueDB(Base):
    """巡检问题表"""
    __tablename__ = 'inspection_issues'

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(String(64), unique=True, index=True)
    record_id = Column(String(64), index=True)
    plan_id = Column(String(64), index=True)
    point_id = Column(String(64), index=True)
    point_name = Column(String(128))
    category = Column(String(32), index=True)           # safety_hazard/hygiene_issue/facility_damage/discipline_violation/fire_safety/other
    title = Column(String(256))
    description = Column(Text)
    photo_urls = Column(JSON, default=list)
    reported_by = Column(String(64))
    reported_by_name = Column(String(128))
    status = Column(String(32), default='pending', index=True)  # pending/assigned/in_progress/pending_review/resolved/closed/rejected
    severity = Column(String(32), default='medium')     # low/medium/high/critical
    assigned_to = Column(String(64), index=True)
    assigned_to_name = Column(String(128))
    assigned_at = Column(DateTime)
    deadline = Column(DateTime)
    rectification_photos = Column(JSON, default=list)
    rectification_notes = Column(Text)
    rectified_at = Column(DateTime)
    reviewer_id = Column(String(64))
    review_result = Column(String(32))                  # pass/reject
    review_notes = Column(Text)
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now, index=True)


class WorkOrderDB(Base):
    """工单表"""
    __tablename__ = 'work_orders'

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(64), unique=True, index=True)
    issue_id = Column(String(64), index=True)
    order_type = Column(String(32), default='rectification')
    status = Column(String(32), default='pending', index=True)
    assigned_by = Column(String(64))
    assigned_to = Column(String(64), index=True)
    assigned_to_name = Column(String(128))
    deadline = Column(DateTime)
    operations = Column(JSON, default=list)             # 操作日志
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 初始化数据库
init_db()
