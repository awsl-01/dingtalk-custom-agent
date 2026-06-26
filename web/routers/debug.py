"""
对话调试 API - 模拟机器人对话，查看处理流程
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import json
import os
import sys
import time
import uuid
import logging
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.config import KNOWLEDGE_DIR
from web.models import SessionLocal, DebugSession

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    corp_id: str = "default"
    user_id: str = "debug_user"
    user_name: str = "调试用户"
    simulate_full: bool = True  # 是否模拟完整流程


@router.post("/chat")
async def debug_chat(request: ChatRequest):
    """模拟对话，返回完整处理流程"""
    start_time = time.time()
    session_id = str(uuid.uuid4())[:16]

    steps = []
    result = {
        "session_id": session_id,
        "user_input": request.message,
        "bot_response": "",
        "steps": steps,
        "skill_matched": None,
        "skill_confidence": 0,
        "kb_results": [],
        "processing_time_ms": 0,
    }

    try:
        # Step 1: 消息接收
        steps.append({
            "step": "消息接收",
            "status": "success",
            "detail": f"收到消息: {request.message[:50]}..."
        })

        # Step 2: 消息过滤检查
        from agent.knowledge_base_v2 import should_skip_message
        should_skip = should_skip_message(request.message)
        steps.append({
            "step": "消息过滤",
            "status": "success",
            "detail": f"{'跳过存档' if should_skip else '将存入知识库'}",
            "data": {"should_skip": should_skip}
        })

        # Step 3: 技能匹配
        from agent.skills import skill_registry
        from agent.skills.loader import load_skills

        # 确保技能已加载
        try:
            load_skills()
        except Exception as e:
            logger.warning(f"加载技能失败: {e}")

        skill_match = skill_registry.match(request.message)
        if skill_match and skill_match.confidence >= 0.7:
            steps.append({
                "step": "技能匹配",
                "status": "success",
                "detail": f"匹配到技能: {skill_match.skill.name} (置信度: {skill_match.confidence:.2f})",
                "data": {
                    "skill_name": skill_match.skill.name,
                    "confidence": skill_match.confidence,
                    "extracted_info": skill_match.extracted_info
                }
            })
            result["skill_matched"] = skill_match.skill.name
            result["skill_confidence"] = skill_match.confidence
        else:
            steps.append({
                "step": "技能匹配",
                "status": "skip",
                "detail": "未匹配到高置信度技能" if not skill_match else f"置信度过低: {skill_match.confidence:.2f}"
            })

        # Step 4: 知识库检索
        from agent.knowledge_base_v2 import get_knowledge_base
        kb = get_knowledge_base(KNOWLEDGE_DIR, request.corp_id)

        kb_start = time.time()
        search_result = await kb.search(request.message, top_k=5)
        kb_time = int((time.time() - kb_start) * 1000)

        if isinstance(search_result, dict):
            kb_results = search_result.get("results", [])
        else:
            kb_results = search_result

        kb_data = []
        for r in kb_results[:3]:
            kb_data.append({
                "text": r.chunk.text[:200],
                "score": r.score,
                "match_type": r.match_type,
                "sender_nick": r.chunk.sender_nick,
                "category": r.chunk.category,
            })

        steps.append({
            "step": "知识库检索",
            "status": "success",
            "detail": f"检索到 {len(kb_results)} 条结果，耗时 {kb_time}ms",
            "data": {
                "results_count": len(kb_results),
                "top_results": kb_data,
                "query_time_ms": kb_time
            }
        })
        result["kb_results"] = kb_data

        # Step 5: 判断是否需要网络搜索
        need_search = False
        search_keywords = ["是什么", "怎么", "为什么", "哪些", "介绍", "解释"]
        for keyword in search_keywords:
            if keyword in request.message:
                need_search = True
                break

        steps.append({
            "step": "网络搜索判断",
            "status": "success",
            "detail": f"{'需要网络搜索' if need_search else '不需要网络搜索'}",
            "data": {"need_search": need_search}
        })

        # Step 6: 生成回复（简化版，不实际调用LLM）
        response_text = await _generate_debug_response(
            request.message,
            kb_data,
            skill_match,
            need_search
        )

        steps.append({
            "step": "生成回复",
            "status": "success",
            "detail": f"生成回复: {response_text[:100]}..."
        })

        result["bot_response"] = response_text

        # Step 7: 知识库存档判断
        if not should_skip:
            steps.append({
                "step": "知识库存档",
                "status": "success",
                "detail": "消息将存入知识库"
            })
        else:
            steps.append({
                "step": "知识库存档",
                "status": "skip",
                "detail": "消息被过滤，不存入知识库"
            })

        # 计算总耗时
        processing_time = int((time.time() - start_time) * 1000)
        result["processing_time_ms"] = processing_time

        # 保存调试会话
        _save_debug_session(result)

        return result

    except Exception as e:
        steps.append({
            "step": "错误",
            "status": "error",
            "detail": str(e)
        })
        result["bot_response"] = f"调试过程中出现错误: {str(e)}"
        return result


@router.get("/skills")
async def list_skills():
    """获取已注册技能列表"""
    from agent.skills import skill_registry
    from agent.skills.loader import load_skills

    # 确保技能已加载
    try:
        load_skills()
    except Exception as e:
        logger.warning(f"加载技能失败: {e}")

    skills = []
    for name, skill in skill_registry._skills.items():
        skills.append({
            "name": skill.name,
            "description": skill.description,
            "keywords": skill.keywords,
            "priority": skill.priority,
        })

    return {
        "skills": skills,
        "total": len(skills)
    }


@router.get("/config")
async def get_config():
    """获取当前配置（脱敏显示）"""
    import config

    def mask_key(key: str) -> str:
        """脱敏处理"""
        if not key or len(key) < 8:
            return "***"
        return key[:4] + "***" + key[-4:]

    return {
        "dingtalk": {
            "app_key": mask_key(config.DINGTALK_APP_KEY),
            "robot_code": config.DINGTALK_ROBOT_CODE,
        },
        "openai": {
            "base_url": config.OPENAI_BASE_URL,
            "model": config.OPENAI_MODEL,
            "api_key": mask_key(config.OPENAI_API_KEY),
        },
        "knowledge": {
            "dir": KNOWLEDGE_DIR,
        }
    }


async def _generate_debug_response(
    query: str,
    kb_results: list,
    skill_match,
    need_search: bool
) -> str:
    """生成调试响应（不实际调用LLM）"""
    parts = []

    if skill_match and skill_match.confidence >= 0.7:
        parts.append(f"【技能回复】匹配到技能「{skill_match.skill.name}」，将由该技能处理您的请求。")
    else:
        if kb_results:
            parts.append("【知识库回复】根据知识库检索结果：")
            for i, r in enumerate(kb_results[:2], 1):
                parts.append(f"{i}. {r['text'][:100]}...")
        else:
            parts.append("【通用回复】抱歉，知识库中没有找到相关信息。")

        if need_search:
            parts.append("\n（将进行网络搜索以获取更多信息）")

    return "\n".join(parts)


def _save_debug_session(result: dict):
    """保存调试会话到数据库"""
    try:
        db = SessionLocal()
        session = DebugSession(
            session_id=result["session_id"],
            user_input=result["user_input"],
            bot_response=result["bot_response"],
            processing_steps=json.dumps(result["steps"], ensure_ascii=False),
            skill_matched=result.get("skill_matched"),
            skill_confidence=result.get("skill_confidence", 0),
            kb_results=json.dumps(result.get("kb_results", []), ensure_ascii=False),
            processing_time_ms=result.get("processing_time_ms", 0),
            status="success"
        )
        db.add(session)
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"保存调试会话失败: {e}")
