"""
PPT Engine - 动画配置

管理页面转场和元素入场动画的配置。
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
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


class EntranceEffect(Enum):
    """入场效果"""
    APPEAR = 'appear'
    FADE = 'fade'
    FLY = 'fly'
    CUT = 'cut'
    ZOOM = 'zoom'
    WIPE = 'wipe'
    SPLIT = 'split'
    BLINDS = 'blinds'
    DISSOLVE = 'dissolve'
    WHEEL = 'wheel'
    BOX = 'box'
    CIRCLE = 'circle'
    DIAMOND = 'diamond'


class AnimationTrigger(Enum):
    """动画触发方式"""
    ON_CLICK = 'on-click'
    WITH_PREVIOUS = 'with-previous'
    AFTER_PREVIOUS = 'after-previous'


@dataclass
class TransitionEffect:
    """转场效果配置"""
    type: TransitionType = TransitionType.FADE
    duration: int = 500  # 毫秒
    direction: str = 'r'  # 方向

    def to_xml_attrs(self) -> Dict[str, str]:
        """转换为XML属性"""
        attrs = {
            'spd': 'med',
            'advClick': '1',
        }

        if self.type == TransitionType.FADE:
            return {'fade': '', **attrs}
        elif self.type == TransitionType.PUSH:
            return {'push': '', 'dir': self.direction, **attrs}
        elif self.type == TransitionType.WIPE:
            return {'wipe': '', 'dir': self.direction, **attrs}
        elif self.type == TransitionType.SPLIT:
            return {'split': '', 'orient': 'horz', 'dir': 'out', **attrs}
        elif self.type == TransitionType.STRIPS:
            return {'strips': '', 'dir': 'rd', **attrs}
        elif self.type == TransitionType.COVER:
            return {'cover': '', 'dir': self.direction, **attrs}
        else:
            return attrs


@dataclass
class EntranceAnimation:
    """入场动画配置"""
    effect: EntranceEffect = EntranceEffect.FADE
    trigger: AnimationTrigger = AnimationTrigger.AFTER_PREVIOUS
    delay: int = 0  # 毫秒
    duration: int = 500  # 毫秒

    def to_xml(self, shape_id: int) -> str:
        """生成XML"""
        effect_name = self.effect.value.capitalize()

        trigger_map = {
            AnimationTrigger.ON_CLICK: '0',
            AnimationTrigger.WITH_PREVIOUS: '1',
            AnimationTrigger.AFTER_PREVIOUS: '2'
        }

        return f'''<p:par>
  <p:ctrnTn id="{shape_id + 1}" dur="1" nodeId="tmRoot">
    <p:childTnLst>
      <p:par>
        <p:ctrnTn id="{shape_id + 2}" dur="1" nodeId="grpId">
          <p:childTnLst>
            <p:seq concurrent="1" nextAc="seek">
              <p:ctrnTn id="{shape_id + 3}" dur="1" nodeId="mainSeq">
                <p:childTnLst>
                  <p:par>
                    <p:cTn id="{shape_id + 4}" fill="hold">
                      <p:stCondLst>
                        <p:cond delay="trigger_map[self.trigger]"/>
                      </p:stCondLst>
                      <p:childTnLst>
                        <p:set>
                          <p:cBhvr>
                            <p:cTn id="{shape_id + 5}" dur="1" fill="hold">
                              <p:stCondLst>
                                <p:cond delay="0"/>
                              </p:stCondLst>
                            </p:cTn>
                            <p:tgtEl>
                              <p:spTgt spid="{shape_id}"/>
                            </p:tgtEl>
                            <p:attrNameLst>
                              <p:attrName>style.visibility</p:attrName>
                            </p:attrNameLst>
                          </p:cBhvr>
                          <p:to>
                            <p:strVal val="visible"/>
                          </p:to>
                        </p:set>
                        <p:{effect_name}>
                          <p:cBhvr>
                            <p:cTn id="{shape_id + 6}" dur="{self.duration}">
                              <p:stCondLst>
                                <p:cond delay="{self.delay}"/>
                              </p:stCondLst>
                            </p:cTn>
                            <p:tgtEl>
                              <p:spTgt spid="{shape_id}"/>
                            </p:tgtEl>
                          </p:cBhvr>
                        </p:{effect_name}>
                      </p:childTnLst>
                    </p:cTn>
                  </p:par>
                </p:childTnLst>
              </p:cTn>
            </p:seq>
          </p:childTnLst>
        </p:ctrnTn>
      </p:par>
    </p:childTnLst>
  </p:ctrnTn>
</p:par>'''


class AnimationConfig:
    """动画配置管理器"""

    # 智能映射规则：根据SVG元素ID前缀选择动画效果
    AUTO_MAPPING = {
        'chart': EntranceEffect.WIPE,
        'card': EntranceEffect.FLY,
        'step': EntranceEffect.FLY,
        'pillar': EntranceEffect.FLY,
        'title': EntranceEffect.FADE,
        'takeaway': EntranceEffect.FADE,
        'hero': EntranceEffect.ZOOM,
        'figure': EntranceEffect.DISSOLVE,
        'image': EntranceEffect.CIRCLE,
        'kpi': EntranceEffect.BOX,
    }

    # 图片类元素的动画池（循环使用，避免重复）
    IMAGE_EFFECTS = [
        EntranceEffect.ZOOM,
        EntranceEffect.DISSOLVE,
        EntranceEffect.CIRCLE,
        EntranceEffect.BOX,
        EntranceEffect.DIAMOND,
        EntranceEffect.WHEEL,
    ]

    # 通用动画池
    DEFAULT_EFFECTS = [
        EntranceEffect.FADE,
        EntranceEffect.WIPE,
        EntranceEffect.FLY,
        EntranceEffect.ZOOM,
    ]

    @classmethod
    def pick_effect(cls, group_id: str, mode: str = 'auto',
                    image_counter: int = 0) -> EntranceEffect:
        """
        根据分组ID和模式选择动画效果

        参数:
            group_id: SVG分组ID
            mode: 动画模式（auto/mixed/random/none/具体效果名）
            image_counter: 图片计数器（用于循环图片效果）

        返回:
            EntranceEffect枚举值
        """
        if mode == 'none':
            return EntranceEffect.APPEAR

        if mode == 'auto':
            # 根据ID前缀匹配
            for prefix, effect in cls.AUTO_MAPPING.items():
                if prefix in group_id.lower():
                    # 图片类元素循环使用效果池
                    if prefix in ('hero', 'figure', 'image', 'kpi'):
                        idx = image_counter % len(cls.IMAGE_EFFECTS)
                        return cls.IMAGE_EFFECTS[idx]
                    return effect

            # 默认效果
            idx = image_counter % len(cls.DEFAULT_EFFECTS)
            return cls.DEFAULT_EFFECTS[idx]

        elif mode == 'mixed':
            # 经典16种效果循环
            all_effects = list(EntranceEffect)
            idx = image_counter % len(all_effects)
            return all_effects[idx]

        elif mode == 'random':
            import random
            return random.choice(list(EntranceEffect))

        else:
            # 尝试解析为效果名称
            try:
                return EntranceEffect(mode)
            except ValueError:
                return EntranceEffect.FADE

    @classmethod
    def create_transition(cls, transition_type: str = 'fade') -> TransitionEffect:
        """创建转场效果"""
        try:
            t_type = TransitionType(transition_type)
        except ValueError:
            t_type = TransitionType.FADE

        return TransitionEffect(type=t_type)

    @classmethod
    def create_animation(cls, effect: str = 'auto', trigger: str = 'after-previous',
                        delay: int = 0, duration: int = 500) -> EntranceAnimation:
        """创建入场动画"""
        try:
            e_effect = EntranceEffect(effect)
        except ValueError:
            e_effect = EntranceEffect.FADE

        try:
            a_trigger = AnimationTrigger(trigger)
        except ValueError:
            a_trigger = AnimationTrigger.AFTER_PREVIOUS

        return EntranceAnimation(
            effect=e_effect,
            trigger=a_trigger,
            delay=delay,
            duration=duration
        )
