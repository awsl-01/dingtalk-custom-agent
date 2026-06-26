"""
PPT Engine - PDF转换器

使用PyMuPDF提取PDF文本内容和图片，转换为Markdown格式。
支持标题检测、粗体/斜体、列表识别。
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import Counter

from .base_converter import BaseConverter, ConversionResult

# 检查PyMuPDF是否可用
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


# 字体大小阈值
FONT_BODY_SIZE = 12
FONT_H1_SIZE = 24
FONT_H2_SIZE = 18
FONT_H3_SIZE = 14

# 页眉页脚检测
HEADER_FOOTER_SAMPLE_LIMIT = 40
HEADER_FOOTER_EDGE_SAMPLE_SIZE = 20


class PDFConverter(BaseConverter):
    """PDF转换器"""

    @property
    def supported_extensions(self) -> List[str]:
        return ['.pdf']

    @property
    def format_name(self) -> str:
        return 'PDF'

    def _analyze_font_sizes(self, doc: 'fitz.Document') -> Dict[str, float]:
        """分析字体大小分布，推断标题级别"""
        size_counter = Counter()

        for page in doc:
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block["type"] == 0:  # 文本块
                    for line in block["lines"]:
                        for span in line["spans"]:
                            size = round(span["size"], 1)
                            text = span["text"].strip()
                            if text:
                                size_counter[size] += len(text)

        if not size_counter:
            return {
                "body": FONT_BODY_SIZE,
                "h1": FONT_H1_SIZE,
                "h2": FONT_H2_SIZE,
                "h3": FONT_H3_SIZE,
            }

        # 找到最常见的字体大小作为正文
        body_size = size_counter.most_common(1)[0][0]

        # 根据正文大小推断标题大小
        h1_size = body_size * 2.0
        h2_size = body_size * 1.5
        h3_size = body_size * 1.2

        return {
            "body": body_size,
            "h1": h1_size,
            "h2": h2_size,
            "h3": h3_size,
        }

    def _detect_header_footer(self, doc: 'fitz.Document') -> Tuple[List[str], List[str]]:
        """检测页眉页脚"""
        headers = []
        footers = []

        # 采样前N页
        sample_pages = min(len(doc), HEADER_FOOTER_SAMPLE_LIMIT)

        for page_idx in range(sample_pages):
            page = doc[page_idx]
            blocks = page.get_text("dict")["blocks"]
            page_height = page.rect.height

            for block in blocks:
                if block["type"] == 0:
                    y_center = (block["bbox"][1] + block["bbox"][3]) / 2
                    text = " ".join(
                        span["text"]
                        for line in block["lines"]
                        for span in line["spans"]
                    ).strip()

                    if not text:
                        continue

                    # 页眉：页面顶部10%区域
                    if y_center < page_height * 0.1:
                        headers.append(text)
                    # 页脚：页面底部10%区域
                    elif y_center > page_height * 0.9:
                        footers.append(text)

        # 统计出现频率
        header_counts = Counter(headers)
        footer_counts = Counter(footers)

        # 返回出现超过50%采样页的文本
        common_headers = [
            text for text, count in header_counts.items()
            if count > sample_pages * 0.5
        ]
        common_footers = [
            text for text, count in footer_counts.items()
            if count > sample_pages * 0.5
        ]

        return common_headers, common_footers

    def _is_heading(self, span: Dict, font_sizes: Dict[str, float]) -> int:
        """判断是否为标题，返回标题级别（0表示不是标题）"""
        size = round(span["size"], 1)
        flags = span.get("flags", 0)

        # 检查是否为粗体
        is_bold = flags & 2 ** 4

        # 根据字体大小判断
        if size >= font_sizes["h1"]:
            return 1
        elif size >= font_sizes["h2"]:
            return 2
        elif size >= font_sizes["h3"] and is_bold:
            return 3

        return 0

    def _extract_page_text(self, page, font_sizes: Dict[str, float],
                           headers: List[str], footers: List[str]) -> str:
        """提取单页文本"""
        blocks = page.get_text("dict")["blocks"]
        lines = []

        for block in blocks:
            if block["type"] != 0:
                continue

            block_lines = []
            for line in block["lines"]:
                line_text = ""
                line_heading = 0

                for span in line["spans"]:
                    text = span["text"]
                    if not text.strip():
                        continue

                    # 检查是否为标题
                    heading_level = self._is_heading(span, font_sizes)
                    if heading_level > 0:
                        line_heading = heading_level

                    # 检查是否为粗体
                    flags = span.get("flags", 0)
                    is_bold = flags & 2 ** 4

                    if is_bold and not heading_level:
                        text = f"**{text}**"

                    # 检查是否为斜体
                    is_italic = flags & 2 ** 1
                    if is_italic:
                        text = f"*{text}*"

                    line_text += text

                if line_text.strip():
                    # 跳过页眉页脚
                    if line_text.strip() in headers or line_text.strip() in footers:
                        continue

                    # 添加标题标记
                    if line_heading:
                        prefix = "#" * line_heading
                        line_text = f"{prefix} {line_text.strip()}"

                    block_lines.append(line_text)

            if block_lines:
                lines.extend(block_lines)
                lines.append("")  # 块之间添加空行

        return "\n".join(lines)

    def _extract_images(self, doc: 'fitz.Document') -> List[Path]:
        """提取图片"""
        image_paths = []

        for page_idx, page in enumerate(doc):
            image_list = page.get_images()

            for img_idx, img in enumerate(image_list):
                xref = img[0]

                try:
                    # 提取图片
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # 生成文件名
                    image_name = f"page{page_idx + 1}_img{img_idx + 1}.{image_ext}"
                    image_path = self.images_dir / image_name

                    # 保存图片
                    image_path.write_bytes(image_bytes)
                    image_paths.append(image_path)

                except Exception as e:
                    print(f"[WARN] Extract image failed (page {page_idx + 1}, img {img_idx + 1}): {e}")

        return image_paths

    def _do_convert(self) -> ConversionResult:
        """执行PDF转换"""
        if not PYMUPDF_AVAILABLE:
            return ConversionResult(
                success=False,
                markdown='',
                images=[],
                metadata=self._extract_metadata(),
                error="PyMuPDF未安装，请运行: pip install PyMuPDF"
            )

        try:
            doc = fitz.open(str(self.input_path))

            # 分析字体大小
            font_sizes = self._analyze_font_sizes(doc)

            # 检测页眉页脚
            headers, footers = self._detect_header_footer(doc)

            # 提取文本
            all_text = []
            for page in doc:
                page_text = self._extract_page_text(page, font_sizes, headers, footers)
                if page_text.strip():
                    all_text.append(page_text)

            # 提取图片
            images = self._extract_images(doc)

            doc.close()

            # 合并文本
            markdown = "\n\n---\n\n".join(all_text)
            markdown = self._clean_text(markdown)

            # 添加图片引用
            if images:
                markdown += "\n\n## 图片\n\n"
                for img_path in images:
                    rel_path = img_path.relative_to(self.output_dir)
                    markdown += f"![{img_path.stem}]({rel_path})\n\n"

            # 更新元数据
            metadata = self._extract_metadata()
            metadata.update({
                'page_count': len(doc),
                'image_count': len(images)
            })

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
                error=f"PDF转换失败: {str(e)}"
            )


def convert_pdf(input_path: str, output_dir: str = None) -> ConversionResult:
    """
    转换PDF文件为Markdown

    参数:
        input_path: PDF文件路径
        output_dir: 输出目录

    返回:
        ConversionResult 对象
    """
    converter = PDFConverter(input_path, output_dir)
    return converter.convert()
