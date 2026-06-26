"""
用户管理 API
支持多组织的用户权限管理
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from pydantic import BaseModel
import json
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from web.config import KNOWLEDGE_DIR

router = APIRouter()


class UserUpdate(BaseModel):
    """用户更新请求"""
    name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    permissions: Optional[List[str]] = None


class UserCreate(BaseModel):
    """用户创建请求"""
    user_id: str
    name: str
    role: str = "teacher"
    department: str = ""
    permissions: List[str] = ["public", "internal"]


# 角色配置
ROLES_CONFIG = {
    "admin": {"name": "管理员", "description": "拥有所有权限", "level": 1},
    "principal": {"name": "校长", "description": "学校最高管理者", "level": 2},
    "director": {"name": "主任", "description": "部门负责人", "level": 3},
    "teacher": {"name": "教师", "description": "普通教师", "level": 4},
    "student": {"name": "学生", "description": "学生用户", "level": 5},
}

# 权限配置
PERMISSIONS_CONFIG = {
    "public": {"name": "公开内容", "description": "所有用户可访问"},
    "internal": {"name": "内部内容", "description": "仅内部人员可访问"},
    "confidential": {"name": "机密内容", "description": "需要授权访问"},
    "admin": {"name": "管理权限", "description": "系统管理权限"},
}


@router.get("/list")
async def list_users(
    corp_id: str = Query(..., description="企业ID"),
    role: Optional[str] = Query(None, description="角色筛选")
):
    """获取用户列表"""
    users = _load_users(corp_id)

    # 角色筛选
    if role:
        users = [u for u in users if u.get("role") == role]

    # 添加角色和权限的显示名称
    for user in users:
        role_info = ROLES_CONFIG.get(user.get("role", ""), {})
        user["role_name"] = role_info.get("name", user.get("role", ""))
        user["role_level"] = role_info.get("level", 99)

        # 权限名称
        perm_names = []
        for perm in user.get("permissions", []):
            perm_info = PERMISSIONS_CONFIG.get(perm, {})
            perm_names.append(perm_info.get("name", perm))
        user["permission_names"] = perm_names

    # 按角色等级排序
    users.sort(key=lambda x: x.get("role_level", 99))

    return {
        "users": users,
        "total": len(users),
        "roles": ROLES_CONFIG,
        "permissions": PERMISSIONS_CONFIG,
    }


@router.get("/stats")
async def get_user_stats(corp_id: str = Query(..., description="企业ID")):
    """获取用户统计"""
    users = _load_users(corp_id)

    stats = {
        "total": len(users),
        "by_role": {},
        "by_permission": {},
    }

    for user in users:
        # 按角色统计
        role = user.get("role", "unknown")
        stats["by_role"][role] = stats["by_role"].get(role, 0) + 1

        # 按权限统计
        for perm in user.get("permissions", []):
            stats["by_permission"][perm] = stats["by_permission"].get(perm, 0) + 1

    return stats


@router.post("/")
async def create_user(corp_id: str = Query(..., description="企业ID"), user: UserCreate = None):
    """创建用户"""
    users = _load_users(corp_id)

    # 检查用户是否已存在
    for u in users:
        if u.get("user_id") == user.user_id:
            raise HTTPException(status_code=400, detail="用户已存在")

    # 创建新用户
    new_user = {
        "user_id": user.user_id,
        "name": user.name,
        "role": user.role,
        "department": user.department,
        "permissions": user.permissions,
        "metadata": {},
    }

    users.append(new_user)
    _save_users(corp_id, users)

    return {"message": "创建成功", "user": new_user}


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    corp_id: str = Query(..., description="企业ID"),
    update: UserUpdate = None
):
    """更新用户信息"""
    users = _load_users(corp_id)

    # 查找用户
    for i, user in enumerate(users):
        if user.get("user_id") == user_id:
            # 更新字段
            if update.name is not None:
                users[i]["name"] = update.name
            if update.role is not None:
                users[i]["role"] = update.role
            if update.department is not None:
                users[i]["department"] = update.department
            if update.permissions is not None:
                users[i]["permissions"] = update.permissions

            _save_users(corp_id, users)
            return {"message": "更新成功", "user": users[i]}

    raise HTTPException(status_code=404, detail="用户不存在")


@router.delete("/{user_id}")
async def delete_user(user_id: str, corp_id: str = Query(..., description="企业ID")):
    """删除用户"""
    users = _load_users(corp_id)

    # 查找并删除用户
    for i, user in enumerate(users):
        if user.get("user_id") == user_id:
            deleted_user = users.pop(i)
            _save_users(corp_id, users)
            return {"message": "删除成功", "user": deleted_user}

    raise HTTPException(status_code=404, detail="用户不存在")


@router.get("/roles")
async def get_roles():
    """获取角色配置"""
    return {"roles": ROLES_CONFIG}


@router.get("/permissions")
async def get_permissions():
    """获取权限配置"""
    return {"permissions": PERMISSIONS_CONFIG}


def _load_users(corp_id: str) -> list:
    """加载用户列表"""
    users_file = os.path.join(KNOWLEDGE_DIR, corp_id, "structured", "users.json")

    if not os.path.exists(users_file):
        return []

    try:
        with open(users_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"加载用户信息失败: {e}")
        return []


def _save_users(corp_id: str, users: list):
    """保存用户列表"""
    users_dir = os.path.join(KNOWLEDGE_DIR, corp_id, "structured")
    os.makedirs(users_dir, exist_ok=True)

    users_file = os.path.join(users_dir, "users.json")

    try:
        with open(users_file, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存用户信息失败: {e}")
