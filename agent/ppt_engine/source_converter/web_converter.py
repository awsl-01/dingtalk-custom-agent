"""
PPT Engine - Web页面转换器

使用requests/BeautifulSoup下载网页并转换为Markdown。
支持微信公众号（通过curl_cffi绕过TLS指纹检测）。
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from .base_converter import BaseConverter, ConversionResult

# 检查依赖
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

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

try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False


# 微信公众号域名
WECHAT_HOSTS = ['mp.weixin.qq.com', 'weixin.qq.com']


class WebConverter(BaseConverter):
    """Web页面转换器"""

    def __init__(self, input_path: str, output_dir: str = None):
        """
        初始化Web转换器

        参数:
            input_path: URL
            output_dir: 输出目录
        """
        # 对于URL，创建一个临时目录
        if output_dir is None:
            output_dir = Path.cwd() / 'web_output'

        super().__init__(input_path, output_dir)

        # 解析URL
        self.url = input_path
        self.parsed_url = urlparse(self.url)

    @property
    def supported_extensions(self) -> List[str]:
        return []  # URL没有扩展名

    @property
    def format_name(self) -> str:
        return 'Web页面'

    def can_convert(self) -> bool:
        """检查是否为有效URL"""
        return self.parsed_url.scheme in ('http', 'https') and bool(self.parsed_url.netloc)

    def _is_wechat(self) -> bool:
        """检查是否为微信公众号页面"""
        return any(host in self.parsed_url.netloc for host in WECHAT_HOSTS)

    def _fetch_page(self) -> Optional[str]:
        """下载网页内容"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        try:
            # 微信页面使用curl_cffi
            if self._is_wechat() and CURL_CFFI_AVAILABLE:
                response = curl_requests.get(self.url, headers=headers, impersonate="chrome")
                return response.text

            # 普通页面使用requests
            if REQUESTS_AVAILABLE:
                response = requests.get(self.url, headers=headers, timeout=30)
                response.encoding = response.apparent_encoding
                return response.text

            return None

        except Exception as e:
            print(f"[WARN] Download page failed: {e}")
            return None

    def _extract_content(self, html: str) -> tuple:
        """提取网页内容"""
        if not BS4_AVAILABLE:
            return html, []

        soup = BeautifulSoup(html, 'html.parser')

        # 提取标题
        title = ''
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.string or ''

        # 提取正文（优先查找article或main标签）
        content = None
        for selector in ['article', 'main', '.content', '.article', '#content']:
            content = soup.select_one(selector)
            if content:
                break

        if not content:
            content = soup.find('body') or soup

        # 提取图片
        images = []
        for idx, img in enumerate(content.find_all('img')):
            src = img.get('src', '') or img.get('data-src', '')
            if not src:
                continue

            try:
                import requests
                if src.startswith('http'):
                    response = requests.get(src, timeout=10)
                    if response.status_code == 200:
                        # 确定扩展名
                        content_type = response.headers.get('content-type', '')
                        ext = '.jpg'
                        if 'png' in content_type:
                            ext = '.png'
                        elif 'gif' in content_type:
                            ext = '.gif'

                        img_name = f"image_{idx + 1}{ext}"
                        img_path = self.images_dir / img_name
                        img_path.write_bytes(response.content)
                        images.append(img_path)

                        # 更新src
                        rel_path = img_path.relative_to(self.output_dir)
                        img['src'] = str(rel_path)
            except Exception:
                pass

        return str(content), images, title

    def _do_convert(self) -> ConversionResult:
        """执行Web页面转换"""
        try:
            # 下载页面
            html = self._fetch_page()
            if not html:
                return ConversionResult(
                    success=False,
                    markdown='',
                    images=[],
                    metadata=self._extract_metadata(),
                    error="下载网页失败"
                )

            # 提取内容
            content_html, images, title = self._extract_content(html)

            # 转换为Markdown
            if MARKDOWNIFY_AVAILABLE:
                markdown = md(content_html, heading_style="ATX")
            else:
                # 简单HTML清理
                markdown = re.sub(r'<[^>]+>', '', content_html)

            # 添加标题
            if title:
                markdown = f"# {title}\n\n{markdown}"

            markdown = self._clean_text(markdown)

            metadata = self._extract_metadata()
            metadata['url'] = self.url
            metadata['title'] = title
            metadata['image_count'] = len(images)
            metadata['is_wechat'] = self._is_wechat()

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
                error=f"Web页面转换失败: {str(e)}"
            )


def convert_web(url: str, output_dir: str = None) -> ConversionResult:
    """
    转换Web页面为Markdown

    参数:
        url: 网页URL
        output_dir: 输出目录

    返回:
        ConversionResult 对象
    """
    converter = WebConverter(url, output_dir)
    return converter.convert()
