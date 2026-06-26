"""
PPT Engine - LaTeX公式渲染器

将LaTeX公式渲染为透明PNG图片。
支持多Provider fallback链。
"""

import re
import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# 检查PIL是否可用
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


@dataclass
class FormulaRequest:
    """公式渲染请求"""
    formula: str
    filename: str = ''
    background: str = 'transparent'  # transparent, white
    color: str = '#000000'
    dpi: int = 300

    def to_dict(self) -> Dict[str, Any]:
        return {
            'formula': self.formula,
            'filename': self.filename,
            'background': self.background,
            'color': self.color,
            'dpi': self.dpi
        }


@dataclass
class FormulaResult:
    """公式渲染结果"""
    success: bool
    image_path: Optional[str] = None
    image_data: Optional[bytes] = None
    provider: str = ''
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LaTeXRenderer:
    """LaTeX公式渲染器"""

    # Provider endpoints
    PROVIDERS = {
        'codecogs': 'https://latex.codecogs.com/png.image?',
        'quicklatex': 'https://quicklatex.com/latex3.f',
        'mathpad': 'https://mathpad.ai/api/v1/latex2image',
        'wikimedia_check': 'https://wikimedia.org/api/rest_v1/media/math/check',
        'wikimedia_render': 'https://wikimedia.org/api/rest_v1/media/math/render/png',
    }

    # 默认Provider顺序
    DEFAULT_PROVIDER_CHAIN = ['codecogs', 'quicklatex', 'mathpad', 'wikimedia']

    def __init__(self, provider_chain: List[str] = None):
        """
        初始化渲染器

        参数:
            provider_chain: Provider调用链
        """
        self.provider_chain = provider_chain or self.DEFAULT_PROVIDER_CHAIN

    def render(self, request: FormulaRequest, output_dir: str) -> FormulaResult:
        """
        渲染公式

        参数:
            request: 渲染请求
            output_dir: 输出目录

        返回:
            FormulaResult对象
        """
        # 生成文件名
        filename = request.filename or f"formula_{hash(request.formula) % 100000}.png"
        output_path = Path(output_dir) / filename

        # 尝试每个Provider
        for provider_name in self.provider_chain:
            try:
                print(f"[RENDER] Trying {provider_name}...")

                result = self._render_with_provider(
                    provider_name, request, output_path
                )

                if result.success:
                    print(f"[OK] Rendered with {provider_name}: {output_path}")
                    return result
                else:
                    print(f"[WARN] {provider_name} failed: {result.error}")

            except Exception as e:
                print(f"[WARN] {provider_name} error: {e}")

        return FormulaResult(
            success=False,
            error="All providers failed"
        )

    def _render_with_provider(self, provider_name: str, request: FormulaRequest,
                             output_path: Path) -> FormulaResult:
        """使用指定Provider渲染"""
        if provider_name == 'codecogs':
            return self._render_codecogs(request, output_path)
        elif provider_name == 'quicklatex':
            return self._render_quicklatex(request, output_path)
        elif provider_name == 'mathpad':
            return self._render_mathpad(request, output_path)
        elif provider_name == 'wikimedia':
            return self._render_wikimedia(request, output_path)
        else:
            return FormulaResult(success=False, error=f"Unknown provider: {provider_name}")

    def _render_codecogs(self, request: FormulaRequest, output_path: Path) -> FormulaResult:
        """使用codecogs渲染"""
        try:
            # 构建URL
            encoded_formula = urllib.parse.quote(request.formula)
            url = f"{self.PROVIDERS['codecogs']}{encoded_formula}"

            # 下载图片
            response = urllib.request.urlopen(url, timeout=30)
            image_data = response.read()

            # 保存图片
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(image_data)

            # 处理透明背景
            if request.background == 'transparent' and PIL_AVAILABLE:
                self._make_transparent(output_path, '#FFFFFF')

            return FormulaResult(
                success=True,
                image_path=str(output_path),
                image_data=image_data,
                provider='codecogs'
            )

        except Exception as e:
            return FormulaResult(success=False, provider='codecogs', error=str(e))

    def _render_quicklatex(self, request: FormulaRequest, output_path: Path) -> FormulaResult:
        """使用quicklatex渲染"""
        try:
            # 构建请求
            data = urllib.parse.urlencode({
                'formula': request.formula,
                'fsize': '17px',
                'fcolor': request.color.lstrip('#'),
                'mode': '0',
                'out': '1',
                'remhost': 'quicklatex.com'
            }).encode()

            req = urllib.request.Request(
                self.PROVIDERS['quicklatex'],
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            # 发送请求
            response = urllib.request.urlopen(req, timeout=30)
            result_text = response.read().decode('utf-8')

            # 解析结果
            lines = result_text.split('\n')
            if len(lines) > 1:
                image_url = lines[1].strip()

                # 下载图片
                img_response = urllib.request.urlopen(image_url, timeout=30)
                image_data = img_response.read()

                # 保存图片
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(image_data)

                # 处理透明背景
                if request.background == 'transparent' and PIL_AVAILABLE:
                    self._make_transparent(output_path, '#FFFFFF')

                return FormulaResult(
                    success=True,
                    image_path=str(output_path),
                    image_data=image_data,
                    provider='quicklatex'
                )
            else:
                return FormulaResult(success=False, provider='quicklatex', error="No image URL")

        except Exception as e:
            return FormulaResult(success=False, provider='quicklatex', error=str(e))

    def _render_mathpad(self, request: FormulaRequest, output_path: Path) -> FormulaResult:
        """使用mathpad渲染"""
        try:
            import json

            # 构建请求
            data = json.dumps({
                'latex': request.formula,
                'backgroundColor': 'transparent' if request.background == 'transparent' else '#FFFFFF',
                'textColor': request.color,
                'dpi': request.dpi
            }).encode()

            req = urllib.request.Request(
                self.PROVIDERS['mathpad'],
                data=data,
                headers={'Content-Type': 'application/json'}
            )

            # 发送请求
            response = urllib.request.urlopen(req, timeout=30)
            result = json.loads(response.read().decode('utf-8'))

            if 'imageUrl' in result:
                # 下载图片
                img_response = urllib.request.urlopen(result['imageUrl'], timeout=30)
                image_data = img_response.read()

                # 保存图片
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(image_data)

                return FormulaResult(
                    success=True,
                    image_path=str(output_path),
                    image_data=image_data,
                    provider='mathpad'
                )
            else:
                return FormulaResult(success=False, provider='mathpad', error="No image URL")

        except Exception as e:
            return FormulaResult(success=False, provider='mathpad', error=str(e))

    def _render_wikimedia(self, request: FormulaRequest, output_path: Path) -> FormulaResult:
        """使用wikimedia渲染"""
        try:
            # Step 1: 检查公式
            check_data = f'q={request.formula}&type=tex'.encode()
            check_req = urllib.request.Request(
                self.PROVIDERS['wikimedia_check'],
                data=check_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            check_response = urllib.request.urlopen(check_req, timeout=30)
            check_result = json.loads(check_response.read().decode('utf-8'))

            if 'hash' not in check_result:
                return FormulaResult(success=False, provider='wikimedia', error="Check failed")

            formula_hash = check_result['hash']

            # Step 2: 渲染公式
            render_url = f"{self.PROVIDERS['wikimedia_render']}/{formula_hash}"
            render_req = urllib.request.Request(render_url)
            render_response = urllib.request.urlopen(render_req, timeout=30)
            image_data = render_response.read()

            # 保存图片
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(image_data)

            # 处理透明背景
            if request.background == 'transparent' and PIL_AVAILABLE:
                self._make_transparent(output_path, '#FFFFFF')

            return FormulaResult(
                success=True,
                image_path=str(output_path),
                image_data=image_data,
                provider='wikimedia'
            )

        except Exception as e:
            return FormulaResult(success=False, provider='wikimedia', error=str(e))

    def _make_transparent(self, image_path: Path, bg_color: str):
        """将背景色设为透明"""
        if not PIL_AVAILABLE:
            return

        try:
            img = Image.open(image_path)
            img = img.convert('RGBA')

            # 获取背景色RGB
            bg_rgb = self._hex_to_rgb(bg_color)

            # 替换背景色为透明
            data = img.getdata()
            new_data = []
            for item in data:
                # 如果颜色接近背景色，设为透明
                if self._color_distance(item[:3], bg_rgb) < 50:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)

            img.putdata(new_data)
            img.save(image_path, 'PNG')

        except Exception as e:
            print(f"[WARN] Make transparent failed: {e}")

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """十六进制颜色转RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _color_distance(self, c1: tuple, c2: tuple) -> float:
        """计算颜色距离"""
        return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5

    def render_from_manifest(self, manifest_path: str, output_dir: str) -> List[FormulaResult]:
        """
        从manifest批量渲染公式

        参数:
            manifest_path: formula_manifest.json路径
            output_dir: 输出目录

        返回:
            FormulaResult列表
        """
        manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
        items = manifest.get('items', [])

        results = []
        for item in items:
            request = FormulaRequest(
                formula=item.get('formula', ''),
                filename=item.get('filename', ''),
                background=item.get('background', 'transparent'),
                color=item.get('color', '#000000'),
                dpi=item.get('dpi', 300)
            )

            result = self.render(request, output_dir)
            results.append(result)

        return results


def render_formula(formula: str, output_dir: str, filename: str = None) -> FormulaResult:
    """
    渲染公式（便捷函数）

    参数:
        formula: LaTeX公式
        output_dir: 输出目录
        filename: 输出文件名

    返回:
        FormulaResult对象
    """
    renderer = LaTeXRenderer()
    request = FormulaRequest(formula=formula, filename=filename)
    return renderer.render(request, output_dir)
