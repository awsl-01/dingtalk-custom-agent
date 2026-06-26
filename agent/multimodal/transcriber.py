"""
音视频转写器

自动转写网课片段或语音通知为文字
支持：
- 音频转写（使用 Whisper）
- 视频转写（提取音频 + 转写）
- 视频关键帧提取
"""
import os
import logging
import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TranscribeResult:
    """转写结果"""
    text: str                    # 转写文字
    segments: list = field(default_factory=list)  # 时间段
    duration: float = 0.0        # 时长（秒）
    language: str = ""           # 语言
    error: str = ""              # 错误信息


@dataclass
class TimeSegment:
    """时间段"""
    start: float        # 开始时间
    end: float          # 结束时间
    text: str           # 文字内容


@dataclass
class VideoFrame:
    """视频关键帧"""
    timestamp: float    # 时间戳
    frame_path: str     # 帧图片路径
    description: str    # 描述


class AudioTranscriber:
    """
    音频转写器

    使用 Whisper 进行音频转写
    """

    def __init__(self, model_size: str = "base"):
        """
        初始化音频转写器

        参数:
            model_size: 模型大小（tiny/base/small/medium/large）
        """
        self._model_size = model_size
        self._model = None

    def _load_model(self):
        """加载 Whisper 模型"""
        if self._model is not None:
            return

        try:
            import whisper
            logger.info(f"加载 Whisper 模型: {self._model_size}")
            self._model = whisper.load_model(self._model_size)
            logger.info("Whisper 模型加载完成")
        except ImportError:
            raise ImportError("需要安装 whisper: pip install openai-whisper")
        except Exception as e:
            logger.error(f"加载 Whisper 模型失败: {e}")
            raise

    async def transcribe(self, audio_path: str,
                        language: str = None) -> TranscribeResult:
        """
        转写音频

        参数:
            audio_path: 音频文件路径
            language: 语言（None 为自动检测）

        返回:
            转写结果
        """
        if not os.path.exists(audio_path):
            return TranscribeResult(
                text="",
                error=f"音频文件不存在: {audio_path}"
            )

        try:
            self._load_model()

            # 执行转写
            options = {}
            if language:
                options["language"] = language

            result = self._model.transcribe(audio_path, **options)

            # 解析结果
            segments = []
            for seg in result.get("segments", []):
                segments.append(TimeSegment(
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"].strip()
                ))

            # 计算时长
            duration = segments[-1].end if segments else 0

            return TranscribeResult(
                text=result.get("text", "").strip(),
                segments=[s.__dict__ for s in segments],
                duration=duration,
                language=result.get("language", "")
            )

        except Exception as e:
            logger.error(f"音频转写失败: {e}")
            return TranscribeResult(text="", error=str(e))


