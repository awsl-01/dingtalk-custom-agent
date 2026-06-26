"""
PPT Engine - SVG质量检查器

检查SVG文件是否符合项目技术规范。
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from xml.etree import ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum


class IssueLevel(Enum):
    """问题级别"""
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'


@dataclass
class QualityIssue:
    """质量问题"""
    level: IssueLevel
    file: str
    line: int
    message: str
    rule: str

    def __str__(self):
        return f"[{self.level.value.upper()}] {self.file}:{self.line} - {self.message} ({self.rule})"


class SVGQualityChecker:
    """SVG质量检查器"""

    # 禁止的SVG特性
    BANNED_FEATURES = [
        'xlink:href',  # 外部引用
        '<script>',    # JavaScript
        '<foreignObject>',  # 外部对象
    ]

    # 字号范围（相对于body字号的倍数）
    FONT_SIZE_MIN_RATIO = 0.5
    FONT_SIZE_MAX_RATIO = 5.0

    def __init__(self, spec_lock_path: str = None):
        """
        初始化检查器

        参数:
            spec_lock_path: spec_lock.md路径（用于检查颜色/字体漂移）
        """
        self.spec_lock_path = spec_lock_path
        self.spec_colors = set()
        self.spec_fonts = set()

        if spec_lock_path and Path(spec_lock_path).exists():
            self._load_spec_lock()

    def _load_spec_lock(self):
        """加载spec_lock规范"""
        try:
            content = Path(self.spec_lock_path).read_text(encoding='utf-8')

            # 提取颜色
            color_pattern = r'#[0-9A-Fa-f]{3,8}'
            self.spec_colors = set(re.findall(color_pattern, content))

            # 提取字体
            font_pattern = r'font-family[:\s]+([^;\n]+)'
            fonts = re.findall(font_pattern, content, re.IGNORECASE)
            for font in fonts:
                self.spec_fonts.update(f.strip().strip('"\'') for f in font.split(','))

        except Exception as e:
            print(f"[WARN] Load spec_lock failed: {e}")

    def check_svg(self, svg_path: str) -> List[QualityIssue]:
        """
        检查单个SVG文件

        参数:
            svg_path: SVG文件路径

        返回:
            问题列表
        """
        issues = []
        svg_path = Path(svg_path)

        if not svg_path.exists():
            issues.append(QualityIssue(
                level=IssueLevel.ERROR,
                file=str(svg_path),
                line=0,
                message="File not found",
                rule="file_exists"
            ))
            return issues

        try:
            content = svg_path.read_text(encoding='utf-8')
            tree = ET.parse(str(svg_path))
            root = tree.getroot()

            # 1. 检查viewBox
            issues.extend(self._check_viewbox(root, svg_path.name))

            # 2. 检查禁止特性
            issues.extend(self._check_banned_features(content, svg_path.name))

            # 3. 检查颜色漂移
            issues.extend(self._check_color_drift(content, svg_path.name))

            # 4. 检查字号范围
            issues.extend(self._check_font_sizes(root, svg_path.name))

            # 5. 检查动画分组
            issues.extend(self._check_animation_groups(root, svg_path.name))

            # 6. 检查图片引用
            issues.extend(self._check_image_refs(root, svg_path.name))

            # 7. 检查文本溢出
            issues.extend(self._check_text_overflow(root, svg_path.name))

        except ET.ParseError as e:
            issues.append(QualityIssue(
                level=IssueLevel.ERROR,
                file=str(svg_path),
                line=0,
                message=f"XML parse error: {e}",
                rule="xml_valid"
            ))
        except Exception as e:
            issues.append(QualityIssue(
                level=IssueLevel.ERROR,
                file=str(svg_path),
                line=0,
                message=f"Check failed: {e}",
                rule="check_error"
            ))

        return issues

    def check_directory(self, svg_dir: str) -> List[QualityIssue]:
        """
        检查目录下所有SVG文件

        参数:
            svg_dir: SVG目录路径

        返回:
            问题列表
        """
        issues = []
        svg_dir = Path(svg_dir)

        if not svg_dir.exists():
            issues.append(QualityIssue(
                level=IssueLevel.ERROR,
                file=str(svg_dir),
                line=0,
                message="Directory not found",
                rule="dir_exists"
            ))
            return issues

        svg_files = sorted(svg_dir.glob('*.svg'))
        if not svg_files:
            issues.append(QualityIssue(
                level=IssueLevel.WARNING,
                file=str(svg_dir),
                line=0,
                message="No SVG files found",
                rule="svg_files_exist"
            ))
            return issues

        for svg_file in svg_files:
            file_issues = self.check_svg(str(svg_file))
            issues.extend(file_issues)

        return issues

    def _check_viewbox(self, root: ET.Element, filename: str) -> List[QualityIssue]:
        """检查viewBox"""
        issues = []

        viewBox = root.get('viewBox')
        if not viewBox:
            issues.append(QualityIssue(
                level=IssueLevel.ERROR,
                file=filename,
                line=0,
                message="Missing viewBox attribute",
                rule="viewbox_required"
            ))
        else:
            parts = viewBox.split()
            if len(parts) != 4:
                issues.append(QualityIssue(
                    level=IssueLevel.ERROR,
                    file=filename,
                    line=0,
                    message=f"Invalid viewBox format: {viewBox}",
                    rule="viewbox_format"
                ))

        return issues

    def _check_banned_features(self, content: str, filename: str) -> List[QualityIssue]:
        """检查禁止的SVG特性"""
        issues = []

        for feature in self.BANNED_FEATURES:
            if feature in content:
                issues.append(QualityIssue(
                    level=IssueLevel.ERROR,
                    file=filename,
                    line=0,
                    message=f"Banned feature found: {feature}",
                    rule="banned_feature"
                ))

        return issues

    def _check_color_drift(self, content: str, filename: str) -> List[QualityIssue]:
        """检查颜色漂移"""
        issues = []

        if not self.spec_colors:
            return issues

        # 提取SVG中的颜色
        color_pattern = r'#[0-9A-Fa-f]{3,8}'
        svg_colors = set(re.findall(color_pattern, content))

        # 检查是否有未在规范中定义的颜色
        unknown_colors = svg_colors - self.spec_colors
        if unknown_colors:
            issues.append(QualityIssue(
                level=IssueLevel.WARNING,
                file=filename,
                line=0,
                message=f"Undefined colors: {', '.join(unknown_colors)}",
                rule="color_drift"
            ))

        return issues

    def _check_font_sizes(self, root: ET.Element, filename: str) -> List[QualityIssue]:
        """检查字号范围"""
        issues = []

        # 查找所有text元素
        for elem in root.iter():
            if elem.tag.endswith('}text') or elem.tag == 'text':
                font_size = elem.get('font-size')
                if font_size:
                    try:
                        size = float(font_size.replace('px', '').replace('pt', ''))
                        # 假设body字号为18px
                        body_size = 18
                        ratio = size / body_size

                        if ratio < self.FONT_SIZE_MIN_RATIO or ratio > self.FONT_SIZE_MAX_RATIO:
                            issues.append(QualityIssue(
                                level=IssueLevel.WARNING,
                                file=filename,
                                line=0,
                                message=f"Font size out of range: {font_size} (ratio: {ratio:.2f})",
                                rule="font_size_range"
                            ))
                    except ValueError:
                        pass

        return issues

    def _check_animation_groups(self, root: ET.Element, filename: str) -> List[QualityIssue]:
        """检查动画分组"""
        issues = []

        # 检查是否有分组ID
        groups = root.findall('.//{http://www.w3.org/2000/svg}g')
        if not groups:
            # SVG没有命名空间
            groups = root.findall('.//g')

        has_ids = False
        for g in groups:
            if g.get('id'):
                has_ids = True
                break

        if not has_ids:
            issues.append(QualityIssue(
                level=IssueLevel.INFO,
                file=filename,
                line=0,
                message="No group IDs found, animation effects may not apply",
                rule="animation_groups"
            ))

        return issues

    def _check_image_refs(self, root: ET.Element, filename: str) -> List[QualityIssue]:
        """检查图片引用"""
        issues = []

        # 查找所有image元素
        for elem in root.iter():
            if elem.tag.endswith('}image') or elem.tag == 'image':
                href = elem.get('href') or elem.get('{http://www.w3.org/1999/xlink}href')

                if not href:
                    issues.append(QualityIssue(
                        level=IssueLevel.WARNING,
                        file=filename,
                        line=0,
                        message="Image element without href",
                        rule="image_href"
                    ))
                elif href.startswith('http'):
                    issues.append(QualityIssue(
                        level=IssueLevel.WARNING,
                        file=filename,
                        line=0,
                        message=f"External image reference: {href[:50]}...",
                        rule="image_external"
                    ))

        return issues

    def _check_text_overflow(self, root: ET.Element, filename: str) -> List[QualityIssue]:
        """检查文本溢出"""
        issues = []

        # 获取viewBox尺寸
        viewBox = root.get('viewBox', '0 0 1920 1080')
        parts = viewBox.split()
        if len(parts) == 4:
            try:
                width = int(parts[2])
                height = int(parts[3])
            except ValueError:
                return issues
        else:
            return issues

        # 检查text元素位置
        for elem in root.iter():
            if elem.tag.endswith('}text') or elem.tag == 'text':
                x = float(elem.get('x', '0'))
                y = float(elem.get('y', '0'))

                if x > width or y > height:
                    issues.append(QualityIssue(
                        level=IssueLevel.WARNING,
                        file=filename,
                        line=0,
                        message=f"Text position ({x}, {y}) outside canvas ({width}x{height})",
                        rule="text_overflow"
                    ))

        return issues

    def get_summary(self, issues: List[QualityIssue]) -> Dict[str, Any]:
        """
        获取问题摘要

        参数:
            issues: 问题列表

        返回:
            摘要字典
        """
        summary = {
            'total': len(issues),
            'errors': sum(1 for i in issues if i.level == IssueLevel.ERROR),
            'warnings': sum(1 for i in issues if i.level == IssueLevel.WARNING),
            'info': sum(1 for i in issues if i.level == IssueLevel.INFO),
            'passed': sum(1 for i in issues if i.level == IssueLevel.ERROR) == 0
        }

        return summary
