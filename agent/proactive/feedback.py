"""
反馈追踪器

记录用户对检索结果的反馈（👍/👎/快速离开）
用于：
1. 低质量知识预警
2. 检索权重自适应
3. 知识质量报告
"""
import logging
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class FeedbackRecord:
    """反馈记录"""
    feedback_id: str
    chunk_id: str
    user_id: str
    query: str
    feedback_type: str  # positive/negative/quick_leave
    dwell_time: float = 0.0  # 停留时间（秒）
    timestamp: float = 0.0
    details: dict = field(default_factory=dict)


@dataclass
class ChunkFeedbackStats:
    """知识块反馈统计"""
    chunk_id: str
    total_feedbacks: int = 0
    positive: int = 0
    negative: int = 0
    quick_leave: int = 0
    avg_dwell_time: float = 0.0
    negative_rate: float = 0.0
    quality_score: float = 1.0  # 质量分数（0-1）


class FeedbackTracker:
    """
    反馈追踪器

    功能：
    1. 记录用户反馈
    2. 统计反馈数据
    3. 识别低质量知识
    4. 生成质量报告
    """

    def __init__(self, storage_dir: str = None):
        self._feedbacks: List[FeedbackRecord] = []
        self._storage_dir = storage_dir

        # 加载历史反馈
        if storage_dir:
            self._load_feedbacks()

    def _load_feedbacks(self):
        """加载历史反馈"""
        import os
        feedback_file = os.path.join(self._storage_dir, "feedbacks.jsonl")
        if os.path.exists(feedback_file):
            try:
                with open(feedback_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data = json.loads(line)
                            self._feedbacks.append(FeedbackRecord(**data))
                logger.info(f"加载了 {len(self._feedbacks)} 条反馈记录")
            except Exception as e:
                logger.error(f"加载反馈记录失败: {e}")

    def _save_feedback(self, feedback: FeedbackRecord):
        """保存反馈记录"""
        if not self._storage_dir:
            return

        import os
        os.makedirs(self._storage_dir, exist_ok=True)
        feedback_file = os.path.join(self._storage_dir, "feedbacks.jsonl")

        try:
            with open(feedback_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(feedback), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"保存反馈记录失败: {e}")

    def record_feedback(self, chunk_id: str, user_id: str,
                       query: str, feedback_type: str,
                       dwell_time: float = 0.0, details: dict = None):
        """
        记录反馈

        参数:
            chunk_id: 知识块ID
            user_id: 用户ID
            query: 查询词
            feedback_type: 反馈类型（positive/negative/quick_leave）
            dwell_time: 停留时间（秒）
            details: 额外详情
        """
        feedback = FeedbackRecord(
            feedback_id=f"fb_{int(time.time() * 1000)}_{len(self._feedbacks)}",
            chunk_id=chunk_id,
            user_id=user_id,
            query=query,
            feedback_type=feedback_type,
            dwell_time=dwell_time,
            timestamp=time.time(),
            details=details or {},
        )

        self._feedbacks.append(feedback)
        self._save_feedback(feedback)

        logger.debug(f"记录反馈: {chunk_id} -> {feedback_type}")

    def record_positive(self, chunk_id: str, user_id: str,
                       query: str, dwell_time: float = 0.0):
        """记录正面反馈"""
        self.record_feedback(chunk_id, user_id, query, "positive", dwell_time)

    def record_negative(self, chunk_id: str, user_id: str,
                       query: str, dwell_time: float = 0.0):
        """记录负面反馈"""
        self.record_feedback(chunk_id, user_id, query, "negative", dwell_time)

    def record_quick_leave(self, chunk_id: str, user_id: str,
                          query: str, dwell_time: float):
        """
        记录快速离开

        参数:
            chunk_id: 知识块ID
            user_id: 用户ID
            query: 查询词
            dwell_time: 停留时间（秒）
        """
        # 只有停留时间少于5秒才算快速离开
        if dwell_time < 5.0:
            self.record_feedback(chunk_id, user_id, query, "quick_leave", dwell_time)

    def get_chunk_stats(self, chunk_id: str) -> ChunkFeedbackStats:
        """
        获取知识块的反馈统计

        参数:
            chunk_id: 知识块ID

        返回:
            反馈统计
        """
        chunk_feedbacks = [
            f for f in self._feedbacks if f.chunk_id == chunk_id
        ]

        if not chunk_feedbacks:
            return ChunkFeedbackStats(chunk_id=chunk_id)

        positive = sum(1 for f in chunk_feedbacks if f.feedback_type == "positive")
        negative = sum(1 for f in chunk_feedbacks if f.feedback_type == "negative")
        quick_leave = sum(1 for f in chunk_feedbacks if f.feedback_type == "quick_leave")
        total = len(chunk_feedbacks)

        avg_dwell = sum(f.dwell_time for f in chunk_feedbacks) / total
        negative_rate = (negative + quick_leave) / total if total > 0 else 0

        # 质量分数：正面反馈越多，质量越高
        quality_score = positive / total if total > 0 else 0.5

        return ChunkFeedbackStats(
            chunk_id=chunk_id,
            total_feedbacks=total,
            positive=positive,
            negative=negative,
            quick_leave=quick_leave,
            avg_dwell_time=avg_dwell,
            negative_rate=negative_rate,
            quality_score=quality_score,
        )

    def get_low_quality_chunks(self, threshold: float = 0.3,
                                min_feedbacks: int = 3) -> List[dict]:
        """
        获取低质量知识块

        参数:
            threshold: 负反馈率阈值
            min_feedbacks: 最小反馈次数

        返回:
            低质量知识块列表
        """
        # 按 chunk_id 分组统计
        chunk_ids = set(f.chunk_id for f in self._feedbacks)

        low_quality = []
        for chunk_id in chunk_ids:
            stats = self.get_chunk_stats(chunk_id)

            # 满足条件：反馈次数 >= min_feedbacks 且负反馈率 > threshold
            if stats.total_feedbacks >= min_feedbacks and stats.negative_rate > threshold:
                low_quality.append({
                    "chunk_id": chunk_id,
                    "total_feedbacks": stats.total_feedbacks,
                    "negative_rate": stats.negative_rate,
                    "quality_score": stats.quality_score,
                    "positive": stats.positive,
                    "negative": stats.negative,
                    "quick_leave": stats.quick_leave,
                })

        # 按负反馈率排序
        low_quality.sort(key=lambda x: x["negative_rate"], reverse=True)

        return low_quality

    def get_query_feedback_stats(self, query: str = None,
                                  days: int = 30) -> dict:
        """
        获取查询反馈统计

        参数:
            query: 查询词过滤
            days: 统计天数

        返回:
            反馈统计
        """
        cutoff = time.time() - days * 24 * 3600
        recent_feedbacks = [
            f for f in self._feedbacks
            if f.timestamp >= cutoff
        ]

        if query:
            recent_feedbacks = [
                f for f in recent_feedbacks if f.query == query
            ]

        total = len(recent_feedbacks)
        positive = sum(1 for f in recent_feedbacks if f.feedback_type == "positive")
        negative = sum(1 for f in recent_feedbacks if f.feedback_type == "negative")
        quick_leave = sum(1 for f in recent_feedbacks if f.feedback_type == "quick_leave")

        return {
            "total": total,
            "positive": positive,
            "negative": negative,
            "quick_leave": quick_leave,
            "positive_rate": positive / total if total > 0 else 0,
            "negative_rate": (negative + quick_leave) / total if total > 0 else 0,
        }

    def get_user_feedback_stats(self, user_id: str,
                                 days: int = 30) -> dict:
        """获取用户反馈统计"""
        cutoff = time.time() - days * 24 * 3600
        user_feedbacks = [
            f for f in self._feedbacks
            if f.user_id == user_id and f.timestamp >= cutoff
        ]

        total = len(user_feedbacks)
        positive = sum(1 for f in user_feedbacks if f.feedback_type == "positive")
        negative = sum(1 for f in user_feedbacks if f.feedback_type == "negative")

        return {
            "user_id": user_id,
            "total": total,
            "positive": positive,
            "negative": negative,
        }

    def get_quality_report(self) -> dict:
        """
        生成质量报告

        返回:
            质量报告
        """
        total_feedbacks = len(self._feedbacks)

        # 按类型统计
        by_type = {}
        for f in self._feedbacks:
            by_type[f.feedback_type] = by_type.get(f.feedback_type, 0) + 1

        # 获取低质量知识块
        low_quality = self.get_low_quality_chunks()

        # 按查询词统计失败
        query_failures = {}
        for f in self._feedbacks:
            if f.feedback_type in ("negative", "quick_leave"):
                query_failures[f.query] = query_failures.get(f.query, 0) + 1

        # 排序失败查询
        top_failed_queries = sorted(
            query_failures.items(), key=lambda x: x[1], reverse=True
        )[:10]

        return {
            "total_feedbacks": total_feedbacks,
            "by_type": by_type,
            "low_quality_count": len(low_quality),
            "low_quality_chunks": low_quality[:20],
            "top_failed_queries": [
                {"query": q, "failures": c}
                for q, c in top_failed_queries
            ],
            "generated_at": datetime.now().isoformat(),
        }

    def get_feedbacks_for_chunk(self, chunk_id: str,
                                 limit: int = 50) -> List[dict]:
        """获取知识块的反馈记录"""
        chunk_feedbacks = [
            f for f in self._feedbacks if f.chunk_id == chunk_id
        ]
        chunk_feedbacks.sort(key=lambda x: x.timestamp, reverse=True)
        return [asdict(f) for f in chunk_feedbacks[:limit]]

    def get_recent_feedbacks(self, limit: int = 100,
                              feedback_type: str = None) -> List[dict]:
        """获取最近的反馈记录"""
        feedbacks = self._feedbacks

        if feedback_type:
            feedbacks = [f for f in feedbacks if f.feedback_type == feedback_type]

        feedbacks.sort(key=lambda x: x.timestamp, reverse=True)
        return [asdict(f) for f in feedbacks[:limit]]

    def clear_old_feedbacks(self, days: int = 90):
        """清理旧反馈记录"""
        cutoff = time.time() - days * 24 * 3600
        before_count = len(self._feedbacks)
        self._feedbacks = [f for f in self._feedbacks if f.timestamp >= cutoff]
        after_count = len(self._feedbacks)

        logger.info(f"清理了 {before_count - after_count} 条旧反馈记录")

        # 重新保存
        if self._storage_dir:
            import os
            feedback_file = os.path.join(self._storage_dir, "feedbacks.jsonl")
            try:
                with open(feedback_file, "w", encoding="utf-8") as f:
                    for feedback in self._feedbacks:
                        f.write(json.dumps(asdict(feedback), ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error(f"重新保存反馈记录失败: {e}")

        return before_count - after_count


# 全局反馈追踪器实例
_feedback_tracker: Optional[FeedbackTracker] = None


def get_feedback_tracker(storage_dir: str = None) -> FeedbackTracker:
    """获取全局反馈追踪器实例"""
    global _feedback_tracker
    if _feedback_tracker is None:
        _feedback_tracker = FeedbackTracker(storage_dir)
    return _feedback_tracker
