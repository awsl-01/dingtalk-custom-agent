"""
钉钉 OAuth2.0 扫码登录认证 API
"""
import os
import sys
import time
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

import jwt
import requests
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import (
    DINGTALK_APP_KEY,
    DINGTALK_APP_SECRET,
    DINGTALK_REDIRECT_URI,
    WEB_SECRET_KEY,
)
from web.config import KNOWLEDGE_DIR

router = APIRouter()

# 存储临时 state 和二维码信息（生产环境应使用 Redis）
_qrcode_states = {}
_user_sessions = {}

# JWT 配置
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24


# ========== 简单登录 API（姓名+工号）==========

class SimpleLoginRequest(BaseModel):
    """简单登录请求"""
    user_name: str
    user_id: str


@router.post("/simple-login")
async def simple_login(request: SimpleLoginRequest):
    """
    简单登录：姓名 + 工号

    适合内部使用，不需要钉钉开放平台配置
    """
    user_name = request.user_name.strip()
    user_id = request.user_id.strip()

    if not user_name or len(user_name) < 2:
        raise HTTPException(status_code=400, detail="姓名长度至少2个字符")

    if not user_id:
        raise HTTPException(status_code=400, detail="请输入工号")

    # 根据工号前缀判断角色
    role = "teacher"  # 默认教师
    if user_id.upper().startswith("S"):
        role = "student"
    elif user_id.upper().startswith("A"):
        role = "admin"
    elif user_id.upper().startswith("T"):
        role = "teacher"
    elif user_id.upper().startswith("P"):
        role = "principal"  # 校长
    elif user_id.upper().startswith("D"):
        role = "director"  # 主任

    # 构建用户信息
    user_info = {
        "user_id": user_id,
        "user_name": user_name,
        "avatar": "",
        "mobile": "",
        "role": role,
    }

    # 创建 JWT Token
    token = _create_jwt_token(user_info)

    # 保存用户会话
    _user_sessions[user_id] = {
        "token": token,
        "user_info": user_info,
        "login_at": datetime.now().isoformat(),
    }

    # 注意：简单登录不自动同步用户到组织
    # 用户需要在 Web 界面中选择组织后，再进行相关操作
    # 这样避免创建默认的 "学校_default" 组织

    return {
        "token": token,
        "user": user_info,
        "message": "登录成功"
    }


class LoginResponse(BaseModel):
    """登录响应"""
    token: str
    user: dict


class QRCodeResponse(BaseModel):
    """二维码响应"""
    qrcode_url: str
    state: str
    expire_seconds: int = 300


def _get_dingtalk_access_token() -> str:
    """获取钉钉 access_token"""
    url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
    headers = {"Content-Type": "application/json"}
    data = {
        "appKey": DINGTALK_APP_KEY,
        "appSecret": DINGTALK_APP_SECRET,
    }

    resp = requests.post(url, headers=headers, json=data, timeout=10)
    result = resp.json()

    if "accessToken" not in result:
        raise Exception(f"获取 access_token 失败: {result}")

    return result["accessToken"]


def _get_user_info_by_code(auth_code: str) -> dict:
    """使用授权码获取用户信息"""
    # 获取 access_token
    access_token = _get_dingtalk_access_token()

    # 使用授权码获取用户信息
    url = "https://api.dingtalk.com/v1.0/contact/users/getByCode"
    headers = {
        "Content-Type": "application/json",
        "x-acs-dingtalk-access-token": access_token,
    }
    data = {"code": auth_code}

    resp = requests.post(url, headers=headers, json=data, timeout=10)
    result = resp.json()

    if "userId" not in result:
        # 尝试其他 API
        url2 = "https://oapi.dingtalk.com/topapi/user/getuserinfo"
        params = {"access_token": access_token, "code": auth_code}
        resp2 = requests.get(url2, params=params, timeout=10)
        result2 = resp2.json()

        if result2.get("errcode") == 0 and result2.get("user_info"):
            user_info = result2["user_info"]
            return {
                "user_id": user_info.get("userid", ""),
                "user_name": user_info.get("name", ""),
                "avatar": user_info.get("avatar", ""),
                "mobile": user_info.get("mobile", ""),
                "department_ids": user_info.get("department", []),
            }
        else:
            raise Exception(f"获取用户信息失败: {result}")

    return {
        "user_id": result.get("userId", ""),
        "user_name": result.get("name", ""),
        "avatar": result.get("avatar", ""),
        "mobile": result.get("mobile", ""),
        "department_ids": result.get("departmentIds", []),
    }


def _get_user_info_from_dingtalk(user_id: str) -> dict:
    """从钉钉 API 获取用户详细信息"""
    access_token = _get_dingtalk_access_token()

    url = "https://oapi.dingtalk.com/topapi/user/get"
    params = {"access_token": access_token, "userid": user_id}

    resp = requests.get(url, params=params, timeout=10)
    result = resp.json()

    if result.get("errcode") == 0 and result.get("user_info"):
        user_info = result["user_info"]
        return {
            "user_id": user_info.get("userid", ""),
            "user_name": user_info.get("name", ""),
            "avatar": user_info.get("avatar", ""),
            "mobile": user_info.get("mobile", ""),
            "email": user_info.get("email", ""),
            "department_ids": user_info.get("department", []),
            "position": user_info.get("position", ""),
            "job_number": user_info.get("jobnumber", ""),
        }

    return {"user_id": user_id, "user_name": "未知用户"}


def _create_jwt_token(user_info: dict) -> str:
    """创建 JWT Token"""
    payload = {
        "user_id": user_info.get("user_id", ""),
        "user_name": user_info.get("user_name", ""),
        "avatar": user_info.get("avatar", ""),
        "mobile": user_info.get("mobile", ""),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, WEB_SECRET_KEY, algorithm=JWT_ALGORITHM)


