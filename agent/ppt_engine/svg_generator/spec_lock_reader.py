"""
PPT Engine - Spec Lock读取器

读取spec_lock.md文件，解析设计规范。
每页SVG生成前必须重读，抵抗上下文漂移。
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ColorScheme:
    """颜色方案"""
    primary: str = '#1A1A1A'
    secondary: str = '#555555'
    accent: str = '#1976D2'
    background: str = '#FFFFFF'
    surface: str = '#F5F5F5'
    text: str = '#1A1A1A'
    text_secondary: str = '#666666'

    def to_dict(self) -> Dict[str, str]:
        return {
            'primary': self.primary,
            'secondary': self.secondary,
            'accent': self.accent,
            'background': self.background,
            'surface': self.surface,
            'text': self.text,
            'text_secondary': self.text_secondary
        }


@dataclass
class Typography:
    """字体方案"""
    title_font: str = 'Microsoft YaHei, SimHei, Arial, sans-serif'
    body_font: str = 'Microsoft YaHei, PingFang SC, Arial, sans-serif'
    title_size: int = 32
    subtitle_size: int = 24
    body_size: int = 18
    caption_size: int = 14

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title_font': self.title_font,
            'body_font': self.body_font,
            'title_size': self.title_size,
            'subtitle_size': self.subtitle_size,
            'body_size': self.body_size,
            'caption_size': self.caption_size
        }


@dataclass
class PageSpec:
    """页面规范"""
    page_num: int = 0
    title: str = ''
    layout: str = 'content'
    rhythm: str = 'dense'  # dense / breathing / anchor
    charts: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'page_num': self.page_num,
            'title': self.title,
            'layout': self.layout,
            'rhythm': self.rhythm,
            'charts': self.charts,
            'images': self.images
        }


@dataclass
class SpecLock:
    """Spec Lock规范"""
    canvas_format: str = 'ppt169'
    width: int = 1920
    height: int = 1080
    colors: ColorScheme = field(default_factory=ColorScheme)
    typography: Typography = field(default_factory=Typography)
    pages: List[PageSpec] = field(default_factory=list)
    icons: List[str] = field(default_factory=list)
    images: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'canvas_format': self.canvas_format,
            'width': self.width,
            'height': self.height,
            'colors': self.colors.to_dict(),
            'typography': self.typography.to_dict(),
            'pages': [p.to_dict() for p in self.pages],
            'icons': self.icons,
            'images': self.images
        }


class SpecLockReader:
    """Spec Lock读取器"""

    # 画布格式尺寸
    CANVAS_SIZES = {
        'ppt169': (1920, 1080),
        'ppt43': (1440, 1080),
        'xhs': (1080, 1440),
        'story': (1080, 1920)
    }

    def __init__(self, spec_lock_path: str):
        """
        初始化读取器

        参数:
            spec_lock_path: spec_lock.md文件路径
        """
        self.spec_lock_path = Path(spec_lock_path)

        if not self.spec_lock_path.exists():
            raise FileNotFoundError(f"spec_lock.md不存在: {spec_lock_path}")

    def read(self) -> SpecLock:
        """
        读取并解析spec_lock.md

        返回:
            SpecLock对象
        """
        content = self.spec_lock_path.read_text(encoding='utf-8')

        spec = SpecLock()

        # 解析画布格式
        spec.canvas_format = self._extract_value(content, 'canvas_format', 'ppt169')
        width, height = self.CANVAS_SIZES.get(spec.canvas_format, (1920, 1080))
        spec.width = self._extract_int(content, 'width', width)
        spec.height = self._extract_int(content, 'height', height)

        # 解析颜色
        spec.colors = self._parse_colors(content)

        # 解析字体
        spec.typography = self._parse_typography(content)

        # 解析页面列表
        spec.pages = self._parse_pages(content)

        # 解析图标
        spec.icons = self._parse_list(content, 'icons')

        # 解析图片
        spec.images = self._parse_images(content)

        return spec

    def _extract_value(self, content: str, key: str, default: str = '') -> str:
        """提取单个值"""
        pattern = rf'{key}\s*[:=]\s*(.+?)(?:\n|$)'
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).strip().strip('"\'')
        return default

    def _extract_int(self, content: str, key: str, default: int = 0) -> int:
        """提取整数值"""
        value = self._extract_value(content, key, str(default))
        try:
            return int(value)
        except ValueError:
            return default

    def _parse_colors(self, content: str) -> ColorScheme:
        """解析颜色方案"""
        colors = ColorScheme()

        # 尝试从colors部分提取
        colors_section = self._extract_section(content, 'colors')
        if colors_section:
            colors.primary = self._extract_hex(colors_section, 'primary', colors.primary)
            colors.secondary = self._extract_hex(colors_section, 'secondary', colors.secondary)
            colors.accent = self._extract_hex(colors_section, 'accent', colors.accent)
            colors.background = self._extract_hex(colors_section, 'background', colors.background)
            colors.surface = self._extract_hex(colors_section, 'surface', colors.surface)
            colors.text = self._extract_hex(colors_section, 'text', colors.text)
            colors.text_secondary = self._extract_hex(colors_section, 'text_secondary', colors.text_secondary)

        return colors

    def _parse_typography(self, content: str) -> Typography:
        """解析字体方案"""
        typo = Typography()

        typo_section = self._extract_section(content, 'typography')
        if typo_section:
            typo.title_font = self._extract_value(typo_section, 'title_font', typo.title_font)
            typo.body_font = self._extract_value(typo_section, 'body_font', typo.body_font)
            typo.title_size = self._extract_int(typo_section, 'title_size', typo.title_size)
            typo.subtitle_size = self._extract_int(typo_section, 'subtitle_size', typo.subtitle_size)
            typo.body_size = self._extract_int(typo_section, 'body_size', typo.body_size)
            typo.caption_size = self._extract_int(typo_section, 'caption_size', typo.caption_size)

        return typo

    def _parse_pages(self, content: str) -> List[PageSpec]:
        """解析页面列表"""
        pages = []

        # 查找pages部分
        pages_section = self._extract_section(content, 'pages')
        if not pages_section:
            return pages

        # 解析每个页面
        page_pattern = r'(\d+)\.\s+\*\*(.+?)\*\*.*?(?:layout:\s*(\w+))?.*?(?:rhythm:\s*(\w+))?'
        for match in re.finditer(page_pattern, pages_section):
            page_num = int(match.group(1))
            title = match.group(2).strip()
            layout = match.group(3) or 'content'
            rhythm = match.group(4) or 'dense'

            pages.append(PageSpec(
                page_num=page_num,
                title=title,
                layout=layout,
                rhythm=rhythm
            ))

        return pages

    def _parse_list(self, content: str, key: str) -> List[str]:
        """解析列表"""
        section = self._extract_section(content, key)
        if not section:
            return []

        items = []
        for line in section.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('*'):
                items.append(line[1:].strip())
            elif line.startswith('`'):
                items.append(line.strip('`'))

        return items

    def _parse_images(self, content: str) -> List[Dict[str, str]]:
        """解析图片列表"""
        images = []

        images_section = self._extract_section(content, 'images')
        if not images_section:
            return images

        # 解析图片行
        img_pattern = r'\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|'
        for match in re.finditer(img_pattern, images_section):
            filename = match.group(1).strip()
            acquire_via = match.group(2).strip()
            status = match.group(3).strip()

            if filename and filename != '---':
                images.append({
                    'filename': filename,
                    'acquire_via': acquire_via,
                    'status': status
                })

        return images

    def _extract_section(self, content: str, section_name: str) -> str:
        """提取章节内容"""
        # 匹配 ## Section Name 或 ### Section Name
        pattern = rf'#+\s+{section_name}\s*\n(.*?)(?=\n#+\s|\Z)'
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return ''

    def _extract_hex(self, content: str, key: str, default: str) -> str:
        """提取十六进制颜色值"""
        pattern = rf'{key}\s*[:=]\s*(#[0-9A-Fa-f]{{3,8}})'
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1)
        return default


def read_spec_lock(spec_lock_path: str) -> SpecLock:
    """
    读取spec_lock.md（便捷函数）

    参数:
        spec_lock_path: spec_lock.md文件路径

    返回:
        SpecLock对象
    """
    reader = SpecLockReader(spec_lock_path)
    return reader.read()
