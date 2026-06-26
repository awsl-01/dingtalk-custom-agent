"""
混合检索权重优化器

根据历史检索成功率，动态调整语义/关键词/rerank 的权重
"""
import logging
import time
import json
import math
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class SearchRecord:
    """检索记录"""
    query: str
    user_id: str
    timestamp: float
    method: str  # semantic/keyword/hybrid
    weights: dict  # 当前使用的权重
    results_count: int
    clicked_index: int = -1  # 用户点击的结果索引（-1表示未点击）
    feedback: str = ""  # positive/negative
    dwell_time: float = 0.0  # 停留时间


@dataclass
class WeightConfig:
    """权重配置"""
    semantic: float = 0.6
    keyword: float = 0.4
    # 可以扩展更多权重
    rerank: float = 0.0


class AdaptiveWeightOptimizer:
    """
    自适应权重优化器

    功能：
    1. 记录检索结果和用户反馈
    2. 根据历史数据优化权重
    3. 平滑更新，避免剧烈变化
    """

    def __init__(self, storage_dir: str = None):
        self._storage_dir = storage_dir
        self._records: List[SearchRecord] = []
        self._current_weights = WeightConfig()

        # 优化参数
        self._learning_rate = 0.01  # 学习率
        self._min_weight = 0.2  # 最小权重
        self._max_weight = 0.8  # 最大权重
        self._smooth_factor = 0.9  # 平滑因子

        # 统计数据
        self._method_stats = defaultdict(lambda: {"total": 0, "success": 0, "clicks": 0})

        # 加载历史数据
        if storage_dir:
            self._load_data()

    def _load_data(self):
        """加载历史数据"""
        import os
        data_file = os.path.join(self._storage_dir, "weight_optimizer.json")
        if os.path.exists(data_file):
            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 加载权重
                if "weights" in data:
                    self._current_weights = WeightConfig(**data["weights"])

                # 加载统计
                if "method_stats" in data:
                    for method, stats in data["method_stats"].items():
                        self._method_stats[method] = stats

                logger.info(f"加载权重优化器数据: weights={asdict(self._current_weights)}")
            except Exception as e:
                logger.error(f"加载权重优化器数据失败: {e}")

    def _save_data(self):
        """保存数据"""
        if not self._storage_dir:
            return

        import os
        os.makedirs(self._storage_dir, exist_ok=True)
        data_file = os.path.join(self._storage_dir, "weight_optimizer.json")

        try:
            data = {
                "weights": asdict(self._current_weights),
                "method_stats": dict(self._method_stats),
                "updated_at": time.time(),
            }
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存权重优化器数据失败: {e}")

    def get_current_weights(self) -> dict:
        """获取当前权重"""
        return asdict(self._current_weights)

    def record_search(self, query: str, user_id: str,
                     method: str, weights: dict,
                     results_count: int, clicked_index: int = -1,
                     feedback: str = "", dwell_time: float = 0.0):
        """
        记录检索结果和用户反馈

        参数:
            query: 查询词
            user_id: 用户ID
            method: 检索方法
            weights: 当前使用的权重
            results_count: 结果数量
            clicked_index: 用户点击的结果索引
            feedback: 用户反馈
            dwell_time: 停留时间
        """
        record = SearchRecord(
            query=query,
            user_id=user_id,
            timestamp=time.time(),
            method=method,
            weights=weights,
            results_count=results_count,
            clicked_index=clicked_index,
            feedback=feedback,
            dwell_time=dwell_time,
        )

        self._records.append(record)

        # 更新方法统计
        self._method_stats[method]["total"] += 1
        if clicked_index >= 0:
            self._method_stats[method]["clicks"] += 1
        if feedback == "positive":
            self._method_stats[method]["success"] += 1

        # 限制记录数量
        if len(self._records) > 10000:
            self._records = self._records[-5000:]

        # 定期优化权重
        if len(self._records) % 100 == 0:
            self.optimize_weights()

    def record_click(self, query: str, user_id: str,
                    clicked_index: int, dwell_time: float):
        """
        记录用户点击

        参数:
            query: 查询词
            user_id: 用户ID
            clicked_index: 点击的结果索引
            dwell_time: 停留时间
        """
        # 查找最近的检索记录
        for record in reversed(self._records):
            if record.query == query and record.user_id == user_id:
                record.clicked_index = clicked_index
                record.dwell_time = dwell_time

                # 根据停留时间判断反馈
                if dwell_time > 30:  # 停留超过30秒视为正面
                    record.feedback = "positive"
                elif dwell_time < 5:  # 停留少于5秒视为负面
                    record.feedback = "negative"

                break

    def optimize_weights(self):
        """
        根据历史数据优化权重

        算法：
        1. 统计不同权重下的检索成功率
        2. 使用梯度上升优化权重
        3. 平滑更新，避免剧烈变化
        """
        if len(self._records) < 50:
            logger.info("记录数量不足，跳过权重优化")
            return

        # 计算各方法的成功率
        method_scores = {}
        for method, stats in self._method_stats.items():
            if stats["total"] > 10:
                # 成功率 = (点击数 + 正面反馈) / 总数
                success_rate = (stats["clicks"] + stats["success"]) / stats["total"]
                method_scores[method] = success_rate

        if not method_scores:
            return

        # 计算新权重（基于成功率的加权）
        total_score = sum(method_scores.values())
        if total_score == 0:
            return

        new_weights = WeightConfig()
        for method, score in method_scores.items():
            normalized_score = score / total_score

            if method == "semantic":
                new_weights.semantic = normalized_score
            elif method == "keyword":
                new_weights.keyword = normalized_score

        # 平滑更新
        self._current_weights.semantic = (
            self._smooth_factor * self._current_weights.semantic +
            (1 - self._smooth_factor) * new_weights.semantic
        )
        self._current_weights.keyword = (
            self._smooth_factor * self._current_weights.keyword +
            (1 - self._smooth_factor) * new_weights.keyword
        )

        # 归一化确保总和为1
        total = self._current_weights.semantic + self._current_weights.keyword
        self._current_weights.semantic /= total
        self._current_weights.keyword /= total

        # 限制权重范围
        self._current_weights.semantic = max(self._min_weight,
                                              min(self._max_weight,
                                                  self._current_weights.semantic))
        self._current_weights.keyword = 1 - self._current_weights.semantic

        # 保存
        self._save_data()

        logger.info(f"权重优化完成: semantic={self._current_weights.semantic:.3f}, "
                   f"keyword={self._current_weights.keyword:.3f}")

    def get_optimization_report(self) -> dict:
        """获取优化报告"""
        return {
            "current_weights": asdict(self._current_weights),
            "total_records": len(self._records),
            "method_stats": dict(self._method_stats),
            "recent_records": [
                {
                    "query": r.query,
                    "method": r.method,
                    "clicked": r.clicked_index >= 0,
                    "feedback": r.feedback,
                }
                for r in self._records[-10:]
            ],
        }

    def reset_weights(self):
        """重置权重为默认值"""
        self._current_weights = WeightConfig()
        self._save_data()
        logger.info("权重已重置为默认值")

    def set_weights(self, semantic: float, keyword: float):
        """
        手动设置权重

        参数:
            semantic: 语义检索权重
            keyword: 关键词检索权重
        """
        total = semantic + keyword
        self._current_weights.semantic = semantic / total
        self._current_weights.keyword = keyword / total
        self._save_data()
        logger.info(f"手动设置权重: semantic={self._current_weights.semantic:.3f}, "
                   f"keyword={self._current_weights.keyword:.3f}")


# 全局优化器实例
_optimizer: Optional[AdaptiveWeightOptimizer] = None


def get_weight_optimizer(storage_dir: str = None) -> AdaptiveWeightOptimizer:
    """获取全局权重优化器实例"""
    global _optimizer
    if _optimizer is None:
        _optimizer = AdaptiveWeightOptimizer(storage_dir)
    return _optimizer
