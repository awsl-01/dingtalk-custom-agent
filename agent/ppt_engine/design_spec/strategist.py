"""
PPT Engine - 设计策略师

生成设计规范（design_spec.md）和执行锁定（spec_lock.md）。
实现八项确认流程。
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ColorScheme:
    """颜色方案"""
    primary: str = '#1A1A1A'
    secondary: str = '#555555'
    accent: str = '#1976D2'
    background: str = '#FFFFFF'
    surface: str = '#F5F5F5'
    text: str = '#1A1A1A'
    text_secondary: str = '#666666'

    def to_dict(self) -> Dict[str, str]:
        return {
            'primary': self.primary,
            'secondary': self.secondary,
            'accent': self.accent,
            'background': self.background,
            'surface': self.surface,
            'text': self.text,
            'text_secondary': self.text_secondary
        }


@dataclass
class Typography:
    """字体方案"""
    title_font: str = 'Microsoft YaHei, SimHei, Arial, sans-serif'
    body_font: str = 'Microsoft YaHei, PingFang SC, Arial, sans-serif'
    title_size: int = 32
    subtitle_size: int = 24
    body_size: int = 18
    caption_size: int = 14

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title_font': self.title_font,
            'body_font': self.body_font,
            'title_size': self.title_size,
            'subtitle_size': self.subtitle_size,
            'body_size': self.body_size,
            'caption_size': self.caption_size
        }


@dataclass
class DesignSpec:
    """设计规范"""
    # 1. 画布格式
    canvas_format: str = 'ppt169'
    width: int = 1920
    height: int = 1080

    # 2. 页数范围
    page_count_min: int = 7
    page_count_max: int = 12

    # 3. 目标受众
    audience: str = 'general'
    audience_desc: str = '通用受众'

    # 4. 风格目标
    style: str = 'modern'
    style_desc: str = '现代简洁风格'

    # 5. 颜色方案
    colors: ColorScheme = field(default_factory=ColorScheme)

    # 6. 图标方案
    icon_style: str = 'outline'  # outline / filled / none
    icon_library: str = 'default'

    # 7. 字体方案
    typography: Typography = field(default_factory=Typography)
    formula_policy: str = 'mixed'  # mixed / render-all / text-only

    # 8. 图片方案
    image_style: str = 'photo'  # photo / illustration / none
    image_acquisition: str = 'ai'  # ai / web / user

    # 内容大纲
    title: str = ''
    subtitle: str = ''
    pages: List[Dict[str, Any]] = field(default_factory=list)

    # 元数据
    created_at: str = ''
    updated_at: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return {
            'canvas_format': self.canvas_format,
            'width': self.width,
            'height': self.height,
            'page_count_min': self.page_count_min,
            'page_count_max': self.page_count_max,
            'audience': self.audience,
            'audience_desc': self.audience_desc,
            'style': self.style,
            'style_desc': self.style_desc,
            'colors': self.colors.to_dict(),
            'icon_style': self.icon_style,
            'icon_library': self.icon_library,
            'typography': self.typography.to_dict(),
            'formula_policy': self.formula_policy,
            'image_style': self.image_style,
            'image_acquisition': self.image_acquisition,
            'title': self.title,
            'subtitle': self.subtitle,
            'pages': self.pages,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class Strategist:
    """设计策略师"""

    # 画布格式
    CANVAS_FORMATS = {
        'ppt169': {'name': 'PPT 16:9', 'width': 1920, 'height': 1080},
        'ppt43': {'name': 'PPT 4:3', 'width': 1440, 'height': 1080},
        'xhs': {'name': '小红书', 'width': 1080, 'height': 1440},
        'story': {'name': '故事', 'width': 1080, 'height': 1920}
    }

    # 预设颜色方案
    COLOR_PRESETS = {
        'modern': ColorScheme(primary='#1A1A1A', accent='#1976D2', background='#FFFFFF'),
        'warm': ColorScheme(primary='#5D4037', accent='#FF6F00', background='#FFF8E1'),
        'cool': ColorScheme(primary='#1A237E', accent='#00BCD4', background='#E8EAF6'),
        'nature': ColorScheme(primary='#1B5E20', accent='#4CAF50', background='#E8F5E9'),
        'elegant': ColorScheme(primary='#311B92', accent='#7C4DFF', background='#EDE7F6'),
        'education': ColorScheme(primary='#1565C0', accent='#FF6F00', background='#E3F2FD'),
        'corporate': ColorScheme(primary='#263238', accent='#FF6F00', background='#ECEFF1'),
        'creative': ColorScheme(primary='#880E4F', accent='#FF4081', background='#FCE4EC'),
    }

    # 预设字体方案
    TYPOGRAPHY_PRESETS = {
        'modern': Typography(
            title_font='Microsoft YaHei, SimHei, Arial, sans-serif',
            body_font='Microsoft YaHei, PingFang SC, Arial, sans-serif'
        ),
        'serif': Typography(
            title_font='STSong, SimSun, serif',
            body_font='STSong, SimSun, serif'
        ),
        'tech': Typography(
            title_font='Consolas, Microsoft YaHei, monospace',
            body_font='Microsoft YaHei, PingFang SC, Arial, sans-serif'
        ),
    }

    def __init__(self, project_path: str):
        """
        初始化策略师

        参数:
            project_path: 项目路径
        """
        self.project_path = Path(project_path)

    def create_design_spec(self, content: Dict[str, Any]) -> DesignSpec:
        """
        创建设计规范

        参数:
            content: 内容信息，包含:
                - title: 标题
                - subtitle: 副标题
                - subject: 学科（可选）
                - audience: 受众（可选）
                - style: 风格（可选）
                - pages: 页面列表（可选）

        返回:
            DesignSpec对象
        """
        spec = DesignSpec()

        # 设置时间
        now = datetime.now().isoformat()
        spec.created_at = now
        spec.updated_at = now

        # 设置标题
        spec.title = content.get('title', 'Untitled')
        spec.subtitle = content.get('subtitle', '')

        # 设置画布格式
        canvas_format = content.get('canvas_format', 'ppt169')
        if canvas_format in self.CANVAS_FORMATS:
            spec.canvas_format = canvas_format
            spec.width = self.CANVAS_FORMATS[canvas_format]['width']
            spec.height = self.CANVAS_FORMATS[canvas_format]['height']

        # 设置页数
        page_count = content.get('page_count', 10)
        spec.page_count_min = max(5, page_count - 3)
        spec.page_count_max = min(20, page_count + 3)

        # 设置受众
        spec.audience = content.get('audience', 'general')
        spec.audience_desc = self._get_audience_desc(spec.audience)

        # 设置风格
        style = content.get('style', 'modern')
        spec.style = style
        spec.style_desc = self._get_style_desc(style)

        # 设置颜色
        subject = content.get('subject', '')
        color_preset = content.get('color_preset') or self._get_subject_color(subject)
        if color_preset in self.COLOR_PRESETS:
            spec.colors = self.COLOR_PRESETS[color_preset]

        # 设置字体
        typo_preset = content.get('typography_preset', 'modern')
        if typo_preset in self.TYPOGRAPHY_PRESETS:
            spec.typography = self.TYPOGRAPHY_PRESETS[typo_preset]

        # 设置图标
        spec.icon_style = content.get('icon_style', 'outline')

        # 设置图片
        spec.image_style = content.get('image_style', 'photo')
        spec.image_acquisition = content.get('image_acquisition', 'ai')

        # 设置页面
        spec.pages = content.get('pages', [])

        return spec

    def _get_audience_desc(self, audience: str) -> str:
        """获取受众描述"""
        descriptions = {
            'general': '通用受众',
            'student': '学生',
            'teacher': '教师',
            'professional': '专业人士',
            'executive': '管理层',
            'children': '儿童',
        }
        return descriptions.get(audience, '通用受众')

    def _get_style_desc(self, style: str) -> str:
        """获取风格描述"""
        descriptions = {
            'modern': '现代简洁风格',
            'classic': '经典传统风格',
            'creative': '创意活泼风格',
            'professional': '专业商务风格',
            'minimalist': '极简风格',
            'education': '教育风格',
        }
        return descriptions.get(style, '现代简洁风格')

    def _get_subject_color(self, subject: str) -> str:
        """根据学科获取颜色方案"""
        subject_colors = {
            '数学': 'cool',
            '物理': 'cool',
            '化学': 'nature',
            '生物': 'nature',
            '语文': 'warm',
            '英语': 'modern',
            '历史': 'warm',
            '地理': 'nature',
            '信息技术': 'tech',
            '政治': 'elegant',
        }
        return subject_colors.get(subject, 'modern')

    def generate_design_spec_md(self, spec: DesignSpec) -> str:
        """
        生成design_spec.md内容

        参数:
            spec: 设计规范

        返回:
            Markdown内容
        """
        md = f"""# {spec.title}

