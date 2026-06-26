"""
PPT Engine - 元素入场动画

支持入场动画：
- appear: 出现
- fade: 淡入
- fly: 飞入
- zoom: 缩放
- wipe: 擦除
- dissolve: 溶解
- box: 盒状
- circle: 圆形
- diamond: 菱形
"""

from typing import Dict, List, Any, Optional
from enum import Enum


class EntranceEffect(Enum):
    """入场效果"""
    APPEAR = 'appear'
    FADE = 'fade'
    FLY = 'fly'
    ZOOM = 'zoom'
    WIPE = 'wipe'
    DISSOLVE = 'dissolve'
    BOX = 'box'
    CIRCLE = 'circle'
    DIAMOND = 'diamond'
    WHEEL = 'wheel'


class AnimationTrigger(Enum):
    """动画触发方式"""
    ON_CLICK = 'on-click'
    WITH_PREVIOUS = 'with-previous'
    AFTER_PREVIOUS = 'after-previous'


class EntranceAnimation:
    """入场动画"""

    # 智能映射规则
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

    # 图片类元素的动画池
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

    def __init__(self, effect: str = 'auto', trigger: str = 'after-previous',
                 delay: int = 0, duration: int = 500):
        """
        初始化入场动画

        参数:
            effect: 动画效果
            trigger: 触发方式
            delay: 延迟时间（毫秒）
            duration: 持续时间（毫秒）
        """
        self.effect = self._parse_effect(effect)
        self.trigger = self._parse_trigger(trigger)
        self.delay = delay
        self.duration = duration

    def _parse_effect(self, effect: str) -> EntranceEffect:
        """解析动画效果"""
        try:
            return EntranceEffect(effect)
        except ValueError:
            return EntranceEffect.FADE

    def _parse_trigger(self, trigger: str) -> AnimationTrigger:
        """解析触发方式"""
        try:
            return AnimationTrigger(trigger)
        except ValueError:
            return AnimationTrigger.AFTER_PREVIOUS

    def to_xml(self, shape_id: int) -> str:
        """
        生成XML

        参数:
            shape_id: 形状ID

        返回:
            PowerPoint XML字符串
        """
        effect_name = self.effect.value.capitalize()

        # 映射触发方式
        trigger_map = {
            AnimationTrigger.ON_CLICK: '0',
            AnimationTrigger.WITH_PREVIOUS: '1',
            AnimationTrigger.AFTER_PREVIOUS: '2'
        }
        trigger_value = trigger_map[self.trigger]

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
                        <p:cond delay="{trigger_value}"/>
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

    @classmethod
    def pick_effect(cls, group_id: str, mode: str = 'auto',
                    image_counter: int = 0) -> EntranceEffect:
        """
        根据分组ID和模式选择动画效果

        参数:
            group_id: SVG分组ID
            mode: 动画模式
            image_counter: 图片计数器

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
            # 经典效果循环
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
    def list_effects(cls) -> list:
        """列出所有动画效果"""
        return [e.value for e in EntranceEffect]


def create_animation(effect: str = 'auto', trigger: str = 'after-previous',
                    delay: int = 0, duration: int = 500) -> EntranceAnimation:
    """
    创建入场动画（便捷函数）

    参数:
        effect: 动画效果
        trigger: 触发方式
        delay: 延迟时间
        duration: 持续时间

    返回:
        EntranceAnimation对象
    """
    return EntranceAnimation(effect, trigger, delay, duration)
