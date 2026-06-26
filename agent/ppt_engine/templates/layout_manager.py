"""
PPT Engine - 布局管理器

管理页面布局结构：画布/页面结构/页面类型/SVG roster。
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Layout:
    """布局配置"""
    id: str
    name: str
    description: str = ''
    category: str = 'general'  # general / subject

    # 适用学科（仅subject类型）
    subjects: List[str] = field(default_factory=list)

    # 页面类型列表
    page_types: List[str] = field(default_factory=list)

    # SVG模板路径
    svg_template: str = ''

    # 默认节奏
    default_rhythm: str = 'dense'  # dense / breathing / anchor

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'subjects': self.subjects,
            'page_types': self.page_types,
            'svg_template': self.svg_template,
            'default_rhythm': self.default_rhythm
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Layout':
        return cls(**data)


class LayoutManager:
    """布局管理器"""

    # 通用布局
    GENERAL_LAYOUTS = {
        'cover': Layout(
            id='cover',
            name='封面',
            description='演示文稿封面页',
            category='general',
            page_types=['title', 'subtitle', 'author', 'date'],
            default_rhythm='anchor'
        ),
        'toc': Layout(
            id='toc',
            name='目录',
            description='内容目录页',
            category='general',
            page_types=['title', 'items'],
            default_rhythm='dense'
        ),
        'content': Layout(
            id='content',
            name='内容',
            description='通用内容页',
            category='general',
            page_types=['title', 'body', 'bullets'],
            default_rhythm='dense'
        ),
        'three_card': Layout(
            id='three_card',
            name='三卡片',
            description='三列卡片布局',
            category='general',
            page_types=['title', 'cards'],
            default_rhythm='dense'
        ),
        'four_card': Layout(
            id='four_card',
            name='四卡片',
            description='2x2卡片布局',
            category='general',
            page_types=['title', 'cards'],
            default_rhythm='dense'
        ),
        'grid_2x2': Layout(
            id='grid_2x2',
            name='2x2网格',
            description='2x2网格布局',
            category='general',
            page_types=['title', 'cards'],
            default_rhythm='dense'
        ),
        'split': Layout(
            id='split',
            name='左右分栏',
            description='左右两栏布局',
            category='general',
            page_types=['title', 'left', 'right'],
            default_rhythm='dense'
        ),
        'quote': Layout(
            id='quote',
            name='引用',
            description='引用/金句页',
            category='general',
            page_types=['quote', 'author'],
            default_rhythm='breathing'
        ),
        'ending': Layout(
            id='ending',
            name='结束',
            description='演示文稿结束页',
            category='general',
            page_types=['title', 'subtitle'],
            default_rhythm='breathing'
        ),
        'breathing': Layout(
            id='breathing',
            name='呼吸',
            description='过渡/休息页',
            category='general',
            page_types=['title'],
            default_rhythm='breathing'
        ),
    }

    # 学科专属布局
    SUBJECT_LAYOUTS = {
        # 数学/物理
        'formula_step': Layout(
            id='formula_step',
            name='公式步骤',
            description='公式推导步骤',
            category='subject',
            subjects=['math', 'physics'],
            page_types=['title', 'formula', 'steps'],
            default_rhythm='dense'
        ),
        'graph_illustration': Layout(
            id='graph_illustration',
            name='图解',
            description='图表说明',
            category='subject',
            subjects=['math', 'physics'],
            page_types=['title', 'graph', 'description'],
            default_rhythm='dense'
        ),
        'proof_deduction': Layout(
            id='proof_deduction',
            name='证明推导',
            description='证明过程',
            category='subject',
            subjects=['math', 'physics'],
            page_types=['title', 'proof', 'conclusion'],
            default_rhythm='dense'
        ),
        'exercise_steps': Layout(
            id='exercise_steps',
            name='练习步骤',
            description='练习题解析',
            category='subject',
            subjects=['math', 'physics'],
            page_types=['title', 'problem', 'solution', 'answer'],
            default_rhythm='dense'
        ),
        'data_table': Layout(
            id='data_table',
            name='数据表格',
            description='数据表格展示',
            category='subject',
            subjects=['math', 'physics', 'chemistry', 'biology'],
            page_types=['title', 'table', 'analysis'],
            default_rhythm='dense'
        ),

        # 化学/生物
        'experiment_flow': Layout(
            id='experiment_flow',
            name='实验流程',
            description='实验步骤流程',
            category='subject',
            subjects=['chemistry', 'biology', 'physics'],
            page_types=['title', 'materials', 'steps', 'result'],
            default_rhythm='dense'
        ),
        'structure_diagram': Layout(
            id='structure_diagram',
            name='结构图',
            description='结构/模型图',
            category='subject',
            subjects=['chemistry', 'biology'],
            page_types=['title', 'diagram', 'labels'],
            default_rhythm='dense'
        ),

        # 语文
        'poetry_vertical': Layout(
            id='poetry_vertical',
            name='竖排诗词',
            description='竖排古诗词展示',
            category='subject',
            subjects=['chinese'],
            page_types=['title', 'poem', 'author'],
            default_rhythm='breathing'
        ),
        'text_analysis': Layout(
            id='text_analysis',
            name='文本分析',
            description='文本段落分析',
            category='subject',
            subjects=['chinese'],
            page_types=['title', 'text', 'analysis'],
            default_rhythm='dense'
        ),
        'comparison_two_column': Layout(
            id='comparison_two_column',
            name='对比分析',
            description='两栏对比',
            category='subject',
            subjects=['chinese', 'english', 'history'],
            page_types=['title', 'left_title', 'left_content', 'right_title', 'right_content'],
            default_rhythm='dense'
        ),

        # 英语
        'vocab_cards': Layout(
            id='vocab_cards',
            name='词汇卡片',
            description='单词卡片展示',
            category='subject',
            subjects=['english'],
            page_types=['title', 'cards'],
            default_rhythm='dense'
        ),
        'role_dialogue': Layout(
            id='role_dialogue',
            name='角色对话',
            description='对话情景展示',
            category='subject',
            subjects=['english'],
            page_types=['title', 'dialogue'],
            default_rhythm='dense'
        ),
        'sentence_pattern': Layout(
            id='sentence_pattern',
            name='句型练习',
            description='句型结构展示',
            category='subject',
            subjects=['english'],
            page_types=['title', 'pattern', 'examples'],
            default_rhythm='dense'
        ),

        # 历史/地理
        'timeline': Layout(
            id='timeline',
            name='时间轴',
            description='历史时间轴',
            category='subject',
            subjects=['history', 'geography'],
            page_types=['title', 'events'],
            default_rhythm='dense'
        ),
        'map_annotation': Layout(
            id='map_annotation',
            name='地图标注',
            description='地图标注说明',
            category='subject',
            subjects=['geography'],
            page_types=['title', 'map', 'annotations'],
            default_rhythm='dense'
        ),

        # 信息技术
        'code_block': Layout(
            id='code_block',
            name='代码块',
            description='代码展示',
            category='subject',
            subjects=['info_tech'],
            page_types=['title', 'code', 'explanation'],
            default_rhythm='dense'
        ),
        'flowchart': Layout(
            id='flowchart',
            name='流程图',
            description='程序流程图',
            category='subject',
            subjects=['info_tech'],
            page_types=['title', 'flowchart', 'description'],
            default_rhythm='dense'
        ),
        'terminal_output': Layout(
            id='terminal_output',
            name='终端输出',
            description='终端命令展示',
            category='subject',
            subjects=['info_tech'],
            page_types=['title', 'terminal'],
            default_rhythm='dense'
        ),
    }

    def __init__(self, templates_dir: str = None):
        """
        初始化布局管理器

        参数:
            templates_dir: 模板目录路径
        """
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            self.templates_dir = Path(__file__).parent / 'layouts'

        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def get_layout(self, layout_id: str) -> Optional[Layout]:
        """
        获取布局配置

        参数:
            layout_id: 布局ID

        返回:
            Layout对象或None
        """
        # 先查找通用布局
        if layout_id in self.GENERAL_LAYOUTS:
            return self.GENERAL_LAYOUTS[layout_id]

        # 查找学科布局
        if layout_id in self.SUBJECT_LAYOUTS:
            return self.SUBJECT_LAYOUTS[layout_id]

        # 查找自定义布局
        layout_path = self.templates_dir / layout_id / 'layout.json'
        if layout_path.exists():
            try:
                data = json.loads(layout_path.read_text(encoding='utf-8'))
                return Layout.from_dict(data)
            except Exception as e:
                print(f"[WARN] Load layout failed: {e}")

        return None

    def list_layouts(self, category: str = None, subject: str = None) -> List[Dict[str, str]]:
        """
        列出所有布局

        参数:
            category: 类别过滤（general/subject）
            subject: 学科过滤

        返回:
            布局信息列表
        """
        layouts = []

        # 通用布局
        if category is None or category == 'general':
            for layout_id, layout in self.GENERAL_LAYOUTS.items():
                if subject is None:
                    layouts.append({
                        'id': layout_id,
                        'name': layout.name,
                        'description': layout.description,
                        'category': 'general'
                    })

        # 学科布局
        if category is None or category == 'subject':
            for layout_id, layout in self.SUBJECT_LAYOUTS.items():
                if subject is None or subject in layout.subjects:
                    layouts.append({
                        'id': layout_id,
                        'name': layout.name,
                        'description': layout.description,
                        'category': 'subject',
                        'subjects': layout.subjects
                    })

        # 自定义布局
        if self.templates_dir.exists():
            for layout_dir in self.templates_dir.iterdir():
                if layout_dir.is_dir():
                    layout_json = layout_dir / 'layout.json'
                    if layout_json.exists():
                        try:
                            data = json.loads(layout_json.read_text(encoding='utf-8'))
                            layouts.append({
                                'id': layout_dir.name,
                                'name': data.get('name', layout_dir.name),
                                'description': data.get('description', ''),
                                'category': 'custom'
                            })
                        except Exception:
                            pass

        return layouts

    def get_subject_layouts(self, subject: str) -> List[Layout]:
        """
        获取学科专属布局

        参数:
            subject: 学科名称

        返回:
            布局列表
        """
        layouts = []

        for layout_id, layout in self.SUBJECT_LAYOUTS.items():
            if subject in layout.subjects:
                layouts.append(layout)

        return layouts

    def save_layout(self, layout: Layout) -> Path:
        """
        保存布局配置

        参数:
            layout: 布局配置

        返回:
            保存路径
        """
        layout_dir = self.templates_dir / layout.id
        layout_dir.mkdir(parents=True, exist_ok=True)

        layout_json = layout_dir / 'layout.json'
        layout_json.write_text(json.dumps(layout.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')

        print(f"[OK] Layout saved: {layout_json}")
        return layout_json
