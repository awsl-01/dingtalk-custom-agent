"""
PPT Engine - SVG到DrawingML转换器

将SVG元素转换为PowerPoint的DrawingML格式。
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from xml.etree import ElementTree as ET


class SVGToDrawingMLConverter:
    """SVG到DrawingML转换器"""

    def __init__(self, slide_width: int = 1920, slide_height: int = 1080):
        """
        初始化转换器

        参数:
            slide_width: 幻灯片宽度（EMU）
            slide_height: 幻灯片高度（EMU）
        """
        self.slide_width = slide_width
        self.slide_height = slide_height

    def convert_svg_file(self, svg_path: str) -> Dict[str, Any]:
        """
        转换SVG文件

        参数:
            svg_path: SVG文件路径

        返回:
            转换结果字典
        """
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()

            # 解析viewBox
            viewBox = root.get('viewBox', '0 0 1920 1080')
            parts = viewBox.split()
            svg_width = int(parts[2])
            svg_height = int(parts[3])

            # 提取元素
            elements = self._extract_elements(root)

            return {
                'success': True,
                'width': svg_width,
                'height': svg_height,
                'elements': elements
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _extract_elements(self, root: ET.Element) -> List[Dict[str, Any]]:
        """提取SVG元素"""
        elements = []

        for elem in root:
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

            if tag == 'rect':
                elements.append(self._parse_rect(elem))
            elif tag == 'text':
                elements.append(self._parse_text(elem))
            elif tag == 'line':
                elements.append(self._parse_line(elem))
            elif tag == 'circle':
                elements.append(self._parse_circle(elem))
            elif tag == 'ellipse':
                elements.append(self._parse_ellipse(elem))
            elif tag == 'path':
                elements.append(self._parse_path(elem))
            elif tag == 'g':
                # 递归解析分组
                children = self._extract_elements(elem)
                group_id = elem.get('id', '')
                elements.append({
                    'type': 'group',
                    'id': group_id,
                    'children': children
                })

        return elements

    def _parse_rect(self, elem: ET.Element) -> Dict[str, Any]:
        """解析矩形"""
        return {
            'type': 'rect',
            'x': self._parse_number(elem.get('x', '0')),
            'y': self._parse_number(elem.get('y', '0')),
            'width': self._parse_number(elem.get('width', '0')),
            'height': self._parse_number(elem.get('height', '0')),
            'rx': self._parse_number(elem.get('rx', '0')),
            'ry': self._parse_number(elem.get('ry', '0')),
            'fill': elem.get('fill', 'none'),
            'stroke': elem.get('stroke', 'none'),
            'stroke-width': self._parse_number(elem.get('stroke-width', '1'))
        }

    def _parse_text(self, elem: ET.Element) -> Dict[str, Any]:
        """解析文本"""
        return {
            'type': 'text',
            'x': self._parse_number(elem.get('x', '0')),
            'y': self._parse_number(elem.get('y', '0')),
            'text': elem.text or '',
            'font-family': elem.get('font-family', 'Arial'),
            'font-size': self._parse_number(elem.get('font-size', '18')),
            'font-weight': elem.get('font-weight', 'normal'),
            'fill': elem.get('fill', '#000000'),
            'text-anchor': elem.get('text-anchor', 'start')
        }

    def _parse_line(self, elem: ET.Element) -> Dict[str, Any]:
        """解析线条"""
        return {
            'type': 'line',
            'x1': self._parse_number(elem.get('x1', '0')),
            'y1': self._parse_number(elem.get('y1', '0')),
            'x2': self._parse_number(elem.get('x2', '0')),
            'y2': self._parse_number(elem.get('y2', '0')),
            'stroke': elem.get('stroke', '#000000'),
            'stroke-width': self._parse_number(elem.get('stroke-width', '1'))
        }

    def _parse_circle(self, elem: ET.Element) -> Dict[str, Any]:
        """解析圆形"""
        return {
            'type': 'circle',
            'cx': self._parse_number(elem.get('cx', '0')),
            'cy': self._parse_number(elem.get('cy', '0')),
            'r': self._parse_number(elem.get('r', '0')),
            'fill': elem.get('fill', 'none'),
            'stroke': elem.get('stroke', 'none')
        }

    def _parse_ellipse(self, elem: ET.Element) -> Dict[str, Any]:
        """解析椭圆"""
        return {
            'type': 'ellipse',
            'cx': self._parse_number(elem.get('cx', '0')),
            'cy': self._parse_number(elem.get('cy', '0')),
            'rx': self._parse_number(elem.get('rx', '0')),
            'ry': self._parse_number(elem.get('ry', '0')),
            'fill': elem.get('fill', 'none'),
            'stroke': elem.get('stroke', 'none')
        }

    def _parse_path(self, elem: ET.Element) -> Dict[str, Any]:
        """解析路径"""
        return {
            'type': 'path',
            'd': elem.get('d', ''),
            'fill': elem.get('fill', 'none'),
            'stroke': elem.get('stroke', 'none'),
            'stroke-width': self._parse_number(elem.get('stroke-width', '1'))
        }

    def _parse_number(self, value: str) -> float:
        """解析数值"""
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
