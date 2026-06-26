"""
PPT Engine - 网络图片搜索模块

多Provider支持：
- Openverse (CC授权)
- Wikimedia (公共领域)
- Pexels (免费授权)
- Pixabay (免费授权)
"""

from .image_searcher import ImageSearcher, SearchRequest, SearchResult

__all__ = ['ImageSearcher', 'SearchRequest', 'SearchResult']
