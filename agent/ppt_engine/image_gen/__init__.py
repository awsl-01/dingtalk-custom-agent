"""
PPT Engine - AI图片生成模块

多Provider支持：
- Gemini (google-genai)
- OpenAI (openai)
- Qwen (dashscope)
- Zhipu (zhipu)
"""

from .image_generator import ImageGenerator, ImageRequest, ImageResult

__all__ = ['ImageGenerator', 'ImageRequest', 'ImageResult']
