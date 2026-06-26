"""
PPT Engine - 源文件转换器基类
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConversionResult:
    """转换结果"""
    success: bool
    markdown: str
    images: List[Path]
    metadata: Dict[str, Any]
    error: Optional[str] = None

    @property
    def has_content(self) -> bool:
        return bool(self.markdown.strip())

    @property
    def image_count(self) -> int:
        return len(self.images)


class BaseConverter(ABC):
    """源文件转换器基类"""

    def __init__(self, input_path: str, output_dir: str = None):
        """
        初始化转换器

        参数:
            input_path: 输入文件路径
            output_dir: 输出目录（默认为输入文件同目录）
        """
        self.input_path = Path(input_path)
        self.output_dir = Path(output_dir) if output_dir else self.input_path.parent

        if not self.input_path.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_path}")

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 创建图片目录
        self.images_dir = self.output_dir / f"{self.input_path.stem}_files"
        self.images_dir.mkdir(parents=True, exist_ok=True)

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """支持的文件扩展名"""
        pass

    @property
    @abstractmethod
    def format_name(self) -> str:
        """格式名称"""
        pass

    def can_convert(self) -> bool:
        """检查是否可以转换此文件"""
        return self.input_path.suffix.lower() in self.supported_extensions

    @abstractmethod
    def _do_convert(self) -> ConversionResult:
        """执行转换（子类实现）"""
        pass

    def convert(self) -> ConversionResult:
        """
        执行转换

        返回:
            ConversionResult 对象
        """
        if not self.can_convert():
            return ConversionResult(
                success=False,
                markdown='',
                images=[],
                metadata={},
                error=f"不支持的文件格式: {self.input_path.suffix}"
            )

        try:
            result = self._do_convert()

            # 保存Markdown文件
            if result.success and result.markdown:
                md_path = self.output_dir / f"{self.input_path.stem}.md"
                md_path.write_text(result.markdown, encoding='utf-8')
                print(f"[OK] Markdown saved: {md_path}")

            return result

        except Exception as e:
            return ConversionResult(
                success=False,
                markdown='',
                images=[],
                metadata={},
                error=str(e)
            )

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        import re

        # 移除控制字符
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)

        # 标准化换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # 移除多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 移除行尾空白
        text = '\n'.join(line.rstrip() for line in text.split('\n'))

        return text.strip()

    def _extract_metadata(self) -> Dict[str, Any]:
        """提取文件元数据"""
        stat = self.input_path.stat()
        return {
            'file_name': self.input_path.name,
            'file_size': stat.st_size,
            'file_type': self.format_name,
            'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'converted_at': datetime.now().isoformat()
        }