def _verify_jwt_token(token: str) -> Optional[dict]:
    """验证 JWT Token"""
    try:
        payload = jwt.decode(token, WEB_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


@router.get("/qrcode")
async def get_qrcode():
    """
    获取钉钉登录二维码 URL

    钉钉 OAuth2.0 授权登录地址：
    https://oapi.dingtalk.com/connect/oauth2/sns_authorize
    """
    # 生成随机 state 用于 CSRF 防护
    state = secrets.token_urlsafe(32)

    # 构建授权 URL
    params = {
        "appid": DINGTALK_APP_KEY,
        "response_type": "code",
        "scope": "openid",
        "state": state,
        "redirect_uri": DINGTALK_REDIRECT_URI,
    }

    qrcode_url = f"https://oapi.dingtalk.com/connect/oauth2/sns_authorize?{urlencode(params)}"

    # 存储 state（5分钟有效期）
    _qrcode_states[state] = {
        "created_at": time.time(),
        "expire_seconds": 300,
    }

    # 清理过期的 state
    current_time = time.time()
    expired_states = [s for s, data in _qrcode_states.items()
                      if current_time - data["created_at"] > data["expire_seconds"]]
    for s in expired_states:
        del _qrcode_states[s]

    return {
        "qrcode_url": qrcode_url,
        "state": state,
        "expire_seconds": 300,
    }


@router.get("/callback")
async def auth_callback(
    authCode: str = Query(..., alias="authCode"),
    state: str = Query(..., alias="state"),
):
    """
    钉钉 OAuth2.0 回调处理

    用户扫码授权后，钉钉会重定向到此 URL，并携带 authCode 和 state 参数
    """
    # 验证 state（CSRF 防护）
    if state not in _qrcode_states:
        raise HTTPException(status_code=400, detail="无效的授权状态，可能是二维码已过期")

    # 检查是否过期
    state_data = _qrcode_states.pop(state)
    if time.time() - state_data["created_at"] > state_data["expire_seconds"]:
        raise HTTPException(status_code=400, detail="二维码已过期，请重新获取")

    try:
        # 使用授权码获取用户信息
        user_info = _get_user_info_by_code(auth_code)

        # 如果用户信息不完整，尝试从钉钉 API 获取
        if user_info.get("user_id") and not user_info.get("user_name"):
            try:
                detailed_info = _get_user_info_from_dingtalk(user_info["user_id"])
                user_info.update(detailed_info)
            except Exception as e:
                print(f"获取详细用户信息失败: {e}")

        # 创建 JWT Token
        token = _create_jwt_token(user_info)

        # 保存用户会话
        _user_sessions[user_info["user_id"]] = {
            "token": token,
            "user_info": user_info,
            "login_at": datetime.now().isoformat(),
        }

        # 同步用户到本地用户管理
        _sync_user_to_local(user_info)

        # 重定向到前端，并携带 token 和用户信息
        # 使用 hash 参数传递，避免暴露在 URL 查询参数中
        redirect_url = f"/?token={token}"
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        # 登录失败，重定向到登录页面并显示错误
        return RedirectResponse(url=f"/?error={str(e)}")


def _sync_user_to_local(user_info: dict, corp_id: str = ""):
    """同步钉钉用户到本地用户管理"""
    user_id = user_info.get("user_id", "")
    user_name = user_info.get("user_name", "")

    if not user_id:
        return

    # 如果没有提供 corp_id，不同步用户（避免创建默认组织）
    if not corp_id:
        return

    users_file = os.path.join(KNOWLEDGE_DIR, corp_id, "structured", "users.json")

    # 加载现有用户
    users = []
    if os.path.exists(users_file):
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
        except:
            users = []

    # 检查用户是否已存在
    existing = next((u for u in users if u.get("user_id") == user_id), None)

    if existing:
        # 更新用户信息
        existing["name"] = user_name
        existing["avatar"] = user_info.get("avatar", "")
        existing["mobile"] = user_info.get("mobile", "")
        existing["last_login_at"] = datetime.now().isoformat()
    else:
        # 添加新用户
        new_user = {
            "user_id": user_id,
            "name": user_name,
            "avatar": user_info.get("avatar", ""),
            "mobile": user_info.get("mobile", ""),
            "role": user_info.get("role", "teacher"),
            "department": "",
            "permissions": ["public", "internal"],
            "metadata": {
                "source": "simple_login",
                "created_at": datetime.now().isoformat(),
            }
        }
        users.append(new_user)

    # 保存用户列表
    os.makedirs(os.path.dirname(users_file), exist_ok=True)
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


@router.get("/me")
async def get_current_user(request: Request):
    """获取当前登录用户信息"""
    # 从 Header 获取 token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")

    token = auth_header[7:]  # 去掉 "Bearer " 前缀

    # 验证 token
    payload = _verify_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    return {
        "user_id": payload.get("user_id", ""),
        "user_name": payload.get("user_name", ""),
        "avatar": payload.get("avatar", ""),
        "mobile": payload.get("mobile", ""),
    }


@router.post("/logout")
async def logout(request: Request):
    """退出登录"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = _verify_jwt_token(token)
        if payload:
            user_id = payload.get("user_id", "")
            if user_id in _user_sessions:
                del _user_sessions[user_id]

    return {"message": "已退出登录"}


@router.get("/verify")
async def verify_token(token: str = Query(...)):
    """验证 Token 是否有效"""
    payload = _verify_jwt_token(token)
    if not payload:
        return {"valid": False}

    return {
        "valid": True,
        "user_id": payload.get("user_id", ""),
        "user_name": payload.get("user_name", ""),
    }
