"""
A/B 测试管理器

对不同检索策略（如不同 embedding 模型、不同 rerank 算法）进行效果对比
"""
import os
import json
import time
import hashlib
import logging
import random
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ExperimentConfig:
    """实验配置"""
    experiment_id: str
    name: str
    description: str
    variants: List[Dict[str, Any]]  # 变体配置
    traffic_split: List[float]      # 流量分配（总和为1）
    created_at: str = ""
    status: str = "running"         # running/paused/completed
    metrics: List[str] = field(default_factory=lambda: ["click_rate", "dwell_time", "feedback_rate"])


@dataclass
class VariantMetric:
    """变体指标"""
    variant_name: str
    total_exposures: int = 0
    total_clicks: int = 0
    total_positive_feedback: int = 0
    total_negative_feedback: int = 0
    total_dwell_time: float = 0.0
    avg_dwell_time: float = 0.0
    click_rate: float = 0.0
    feedback_rate: float = 0.0


class ABTestManager:
    """
    A/B 测试管理器

    功能：
    1. 创建和管理实验
    2. 分配用户到变体
    3. 记录指标
    4. 分析实验结果
    """

    def __init__(self, storage_dir: str = None):
        """
        初始化 A/B 测试管理器

        参数:
            storage_dir: 存储目录
        """
        self._storage_dir = storage_dir
        self._experiments: Dict[str, ExperimentConfig] = {}
        self._assignments: Dict[str, Dict[str, str]] = {}  # {exp_id: {user_id: variant}}
        self._metrics: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))

        # 加载历史数据
        if storage_dir:
            self._load_data()

    def _load_data(self):
        """加载历史数据"""
        import os

        # 加载实验配置
        experiments_file = os.path.join(self._storage_dir, "ab_experiments.json")
        if os.path.exists(experiments_file):
            try:
                with open(experiments_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for exp_data in data:
                    exp = ExperimentConfig(**exp_data)
                    self._experiments[exp.experiment_id] = exp
                logger.info(f"加载了 {len(self._experiments)} 个实验")
            except Exception as e:
                logger.error(f"加载实验配置失败: {e}")

        # 加载用户分配
        assignments_file = os.path.join(self._storage_dir, "ab_assignments.json")
        if os.path.exists(assignments_file):
            try:
                with open(assignments_file, "r", encoding="utf-8") as f:
                    self._assignments = json.load(f)
            except Exception as e:
                logger.error(f"加载用户分配失败: {e}")

    def _save_data(self):
        """保存数据"""
        if not self._storage_dir:
            return

        import os
        os.makedirs(self._storage_dir, exist_ok=True)

        # 保存实验配置
        experiments_file = os.path.join(self._storage_dir, "ab_experiments.json")
        try:
            with open(experiments_file, "w", encoding="utf-8") as f:
                json.dump(
                    [asdict(exp) for exp in self._experiments.values()],
                    f, ensure_ascii=False, indent=2
                )
        except Exception as e:
            logger.error(f"保存实验配置失败: {e}")

        # 保存用户分配
        assignments_file = os.path.join(self._storage_dir, "ab_assignments.json")
        try:
            with open(assignments_file, "w", encoding="utf-8") as f:
                json.dump(self._assignments, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存用户分配失败: {e}")

    def create_experiment(self, name: str,
                         variants: List[Dict[str, Any]],
                         traffic_split: List[float] = None,
                         description: str = "") -> str:
        """
        创建实验

        参数:
            name: 实验名称
            variants: 变体配置列表
            traffic_split: 流量分配（默认均匀分配）
            description: 实验描述

        返回:
            实验ID
        """
        # 生成实验ID
        experiment_id = f"exp_{int(time.time())}_{hashlib.md5(name.encode()).hexdigest()[:6]}"

        # 默认均匀分配
        if traffic_split is None:
            traffic_split = [1.0 / len(variants)] * len(variants)

        # 验证参数
        if len(variants) != len(traffic_split):
            raise ValueError("变体数量必须与流量分配数量一致")

        if abs(sum(traffic_split) - 1.0) > 0.01:
            raise ValueError("流量分配总和必须为1")

        # 创建实验配置
        experiment = ExperimentConfig(
            experiment_id=experiment_id,
            name=name,
            description=description,
            variants=variants,
            traffic_split=traffic_split,
            created_at=datetime.now().isoformat()
        )

        self._experiments[experiment_id] = experiment
        self._assignments[experiment_id] = {}

        # 保存
        self._save_data()

        logger.info(f"创建实验: {name} ({experiment_id})")
        return experiment_id

    def get_variant(self, experiment_id: str,
                   user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户对应的变体

        参数:
            experiment_id: 实验ID
            user_id: 用户ID

        返回:
            变体配置
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return None

        if experiment.status != "running":
            return None

        # 检查是否已分配
        if experiment_id in self._assignments:
            if user_id in self._assignments[experiment_id]:
                variant_name = self._assignments[experiment_id][user_id]
                # 查找对应变体
                for variant in experiment.variants:
                    if variant.get("name") == variant_name:
                        return variant

        # 新用户，分配变体
        variant = self._assign_variant(experiment, user_id)
        return variant

    def _assign_variant(self, experiment: ExperimentConfig,
                       user_id: str) -> Dict[str, Any]:
        """分配变体"""
        # 使用用户ID的哈希值确保分配一致性
        hash_value = int(hashlib.md5(f"{experiment.experiment_id}:{user_id}".encode()).hexdigest(), 16)
        hash_ratio = (hash_value % 10000) / 10000.0

        # 根据流量分配选择变体
        cumulative = 0.0
        for i, split in enumerate(experiment.traffic_split):
            cumulative += split
            if hash_ratio < cumulative:
                variant = experiment.variants[i]
                variant_name = variant.get("name", f"variant_{i}")

                # 记录分配
                if experiment.experiment_id not in self._assignments:
                    self._assignments[experiment.experiment_id] = {}
                self._assignments[experiment.experiment_id][user_id] = variant_name

                return variant

        # 默认返回最后一个变体
        return experiment.variants[-1]

    def record_exposure(self, experiment_id: str,
                       user_id: str, variant_name: str):
        """
        记录曝光

        参数:
            experiment_id: 实验ID
            user_id: 用户ID
            variant_name: 变体名称
        """
        self._metrics[experiment_id][variant_name].append({
            "type": "exposure",
            "user_id": user_id,
            "timestamp": time.time()
        })

    def record_click(self, experiment_id: str,
                    user_id: str, variant_name: str,
                    dwell_time: float = 0.0):
        """
        记录点击

        参数:
            experiment_id: 实验ID
            user_id: 用户ID
            variant_name: 变体名称
            dwell_time: 停留时间
        """
        self._metrics[experiment_id][variant_name].append({
            "type": "click",
            "user_id": user_id,
            "dwell_time": dwell_time,
            "timestamp": time.time()
        })

    def record_feedback(self, experiment_id: str,
                       user_id: str, variant_name: str,
                       feedback_type: str):
        """
        记录反馈

        参数:
            experiment_id: 实验ID
            user_id: 用户ID
            variant_name: 变体名称
            feedback_type: 反馈类型（positive/negative）
        """
        self._metrics[experiment_id][variant_name].append({
            "type": "feedback",
            "user_id": user_id,
            "feedback_type": feedback_type,
            "timestamp": time.time()
        })

    def analyze_results(self, experiment_id: str) -> Dict[str, Any]:
        """
        分析实验结果

        参数:
            experiment_id: 实验ID

        返回:
            分析结果
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return {"error": "实验不存在"}

        results = {
            "experiment": {
                "id": experiment.experiment_id,
                "name": experiment.name,
                "status": experiment.status,
                "created_at": experiment.created_at,
            },
            "variants": {},
            "winner": None,
            "confidence": 0.0,
        }

        # 计算各变体指标
        variant_metrics = []
        for variant in experiment.variants:
            variant_name = variant.get("name", "unknown")
            metrics = self._metrics.get(experiment_id, {}).get(variant_name, [])

            # 计算指标
            total_exposures = sum(1 for m in metrics if m["type"] == "exposure")
            total_clicks = sum(1 for m in metrics if m["type"] == "click")
            total_positive = sum(1 for m in metrics if m["type"] == "feedback" and m.get("feedback_type") == "positive")
            total_negative = sum(1 for m in metrics if m["type"] == "feedback" and m.get("feedback_type") == "negative")
            total_dwell_time = sum(m.get("dwell_time", 0) for m in metrics if m["type"] == "click")

            click_rate = total_clicks / total_exposures if total_exposures > 0 else 0
            avg_dwell_time = total_dwell_time / total_clicks if total_clicks > 0 else 0
            feedback_rate = total_positive / (total_positive + total_negative) if (total_positive + total_negative) > 0 else 0

            variant_metric = VariantMetric(
                variant_name=variant_name,
                total_exposures=total_exposures,
                total_clicks=total_clicks,
                total_positive_feedback=total_positive,
                total_negative_feedback=total_negative,
                total_dwell_time=total_dwell_time,
                avg_dwell_time=avg_dwell_time,
                click_rate=click_rate,
                feedback_rate=feedback_rate,
            )

            results["variants"][variant_name] = asdict(variant_metric)
            variant_metrics.append(variant_metric)

        # 确定获胜者（基于点击率）
        if variant_metrics:
            winner = max(variant_metrics, key=lambda x: x.click_rate)
            results["winner"] = winner.variant_name
            results["confidence"] = self._calculate_confidence(variant_metrics)

        return results

    def _calculate_confidence(self, metrics: List[VariantMetric]) -> float:
        """计算统计置信度（简化实现）"""
        if len(metrics) < 2:
            return 0.0

        # 简化计算：基于样本量和差异
        rates = [m.click_rate for m in metrics if m.total_exposures > 0]
        if len(rates) < 2:
            return 0.0

        max_rate = max(rates)
        min_rate = min(rates)
        diff = max_rate - min_rate

        # 样本量因子
        total_samples = sum(m.total_exposures for m in metrics)
        sample_factor = min(total_samples / 1000, 1.0)

        # 简化的置信度计算
        confidence = diff * sample_factor * 100
        return min(confidence, 99.0)

    def get_experiment(self, experiment_id: str) -> Optional[Dict]:
        """获取实验配置"""
        experiment = self._experiments.get(experiment_id)
        if experiment:
            return asdict(experiment)
        return None

    def list_experiments(self, status: str = None) -> List[Dict]:
        """列出实验"""
        experiments = list(self._experiments.values())
        if status:
            experiments = [e for e in experiments if e.status == status]
        return [asdict(e) for e in experiments]

    def pause_experiment(self, experiment_id: str) -> bool:
        """暂停实验"""
        if experiment_id in self._experiments:
            self._experiments[experiment_id].status = "paused"
            self._save_data()
            return True
        return False

    def resume_experiment(self, experiment_id: str) -> bool:
        """恢复实验"""
        if experiment_id in self._experiments:
            self._experiments[experiment_id].status = "running"
            self._save_data()
            return True
        return False

    def complete_experiment(self, experiment_id: str) -> bool:
        """完成实验"""
        if experiment_id in self._experiments:
            self._experiments[experiment_id].status = "completed"
            self._save_data()
            return True
        return False

    def delete_experiment(self, experiment_id: str) -> bool:
        """删除实验"""
        if experiment_id in self._experiments:
            del self._experiments[experiment_id]
            if experiment_id in self._assignments:
                del self._assignments[experiment_id]
            if experiment_id in self._metrics:
                del self._metrics[experiment_id]
            self._save_data()
            return True
        return False


# 全局 A/B 测试管理器实例
_ab_manager: Optional[ABTestManager] = None


def get_ab_manager(storage_dir: str = None) -> ABTestManager:
    """获取全局 A/B 测试管理器实例"""
    global _ab_manager
    if _ab_manager is None:
        _ab_manager = ABTestManager(storage_dir)
    return _ab_manager
