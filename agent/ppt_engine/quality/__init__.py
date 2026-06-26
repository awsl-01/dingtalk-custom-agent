"""
PPT Engine - 质量检查模块

检查SVG文件是否符合项目技术规范。
"""

from .svg_quality_checker import SVGQualityChecker, QualityIssue

__all__ = ['SVGQualityChecker', 'QualityIssue']
