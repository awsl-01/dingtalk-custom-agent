"""
PPT Engine - DOCX转换器

使用mammoth将DOCX转换为Markdown，保留格式和图片。
支持Word文档（.docx）、旧版Word（.doc通过pandoc）、
OpenDocument（.odt）、RTF、EPUB等格式。
"""

import re
import base64
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any

from .base_converter import BaseConverter, ConversionResult

# 检查依赖
try:
    import mammoth
    MAMMOTH_AVAILABLE = True
except ImportError:
    MAMMOTH_AVAILABLE = False

try:
    from ebooklib import epub
    EBOOKLIB_AVAILABLE = True
except ImportError:
    EBOOKLIB_AVAILABLE = False

try:
    from markdownify import markdownify as md
    MARKDOWNIFY_AVAILABLE = True
except ImportError:
    MARKDOWNIFY_AVAILABLE = False


# 原生支持的格式
NATIVE_FORMATS = {'.docx', '.html', '.htm', '.epub', '.ipynb'}

# 需要pandoc的格式
PANDOC_FORMATS = {
    '.doc': 'doc',
    '.odt': 'odt',
    '.rtf': 'rtf',
    '.tex': 'latex',
    '.latex': 'latex',
    '.rst': 'rst',
    '.org': 'org',
    '.typ': 'typst'
}


