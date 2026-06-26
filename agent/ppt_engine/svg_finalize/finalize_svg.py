"""
PPT Engine - SVG后处理工具

处理SVG文件，包括：
- 嵌入图标（替换 <use data-icon="..."/>）
- 嵌入图片（Base64编码）
- 扁平化文本（<tspan> 转独立 <text>）
- 转换圆角矩形（<rect rx="..."/> 转 <path>）
"""

import re
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional
from xml.etree import ElementTree as ET


class SVGFinalizer:
    """SVG后处理器"""

    def __init__(self, project_path: str):
        """
        初始化后处理器

        参数:
            project_path: 项目路径
        """
        self.project_path = Path(project_path)
        self.svg_output_dir = self.project_path / 'svg_output'
        self.svg_final_dir = self.project_path / 'svg_final'
        self.images_dir = self.project_path / 'images'

        # 创建输出目录
        self.svg_final_dir.mkdir(parents=True, exist_ok=True)

    def process_all(self) -> List[Path]:
        """
        处理所有SVG文件

        返回:
            处理后的文件路径列表
        """
        svg_files = sorted(self.svg_output_dir.glob('*.svg'))

        if not svg_files:
            print("[WARN] No SVG files found")
            return []

        processed_files = []

        for svg_file in svg_files:
            print(f"[PROCESS] {svg_file.name}")
            result = self.process_svg(svg_file)
            if result:
                processed_files.append(result)

        print(f"\n[OK] Processed: {len(processed_files)}/{len(svg_files)} files")
        return processed_files

    def process_svg(self, svg_path: Path) -> Optional[Path]:
        """
        处理单个SVG文件

        参数:
            svg_path: SVG文件路径

        返回:
            处理后的文件路径
        """
        try:
            content = svg_path.read_text(encoding='utf-8')

            # 1. 移除linearGradient（ppt-master不支持）
            content = self._remove_gradients(content)

            # 2. 嵌入图标
            content = self._embed_icons(content)

            # 3. 嵌入图片
            content = self._embed_images(content)

            # 4. 扁平化文本
            content = self._flatten_tspan(content)

            # 5. 转换圆角矩形
            content = self._convert_rounded_rect(content)

            # 保存到final目录
            output_path = self.svg_final_dir / svg_path.name
            output_path.write_text(content, encoding='utf-8')

            return output_path

        except Exception as e:
            print(f"[ERROR] Process failed {svg_path.name}: {e}")
            return None

    def _remove_gradients(self, content: str) -> str:
        """
        移除linearGradient元素，将gradient fill替换为纯色。
        ppt-master的svg_to_pptx不支持gradient，需要移除。
        """
        # 提取所有linearGradient定义
        gradient_pattern = r'<linearGradient[^>]*>(.*?)</linearGradient>'
        gradients = re.findall(gradient_pattern, content, re.DOTALL)

        # 提取gradient的颜色（使用第一个stop的颜色）
        gradient_colors = {}
        for gradient_content in gradients:
            # 提取id
            id_match = re.search(r'id="([^"]*)"', gradient_content)
            if id_match:
                gradient_id = id_match.group(1)
                # 提取第一个stop的颜色
                stop_match = re.search(r'<stop[^>]*stop-color="([^"]*)"', gradient_content)
                if stop_match:
                    gradient_colors[gradient_id] = stop_match.group(1)

        # 移除linearGradient定义
        content = re.sub(r'<linearGradient[^>]*>.*?</linearGradient>', '', content, flags=re.DOTALL)

        # 将url(#gradient-id)替换为纯色
        for gradient_id, color in gradient_colors.items():
            content = content.replace(f'url(#{gradient_id})', color)

        return content

    def _embed_icons(self, content: str) -> str:
        """嵌入图标（替换 <use data-icon="..."/>）"""
        # 匹配 <use data-icon="icon_name"/>
        pattern = r'<use\s+[^>]*data-icon="([^"]*)"[^>]*/>'

        def replace_icon(match):
            icon_name = match.group(1)
            icon_path = self._find_icon(icon_name)

            if icon_path and icon_path.exists():
                # 读取图标SVG
                icon_svg = icon_path.read_text(encoding='utf-8')
                # 提取<path>内容
                paths = re.findall(r'<path[^>]*/>', icon_svg)
                return ' '.join(paths)

            # 找不到图标，保留原样
            return match.group(0)

        return re.sub(pattern, replace_icon, content)

    def _find_icon(self, icon_name: str) -> Optional[Path]:
        """查找图标文件"""
        # 在项目的templates/icons目录查找
        icons_dir = self.project_path.parent.parent / 'ppt-master' / 'skills' / 'ppt-master' / 'templates' / 'icons'

        if not icons_dir.exists():
            return None

        # 搜索所有子目录
        for icon_file in icons_dir.rglob(f'{icon_name}.svg'):
            return icon_file

        return None

    def _embed_images(self, content: str) -> str:
        """嵌入图片（Base64编码）"""
        # 匹配 <image href="..."/>
        pattern = r'<image\s+[^>]*href="([^"]*)"[^>]*/>'

        def replace_image(match):
            href = match.group(1)

            # 如果已经是Base64，跳过
            if href.startswith('data:'):
                return match.group(0)

            # 查找图片文件
            img_path = self.images_dir / href
            if not img_path.exists():
                # 尝试相对路径
                img_path = self.project_path / href

            if img_path.exists():
                # 读取图片并转为Base64
                img_data = img_path.read_bytes()
                ext = img_path.suffix.lower()
                mime = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp',
                    '.svg': 'image/svg+xml'
                }.get(ext, 'image/png')

                b64 = base64.b64encode(img_data).decode('utf-8')
                data_uri = f'data:{mime};base64,{b64}'

                # 替换href
                return match.group(0).replace(f'href="{href}"', f'href="{data_uri}"')

            return match.group(0)

        return re.sub(pattern, replace_image, content)

    def _flatten_tspan(self, content: str) -> str:
        """扁平化文本（<tspan> 转独立 <text>）"""
        try:
            # 解析XML
            root = ET.fromstring(content)
            ns = {'svg': 'http://www.w3.org/2000/svg'}

            # 查找所有包含tspan的text元素
            for text_elem in root.findall('.//svg:text', ns):
                tspan_elems = text_elem.findall('svg:tspan', ns)

                if tspan_elems:
                    # 获取父text的属性
                    x = text_elem.get('x', '0')
                    y = text_elem.get('y', '0')
                    fill = text_elem.get('fill', '#000000')
                    font_family = text_elem.get('font-family', 'Arial')
                    font_size = text_elem.get('font-size', '18')

                    # 替换tspan为独立的text
                    parent = text_elem.getparent()
                    if parent is None:
                        continue

                    # 移除原始text
                    parent.remove(text_elem)

                    # 添加新的text元素
                    for i, tspan in enumerate(tspan_elems):
                        new_text = ET.SubElement(parent, '{http://www.w3.org/2000/svg}text')
                        new_text.set('x', tspan.get('x', x))
                        new_text.set('y', tspan.get('y', str(int(y) + i * int(font_size) * 1.5)))
                        new_text.set('fill', tspan.get('fill', fill))
                        new_text.set('font-family', tspan.get('font-family', font_family))
                        new_text.set('font-size', tspan.get('font-size', font_size))
                        new_text.text = tspan.text

            return ET.tostring(root, encoding='unicode')

        except Exception:
            # 如果解析失败，返回原内容
            return content

    def _convert_rounded_rect(self, content: str) -> str:
        """转换圆角矩形（<rect rx="..."/> 转 <path>）"""
        pattern = r'<rect\s+x="(\d+)"\s+y="(\d+)"\s+width="(\d+)"\s+height="(\d+)"\s+rx="(\d+)"([^/]*)/?>'

        def convert_rect(match):
            x, y, w, h, r = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4)), int(match.group(5))
            attrs = match.group(6)

            # 生成圆角矩形路径
            d = f'M {x+r},{y} L {x+w-r},{y} Q {x+w},{y} {x+w},{y+r} L {x+w},{y+h-r} Q {x+w},{y+h} {x+w-r},{y+h} L {x+r},{y+h} Q {x},{y+h} {x},{y+h-r} L {x},{y+r} Q {x},{y} {x+r},{y} Z'

            return f'<path d="{d}"{attrs}/>'

        return re.sub(pattern, convert_rect, content)


def finalize_svg(project_path: str) -> List[Path]:
    """
    后处理SVG文件（便捷函数）

    参数:
        project_path: 项目路径

    返回:
        处理后的文件路径列表
    """
    finalizer = SVGFinalizer(project_path)
    return finalizer.process_all()
