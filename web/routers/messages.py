"""
消息日志 API
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import Optional
import json

from web.models import get_db, MessageLog

router = APIRouter()


@router.get("/list")
async def list_messages(
    sender_id: Optional[str] = Query(None, description="发送者ID"),
    message_type: Optional[str] = Query(None, description="消息类型"),
    status: Optional[str] = Query(None, description="处理状态"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取消息列表"""
    query = db.query(MessageLog)

    # 筛选条件
    if sender_id:
        query = query.filter(MessageLog.sender_id == sender_id)
    if message_type:
        query = query.filter(MessageLog.message_type == message_type)
    if status:
        query = query.filter(MessageLog.status == status)
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(MessageLog.created_at >= start)
        except ValueError:
            pass
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(MessageLog.created_at < end)
        except ValueError:
            pass

    # 总数
    total = query.count()

    # 分页
    messages = query.order_by(desc(MessageLog.created_at)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    # 序列化
    result = []
    for msg in messages:
        result.append({
            "id": msg.id,
            "msg_id": msg.msg_id,
            "sender_id": msg.sender_id,
            "sender_nick": msg.sender_nick,
            "content": msg.content[:200] if msg.content else "",
            "full_content": msg.content,
            "message_type": msg.message_type,
            "conversation_id": msg.conversation_id,
            "corp_id": msg.corp_id,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
            "status": msg.status,
            "error_msg": msg.error_msg,
            "processing_time_ms": msg.processing_time_ms,
            "skill_used": msg.skill_used,
            "kb_results_count": msg.kb_results_count,
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "messages": result
    }


@router.get("/{msg_id}")
async def get_message(msg_id: str, db: Session = Depends(get_db)):
    """获取消息详情"""
    msg = db.query(MessageLog).filter(MessageLog.msg_id == msg_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")

    return {
        "id": msg.id,
        "msg_id": msg.msg_id,
        "sender_id": msg.sender_id,
        "sender_nick": msg.sender_nick,
        "content": msg.content,
        "message_type": msg.message_type,
        "conversation_id": msg.conversation_id,
        "corp_id": msg.corp_id,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
        "status": msg.status,
        "error_msg": msg.error_msg,
        "processing_time_ms": msg.processing_time_ms,
        "skill_used": msg.skill_used,
        "kb_results_count": msg.kb_results_count,
    }


@router.get("/stats/overview")
async def get_message_stats(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    db: Session = Depends(get_db)
):
    """获取消息统计概览"""
    start_date = datetime.now() - timedelta(days=days)

    # 总消息数
    total = db.query(func.count(MessageLog.id)).filter(
        MessageLog.created_at >= start_date
    ).scalar() or 0

    # 按状态统计
    status_stats = db.query(
        MessageLog.status,
        func.count(MessageLog.id)
    ).filter(
        MessageLog.created_at >= start_date
    ).group_by(MessageLog.status).all()

    # 按消息类型统计
    type_stats = db.query(
        MessageLog.message_type,
        func.count(MessageLog.id)
    ).filter(
        MessageLog.created_at >= start_date
    ).group_by(MessageLog.message_type).all()

    # 按技能统计
    skill_stats = db.query(
        MessageLog.skill_used,
        func.count(MessageLog.id)
    ).filter(
        MessageLog.created_at >= start_date,
        MessageLog.skill_used.isnot(None),
        MessageLog.skill_used != ""
    ).group_by(MessageLog.skill_used).all()

    return {
        "period_days": days,
        "total": total,
        "by_status": {s[0]: s[1] for s in status_stats},
        "by_type": {s[0]: s[1] for s in type_stats},
        "by_skill": {s[0]: s[1] for s in skill_stats},
    }


@router.post("/log")
async def create_message_log(
    msg_id: str,
    sender_id: str,
    sender_nick: str = "",
    content: str = "",
    message_type: str = "text",
    conversation_id: str = "",
    corp_id: str = "",
    db: Session = Depends(get_db)
):
    """创建消息日志（供主程序调用）"""
    # 检查是否已存在
    existing = db.query(MessageLog).filter(MessageLog.msg_id == msg_id).first()
    if existing:
        return {"message": "消息已存在", "id": existing.id}

    log = MessageLog(
        msg_id=msg_id,
        sender_id=sender_id,
        sender_nick=sender_nick,
        content=content,
        message_type=message_type,
        conversation_id=conversation_id,
        corp_id=corp_id,
        status="processing"
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return {"message": "创建成功", "id": log.id}


@router.put("/{msg_id}/status")
async def update_message_status(
    msg_id: str,
    status: str,
    error_msg: str = "",
    processing_time_ms: int = 0,
    skill_used: str = "",
    kb_results_count: int = 0,
    db: Session = Depends(get_db)
):
    """更新消息状态（供主程序调用）"""
    msg = db.query(MessageLog).filter(MessageLog.msg_id == msg_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")

    msg.status = status
    if error_msg:
        msg.error_msg = error_msg
    if processing_time_ms:
        msg.processing_time_ms = processing_time_ms
    if skill_used:
        msg.skill_used = skill_used
    if kb_results_count:
        msg.kb_results_count = kb_results_count

    db.commit()

    return {"message": "更新成功"}
