"""
PPT Engine - TTS音频生成模块

多Provider支持：
- Edge-TTS (默认，无需API Key)
- ElevenLabs
- MiniMax
- Qwen
- CosyVoice
"""

from .tts_generator import TTSGenerator, AudioRequest, AudioResult

__all__ = ['TTSGenerator', 'AudioRequest', 'AudioResult']
