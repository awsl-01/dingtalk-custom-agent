"""
PPT Engine - 套牌管理器

管理完整套牌配置：brand + layout + 内容概览。
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .brand_manager import BrandManager, Brand
from .layout_manager import LayoutManager, Layout


@dataclass
class Deck:
    """套牌配置"""
    id: str
    name: str
    description: str = ''

    # 品牌配置
    brand_id: str = 'default'
    brand: Optional[Brand] = None

    # 布局配置
    layout_ids: List[str] = field(default_factory=list)
    layouts: List[Layout] = field(default_factory=list)

    # 内容概览
    use_cases: List[str] = field(default_factory=list)
    design_intent: str = ''

    # 页面结构
    page_structure: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'brand_id': self.brand_id,
            'layout_ids': self.layout_ids,
            'use_cases': self.use_cases,
            'design_intent': self.design_intent,
            'page_structure': self.page_structure
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Deck':
        return cls(**data)


class DeckManager:
    """套牌管理器"""

    # 预设套牌
    PRESET_DECKS = {
        'education_math': Deck(
            id='education_math',
            name='数学教学套牌',
            description='数学学科教学专用套牌',
            brand_id='math',
            layout_ids=['cover', 'toc', 'formula_step', 'graph_illustration', 'proof_deduction', 'exercise_steps', 'data_table', 'ending'],
            use_cases=['数学课件', '公式推导', '习题讲解'],
            design_intent='清晰展示数学公式和推导过程',
            page_structure=[
                {'title': '封面', 'layout': 'cover', 'rhythm': 'anchor'},
                {'title': '目录', 'layout': 'toc', 'rhythm': 'dense'},
                {'title': '公式推导', 'layout': 'formula_step', 'rhythm': 'dense'},
                {'title': '图解说明', 'layout': 'graph_illustration', 'rhythm': 'dense'},
                {'title': '证明过程', 'layout': 'proof_deduction', 'rhythm': 'dense'},
                {'title': '例题解析', 'layout': 'exercise_steps', 'rhythm': 'dense'},
                {'title': '数据表格', 'layout': 'data_table', 'rhythm': 'dense'},
                {'title': '结束', 'layout': 'ending', 'rhythm': 'breathing'},
            ]
        ),
        'education_chinese': Deck(
            id='education_chinese',
            name='语文教学套牌',
            description='语文学科教学专用套牌',
            brand_id='chinese',
            layout_ids=['cover', 'toc', 'text_analysis', 'poetry_vertical', 'comparison_two_column', 'quote', 'ending'],
            use_cases=['语文课件', '古诗词赏析', '文本分析'],
            design_intent='展现语文的文学美感',
            page_structure=[
                {'title': '封面', 'layout': 'cover', 'rhythm': 'anchor'},
                {'title': '目录', 'layout': 'toc', 'rhythm': 'dense'},
                {'title': '文本分析', 'layout': 'text_analysis', 'rhythm': 'dense'},
                {'title': '诗词赏析', 'layout': 'poetry_vertical', 'rhythm': 'breathing'},
                {'title': '对比分析', 'layout': 'comparison_two_column', 'rhythm': 'dense'},
                {'title': '名句品读', 'layout': 'quote', 'rhythm': 'breathing'},
                {'title': '结束', 'layout': 'ending', 'rhythm': 'breathing'},
            ]
        ),
        'education_english': Deck(
            id='education_english',
            name='英语教学套牌',
            description='英语学科教学专用套牌',
            brand_id='english',
            layout_ids=['cover', 'toc', 'vocab_cards', 'role_dialogue', 'sentence_pattern', 'quote', 'ending'],
            use_cases=['英语课件', '词汇学习', '对话练习'],
            design_intent='生动展示英语学习内容',
            page_structure=[
                {'title': '封面', 'layout': 'cover', 'rhythm': 'anchor'},
                {'title': '目录', 'layout': 'toc', 'rhythm': 'dense'},
                {'title': '词汇学习', 'layout': 'vocab_cards', 'rhythm': 'dense'},
                {'title': '情景对话', 'layout': 'role_dialogue', 'rhythm': 'dense'},
                {'title': '句型练习', 'layout': 'sentence_pattern', 'rhythm': 'dense'},
                {'title': '文化角', 'layout': 'quote', 'rhythm': 'breathing'},
                {'title': '结束', 'layout': 'ending', 'rhythm': 'breathing'},
            ]
        ),
        'corporate': Deck(
            id='corporate',
            name='企业汇报套牌',
            description='企业商务汇报专用套牌',
            brand_id='corporate',
            layout_ids=['cover', 'toc', 'three_card', 'four_card', 'split', 'data_table', 'ending'],
            use_cases=['工作汇报', '项目介绍', '数据分析'],
            design_intent='专业简洁的商务风格',
            page_structure=[
                {'title': '封面', 'layout': 'cover', 'rhythm': 'anchor'},
                {'title': '目录', 'layout': 'toc', 'rhythm': 'dense'},
                {'title': '核心要点', 'layout': 'three_card', 'rhythm': 'dense'},
                {'title': '详细分析', 'layout': 'four_card', 'rhythm': 'dense'},
                {'title': '对比说明', 'layout': 'split', 'rhythm': 'dense'},
                {'title': '数据展示', 'layout': 'data_table', 'rhythm': 'dense'},
                {'title': '结束', 'layout': 'ending', 'rhythm': 'breathing'},
            ]
        ),
    }

    def __init__(self, templates_dir: str = None):
        """
        初始化套牌管理器

        参数:
            templates_dir: 模板目录路径
        """
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            self.templates_dir = Path(__file__).parent / 'decks'

        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # 初始化品牌和布局管理器
        self.brand_manager = BrandManager()
        self.layout_manager = LayoutManager()

    def get_deck(self, deck_id: str) -> Optional[Deck]:
        """
        获取套牌配置

        参数:
            deck_id: 套牌ID

        返回:
            Deck对象或None
        """
        # 先查找预设套牌
        if deck_id in self.PRESET_DECKS:
            deck = self.PRESET_DECKS[deck_id]
            self._resolve_deck(deck)
            return deck

        # 查找自定义套牌
        deck_path = self.templates_dir / deck_id / 'deck.json'
        if deck_path.exists():
            try:
                data = json.loads(deck_path.read_text(encoding='utf-8'))
                deck = Deck.from_dict(data)
                self._resolve_deck(deck)
                return deck
            except Exception as e:
                print(f"[WARN] Load deck failed: {e}")

        return None

    def _resolve_deck(self, deck: Deck):
        """解析套牌的品牌和布局引用"""
        # 解析品牌
        if deck.brand_id:
            deck.brand = self.brand_manager.get_brand(deck.brand_id)

        # 解析布局
        deck.layouts = []
        for layout_id in deck.layout_ids:
            layout = self.layout_manager.get_layout(layout_id)
            if layout:
                deck.layouts.append(layout)

    def list_decks(self) -> List[Dict[str, str]]:
        """
        列出所有套牌

        返回:
            套牌信息列表
        """
        decks = []

        # 预设套牌
        for deck_id, deck in self.PRESET_DECKS.items():
            decks.append({
                'id': deck_id,
                'name': deck.name,
                'description': deck.description,
                'type': 'preset',
                'brand': deck.brand_id
            })

        # 自定义套牌
        if self.templates_dir.exists():
            for deck_dir in self.templates_dir.iterdir():
                if deck_dir.is_dir():
                    deck_json = deck_dir / 'deck.json'
                    if deck_json.exists():
                        try:
                            data = json.loads(deck_json.read_text(encoding='utf-8'))
                            decks.append({
                                'id': deck_dir.name,
                                'name': data.get('name', deck_dir.name),
                                'description': data.get('description', ''),
                                'type': 'custom',
                                'brand': data.get('brand_id', '')
                            })
                        except Exception:
                            pass

        return decks

    def save_deck(self, deck: Deck) -> Path:
        """
        保存套牌配置

        参数:
            deck: 套牌配置

        返回:
            保存路径
        """
        deck_dir = self.templates_dir / deck.id
        deck_dir.mkdir(parents=True, exist_ok=True)

        deck_json = deck_dir / 'deck.json'
        deck_json.write_text(json.dumps(deck.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')

        print(f"[OK] Deck saved: {deck_json}")
        return deck_json

    def create_deck_from_content(self, content: Dict[str, Any]) -> Deck:
        """
        从内容创建套牌

        参数:
            content: 内容信息

        返回:
            Deck对象
        """
        # 获取学科
        subject = content.get('subject', '')
        style = content.get('style', 'modern')

        # 选择品牌
        brand_id = content.get('brand_id') or self._get_subject_brand(subject)

        # 选择布局
        layout_ids = content.get('layout_ids') or self._get_default_layouts(subject)

        # 创建套牌
        deck = Deck(
            id=content.get('id', 'custom'),
            name=content.get('name', 'Custom Deck'),
            description=content.get('description', ''),
            brand_id=brand_id,
            layout_ids=layout_ids,
            use_cases=content.get('use_cases', []),
            design_intent=content.get('design_intent', ''),
            page_structure=content.get('page_structure', [])
        )

        # 解析引用
        self._resolve_deck(deck)

        return deck

    def _get_subject_brand(self, subject: str) -> str:
        """获取学科对应的品牌ID"""
        subject_brands = {
            '数学': 'math',
            '物理': 'physics',
            '化学': 'chemistry',
            '生物': 'biology',
            '语文': 'chinese',
            '英语': 'english',
            '历史': 'history',
            '地理': 'geography',
            '信息技术': 'info_tech',
            '政治': 'politics',
        }
        return subject_brands.get(subject, 'default')

    def _get_default_layouts(self, subject: str) -> List[str]:
        """获取学科默认布局列表"""
        subject_layouts = {
            '数学': ['cover', 'toc', 'formula_step', 'graph_illustration', 'exercise_steps', 'ending'],
            '物理': ['cover', 'toc', 'experiment_flow', 'formula_step', 'data_table', 'ending'],
            '化学': ['cover', 'toc', 'experiment_flow', 'structure_diagram', 'data_table', 'ending'],
            '生物': ['cover', 'toc', 'structure_diagram', 'experiment_flow', 'data_table', 'ending'],
            '语文': ['cover', 'toc', 'text_analysis', 'poetry_vertical', 'quote', 'ending'],
            '英语': ['cover', 'toc', 'vocab_cards', 'role_dialogue', 'sentence_pattern', 'ending'],
            '历史': ['cover', 'toc', 'timeline', 'comparison_two_column', 'data_table', 'ending'],
            '地理': ['cover', 'toc', 'map_annotation', 'data_table', 'comparison_two_column', 'ending'],
            '信息技术': ['cover', 'toc', 'code_block', 'flowchart', 'terminal_output', 'ending'],
            '政治': ['cover', 'toc', 'content', 'data_table', 'comparison_two_column', 'ending'],
        }
        return subject_layouts.get(subject, ['cover', 'toc', 'content', 'three_card', 'ending'])
