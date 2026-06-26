"""
PPT Engine - 页面转场效果

支持转场效果：
- fade: 淡入淡出
- push: 推入
- wipe: 擦除
- split: 分裂
- strips: 条纹
- cover: 覆盖
- random: 随机
"""

from typing import Dict, Any, Optional
from enum import Enum


class TransitionType(Enum):
    """转场类型"""
    FADE = 'fade'
    PUSH = 'push'
    WIPE = 'wipe'
    SPLIT = 'split'
    STRIPS = 'strips'
    COVER = 'cover'
    RANDOM = 'random'
    NONE = 'none'


class TransitionEffect:
    """转场效果"""

    # 转场定义
    TRANSITIONS = {
        'fade': {
            'name': 'Fade',
            'element': 'p:fade',
            'attrs': {},
        },
        'push': {
            'name': 'Push',
            'element': 'p:push',
            'attrs': {'dir': 'r'},
        },
        'wipe': {
            'name': 'Wipe',
            'element': 'p:wipe',
            'attrs': {'dir': 'r'},
        },
        'split': {
            'name': 'Split',
            'element': 'p:split',
            'attrs': {'orient': 'horz', 'dir': 'out'},
        },
        'strips': {
            'name': 'Strips',
            'element': 'p:strips',
            'attrs': {'dir': 'rd'},
        },
        'cover': {
            'name': 'Cover',
            'element': 'p:cover',
            'attrs': {'dir': 'r'},
        },
    }

    def __init__(self, transition_type: str = 'fade', duration: int = 500):
        """
        初始化转场效果

        参数:
            transition_type: 转场类型
            duration: 持续时间（毫秒）
        """
        self.type = self._parse_type(transition_type)
        self.duration = duration

    def _parse_type(self, transition_type: str) -> TransitionType:
        """解析转场类型"""
        try:
            return TransitionType(transition_type)
        except ValueError:
            return TransitionType.FADE

    def to_xml(self) -> str:
        """
        生成XML

        返回:
            PowerPoint XML字符串
        """
        if self.type == TransitionType.NONE:
            return ''

        if self.type == TransitionType.RANDOM:
            import random
            effect_name = random.choice(list(self.TRANSITIONS.keys()))
        else:
            effect_name = self.type.value

        transition = self.TRANSITIONS.get(effect_name, self.TRANSITIONS['fade'])

        # 构建属性
        attrs = ['spd="med"', 'advClick="1"']
        for key, value in transition['attrs'].items():
            attrs.append(f'{key}="{value}"')

        attrs_str = ' '.join(attrs)

        return f'<p:transition {attrs_str}><{transition["element"]} /></p:transition>'

    @classmethod
    def list_transitions(cls) -> list:
        """列出所有转场效果"""
        return list(cls.TRANSITIONS.keys())


def create_transition(transition_type: str = 'fade', duration: int = 500) -> TransitionEffect:
    """
    创建转场效果（便捷函数）

    参数:
        transition_type: 转场类型
        duration: 持续时间

    返回:
        TransitionEffect对象
    """
    return TransitionEffect(transition_type, duration)
