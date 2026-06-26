"""
多学校配置管理模块
通过 corp_id 识别和隔离不同学校的配置
"""
import os
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class SchoolConfig:
    """单个学校的配置"""
    corp_id: str                          # 钉钉企业ID（唯一标识）
    name: str = ""                        # 学校名称
    system_prompt: str = ""               # 自定义system prompt（追加到默认prompt）
    knowledge_dir: str = ""               # 知识库目录路径（绝对路径）
    features: dict = field(default_factory=lambda: {
        "ppt_generation": True,
        "web_search": True,
        "knowledge_qa": True,
        "schedule_qa": True,
    })
    metadata: dict = field(default_factory=dict)  # 扩展字段

    def __post_init__(self):
        """确保 knowledge_dir 是绝对路径"""
        if self.knowledge_dir and not os.path.isabs(self.knowledge_dir):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.knowledge_dir = os.path.join(project_root, self.knowledge_dir)


class SchoolConfigManager:
    """多学校配置管理器"""
    # 项目根目录（绝对路径）
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def __init__(self, base_dir: str = "knowledge"):
        # 将相对路径转为绝对路径
        if not os.path.isabs(base_dir):
            self._base_dir = os.path.join(self._PROJECT_ROOT, base_dir)
        else:
            self._base_dir = base_dir
        self._schools: Dict[str, SchoolConfig] = {}
        self._load_all_schools()

    def _load_all_schools(self):
        """从目录中加载所有已注册的学校配置"""
        if not os.path.exists(self._base_dir):
            os.makedirs(self._base_dir, exist_ok=True)
            return

        for name in os.listdir(self._base_dir):
            school_dir = os.path.join(self._base_dir, name)
            meta_file = os.path.join(school_dir, "meta.json")
            if os.path.isdir(school_dir) and os.path.exists(meta_file):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    config = SchoolConfig(
                        corp_id=meta.get("corp_id", name),
                        name=meta.get("name", ""),
                        system_prompt=meta.get("system_prompt", ""),
                        knowledge_dir=school_dir,
                        features=meta.get("features", {}),
                        metadata=meta.get("metadata", {}),
                    )
                    self._schools[config.corp_id] = config
                    logger.info(f"加载学校配置: {config.name} ({config.corp_id})")
                except Exception as e:
                    logger.warning(f"加载学校配置失败 [{name}]: {e}")

    def get_school(self, corp_id: str) -> SchoolConfig:
        """根据corp_id获取学校配置，不存在则自动创建"""
        if corp_id not in self._schools:
            self._register_school(corp_id)
        return self._schools[corp_id]

    def _register_school(self, corp_id: str, name: str = "") -> SchoolConfig:
        """注册新学校，创建对应目录结构"""
        school_dir = os.path.join(self._base_dir, corp_id)
        subdirs = ["messages", "files", "index", "structured"]
        for sub in subdirs:
            os.makedirs(os.path.join(school_dir, sub), exist_ok=True)

        config = SchoolConfig(
            corp_id=corp_id,
            name=name or f"学校_{corp_id[:8]}",
            knowledge_dir=school_dir,
        )

        # 保存meta.json
        meta_file = os.path.join(school_dir, "meta.json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(asdict(config), f, ensure_ascii=False, indent=2)

        # 初始化结构化数据文件
        for data_file in ["schedules.json", "exams.json", "contacts.json"]:
            path = os.path.join(school_dir, "structured", data_file)
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump([], f)

        self._schools[corp_id] = config
        logger.info(f"注册新学校: {config.name} ({corp_id})")
        return config

    def register_school(self, corp_id: str, name: str = "",
                        system_prompt: str = "", **kwargs) -> SchoolConfig:
        """公开接口：注册新学校"""
        config = self._register_school(corp_id, name)
        if system_prompt:
            config.system_prompt = system_prompt
        if kwargs:
            config.metadata.update(kwargs)
            self._save_meta(config)
        return config

    def _save_meta(self, config: SchoolConfig):
        """保存学校配置到meta.json"""
        meta_file = os.path.join(config.knowledge_dir, "meta.json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(asdict(config), f, ensure_ascii=False, indent=2)

    def list_schools(self) -> list:
        """列出所有已注册的学校"""
        return [
            {"corp_id": c.corp_id, "name": c.name}
            for c in self._schools.values()
        ]


# 全局实例
school_manager = SchoolConfigManager()