class DocxConverter(BaseConverter):
    """DOCX转换器"""

    @property
    def supported_extensions(self) -> List[str]:
        return list(NATIVE_FORMATS) + list(PANDOC_FORMATS.keys())

    @property
    def format_name(self) -> str:
        ext = self.input_path.suffix.lower()
        if ext == '.docx':
            return 'Word文档'
        elif ext == '.epub':
            return '电子书'
        elif ext in PANDOC_FORMATS:
            return f'{ext[1:].upper()}文档'
        return '文档'

    def _convert_docx(self) -> ConversionResult:
        """转换DOCX文件"""
        if not MAMMOTH_AVAILABLE:
            return ConversionResult(
                success=False,
                markdown='',
                images=[],
                metadata=self._extract_metadata(),
                error="mammoth未安装，请运行: pip install mammoth"
            )

        try:
            # 提取图片
            images = []
            image_map = {}

            def handle_image(image):
                """处理图片回调"""
                # 生成图片文件名
                img_idx = len(images) + 1
                ext = image.content_type.split('/')[-1]
                if ext == 'jpeg':
                    ext = 'jpg'
                img_name = f"image_{img_idx}.{ext}"
                img_path = self.images_dir / img_name

                # 保存图片
                img_path.write_bytes(image.open().read())
                images.append(img_path)

                # 返回相对路径
                rel_path = img_path.relative_to(self.output_dir)
                return {'src': str(rel_path)}

            # 转换文档
            with open(self.input_path, 'rb') as docx_file:
                result = mammoth.convert_to_markdown(
                    docx_file,
                    convert_image=mammoth.images.img_element(handle_image)
                )

            markdown = result.value

            # 转换警告
            if result.messages:
                for msg in result.messages:
                    print(f"[WARN] {msg}")

            markdown = self._clean_text(markdown)

            metadata = self._extract_metadata()
            metadata['image_count'] = len(images)

            return ConversionResult(
                success=True,
                markdown=markdown,
                images=images,
                metadata=metadata
            )

        except Exception as e:
            return ConversionResult(
                success=False,
                markdown='',
                images=[],
                metadata=self._extract_metadata(),
                error=f"DOCX转换失败: {str(e)}"
            )

    def _convert_epub(self) -> ConversionResult:
        """转换EPUB文件"""
        if not EBOOKLIB_AVAILABLE:
            return ConversionResult(
                success=False,
                markdown='',
                images=[],
                metadata=self._extract_metadata(),
                error="ebooklib未安装，请运行: pip install ebooklib"
            )

        try:
            book = epub.read_epub(str(self.input_path))

            # 提取文本
            chapters = []
            for item in book.get_items():
                if item.get_type() == 9:  # ITEM_DOCUMENT
                    content = item.get_content().decode('utf-8')
                    if MARKDOWNIFY_AVAILABLE:
                        md_content = md(content, heading_style="ATX")
                    else:
                        # 简单HTML清理
                        md_content = re.sub(r'<[^>]+>', '', content)
                    chapters.append(md_content)

            # 提取图片
            images = []
            for item in book.get_items():
                if item.get_type() == 3:  # ITEM_IMAGE
                    img_name = item.get_name()
                    img_path = self.images_dir / img_name
                    img_path.parent.mkdir(parents=True, exist_ok=True)
                    img_path.write_bytes(item.get_content())
                    images.append(img_path)

            markdown = "\n\n---\n\n".join(chapters)
            markdown = self._clean_text(markdown)

            metadata = self._extract_metadata()
            metadata['image_count'] = len(images)
            metadata['title'] = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else None

            return ConversionResult(
                success=True,
                markdown=markdown,
                images=images,
                metadata=metadata
            )

        except Exception as e:
            return ConversionResult(
                success=False,
                markdown='',
                images=[],
                metadata=self._extract_metadata(),
                error=f"EPUB转换失败: {str(e)}"
            )

    def _convert_with_pandoc(self) -> ConversionResult:
        """使用pandoc转换"""
        pandoc_format = PANDOC_FORMATS.get(self.input_path.suffix.lower())
        if not pandoc_format:
            return ConversionResult(
                success=False,
                markdown='',
                images=[],
                metadata=self._extract_metadata(),
                error=f"不支持的格式: {self.input_path.suffix}"
            )

        # 检查pandoc是否可用
        if not shutil.which('pandoc'):
            return ConversionResult(
                success=False,
                markdown='',
                images=[],
                metadata=self._extract_metadata(),
                error="pandoc未安装，请访问 https://pandoc.org/installing.html 安装"
            )

        try:
            # 生成输出路径
            md_path = self.output_dir / f"{self.input_path.stem}.md"

            # 构建pandoc命令
            cmd = [
                'pandoc',
                str(self.input_path),
                '-f', pandoc_format,
                '-t', 'markdown',
                '-o', str(md_path),
                '--extract-media', str(self.images_dir)
            ]

            # 执行转换
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                return ConversionResult(
                    success=False,
                    markdown='',
                    images=[],
                    metadata=self._extract_metadata(),
                    error=f"pandoc转换失败: {result.stderr}"
                )

            # 读取生成的Markdown
            markdown = md_path.read_text(encoding='utf-8')
            markdown = self._clean_text(markdown)

            # 收集图片
            images = list(self.images_dir.rglob('*'))
            images = [img for img in images if img.is_file() and img.suffix.lower() in {'.png', '.jpg', '.jpeg', '.gif', '.webp'}]

            metadata = self._extract_metadata()
            metadata['image_count'] = len(images)

            return ConversionResult(
                success=True,
                markdown=markdown,
                images=images,
                metadata=metadata
            )

        except Exception as e:
            return ConversionResult(
                success=False,
                markdown='',
                images=[],
                metadata=self._extract_metadata(),
                error=f"pandoc转换失败: {str(e)}"
            )

    def _do_convert(self) -> ConversionResult:
        """执行转换"""
        ext = self.input_path.suffix.lower()

        # 原生格式
        if ext == '.docx':
            return self._convert_docx()
        elif ext == '.epub':
            return self._convert_epub()
        elif ext in {'.html', '.htm'}:
            return self._convert_html()
        elif ext == '.ipynb':
            return self._convert_notebook()

        # pandoc格式
        elif ext in PANDOC_FORMATS:
            return self._convert_with_pandoc()

        else:
            return ConversionResult(
                success=False,
                markdown='',
                images=[],
                metadata=self._extract_metadata(),
                error=f"不支持的格式: {ext}"
            )

    def _convert_html(self) -> ConversionResult:
        """转换HTML文件"""
        try:
            content = self.input_path.read_text(encoding='utf-8')

            if MARKDOWNIFY_AVAILABLE:
                markdown = md(content, heading_style="ATX")
            else:
                # 简单HTML清理
                markdown = re.sub(r'<[^>]+>', '', content)

            markdown = self._clean_text(markdown)

            return ConversionResult(
                success=True,
                markdown=markdown,
                images=[],
                metadata=self._extract_metadata()
            )

        except Exception as e:
            return ConversionResult(
                success=False,
                markdown='',
                images=[],
                metadata=self._extract_metadata(),
                error=f"HTML转换失败: {str(e)}"
            )

    def _convert_notebook(self) -> ConversionResult:
        """转换Jupyter Notebook"""
        try:
            import json

            content = self.input_path.read_text(encoding='utf-8')
            notebook = json.loads(content)

            cells = []
            for cell in notebook.get('cells', []):
                cell_type = cell.get('cell_type', '')
                source = ''.join(cell.get('source', []))

                if cell_type == 'markdown':
                    cells.append(source)
                elif cell_type == 'code':
                    cells.append(f"```python\n{source}\n```")

            markdown = "\n\n---\n\n".join(cells)
            markdown = self._clean_text(markdown)

            return ConversionResult(
                success=True,
                markdown=markdown,
                images=[],
                metadata=self._extract_metadata()
            )

        except Exception as e:
            return ConversionResult(
                success=False,
                markdown='',
                images=[],
                metadata=self._extract_metadata(),
                error=f"Notebook转换失败: {str(e)}"
            )


def convert_docx(input_path: str, output_dir: str = None) -> ConversionResult:
    """
    转换DOCX文件为Markdown

    参数:
        input_path: DOCX文件路径
        output_dir: 输出目录

    返回:
        ConversionResult 对象
    """
    converter = DocxConverter(input_path, output_dir)
    return converter.convert()
