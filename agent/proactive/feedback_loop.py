"""
用户反馈循环

收集用户反馈，分析检索失败，生成改进建议
"""
import logging
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


@dataclass
class SearchFeedback:
    """检索反馈"""
    feedback_id: str
    query: str
    user_id: str
    timestamp: float
    results_count: int
    clicked_index: int = -1      # 点击的结果索引
    clicked_chunk_id: str = ""   # 点击的知识块ID
    feedback_type: str = ""      # positive/negative/neutral
    dwell_time: float = 0.0      # 停留时间
    refinements: list = field(default_factory=list)  # 后续查询（用户修改查询重新搜索）


@dataclass
class SearchFailure:
    """检索失败记录"""
    query: str
    user_id: str
    timestamp: float
    results_count: int
    clicked: bool = False
    reason: str = ""  # no_results/irrelevant/low_quality


@dataclass
class KnowledgeGap:
    """知识缺口"""
    topic: str                    # 主题
    related_queries: list         # 相关查询
    frequency: int = 0            # 出现频率
    suggestion: str = ""          # 补充建议


class FeedbackCollector:
    """
    反馈收集器

    功能：
    1. 收集用户检索反馈
    2. 记录检索失败
    3. 分析知识缺口
    4. 生成改进建议
    """

    def __init__(self, storage_dir: str = None):
        self._storage_dir = storage_dir
        self._feedbacks: List[SearchFeedback] = []
        self._failures: List[SearchFailure] = []

        # 加载历史数据
        if storage_dir:
            self._load_data()

    def _load_data(self):
        """加载历史数据"""
        import os

        # 加载反馈数据
        feedback_file = os.path.join(self._storage_dir, "search_feedbacks.jsonl")
        if os.path.exists(feedback_file):
            try:
                with open(feedback_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data = json.loads(line)
                            self._feedbacks.append(SearchFeedback(**data))
                logger.info(f"加载了 {len(self._feedbacks)} 条反馈记录")
            except Exception as e:
                logger.error(f"加载反馈数据失败: {e}")

        # 加载失败数据
        failure_file = os.path.join(self._storage_dir, "search_failures.jsonl")
        if os.path.exists(failure_file):
            try:
                with open(failure_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data = json.loads(line)
                            self._failures.append(SearchFailure(**data))
                logger.info(f"加载了 {len(self._failures)} 条失败记录")
            except Exception as e:
                logger.error(f"加载失败数据失败: {e}")

    def _save_feedback(self, feedback: SearchFeedback):
        """保存反馈数据"""
        if not self._storage_dir:
            return

        import os
        os.makedirs(self._storage_dir, exist_ok=True)
        feedback_file = os.path.join(self._storage_dir, "search_feedbacks.jsonl")

        try:
            with open(feedback_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(feedback), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"保存反馈数据失败: {e}")

    def _save_failure(self, failure: SearchFailure):
        """保存失败数据"""
        if not self._storage_dir:
            return

        import os
        os.makedirs(self._storage_dir, exist_ok=True)
        failure_file = os.path.join(self._storage_dir, "search_failures.jsonl")

        try:
            with open(failure_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(failure), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"保存失败数据失败: {e}")

    def record_search(self, query: str, user_id: str,
                     results_count: int, clicked_index: int = -1,
                     clicked_chunk_id: str = ""):
        """
        记录检索行为

        参数:
            query: 查询词
            user_id: 用户ID
            results_count: 结果数量
            clicked_index: 点击的结果索引
            clicked_chunk_id: 点击的知识块ID
        """
        feedback = SearchFeedback(
            feedback_id=f"fb_{int(time.time() * 1000)}_{len(self._feedbacks)}",
            query=query,
            user_id=user_id,
            timestamp=time.time(),
            results_count=results_count,
            clicked_index=clicked_index,
            clicked_chunk_id=clicked_chunk_id,
        )

        self._feedbacks.append(feedback)

        # 如果没有结果或没有点击，记录为失败
        if results_count == 0:
            self._record_failure(query, user_id, results_count, "no_results")
        elif clicked_index < 0:
            self._record_failure(query, user_id, results_count, "irrelevant")

    def record_click(self, query: str, user_id: str,
                    clicked_index: int, clicked_chunk_id: str,
                    dwell_time: float):
        """
        记录用户点击

        参数:
            query: 查询词
            user_id: 用户ID
            clicked_index: 点击的结果索引
            clicked_chunk_id: 点击的知识块ID
            dwell_time: 停留时间
        """
        # 查找最近的反馈记录
        for feedback in reversed(self._feedbacks):
            if feedback.query == query and feedback.user_id == user_id:
                feedback.clicked_index = clicked_index
                feedback.clicked_chunk_id = clicked_chunk_id
                feedback.dwell_time = dwell_time

                # 根据停留时间判断反馈类型
                if dwell_time > 30:
                    feedback.feedback_type = "positive"
                elif dwell_time < 5:
                    feedback.feedback_type = "negative"
                else:
                    feedback.feedback_type = "neutral"

                break

    def record_feedback(self, query: str, user_id: str,
                       feedback_type: str, chunk_id: str = ""):
        """
        记录显式反馈

        参数:
            query: 查询词
            user_id: 用户ID
            feedback_type: 反馈类型（positive/negative）
            chunk_id: 知识块ID
        """
        for feedback in reversed(self._feedbacks):
            if feedback.query == query and feedback.user_id == user_id:
                feedback.feedback_type = feedback_type
                break

    def record_refinement(self, original_query: str, new_query: str,
                         user_id: str):
        """
        记录查询优化（用户修改查询重新搜索）

        参数:
            original_query: 原始查询
            new_query: 新查询
            user_id: 用户ID
        """
        for feedback in reversed(self._feedbacks):
            if feedback.query == original_query and feedback.user_id == user_id:
                feedback.refinements.append(new_query)
                break

    def _record_failure(self, query: str, user_id: str,
                       results_count: int, reason: str):
        """记录检索失败"""
        failure = SearchFailure(
            query=query,
            user_id=user_id,
            timestamp=time.time(),
            results_count=results_count,
            reason=reason
        )
        self._failures.append(failure)
        self._save_failure(failure)

    def get_feedback_stats(self, days: int = 30) -> dict:
        """
        获取反馈统计

        参数:
            days: 统计天数

        返回:
            统计信息
        """
        cutoff = time.time() - days * 24 * 3600
        recent = [f for f in self._feedbacks if f.timestamp >= cutoff]

        total = len(recent)
        positive = sum(1 for f in recent if f.feedback_type == "positive")
        negative = sum(1 for f in recent if f.feedback_type == "negative")
        neutral = sum(1 for f in recent if f.feedback_type == "neutral")
        clicked = sum(1 for f in recent if f.clicked_index >= 0)

        return {
            "total": total,
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "clicked": clicked,
            "click_rate": clicked / total if total > 0 else 0,
            "positive_rate": positive / total if total > 0 else 0,
            "negative_rate": negative / total if total > 0 else 0,
        }

    def get_failure_stats(self, days: int = 30) -> dict:
        """
        获取失败统计

        参数:
            days: 统计天数

        返回:
            统计信息
        """
        cutoff = time.time() - days * 24 * 3600
        recent = [f for f in self._failures if f.timestamp >= cutoff]

        total = len(recent)
        by_reason = Counter(f.reason for f in recent)
        by_query = Counter(f.query for f in recent)

        return {
            "total": total,
            "by_reason": dict(by_reason),
            "top_failed_queries": by_query.most_common(20),
        }

    def analyze_knowledge_gaps(self, days: int = 30,
                                min_frequency: int = 3) -> List[KnowledgeGap]:
        """
        分析知识缺口

        参数:
            days: 分析天数
            min_frequency: 最小出现频率

        返回:
            知识缺口列表
        """
        cutoff = time.time() - days * 24 * 3600

        # 收集失败查询
        failed_queries = []
        for failure in self._failures:
            if failure.timestamp >= cutoff:
                failed_queries.append(failure.query)

        # 统计查询频率
        query_counter = Counter(failed_queries)

        # 聚类相似查询（简化实现）
        gaps = []
        processed = set()

        for query, count in query_counter.most_common():
            if count < min_frequency:
                break

            if query in processed:
                continue

            # 查找相似查询
            similar_queries = [query]
            for other_query, other_count in query_counter.items():
                if other_query != query and other_query not in processed:
                    # 简单相似度：包含相同关键词
                    if self._is_similar(query, other_query):
                        similar_queries.append(other_query)
                        processed.add(other_query)

            # 生成知识缺口
            gap = KnowledgeGap(
                topic=self._extract_topic(similar_queries),
                related_queries=similar_queries,
                frequency=count,
                suggestion=f"建议补充关于「{self._extract_topic(similar_queries)}」的知识"
            )
            gaps.append(gap)
            processed.add(query)

        return gaps

    def _is_similar(self, query1: str, query2: str) -> bool:
        """判断两个查询是否相似"""
        # 简化实现：检查是否有共同关键词
        words1 = set(query1)
        words2 = set(query2)
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union > 0.3 if union > 0 else False

    def _extract_topic(self, queries: List[str]) -> str:
        """从查询列表中提取主题"""
        # 简化实现：取最长的查询作为主题
        return max(queries, key=len) if queries else ""

    def get_improvement_suggestions(self) -> List[dict]:
        """
        生成改进建议

        返回:
            改进建议列表
        """
        suggestions = []

        # 1. 分析知识缺口
        gaps = self.analyze_knowledge_gaps()
        for gap in gaps[:10]:
            suggestions.append({
                "type": "knowledge_gap",
                "priority": "high",
                "topic": gap.topic,
                "frequency": gap.frequency,
                "suggestion": gap.suggestion,
                "related_queries": gap.related_queries[:5],
            })

        # 2. 分析低质量知识块
        negative_feedbacks = [
            f for f in self._feedbacks
            if f.feedback_type == "negative" and f.clicked_chunk_id
        ]
        chunk_negative_count = Counter(f.clicked_chunk_id for f in negative_feedbacks)

        for chunk_id, count in chunk_negative_count.most_common(10):
            if count >= 3:
                suggestions.append({
                    "type": "low_quality",
                    "priority": "medium",
                    "chunk_id": chunk_id,
                    "negative_count": count,
                    "suggestion": f"知识块 {chunk_id} 收到 {count} 次负面反馈，建议审核或更新",
                })

        # 3. 分析查询优化
        refinement_feedbacks = [
            f for f in self._feedbacks if f.refinements
        ]
        if refinement_feedbacks:
            suggestions.append({
                "type": "search_improvement",
                "priority": "low",
                "suggestion": f"有 {len(refinement_feedbacks)} 次查询被用户优化，考虑改进检索算法",
            })

        return suggestions

    def get_report(self, days: int = 30) -> dict:
        """
        生成完整报告

        参数:
            days: 统计天数

        返回:
            报告内容
        """
        return {
            "feedback_stats": self.get_feedback_stats(days),
            "failure_stats": self.get_failure_stats(days),
            "knowledge_gaps": [
                {
                    "topic": gap.topic,
                    "frequency": gap.frequency,
                    "related_queries": gap.related_queries[:5],
                }
                for gap in self.analyze_knowledge_gaps(days)
            ],
            "improvement_suggestions": self.get_improvement_suggestions(),
            "generated_at": datetime.now().isoformat(),
        }


# 全局反馈收集器实例
_feedback_collector: Optional[FeedbackCollector] = None


def get_feedback_collector(storage_dir: str = None) -> FeedbackCollector:
    """获取全局反馈收集器实例"""
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector(storage_dir)
    return _feedback_collector
