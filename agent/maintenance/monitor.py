"""
SLA 监控器

监控检索延迟、索引更新延迟、向量库健康状态，并提供告警
"""
import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """健康状态"""
    status: str  # healthy/degraded/unhealthy
    search_p50: float = 0.0
    search_p95: float = 0.0
    search_p99: float = 0.0
    index_update_p99: float = 0.0
    error_rate: float = 0.0
    total_searches: int = 0
    total_errors: int = 0
    uptime_hours: float = 0.0
    issues: List[str] = field(default_factory=list)
    checked_at: str = ""


@dataclass
class AlertRule:
    """告警规则"""
    metric: str           # 指标名称
    threshold: float      # 阈值
    operator: str         # 比较运算符：gt/lt/eq
    severity: str         # 严重程度：warning/critical
    message: str          # 告警消息


class SLAMonitor:
    """
    SLA 监控器

    功能：
    1. 记录检索延迟
    2. 记录索引更新延迟
    3. 记录错误
    4. 健康检查
    5. 告警触发
    """

    def __init__(self, storage_dir: str = None):
        """
        初始化 SLA 监控器

        参数:
            storage_dir: 存储目录
        """
        self._storage_dir = storage_dir
        self._start_time = time.time()

        # 延迟记录（使用 deque 限制内存占用）
        self._search_latencies = deque(maxlen=10000)
        self._index_update_latencies = deque(maxlen=1000)
        self._errors = deque(maxlen=1000)

        # 告警规则
        self._alert_rules = [
            AlertRule(
                metric="search_p99",
                threshold=2.0,
                operator="gt",
                severity="warning",
                message="检索 P99 延迟超过 {threshold}s"
            ),
            AlertRule(
                metric="search_p99",
                threshold=5.0,
                operator="gt",
                severity="critical",
                message="检索 P99 延迟严重超标"
            ),
            AlertRule(
                metric="error_rate",
                threshold=0.05,
                operator="gt",
                severity="warning",
                message="错误率超过 {threshold}"
            ),
            AlertRule(
                metric="error_rate",
                threshold=0.10,
                operator="gt",
                severity="critical",
                message="错误率严重超标"
            ),
        ]

        # 告警历史
        self._alerts = deque(maxlen=1000)

        # 加载历史数据
        if storage_dir:
            self._load_data()

    def _load_data(self):
        """加载历史数据"""
        import os
        data_file = os.path.join(self._storage_dir, "sla_metrics.json")
        if os.path.exists(data_file):
            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # 恢复部分历史数据（最近24小时）
                cutoff = time.time() - 24 * 3600
                for record in data.get("search_latencies", []):
                    if record.get("timestamp", 0) > cutoff:
                        self._search_latencies.append(record)
                logger.info(f"加载了 {len(self._search_latencies)} 条延迟记录")
            except Exception as e:
                logger.error(f"加载 SLA 数据失败: {e}")

    def _save_data(self):
        """保存数据"""
        if not self._storage_dir:
            return

        import os
        os.makedirs(self._storage_dir, exist_ok=True)
        data_file = os.path.join(self._storage_dir, "sla_metrics.json")

        try:
            data = {
                "search_latencies": list(self._search_latencies)[-1000:],
                "index_update_latencies": list(self._index_update_latencies)[-100:],
                "errors": list(self._errors)[-100:],
                "saved_at": time.time()
            }
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"保存 SLA 数据失败: {e}")

    def record_search_latency(self, latency: float,
                             query: str = "",
                             results_count: int = 0):
        """
        记录检索延迟

        参数:
            latency: 延迟（秒）
            query: 查询词
            results_count: 结果数量
        """
        self._search_latencies.append({
            "latency": latency,
            "query": query,
            "results_count": results_count,
            "timestamp": time.time()
        })

        # 定期保存
        if len(self._search_latencies) % 100 == 0:
            self._save_data()

    def record_index_update_latency(self, latency: float,
                                    chunks_count: int = 0):
        """
        记录索引更新延迟

        参数:
            latency: 延迟（秒）
            chunks_count: 更新的分块数量
        """
        self._index_update_latencies.append({
            "latency": latency,
            "chunks_count": chunks_count,
            "timestamp": time.time()
        })

    def record_error(self, error_type: str, message: str,
                    details: dict = None):
        """
        记录错误

        参数:
            error_type: 错误类型
            message: 错误消息
            details: 额外详情
        """
        self._errors.append({
            "type": error_type,
            "message": message,
            "details": details,
            "timestamp": time.time()
        })

    def check_health(self) -> HealthStatus:
        """
        健康检查

        返回:
            健康状态
        """
        now = time.time()
        issues = []

        # 计算检索延迟
        recent_latencies = [
            r["latency"] for r in self._search_latencies
            if r["timestamp"] > now - 3600  # 最近1小时
        ]

        search_p50 = 0.0
        search_p95 = 0.0
        search_p99 = 0.0

        if recent_latencies:
            recent_latencies.sort()
            n = len(recent_latencies)
            search_p50 = recent_latencies[int(n * 0.5)]
            search_p95 = recent_latencies[int(n * 0.95)]
            search_p99 = recent_latencies[int(n * 0.99)]

        # 计算索引更新延迟
        recent_index_latencies = [
            r["latency"] for r in self._index_update_latencies
            if r["timestamp"] > now - 3600
        ]
        index_update_p99 = 0.0
        if recent_index_latencies:
            recent_index_latencies.sort()
            index_update_p99 = recent_index_latencies[int(len(recent_index_latencies) * 0.99)]

        # 计算错误率
        total_searches = len(recent_latencies)
        recent_errors = [
            e for e in self._errors
            if e["timestamp"] > now - 3600
        ]
        total_errors = len(recent_errors)
        error_rate = total_errors / total_searches if total_searches > 0 else 0.0

        # 检查告警规则
        for rule in self._alert_rules:
            value = 0.0
            if rule.metric == "search_p99":
                value = search_p99
            elif rule.metric == "error_rate":
                value = error_rate

            triggered = False
            if rule.operator == "gt" and value > rule.threshold:
                triggered = True
            elif rule.operator == "lt" and value < rule.threshold:
                triggered = True
            elif rule.operator == "eq" and abs(value - rule.threshold) < 0.001:
                triggered = True

            if triggered:
                issue = rule.message.format(threshold=rule.threshold)
                issues.append(issue)
                self._record_alert(rule.severity, issue)

        # 确定整体状态
        if any("critical" in str(a) for a in self._alerts[-10:]):
            status = "unhealthy"
        elif issues:
            status = "degraded"
        else:
            status = "healthy"

        # 计算运行时间
        uptime_hours = (now - self._start_time) / 3600

        return HealthStatus(
            status=status,
            search_p50=round(search_p50, 3),
            search_p95=round(search_p95, 3),
            search_p99=round(search_p99, 3),
            index_update_p99=round(index_update_p99, 3),
            error_rate=round(error_rate, 4),
            total_searches=total_searches,
            total_errors=total_errors,
            uptime_hours=round(uptime_hours, 2),
            issues=issues,
            checked_at=datetime.now().isoformat()
        )

    def _record_alert(self, severity: str, message: str):
        """记录告警"""
        self._alerts.append({
            "severity": severity,
            "message": message,
            "timestamp": time.time()
        })

    def get_alerts(self, limit: int = 50,
                  severity: str = None) -> List[Dict]:
        """
        获取告警历史

        参数:
            limit: 返回数量
            severity: 严重程度过滤

        返回:
            告警列表
        """
        alerts = list(self._alerts)
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]

        # 按时间倒序
        alerts.sort(key=lambda x: x["timestamp"], reverse=True)
        return alerts[:limit]

    def get_latency_stats(self, hours: int = 24) -> Dict:
        """
        获取延迟统计

        参数:
            hours: 统计小时数

        返回:
            延迟统计
        """
        cutoff = time.time() - hours * 3600
        latencies = [
            r["latency"] for r in self._search_latencies
            if r["timestamp"] > cutoff
        ]

        if not latencies:
            return {"count": 0}

        latencies.sort()
        n = len(latencies)

        return {
            "count": n,
            "min": round(min(latencies), 3),
            "max": round(max(latencies), 3),
            "avg": round(sum(latencies) / n, 3),
            "p50": round(latencies[int(n * 0.5)], 3),
            "p90": round(latencies[int(n * 0.9)], 3),
            "p95": round(latencies[int(n * 0.95)], 3),
            "p99": round(latencies[int(n * 0.99)], 3),
        }

    def get_error_stats(self, hours: int = 24) -> Dict:
        """
        获取错误统计

        参数:
            hours: 统计小时数

        返回:
            错误统计
        """
        cutoff = time.time() - hours * 3600
        errors = [
            e for e in self._errors
            if e["timestamp"] > cutoff
        ]

        # 按类型统计
        by_type = {}
        for error in errors:
            error_type = error["type"]
            by_type[error_type] = by_type.get(error_type, 0) + 1

        return {
            "total": len(errors),
            "by_type": by_type,
            "recent": errors[-10:] if errors else [],
        }

    def get_sla_report(self, hours: int = 24) -> Dict:
        """
        生成 SLA 报告

        参数:
            hours: 报告小时数

        返回:
            SLA 报告
        """
        health = self.check_health()
        latency_stats = self.get_latency_stats(hours)
        error_stats = self.get_error_stats(hours)

        # 计算 SLA 达成率
        # 假设 SLA 目标：P99 < 2s, 错误率 < 1%
        sla_target_p99 = 2.0
        sla_target_error_rate = 0.01

        p99_met = latency_stats.get("p99", 0) < sla_target_p99 if latency_stats.get("count", 0) > 0 else True
        error_met = error_stats.get("total", 0) / max(latency_stats.get("count", 1), 1) < sla_target_error_rate

        sla_compliance = p99_met and error_met

        return {
            "health": asdict(health),
            "latency": latency_stats,
            "errors": error_stats,
            "sla": {
                "compliant": sla_compliance,
                "targets": {
                    "p99_latency": sla_target_p99,
                    "error_rate": sla_target_error_rate,
                },
                "actual": {
                    "p99_latency": latency_stats.get("p99", 0),
                    "error_rate": error_stats.get("total", 0) / max(latency_stats.get("count", 1), 1),
                }
            },
            "generated_at": datetime.now().isoformat(),
        }

    def add_alert_rule(self, metric: str, threshold: float,
                      operator: str, severity: str, message: str):
        """
        添加告警规则

        参数:
            metric: 指标名称
            threshold: 阈值
            operator: 比较运算符
            severity: 严重程度
            message: 告警消息
        """
        rule = AlertRule(
            metric=metric,
            threshold=threshold,
            operator=operator,
            severity=severity,
            message=message
        )
        self._alert_rules.append(rule)

    def clear_old_data(self, days: int = 7):
        """清理旧数据"""
        cutoff = time.time() - days * 24 * 3600

        self._search_latencies = deque(
            [r for r in self._search_latencies if r["timestamp"] > cutoff],
            maxlen=10000
        )
        self._index_update_latencies = deque(
            [r for r in self._index_update_latencies if r["timestamp"] > cutoff],
            maxlen=1000
        )
        self._errors = deque(
            [e for e in self._errors if e["timestamp"] > cutoff],
            maxlen=1000
        )
        self._alerts = deque(
            [a for a in self._alerts if a["timestamp"] > cutoff],
            maxlen=1000
        )

        logger.info(f"清理了 {days} 天前的 SLA 数据")


# 全局 SLA 监控器实例
_sla_monitor: Optional[SLAMonitor] = None


def get_sla_monitor(storage_dir: str = None) -> SLAMonitor:
    """获取全局 SLA 监控器实例"""
    global _sla_monitor
    if _sla_monitor is None:
        _sla_monitor = SLAMonitor(storage_dir)
    return _sla_monitor