{spec.subtitle}

## I. 画布格式

- 格式: {self.CANVAS_FORMATS[spec.canvas_format]['name']}
- 尺寸: {spec.width} x {spec.height}
- 比例: {spec.width}:{spec.height}

## II. 页数范围

- 最少: {spec.page_count_min} 页
- 最多: {spec.page_count_max} 页

## III. 目标受众

- 受众类型: {spec.audience_desc}
- 受众代码: {spec.audience}

## IV. 风格目标

- 风格: {spec.style_desc}
- 风格代码: {spec.style}

## V. 颜色方案

| 角色 | 颜色值 | 用途 |
|------|--------|------|
| Primary | `{spec.colors.primary}` | 主色调、标题 |
| Secondary | `{spec.colors.secondary}` | 次要文字 |
| Accent | `{spec.colors.accent}` | 强调色、按钮 |
| Background | `{spec.colors.background}` | 页面背景 |
| Surface | `{spec.colors.surface}` | 卡片背景 |
| Text | `{spec.colors.text}` | 正文文字 |
| Text Secondary | `{spec.colors.text_secondary}` | 辅助文字 |

## VI. 图标方案

- 风格: {spec.icon_style}
- 图标库: {spec.icon_library}

## VII. 字体方案

| 角色 | 字体 | 字号 |
|------|------|------|
| 标题 | {spec.typography.title_font} | {spec.typography.title_size}px |
| 副标题 | {spec.typography.title_font} | {spec.typography.subtitle_size}px |
| 正文 | {spec.typography.body_font} | {spec.typography.body_size}px |
| 注释 | {spec.typography.body_font} | {spec.typography.caption_size}px |

