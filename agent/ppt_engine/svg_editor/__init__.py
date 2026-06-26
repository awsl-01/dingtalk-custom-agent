"""
PPT Engine - 实时预览模块

Flask Web服务器，提供SVG实时预览和标注功能。
"""

from .server import create_app, run_server

__all__ = ['create_app', 'run_server']
