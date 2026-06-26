"""
PPT Engine - 页面构建器

提供各种页面布局的SVG生成方法。
"""

from typing import Dict, List, Any, Optional
from .base_generator import SVGPageGenerator, SVGPage


class PageBuilder(SVGPageGenerator):
    """页面构建器"""

    def generate_page(self, page_num: int, content: Dict[str, Any]) -> SVGPage:
        """
        生成单页SVG

        参数:
            page_num: 页码
            content: 页面内容，包含:
                - title: 页面标题
                - layout: 布局类型
                - rhythm: 节奏（dense/breathing/anchor）
                - 其他内容字段

        返回:
            SVGPage对象
        """
        # 重新加载spec_lock
        self._reload_spec_lock()

        title = content.get('title', '')
        layout = content.get('layout', 'content')
        rhythm = content.get('rhythm', 'dense')

        # 根据布局类型选择生成方法
        layout_methods = {
            'cover': self._generate_cover,
            'toc': self._generate_toc,
            'content': self._generate_content,
            'three_card': self._generate_three_card,
            'four_card': self._generate_four_card,
            'grid_2x2': self._generate_grid_2x2,
            'split': self._generate_split,
            'quote': self._generate_quote,
            'ending': self._generate_ending,
            'breathing': self._generate_breathing,
        }

        generate_func = layout_methods.get(layout, self._generate_content)
        svg_content = generate_func(page_num, content)

        return SVGPage(
            page_num=page_num,
            title=title,
            svg_content=svg_content,
            layout=layout,
            rhythm=rhythm,
            metadata=content
        )

    def _generate_cover(self, page_num: int, content: Dict[str, Any]) -> str:
        """生成封面页"""
        title = content.get('title', '标题')
        subtitle = content.get('subtitle', '副标题')
        author = content.get('author', '')
        date = content.get('date', '')

        accent = self.colors['accent']
        primary = self.colors['primary']

        svg = self.generate_svg_header()
        svg += self.generate_background()

        # 装饰线条
        svg += f'  <rect x="0" y="0" width="8" height="{self.canvas_height}" fill="{accent}"/>\n'

        # 标题区域
        svg += f'''  <g id="title">
    <text x="120" y="{self.canvas_height // 2 - 40}" fill="{primary}" font-family="{self.typography['title_font']}" font-size="48" font-weight="bold">{title}</text>
    <text x="120" y="{self.canvas_height // 2 + 20}" fill="{self.colors['text_secondary']}" font-family="{self.typography['body_font']}" font-size="24">{subtitle}</text>
  </g>
'''

        # 作者和日期
        if author:
            svg += f'  <text x="120" y="{self.canvas_height - 100}" fill="{self.colors["text_secondary"]}" font-family="{self.typography["body_font"]}" font-size="16">{author}</text>\n'
        if date:
            svg += f'  <text x="120" y="{self.canvas_height - 70}" fill="{self.colors["text_secondary"]}" font-family="{self.typography["body_font"]}" font-size="14">{date}</text>\n'

        svg += self.generate_svg_footer()
        return svg

    def _generate_toc(self, page_num: int, content: Dict[str, Any]) -> str:
        """生成目录页"""
        items = content.get('items', [])
        accent = self.colors['accent']

        svg = self.generate_svg_header()
        svg += self.generate_background()
        svg += self.generate_header_bar('目录', f'第 {page_num} 页')

        # 目录项
        start_y = 120
        for i, item in enumerate(items):
            item_y = start_y + i * 50
            svg += f'''  <g id="toc-{i+1}">
    <circle cx="60" cy="{item_y}" r="15" fill="{accent}"/>
    <text x="60" y="{item_y + 5}" fill="#FFFFFF" font-family="{self.typography['body_font']}" font-size="14" text-anchor="middle">{i+1}</text>
    <text x="90" y="{item_y + 5}" fill="{self.colors['text']}" font-family="{self.typography['body_font']}" font-size="18">{item}</text>
  </g>
'''

        svg += self.generate_footer(page_num)
        svg += self.generate_svg_footer()
        return svg

    def _generate_content(self, page_num: int, content: Dict[str, Any]) -> str:
        """生成内容页"""
        title = content.get('title', '')
        body = content.get('body', '')
        bullets = content.get('bullets', [])

        svg = self.generate_svg_header()
        svg += self.generate_background()
        svg += self.generate_header_bar(title, f'第 {page_num} 页')

        # 内容区域
        content_y = 120

        if body:
            svg += self.generate_text_block(60, content_y, body, font_size=18)
            content_y += 40

        if bullets:
            svg += self.generate_bullet_list(60, content_y, bullets)

        svg += self.generate_footer(page_num)
        svg += self.generate_svg_footer()
        return svg

    def _generate_three_card(self, page_num: int, content: Dict[str, Any]) -> str:
        """生成三卡片布局"""
        title = content.get('title', '')
        cards = content.get('cards', [])

        svg = self.generate_svg_header()
        svg += self.generate_background()
        svg += self.generate_header_bar(title, f'第 {page_num} 页')

        # 三列卡片
        card_width = (self.canvas_width - 120 - 40) // 3
        card_height = self.canvas_height - 250

        for i in range(3):
            if i < len(cards):
                card = cards[i]
                x = 60 + i * (card_width + 20)
                svg += self.generate_card(
                    x, 120, card_width, card_height,
                    title=card.get('title', ''),
                    content=card.get('content', ''),
                    card_id=f'card-{i+1}'
                )

        svg += self.generate_footer(page_num)
        svg += self.generate_svg_footer()
        return svg

    def _generate_four_card(self, page_num: int, content: Dict[str, Any]) -> str:
        """生成四卡片布局"""
        title = content.get('title', '')
        cards = content.get('cards', [])

        svg = self.generate_svg_header()
        svg += self.generate_background()
        svg += self.generate_header_bar(title, f'第 {page_num} 页')

        # 2x2 卡片
        card_width = (self.canvas_width - 120 - 20) // 2
        card_height = (self.canvas_height - 260) // 2

        for i in range(4):
            if i < len(cards):
                card = cards[i]
                col = i % 2
                row = i // 2
                x = 60 + col * (card_width + 20)
                y = 120 + row * (card_height + 20)
                svg += self.generate_card(
                    x, y, card_width, card_height,
                    title=card.get('title', ''),
                    content=card.get('content', ''),
                    card_id=f'card-{i+1}'
                )

        svg += self.generate_footer(page_num)
        svg += self.generate_svg_footer()
        return svg

    def _generate_grid_2x2(self, page_num: int, content: Dict[str, Any]) -> str:
        """生成2x2网格布局"""
        return self._generate_four_card(page_num, content)

    def _generate_split(self, page_num: int, content: Dict[str, Any]) -> str:
        """生成左右分栏布局"""
        title = content.get('title', '')
        left_content = content.get('left', '')
        right_content = content.get('right', '')

        svg = self.generate_svg_header()
        svg += self.generate_background()
        svg += self.generate_header_bar(title, f'第 {page_num} 页')

        # 左栏
        half_width = (self.canvas_width - 120 - 20) // 2
        svg += self.generate_card(60, 120, half_width, self.canvas_height - 250,
                                 content=left_content)

        # 右栏
        svg += self.generate_card(60 + half_width + 20, 120, half_width, self.canvas_height - 250,
                                 content=right_content)

        svg += self.generate_footer(page_num)
        svg += self.generate_svg_footer()
        return svg

    def _generate_quote(self, page_num: int, content: Dict[str, Any]) -> str:
        """生成引用页"""
        quote = content.get('quote', '')
        author = content.get('author', '')

        accent = self.colors['accent']

        svg = self.generate_svg_header()
        svg += self.generate_background()

        # 大引号
        svg += f'  <text x="100" y="200" fill="{accent}" font-size="120" font-family="Georgia, serif" opacity="0.3">"</text>\n'

        # 引用文本
        svg += f'  <text x="150" y="300" fill="{self.colors["text"]}" font-family="{self.typography["title_font"]}" font-size="28" font-style="italic">{quote}</text>\n'

        # 作者
        if author:
            svg += f'  <text x="150" y="380" fill="{self.colors["text_secondary"]}" font-family="{self.typography["body_font"]}" font-size="18">— {author}</text>\n'

        svg += self.generate_footer(page_num)
        svg += self.generate_svg_footer()
        return svg

    def _generate_ending(self, page_num: int, content: Dict[str, Any]) -> str:
        """生成结束页"""
        title = content.get('title', '谢谢')
        subtitle = content.get('subtitle', '')

        accent = self.colors['accent']

        svg = self.generate_svg_header()
        svg += self.generate_background()

        # 居中标题
        svg += f'  <text x="{self.canvas_width // 2}" y="{self.canvas_height // 2 - 20}" fill="{self.colors["primary"]}" font-family="{self.typography["title_font"]}" font-size="48" font-weight="bold" text-anchor="middle">{title}</text>\n'

        if subtitle:
            svg += f'  <text x="{self.canvas_width // 2}" y="{self.canvas_height // 2 + 30}" fill="{self.colors["text_secondary"]}" font-family="{self.typography["body_font"]}" font-size="24" text-anchor="middle">{subtitle}</text>\n'

        # 装饰线
        svg += f'  <line x1="{self.canvas_width // 2 - 50}" y1="{self.canvas_height // 2 + 60}" x2="{self.canvas_width // 2 + 50}" y2="{self.canvas_height // 2 + 60}" stroke="{accent}" stroke-width="2"/>\n'

        svg += self.generate_svg_footer()
        return svg

    def _generate_breathing(self, page_num: int, content: Dict[str, Any]) -> str:
        """生成呼吸页（空白过渡页）"""
        title = content.get('title', '')

        svg = self.generate_svg_header()
        svg += self.generate_background()

        # 简单标题
        if title:
            svg += f'  <text x="{self.canvas_width // 2}" y="{self.canvas_height // 2}" fill="{self.colors["text_secondary"]}" font-family="{self.typography["body_font"]}" font-size="24" text-anchor="middle">{title}</text>\n'

        svg += self.generate_svg_footer()
        return svg


def build_page(project_path: str, page_num: int, content: Dict[str, Any]) -> SVGPage:
    """
    构建单页SVG（便捷函数）

    参数:
        project_path: 项目路径
        page_num: 页码
        content: 页面内容

    返回:
        SVGPage对象
    """
    builder = PageBuilder(project_path)
    return builder.generate_page(page_num, content)