- 公式策略: {spec.formula_policy}

## VIII. 图片方案

- 图片风格: {spec.image_style}
- 获取方式: {spec.image_acquisition}

## IX. 内容大纲

"""
        # 添加页面列表
        if spec.pages:
            for i, page in enumerate(spec.pages, 1):
                title = page.get('title', f'Page {i}')
                layout = page.get('layout', 'content')
                md += f"{i}. **{title}** (layout: {layout})\n"
        else:
            md += "(待填充)\n"

        md += f"""
## X. 元数据

- 创建时间: {spec.created_at}
- 更新时间: {spec.updated_at}

---
*Generated by PPT Engine Strategist*
"""
        return md

    def save_design_spec(self, spec: DesignSpec) -> Path:
        """
        保存设计规范

        参数:
            spec: 设计规范

        返回:
            保存路径
        """
        md_content = self.generate_design_spec_md(spec)
        output_path = self.project_path / 'design_spec.md'
        output_path.write_text(md_content, encoding='utf-8')

        print(f"[OK] Design spec saved: {output_path}")
        return output_path


def create_design_spec(project_path: str, content: Dict[str, Any]) -> DesignSpec:
    """
    创建设计规范（便捷函数）

    参数:
        project_path: 项目路径
        content: 内容信息

    返回:
        DesignSpec对象
    """
    strategist = Strategist(project_path)
    spec = strategist.create_design_spec(content)
    strategist.save_design_spec(spec)
    return spec
