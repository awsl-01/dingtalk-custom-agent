"""
PPT Engine - 设计规范模块

管理设计规范和执行锁定文件。
"""

from .strategist import Strategist, DesignSpec
from .spec_lock_generator import SpecLockGenerator

__all__ = ['Strategist', 'DesignSpec', 'SpecLockGenerator']
