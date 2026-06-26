"""
PPT Engine - SVG页面生成器基类

逐页手写SVG，保证跨页视觉一致性。
每页生成前重读spec_lock，抵抗上下文漂移。
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .spec_lock_reader import SpecLock, SpecLockReader, read_spec_lock


@dataclass
class SVGPage:
    """SVG页面"""
    page_num: int
    title: str
    svg_content: str
    layout: str
    rhythm: str
    metadata: Dict[str, Any]

    def save(self, output_dir: str):
        """保存SVG文件"""
        output_path = Path(output_dir) / f"slide_{self.page_num:02d}.svg"
        output_path.write_text(self.svg_content, encoding='utf-8')
        return output_path


class SVGPageGenerator(ABC):
    """SVG页面生成器基类"""

    def __init__(self, project_path: str, spec_lock_path: str = None):
        """
        初始化生成器

        参数:
            project_path: 项目路径
            spec_lock_path: spec_lock.md路径（默认为项目目录下）
        """
        self.project_path = Path(project_path)

        if spec_lock_path:
            self.spec_lock_path = Path(spec_lock_path)
        else:
            self.spec_lock_path = self.project_path / 'spec_lock.md'

        # 初始化spec_lock
        self.spec_lock = self._load_spec_lock()

    def _load_spec_lock(self) -> SpecLock:
        """加载spec_lock（每次生成前调用）"""
        return read_spec_lock(str(self.spec_lock_path))

    def _reload_spec_lock(self):
        """重新加载spec_lock"""
        self.spec_lock = self._load_spec_lock()

    @property
    def canvas_width(self) -> int:
        return self.spec_lock.width

    @property
    def canvas_height(self) -> int:
        return self.spec_lock.height

    @property
    def colors(self) -> Dict[str, str]:
        return self.spec_lock.colors.to_dict()

    @property
    def typography(self) -> Dict[str, Any]:
        return self.spec_lock.typography.to_dict()

    def generate_svg_header(self) -> str:
        """生成SVG头部"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     viewBox="0 0 {self.canvas_width} {self.canvas_height}"
     width="{self.canvas_width}"
     height="{self.canvas_height}">
'''

    def generate_svg_footer(self) -> str:
        """生成SVG尾部"""
        return '</svg>'

    def generate_background(self, color: str = None) -> str:
        """生成背景"""
        bg_color = color or self.colors['background']
        return f'  <rect width="{self.canvas_width}" height="{self.canvas_height}" fill="{bg_color}"/>'

    def generate_header_bar(self, title: str, subtitle: str = None) -> str:
        """生成顶部标题栏"""
        header_height = 70
        header_bg = self.colors['primary']

        svg = f'''  <g id="header">
    <rect x="0" y="0" width="{self.canvas_width}" height="{header_height}" fill="{header_bg}"/>
    <text x="40" y="45" fill="#FFFFFF" font-family="{self.typography['title_font']}" font-size="24" font-weight="bold">{title}</text>
'''

        if subtitle:
            svg += f'    <text x="{self.canvas_width - 40}" y="45" fill="#FFFFFF" font-family="{self.typography['body_font']}" font-size="14" text-anchor="end">{subtitle}</text>\n'

        svg += '  </g>\n'
        return svg

    def generate_footer(self, page_num: int, total_pages: int = None) -> str:
        """生成页脚"""
        footer_y = self.canvas_height - 40
        footer_color = self.colors.get('text_secondary', '#888888')

        page_text = f"{page_num}"
        if total_pages:
            page_text += f" / {total_pages}"

        return f'''  <g id="footer">
    <line x1="40" y1="{footer_y}" x2="{self.canvas_width - 40}" y2="{footer_y}" stroke="{footer_color}" stroke-width="0.5" stroke-opacity="0.3"/>
    <text x="{self.canvas_width - 40}" y="{footer_y + 25}" fill="{footer_color}" font-family="{self.typography['body_font']}" font-size="12" text-anchor="end">{page_text}</text>
  </g>
