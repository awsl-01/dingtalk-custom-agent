"""
意图识别监控模块 - 记录和分析 LLM 意图识别的性能和准确性
"""
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


@dataclass
class IntentRecord:
    """意图识别记录"""
    timestamp: float
    text: str
    intent_type: str
    intent_action: str
    confidence: float
    params: Dict
    source: str  # llm / rule / fallback
    latency_ms: float
    success: bool
    error_msg: str = ""


class IntentMonitor:
    """意图识别监控器"""

    def __init__(self, max_records: int = 10000):
        self._records: List[IntentRecord] = []
        self._max_records = max_records
        self._lock = threading.Lock()

        # 统计数据
        self._stats = {
            "total_calls": 0,
            "llm_calls": 0,
            "rule_calls": 0,
            "fallback_calls": 0,
            "success_count": 0,
            "error_count": 0,
            "avg_latency_ms": 0,
            "intent_distribution": defaultdict(int),
            "hourly_calls": defaultdict(int),
        }

    def record(
        self,
        text: str,
        intent_type: str,
        intent_action: str,
        confidence: float,
        params: Dict,
        source: str,
        latency_ms: float,
        success: bool,
        error_msg: str = "",
    ):
        """记录一次意图识别"""
        record = IntentRecord(
            timestamp=time.time(),
            text=text[:200],  # 截断长文本
            intent_type=intent_type,
            intent_action=intent_action,
            confidence=confidence,
            params=params,
            source=source,
            latency_ms=latency_ms,
            success=success,
            error_msg=error_msg,
        )

        with self._lock:
            self._records.append(record)

            # 限制记录数量
            if len(self._records) > self._max_records:
                self._records = self._records[-self._max_records:]

            # 更新统计
            self._update_stats(record)

    def _update_stats(self, record: IntentRecord):
        """更新统计数据"""
        self._stats["total_calls"] += 1

        if record.source == "llm":
            self._stats["llm_calls"] += 1
        elif record.source == "rule":
            self._stats["rule_calls"] += 1
        else:
            self._stats["fallback_calls"] += 1

        if record.success:
            self._stats["success_count"] += 1
        else:
            self._stats["error_count"] += 1

        # 更新平均延迟
        total = self._stats["total_calls"]
        avg = self._stats["avg_latency_ms"]
        self._stats["avg_latency_ms"] = (avg * (total - 1) + record.latency_ms) / total

        # 意图分布
        self._stats["intent_distribution"][record.intent_type] += 1

        # 每小时调用统计
        hour_key = datetime.fromtimestamp(record.timestamp).strftime("%Y-%m-%d %H:00")
        self._stats["hourly_calls"][hour_key] += 1

    def get_stats(self) -> Dict:
        """获取统计数据"""
        with self._lock:
            return {
                "total_calls": self._stats["total_calls"],
                "llm_calls": self._stats["llm_calls"],
                "rule_calls": self._stats["rule_calls"],
                "fallback_calls": self._stats["fallback_calls"],
                "success_count": self._stats["success_count"],
                "error_count": self._stats["error_count"],
                "success_rate": (
                    self._stats["success_count"] / self._stats["total_calls"] * 100
                    if self._stats["total_calls"] > 0
                    else 0
                ),
                "avg_latency_ms": round(self._stats["avg_latency_ms"], 2),
                "intent_distribution": dict(self._stats["intent_distribution"]),
                "llm_ratio": (
                    self._stats["llm_calls"] / self._stats["total_calls"] * 100
                    if self._stats["total_calls"] > 0
                    else 0
                ),
            }

    def get_recent_records(self, limit: int = 100) -> List[Dict]:
        """获取最近的记录"""
        with self._lock:
            return [asdict(r) for r in self._records[-limit:]]

    def get_error_records(self, limit: int = 50) -> List[Dict]:
        """获取错误记录"""
        with self._lock:
            errors = [r for r in self._records if not r.success]
            return [asdict(r) for r in errors[-limit:]]

    def get_slow_records(self, threshold_ms: float = 1000, limit: int = 50) -> List[Dict]:
        """获取慢调用记录"""
        with self._lock:
            slow = [r for r in self._records if r.latency_ms > threshold_ms]
            return [asdict(r) for r in slow[-limit:]]

    def get_hourly_stats(self, hours: int = 24) -> Dict:
        """获取每小时统计"""
        with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(hours=hours)

            hourly = defaultdict(lambda: {"calls": 0, "success": 0, "errors": 0})
            for record in self._records:
                if record.timestamp >= cutoff.timestamp():
                    hour_key = datetime.fromtimestamp(record.timestamp).strftime("%H:00")
                    hourly[hour_key]["calls"] += 1
                    if record.success:
                        hourly[hour_key]["success"] += 1
                    else:
                        hourly[hour_key]["errors"] += 1

            return dict(hourly)

    def export_records(self, filepath: str, format: str = "json"):
        """导出记录"""
        with self._lock:
            if format == "json":
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump([asdict(r) for r in self._records], f, ensure_ascii=False, indent=2)
            elif format == "csv":
                import csv
                with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "timestamp", "text", "intent_type", "intent_action",
                        "confidence", "source", "latency_ms", "success", "error_msg"
                    ])
                    for r in self._records:
                        writer.writerow([
                            datetime.fromtimestamp(r.timestamp).isoformat(),
                            r.text, r.intent_type, r.intent_action,
                            r.confidence, r.source, r.latency_ms, r.success, r.error_msg
                        ])

    def clear(self):
        """清空记录"""
        with self._lock:
            self._records.clear()
            self._stats = {
                "total_calls": 0,
                "llm_calls": 0,
                "rule_calls": 0,
                "fallback_calls": 0,
                "success_count": 0,
                "error_count": 0,
                "avg_latency_ms": 0,
                "intent_distribution": defaultdict(int),
                "hourly_calls": defaultdict(int),
            }


# 全局监控实例
intent_monitor = IntentMonitor()
