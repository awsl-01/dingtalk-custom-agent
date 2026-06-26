"""
意图识别 API - 提供意图识别的监控和管理接口
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/intent", tags=["intent"])


class ClassifyRequest(BaseModel):
    """分类请求"""
    text: str
    context: Optional[Dict] = None


class ClassifyResponse(BaseModel):
    """分类响应"""
    intent_type: str
    intent_action: str
    confidence: float
    params: Dict
    source: str
    latency_ms: float


@router.post("/classify", response_model=ClassifyResponse)
async def classify_intent(request: ClassifyRequest):
    """识别用户意图"""
    import time
    from agent.intent_router import intent_router

    start_time = time.time()

    try:
        intent = await intent_router.classify(request.text, request.context)
        latency_ms = (time.time() - start_time) * 1000

        return ClassifyResponse(
            intent_type=intent.type,
            intent_action=intent.action,
            confidence=intent.confidence,
            params=intent.params,
            source="llm",
            latency_ms=latency_ms,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """获取意图识别统计"""
    from agent.intent_monitor import intent_monitor
    from agent.intent_router import intent_router

    stats = intent_monitor.get_stats()
    cache_stats = intent_router.get_cache_stats()

    return {
        "intent_stats": stats,
        "cache_stats": cache_stats,
    }


@router.get("/recent")
async def get_recent_records(limit: int = 100):
    """获取最近的识别记录"""
    from agent.intent_monitor import intent_monitor

    return {
        "records": intent_monitor.get_recent_records(limit),
    }


@router.get("/errors")
async def get_error_records(limit: int = 50):
    """获取错误记录"""
    from agent.intent_monitor import intent_monitor

    return {
        "records": intent_monitor.get_error_records(limit),
    }


@router.get("/slow")
async def get_slow_records(threshold_ms: float = 1000, limit: int = 50):
    """获取慢调用记录"""
    from agent.intent_monitor import intent_monitor

    return {
        "records": intent_monitor.get_slow_records(threshold_ms, limit),
    }


@router.get("/hourly")
async def get_hourly_stats(hours: int = 24):
    """获取每小时统计"""
    from agent.intent_monitor import intent_monitor

    return {
        "hourly_stats": intent_monitor.get_hourly_stats(hours),
    }


@router.post("/clear-cache")
async def clear_cache():
    """清空缓存"""
    from agent.intent_router import intent_router

    intent_router.clear_cache()
    return {"message": "缓存已清空"}


@router.post("/clear-records")
async def clear_records():
    """清空监控记录"""
    from agent.intent_monitor import intent_monitor

    intent_monitor.clear()
    return {"message": "监控记录已清空"}


@router.get("/export")
async def export_records(format: str = "json"):
    """导出监控记录"""
    from agent.intent_monitor import intent_monitor
    import tempfile
    import os

    # 创建临时文件
    suffix = ".json" if format == "json" else ".csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        filepath = f.name

    try:
        intent_monitor.export_records(filepath, format)

        # 读取文件内容
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 删除临时文件
        os.unlink(filepath)

        return {
            "format": format,
            "content": content,
            "size": len(content),
        }
    except Exception as e:
        # 清理临时文件
        if os.path.exists(filepath):
            os.unlink(filepath)
        raise HTTPException(status_code=500, detail=str(e))
