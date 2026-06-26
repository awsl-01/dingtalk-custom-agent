"""
PPT Engine - 品牌管理器

管理品牌标识配置：颜色/字体/Logo/语音/图标风格。
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Brand:
    """品牌配置"""
    id: str
    name: str
    description: str = ''

    # 颜色方案
    colors: Dict[str, str] = field(default_factory=lambda: {
        'primary': '#1A1A1A',
        'secondary': '#555555',
        'accent': '#1976D2',
        'background': '#FFFFFF',
        'surface': '#F5F5F5',
        'text': '#1A1A1A',
        'text_secondary': '#666666'
    })

    # 字体方案
    typography: Dict[str, Any] = field(default_factory=lambda: {
        'title_font': 'Microsoft YaHei, SimHei, Arial, sans-serif',
        'body_font': 'Microsoft YaHei, PingFang SC, Arial, sans-serif',
        'title_size': 32,
        'subtitle_size': 24,
        'body_size': 18,
        'caption_size': 14
    })

    # Logo
    logo_path: str = ''
    logo_width: int = 120
    logo_height: int = 40

    # 语音语调
    voice: str = 'professional'
    tone: str = 'formal'

    # 图标风格
    icon_style: str = 'outline'
    icon_library: str = 'default'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'colors': self.colors,
            'typography': self.typography,
            'logo_path': self.logo_path,
            'logo_width': self.logo_width,
            'logo_height': self.logo_height,
            'voice': self.voice,
            'tone': self.tone,
            'icon_style': self.icon_style,
            'icon_library': self.icon_library
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Brand':
        return cls(**data)


class BrandManager:
    """品牌管理器"""

    # 预设品牌
    PRESET_BRANDS = {
        'default': Brand(
            id='default',
            name='默认品牌',
            description='通用默认品牌配置',
            colors={
                'primary': '#1A1A1A',
                'secondary': '#555555',
                'accent': '#1976D2',
                'background': '#FFFFFF',
                'surface': '#F5F5F5',
                'text': '#1A1A1A',
                'text_secondary': '#666666'
            }
        ),
        'education': Brand(
            id='education',
            name='教育品牌',
            description='教育场景专用品牌',
            colors={
                'primary': '#1565C0',
                'secondary': '#42A5F5',
                'accent': '#FF6F00',
                'background': '#E3F2FD',
                'surface': '#FFFFFF',
                'text': '#1A1A1A',
                'text_secondary': '#666666'
            }
        ),
        'corporate': Brand(
            id='corporate',
            name='企业品牌',
            description='商务企业品牌',
            colors={
                'primary': '#263238',
                'secondary': '#546E7A',
                'accent': '#FF6F00',
                'background': '#ECEFF1',
                'surface': '#FFFFFF',
                'text': '#263238',
                'text_secondary': '#666666'
            }
        ),
        'creative': Brand(
            id='creative',
            name='创意品牌',
            description='创意活泼品牌',
            colors={
                'primary': '#880E4F',
                'secondary': '#AD1457',
                'accent': '#FF4081',
                'background': '#FCE4EC',
                'surface': '#FFFFFF',
                'text': '#880E4F',
                'text_secondary': '#666666'
            }
        ),
        'tech': Brand(
            id='tech',
            name='科技品牌',
            description='科技风格品牌',
            colors={
                'primary': '#0D1117',
                'secondary': '#161B22',
                'accent': '#00FF88',
                'background': '#0D1117',
                'surface': '#161B22',
                'text': '#E6EDF3',
                'text_secondary': '#8B949E'
            },
            typography={
                'title_font': 'Consolas, Microsoft YaHei, monospace',
                'body_font': 'Microsoft YaHei, PingFang SC, Arial, sans-serif',
                'title_size': 32,
                'subtitle_size': 24,
                'body_size': 18,
                'caption_size': 14
            }
        ),
    }

    # 学科品牌
    SUBJECT_BRANDS = {
        'math': Brand(
            id='math',
            name='数学',
            description='数学学科品牌',
            colors={
                'primary': '#1A5276',
                'secondary': '#2980B9',
                'accent': '#E74C3C',
                'background': '#F0F5FB',
                'surface': '#FFFFFF',
                'text': '#1A1A1A',
                'text_secondary': '#555555'
            }
        ),
        'physics': Brand(
            id='physics',
            name='物理',
            description='物理学科品牌',
            colors={
                'primary': '#1B4F72',
                'secondary': '#2E86C1',
                'accent': '#48C9B0',
                'background': '#EBF2F8',
                'surface': '#FFFFFF',
                'text': '#1A1A1A',
                'text_secondary': '#555555'
            }
        ),
        'chemistry': Brand(
            id='chemistry',
            name='化学',
            description='化学学科品牌',
            colors={
                'primary': '#6C3483',
                'secondary': '#8E44AD',
                'accent': '#EC7063',
                'background': '#F3EDFA',
                'surface': '#FFFFFF',
                'text': '#1A1A1A',
                'text_secondary': '#555555'
            }
        ),
        'biology': Brand(
            id='biology',
            name='生物',
            description='生物学科品牌',
            colors={
                'primary': '#1E8449',
                'secondary': '#27AE60',
                'accent': '#F0B27A',
                'background': '#EAF7EA',
                'surface': '#FFFFFF',
                'text': '#1A1A1A',
                'text_secondary': '#555555'
            }
        ),
        'chinese': Brand(
            id='chinese',
            name='语文',
            description='语文学科品牌',
            colors={
                'primary': '#7B5B3A',
                'secondary': '#A0522D',
                'accent': '#D35400',
                'background': '#FBF9F6',
                'surface': '#FFFFFF',
                'text': '#2D2D2D',
                'text_secondary': '#666666'
            },
            typography={
                'title_font': 'KaiTi, STKaiti, SimSun, serif',
                'body_font': 'Microsoft YaHei, PingFang SC, Arial, sans-serif',
                'title_size': 32,
                'subtitle_size': 24,
                'body_size': 18,
                'caption_size': 14
            }
        ),
        'english': Brand(
            id='english',
            name='英语',
            description='英语学科品牌',
            colors={
                'primary': '#1A6FC4',
                'secondary': '#3498DB',
                'accent': '#F39C12',
                'background': '#EBF3FC',
                'surface': '#FFFFFF',
                'text': '#1A1A1A',
                'text_secondary': '#555555'
            },
            typography={
                'title_font': 'Segoe UI, Microsoft YaHei, Arial, sans-serif',
                'body_font': 'Microsoft YaHei, PingFang SC, Arial, sans-serif',
                'title_size': 32,
                'subtitle_size': 24,
                'body_size': 18,
                'caption_size': 14
            }
        ),
        'history': Brand(
            id='history',
            name='历史',
            description='历史学科品牌',
            colors={
                'primary': '#7D5A3C',
                'secondary': '#A0522D',
                'accent': '#CB4335',
                'background': '#F8F3EA',
                'surface': '#FFFDF8',
                'text': '#2D2D2D',
                'text_secondary': '#666666'
            },
            typography={
                'title_font': 'STSong, SimSun, serif',
                'body_font': 'Microsoft YaHei, PingFang SC, Arial, sans-serif',
                'title_size': 32,
                'subtitle_size': 24,
                'body_size': 18,
                'caption_size': 14
            }
        ),
        'geography': Brand(
            id='geography',
            name='地理',
            description='地理学科品牌',
            colors={
                'primary': '#2E7D32',
                'secondary': '#43A047',
                'accent': '#0288D1',
                'background': '#E8F5E9',
                'surface': '#FFFFFF',
                'text': '#1A1A1A',
                'text_secondary': '#555555'
            }
        ),
        'info_tech': Brand(
            id='info_tech',
            name='信息技术',
            description='信息技术学科品牌',
            colors={
                'primary': '#00FF88',
                'secondary': '#00CC6A',
                'accent': '#FF6B6B',
                'background': '#0D1117',
                'surface': '#161B22',
                'text': '#E6EDF3',
                'text_secondary': '#8B949E'
            },
            typography={
                'title_font': 'Consolas, Microsoft YaHei, monospace',
                'body_font': 'Microsoft YaHei, PingFang SC, Arial, sans-serif',
                'title_size': 32,
                'subtitle_size': 24,
                'body_size': 18,
                'caption_size': 14
            }
        ),
        'politics': Brand(
            id='politics',
            name='政治',
            description='政治学科品牌',
            colors={
                'primary': '#C0392B',
                'secondary': '#E74C3C',
                'accent': '#D4AC0D',
                'background': '#FFFDF5',
                'surface': '#FFFFFF',
                'text': '#1A1A1A',
                'text_secondary': '#555555'
            }
        ),
    }

    def __init__(self, templates_dir: str = None):
        """
        初始化品牌管理器

        参数:
            templates_dir: 模板目录路径
        """
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            self.templates_dir = Path(__file__).parent / 'brands'

        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def get_brand(self, brand_id: str) -> Optional[Brand]:
        """
        获取品牌配置

        参数:
            brand_id: 品牌ID

        返回:
            Brand对象或None
        """
        # 先查找预设品牌
        if brand_id in self.PRESET_BRANDS:
            return self.PRESET_BRANDS[brand_id]

        # 查找学科品牌
        if brand_id in self.SUBJECT_BRANDS:
            return self.SUBJECT_BRANDS[brand_id]

        # 查找自定义品牌
        brand_path = self.templates_dir / brand_id / 'brand.json'
        if brand_path.exists():
            try:
                data = json.loads(brand_path.read_text(encoding='utf-8'))
                return Brand.from_dict(data)
            except Exception as e:
                print(f"[WARN] Load brand failed: {e}")

        return None

    def list_brands(self) -> List[Dict[str, str]]:
        """
        列出所有品牌

        返回:
            品牌信息列表
        """
        brands = []

        # 预设品牌
        for brand_id, brand in self.PRESET_BRANDS.items():
            brands.append({
                'id': brand_id,
                'name': brand.name,
                'description': brand.description,
                'type': 'preset'
            })

        # 学科品牌
        for brand_id, brand in self.SUBJECT_BRANDS.items():
            brands.append({
                'id': brand_id,
                'name': brand.name,
                'description': brand.description,
                'type': 'subject'
            })

        # 自定义品牌
        if self.templates_dir.exists():
            for brand_dir in self.templates_dir.iterdir():
                if brand_dir.is_dir():
                    brand_json = brand_dir / 'brand.json'
                    if brand_json.exists():
                        try:
                            data = json.loads(brand_json.read_text(encoding='utf-8'))
                            brands.append({
                                'id': brand_dir.name,
                                'name': data.get('name', brand_dir.name),
                                'description': data.get('description', ''),
                                'type': 'custom'
                            })
                        except Exception:
                            pass

        return brands

    def save_brand(self, brand: Brand) -> Path:
        """
        保存品牌配置

        参数:
            brand: 品牌配置

        返回:
            保存路径
        """
        brand_dir = self.templates_dir / brand.id
        brand_dir.mkdir(parents=True, exist_ok=True)

        brand_json = brand_dir / 'brand.json'
        brand_json.write_text(json.dumps(brand.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')

        print(f"[OK] Brand saved: {brand_json}")
        return brand_json

    def fuse_brands(self, *brand_ids: str) -> Brand:
        """
        融合多个品牌

        参数:
            brand_ids: 品牌ID列表

        返回:
            融合后的Brand对象
        """
        if not brand_ids:
            return self.PRESET_BRANDS['default']

        brands = [self.get_brand(bid) for bid in brand_ids]
        brands = [b for b in brands if b is not None]

        if not brands:
            return self.PRESET_BRANDS['default']

        # 使用最后一个品牌作为基础
        base = brands[-1]

        # 合并颜色（后者覆盖）
        colors = {}
        for brand in brands:
            colors.update(brand.colors)

        # 合并字体（后者覆盖）
        typography = {}
        for brand in brands:
            typography.update(brand.typography)

        return Brand(
            id='_'.join(brand_ids),
            name=' + '.join(b.name for b in brands),
            description='Fused brand',
            colors=colors,
            typography=typography,
            icon_style=base.icon_style,
            icon_library=base.icon_library,
            voice=base.voice,
            tone=base.tone
        )
