"""
仪表盘 API - 系统概览和统计
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import os
import logging

from web.models import get_db, MessageLog, DebugSession
from web.config import KNOWLEDGE_DIR

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """获取仪表盘统计数据"""
    # 消息统计
    total_messages = db.query(func.count(MessageLog.id)).scalar() or 0
    success_messages = db.query(func.count(MessageLog.id)).filter(
        MessageLog.status == "success"
    ).scalar() or 0
    error_messages = db.query(func.count(MessageLog.id)).filter(
        MessageLog.status == "error"
    ).scalar() or 0

    # 今日消息
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_messages = db.query(func.count(MessageLog.id)).filter(
        MessageLog.created_at >= today
    ).scalar() or 0

    # 活跃用户数
    active_users = db.query(func.count(func.distinct(MessageLog.sender_id))).scalar() or 0

    # 知识库统计
    kb_stats = await _get_knowledge_stats()

    # 调试会话统计
    debug_sessions = db.query(func.count(DebugSession.id)).scalar() or 0

    return {
        "messages": {
            "total": total_messages,
            "success": success_messages,
            "error": error_messages,
            "today": today_messages,
        },
        "users": {
            "active": active_users,
        },
        "knowledge": kb_stats,
        "debug": {
            "sessions": debug_sessions,
        }
    }


@router.get("/recent-activity")
async def get_recent_activity(db: Session = Depends(get_db)):
    """获取最近活动（最近7天的消息趋势）"""
    days = []
    for i in range(6, -1, -1):
        date = datetime.now() - timedelta(days=i)
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        count = db.query(func.count(MessageLog.id)).filter(
            MessageLog.created_at >= day_start,
            MessageLog.created_at < day_end
        ).scalar() or 0

        days.append({
            "date": day_start.strftime("%m-%d"),
            "count": count
        })

    return {"days": days}


@router.get("/skill-stats")
async def get_skill_stats(db: Session = Depends(get_db)):
    """获取技能使用统计"""
    stats = db.query(
        MessageLog.skill_used,
        func.count(MessageLog.id).label('count')
    ).filter(
        MessageLog.skill_used.isnot(None),
        MessageLog.skill_used != ""
    ).group_by(MessageLog.skill_used).all()

    return {
        "skills": [{"name": s[0], "count": s[1]} for s in stats]
    }


async def _get_knowledge_stats() -> dict:
    """获取知识库统计"""
    try:
        knowledge_dir = KNOWLEDGE_DIR
        if not os.path.exists(knowledge_dir):
            return {"exists": False}

        # 扫描知识库目录
        total_chunks = 0
        total_files = 0
        categories = {}

        for corp_dir in os.listdir(knowledge_dir):
            corp_path = os.path.join(knowledge_dir, corp_dir)
            if not os.path.isdir(corp_path) or corp_dir.startswith('.'):
                continue

            # 查找 chunks.jsonl 文件
            chunks_file = os.path.join(corp_path, "chunks.jsonl")
            if os.path.exists(chunks_file):
                try:
                    with open(chunks_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                total_chunks += 1
                                # 尝试解析类别
                                try:
                                    import json
                                    chunk = json.loads(line.strip())
                                    cat = chunk.get("category", "other")
                                    categories[cat] = categories.get(cat, 0) + 1
                                except (json.JSONDecodeError, KeyError) as e:
                                    logger.debug(f"解析 chunk 类别失败: {e}")
                except Exception as e:
                    logger.error(f"读取 chunks.jsonl 失败: {chunks_file}, error: {e}")

            # 统计文件数量
            files_dir = os.path.join(corp_path, "files")
            if os.path.exists(files_dir):
                for root, dirs, files in os.walk(files_dir):
                    total_files += len(files)

        return {
            "exists": True,
            "total_chunks": total_chunks,
            "total_files": total_files,
            "categories": categories
        }
    except Exception as e:
        return {"exists": False, "error": str(e)}
