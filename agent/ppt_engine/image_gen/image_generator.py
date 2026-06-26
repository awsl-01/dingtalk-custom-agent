"""
PPT Engine - AI图片生成器

统一接口调用多个AI图片生成Provider。
"""

import os
import json
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class ImageRequest:
    """图片生成请求"""
    prompt: str
    filename: str = ''
    aspect_ratio: str = '16:9'  # 16:9, 4:3, 1:1
    style: str = 'natural'  # natural, artistic, realistic
    negative_prompt: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return {
            'prompt': self.prompt,
            'filename': self.filename,
            'aspect_ratio': self.aspect_ratio,
            'style': self.style,
            'negative_prompt': self.negative_prompt
        }


@dataclass
class ImageResult:
    """图片生成结果"""
    success: bool
    image_path: Optional[str] = None
    image_data: Optional[bytes] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseImageBackend(ABC):
    """图片生成后端基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """后端名称"""
        pass

    @abstractmethod
    def generate(self, request: ImageRequest, output_dir: str) -> ImageResult:
        """
        生成图片

        参数:
            request: 生成请求
            output_dir: 输出目录

        返回:
            ImageResult对象
        """
        pass

    def _get_api_key(self, env_key: str) -> str:
        """获取API Key"""
        api_key = os.environ.get(env_key, '')
        if not api_key:
            raise ValueError(f"Environment variable {env_key} not set")
        return api_key

    def _save_image(self, image_data: bytes, output_path: Path) -> Path:
        """保存图片"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_data)
        return output_path


class GeminiBackend(BaseImageBackend):
    """Gemini图片生成后端"""

    @property
    def name(self) -> str:
        return 'gemini'

    def generate(self, request: ImageRequest, output_dir: str) -> ImageResult:
        try:
            from google import genai

            api_key = self._get_api_key('GEMINI_API_KEY')
            client = genai.Client(api_key=api_key)

            # 生成图片
            response = client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=request.prompt,
                config={
                    'number_of_images': 1,
                    'aspect_ratio': request.aspect_ratio,
                }
            )

            if response.generated_images:
                image = response.generated_images[0]
                image_data = image.image.image_bytes

                # 保存图片
                filename = request.filename or 'generated_image.png'
                output_path = Path(output_dir) / filename
                self._save_image(image_data, output_path)

                return ImageResult(
                    success=True,
                    image_path=str(output_path),
                    image_data=image_data,
                    metadata={'provider': 'gemini'}
                )
            else:
                return ImageResult(success=False, error="No image generated")

        except Exception as e:
            return ImageResult(success=False, error=str(e))


class OpenAIBackend(BaseImageBackend):
    """OpenAI图片生成后端"""

    @property
    def name(self) -> str:
        return 'openai'

    def generate(self, request: ImageRequest, output_dir: str) -> ImageResult:
        try:
            from openai import OpenAI

            api_key = self._get_api_key('OPENAI_API_KEY')
            client = OpenAI(api_key=api_key)

            # 映射尺寸
            size_map = {
                '16:9': '1792x1024',
                '4:3': '1024x1024',
                '1:1': '1024x1024',
            }
            size = size_map.get(request.aspect_ratio, '1024x1024')

            # 生成图片
            response = client.images.generate(
                model="dall-e-3",
                prompt=request.prompt,
                size=size,
                quality="standard",
                n=1,
            )

            if response.data:
                image_url = response.data[0].url

                # 下载图片
                import requests
                img_response = requests.get(image_url)
                image_data = img_response.content

                # 保存图片
                filename = request.filename or 'generated_image.png'
                output_path = Path(output_dir) / filename
                self._save_image(image_data, output_path)

                return ImageResult(
                    success=True,
                    image_path=str(output_path),
                    image_data=image_data,
                    metadata={'provider': 'openai', 'url': image_url}
                )
            else:
                return ImageResult(success=False, error="No image generated")

        except Exception as e:
            return ImageResult(success=False, error=str(e))


class QwenBackend(BaseImageBackend):
    """Qwen图片生成后端"""

    @property
    def name(self) -> str:
        return 'qwen'

    def generate(self, request: ImageRequest, output_dir: str) -> ImageResult:
        try:
            import requests

            api_key = self._get_api_key('DASHSCOPE_API_KEY')

            # 调用Qwen图片生成API
            url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"

            # 映射尺寸
            size_map = {
                '16:9': '1920*1080',
                '4:3': '1024*1024',
                '1:1': '1024*1024',
            }
            size = size_map.get(request.aspect_ratio, '1024*1024')

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                "model": "wanx-v1",
                "input": {
                    "prompt": request.prompt
                },
                "parameters": {
                    "size": size,
                    "n": 1
                }
            }

            response = requests.post(url, headers=headers, json=data)
            result = response.json()

            if 'output' in result and 'results' in result['output']:
                image_url = result['output']['results'][0]['url']

                # 下载图片
                img_response = requests.get(image_url)
                image_data = img_response.content

                # 保存图片
                filename = request.filename or 'generated_image.png'
                output_path = Path(output_dir) / filename
                self._save_image(image_data, output_path)

                return ImageResult(
                    success=True,
                    image_path=str(output_path),
                    image_data=image_data,
                    metadata={'provider': 'qwen', 'url': image_url}
                )
            else:
                error_msg = result.get('message', 'Unknown error')
                return ImageResult(success=False, error=error_msg)

        except Exception as e:
            return ImageResult(success=False, error=str(e))


