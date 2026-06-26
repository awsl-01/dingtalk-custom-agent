"""
检索建议器

提供检索建议和纠错功能：
1. 自动补全：用户输入"下周三考数" → 自动补全"下周三数学考试安排"
2. 错词修正：用户输入"棵表" → 提示"您是否要搜索：课表"
3. 热门建议：根据历史查询提供热门搜索建议
"""
import logging
import re
from typing import List, Dict, Optional, Tuple
from collections import Counter
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SearchSuggestionItem:
    """搜索建议项"""
    text: str               # 建议文本
    source: str             # 来源：history/content/hot/correction
    score: float = 0.0      # 相关性分数
    highlight: str = ""     # 高亮部分
    correction: str = ""    # 纠正的原词（如果是纠错）


class SearchSuggestion:
    """
    检索建议器

    功能：
    1. 基于查询历史的建议
    2. 基于知识库内容的建议
    3. 基于热词的建议
    4. 错词纠正
    """

    def __init__(self, kb=None):
        self.kb = kb
        self._query_history: List[Dict] = []  # 查询历史
        self._hot_queries: Counter = Counter()  # 热词统计

        # 常见错词映射
        self._common_corrections = {
            "棵表": "课表",
            "克表": "课表",
            "课表": "课表",
            "考式": "考试",
            "考势": "考试",
            "考试": "考试",
            "做业": "作业",
            "昨业": "作业",
            "作业": "作业",
            "通址": "通知",
            "同志": "通知",
            "通知": "通知",
            "连习": "联系",
            "联习": "联系",
            "联系": "联系",
        }

    def set_knowledge_base(self, kb):
        """设置知识库实例"""
        self.kb = kb

    def record_query(self, query: str, user_id: str = "",
                     clicked: bool = False):
        """
        记录查询历史

        参数:
            query: 查询词
            user_id: 用户ID
            clicked: 是否点击了结果
        """
        self._query_history.append({
            "query": query,
            "user_id": user_id,
            "clicked": clicked,
            "timestamp": __import__('time').time(),
        })

        # 更新热词
        self._hot_queries[query] += 1

        # 限制历史记录数量
        if len(self._query_history) > 10000:
            self._query_history = self._query_history[-5000:]

    def suggest(self, partial_query: str, top_k: int = 5) -> List[SearchSuggestionItem]:
        """
        提供检索建议

        参数:
            partial_query: 部分查询词
            top_k: 返回建议数量

        返回:
            建议列表
        """
        if not partial_query or len(partial_query) < 2:
            return []

        suggestions = []
        seen_texts = set()

        # 1. 纠错建议
        corrections = self._get_corrections(partial_query)
        for correction in corrections:
            if correction.text not in seen_texts:
                suggestions.append(correction)
                seen_texts.add(correction.text)

        # 2. 基于查询历史的建议
        history_suggestions = self._suggest_from_history(partial_query)
        for suggestion in history_suggestions:
            if suggestion.text not in seen_texts:
                suggestions.append(suggestion)
                seen_texts.add(suggestion.text)

        # 3. 基于知识库内容的建议
        if self.kb:
            content_suggestions = self._suggest_from_content(partial_query)
            for suggestion in content_suggestions:
                if suggestion.text not in seen_texts:
                    suggestions.append(suggestion)
                    seen_texts.add(suggestion.text)

        # 4. 基于热词的建议
        hot_suggestions = self._suggest_from_hot_queries(partial_query)
        for suggestion in hot_suggestions:
            if suggestion.text not in seen_texts:
                suggestions.append(suggestion)
                seen_texts.add(suggestion.text)

        # 按分数排序并返回 Top-K
        suggestions.sort(key=lambda x: x.score, reverse=True)
        return suggestions[:top_k]

    def _get_corrections(self, query: str) -> List[SearchSuggestionItem]:
        """获取纠错建议"""
        corrections = []

        # 检查常见错词
        for wrong, correct in self._common_corrections.items():
            if wrong in query and wrong != correct:
                corrected_query = query.replace(wrong, correct)
                corrections.append(SearchSuggestionItem(
                    text=corrected_query,
                    source="correction",
                    score=0.9,
                    correction=wrong,
                ))

        return corrections

    def _suggest_from_history(self, partial: str) -> List[SearchSuggestionItem]:
        """从查询历史中建议"""
        suggestions = []
        partial_lower = partial.lower()

        # 统计匹配的查询
        matched_queries = Counter()
        for record in self._query_history:
            query = record["query"]
            if query.lower().startswith(partial_lower) and query != partial:
                matched_queries[query] += 1

        # 生成建议
        for query, count in matched_queries.most_common(5):
            # 计算分数：基于出现次数和是否被点击
            score = min(count / 10, 1.0) * 0.8

            suggestions.append(SearchSuggestionItem(
                text=query,
                source="history",
                score=score,
                highlight=query[len(partial):],
            ))

        return suggestions

    def _suggest_from_content(self, partial: str) -> List[SearchSuggestionItem]:
        """从知识库内容中建议"""
        if not self.kb:
            return []

        suggestions = []
        partial_lower = partial.lower()

        # 从知识库的关键词中提取建议
        keyword_suggestions = set()

        for chunk in self.kb._chunks[:1000]:  # 限制扫描范围
            # 从摘要中提取
            if chunk.summary:
                # 查找包含查询词的短语
                phrases = re.split(r'[，。、；]', chunk.summary)
                for phrase in phrases:
                    phrase = phrase.strip()
                    if len(phrase) >= 4 and partial_lower in phrase.lower():
                        keyword_suggestions.add(phrase)

            # 从关键词中提取
            for keyword in chunk.keywords:
                if partial_lower in keyword.lower():
                    keyword_suggestions.add(keyword)

        # 生成建议
        for text in list(keyword_suggestions)[:5]:
            suggestions.append(SearchSuggestionItem(
                text=text,
                source="content",
                score=0.6,
                highlight=text[len(partial):] if text.startswith(partial) else "",
            ))

        return suggestions

    def _suggest_from_hot_queries(self, partial: str) -> List[SearchSuggestionItem]:
        """从热词中建议"""
        suggestions = []
        partial_lower = partial.lower()

        # 获取匹配的热词
        hot_matches = []
        for query, count in self._hot_queries.items():
            if query.lower().startswith(partial_lower) and query != partial:
                hot_matches.append((query, count))

        # 按热度排序
        hot_matches.sort(key=lambda x: x[1], reverse=True)

        # 生成建议
        for query, count in hot_matches[:3]:
            score = min(count / 50, 1.0) * 0.7

            suggestions.append(SearchSuggestionItem(
                text=query,
                source="hot",
                score=score,
                highlight=query[len(partial):],
            ))

        return suggestions

    def correct(self, query: str) -> dict:
        """
        纠错建议

        参数:
            query: 原始查询

        返回:
            {
                "original": "下周三考数",
                "corrected": "下周三数学考试",
                "corrections": [
                    {"original": "考数", "corrected": "数学考试", "type": "auto"}
                ],
                "has_correction": True
            }
        """
        corrections = []
        corrected_query = query

        # 1. 检查常见错词
        for wrong, correct in self._common_corrections.items():
            if wrong in query:
                corrected_query = corrected_query.replace(wrong, correct)
                corrections.append({
                    "original": wrong,
                    "corrected": correct,
                    "type": "common",
                })

        # 2. 检查拼音相似词（简化版）
        # 实际应用中可以使用拼音库进行更准确的匹配

        has_correction = corrected_query != query

        return {
            "original": query,
            "corrected": corrected_query,
            "corrections": corrections,
            "has_correction": has_correction,
        }

    def get_hot_queries(self, top_k: int = 10) -> List[dict]:
        """获取热门查询"""
        return [
            {"query": query, "count": count}
            for query, count in self._hot_queries.most_common(top_k)
        ]

    def get_query_history(self, user_id: str = None,
                          limit: int = 100) -> List[dict]:
        """获取查询历史"""
        history = self._query_history

        if user_id:
            history = [r for r in history if r["user_id"] == user_id]

        history.sort(key=lambda x: x["timestamp"], reverse=True)
        return history[:limit]

    def get_stats(self) -> dict:
        """获取统计信息"""
        total_queries = len(self._query_history)
        unique_queries = len(self._hot_queries)
        clicked_queries = sum(1 for r in self._query_history if r["clicked"])

        return {
            "total_queries": total_queries,
            "unique_queries": unique_queries,
            "clicked_queries": clicked_queries,
            "click_rate": clicked_queries / total_queries if total_queries > 0 else 0,
            "top_hot_queries": self.get_hot_queries(10),
        }


# 全局建议器实例
_suggester: Optional[SearchSuggestion] = None


def get_search_suggester(kb=None) -> SearchSuggestion:
    """获取全局搜索建议器实例"""
    global _suggester
    if _suggester is None:
        _suggester = SearchSuggestion(kb)
    return _suggester
