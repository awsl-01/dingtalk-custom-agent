"""
知识快照管理器

支持按时间点回滚整个知识库（误删除或批量更新出错时非常有用）
"""
import os
import json
import shutil
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class SnapshotInfo:
    """快照信息"""
    snapshot_id: str
    description: str
    created_at: str
    chunks_count: int
    size_mb: float
    tags: list = field(default_factory=list)


class KnowledgeSnapshot:
    """
    知识快照管理器

    功能：
    1. 创建知识库快照
    2. 列出所有快照
    3. 恢复到指定快照
    4. 删除快照
    5. 比较快照差异
    """

    def __init__(self, kb, snapshot_dir: str = None):
        """
        初始化快照管理器

        参数:
            kb: 知识库实例
            snapshot_dir: 快照存储目录
        """
        self.kb = kb
        self._snapshot_dir = snapshot_dir or os.path.join(kb._school_dir, "snapshots")
        os.makedirs(self._snapshot_dir, exist_ok=True)

        # 快照元数据文件
        self._meta_file = os.path.join(self._snapshot_dir, "snapshots_meta.json")

    def _load_meta(self) -> List[dict]:
        """加载快照元数据"""
        if os.path.exists(self._meta_file):
            try:
                with open(self._meta_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载快照元数据失败: {e}")
        return []

    def _save_meta(self, meta: List[dict]):
        """保存快照元数据"""
        try:
            with open(self._meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存快照元数据失败: {e}")

    def create_snapshot(self, description: str = "",
                       tags: list = None) -> str:
        """
        创建快照

        参数:
            description: 快照描述
            tags: 标签列表

        返回:
            快照ID
        """
        snapshot_id = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        snapshot_path = os.path.join(self._snapshot_dir, snapshot_id)

        try:
            # 创建快照目录
            os.makedirs(snapshot_path, exist_ok=True)

            # 备份索引文件
            index_src = self.kb._index_dir
            index_dst = os.path.join(snapshot_path, "index")
            if os.path.exists(index_src):
                shutil.copytree(index_src, index_dst)

            # 备份结构化数据
            structured_src = self.kb._structured_dir
            structured_dst = os.path.join(snapshot_path, "structured")
            if os.path.exists(structured_src):
                shutil.copytree(structured_src, structured_dst)

            # 备份消息归档
            messages_src = self.kb._messages_dir
            messages_dst = os.path.join(snapshot_path, "messages")
            if os.path.exists(messages_src):
                shutil.copytree(messages_src, messages_dst)

            # 计算快照大小
            size_mb = self._get_dir_size(snapshot_path) / (1024 * 1024)

            # 保存快照信息
            info = SnapshotInfo(
                snapshot_id=snapshot_id,
                description=description or f"快照 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                created_at=datetime.now().isoformat(),
                chunks_count=len(self.kb._chunks),
                size_mb=round(size_mb, 2),
                tags=tags or [],
            )

            # 保存快照信息到快照目录
            info_file = os.path.join(snapshot_path, "snapshot_info.json")
            with open(info_file, "w", encoding="utf-8") as f:
                json.dump(asdict(info), f, ensure_ascii=False, indent=2)

            # 更新元数据
            meta = self._load_meta()
            meta.append(asdict(info))
            self._save_meta(meta)

            logger.info(f"创建快照成功: {snapshot_id}, 大小: {size_mb:.2f}MB, 分块数: {len(self.kb._chunks)}")

            # 记录操作日志
            self.kb._op_logger.log(
                timestamp=datetime.now().isoformat(),
                operation="create_snapshot",
                result_count=len(self.kb._chunks),
                status="success",
                details=f"快照ID={snapshot_id}, {description}"
            )

            return snapshot_id

        except Exception as e:
            logger.error(f"创建快照失败: {e}")
            # 清理失败的快照
            if os.path.exists(snapshot_path):
                shutil.rmtree(snapshot_path)
            raise

    def list_snapshots(self) -> List[SnapshotInfo]:
        """列出所有快照"""
        meta = self._load_meta()
        return [SnapshotInfo(**m) for m in meta]

    def get_snapshot_info(self, snapshot_id: str) -> Optional[SnapshotInfo]:
        """获取快照信息"""
        meta = self._load_meta()
        for m in meta:
            if m["snapshot_id"] == snapshot_id:
                return SnapshotInfo(**m)
        return None

    def restore_snapshot(self, snapshot_id: str,
                        dry_run: bool = True) -> dict:
        """
        恢复快照

        参数:
            snapshot_id: 快照ID
            dry_run: 是否为试运行

        返回:
            恢复结果
        """
        snapshot_path = os.path.join(self._snapshot_dir, snapshot_id)

        if not os.path.exists(snapshot_path):
            return {"success": False, "error": f"快照不存在: {snapshot_id}"}

        result = {
            "success": False,
            "snapshot_id": snapshot_id,
            "dry_run": dry_run,
            "changes": {
                "index": False,
                "structured": False,
                "messages": False,
            },
        }

        try:
            # 检查快照内容
            index_src = os.path.join(snapshot_path, "index")
            structured_src = os.path.join(snapshot_path, "structured")
            messages_src = os.path.join(snapshot_path, "messages")

            if os.path.exists(index_src):
                result["changes"]["index"] = True
            if os.path.exists(structured_src):
                result["changes"]["structured"] = True
            if os.path.exists(messages_src):
                result["changes"]["messages"] = True

            if dry_run:
                result["success"] = True
                result["message"] = "试运行完成，未实际恢复"
                return result

            # 实际恢复
            # 先创建当前状态的备份
            backup_id = self.create_snapshot(
                description=f"恢复前自动备份",
                tags=["auto_backup", "pre_restore"]
            )
            result["backup_id"] = backup_id

            # 恢复索引
            if os.path.exists(index_src):
                # 删除当前索引
                if os.path.exists(self.kb._index_dir):
                    shutil.rmtree(self.kb._index_dir)
                # 复制快照索引
                shutil.copytree(index_src, self.kb._index_dir)

            # 恢复结构化数据
            if os.path.exists(structured_src):
                if os.path.exists(self.kb._structured_dir):
                    shutil.rmtree(self.kb._structured_dir)
                shutil.copytree(structured_src, self.kb._structured_dir)

            # 恢复消息归档
            if os.path.exists(messages_src):
                if os.path.exists(self.kb._messages_dir):
                    shutil.rmtree(self.kb._messages_dir)
                shutil.copytree(messages_src, self.kb._messages_dir)

            # 重新加载索引
            self.kb._load_index()

            result["success"] = True
            result["message"] = f"恢复成功，当前分块数: {len(self.kb._chunks)}"

            logger.info(f"恢复快照成功: {snapshot_id}")

            # 记录操作日志
            self.kb._op_logger.log(
                timestamp=datetime.now().isoformat(),
                operation="restore_snapshot",
                result_count=len(self.kb._chunks),
                status="success",
                details=f"从快照 {snapshot_id} 恢复"
            )

        except Exception as e:
            logger.error(f"恢复快照失败: {e}")
            result["error"] = str(e)

        return result

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """删除快照"""
        snapshot_path = os.path.join(self._snapshot_dir, snapshot_id)

        if not os.path.exists(snapshot_path):
            return False

        try:
            # 删除快照目录
            shutil.rmtree(snapshot_path)

            # 更新元数据
            meta = self._load_meta()
            meta = [m for m in meta if m["snapshot_id"] != snapshot_id]
            self._save_meta(meta)

            logger.info(f"删除快照成功: {snapshot_id}")
            return True

        except Exception as e:
            logger.error(f"删除快照失败: {e}")
            return False

    def compare_snapshots(self, snapshot_id1: str,
                         snapshot_id2: str = None) -> dict:
        """
        比较两个快照的差异

        参数:
            snapshot_id1: 快照ID1
            snapshot_id2: 快照ID2（如果为None，则与当前状态比较）

        返回:
            差异信息
        """
        path1 = os.path.join(self._snapshot_dir, snapshot_id1)
        if not os.path.exists(path1):
            return {"error": f"快照不存在: {snapshot_id1}"}

        # 获取快照1的分块数
        info1_file = os.path.join(path1, "snapshot_info.json")
        with open(info1_file, "r", encoding="utf-8") as f:
            info1 = json.load(f)
        chunks1_count = info1.get("chunks_count", 0)

        # 获取快照2的分块数
        if snapshot_id2:
            path2 = os.path.join(self._snapshot_dir, snapshot_id2)
            if not os.path.exists(path2):
                return {"error": f"快照不存在: {snapshot_id2}"}
            info2_file = os.path.join(path2, "snapshot_info.json")
            with open(info2_file, "r", encoding="utf-8") as f:
                info2 = json.load(f)
            chunks2_count = info2.get("chunks_count", 0)
        else:
            chunks2_count = len(self.kb._chunks)

        # 计算差异
        diff = chunks2_count - chunks1_count
        diff_percent = (diff / chunks1_count * 100) if chunks1_count > 0 else 0

        return {
            "snapshot1": {
                "id": snapshot_id1,
                "chunks_count": chunks1_count,
                "created_at": info1.get("created_at"),
            },
            "snapshot2": {
                "id": snapshot_id2 or "current",
                "chunks_count": chunks2_count,
            },
            "difference": {
                "chunks_diff": diff,
                "diff_percent": round(diff_percent, 2),
                "direction": "增加" if diff > 0 else "减少" if diff < 0 else "相同",
            }
        }

    def _get_dir_size(self, path: str) -> int:
        """获取目录大小（字节）"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total_size += os.path.getsize(fp)
        return total_size

    def cleanup_old_snapshots(self, keep_count: int = 10,
                              keep_days: int = 30) -> int:
        """
        清理旧快照

        参数:
            keep_count: 保留的快照数量
            keep_days: 保留的天数

        返回:
            清理的快照数量
        """
        meta = self._load_meta()

        if len(meta) <= keep_count:
            return 0

        # 按时间排序
        meta.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # 计算截止时间
        cutoff_time = datetime.now().timestamp() - keep_days * 24 * 3600

        # 找出需要删除的快照
        to_delete = []
        for i, m in enumerate(meta):
            if i < keep_count:
                continue  # 保留最新的几个

            created_at = m.get("created_at", "")
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at)
                    if dt.timestamp() < cutoff_time:
                        to_delete.append(m["snapshot_id"])
                except:
                    pass

        # 删除
        deleted = 0
        for snapshot_id in to_delete:
            if self.delete_snapshot(snapshot_id):
                deleted += 1

        logger.info(f"清理了 {deleted} 个旧快照")
        return deleted


# 全局快照管理器实例
_snapshot_manager: Optional[KnowledgeSnapshot] = None


def get_snapshot_manager(kb=None) -> Optional[KnowledgeSnapshot]:
    """获取全局快照管理器实例"""
    global _snapshot_manager
    if _snapshot_manager is None and kb is not None:
        _snapshot_manager = KnowledgeSnapshot(kb)
    return _snapshot_manager