class ZhipuBackend(BaseImageBackend):
    """Zhipu图片生成后端"""

    @property
    def name(self) -> str:
        return 'zhipu'

    def generate(self, request: ImageRequest, output_dir: str) -> ImageResult:
        try:
            import requests

            api_key = self._get_api_key('ZHIPU_API_KEY')

            # 调用Zhipu图片生成API
            url = "https://open.bigmodel.cn/api/paas/v4/images/generations"

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                "model": "cogview-3",
                "prompt": request.prompt,
                "size": "1024x1024"
            }

            response = requests.post(url, headers=headers, json=data)
            result = response.json()

            if 'data' in result and len(result['data']) > 0:
                image_url = result['data'][0]['url']

                # 下载图片
                img_response = requests.get(image_url)
                image_data = img_response.content

                # 保存图片
                filename = request.filename or 'generated_image.png'
                output_path = Path(output_dir) / filename
                self._save_image(image_data, output_path)

                return ImageResult(
                    success=True,
                    image_path=str(output_path),
                    image_data=image_data,
                    metadata={'provider': 'zhipu', 'url': image_url}
                )
            else:
                error_msg = result.get('error', {}).get('message', 'Unknown error')
                return ImageResult(success=False, error=error_msg)

        except Exception as e:
            return ImageResult(success=False, error=str(e))


class ImageGenerator:
    """图片生成器"""

    # 支持的后端
    BACKENDS = {
        'gemini': GeminiBackend,
        'openai': OpenAIBackend,
        'qwen': QwenBackend,
        'zhipu': ZhipuBackend,
    }

    def __init__(self, default_backend: str = None):
        """
        初始化图片生成器

        参数:
            default_backend: 默认后端名称
        """
        self.default_backend = default_backend or self._detect_backend()

    def _detect_backend(self) -> str:
        """自动检测可用的后端"""
        if os.environ.get('GEMINI_API_KEY'):
            return 'gemini'
        elif os.environ.get('OPENAI_API_KEY'):
            return 'openai'
        elif os.environ.get('DASHSCOPE_API_KEY'):
            return 'qwen'
        elif os.environ.get('ZHIPU_API_KEY'):
            return 'zhipu'
        else:
            return 'gemini'  # 默认

    def get_backend(self, backend_name: str = None) -> BaseImageBackend:
        """获取后端实例"""
        name = backend_name or self.default_backend
        backend_cls = self.BACKENDS.get(name)

        if not backend_cls:
            raise ValueError(f"Unknown backend: {name}")

        return backend_cls()

    def generate(self, request: ImageRequest, output_dir: str,
                backend_name: str = None) -> ImageResult:
        """
        生成图片

        参数:
            request: 生成请求
            output_dir: 输出目录
            backend_name: 后端名称（可选）

        返回:
            ImageResult对象
        """
        backend = self.get_backend(backend_name)

        print(f"[GENERATE] Using {backend.name} backend")
        print(f"   Prompt: {request.prompt[:50]}...")

        result = backend.generate(request, output_dir)

        if result.success:
            print(f"[OK] Image saved: {result.image_path}")
        else:
            print(f"[FAIL] Generation failed: {result.error}")

        return result

    def generate_from_manifest(self, manifest_path: str, output_dir: str) -> List[ImageResult]:
        """
        从manifest批量生成图片

        参数:
            manifest_path: manifest.json路径
            output_dir: 输出目录

        返回:
            ImageResult列表
        """
        manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
        items = manifest.get('items', [])

        results = []
        for item in items:
            request = ImageRequest(
                prompt=item.get('prompt', ''),
                filename=item.get('filename', ''),
                aspect_ratio=item.get('aspect_ratio', '16:9'),
                style=item.get('style', 'natural'),
                negative_prompt=item.get('negative_prompt', '')
            )

            result = self.generate(request, output_dir)
            results.append(result)

        return results

    def list_backends(self) -> List[str]:
        """列出可用后端"""
        return list(self.BACKENDS.keys())


def generate_image(prompt: str, output_dir: str, filename: str = None,
                  backend: str = None) -> ImageResult:
    """
    生成图片（便捷函数）

    参数:
        prompt: 生成提示
        output_dir: 输出目录
        filename: 输出文件名
        backend: 后端名称

    返回:
        ImageResult对象
    """
    generator = ImageGenerator()
    request = ImageRequest(prompt=prompt, filename=filename or 'generated.png')
    return generator.generate(request, output_dir, backend)
