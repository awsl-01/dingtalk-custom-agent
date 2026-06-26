"""
PPT Engine - TTS音频生成器

将文本转换为语音音频。
支持多Provider：Edge-TTS, ElevenLabs, MiniMax, Qwen, CosyVoice。
"""

import os
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class AudioRequest:
    """音频生成请求"""
    text: str
    filename: str = ''
    voice: str = 'zh-CN-XiaoxiaoNeural'
    rate: str = '+0%'
    volume: str = '+0%'
    pitch: str = '+0Hz'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'text': self.text,
            'filename': self.filename,
            'voice': self.voice,
            'rate': self.rate,
            'volume': self.volume,
            'pitch': self.pitch
        }


@dataclass
class AudioResult:
    """音频生成结果"""
    success: bool
    audio_path: Optional[str] = None
    duration: float = 0.0
    provider: str = ''
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseTTSBackend(ABC):
    """TTS后端基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """后端名称"""
        pass

    @abstractmethod
    def generate(self, request: AudioRequest, output_dir: str) -> AudioResult:
        """
        生成音频

        参数:
            request: 生成请求
            output_dir: 输出目录

        返回:
            AudioResult对象
        """
        pass

    def _get_api_key(self, env_key: str) -> str:
        """获取API Key"""
        api_key = os.environ.get(env_key, '')
        if not api_key:
            raise ValueError(f"Environment variable {env_key} not set")
        return api_key


class EdgeTTSBackend(BaseTTSBackend):
    """Edge-TTS后端"""

    @property
    def name(self) -> str:
        return 'edge'

    def generate(self, request: AudioRequest, output_dir: str) -> AudioResult:
        try:
            import edge_tts

            # 生成文件名
            filename = request.filename or 'audio.mp3'
            output_path = Path(output_dir) / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 运行异步生成
            asyncio.run(self._generate_edge_tts(
                request.text,
                request.voice,
                request.rate,
                request.volume,
                request.pitch,
                str(output_path)
            ))

            # 获取时长
            duration = self._get_audio_duration(output_path)

            return AudioResult(
                success=True,
                audio_path=str(output_path),
                duration=duration,
                provider='edge',
                metadata={'voice': request.voice}
            )

        except Exception as e:
            return AudioResult(success=False, provider='edge', error=str(e))

    async def _generate_edge_tts(self, text: str, voice: str, rate: str,
                                 volume: str, pitch: str, output_path: str):
        """使用edge-tts生成音频"""
        import edge_tts

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            volume=volume,
            pitch=pitch
        )

        await communicate.save(output_path)

    def _get_audio_duration(self, audio_path: Path) -> float:
        """获取音频时长"""
        try:
            # 简单估算：根据文件大小
            file_size = audio_path.stat().st_size
            # MP3大约128kbps = 16KB/s
            duration = file_size / 16000
            return round(duration, 2)
        except Exception:
            return 0.0

    def list_voices(self, locale: str = None) -> List[Dict[str, str]]:
        """列出可用声音"""
        try:
            import edge_tts

            voices = asyncio.run(edge_tts.list_voices())

            if locale:
                voices = [v for v in voices if v['Locale'].startswith(locale)]

            return [{
                'name': v['ShortName'],
                'locale': v['Locale'],
                'gender': v['Gender'],
                'display_name': v['FriendlyName']
            } for v in voices]

        except Exception as e:
            print(f"[WARN] List voices failed: {e}")
            return []


class ElevenLabsBackend(BaseTTSBackend):
    """ElevenLabs后端"""

    @property
    def name(self) -> str:
        return 'elevenlabs'

    def generate(self, request: AudioRequest, output_dir: str) -> AudioResult:
        try:
            import requests

            api_key = self._get_api_key('ELEVENLABS_API_KEY')
            voice_id = os.environ.get('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

            headers = {
                'xi-api-key': api_key,
                'Content-Type': 'application/json'
            }

            data = {
                'text': request.text,
                'model_id': 'eleven_multilingual_v2',
                'voice_settings': {
                    'stability': 0.5,
                    'similarity_boost': 0.75
                }
            }

            response = requests.post(url, json=data, headers=headers)

            if response.status_code == 200:
                # 生成文件名
                filename = request.filename or 'audio.mp3'
                output_path = Path(output_dir) / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(response.content)

                return AudioResult(
                    success=True,
                    audio_path=str(output_path),
                    provider='elevenlabs',
                    metadata={'voice_id': voice_id}
                )
            else:
                return AudioResult(
                    success=False,
                    provider='elevenlabs',
                    error=f"API error: {response.status_code}"
                )

        except Exception as e:
            return AudioResult(success=False, provider='elevenlabs', error=str(e))


class MiniMaxBackend(BaseTTSBackend):
    """MiniMax后端"""

    @property
    def name(self) -> str:
        return 'minimax'

    def generate(self, request: AudioRequest, output_dir: str) -> AudioResult:
        try:
            import requests

            api_key = self._get_api_key('MINIMAX_API_KEY')

            url = "https://api.minimax.chat/v1/text/speech"

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                'model': 'speech-01',
                'text': request.text,
                'voice_id': request.voice or 'male-qn-qingse'
            }

            response = requests.post(url, json=data, headers=headers)
            result = response.json()

            if 'audio_file' in result:
                audio_url = result['audio_file']

                # 下载音频
                audio_response = requests.get(audio_url)
                audio_data = audio_response.content

                # 生成文件名
                filename = request.filename or 'audio.mp3'
                output_path = Path(output_dir) / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(audio_data)

                return AudioResult(
                    success=True,
                    audio_path=str(output_path),
                    provider='minimax',
                    metadata={'voice_id': data['voice_id']}
                )
            else:
                error_msg = result.get('status_msg', 'Unknown error')
                return AudioResult(success=False, provider='minimax', error=error_msg)

        except Exception as e:
            return AudioResult(success=False, provider='minimax', error=str(e))


class QwenBackend(BaseTTSBackend):
    """Qwen后端"""

    @property
    def name(self) -> str:
        return 'qwen'

    def generate(self, request: AudioRequest, output_dir: str) -> AudioResult:
        try:
            import requests

            api_key = self._get_api_key('DASHSCOPE_API_KEY')

            url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                'model': 'cosyvoice-v1',
                'input': {
                    'text': request.text
                },
                'parameters': {
                    'voice': request.voice or 'zhixiaobichun'
                }
            }

            response = requests.post(url, json=data, headers=headers)
            result = response.json()

            if 'output' in result and 'audio' in result['output']:
                audio_url = result['output']['audio']

                # 下载音频
                audio_response = requests.get(audio_url)
                audio_data = audio_response.content

                # 生成文件名
                filename = request.filename or 'audio.mp3'
                output_path = Path(output_dir) / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(audio_data)

                return AudioResult(
                    success=True,
                    audio_path=str(output_path),
                    provider='qwen',
                    metadata={'voice': data['parameters']['voice']}
                )
            else:
                error_msg = result.get('message', 'Unknown error')
                return AudioResult(success=False, provider='qwen', error=error_msg)

        except Exception as e:
            return AudioResult(success=False, provider='qwen', error=str(e))


class CosyVoiceBackend(BaseTTSBackend):
    """CosyVoice后端"""

    @property
    def name(self) -> str:
        return 'cosyvoice'

    def generate(self, request: AudioRequest, output_dir: str) -> AudioResult:
        # CosyVoice使用与Qwen相同的API
        qwen_backend = QwenBackend()
        return qwen_backend.generate(request, output_dir)


class TTSGenerator:
    """TTS生成器"""

    # 支持的后端
    BACKENDS = {
        'edge': EdgeTTSBackend,
        'elevenlabs': ElevenLabsBackend,
        'minimax': MiniMaxBackend,
        'qwen': QwenBackend,
        'cosyvoice': CosyVoiceBackend,
    }

    def __init__(self, default_backend: str = None):
        """
        初始化TTS生成器

        参数:
            default_backend: 默认后端名称
        """
        self.default_backend = default_backend or self._detect_backend()

    def _detect_backend(self) -> str:
        """自动检测可用的后端"""
        if os.environ.get('ELEVENLABS_API_KEY'):
            return 'elevenlabs'
        elif os.environ.get('MINIMAX_API_KEY'):
            return 'minimax'
        elif os.environ.get('DASHSCOPE_API_KEY'):
            return 'qwen'
        else:
            return 'edge'  # 默认使用Edge-TTS

    def get_backend(self, backend_name: str = None) -> BaseTTSBackend:
        """获取后端实例"""
        name = backend_name or self.default_backend
        backend_cls = self.BACKENDS.get(name)

        if not backend_cls:
            raise ValueError(f"Unknown backend: {name}")

        return backend_cls()

    def generate(self, request: AudioRequest, output_dir: str,
                backend_name: str = None) -> AudioResult:
        """
        生成音频

        参数:
            request: 生成请求
            output_dir: 输出目录
            backend_name: 后端名称（可选）

        返回:
            AudioResult对象
        """
        backend = self.get_backend(backend_name)

        print(f"[TTS] Using {backend.name} backend")
        print(f"   Text: {request.text[:50]}...")

        result = backend.generate(request, output_dir)

        if result.success:
            print(f"[OK] Audio saved: {result.audio_path}")
            print(f"   Duration: {result.duration}s")
        else:
            print(f"[FAIL] Generation failed: {result.error}")

        return result

    def generate_from_notes(self, notes_dir: str, output_dir: str,
                           voice: str = None) -> List[AudioResult]:
        """
        从演讲备注生成音频

        参数:
            notes_dir: 备注目录
            output_dir: 输出目录
            voice: 声音名称

        返回:
            AudioResult列表
        """
        notes_dir = Path(notes_dir)
        if not notes_dir.exists():
            return []

        results = []
        for note_file in sorted(notes_dir.glob('*.md')):
            text = note_file.read_text(encoding='utf-8').strip()
            if not text:
                continue

            # 生成文件名
            filename = f"{note_file.stem}.mp3"

            request = AudioRequest(
                text=text,
                filename=filename,
                voice=voice or 'zh-CN-XiaoxiaoNeural'
            )

            result = self.generate(request, output_dir)
            results.append(result)

        return results

    def list_backends(self) -> List[str]:
        """列出可用后端"""
        return list(self.BACKENDS.keys())


def generate_audio(text: str, output_dir: str, filename: str = None,
                  voice: str = None, backend: str = None) -> AudioResult:
    """
    生成音频（便捷函数）

    参数:
        text: 文本内容
        output_dir: 输出目录
        filename: 输出文件名
        voice: 声音名称
        backend: 后端名称

    返回:
        AudioResult对象
    """
    generator = TTSGenerator()
    request = AudioRequest(text=text, filename=filename or 'audio.mp3', voice=voice or 'zh-CN-XiaoxiaoNeural')
    return generator.generate(request, output_dir, backend)
