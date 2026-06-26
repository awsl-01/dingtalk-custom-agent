"""
PPT Engine - SVG转PPTX模块

将SVG文件转换为PowerPoint演示文稿。
支持DrawingML转换、图标嵌入、图片嵌入、动画效果。
"""

from .pptx_builder import PPTXBuilder
from .drawingml_converter import SVGToDrawingMLConverter

__all__ = ['PPTXBuilder', 'SVGToDrawingMLConverter']
