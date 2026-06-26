"""
PPT Engine - 源文件处理模块

支持格式：
- PDF → PyMuPDF
- DOCX → mammoth
- HTML → markdownify + BeautifulSoup
- EPUB → ebooklib
- Excel → openpyxl
- Web → requests/curl_cffi
"""

from .pdf_converter import PDFConverter
from .docx_converter import DocxConverter
from .html_converter import HTMLConverter
from .excel_converter import ExcelConverter
from .web_converter import WebConverter
from .source_to_md import SourceToMarkdown, convert_source

__all__ = [
    'PDFConverter',
    'DocxConverter',
    'HTMLConverter',
    'ExcelConverter',
    'WebConverter',
    'SourceToMarkdown',
    'convert_source'
]
