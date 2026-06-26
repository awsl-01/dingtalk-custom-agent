"""
PPT Engine - HTML转换器

使用markdownify + BeautifulSoup将HTML转换为Markdown。
支持表格、列表、图片、链接等格式保留。
"""

import re
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse

from .base_converter import BaseConverter, ConversionResult

# 检查依赖
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    from markdownify import markdownify as md
    MARKDOWNIFY_AVAILABLE = True
except ImportError:
    MARKDOWNIFY_AVAILABLE = False


class HTMLConverter(BaseConverter):
    """HTML转换器"""

    @property
    def supported_extensions(self) -> List[str]:
        return ['.html', '.htm']

    @property
    def format_name(self) -> str:
        return 'HTML'

    def _extract_images(self, soup: 'BeautifulSoup', base_url: str = None) -> List[Path]:
        """提取图片"""
        import requests

        images = []
        img_tags = soup.find_all('img')

        for idx, img in enumerate(img_tags):
            src = img.get('src', '')
            if not src:
                continue

            # 处理相对URL
            if base_url and not urlparse(src).netloc:
                src = urljoin(base_url, src)

            try:
                # 下载图片
                if src.startswith('http'):
                    response = requests.get(src, timeout=10)
                    if response.status_code == 200:
                        # 确定文件扩展名
                        content_type = response.headers.get('content-type', '')
                        ext = '.jpg'
                        if 'png' in content_type:
                            ext = '.png'
                        elif 'gif' in content_type:
                            ext = '.gif'
                        elif 'webp' in content_type:
                            ext = '.webp'

                        img_name = f"image_{idx + 1}{ext}"
                        img_path = self.images_dir / img_name
                        img_path.write_bytes(response.content)
                        images.append(img_path)

                        # 更新img标签的src
                        rel_path = img_path.relative_to(self.output_dir)
                        img['src'] = str(rel_path)

            except Exception as e:
                print(f"[WARN] Download image failed: {src} - {e}")

        return images

    def _do_convert(self) -> ConversionResult:
        """执行HTML转换"""
        if not BS4_AVAILABLE:
            return ConversionResult(
                success=False,
                markdown='',
                images=[],
                metadata=self._extract_metadata(),
                error="beautifulsoup4未安装，请运行: pip install beautifulsoup4"
            )

        try:
            # 读取HTML
            content = self.input_path.read_text(encoding='utf-8')

            # 解析HTML
            soup = BeautifulSoup(content, 'html.parser')

            # 提取图片
            images = self._extract_images(soup)

            # 移除脚本和样式
            for tag in soup(['script', 'style', 'noscript']):
                tag.decompose()

            # 转换为Markdown
            if MARKDOWNIFY_AVAILABLE:
                markdown = md(str(soup), heading_style="ATX")
            else:
                # 简单HTML清理
                markdown = re.sub(r'<[^>]+>', '', str(soup))

            markdown = self._clean_text(markdown)

            metadata = self._extract_metadata()
            metadata['image_count'] = len(images)

            # 提取标题
            title_tag = soup.find('title')
            if title_tag:
                metadata['title'] = title_tag.string

            return ConversionResult(
                success=True,
                markdown=markdown,
                images=images,
                metadata=metadata
            )

        except Exception as e:
            return ConversionResult(
                success=False,
                markdown='',
                images=[],
                metadata=self._extract_metadata(),
                error=f"HTML转换失败: {str(e)}"
            )


def convert_html(input_path: str, output_dir: str = None) -> ConversionResult:
    """
    转换HTML文件为Markdown

    参数:
        input_path: HTML文件路径
        output_dir: 输出目录

    返回:
        ConversionResult 对象
    """
    converter = HTMLConverter(input_path, output_dir)
    return converter.convert()
