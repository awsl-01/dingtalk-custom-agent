"""
多模态处理模块

提供图片OCR、文件深度解析、音视频转写等功能
"""

from .ocr import OCREngine
from .parser import DeepFileParser

__all__ = [
    "OCREngine",
    "DeepFileParser",
]