class VideoTranscriber:
    """
    视频转写器

    功能：
    1. 提取视频音频
    2. 转写音频为文字
    3. 提取关键帧
    """

    def __init__(self, audio_transcriber: AudioTranscriber = None):
        """
        初始化视频转写器

        参数:
            audio_transcriber: 音频转写器实例
        """
        self._audio_transcriber = audio_transcriber or AudioTranscriber()

    async def transcribe(self, video_path: str,
                        language: str = None,
                        extract_frames: bool = False,
                        frame_interval: float = 30.0) -> TranscribeResult:
        """
        转写视频

        参数:
            video_path: 视频文件路径
            language: 语言
            extract_frames: 是否提取关键帧
            frame_interval: 关键帧间隔（秒）

        返回:
            转写结果
        """
        if not os.path.exists(video_path):
            return TranscribeResult(
                text="",
                error=f"视频文件不存在: {video_path}"
            )

        try:
            # 提取音频
            audio_path = await self._extract_audio(video_path)
            if not audio_path:
                return TranscribeResult(
                    text="",
                    error="提取音频失败"
                )

            # 转写音频
            result = await self._audio_transcriber.transcribe(audio_path, language)

            # 提取关键帧（如果需要）
            if extract_frames and not result.error:
                frames = await self._extract_frames(video_path, frame_interval)
                result.segments.extend([f.__dict__ for f in frames])

            # 清理临时音频文件
            if os.path.exists(audio_path):
                os.remove(audio_path)

            return result

        except Exception as e:
            logger.error(f"视频转写失败: {e}")
            return TranscribeResult(text="", error=str(e))

    async def _extract_audio(self, video_path: str) -> Optional[str]:
        """从视频中提取音频"""
        try:
            import subprocess

            # 生成临时音频文件路径
            audio_path = video_path + ".temp_audio.wav"

            # 使用 ffmpeg 提取音频
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vn",  # 不包含视频
                "-acodec", "pcm_s16le",  # WAV 格式
                "-ar", "16000",  # 采样率
                "-ac", "1",  # 单声道
                "-y",  # 覆盖已有文件
                audio_path
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300  # 5分钟超时
            )

            if result.returncode == 0 and os.path.exists(audio_path):
                return audio_path
            else:
                logger.error(f"ffmpeg 提取音频失败: {result.stderr.decode()}")
                return None

        except FileNotFoundError:
            logger.error("需要安装 ffmpeg")
            return None
        except Exception as e:
            logger.error(f"提取音频失败: {e}")
            return None

    async def _extract_frames(self, video_path: str,
                             interval: float = 30.0) -> List[VideoFrame]:
        """提取视频关键帧"""
        try:
            import subprocess

            # 创建临时目录
            frames_dir = video_path + "_frames"
            os.makedirs(frames_dir, exist_ok=True)

            # 使用 ffmpeg 提取关键帧
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vf", f"fps=1/{interval}",  # 每 interval 秒一帧
                "-q:v", "2",  # 质量
                os.path.join(frames_dir, "frame_%04d.jpg")
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=600  # 10分钟超时
            )

            frames = []
            if result.returncode == 0:
                # 获取视频时长
                duration = await self._get_video_duration(video_path)

                # 收集帧文件
                frame_files = sorted([
                    f for f in os.listdir(frames_dir)
                    if f.endswith(".jpg")
                ])

                for i, frame_file in enumerate(frame_files):
                    frame_path = os.path.join(frames_dir, frame_file)
                    timestamp = i * interval

                    frames.append(VideoFrame(
                        timestamp=timestamp,
                        frame_path=frame_path,
                        description=f"第 {i+1} 帧 ({timestamp:.1f}s)"
                    ))

            return frames

        except Exception as e:
            logger.error(f"提取关键帧失败: {e}")
            return []

    async def _get_video_duration(self, video_path: str) -> float:
        """获取视频时长"""
        try:
            import subprocess

            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )

            if result.returncode == 0:
                return float(result.stdout.decode().strip())
            return 0.0

        except Exception:
            return 0.0


class MediaTranscriber:
    """
    媒体转写器（统一接口）

    支持音频和视频文件的转写
    """

    def __init__(self, whisper_model: str = "base"):
        """
        初始化媒体转写器

        参数:
            whisper_model: Whisper 模型大小
        """
        self._audio_transcriber = AudioTranscriber(whisper_model)
        self._video_transcriber = VideoTranscriber(self._audio_transcriber)

        # 支持的格式
        self._audio_formats = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac"}
        self._video_formats = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"}

    async def transcribe(self, file_path: str,
                        language: str = None,
                        extract_frames: bool = False) -> TranscribeResult:
        """
        转写媒体文件

        参数:
            file_path: 媒体文件路径
            language: 语言
            extract_frames: 是否提取视频关键帧

        返回:
            转写结果
        """
        if not os.path.exists(file_path):
            return TranscribeResult(
                text="",
                error=f"文件不存在: {file_path}"
            )

        ext = os.path.splitext(file_path)[1].lower()

        if ext in self._audio_formats:
            return await self._audio_transcriber.transcribe(file_path, language)
        elif ext in self._video_formats:
            return await self._video_transcriber.transcribe(
                file_path, language, extract_frames
            )
        else:
            return TranscribeResult(
                text="",
                error=f"不支持的文件格式: {ext}"
            )

    def get_supported_formats(self) -> dict:
        """获取支持的格式"""
        return {
            "audio": list(self._audio_formats),
            "video": list(self._video_formats),
        }


# 全局媒体转写器实例
_transcriber: Optional[MediaTranscriber] = None


def get_media_transcriber(whisper_model: str = "base") -> MediaTranscriber:
    """获取全局媒体转写器实例"""
    global _transcriber
    if _transcriber is None:
        _transcriber = MediaTranscriber(whisper_model)
    return _transcriber
