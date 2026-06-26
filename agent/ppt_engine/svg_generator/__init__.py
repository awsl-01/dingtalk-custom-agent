"""
PPT Engine - SVG生成引擎

逐页手写SVG，保证跨页视觉一致性。
每页生成前重读spec_lock，抵抗长文档上下文漂移。
"""

from .base_generator import SVGPageGenerator
from .page_builder import PageBuilder
from .spec_lock_reader import SpecLockReader

__all__ = ['SVGPageGenerator', 'PageBuilder', 'SpecLockReader']
