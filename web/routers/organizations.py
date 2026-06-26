"""
组织管理 API
支持多组织隔离和切换
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from pydantic import BaseModel
import json
import os

from web.config import KNOWLEDGE_DIR

router = APIRouter()


class OrgNameUpdate(BaseModel):
    """组织名称更新请求"""
    name: str


@router.get("/list")
async def list_organizations():
    """获取所有组织列表"""
    organizations = []

    # 系统目录列表（排除这些目录）
    SYSTEM_DIRS = {"files", "index", "logs", "messages", "proactive", "snapshots", "structured", "scheduling"}

    if not os.path.exists(KNOWLEDGE_DIR):
        return {"organizations": [], "total": 0}

    for corp_dir in os.listdir(KNOWLEDGE_DIR):
        corp_path = os.path.join(KNOWLEDGE_DIR, corp_dir)

        # 只处理目录，跳过隐藏目录
        if not os.path.isdir(corp_path) or corp_dir.startswith('.'):
            continue

        # 跳过系统目录
        if corp_dir in SYSTEM_DIRS:
            continue

        # 获取组织信息（会检查是否有实际内容）
        org_info = _get_org_info(corp_dir, corp_path)
        if org_info["message_count"] > 0 or org_info["file_count"] > 0 or os.path.exists(os.path.join(corp_path, "meta.json")):
            organizations.append(org_info)

    # 按最后活跃时间排序
    organizations.sort(key=lambda x: x.get("last_active", "") or "", reverse=True)

    return {
        "organizations": organizations,
        "total": len(organizations)
    }


@router.get("/stats")
async def get_org_stats(corp_id: Optional[str] = None):
    """获取组织统计数据"""
    stats = {}

    if corp_id:
        stats[corp_id] = _calc_org_stats(corp_id)
    else:
        # 统计所有组织
        for corp_dir in os.listdir(KNOWLEDGE_DIR):
            corp_path = os.path.join(KNOWLEDGE_DIR, corp_dir)
            if not os.path.isdir(corp_path) or corp_dir.startswith('.'):
                continue
            if not any(c.isdigit() for c in corp_dir):
                continue
            stats[corp_dir] = _calc_org_stats(corp_dir)

    return {"stats": stats}


@router.put("/{corp_id}/name")
async def update_org_name(corp_id: str, update: OrgNameUpdate):
    """修改组织名称"""
    # 检查组织目录是否存在
    corp_path = os.path.join(KNOWLEDGE_DIR, corp_id)
    if not os.path.exists(corp_path):
        raise HTTPException(status_code=404, detail="组织不存在")

    # 读取或创建 meta.json
    meta_file = os.path.join(corp_path, "meta.json")
    meta = {}
    if os.path.exists(meta_file):
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = json.load(f)
        except:
            pass

    # 更新名称
    meta["name"] = update.name
    meta["corp_id"] = corp_id

    # 保存 meta.json
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return {"message": "修改成功", "corp_id": corp_id, "name": update.name}


def _get_org_info(corp_id: str, corp_path: str) -> dict:
    """获取单个组织信息"""
    info = {
        "corp_id": corp_id,
        "name": _get_org_name(corp_id),
        "message_count": 0,
        "file_count": 0,
        "total_size": 0,
        "last_active": None,
    }

    # 统计消息
    messages_dir = os.path.join(corp_path, "messages")
    if os.path.exists(messages_dir):
        for date_dir in os.listdir(messages_dir):
            date_path = os.path.join(messages_dir, date_dir)
            if not os.path.isdir(date_path):
                continue
            md_files = [f for f in os.listdir(date_path) if f.endswith('.md')]
            info["message_count"] += len(md_files)

            # 查找最新的消息
            for f in md_files:
                file_path = os.path.join(date_path, f)
                mtime = os.path.getmtime(file_path)
                from datetime import datetime
                mod_time = datetime.fromtimestamp(mtime).isoformat()
                if info["last_active"] is None or mod_time > info["last_active"]:
                    info["last_active"] = mod_time

    # 统计文件
    files_dir = os.path.join(corp_path, "files")
    if os.path.exists(files_dir):
        for date_dir in os.listdir(files_dir):
            date_path = os.path.join(files_dir, date_dir)
            if not os.path.isdir(date_path):
                continue
            for f in os.listdir(date_path):
                file_path = os.path.join(date_path, f)
                if os.path.isfile(file_path):
                    info["file_count"] += 1
                    info["total_size"] += os.path.getsize(file_path)

    info["total_size_display"] = _format_size(info["total_size"])

    return info


def _get_org_name(corp_id: str) -> str:
    """获取组织名称（从 meta.json 或配置中读取）"""
    # 尝试从 meta.json 读取
    meta_file = os.path.join(KNOWLEDGE_DIR, corp_id, "meta.json")
    if os.path.exists(meta_file):
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = json.load(f)
                return meta.get("name", meta.get("org_name", corp_id[:8]))
        except:
            pass

    # 尝试从 school_config 读取
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from agent.school_config import school_manager
        school_config = school_manager.get_school(corp_id)
        if school_config and school_config.name:
            return school_config.name
    except:
        pass

    # 返回 corp_id 前8位
    return corp_id[:8] + "..."


def _calc_org_stats(corp_id: str) -> dict:
    """计算单个组织的统计数据"""
    stats = {
        "message_count": 0,
        "file_count": 0,
        "total_size": 0,
        "dates": {},
        "file_types": {},
    }

    corp_path = os.path.join(KNOWLEDGE_DIR, corp_id)
    if not os.path.exists(corp_path):
        return stats

    # 统计消息
    messages_dir = os.path.join(corp_path, "messages")
    if os.path.exists(messages_dir):
        for date_dir in os.listdir(messages_dir):
            date_path = os.path.join(messages_dir, date_dir)
            if not os.path.isdir(date_path):
                continue
            md_files = [f for f in os.listdir(date_path) if f.endswith('.md')]
            stats["message_count"] += len(md_files)
            stats["dates"][date_dir] = len(md_files)

    # 统计文件
    files_dir = os.path.join(corp_path, "files")
    if os.path.exists(files_dir):
        for date_dir in os.listdir(files_dir):
            date_path = os.path.join(files_dir, date_dir)
            if not os.path.isdir(date_path):
                continue
            for f in os.listdir(date_path):
                file_path = os.path.join(date_path, f)
                if os.path.isfile(file_path):
                    stats["file_count"] += 1
                    size = os.path.getsize(file_path)
                    stats["total_size"] += size

                    ext = os.path.splitext(f)[1].lower()
                    file_type = _get_file_type(ext)
                    stats["file_types"][file_type] = stats["file_types"].get(file_type, 0) + 1

    stats["total_size_display"] = _format_size(stats["total_size"])

    return stats


def _get_file_type(ext: str) -> str:
    """根据扩展名判断文件类型"""
    type_map = {
        '.pdf': 'pdf',
        '.doc': 'word', '.docx': 'word',
        '.xls': 'excel', '.xlsx': 'excel',
        '.ppt': 'ppt', '.pptx': 'ppt',
        '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.gif': 'image',
        '.txt': 'text', '.md': 'text', '.csv': 'text',
    }
    return type_map.get(ext, 'other')


def _format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
