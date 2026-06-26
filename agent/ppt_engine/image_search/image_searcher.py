"""
PPT Engine - 网络图片搜索器

搜索开放授权的图片资源。
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class SearchRequest:
    """图片搜索请求"""
    query: str
    filename: str = ''
    orientation: str = 'landscape'  # landscape, portrait, square
    license_type: str = 'all'  # all, cc0, public_domain, cc_by
    strict_no_attribution: bool = False
    limit: int = 10

    def to_dict(self) -> Dict[str, Any]:
        return {
            'query': self.query,
            'filename': self.filename,
            'orientation': self.orientation,
            'license_type': self.license_type,
            'strict_no_attribution': self.strict_no_attribution,
            'limit': self.limit
        }


@dataclass
class SearchResult:
    """图片搜索结果"""
    success: bool
    image_path: Optional[str] = None
    source_url: str = ''
    author: str = ''
    license: str = ''
    attribution: str = ''
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseSearchProvider(ABC):
    """搜索Provider基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider名称"""
        pass

    @abstractmethod
    def search(self, request: SearchRequest) -> List[Dict[str, Any]]:
        """
        搜索图片

        参数:
            request: 搜索请求

        返回:
            图片信息列表
        """
        pass

    def _download_image(self, url: str, output_path: Path) -> bool:
        """下载图片"""
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(response.content)
                return True
            return False
        except Exception:
            return False


class OpenverseProvider(BaseSearchProvider):
    """Openverse搜索Provider"""

    API_URL = "https://api.openverse.org/v1/images"

    @property
    def name(self) -> str:
        return 'openverse'

    def search(self, request: SearchRequest) -> List[Dict[str, Any]]:
        try:
            params = {
                'q': request.query,
                'page_size': request.limit,
                'source': 'flickr,wikimedia',
            }

            # License过滤
            if request.license_type == 'cc0':
                params['license'] = 'cc0'
            elif request.license_type == 'cc_by':
                params['license'] = 'by'

            response = requests.get(self.API_URL, params=params, timeout=30)
            data = response.json()

            results = []
            for item in data.get('results', []):
                results.append({
                    'url': item.get('url', ''),
                    'thumbnail': item.get('thumbnail', ''),
                    'title': item.get('title', ''),
                    'author': item.get('creator', ''),
                    'license': item.get('license', ''),
                    'license_version': item.get('license_version', ''),
                    'source': item.get('source', ''),
                })

            return results

        except Exception as e:
            print(f"[WARN] Openverse search failed: {e}")
            return []


class WikimediaProvider(BaseSearchProvider):
    """Wikimedia搜索Provider"""

    API_URL = "https://commons.wikimedia.org/w/api.php"

    @property
    def name(self) -> str:
        return 'wikimedia'

    def search(self, request: SearchRequest) -> List[Dict[str, Any]]:
        try:
            params = {
                'action': 'query',
                'generator': 'search',
                'gsrsearch': request.query,
                'gsrnamespace': '6',  # File namespace
                'gsrlimit': request.limit,
                'prop': 'imageinfo',
                'iiprop': 'url|extmetadata',
                'format': 'json',
            }

            response = requests.get(self.API_URL, params=params, timeout=30)
            data = response.json()

            results = []
            pages = data.get('query', {}).get('pages', {})

            for page_id, page in pages.items():
                imageinfo = page.get('imageinfo', [{}])[0]
                metadata = imageinfo.get('extmetadata', {})

                # 获取授权信息
                license_short = metadata.get('LicenseShortName', {}).get('value', '')
                artist = metadata.get('Artist', {}).get('value', '')

                results.append({
                    'url': imageinfo.get('url', ''),
                    'title': page.get('title', ''),
                    'author': artist,
                    'license': license_short,
                    'source': 'wikimedia',
                })

            return results

        except Exception as e:
            print(f"[WARN] Wikimedia search failed: {e}")
            return []


class PexelsProvider(BaseSearchProvider):
    """Pexels搜索Provider"""

    API_URL = "https://api.pexels.com/v1/search"

    @property
    def name(self) -> str:
        return 'pexels'

    def search(self, request: SearchRequest) -> List[Dict[str, Any]]:
        try:
            api_key = os.environ.get('PEXELS_API_KEY', '')
            if not api_key:
                return []

            headers = {'Authorization': api_key}
            params = {
                'query': request.query,
                'per_page': request.limit,
                'orientation': request.orientation,
            }

            response = requests.get(self.API_URL, headers=headers, params=params, timeout=30)
            data = response.json()

            results = []
            for photo in data.get('photos', []):
                src = photo.get('src', {})
                results.append({
                    'url': src.get('large', ''),
                    'thumbnail': src.get('medium', ''),
                    'title': photo.get('alt', ''),
                    'author': photo.get('photographer', ''),
                    'license': 'Pexels License',
                    'source': 'pexels',
                })

            return results

        except Exception as e:
            print(f"[WARN] Pexels search failed: {e}")
            return []


class PixabayProvider(BaseSearchProvider):
    """Pixabay搜索Provider"""

    API_URL = "https://pixabay.com/api/"

    @property
    def name(self) -> str:
        return 'pixabay'

    def search(self, request: SearchRequest) -> List[Dict[str, Any]]:
        try:
            api_key = os.environ.get('PIXABAY_API_KEY', '')
            if not api_key:
                return []

            params = {
                'key': api_key,
                'q': request.query,
                'per_page': request.limit,
                'orientation': 'horizontal' if request.orientation == 'landscape' else 'vertical',
            }

            response = requests.get(self.API_URL, params=params, timeout=30)
            data = response.json()

            results = []
            for hit in data.get('hits', []):
                results.append({
                    'url': hit.get('largeImageURL', ''),
                    'thumbnail': hit.get('webformatURL', ''),
                    'title': hit.get('tags', ''),
                    'author': hit.get('user', ''),
                    'license': 'Pixabay License',
                    'source': 'pixabay',
                })

            return results

        except Exception as e:
            print(f"[WARN] Pixabay search failed: {e}")
            return []


class ImageSearcher:
    """图片搜索器"""

    # 支持的Provider
    PROVIDERS = {
        'openverse': OpenverseProvider,
        'wikimedia': WikimediaProvider,
        'pexels': PexelsProvider,
        'pixabay': PixabayProvider,
    }

    def __init__(self):
        """初始化图片搜索器"""
        pass

    def get_provider(self, provider_name: str) -> BaseSearchProvider:
        """获取Provider实例"""
        provider_cls = self.PROVIDERS.get(provider_name)

        if not provider_cls:
            raise ValueError(f"Unknown provider: {provider_name}")

        return provider_cls()

    def search(self, request: SearchRequest, provider_name: str = None) -> List[Dict[str, Any]]:
        """
        搜索图片

        参数:
            request: 搜索请求
            provider_name: Provider名称（可选，默认搜索所有）

        返回:
            图片信息列表
        """
        all_results = []

        if provider_name:
            providers = [provider_name]
        else:
            providers = ['openverse', 'wikimedia']

        for prov_name in providers:
            try:
                provider = self.get_provider(prov_name)
                print(f"[SEARCH] Using {prov_name} provider...")

                results = provider.search(request)
                all_results.extend(results)

                print(f"   Found {len(results)} images")

            except Exception as e:
                print(f"[WARN] {prov_name} search failed: {e}")

        return all_results

    def search_and_download(self, request: SearchRequest, output_dir: str,
                           provider_name: str = None) -> SearchResult:
        """
        搜索并下载图片

        参数:
            request: 搜索请求
            output_dir: 输出目录
            provider_name: Provider名称

        返回:
            SearchResult对象
        """
        results = self.search(request, provider_name)

        if not results:
            return SearchResult(success=False, error="No images found")

        # 选择最佳结果
        best = results[0]

        # 生成文件名
        filename = request.filename or f"image_{hash(request.query) % 10000}.jpg"
        output_path = Path(output_dir) / filename

        # 下载图片
        provider = self.get_provider(best.get('source', 'openverse'))
        if provider._download_image(best['url'], output_path):
            # 生成归属信息
            attribution = self._build_attribution(best)

            return SearchResult(
                success=True,
                image_path=str(output_path),
                source_url=best.get('url', ''),
                author=best.get('author', ''),
                license=best.get('license', ''),
                attribution=attribution,
                metadata=best
            )
        else:
            return SearchResult(success=False, error="Download failed")

    def _build_attribution(self, image_info: Dict[str, Any]) -> str:
        """构建归属信息"""
        author = image_info.get('author', 'Unknown')
        license_name = image_info.get('license', 'Unknown')
        source = image_info.get('source', '')

        if 'CC0' in license_name or 'Public Domain' in license_name:
            return f"By {author} ({license_name})"
        else:
            return f"By {author} ({license_name}) via {source}"

    def list_providers(self) -> List[str]:
        """列出可用Provider"""
        return list(self.PROVIDERS.keys())


def search_images(query: str, output_dir: str, filename: str = None,
                 provider: str = None) -> SearchResult:
    """
    搜索图片（便捷函数）

    参数:
        query: 搜索关键词
        output_dir: 输出目录
        filename: 输出文件名
        provider: Provider名称

    返回:
        SearchResult对象
    """
    searcher = ImageSearcher()
    request = SearchRequest(query=query, filename=filename)
    return searcher.search_and_download(request, output_dir, provider)