'''

    def generate_card(self, x: int, y: int, width: int, height: int,
                      title: str = None, content: str = None,
                      card_id: str = None) -> str:
        """生成卡片"""
        card_bg = self.colors['surface']
        card_border = self.colors.get('card_border', '#E0E0E0')
        text_color = self.colors['text']

        svg = f'  <g'
        if card_id:
            svg += f' id="{card_id}"'
        svg += f'>\n'

        # 卡片背景
        svg += f'    <rect x="{x}" y="{y}" width="{width}" height="{height}" rx="8" fill="{card_bg}" stroke="{card_border}" stroke-width="1"/>\n'

        # 标题
        if title:
            svg += f'    <text x="{x + 20}" y="{y + 35}" fill="{text_color}" font-family="{self.typography["title_font"]}" font-size="18" font-weight="bold">{title}</text>\n'

        # 内容
        if content:
            content_y = y + 60 if title else y + 30
            svg += f'    <text x="{x + 20}" y="{content_y}" fill="{self.colors["text_secondary"]}" font-family="{self.typography["body_font"]}" font-size="14">{content}</text>\n'

        svg += '  </g>\n'
        return svg

    def generate_text_block(self, x: int, y: int, text: str,
                           font_size: int = 18, font_weight: str = 'normal',
                           color: str = None, max_width: int = None) -> str:
        """生成文本块"""
        text_color = color or self.colors['text']

        svg = f'  <text x="{x}" y="{y}" fill="{text_color}" font-family="{self.typography["body_font"]}" font-size="{font_size}" font-weight="{font_weight}"'

        if max_width:
            svg += f' textLength="{max_width}" lengthAdjust="spacingAndGlyphs"'

        svg += f'>{text}</text>\n'
        return svg

    def generate_bullet_list(self, x: int, y: int, items: List[str],
                            spacing: int = 30, bullet: str = '•') -> str:
        """生成项目符号列表"""
        svg = ''
        for i, item in enumerate(items):
            item_y = y + i * spacing
            svg += f'  <text x="{x}" y="{item_y}" fill="{self.colors["accent"]}" font-family="{self.typography["body_font"]}" font-size="16">{bullet}</text>\n'
            svg += f'  <text x="{x + 25}" y="{item_y}" fill="{self.colors["text"]}" font-family="{self.typography["body_font"]}" font-size="16">{item}</text>\n'
        return svg

    def add_group_id(self, svg: str, group_id: str) -> str:
        """为SVG元素添加分组ID"""
        # 在第一个 <g> 标签后添加id
        if '<g>' in svg:
            svg = svg.replace('<g>', f'<g id="{group_id}">', 1)
        return svg

    @abstractmethod
    def generate_page(self, page_num: int, content: Dict[str, Any]) -> SVGPage:
        """
        生成单页SVG

        参数:
            page_num: 页码
            content: 页面内容

        返回:
            SVGPage对象
        """
        pass

    def generate_pages(self, pages_content: List[Dict[str, Any]]) -> List[SVGPage]:
        """
        批量生成页面

        参数:
            pages_content: 页面内容列表

        返回:
            SVGPage列表
        """
        pages = []
        total_pages = len(pages_content)

        for i, content in enumerate(pages_content):
            # 每页重新加载spec_lock
            self._reload_spec_lock()

            page_num = i + 1
            page = self.generate_page(page_num, content)
            page.metadata['total_pages'] = total_pages
            pages.append(page)

        return pages

    def save_pages(self, pages: List[SVGPage], output_dir: str = None) -> List[Path]:
        """
        保存所有页面

        参数:
            pages: SVGPage列表
            output_dir: 输出目录（默认为svg_output）

        返回:
            保存的文件路径列表
        """
        if output_dir is None:
            output_dir = self.project_path / 'svg_output'
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        saved_paths = []
        for page in pages:
            path = page.save(str(output_dir))
            saved_paths.append(path)
            print(f"[OK] Saved: {path.name}")

        return saved_paths
