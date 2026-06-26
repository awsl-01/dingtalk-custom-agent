"""
LLM 意图路由器 - 完全基于大模型理解用户意图
"""
import json
import logging
import hashlib
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from collections import OrderedDict

logger = logging.getLogger(__name__)


class IntentCache:
    """意图识别缓存 - LRU 缓存常见意图"""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self._cache: OrderedDict[str, tuple] = OrderedDict()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0

    def _make_key(self, text: str) -> str:
        """生成缓存键"""
        # 标准化文本：去除空格、标点，转小部
        normalized = text.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()

    def get(self, text: str) -> Optional['UserIntent']:
        """获取缓存"""
        key = self._make_key(text)

        if key in self._cache:
            intent, timestamp = self._cache[key]
            # 检查是否过期
            if time.time() - timestamp < self._ttl_seconds:
                # 移到末尾（最近使用）
                self._cache.move_to_end(key)
                self._hits += 1
                logger.debug(f"缓存命中: {text[:30]}...")
                return intent
            else:
                # 过期，删除
                del self._cache[key]

        self._misses += 1
        return None

    def set(self, text: str, intent: 'UserIntent'):
        """设置缓存"""
        key = self._make_key(text)

        # 如果已存在，更新
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            # 如果满了，删除最旧的
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)

        self._cache[key] = (intent, time.time())

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total * 100 if total > 0 else 0,
        }


@dataclass
class UserIntent:
    """用户意图"""
    type: str                    # 意图类型
    action: str                  # 具体操作
    params: Dict[str, Any]      # 参数
    raw_text: str               # 原始消息
    confidence: float = 0.9     # 置信度


