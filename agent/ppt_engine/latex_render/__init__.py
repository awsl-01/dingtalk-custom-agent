"""
PPT Engine - LaTeX公式渲染模块

多Provider fallback：
- codecogs (默认)
- quicklatex
- mathpad
- wikimedia (备用)
"""

from .latex_renderer import LaTeXRenderer, FormulaRequest, FormulaResult

__all__ = ['LaTeXRenderer', 'FormulaRequest', 'FormulaResult']
