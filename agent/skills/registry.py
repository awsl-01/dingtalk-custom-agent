"""
技能注册系统 - 让技能可以独立开发，不影响主文件
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SkillMatch:
    """技能匹配结果"""
    skill: 'BaseSkill'
    confidence: float  # 0-1，置信度
    extracted_info: dict  # 提取的信息


class BaseSkill(ABC):
    """技能基类 - 所有技能继承此类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """技能名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """技能描述"""
        pass

    @property
    def keywords(self) -> List[str]:
        """触发关键词"""
        return []

    @property
    def priority(self) -> int:
        """优先级，数字越小越优先"""
        return 100

    @abstractmethod
    def can_handle(self, text: str) -> float:
        """
        判断是否能处理此消息

        参数:
            text: 用户消息

        返回:
            0-1 的置信度，0 表示不能处理，1 表示完全匹配
        """
        pass

    @abstractmethod
    async def execute(self, text: str, context: dict) -> str:
        """
        执行技能

        参数:
            text: 用户消息
            context: 上下文信息（sender_nick, user_id, conversation_id, school_config 等）

        返回:
            回复文本
        """
        pass

    def extract_info(self, text: str) -> dict:
        """
        从消息中提取信息

        参数:
            text: 用户消息

        返回:
            提取的信息字典
        """
        return {}


class SkillRegistry:
    """技能注册中心"""

    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}
        self._handlers: Dict[str, Callable] = {}

    def register(self, skill: BaseSkill):
        """注册技能"""
        if skill.name in self._skills:
            logger.warning(f"技能 {skill.name} 已存在，将被覆盖")
        self._skills[skill.name] = skill
        logger.info(f"注册技能: {skill.name}")

    def unregister(self, skill_name: str):
        """注销技能"""
        if skill_name in self._skills:
            del self._skills[skill_name]
            logger.info(f"注销技能: {skill_name}")

    def get_skill(self, skill_name: str) -> Optional[BaseSkill]:
        """获取技能"""
        return self._skills.get(skill_name)

    def get_all_skills(self) -> List[BaseSkill]:
        """获取所有技能"""
        return list(self._skills.values())

    def match(self, text: str) -> Optional[SkillMatch]:
        """
        匹配最适合的技能

        参数:
            text: 用户消息

        返回:
            最佳匹配结果，如果没有匹配则返回 None
        """
        matches = []

        for skill in self._skills.values():
            try:
                confidence = skill.can_handle(text)
                if confidence > 0:
                    info = skill.extract_info(text)
                    matches.append(SkillMatch(
                        skill=skill,
                        confidence=confidence,
                        extracted_info=info,
                    ))
            except Exception as e:
                logger.error(f"技能 {skill.name} 匹配失败: {e}")

        if not matches:
            return None

        # 按置信度和优先级排序
        matches.sort(key=lambda m: (-m.confidence, m.skill.priority))
        return matches[0]

    def match_all(self, text: str) -> List[SkillMatch]:
        """
        匹配所有能处理的技能

        参数:
            text: 用户消息

        返回:
            所有匹配结果
        """
        matches = []

        for skill in self._skills.values():
            try:
                confidence = skill.can_handle(text)
                if confidence > 0:
                    info = skill.extract_info(text)
                    matches.append(SkillMatch(
                        skill=skill,
                        confidence=confidence,
                        extracted_info=info,
                    ))
            except Exception as e:
                logger.error(f"技能 {skill.name} 匹配失败: {e}")

        # 按置信度和优先级排序
        matches.sort(key=lambda m: (-m.confidence, m.skill.priority))
        return matches


# 全局技能注册中心
skill_registry = SkillRegistry()