class IntentRouter:
    """LLM 意图路由器"""

    # 意图类型定义
    INTENT_TYPES = {
        "inspection": {
            "name": "巡检管理",
            "actions": ["checkin", "checkout", "query", "stats", "add_point", "add_photo"],
            "description": "巡检打卡、查看记录、统计、管理巡检点位"
        },
        "ppt": {
            "name": "PPT生成",
            "actions": ["generate", "modify", "confirm", "cancel"],
            "description": "生成PPT、课件、演示文稿"
        },
        "search": {
            "name": "搜索查询",
            "actions": ["web", "resource", "news", "material", "exam"],
            "description": "搜索网络信息、教学资源、新闻、习题"
        },
        "asset": {
            "name": "资产管理",
            "actions": ["add", "query", "borrow", "return", "stats", "import"],
            "description": "录入、查询、借用、归还资产"
        },
        "schedule": {
            "name": "课表管理",
            "actions": ["query", "swap", "permanent_swap"],
            "description": "查询课表、调课"
        },
        "knowledge": {
            "name": "知识库",
            "actions": ["query", "stats", "export"],
            "description": "查询知识库、统计、导出"
        },
        "chat": {
            "name": "普通对话",
            "actions": ["chat"],
            "description": "闲聊、问答"
        }
    }

    def __init__(self):
        self._llm_client = None
        self._model = None
        self._cache = IntentCache(max_size=1000, ttl_seconds=300)
        self._monitor = None  # 延迟加载避免循环依赖

    def _get_monitor(self):
        """延迟加载监控器"""
        if self._monitor is None:
            try:
                from agent.intent_monitor import intent_monitor
                self._monitor = intent_monitor
            except ImportError:
                pass
        return self._monitor

    def _get_llm_client(self):
        """获取 LLM 客户端"""
        if self._llm_client is None:
            import config
            import openai
            self._llm_client = openai.OpenAI(
                api_key=config.OPENAI_API_KEY,
                base_url=config.OPENAI_BASE_URL,
            )
            self._model = config.OPENAI_MODEL
        return self._llm_client

    async def classify(self, text: str, context: Dict = None) -> UserIntent:
        """
        识别用户意图

        参数:
            text: 用户消息
            context: 上下文信息（可选，用于理解指代）
        """
        start_time = time.time()

        # 检查缓存（只缓存无上下文的简单查询）
        if not context or len(context) <= 2:
            cached = self._cache.get(text)
            if cached:
                logger.debug(f"缓存命中: {text[:30]}...")
                return cached

        try:
            client = self._get_llm_client()

            # 构建系统提示词
            system_prompt = self._build_system_prompt()

            # 构建用户消息
            user_message = self._build_user_message(text, context)

            # 调用 LLM
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0,
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            # 解析结果
            intent = UserIntent(
                type=result.get("intent", "chat"),
                action=result.get("action", "chat"),
                params=result.get("params", {}),
                raw_text=text,
                confidence=result.get("confidence", 0.9)
            )

            # 计算延迟
            latency_ms = (time.time() - start_time) * 1000

            # 记录监控
            monitor = self._get_monitor()
            if monitor:
                monitor.record(
                    text=text,
                    intent_type=intent.type,
                    intent_action=intent.action,
                    confidence=intent.confidence,
                    params=intent.params,
                    source="llm",
                    latency_ms=latency_ms,
                    success=True,
                )

            # 设置缓存
            if not context or len(context) <= 2:
                self._cache.set(text, intent)

            logger.info(f"LLM意图识别: {intent.type}/{intent.action}, 置信度: {intent.confidence:.2f}, 耗时: {latency_ms:.0f}ms")
            return intent

        except Exception as e:
            # 计算延迟
            latency_ms = (time.time() - start_time) * 1000

            # 记录监控
            monitor = self._get_monitor()
            if monitor:
                monitor.record(
                    text=text,
                    intent_type="unknown",
                    intent_action="unknown",
                    confidence=0,
                    params={},
                    source="llm",
                    latency_ms=latency_ms,
                    success=False,
                    error_msg=str(e),
                )

            logger.error(f"LLM意图识别失败: {e}", exc_info=True)
            # 降级到简单规则
            return self._fallback_classify(text)

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        intent_desc = "\n".join([
            f"- {k}: {v['name']} - {v['description']}"
            for k, v in self.INTENT_TYPES.items()
        ])

        return f"""你是一个智能意图识别助手。你的任务是理解用户的自然语言消息，识别其意图并提取参数。

## 可选意图类型

{intent_desc}

## 输出格式

请返回JSON格式，包含以下字段：

```json
{{
    "intent": "意图类型",
    "action": "具体操作",
    "confidence": 0.0-1.0,
    "params": {{
        "参数名": "参数值"
    }}
}}
```

## 参数说明

### 时间参数 (time)
- "today" - 今天
- "yesterday" - 昨天
- "this_week" - 这周
- "last_week" - 上周
- "this_month" - 这月
- "last_month" - 上月
- "recent" - 最近
- "2024-01-15" - 具体日期
- "3_days_ago" - 3天前
- "7_days_ago" - 7天前

### 操作参数 (action)
- "query" - 查询
- "add" - 新增
- "delete" - 删除
- "update" - 修改
- "stats" - 统计
- "export" - 导出

### 巡检专用参数
- "checkin" - 打卡
- "checkout" - 签退
- "point_name" - 巡检点位名称
- "photo_urls" - 照片列表
- "query_type" - 查询类型（重要！必须准确识别）
  - "记录" 或 "records" - 查询巡检记录（打卡记录）
  - "问题" 或 "issues" 或 "problems" - 查询巡检问题（发现的问题）
  - "统计" 或 "stats" - 查询统计数据
  - "照片" 或 "photos" - 查询巡检照片

### PPT专用参数
- "topic" - 主题
- "subject" - 学科
- "grade" - 年级
- "page_count" - 页数
- "difficulty" - 难度

### 资产专用参数
- "asset_name" - 资产名称
- "asset_type" - 资产类型
- "location" - 位置
- "quantity" - 数量

### 课表专用参数
- "class_name" - 班级
- "teacher_name" - 教师
- "day_of_week" - 星期几
- "period" - 节次
- "swap_type" - 调课类型（temporary/permanent）

## 规则

1. 理解自然语言，包括口语化表达、省略、指代
2. 准确提取所有可见的参数
3. 对于模糊表达，使用合理的默认值
4. 只返回JSON，不要其他内容"""

    def _build_user_message(self, text: str, context: Dict = None) -> str:
        """构建用户消息"""
        message = f"用户消息：{text}\n"

        if context:
            # 添加上下文信息
            if "sender_nick" in context:
                message += f"发送者：{context['sender_nick']}\n"
            if "previous_message" in context:
                message += f"上一条消息：{context['previous_message']}\n"
            if "current_time" in context:
                message += f"当前时间：{context['current_time']}\n"

        # 添加当前时间
        message += f"\n当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

        return message

    def _fallback_classify(self, text: str) -> UserIntent:
        """降级分类（简单规则）"""
        text_lower = text.lower()

        # 简单关键词匹配
        if any(kw in text_lower for kw in ["巡检", "打卡", "签到"]):
            intent = UserIntent("inspection", "query", {}, text, 0.6)
        elif any(kw in text_lower for kw in ["ppt", "课件", "幻灯片"]):
            intent = UserIntent("ppt", "generate", {}, text, 0.6)
        elif any(kw in text_lower for kw in ["资产", "设备"]):
            intent = UserIntent("asset", "query", {}, text, 0.6)
        elif any(kw in text_lower for kw in ["课表", "调课"]):
            intent = UserIntent("schedule", "query", {}, text, 0.6)
        elif any(kw in text_lower for kw in ["搜索", "查询", "查找"]):
            intent = UserIntent("search", "web", {}, text, 0.6)
        else:
            intent = UserIntent("chat", "chat", {}, text, 0.5)

        # 记录监控
        monitor = self._get_monitor()
        if monitor:
            monitor.record(
                text=text,
                intent_type=intent.type,
                intent_action=intent.action,
                confidence=intent.confidence,
                params=intent.params,
                source="fallback",
                latency_ms=0,
                success=True,
            )

        return intent

    def get_cache_stats(self) -> Dict:
        """获取缓存统计"""
        return self._cache.get_stats()

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()


# 全局实例
intent_router = IntentRouter()
