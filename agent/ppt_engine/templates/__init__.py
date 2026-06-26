"""
PPT Engine - 模板系统

三层模板架构：
- brand: 品牌标识（颜色/字体/Logo/语音/图标风格）
- layout: 布局结构（画布/页面结构/页面类型/SVG roster）
- deck: 完整套牌（brand + layout + 内容概览）
"""

from .brand_manager import BrandManager, Brand
from .layout_manager import LayoutManager, Layout
from .deck_manager import DeckManager, Deck

__all__ = ['BrandManager', 'Brand', 'LayoutManager', 'Layout', 'DeckManager', 'Deck']
