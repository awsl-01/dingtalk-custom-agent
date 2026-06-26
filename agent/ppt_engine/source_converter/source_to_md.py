"""
PPT Engine - 源文件转Markdown统一入口

自动识别文件格式并选择合适的转换器。

使用方式：
    python -m agent.ppt_engine.source_converter.source_to_md <input> [-o output_dir]
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .base_converter import ConversionResult
from .pdf_converter import PDFConverter
from .docx_converter import DocxConverter
from .html_converter import HTMLConverter
from .excel_converter import ExcelConverter
from .web_converter import WebConverter


# 转换器注册表
CONVERTERS = {
    '.pdf': PDFConverter,
    '.docx': DocxConverter,
    '.doc': DocxConverter,
    '.odt': DocxConverter,
    '.rtf': DocxConverter,
    '.epub': DocxConverter,
    '.html': HTMLConverter,
    '.htm': HTMLConverter,
    '.xlsx': ExcelConverter,
    '.xlsm': ExcelConverter,
    '.tex': DocxConverter,
    '.latex': DocxConverter,
    '.rst': DocxConverter,
    '.org': DocxConverter,
    '.typ': DocxConverter,
    '.ipynb': DocxConverter,
}


class SourceToMarkdown:
    """源文件转Markdown统一入口"""

    def __init__(self, output_dir: str = None):
        """
        初始化

        参数:
            output_dir: 输出目录（默认为输入文件同目录）
        """
        self.output_dir = output_dir

    def _is_url(self, path: str) -> bool:
        """检查是否为URL"""
        from urllib.parse import urlparse
        parsed = urlparse(path)
        return parsed.scheme in ('http', 'https') and bool(parsed.netloc)

    def _get_converter(self, input_path: str):
        """获取合适的转换器"""
        # URL
        if self._is_url(input_path):
            return WebConverter(input_path, self.output_dir)

        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {input_path}")

        ext = path.suffix.lower()
        converter_cls = CONVERTERS.get(ext)

        if not converter_cls:
            raise ValueError(f"不支持的文件格式: {ext}")

        return converter_cls(input_path, self.output_dir)

    def convert(self, input_path: str) -> ConversionResult:
        """
        转换文件

        参数:
            input_path: 输入文件路径或URL

        返回:
            ConversionResult 对象
        """
        try:
            converter = self._get_converter(input_path)
            return converter.convert()
        except Exception as e:
            return ConversionResult(
                success=False,
                markdown='',
                images=[],
                metadata={'file_name': Path(input_path).name},
                error=str(e)
            )

    def batch_convert(self, input_paths: List[str]) -> List[ConversionResult]:
        """
        批量转换

        参数:
            input_paths: 输入文件路径列表

        返回:
            ConversionResult 列表
        """
        results = []
        for path in input_paths:
            print(f"\n{'='*50}")
            print(f"[CONVERT] {path}")
            print('='*50)
            result = self.convert(path)
            results.append(result)

            if result.success:
                print(f"[OK] Conversion success")
                print(f"   Text length: {len(result.markdown)} chars")
                print(f"   Image count: {result.image_count}")
            else:
                print(f"[FAIL] Conversion failed: {result.error}")

        return results


def convert_source(input_path: str, output_dir: str = None) -> ConversionResult:
    """
    转换源文件为Markdown（便捷函数）

    参数:
        input_path: 输入文件路径或URL
        output_dir: 输出目录

    返回:
        ConversionResult 对象
    """
    converter = SourceToMarkdown(output_dir)
    return converter.convert(input_path)


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='源文件转Markdown')
    parser.add_argument('input', help='输入文件路径或URL')
    parser.add_argument('-o', '--output', help='输出目录')

    args = parser.parse_args()

    converter = SourceToMarkdown(args.output)
    result = converter.convert(args.input)

    if result.success:
        print(f"\n[OK] Conversion success!")
        print(f"   Text length: {len(result.markdown)} chars")
        print(f"   Image count: {result.image_count}")
        print(f"\n[PREVIEW]")
        print("-" * 50)
        # 显示前500字符
        preview = result.markdown[:500]
        if len(result.markdown) > 500:
            preview += "\n..."
        print(preview)
    else:
        print(f"\n[FAIL] Conversion failed: {result.error}")
        sys.exit(1)


if __name__ == '__main__':
    main()
