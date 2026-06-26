"""
检索结果解释器

返回每条结果时附带匹配原因，例如：
- "命中课表时间字段"
- "语义相似度 0.92"
- "关键词'考试'出现 3 次"
"""
import logging
import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SearchExplanation:
    """搜索解释"""
    # 分数明细
    semantic_score: float = 0.0      # 语义相似度分数
    keyword_score: float = 0.0       # 关键词匹配分数
    category_score: float = 0.0      # 类别匹配分数
    time_score: float = 0.0          # 时间相关性分数
    popularity_score: float = 0.0    # 热度分数

    # 匹配详情
    matched_keywords: list = field(default_factory=list)    # 匹配的关键词
    keyword_positions: dict = field(default_factory=dict)   # 关键词位置
    keyword_count: int = 0           # 关键词出现次数
    category_match: bool = False     # 类别是否匹配
    time_relevance: float = 0.0      # 时间相关性

    # 解释文本
    explanation_text: str = ""       # 解释文本
    match_highlights: list = field(default_factory=list)  # 匹配高亮

    def to_text(self) -> str:
        """生成可读的解释文本"""
        parts = []

        if self.semantic_score > 0.5:
            parts.append(f"语义相似度 {self.semantic_score:.2f}")

        if self.matched_keywords:
            if len(self.matched_keywords) <= 3:
                kw_str = "、".join(self.matched_keywords)
                parts.append(f"关键词「{kw_str}」匹配")
            else:
                kw_str = "、".join(self.matched_keywords[:3])
                parts.append(f"关键词「{kw_str}」等{len(self.matched_keywords)}个匹配")

        if self.keyword_count > 1:
            parts.append(f"关键词出现 {self.keyword_count} 次")

        if self.category_match:
            parts.append("类别匹配")

        if self.time_relevance > 0.5:
            parts.append("时间相关")

        if self.popularity_score > 0.5:
            parts.append("热门内容")

        return "，".join(parts) if parts else "综合匹配"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "scores": {
                "semantic": round(self.semantic_score, 3),
                "keyword": round(self.keyword_score, 3),
                "category": round(self.category_score, 3),
                "time": round(self.time_score, 3),
                "popularity": round(self.popularity_score, 3),
            },
            "matched_keywords": self.matched_keywords,
            "keyword_count": self.keyword_count,
            "category_match": self.category_match,
            "time_relevance": round(self.time_relevance, 3),
            "explanation_text": self.explanation_text,
            "match_highlights": self.match_highlights,
        }


class SearchExplainer:
    """
    搜索解释器

    功能：
    1. 分析查询和结果的匹配原因
    2. 计算各维度的匹配分数
    3. 生成可读的解释文本
    """

    def __init__(self):
        # 关键词权重
        self.keyword_weights = {
            "exact_match": 1.0,      # 完全匹配
            "prefix_match": 0.8,     # 前缀匹配
            "contains_match": 0.6,   # 包含匹配
        }

    def explain(self, query: str, result, category_filter: str = None) -> SearchExplanation:
        """
        生成搜索解释

        参数:
            query: 查询词
            result: 搜索结果（SearchResult 对象）
            category_filter: 类别过滤

        返回:
            搜索解释
        """
        chunk = result.chunk
        explanation = SearchExplanation()

        # 1. 语义相似度分数
        explanation.semantic_score = result.score

        # 2. 关键词匹配分析
        self._analyze_keyword_match(query, chunk.text, explanation)

        # 3. 类别匹配分析
        if category_filter and chunk.category:
            explanation.category_match = (chunk.category == category_filter)
            explanation.category_score = 1.0 if explanation.category_match else 0.0

        # 4. 时间相关性分析
        self._analyze_time_relevance(chunk, explanation)

        # 5. 热度分数
        if hasattr(chunk, 'access_count'):
            explanation.popularity_score = min(chunk.access_count / 100, 1.0)

        # 6. 生成解释文本
        explanation.explanation_text = explanation.to_text()

        # 7. 生成匹配高亮
        explanation.match_highlights = self._generate_highlights(
            query, chunk.text, explanation.matched_keywords
        )

        return explanation

    def _analyze_keyword_match(self, query: str, text: str,
                                explanation: SearchExplanation):
        """分析关键词匹配"""
        # 清洗查询词
        query_clean = re.sub(r'[^\w\s]', '', query.lower())
        query_keywords = query_clean.split()

        # 清洗文本
        text_lower = text.lower()

        matched_keywords = []
        keyword_positions = {}
        total_count = 0

        for keyword in query_keywords:
            if len(keyword) < 2:  # 忽略太短的词
                continue

            # 查找关键词在文本中的位置
            positions = []
            start = 0
            while True:
                pos = text_lower.find(keyword, start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + 1

            if positions:
                matched_keywords.append(keyword)
                keyword_positions[keyword] = positions
                total_count += len(positions)

        explanation.matched_keywords = matched_keywords
        explanation.keyword_positions = keyword_positions
        explanation.keyword_count = total_count

        # 计算关键词分数
        if matched_keywords:
            match_ratio = len(matched_keywords) / len(query_keywords) if query_keywords else 0
            density = min(total_count / 10, 1.0)  # 关键词密度
            explanation.keyword_score = (match_ratio * 0.7 + density * 0.3)

    def _analyze_time_relevance(self, chunk, explanation: SearchExplanation):
        """分析时间相关性"""
        import time

        if not chunk.timestamp:
            return

        now = time.time()
        age_days = (now - chunk.timestamp) / (24 * 3600)

        # 时间衰减函数：越新的内容，时间相关性越高
        # 使用指数衰减：score = exp(-age_days / 30)
        import math
        explanation.time_relevance = math.exp(-age_days / 30)
        explanation.time_score = explanation.time_relevance

    def _generate_highlights(self, query: str, text: str,
                              matched_keywords: list) -> list:
        """生成匹配高亮"""
        highlights = []

        # 提取包含关键词的句子或片段
        sentences = re.split(r'[。！？\n]', text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # 检查句子是否包含匹配的关键词
            for keyword in matched_keywords:
                if keyword in sentence.lower():
                    # 截取合适的长度
                    if len(sentence) > 100:
                        # 找到关键词位置，前后各取30个字符
                        pos = sentence.lower().find(keyword)
                        start = max(0, pos - 30)
                        end = min(len(sentence), pos + len(keyword) + 30)
                        highlight = "..." + sentence[start:end] + "..."
                    else:
                        highlight = sentence

                    highlights.append(highlight)
                    break  # 每个句子只取一次

        # 限制高亮数量
        return highlights[:3]

    def explain_batch(self, query: str, results: list,
                      category_filter: str = None) -> List[SearchExplanation]:
        """
        批量生成搜索解释

        参数:
            query: 查询词
            results: 搜索结果列表
            category_filter: 类别过滤

        返回:
            搜索解释列表
        """
        explanations = []
        for result in results:
            explanation = self.explain(query, result, category_filter)
            explanations.append(explanation)
        return explanations


# 全局解释器实例
_explainer: Optional[SearchExplainer] = None


def get_search_explainer() -> SearchExplainer:
    """获取全局搜索解释器实例"""
    global _explainer
    if _explainer is None:
        _explainer = SearchExplainer()
    return _explainer
