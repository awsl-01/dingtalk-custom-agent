"""
查询意图理解模块

功能：
1. 识别用户查询意图（想了解什么类型的信息）
2. 提取查询中的实体（人名、班级、时间等）
3. 根据意图动态调整检索策略
"""
import logging
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class QueryIntent:
    """查询意图"""
    # 意图类型
    type: str  # person_info/schedule/exam/contact/teaching/notice/other

    # 提取的实体
    entities: Dict[str, str] = field(default_factory=dict)
    # 例如：{"person": "张教授", "class": "计算机2301", "time": "周一"}

    # 用户想了解的信息类型
    info_type: str = ""  # 课程/联系方式/个人信息/考试安排/...

    # 置信度
    confidence: float = 0.5

    # 原始查询
    original_query: str = ""

    # 建议的检索关键词
    suggested_keywords: List[str] = field(default_factory=list)

    # 建议的检索类别
    suggested_categories: List[str] = field(default_factory=list)


class IntentRecognizer:
    """
    意图识别器

    功能：
    1. 分析用户查询，识别意图类型
    2. 提取查询中的实体信息
    3. 生成检索建议
    """

    def __init__(self):
        # 意图类型关键词映射
        self._intent_keywords = {
            "person_info": ["是谁", "是谁啊", "介绍", "简介", "资料", "信息", "联系方式", "电话", "邮箱", "办公室"],
            "schedule": ["课表", "课程", "上课", "上课时间", "课", "调课", "换课", "教室"],
            "exam": ["考试", "测验", "成绩", "分数", "期中", "期末", "月考"],
            "contact": ["联系方式", "电话", "手机", "邮箱", "微信", "QQ", "地址"],
            "homework": ["作业", "练习", "习题", "试卷"],
            "notice": ["通知", "公告", "放假", "活动", "安排"],
            "teaching": ["教案", "课件", "PPT", "教学", "备课"],
        }

        # 实体提取模式
        self._entity_patterns = {
            "person": [
                r'([一-龥]{2,4})(教授|老师|医生|主任|院长|同学|学生)',
                r'(张|王|李|刘|陈|杨|黄|赵|周|吴)(教授|老师|医生|主任|院长)',
            ],
            "class": [
                r'([一-龥]+\d{4})班?',  # 计算机2301班
                r'([一-龥]+\d+年级\d+班)',  # 三年级2班
                r'([一-龥]+班)',  # 计算机班
            ],
            "time": [
                r'(周[一二三四五六日天])',
                r'(上午|下午|晚上)',
                r'(第[一二三四五六七八九十]+节)',
                r'(\d{1,2}月\d{1,2}[日号])',
                r'(明天|后天|下周|这周)',
            ],
            "subject": [
                r'(语文|数学|英语|物理|化学|生物|历史|地理|政治|音乐|美术|体育|科学|信息技术)',
            ],
        }

    async def recognize(self, query: str) -> QueryIntent:
        """
        识别查询意图

        参数:
            query: 用户查询

        返回:
            QueryIntent 对象
        """
        # 第一步：基于规则的快速识别
        intent = self._rule_based_recognize(query)

        # 第二步：使用 LLM 增强识别（可选）
        try:
            llm_intent = await self._llm_based_recognize(query)
            if llm_intent and llm_intent.confidence > intent.confidence:
                return llm_intent
        except Exception as e:
            logger.debug(f"LLM 意图识别失败，使用规则识别: {e}")

        return intent

    def _rule_based_recognize(self, query: str) -> QueryIntent:
        """
        基于规则的意图识别（快速，无需 API 调用）

        参数:
            query: 用户查询

        返回:
            QueryIntent 对象
        """
        query_lower = query.lower()
        intent = QueryIntent(type="other", original_query=query)

        # 识别意图类型
        scores = {}
        for intent_type, keywords in self._intent_keywords.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                scores[intent_type] = score

        if scores:
            intent.type = max(scores, key=scores.get)
            intent.confidence = min(0.7, scores[intent.type] * 0.2 + 0.3)
        else:
            intent.type = "other"
            intent.confidence = 0.3

        # 提取实体
        intent.entities = self._extract_entities(query)

        # 生成检索建议
        intent.suggested_keywords = self._generate_keywords(query, intent)
        intent.suggested_categories = self._generate_categories(intent)

        return intent

    async def _llm_based_recognize(self, query: str) -> Optional[QueryIntent]:
        """
        基于 LLM 的意图识别（准确，需要 API 调用）

        参数:
            query: 用户查询

        返回:
            QueryIntent 对象，失败返回 None
        """
        try:
            from agent.llm_utils import call_llm_json

            system_prompt = """你是一个查询意图识别助手，负责分析用户查询，识别其意图和提取关键信息。

意图类型：
- person_info: 想了解某人的信息（如"张教授是谁"、"介绍一下李老师"）
- schedule: 想了解课程安排（如"课表"、"周一有什么课"）
- exam: 想了解考试信息（如"考试安排"、"成绩查询"）
- contact: 想了解联系方式（如"电话"、"邮箱"、"地址"）
- homework: 想了解作业信息（如"作业布置"、"练习题"）
- notice: 想了解通知公告（如"放假通知"、"活动安排"）
- teaching: 想了解教学资料（如"教案"、"课件"）
- other: 其他意图

请返回 JSON 格式：
{
    "type": "意图类型",
    "entities": {"person": "人名", "class": "班级", "time": "时间", "subject": "学科"},
    "info_type": "想了解的信息类型",
    "confidence": 0.0-1.0,
    "suggested_keywords": ["建议的检索关键词"],
    "suggested_categories": ["建议的检索类别"]
}"""

            prompt = f"""请分析以下查询的意图：

查询：{query}

请返回 JSON 格式的分析结果。"""

            result = await call_llm_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=300,
            )

            if result and "type" in result:
                return QueryIntent(
                    type=result.get("type", "other"),
                    entities=result.get("entities", {}),
                    info_type=result.get("info_type", ""),
                    confidence=result.get("confidence", 0.5),
                    original_query=query,
                    suggested_keywords=result.get("suggested_keywords", []),
                    suggested_categories=result.get("suggested_categories", []),
                )

        except Exception as e:
            logger.debug(f"LLM 意图识别失败: {e}")

        return None

    def _extract_entities(self, query: str) -> Dict[str, str]:
        """
        提取查询中的实体

        参数:
            query: 用户查询

        返回:
            实体字典
        """
        entities = {}

        for entity_type, patterns in self._entity_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, query)
                if match:
                    entities[entity_type] = match.group(1) if match.lastindex else match.group()
                    break

        return entities

    def _generate_keywords(self, query: str, intent: QueryIntent) -> List[str]:
        """
        生成检索关键词

        参数:
            query: 用户查询
            intent: 查询意图

        返回:
            关键词列表
        """
        keywords = []

        # 添加实体作为关键词
        for entity_type, entity_value in intent.entities.items():
            keywords.append(entity_value)

        # 根据意图类型添加相关关键词
        if intent.type == "person_info":
            # 人物信息查询，添加人物相关关键词
            if "person" in intent.entities:
                person = intent.entities["person"]
                keywords.extend([person, "教授", "老师", "联系方式", "个人信息"])
        elif intent.type == "schedule":
            # 课表查询，添加课表相关关键词
            keywords.extend(["课表", "课程", "上课"])
            if "time" in intent.entities:
                keywords.append(intent.entities["time"])
        elif intent.type == "exam":
            # 考试查询，添加考试相关关键词
            keywords.extend(["考试", "测验", "成绩"])
        elif intent.type == "contact":
            # 联系方式查询，添加联系方式相关关键词
            keywords.extend(["联系方式", "电话", "邮箱", "地址"])

        # 去重
        keywords = list(set(keywords))

        return keywords

    def _generate_categories(self, intent: QueryIntent) -> List[str]:
        """
        生成检索类别

        参数:
            intent: 查询意图

        返回:
            类别列表
        """
        category_map = {
            "person_info": ["contact", "student"],
            "schedule": ["schedule"],
            "exam": ["exam"],
            "contact": ["contact"],
            "homework": ["homework"],
            "notice": ["notice"],
            "teaching": ["teaching"],
            "other": [],
        }

        return category_map.get(intent.type, [])


# 全局意图识别器实例
_intent_recognizer: Optional[IntentRecognizer] = None


def get_intent_recognizer() -> IntentRecognizer:
    """获取全局意图识别器实例"""
    global _intent_recognizer
    if _intent_recognizer is None:
        _intent_recognizer = IntentRecognizer()
    return _intent_recognizer


async def recognize_intent(query: str) -> QueryIntent:
    """
    便捷函数：识别查询意图

    参数:
        query: 用户查询

    返回:
        QueryIntent 对象
    """
    recognizer = get_intent_recognizer()
    return await recognizer.recognize(query)
