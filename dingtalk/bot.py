import os
import time
import base64
import logging
import httpx
import config

logger = logging.getLogger(__name__)

# 钉钉 access token 缓存
_token_cache = {"token": "", "expire_time": 0}


async def get_access_token() -> str:
    """获取钉钉开放平台 access_token（自动缓存）"""
    now = time.time()
    if _token_cache["token"] and _token_cache["expire_time"] > now:
        return _token_cache["token"]

    url = "https://oapi.dingtalk.com/gettoken"
    params = {
        "appkey": config.DINGTALK_APP_KEY,
        "appsecret": config.DINGTALK_APP_SECRET,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()

    if data.get("errcode") != 0:
        raise RuntimeError(f"获取 access_token 失败: {data}")

    token = data["access_token"]
    _token_cache["token"] = token
    _token_cache["expire_time"] = now + data.get("expires_in", 7200) - 300
    return token


async def upload_media(file_path: str, media_type: str = "file") -> str:
    """
    上传文件到钉钉，获取 mediaId

    参数:
        file_path: 文件路径
        media_type: 媒体类型（image/video/file）

    返回:
        mediaId
    """
    token = await get_access_token()
    url = f"https://oapi.dingtalk.com/media/upload?access_token={token}&type={media_type}"

    file_name = os.path.basename(file_path)
    async with httpx.AsyncClient() as client:
        with open(file_path, 'rb') as f:
            files = {'media': (file_name, f, 'application/octet-stream')}
            resp = await client.post(url, files=files)
            data = resp.json()

    if data.get("errcode") != 0:
        logger.error(f"上传文件失败: {data}")
        raise RuntimeError(f"上传文件失败: {data}")

    return data.get("media_id", "")


async def reply_text(conversation_id: str, sender_id: str, text: str):
    """通过钉钉消息接口回复文本消息"""
    token = await get_access_token()
    url = f"https://api.dingtalk.com/v1.0/robot/oToMessages/batchSend"

    headers = {"x-acs-dingtalk-access-token": token}
    body = {
        "robotCode": config.DINGTALK_ROBOT_CODE,
        "userIds": [sender_id],
        "msgKey": "sampleText",
        "msgParam": f'{{"content":"{text}"}}',
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=body, headers=headers)
        return resp.json()


async def reply_file(conversation_id: str, sender_id: str, file_path: str, file_name: str = ""):
    """
    通过钉钉消息接口回复文件消息

    参数:
        conversation_id: 会话ID
        sender_id: 发送者ID
        file_path: 文件路径
        file_name: 文件名（可选）
    """
    if not file_name:
        file_name = os.path.basename(file_path)

    # 上传文件获取 mediaId
    try:
        media_id = await upload_media(file_path, "file")
    except Exception as e:
        logger.error(f"上传文件失败: {e}")
        # 回退到文本消息
        await reply_text(conversation_id, sender_id, f"文件上传失败：{str(e)}")
        return

    token = await get_access_token()
    url = f"https://api.dingtalk.com/v1.0/robot/oToMessages/batchSend"

    headers = {"x-acs-dingtalk-access-token": token}
    body = {
        "robotCode": config.DINGTALK_ROBOT_CODE,
        "userIds": [sender_id],
        "msgKey": "sampleFile",
        "msgParam": f'{{"mediaId":"{media_id}","fileName":"{file_name}"}}',
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=body, headers=headers)
        return resp.json()


async def reply_file_in_group(conversation_id: str, sender_id: str, file_path: str, file_name: str = ""):
    """
    在群聊中回复文件消息

    参数:
        conversation_id: 会话ID
        sender_id: 发送者ID
        file_path: 文件路径
        file_name: 文件名（可选）
    """
    if not file_name:
        file_name = os.path.basename(file_path)

    # 上传文件获取 mediaId
    try:
        media_id = await upload_media(file_path, "file")
    except Exception as e:
        logger.error(f"上传文件失败: {e}")
        await reply_in_group(conversation_id, sender_id, f"文件上传失败：{str(e)}")
        return

    token = await get_access_token()
    url = f"https://api.dingtalk.com/v1.0/robot/groupMessages/send"

    headers = {"x-acs-dingtalk-access-token": token}
    body = {
        "robotCode": config.DINGTALK_ROBOT_CODE,
        "openConversationId": conversation_id,
        "msgKey": "sampleFile",
        "msgParam": f'{{"mediaId":"{media_id}","fileName":"{file_name}"}}',
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=body, headers=headers)
        return resp.json()


async def reply_to_conversation(conversation_id: str, sender_id: str, text: str):
    """回复消息（群聊或单聊自适应）"""
    if conversation_id:
        return await reply_in_group(conversation_id, sender_id, text)
    return await reply_text(conversation_id, sender_id, text)


async def reply_file_to_conversation(conversation_id: str, sender_id: str, file_path: str, file_name: str = ""):
    """回复文件消息（群聊或单聊自适应）"""
    if conversation_id:
        return await reply_file_in_group(conversation_id, sender_id, file_path, file_name)
    return await reply_file(conversation_id, sender_id, file_path, file_name)


async def reply_in_group(conversation_id: str, sender_id: str, text: str):
    """在群聊中回复消息"""
    token = await get_access_token()
    url = f"https://api.dingtalk.com/v1.0/robot/groupMessages/send"

    headers = {"x-acs-dingtalk-access-token": token}
    body = {
        "robotCode": config.DINGTALK_ROBOT_CODE,
        "openConversationId": conversation_id,
        "msgKey": "sampleText",
        "msgParam": f'{{"content":"{text}"}}',
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=body, headers=headers)
        return resp.json()
