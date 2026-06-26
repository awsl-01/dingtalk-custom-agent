"""
PPT Master 集成模块
使用 ppt-master 流水线生成专业级 PPT

流水线步骤：
1. 创建项目 (project_manager.py init)
2. 生成设计规范 (design_spec.md + spec_lock.md)
3. AI 逐页生成 SVG (Executor 阶段)
4. 生成演讲备注 (notes/total.md)
5. 质量检查 (svg_quality_checker.py)
6. 后处理 (total_md_split.py → finalize_svg.py → svg_to_pptx.py)
"""

import os
import sys
import json
import subprocess
import logging
import re
import glob
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# 路径常量
PPT_MASTER_DIR = Path(__file__).parent.parent / "ppt-master"
SKILL_DIR = PPT_MASTER_DIR / "skills" / "ppt-master"
SCRIPTS_DIR = SKILL_DIR / "scripts"
PROJECTS_DIR = PPT_MASTER_DIR / "projects"

# ⚠️ 关键：在修改 sys.path 之前，先保存项目根目录的 config 引用
# 避免后续 sys.path.insert 导入到 ppt-master/scripts/config.py（覆盖项目 config）
import importlib.util
_config_spec = importlib.util.spec_from_file_location("project_config", str(Path(__file__).parent.parent / "config.py"))
_config_module = importlib.util.module_from_spec(_config_spec)
_config_spec.loader.exec_module(_config_module)

# 将项目根目录的 config 模块注入到 sys.modules，确保其他模块能正确导入
sys.modules['config'] = _config_module

sys.path.insert(0, str(SCRIPTS_DIR))


# ─────────────────────────── 模板注册表 ───────────────────────────
# 每个模板包含：配色、字体、页面结构、装饰元素
# 参考 ppt-master/skills/ppt-master/templates/layouts/ 中的设计规范

# ── 学科独立模板 ──
# 每个模板包含完整视觉属性，渲染函数直接使用，不依赖 style 分支
TEMPLATES = {
    'math': {'name':'数学','bg':'#F0F5FB','primary':'#1A5276','accent':'#E74C3C','accent2':'#2980B9','text':'#1A1A1A','text_secondary':'#555555','text_light':'#888888','card_bg':'#FFFFFF','card_border':'#C8D8E8','title_font':'Microsoft YaHei, SimHei, Arial, sans-serif','body_font':'Microsoft YaHei, PingFang SC, Arial, sans-serif','baseline':20,'header_h':70,'header_bg':'#1A5276','accent_bar_w':6,'footer_h':40,'footer_y':680,'footer_color':'#8899AA','bg_pattern':'math_grid','decor_icon':'geometric','shadow':'0 2px 10px rgba(26,82,118,0.10)','card_radius':12},
    'physics': {'name':'物理','bg':'#EBF2F8','primary':'#1B4F72','accent':'#2E86C1','accent2':'#48C9B0','text':'#1A1A1A','text_secondary':'#555555','text_light':'#888888','card_bg':'#FFFFFF','card_border':'#A8C8E0','title_font':'Microsoft YaHei, SimHei, Arial, sans-serif','body_font':'Microsoft YaHei, PingFang SC, Arial, sans-serif','baseline':20,'header_h':65,'header_bg':'#1B4F72','accent_bar_w':5,'footer_h':40,'footer_y':680,'footer_color':'#7A99AA','bg_pattern':'atom_orbit','decor_icon':'atom','shadow':'0 2px 10px rgba(27,79,114,0.10)','card_radius':10},
    'chemistry': {'name':'化学','bg':'#F3EDFA','primary':'#6C3483','accent':'#EC7063','accent2':'#1ABC9C','text':'#1A1A1A','text_secondary':'#555555','text_light':'#888888','card_bg':'#FFFFFF','card_border':'#D0B8E0','title_font':'Microsoft YaHei, SimHei, Arial, sans-serif','body_font':'Microsoft YaHei, PingFang SC, Arial, sans-serif','baseline':20,'header_h':65,'header_bg':'#6C3483','accent_bar_w':5,'footer_h':40,'footer_y':680,'footer_color':'#9988BB','bg_pattern':'molecule','decor_icon':'flask','shadow':'0 2px 10px rgba(108,52,131,0.10)','card_radius':10},
    'biology': {'name':'生物','bg':'#EAF7EA','primary':'#1E8449','accent':'#F0B27A','accent2':'#58D68D','text':'#1A1A1A','text_secondary':'#555555','text_light':'#888888','card_bg':'#FFFFFF','card_border':'#B8D8B8','title_font':'Microsoft YaHei, SimHei, Arial, sans-serif','body_font':'Microsoft YaHei, PingFang SC, Arial, sans-serif','baseline':20,'header_h':65,'header_bg':'#1E8449','accent_bar_w':5,'footer_h':40,'footer_y':680,'footer_color':'#77AA77','bg_pattern':'cell_outline','decor_icon':'leaf','shadow':'0 2px 10px rgba(30,132,73,0.10)','card_radius':12},
    'chinese': {'name':'语文','bg':'#FBF9F6','primary':'#7B5B3A','accent':'#D35400','accent2':'#B7950B','text':'#2D2D2D','text_secondary':'#666666','text_light':'#999999','card_bg':'#FFFFFF','card_border':'#E0D5C8','title_font':'KaiTi, STKaiti, SimSun, serif','body_font':'Microsoft YaHei, PingFang SC, Arial, sans-serif','baseline':20,'header_h':60,'header_bg':'#7B5B3A','accent_bar_w':4,'footer_h':40,'footer_y':680,'footer_color':'#AA9988','bg_pattern':'xuan_paper','decor_icon':'brush','shadow':'0 2px 8px rgba(123,91,58,0.10)','card_radius':8},
    'english': {'name':'英语','bg':'#EBF3FC','primary':'#1A6FC4','accent':'#F39C12','accent2':'#00BCD4','text':'#1A1A1A','text_secondary':'#555555','text_light':'#888888','card_bg':'#FFFFFF','card_border':'#A8C8E8','title_font':'Segoe UI, Microsoft YaHei, Arial, sans-serif','body_font':'Microsoft YaHei, PingFang SC, Arial, sans-serif','baseline':20,'header_h':60,'header_bg':'#1A6FC4','accent_bar_w':4,'footer_h':40,'footer_y':680,'footer_color':'#7799CC','bg_pattern':'bubble','decor_icon':'chat','shadow':'0 2px 10px rgba(26,111,196,0.10)','card_radius':14},
    'history': {'name':'历史','bg':'#F8F3EA','primary':'#7D5A3C','accent':'#CB4335','accent2':'#D4AC0D','text':'#2D2D2D','text_secondary':'#666666','text_light':'#999999','card_bg':'#FFFDF8','card_border':'#D0C0A0','title_font':'STSong, SimSun, serif','body_font':'Microsoft YaHei, PingFang SC, Arial, sans-serif','baseline':20,'header_h':56,'header_bg':'#7D5A3C','accent_bar_w':4,'footer_h':40,'footer_y':680,'footer_color':'#AA9977','bg_pattern':'parchment','decor_icon':'scroll','shadow':'0 2px 8px rgba(125,90,60,0.10)','card_radius':6},
    'geography': {'name':'地理','bg':'#E8F5E9','primary':'#2E7D32','accent':'#0288D1','accent2':'#00897B','text':'#1A1A1A','text_secondary':'#555555','text_light':'#888888','card_bg':'#FFFFFF','card_border':'#A8D0B0','title_font':'Microsoft YaHei, SimHei, Arial, sans-serif','body_font':'Microsoft YaHei, PingFang SC, Arial, sans-serif','baseline':20,'header_h':56,'header_bg':'#2E7D32','accent_bar_w':4,'footer_h':40,'footer_y':680,'footer_color':'#66AA77','bg_pattern':'map_contour','decor_icon':'globe','shadow':'0 2px 8px rgba(46,125,50,0.10)','card_radius':10},
    'info_tech': {'name':'信息技术','bg':'#0D1117','primary':'#00FF88','accent':'#FF6B6B','accent2':'#FFD93D','text':'#E6EDF3','text_secondary':'#8B949E','text_light':'#6E7681','card_bg':'#161B22','card_border':'#30363D','title_font':'Consolas, Microsoft YaHei, monospace','body_font':'Microsoft YaHei, PingFang SC, Arial, sans-serif','baseline':20,'header_h':50,'header_bg':'#161B22','accent_bar_w':3,'footer_h':35,'footer_y':685,'footer_color':'#6E7681','bg_pattern':'code_matrix','decor_icon':'terminal','shadow':'0 2px 8px rgba(0,255,136,0.08)','card_radius':6},
    'politics': {'name':'政治','bg':'#FFFDF5','primary':'#C0392B','accent':'#D4AC0D','accent2':'#A93226','text':'#1A1A1A','text_secondary':'#555555','text_light':'#888888','card_bg':'#FFFFFF','card_border':'#E0C8B0','title_font':'Microsoft YaHei, SimHei, Arial, sans-serif','body_font':'Microsoft YaHei, PingFang SC, Arial, sans-serif','baseline':20,'header_h':56,'header_bg':'#C0392B','accent_bar_w':5,'footer_h':40,'footer_y':680,'footer_color':'#CC9966','bg_pattern':'stripe','decor_icon':'star','shadow':'0 2px 8px rgba(192,57,43,0.10)','card_radius':8},
    'general': {'name':'通用','bg':'#FAFAFA','primary':'#37474F','accent':'#1976D2','accent2':'#43A047','text':'#1A1A1A','text_secondary':'#555555','text_light':'#888888','card_bg':'#FFFFFF','card_border':'#E0E0E0','title_font':'Microsoft YaHei, SimHei, Arial, sans-serif','body_font':'Microsoft YaHei, PingFang SC, Arial, sans-serif','baseline':20,'header_h':56,'header_bg':'#37474F','accent_bar_w':4,'footer_h':40,'footer_y':680,'footer_color':'#999999','bg_pattern':'none','decor_icon':'none','shadow':'0 2px 8px rgba(0,0,0,0.08)','card_radius':8},
}


# ── 学科分组模板注册表 ──
# 定义每个学科分组的可用布局、视觉元素、背景风格
# required_layouts: 该学科内容页必须优先使用的专属布局（至少选2种）
# forbidden_layouts: 该学科禁止使用的通用布局
SUBJECT_GROUP_LAYOUTS = {
    "math_physics": {
        "allowed_layouts": [
            "cover", "toc", "three_card", "four_card", "grid_2x2", "split",
            "formula_step", "graph_illustration", "proof_deduction", "exercise_steps",
            "data_table", "breathing", "ending"
        ],
        "required_layouts": ["formula_step", "graph_illustration", "proof_deduction", "exercise_steps", "data_table"],
        "forbidden_layouts": ["poetry_vertical", "timeline"],
        "visual_elements": ["formula_block", "coordinate_axis", "step_cards", "geometric_shapes"],
        "background_style": "grid_lines",
        "description": "数学：公式推导、坐标图解、步骤卡片、证明演绎",
    },
    "biology_chemistry": {
        "allowed_layouts": [
            "cover", "toc", "three_card", "four_card", "grid_2x2", "split",
            "experiment_flow", "structure_diagram", "data_table", "formula_step",
            "breathing", "ending"
        ],
        "required_layouts": ["experiment_flow", "structure_diagram", "data_table", "formula_step"],
        "forbidden_layouts": ["poetry_vertical"],
        "visual_elements": ["arrow_flow", "cell_shape", "molecule", "process_arrow"],
        "background_style": "life_curve",
        "description": "物理/化学/生物：实验流程、结构图、数据表格、反应方程式",
    },
    "chinese_narrative": {
        "allowed_layouts": [
            "cover", "toc", "three_card", "four_card", "split",
            "poetry_vertical", "quote", "text_analysis", "comparison_two_column",
            "breathing", "ending"
        ],
        "required_layouts": ["poetry_vertical", "quote", "text_analysis", "comparison_two_column"],
        "forbidden_layouts": ["formula_step", "graph_illustration"],
        "visual_elements": ["ink_lines", "quote_marks", "vertical_text", "brush_strokes"],
        "background_style": "ink_wash",
        "description": "语文（散文/叙事）：竖排诗词、引文赏析、文本分析、对比赏析",
    },
    "chinese_other": {
        "allowed_layouts": [
            "cover", "toc", "three_card", "four_card", "split",
            "quote", "text_analysis", "comparison_two_column", "vocab",
            "breathing", "ending"
        ],
        "required_layouts": ["quote", "text_analysis", "comparison_two_column"],
        "forbidden_layouts": ["formula_step", "graph_illustration"],
        "visual_elements": ["ink_lines", "quote_marks", "brush_strokes"],
        "background_style": "ink_wash",
        "description": "语文（其他）：引文赏析、文本分析、对比赏析",
    },
    "english": {
        "allowed_layouts": [
            "cover", "toc", "three_card", "four_card", "split",
            "vocab_cards", "role_dialogue", "sentence_pattern", "quote",
            "breathing", "ending"
        ],
        "required_layouts": ["vocab_cards", "role_dialogue", "sentence_pattern", "quote"],
        "forbidden_layouts": [],
        "visual_elements": ["ink_lines", "quote_marks", "vertical_text", "brush_strokes"],
        "background_style": "ink_wash",
        "description": "英语：词汇卡片、角色对话、句型练习、引文赏析",
    },
    "history_geography": {
        "allowed_layouts": [
            "cover", "toc", "three_card", "four_card", "grid_2x2", "split",
            "timeline", "comparison_two_column", "map_annotation", "data_table",
            "breathing", "ending"
        ],
        "required_layouts": ["timeline", "comparison_two_column", "map_annotation", "data_table"],
        "forbidden_layouts": ["formula_step", "experiment_flow"],
        "visual_elements": ["timeline_bar", "stat_card", "comparison_columns"],
        "background_style": "paper_texture",
        "description": "历史/地理：时间轴、对比表格、地图标注、数据统计",
    },
    "info_tech": {
        "allowed_layouts": [
            "cover", "toc", "three_card", "four_card", "grid_2x2",
            "code_block", "flowchart", "terminal_output", "tech_dark",
            "breathing", "ending"
        ],
        "required_layouts": ["code_block", "flowchart", "tech_dark", "terminal_output"],
        "forbidden_layouts": ["poetry_vertical"],
        "visual_elements": ["code_fragments", "terminal_prompt", "neon_accents"],
        "background_style": "terminal_grid",
        "description": "信息技术：代码块、流程图、终端输出、科技暗色",
    },
    "general": {
        "allowed_layouts": [
            "cover", "toc", "three_card", "four_card", "grid_2x2",
            "split", "breathing", "quote", "ending"
        ],
        "required_layouts": [],
        "forbidden_layouts": [],
        "visual_elements": ["standard_cards", "icons"],
        "background_style": "clean",
        "description": "通用：标准卡片布局",
    },
}


# ── 学科骨架映射表 ──
# 每个学科的推荐页面结构骨架，AI规划时必须遵循
# layout: 必须使用专属布局，不允许回退通用布局
# optional: True 表示该页可选（根据内容量决定是否包含）
SUBJECT_SKELETONS = {
    "chinese_narrative": {
        "name": "语文（散文/叙事）",
        "min_pages": 7, "max_pages": 12,
        "pages": [
            {"title": "情境导入", "desc": "作者介绍、写作背景、时代语境", "layout": "text_analysis", "rhythm": "dense"},
            {"title": "整体感知", "desc": "内容概括、结构梳理、主旨提炼", "layout": "comparison_two_column", "rhythm": "dense"},
            {"title": "重点语段赏析", "desc": "精彩语句逐句赏析、修辞手法", "layout": "poetry_vertical", "rhythm": "dense"},
            {"title": "深层品读", "desc": "关键段落分析、语言特色", "layout": "text_analysis", "rhythm": "dense", "optional": True},
            {"title": "人物/手法分析", "desc": "人物形象、写作手法对比", "layout": "comparison_two_column", "rhythm": "dense"},
            {"title": "名句品读", "desc": "经典名句赏析、文学价值", "layout": "quote", "rhythm": "breathing"},
            {"title": "拓展与思辨", "desc": "讨论题、联系现实", "layout": "comparison_two_column", "rhythm": "dense", "optional": True},
            {"title": "微写作/练笔", "desc": "仿写、续写、感悟", "layout": "text_analysis", "rhythm": "dense", "optional": True},
            {"title": "推荐阅读", "desc": "同类作品推荐、课外延伸", "layout": "quote", "rhythm": "breathing"},
        ],
    },
    "chinese_other": {
        "name": "语文（其他）",
        "min_pages": 6, "max_pages": 10,
        "pages": [
            {"title": "学习目标", "desc": "本课学习目标与重难点", "layout": "text_analysis", "rhythm": "dense"},
            {"title": "知识要点", "desc": "核心概念、关键知识点", "layout": "text_analysis", "rhythm": "dense"},
            {"title": "课文分析", "desc": "文章结构、写作手法", "layout": "comparison_two_column", "rhythm": "dense"},
            {"title": "名句赏析", "desc": "经典语句品读", "layout": "quote", "rhythm": "breathing"},
            {"title": "练习巩固", "desc": "基础练习、拓展提升", "layout": "text_analysis", "rhythm": "dense"},
            {"title": "总结", "desc": "本课核心收获", "layout": "quote", "rhythm": "breathing"},
        ],
    },
    "math": {
        "name": "数学",
        "min_pages": 7, "max_pages": 12,
        "pages": [
            {"title": "问题引入", "desc": "生活情境或旧知回顾，引出新课", "layout": "graph_illustration", "rhythm": "dense"},
            {"title": "概念/定义", "desc": "核心概念的定义与内涵", "layout": "formula_step", "rhythm": "dense"},
            {"title": "公式/定理", "desc": "公式推导、定理证明", "layout": "proof_deduction", "rhythm": "dense"},
            {"title": "典型例题", "desc": "基础题型的分步解法", "layout": "exercise_steps", "rhythm": "dense"},
            {"title": "综合例题", "desc": "综合题型解析", "layout": "exercise_steps", "rhythm": "dense", "optional": True},
            {"title": "变式训练", "desc": "举一反三、变式练习", "layout": "exercise_steps", "rhythm": "dense", "optional": True},
            {"title": "易错辨析", "desc": "常见错误类型与纠正", "layout": "data_table", "rhythm": "dense"},
            {"title": "数学思想", "desc": "核心数学思想方法总结", "layout": "graph_illustration", "rhythm": "breathing"},
            {"title": "总结与作业", "desc": "知识总结、课后作业", "layout": "formula_step", "rhythm": "dense"},
        ],
    },
    "english": {
        "name": "英语",
        "min_pages": 7, "max_pages": 12,
        "pages": [
            {"title": "Warm-up", "desc": "情境对话、图片讨论、热身活动", "layout": "role_dialogue", "rhythm": "dense"},
            {"title": "Vocabulary", "desc": "核心词汇学习", "layout": "vocab_cards", "rhythm": "dense"},
            {"title": "Sentence Patterns", "desc": "重点句型结构与练习", "layout": "sentence_pattern", "rhythm": "dense"},
            {"title": "Listening/Speaking", "desc": "听力口语练习、情景对话", "layout": "role_dialogue", "rhythm": "dense"},
            {"title": "Grammar Focus", "desc": "语法要点、对比分析", "layout": "comparison_two_column", "rhythm": "dense", "optional": True},
            {"title": "Reading", "desc": "课文阅读理解", "layout": "text_analysis", "rhythm": "dense", "optional": True},
            {"title": "Writing Task", "desc": "写作练习", "layout": "sentence_pattern", "rhythm": "dense"},
            {"title": "Culture Corner", "desc": "文化拓展、跨文化理解", "layout": "quote", "rhythm": "breathing"},
        ],
    },
    "physics": {
        "name": "物理",
        "min_pages": 7, "max_pages": 12,
        "pages": [
            {"title": "现象引入", "desc": "实验视频、生活现象、问题提出", "layout": "experiment_flow", "rhythm": "dense"},
            {"title": "提出问题", "desc": "猜想与假设、研究方向", "layout": "data_table", "rhythm": "dense"},
            {"title": "实验探究", "desc": "实验步骤、操作流程", "layout": "experiment_flow", "rhythm": "dense"},
            {"title": "规律总结", "desc": "物理规律、公式推导", "layout": "formula_step", "rhythm": "dense"},
            {"title": "数据记录", "desc": "实验数据、分析表格", "layout": "data_table", "rhythm": "dense", "optional": True},
            {"title": "应用实例", "desc": "生活应用、科技前沿", "layout": "structure_diagram", "rhythm": "dense"},
            {"title": "练习与反思", "desc": "巩固练习、易错分析", "layout": "formula_step", "rhythm": "dense"},
        ],
    },
    "chemistry": {
        "name": "化学",
        "min_pages": 7, "max_pages": 12,
        "pages": [
            {"title": "问题引入", "desc": "实验现象、生活问题引入", "layout": "experiment_flow", "rhythm": "dense"},
            {"title": "原理分析", "desc": "化学原理、分子结构", "layout": "structure_diagram", "rhythm": "dense"},
            {"title": "实验步骤", "desc": "实验操作流程", "layout": "experiment_flow", "rhythm": "dense"},
            {"title": "数据记录", "desc": "实验数据、反应条件", "layout": "data_table", "rhythm": "dense"},
            {"title": "结论与方程式", "desc": "化学方程式、反应总结", "layout": "formula_step", "rhythm": "dense"},
            {"title": "安全提醒", "desc": "实验安全、注意事项", "layout": "data_table", "rhythm": "dense", "optional": True},
            {"title": "拓展应用", "desc": "化学在生活中的应用", "layout": "structure_diagram", "rhythm": "breathing"},
        ],
    },
    "biology": {
        "name": "生物",
        "min_pages": 7, "max_pages": 12,
        "pages": [
            {"title": "科学史/发现", "desc": "相关科学发现的历史脉络", "layout": "timeline", "rhythm": "dense"},
            {"title": "结构与功能", "desc": "生物结构、功能分析", "layout": "structure_diagram", "rhythm": "dense"},
            {"title": "实验探究", "desc": "实验步骤、观察方法", "layout": "experiment_flow", "rhythm": "dense"},
            {"title": "数据对比", "desc": "实验数据、对比分析", "layout": "data_table", "rhythm": "dense"},
            {"title": "应用与前沿", "desc": "生物科技应用、前沿进展", "layout": "structure_diagram", "rhythm": "dense", "optional": True},
            {"title": "综合思考", "desc": "综合分析、拓展思考", "layout": "comparison_two_column", "rhythm": "breathing"},
        ],
    },
    "history": {
        "name": "历史",
        "min_pages": 7, "max_pages": 12,
        "pages": [
            {"title": "时代背景", "desc": "历史背景、时代语境", "layout": "timeline", "rhythm": "dense"},
            {"title": "关键事件", "desc": "重大历史事件详述", "layout": "timeline", "rhythm": "dense"},
            {"title": "人物评析", "desc": "历史人物分析评价", "layout": "comparison_two_column", "rhythm": "dense"},
            {"title": "影响与意义", "desc": "历史影响、深远意义", "layout": "data_table", "rhythm": "dense"},
            {"title": "史料实证", "desc": "史料分析、证据链", "layout": "text_analysis", "rhythm": "dense", "optional": True},
            {"title": "思考与讨论", "desc": "开放性讨论、现实启示", "layout": "comparison_two_column", "rhythm": "breathing"},
        ],
    },
    "geography": {
        "name": "地理",
        "min_pages": 7, "max_pages": 12,
        "pages": [
            {"title": "地理位置", "desc": "地理位置、地图标注", "layout": "map_annotation", "rhythm": "dense"},
            {"title": "自然特征", "desc": "气候、地形、水文", "layout": "data_table", "rhythm": "dense"},
            {"title": "人文特征", "desc": "人口、经济、文化", "layout": "data_table", "rhythm": "dense"},
            {"title": "人地关系", "desc": "人类活动与地理环境", "layout": "comparison_two_column", "rhythm": "dense"},
            {"title": "案例探究", "desc": "典型案例分析", "layout": "map_annotation", "rhythm": "dense", "optional": True},
            {"title": "总结思考", "desc": "核心知识总结", "layout": "data_table", "rhythm": "breathing"},
        ],
    },
    "info_tech": {
        "name": "信息技术",
        "min_pages": 6, "max_pages": 10,
        "pages": [
            {"title": "问题情境", "desc": "实际问题、应用场景引入", "layout": "tech_dark", "rhythm": "dense"},
            {"title": "算法/流程", "desc": "算法设计、流程图", "layout": "flowchart", "rhythm": "dense"},
            {"title": "代码实现", "desc": "核心代码、语法要点", "layout": "code_block", "rhythm": "dense"},
            {"title": "调试与优化", "desc": "调试技巧、性能优化", "layout": "terminal_output", "rhythm": "dense", "optional": True},
            {"title": "拓展任务", "desc": "进阶练习、项目拓展", "layout": "tech_dark", "rhythm": "dense"},
        ],
    },
    "politics": {
        "name": "政治/道法",
        "min_pages": 6, "max_pages": 10,
        "pages": [
            {"title": "案例导入", "desc": "时事案例、生活情境", "layout": "timeline", "rhythm": "dense"},
            {"title": "概念解析", "desc": "核心概念、理论框架", "layout": "data_table", "rhythm": "dense"},
            {"title": "多角度辩论", "desc": "不同观点对比分析", "layout": "comparison_two_column", "rhythm": "dense"},
            {"title": "实践指导", "desc": "实际应用、行动指南", "layout": "data_table", "rhythm": "dense", "optional": True},
            {"title": "价值升华", "desc": "核心价值观、思想升华", "layout": "quote", "rhythm": "breathing"},
        ],
    },
}


def get_skeleton(subject: str = "", topic: str = "") -> dict:
    """根据学科获取对应的骨架"""
    combined = f"{subject} {topic}"

    # 语文特殊处理
    if "语文" in combined:
        for kw in CHINESE_NARRATIVE_KEYWORDS:
            if kw in combined:
                return SUBJECT_SKELETONS["chinese_narrative"]
        return SUBJECT_SKELETONS["chinese_other"]

    # 其他学科
    skeleton_map = {
        "数学": "math", "几何": "math", "代数": "math",
        "英语": "english", "外语": "english",
        "物理": "physics",
        "化学": "chemistry",
        "生物": "biology", "科学": "biology",
        "历史": "history",
        "地理": "geography",
        "信息技术": "info_tech", "编程": "info_tech",
        "政治": "politics", "道德": "politics", "班会": "politics", "德育": "politics",
    }
    for kw, sk_id in skeleton_map.items():
        if kw in combined:
            return SUBJECT_SKELETONS[sk_id]

    # 通用骨架（扩展版，更多页面）
    return {
        "name": "通用",
        "min_pages": 8, "max_pages": 15,
        "pages": [
            {"title": "学习目标", "desc": "学习目标与重难点", "layout": "three_card", "rhythm": "dense"},
            {"title": "知识背景", "desc": "背景介绍与前置知识", "layout": "split", "rhythm": "dense"},
            {"title": "核心概念", "desc": "核心概念与定义", "layout": "three_card", "rhythm": "dense"},
            {"title": "重点解析", "desc": "重点内容详细解析", "layout": "grid_2x2", "rhythm": "dense"},
            {"title": "方法技巧", "desc": "学习方法与技巧", "layout": "three_card", "rhythm": "dense"},
            {"title": "案例分析", "desc": "典型案例分析", "layout": "split", "rhythm": "dense"},
            {"title": "实践应用", "desc": "知识运用与练习", "layout": "four_card", "rhythm": "dense"},
            {"title": "拓展延伸", "desc": "拓展知识与延伸阅读", "layout": "quote", "rhythm": "breathing"},
            {"title": "课堂小结", "desc": "核心收获与总结", "layout": "three_card", "rhythm": "dense"},
            {"title": "课后思考", "desc": "思考题与作业", "layout": "grid_2x2", "rhythm": "dense"},
        ],
    }


# 学科 -> 学科分组映射
# 语文需要根据主题判断是散文/叙事还是其他类型
SUBJECT_GROUP_MAP = {
    "数学": "math_physics", "几何": "math_physics", "代数": "math_physics",
    "体育": "math_physics",
    "物理": "biology_chemistry", "化学": "biology_chemistry",
    "生物": "biology_chemistry", "科学": "biology_chemistry",
    "英语": "english", "外语": "english",
    "音乐": "chinese_other", "美术": "chinese_other", "心理": "chinese_other",
    "历史": "history_geography", "地理": "history_geography",
    "政治": "history_geography", "道德": "history_geography",
    "班会": "history_geography", "德育": "history_geography",
    "信息技术": "info_tech", "编程": "info_tech",
}

# 语文散文/叙事类关键词（用于区分语文的子类型）
CHINESE_NARRATIVE_KEYWORDS = [
    "散文", "叙事", "记叙", "写景", "抒情", "游记", "回忆", "从百草园", "背影",
    "春", "济南的冬天", "荷塘月色", "故都的秋", "藤野先生", "社戏", "散步",
    "秋天的怀念", "紫藤萝瀑布", "安塞腰鼓", "壶口瀑布", "昆明的雨",
]


def get_subject_group(subject: str = "", topic: str = "") -> str:
    """获取学科分组ID"""
    combined = f"{subject} {topic}"

    # 语文需要特殊处理：判断是散文/叙事还是其他
    if "语文" in combined:
        for kw in CHINESE_NARRATIVE_KEYWORDS:
            if kw in combined:
                return "chinese_narrative"
        return "chinese_other"

    for keyword, group_id in SUBJECT_GROUP_MAP.items():
        if keyword in combined:
            return group_id
    return "general"


def get_allowed_layouts(subject: str = "", topic: str = "") -> list:
    """获取当前学科允许的布局类型"""
    group_id = get_subject_group(subject, topic)
    return SUBJECT_GROUP_LAYOUTS[group_id]["allowed_layouts"]


def get_required_layouts(subject: str = "", topic: str = "") -> list:
    """获取当前学科必须优先使用的专属布局"""
    group_id = get_subject_group(subject, topic)
    return SUBJECT_GROUP_LAYOUTS[group_id].get("required_layouts", [])


def get_forbidden_layouts(subject: str = "", topic: str = "") -> list:
    """获取当前学科禁止使用的布局"""
    group_id = get_subject_group(subject, topic)
    return SUBJECT_GROUP_LAYOUTS[group_id].get("forbidden_layouts", [])


def get_visual_elements(subject: str = "", topic: str = "") -> list:
    """获取当前学科的视觉元素"""
    group_id = get_subject_group(subject, topic)
    return SUBJECT_GROUP_LAYOUTS[group_id]["visual_elements"]


def get_background_style(subject: str = "", topic: str = "") -> str:
    """获取当前学科的背景风格"""
    group_id = get_subject_group(subject, topic)
    return SUBJECT_GROUP_LAYOUTS[group_id]["background_style"]


# 学科 -> 模板映射
SUBJECT_TEMPLATE_MAP = {
    # 数学
    "数学": "math", "几何": "math", "代数": "math", "体育": "math",
    # 物理
    "物理": "physics",
    # 化学
    "化学": "chemistry",
    # 生物
    "生物": "biology", "科学": "biology",
    # 语文
    "语文": "chinese",
    # 英语
    "英语": "english", "外语": "english",
    # 历史
    "历史": "history",
    # 地理
    "地理": "geography",
    # 政治/道法
    "政治": "politics", "道德": "politics", "班会": "politics", "德育": "politics",
    # 信息技术
    "信息技术": "info_tech", "编程": "info_tech",
    # 艺术/心理（默认用语文模板）
    "音乐": "chinese", "美术": "chinese", "心理": "chinese",
}


def pick_theme(subject: str = "", topic: str = "") -> dict:
    """根据学科选择模板风格"""
    combined = f"{subject} {topic}"
    for keyword, template_id in SUBJECT_TEMPLATE_MAP.items():
        if keyword in combined:
            return TEMPLATES[template_id]
    return TEMPLATES["general"]


def get_subject_theme(subject: str) -> dict:
    """获取学科专属配色方案（增强版）

    返回的 theme 包含完整的视觉属性，与 TEMPLATES 字典结构兼容。
    """
    # 默认完整 theme 结构（从 TEMPLATES['general'] 继承）
    base_theme = TEMPLATES.get('general', {}).copy()

    SUBJECT_THEMES = {
        '语文': {
            'primary': '#5B7F5E', 'accent': '#C4883A', 'accent2': '#8B6914',
            'bg': '#FBF8F1', 'card_bg': '#FFFFFF', 'card_border': '#E8DCC8',
            'text': '#2D2D2D', 'text_secondary': '#666666', 'text_light': '#999999',
            'header_bg': '#5B7F5E', 'footer_color': '#AA9988',
            'bg_pattern': 'xuan_paper', 'decor_icon': 'brush',
            'title_font': 'KaiTi, STKaiti, SimSun, serif',
        },
        '数学': {
            'primary': '#1A5276', 'accent': '#E74C3C', 'accent2': '#2980B9',
            'bg': '#F0F5FB', 'card_bg': '#FFFFFF', 'card_border': '#C8D8E8',
            'text': '#1A1A1A', 'text_secondary': '#555555', 'text_light': '#888888',
            'header_bg': '#1A5276', 'footer_color': '#8899AA',
            'bg_pattern': 'math_grid', 'decor_icon': 'geometric',
        },
        '英语': {
            'primary': '#1A6FC4', 'accent': '#F39C12', 'accent2': '#00BCD4',
            'bg': '#EBF3FC', 'card_bg': '#FFFFFF', 'card_border': '#A8C8E8',
            'text': '#1A1A1A', 'text_secondary': '#555555', 'text_light': '#888888',
            'header_bg': '#1A6FC4', 'footer_color': '#7799CC',
            'bg_pattern': 'bubble', 'decor_icon': 'chat',
        },
        '物理': {
            'primary': '#1B4F72', 'accent': '#2E86C1', 'accent2': '#48C9B0',
            'bg': '#EBF2F8', 'card_bg': '#FFFFFF', 'card_border': '#A8C8E0',
            'text': '#1A1A1A', 'text_secondary': '#555555', 'text_light': '#888888',
            'header_bg': '#1B4F72', 'footer_color': '#7A99AA',
            'bg_pattern': 'atom_orbit', 'decor_icon': 'atom',
        },
        '化学': {
            'primary': '#6C3483', 'accent': '#EC7063', 'accent2': '#1ABC9C',
            'bg': '#F3EDFA', 'card_bg': '#FFFFFF', 'card_border': '#D0B8E0',
            'text': '#1A1A1A', 'text_secondary': '#555555', 'text_light': '#888888',
            'header_bg': '#6C3483', 'footer_color': '#9988BB',
            'bg_pattern': 'molecule', 'decor_icon': 'flask',
        },
        '生物': {
            'primary': '#1E8449', 'accent': '#F0B27A', 'accent2': '#58D68D',
            'bg': '#EAF7EA', 'card_bg': '#FFFFFF', 'card_border': '#B8D8B8',
            'text': '#1A1A1A', 'text_secondary': '#555555', 'text_light': '#888888',
            'header_bg': '#1E8449', 'footer_color': '#77AA77',
            'bg_pattern': 'cell_outline', 'decor_icon': 'leaf',
        },
        '历史': {
            'primary': '#7D5A3C', 'accent': '#CB4335', 'accent2': '#D4AC0D',
            'bg': '#F8F3EA', 'card_bg': '#FFFDF8', 'card_border': '#D0C0A0',
            'text': '#2D2D2D', 'text_secondary': '#666666', 'text_light': '#999999',
            'header_bg': '#7D5A3C', 'footer_color': '#AA9977',
            'bg_pattern': 'parchment', 'decor_icon': 'scroll',
            'title_font': 'STSong, SimSun, serif',
        },
        '地理': {
            'primary': '#2E7D32', 'accent': '#0288D1', 'accent2': '#00897B',
            'bg': '#E8F5E9', 'card_bg': '#FFFFFF', 'card_border': '#A8D0B0',
            'text': '#1A1A1A', 'text_secondary': '#555555', 'text_light': '#888888',
            'header_bg': '#2E7D32', 'footer_color': '#66AA77',
            'bg_pattern': 'map_contour', 'decor_icon': 'globe',
        },
        '信息技术': {
            'primary': '#00FF88', 'accent': '#FF6B6B', 'accent2': '#FFD93D',
            'bg': '#0D1117', 'card_bg': '#161B22', 'card_border': '#30363D',
            'text': '#E6EDF3', 'text_secondary': '#8B949E', 'text_light': '#6E7681',
            'header_bg': '#161B22', 'footer_color': '#6E7681',
            'bg_pattern': 'code_matrix', 'decor_icon': 'terminal',
            'title_font': 'Consolas, Microsoft YaHei, monospace',
        },
        '政治': {
            'primary': '#C0392B', 'accent': '#D4AC0D', 'accent2': '#A93226',
            'bg': '#FFFDF5', 'card_bg': '#FFFFFF', 'card_border': '#E0C8B0',
            'text': '#1A1A1A', 'text_secondary': '#555555', 'text_light': '#888888',
            'header_bg': '#C0392B', 'footer_color': '#CC9966',
            'bg_pattern': 'stripe', 'decor_icon': 'star',
        },
    }

    # 查找匹配的学科，用学科配色覆盖 base_theme
    for key, overrides in SUBJECT_THEMES.items():
        if key in subject:
            theme = base_theme.copy()
            theme.update(overrides)
            return theme

    return base_theme

    # 默认配色
    return {
        'primary': '#37474F',
        'accent': '#1976D2',
        'accent2': '#43A047',
        'bg': '#FAFAFA',
        'card_bg': '#FFFFFF',
        'card_border': '#E0E0E0',
        'text': '#1A1A1A',
        'text_secondary': '#555555',
        'header_bg': '#37474F',
        'decor_color': '#1976D2',
        'gradient_start': '#37474F',
        'gradient_end': '#1976D2',
    }


def get_template_id(subject: str = "", topic: str = "") -> str:
    """获取模板ID"""
    combined = f"{subject} {topic}"
    for keyword, template_id in SUBJECT_TEMPLATE_MAP.items():
        if keyword in combined:
            return template_id
    return "general"




# ─────────────────────── 项目创建 ───────────────────────

def create_project(project_name: str, fmt: str = "ppt169") -> str:
    """创建 ppt-master 项目，返回项目路径"""
    safe_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name[:50].replace(' ', '_')

    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "project_manager.py"),
        "init", safe_name,
        "--format", fmt,
        "--dir", str(PROJECTS_DIR),
    ]

    result = subprocess.run(
        cmd, capture_output=True, cwd=str(PPT_MASTER_DIR),
        encoding='utf-8', errors='replace',
    )
    logger.info(f"project_manager init: {result.stdout[:300]}")
    if result.returncode != 0:
        logger.warning(f"init stderr: {result.stderr[:300]}")

    # 查找创建的项目目录
    pattern = str(PROJECTS_DIR / f"{safe_name}*")
    project_dirs = glob.glob(pattern)
    if not project_dirs:
        if "Project created:" in result.stdout:
            created_path = result.stdout.split("Project created:")[1].split("\n")[0].strip()
            full = PPT_MASTER_DIR / created_path
            if full.exists():
                return str(full)
        raise RuntimeError(f"创建项目失败: {result.stdout}\n{result.stderr}")

    project_path = max(project_dirs, key=os.path.getmtime)
    return project_path


# ─────────────────────── 设计规范生成 ───────────────────────

def generate_design_spec(project_path: str, topic: str, page_specs: list,
                         theme: dict, subject: str = "", grade: str = "") -> str:
    """生成 design_spec.md"""
    page_count = len(page_specs)
    outline_table = "\n".join(
        f"| {i+1:02d} | {spec['title']} | {spec['rhythm']} | {spec['layout']} |"
        for i, spec in enumerate(page_specs)
    )

    spec_md = f"""# {topic} — Design Spec

## I. Project Information

| Item | Value |
| ---- | ----- |
| **Project Name** | {topic} |
| **Canvas Format** | PPT 16:9 (1280x720) |
| **Page Count** | {page_count} |
| **Design Style** | 新中式文艺风格 |
| **Target Audience** | {grade or '学生'} |
| **Use Case** | {subject or '语文'}教学课件 |
| **Created Date** | {datetime.now().strftime('%Y-%m-%d')} |

## II. Canvas Specification

| Property | Value |
| -------- | ----- |
| **Format** | PPT 16:9 |
| **Dimensions** | 1280x720 |
| **viewBox** | `0 0 1280 720` |
| **Margins** | left/right 60px, top/bottom 50px |
| **Content Area** | 1160x620 |

## III. Visual Theme

### Color Scheme

| Role | HEX | Purpose |
| ---- | --- | ------- |
| **Background** | `{theme['bg']}` | 页面背景 |
| **Primary** | `{theme['primary']}` | 标题装饰、关键区块、图标 |
| **Accent** | `{theme['accent']}` | 数据高亮、强调色 |
| **Body text** | `{theme['text']}` | 正文文字 |
| **Secondary text** | `{theme['text_secondary']}` | 标注、说明 |
| **Tertiary text** | `{theme['text_light']}` | 页码、补充信息 |
| **Card background** | `{theme['card_bg']}` | 卡片背景 |
| **Card border** | `{theme['card_border']}` | 卡片边框 |

### Typography

| Role | Font | Weight |
| ---- | ---- | ------ |
| **Title** | {theme['title_font']} | Bold |
| **Body** | {theme['body_font']} | Regular |
baseline: 20,

**Baseline**: {theme['baseline']}px

### Font Size Hierarchy

| Purpose | Size | Weight |
| ------- | ---- | ------ |
| Cover title | 52-60px | Bold |
| Page title | 36px | Bold |
| Section subtitle | 24-28px | Bold |
| Body content | 20px | Regular |
| Annotation | 16px | Regular |
| Page number | 11px | Regular |

## IV. Icon Library

Source: `tabler-outline` (stroke-width 2)

## V. Content Outline

| Page | Title | Rhythm | Layout |
| ---- | ----- | ------ | ------ |
{outline_table}

## VI. Page Rhythm

- **anchor**: 结构性页面（封面、结束页、章节分隔页）
- **dense**: 信息密集页面（知识点、分析、列表）
- **breathing**: 低密度留白页面（引文、主题思想、过渡页）

## VII. Speaker Notes Requirements

- **Duration**: 约{max(10, page_count * 2)}分钟
- **Style**: 专业生动，适合课堂讲解
- **Purpose**: {subject or '语文'}教学
"""
    spec_path = Path(project_path) / "design_spec.md"
    spec_path.write_text(spec_md, encoding='utf-8')
    return str(spec_path)


def generate_spec_lock(project_path: str, topic: str, page_specs: list,
                       theme: dict) -> str:
    """生成 spec_lock.md"""
    pages_yaml = "\n".join(
        f"  - id: {i+1:02d}\n    title: \"{spec['title']}\"\n    rhythm: {spec['rhythm']}\n    layout: {spec['layout']}"
        for i, spec in enumerate(page_specs)
    )

    lock_md = f"""# Spec Lock — {topic}

## Canvas

- format: ppt169
- width: 1280
- height: 720
- viewBox: "0 0 1280 720"

## Colors

- bg: "{theme['bg']}"
- primary: "{theme['primary']}"
- accent: "{theme['accent']}"
- text: "{theme['text']}"
- text_secondary: "{theme['text_secondary']}"
- text_light: "{theme['text_light']}"
- card_bg: "{theme['card_bg']}"
- card_border: "{theme['card_border']}"

## Typography

- title_font: "{theme['title_font']}"
- body_font: "{theme['body_font']}"
- baseline: {theme['baseline']}
- title_size: 36
- subtitle_size: 24
- body_size: 20
- annotation_size: 16
- page_number_size: 11

## Icons

- source: tabler-outline
- stroke_width: 2

## Pages

{pages_yaml}
"""
    lock_path = Path(project_path) / "spec_lock.md"
    lock_path.write_text(lock_md, encoding='utf-8')
    return str(lock_path)


# ─────────────────────── SVG 生成引擎 ───────────────────────

def _svg_header() -> str:
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">'


def _svg_footer(page_num: int, total: int, theme: dict) -> str:
    """渲染页脚，根据模板的 decor_icon 添加学科装饰"""
    # 确保参数不为 None
    if page_num is None:
        page_num = 1
    if total is None:
        total = 1

    c = theme
    footer_y = c.get("footer_y", 680)
    text_y = footer_y + 20
    bar_y = 716
    footer_color = c.get("footer_color", c.get("text_light", "#999999"))
    body_font = c.get("body_font", "Microsoft YaHei, PingFang SC, Arial, sans-serif")
    primary = c["primary"]
    accent = c.get("accent", "#CC0000")
    decor = c.get("decor_icon", "none")

    svg = f'  <text x="1220" y="{text_y}" text-anchor="end" font-family="{body_font}" font-size="11" fill="{footer_color}">{page_num:02d} / {total:02d}</text>\n'

    # 学科装饰图标
    if decor == "brush":
        # 语文：毛笔小墨点
        svg += f'  <circle cx="80" cy="{text_y - 4}" r="3" fill="{primary}" fill-opacity="0.25"/>\n'
        svg += f'  <path d="M70,{text_y} Q75,{text_y - 6} 85,{text_y - 2}" fill="none" stroke="{primary}" stroke-opacity="0.20" stroke-width="1" stroke-linecap="round"/>\n'
    elif decor == "geometric":
        # 数学：小三角形
        svg += f'  <polygon points="80,{text_y - 8} 72,{text_y} 88,{text_y}" fill="none" stroke="{accent}" stroke-opacity="0.20" stroke-width="1"/>\n'
    elif decor == "atom":
        # 物理：小原子
        svg += f'  <circle cx="80" cy="{text_y - 4}" r="4" fill="none" stroke="{accent}" stroke-opacity="0.20" stroke-width="0.8"/>\n'
        svg += f'  <circle cx="80" cy="{text_y - 4}" r="1.5" fill="{accent}" fill-opacity="0.18"/>\n'
    elif decor == "flask":
        # 化学：小烧杯
        svg += f'  <rect x="74" y="{text_y - 8}" width="12" height="10" rx="1" fill="none" stroke="{primary}" stroke-opacity="0.20" stroke-width="0.8"/>\n'
    elif decor == "leaf":
        # 生物：小叶子
        svg += f'  <path d="M75,{text_y} Q80,{text_y - 10} 85,{text_y}" fill="none" stroke="{primary}" stroke-opacity="0.20" stroke-width="1" stroke-linecap="round"/>\n'
    elif decor == "chat":
        # 英语：小气泡
        svg += f'  <rect x="72" y="{text_y - 10}" width="16" height="10" rx="5" fill="none" stroke="{accent}" stroke-opacity="0.20" stroke-width="0.8"/>\n'
    elif decor == "scroll":
        # 历史：小卷轴
        svg += f'  <rect x="72" y="{text_y - 8}" width="16" height="8" rx="2" fill="none" stroke="{primary}" stroke-opacity="0.20" stroke-width="0.8"/>\n'
    elif decor == "globe":
        # 地理：小地球
        svg += f'  <circle cx="80" cy="{text_y - 4}" r="5" fill="none" stroke="{accent}" stroke-opacity="0.20" stroke-width="0.8"/>\n'
        svg += f'  <line x1="75" y1="{text_y - 4}" x2="85" y2="{text_y - 4}" stroke="{accent}" stroke-opacity="0.12" stroke-width="0.5"/>\n'
    elif decor == "terminal":
        # 信息技术：终端提示符
        svg += f'  <text x="70" y="{text_y}" font-family="Consolas, monospace" font-size="10" fill="{primary}" fill-opacity="0.20">&gt;_</text>\n'
    elif decor == "star":
        # 政治：小星
        svg += f'  <text x="76" y="{text_y}" font-family="{body_font}" font-size="10" fill="{accent}" fill-opacity="0.20">★</text>\n'

    # 底部装饰条
    bar_color = accent if c.get("bg_pattern") == "stripe" else primary
    svg += f'  <rect x="0" y="{bar_y}" width="1280" height="4" fill="{bar_color}" fill-opacity="0.4"/>\n'
    svg += '</svg>'

    return svg


def _top_bar(theme: dict) -> str:
    """根据模板的 bg_pattern 渲染顶部区域"""
    c = theme
    pattern = c.get("bg_pattern", "none")
    header_h = c.get("header_h", 70)
    header_bg = c.get("header_bg", c["primary"])
    accent = c.get("accent", "#CC0000")
    primary = c["primary"]

    if pattern == "code_matrix":
        # 信息技术科技风：霓虹双线
        return f"""  <rect x="0" y="0" width="1280" height="4" fill="{primary}" fill-opacity="0.8"/>
  <rect x="0" y="6" width="1280" height="2" fill="{primary}" fill-opacity="0.4"/>"""
    elif pattern == "stripe":
        # 政治庄重风：顶部渐变条
        return f"""  <rect x="0" y="0" width="1280" height="6" fill="{accent}" fill-opacity="0.8"/>
  <rect x="0" y="6" width="1280" height="2" fill="{primary}"/>"""
    elif pattern in ("xuan_paper", "parchment", "bubble"):
        # 语文/历史/英语温暖风：细线 + 渐变感
        return f"""  <rect x="0" y="0" width="1280" height="3" fill="{primary}" fill-opacity="0.6"/>
  <rect x="60" y="8" width="200" height="2" fill="{accent}" fill-opacity="0.4"/>"""
    else:
        # 默认学术风：深色header条
        accent_w = c.get("accent_bar_w", 6)
        return f"""  <rect x="0" y="0" width="1280" height="4" fill="{header_bg}"/>
  <rect x="0" y="4" width="{accent_w}" height="20" fill="{accent}"/>"""


def _page_title_block(title: str, icon: str, theme: dict, y: int = 66) -> str:
    """根据模板的 bg_pattern 渲染页面标题"""
    c = theme
    pattern = c.get("bg_pattern", "none")
    primary = c["primary"]
    accent = c.get("accent", "#CC0000")
    text_color = c.get("text", "#1A1A1A")
    title_font = c.get("title_font", "Microsoft YaHei, SimHei, Arial, sans-serif")

    if pattern == "code_matrix":
        # 信息技术科技风：霓虹标题
        tech_font = c.get("title_font", "Consolas, monospace")
        return f"""  <text x="60" y="50" font-family="{tech_font}" font-size="14" fill="{primary}" fill-opacity="0.6">&gt; {title}</text>
  <text x="60" y="78" font-family="{tech_font}" font-size="32" font-weight="bold" fill="{primary}">{title}</text>
  <rect x="60" y="88" width="300" height="2" fill="{primary}" fill-opacity="0.5"/>"""
    elif pattern == "stripe":
        # 政治庄重风：编号块 + 标题
        return f"""  <rect x="60" y="30" width="50" height="50" rx="4" fill="{primary}"/>
  <text x="85" y="64" text-anchor="middle" font-family="{title_font}" font-size="24" font-weight="bold" fill="#FFFFFF">1</text>
  <text x="125" y="64" font-family="{title_font}" font-size="28" font-weight="bold" fill="{text_color}">{title}</text>"""
    elif pattern in ("xuan_paper", "parchment", "bubble"):
        # 语文/历史/英语温暖风：竖条 + 标题 + 装饰线
        return f"""  <rect x="60" y="30" width="4" height="40" rx="2" fill="{accent}"/>
  <text x="76" y="66" font-family="{title_font}" font-size="32" font-weight="bold" fill="{text_color}">{title}</text>
  <rect x="76" y="76" width="160" height="2" rx="1" fill="{primary}" fill-opacity="0.3"/>"""
    else:
        # 默认学术风：深色header + 红色竖条
        header_bg = c.get("header_bg", primary)
        accent_w = c.get("accent_bar_w", 6)
        return f"""  <rect x="0" y="0" width="1280" height="70" fill="{header_bg}" fill-opacity="0.95"/>
  <rect x="0" y="0" width="{accent_w}" height="70" fill="{accent}"/>
  <text x="24" y="46" font-family="{title_font}" font-size="26" font-weight="bold" fill="#FFFFFF">{title}</text>"""


def _escape_xml(text: str) -> str:
    """转义 XML 特殊字符，防止 SVG 解析错误"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_background(theme: dict) -> str:
    """根据模板的 bg_pattern 属性渲染页面背景装饰，不依赖 style"""
    c = theme
    bg = c["bg"]
    primary = c["primary"]
    accent = c.get("accent", "#CC0000")
    accent2 = c.get("accent2", "#0066CC")
    pattern = c.get("bg_pattern", "none")

    # 基础背景
    svg = f'  <rect width="1280" height="720" fill="{bg}"/>'

    if pattern == "math_grid":
        # 数学：网格线 + 几何图形
        svg += (
            f'\n  <defs><pattern id="bgpat" width="40" height="40" patternUnits="userSpaceOnUse">'
            f'\n    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="{primary}" stroke-opacity="0.10" stroke-width="0.5"/>'
            f'\n  </pattern></defs>'
            f'\n  <rect width="1280" height="720" fill="url(#bgpat)"/>'
            f'\n  <circle cx="1100" cy="150" r="60" fill="none" stroke="{accent}" stroke-opacity="0.12" stroke-width="1"/>'
            f'\n  <rect x="1050" y="500" width="80" height="80" rx="4" fill="none" stroke="{primary}" stroke-opacity="0.10" stroke-width="1" transform="rotate(15 1090 540)"/>'
        )
    elif pattern == "atom_orbit":
        # 物理：原子轨道
        svg += (
            f'\n  <circle cx="1100" cy="180" r="80" fill="none" stroke="{accent}" stroke-opacity="0.12" stroke-width="1"/>'
            f'\n  <circle cx="1100" cy="180" r="50" fill="none" stroke="{accent}" stroke-opacity="0.10" stroke-width="0.8"/>'
            f'\n  <circle cx="1100" cy="180" r="20" fill="none" stroke="{accent}" stroke-opacity="0.14" stroke-width="1"/>'
            f'\n  <circle cx="1100" cy="180" r="5" fill="{accent}" fill-opacity="0.15"/>'
            f'\n  <ellipse cx="1100" cy="180" rx="80" ry="30" fill="none" stroke="{accent2}" stroke-opacity="0.10" stroke-width="0.8" transform="rotate(-30 1100 180)"/>'
        )
    elif pattern == "molecule":
        # 化学：分子结构
        svg += (
            f'\n  <circle cx="1100" cy="200" r="12" fill="none" stroke="{accent}" stroke-opacity="0.14" stroke-width="1.5"/>'
            f'\n  <circle cx="1140" cy="170" r="10" fill="none" stroke="{accent2}" stroke-opacity="0.12" stroke-width="1.5"/>'
            f'\n  <circle cx="1060" cy="175" r="10" fill="none" stroke="{primary}" stroke-opacity="0.12" stroke-width="1.5"/>'
            f'\n  <line x1="1100" y1="188" x2="1140" y2="180" stroke="{accent}" stroke-opacity="0.10" stroke-width="1"/>'
            f'\n  <line x1="1100" y1="188" x2="1060" y2="183" stroke="{primary}" stroke-opacity="0.10" stroke-width="1"/>'
            f'\n  <circle cx="120" cy="580" r="8" fill="none" stroke="{accent2}" stroke-opacity="0.10" stroke-width="1"/>'
        )
    elif pattern == "cell_outline":
        # 生物：细胞轮廓
        svg += (
            f'\n  <ellipse cx="1100" cy="550" rx="120" ry="80" fill="none" stroke="{accent2}" stroke-opacity="0.12" stroke-width="1.5"/>'
            f'\n  <circle cx="1100" cy="540" r="25" fill="none" stroke="{primary}" stroke-opacity="0.12" stroke-width="1"/>'
            f'\n  <circle cx="1100" cy="540" r="8" fill="{primary}" fill-opacity="0.08"/>'
            f'\n  <circle cx="1060" cy="570" r="5" fill="{accent2}" fill-opacity="0.08"/>'
            f'\n  <circle cx="1130" cy="520" r="4" fill="{accent2}" fill-opacity="0.08"/>'
        )
    elif pattern == "xuan_paper":
        # 语文：宣纸纹理 + 毛笔笔触
        svg += (
            f'\n  <defs><pattern id="bgpat" width="100" height="100" patternUnits="userSpaceOnUse">'
            f'\n    <rect width="100" height="100" fill="none" stroke="{primary}" stroke-opacity="0.04" stroke-width="0.3"/>'
            f'\n  </pattern></defs>'
            f'\n  <rect width="1280" height="720" fill="url(#bgpat)"/>'
            f'\n  <path d="M1050,100 Q1080,70 1100,120 Q1115,160 1090,180" fill="none" stroke="{primary}" stroke-opacity="0.12" stroke-width="2.5" stroke-linecap="round"/>'
            f'\n  <path d="M100,550 Q140,520 150,560 Q155,590 125,600" fill="none" stroke="{accent}" stroke-opacity="0.10" stroke-width="2" stroke-linecap="round"/>'
            f'\n  <circle cx="1055" cy="185" r="3" fill="{primary}" fill-opacity="0.08"/>'
        )
    elif pattern == "bubble":
        # 英语：对话气泡
        svg += (
            f'\n  <rect x="1050" y="120" width="100" height="60" rx="20" fill="none" stroke="{accent}" stroke-opacity="0.12" stroke-width="1"/>'
            f'\n  <polygon points="1080,180 1100,200 1120,180" fill="none" stroke="{accent}" stroke-opacity="0.10" stroke-width="1"/>'
            f'\n  <rect x="130" y="520" width="80" height="45" rx="15" fill="none" stroke="{accent2}" stroke-opacity="0.10" stroke-width="1"/>'
            f'\n  <circle cx="1100" cy="600" r="40" fill="{primary}" fill-opacity="0.10"/>'
        )
    elif pattern == "parchment":
        # 历史：羊皮纸纹理
        svg += (
            f'\n  <defs><pattern id="bgpat" width="200" height="200" patternUnits="userSpaceOnUse">'
            f'\n    <rect width="200" height="200" fill="none" stroke="{primary}" stroke-opacity="0.05" stroke-width="0.3"/>'
            f'\n  </pattern></defs>'
            f'\n  <rect width="1280" height="720" fill="url(#bgpat)"/>'
            f'\n  <path d="M1050,100 Q1100,80 1150,120 Q1180,160 1120,200 Q1080,180 1050,140 Z" fill="none" stroke="{primary}" stroke-opacity="0.10" stroke-width="1"/>'
            f'\n  <circle cx="1100" cy="150" r="3" fill="{accent}" fill-opacity="0.15"/>'
        )
    elif pattern == "map_contour":
        # 地理：地图等高线
        svg += (
            f'\n  <path d="M1020,120 Q1080,100 1140,130 Q1160,180 1100,200 Q1040,190 1020,150 Z" fill="none" stroke="{accent}" stroke-opacity="0.12" stroke-width="1"/>'
            f'\n  <path d="M1040,140 Q1080,125 1120,145 Q1135,170 1095,185 Q1055,178 1040,160 Z" fill="none" stroke="{accent2}" stroke-opacity="0.10" stroke-width="0.8"/>'
            f'\n  <circle cx="1080" cy="155" r="3" fill="{accent}" fill-opacity="0.12"/>'
        )
    elif pattern == "code_matrix":
        # 信息技术：代码矩阵
        svg += (
            f'\n  <defs><pattern id="bgpat" width="32" height="32" patternUnits="userSpaceOnUse">'
            f'\n    <rect width="32" height="32" fill="none" stroke="{primary}" stroke-opacity="0.10" stroke-width="0.3"/>'
            f'\n  </pattern></defs>'
            f'\n  <rect width="1280" height="720" fill="url(#bgpat)"/>'
            f'\n  <text x="1100" y="100" font-family="Consolas, monospace" font-size="10" fill="{primary}" fill-opacity="0.12">01001101</text>'
            f'\n  <text x="1100" y="120" font-family="Consolas, monospace" font-size="10" fill="{primary}" fill-opacity="0.12">10110010</text>'
            f'\n  <text x="1100" y="140" font-family="Consolas, monospace" font-size="10" fill="{primary}" fill-opacity="0.12">11001010</text>'
            f'\n  <rect x="50" y="600" width="60" height="2" fill="{primary}" fill-opacity="0.12"/>'
            f'\n  <rect x="120" y="600" width="40" height="2" fill="{primary}" fill-opacity="0.08"/>'
        )
    elif pattern == "stripe":
        # 政治：渐变条纹
        svg += (
            f'\n  <rect x="0" y="0" width="1280" height="4" fill="{accent}" fill-opacity="0.6"/>'
            f'\n  <rect x="0" y="716" width="1280" height="4" fill="{accent}" fill-opacity="0.4"/>'
            f'\n  <rect x="60" y="100" width="3" height="520" fill="{primary}" fill-opacity="0.08"/>'
            f'\n  <rect x="1217" y="100" width="3" height="520" fill="{primary}" fill-opacity="0.08"/>'
        )

    return svg


def _render_top_bar(theme: dict, title: str, style_hint: str = "") -> str:
    """渲染顶部标题栏，直接使用模板属性，不依赖 style"""
    c = theme
    primary = c["primary"]
    accent = c.get("accent", "#CC0000")
    title_font = c.get("title_font", "Microsoft YaHei, SimHei, Arial, sans-serif")
    header_bg = c.get("header_bg", primary)
    header_h = c.get("header_h", 56)
    accent_w = c.get("accent_bar_w", 4)
    text_color = c.get("text", "#1A1A1A")
    bg_pattern = c.get("bg_pattern", "none")

    # 深色背景模板（信息技术）用霓虹风格
    if bg_pattern == "code_matrix":
        return (
            f'<rect x="0" y="0" width="1280" height="4" fill="{primary}" fill-opacity="0.8"/>'
            f'\n  <rect x="0" y="6" width="1280" height="2" fill="{primary}" fill-opacity="0.4"/>'
            f'\n  <text x="60" y="40" font-family="Consolas, monospace" font-size="14" fill="{primary}" fill-opacity="0.5">&gt; {title}.slide</text>'
            f'\n  <text x="60" y="75" font-family="Consolas, monospace" font-size="30" font-weight="bold" fill="{primary}">{title}</text>'
            f'\n  <rect x="60" y="85" width="250" height="2" fill="{primary}" fill-opacity="0.4"/>'
        )

    # 浅色文字模板（深色header）用白色文字
    if header_h >= 50:
        return (
            f'<rect x="0" y="0" width="1280" height="{header_h}" fill="{header_bg}" fill-opacity="0.95"/>'
            f'\n  <rect x="0" y="0" width="{accent_w}" height="{header_h}" fill="{accent}"/>'
            f'\n  <text x="24" y="{header_h - 24}" font-family="{title_font}" font-size="26" font-weight="bold" fill="#FFFFFF">{title}</text>'
        )

    # 短header + 页面内标题
    return (
        f'<rect x="0" y="0" width="1280" height="{header_h}" fill="{header_bg}" fill-opacity="0.9"/>'
        f'\n  <rect x="0" y="{header_h - 3}" width="1280" height="3" fill="{accent}" fill-opacity="0.6"/>'
        f'\n  <text x="60" y="{header_h + 30}" font-family="{title_font}" font-size="28" font-weight="bold" fill="{text_color}">{title}</text>'
    )


def _wrap_text(text: str, max_chars: int = 18) -> list:
    """将长文本按指定字符数自动换行（自动转义XML特殊字符）"""
    text = _escape_xml(text)
    if len(text) <= max_chars:
        return [text]
    lines = []
    while text:
        if len(text) <= max_chars:
            lines.append(text)
            break
        # 找一个合适的断点（标点、空格）
        cut = max_chars
        for bp in range(min(max_chars, len(text)), max(max_chars - 6, 0), -1):
            if text[bp] in '，。、；：！？）》」』,.;:!?) ':
                cut = bp + 1
                break
        lines.append(text[:cut])
        text = text[cut:]
    return lines


def generate_enhanced_decorations(theme: dict, layout: str = "cover") -> str:
    """生成增强装饰元素"""
    c = theme
    primary = c.get('primary', '#37474F')
    accent = c.get('accent', '#1976D2')
    gradient_start = c.get('gradient_start', primary)
    gradient_end = c.get('gradient_end', accent)

    decorations = []

    # 渐变背景
    decorations.append(f'''  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{gradient_start}" stop-opacity="0.12" />
      <stop offset="100%" stop-color="{gradient_end}" stop-opacity="0.08" />
    </linearGradient>
    <linearGradient id="accentLine" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{gradient_start}" />
      <stop offset="100%" stop-color="{gradient_end}" />
    </linearGradient>
  </defs>''')

    # 装饰圆形
    if layout == "cover":
        decorations.append(f'''  <rect width="1280" height="720" fill="url(#bgGrad)" />
  <circle cx="80" cy="120" r="60" fill="{primary}" fill-opacity="0.06" />
  <circle cx="140" cy="200" r="40" fill="{primary}" fill-opacity="0.04" />
  <circle cx="60" cy="300" r="30" fill="{accent}" fill-opacity="0.05" />
  <circle cx="1200" cy="580" r="70" fill="{primary}" fill-opacity="0.06" />
  <circle cx="1140" cy="500" r="45" fill="{accent}" fill-opacity="0.04" />''')
    elif layout in ["three_card", "four_card", "grid_2x2"]:
        decorations.append(f'''  <rect x="0" y="0" width="1280" height="4" fill="url(#accentLine)" />
  <circle cx="1200" cy="100" r="30" fill="{primary}" fill-opacity="0.06" />
  <circle cx="80" cy="650" r="25" fill="{accent}" fill-opacity="0.05" />''')
    elif layout == "split":
        decorations.append(f'''  <rect x="0" y="0" width="1280" height="3" fill="url(#accentLine)" />
  <circle cx="640" cy="360" r="200" fill="{primary}" fill-opacity="0.03" />''')
    else:
        decorations.append(f'''  <rect x="0" y="0" width="1280" height="3" fill="url(#accentLine)" />''')

    return '\n'.join(decorations)


def generate_cover_svg(topic: str, subtitle: str, info: str, theme: dict, total: int = 12) -> str:
    """封面页 — 按 bg_pattern + header_h 生成不同结构"""
    c = theme
    pattern = c.get("bg_pattern", "none")
    header_h = c.get("header_h", 56)

    if pattern == "code_matrix":
        # 信息技术科技风：深色背景 + 霓虹
        return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  <rect x="0" y="0" width="1280" height="4" fill="{c['primary']}" fill-opacity="0.8"/>
  <rect x="0" y="6" width="1280" height="2" fill="{c['primary']}" fill-opacity="0.4"/>
  <text x="60" y="200" font-family="Consolas, monospace" font-size="16" fill="{c['primary']}" fill-opacity="0.5">&gt; loading presentation...</text>
  <text x="60" y="340" font-family="Consolas, monospace" font-size="56" font-weight="bold" fill="{c['primary']}">{topic}</text>
  <rect x="60" y="360" width="400" height="3" fill="{c['primary']}" fill-opacity="0.6"/>
  <text x="60" y="400" font-family="{c['body_font']}" font-size="20" fill="{c['text_secondary']}">{subtitle}</text>
  <rect x="60" y="600" width="200" height="36" rx="4" fill="{c['primary']}" fill-opacity="0.15" stroke="{c['primary']}" stroke-width="1" stroke-opacity="0.4"/>
  <text x="160" y="624" text-anchor="middle" font-family="Consolas, monospace" font-size="14" fill="{c['primary']}">PRESS START</text>
  <text x="60" y="680" font-family="Consolas, monospace" font-size="12" fill="{c['text_light']}">{info}</text>
  {_svg_footer(1, total, c)}"""

    elif pattern == "stripe":
        # 政治庄重风：编号块 + 横条
        return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  <rect x="0" y="0" width="1280" height="6" fill="{c['accent']}" fill-opacity="0.8"/>
  <rect x="0" y="6" width="1280" height="2" fill="{c['primary']}"/>
  <rect x="60" y="280" width="6" height="160" rx="3" fill="{c['primary']}"/>
  <text x="90" y="360" font-family="{c['title_font']}" font-size="52" font-weight="bold" fill="{c['text']}">{topic}</text>
  <text x="90" y="410" font-family="{c['body_font']}" font-size="22" fill="{c['text_secondary']}">{subtitle}</text>
  <rect x="90" y="430" width="150" height="3" rx="1.5" fill="{c['accent']}"/>
  <rect x="0" y="620" width="1280" height="100" fill="{c['primary']}" fill-opacity="0.12"/>
  <text x="90" y="660" font-family="{c['body_font']}" font-size="16" fill="{c['text_light']}">{info}</text>
  {_svg_footer(1, total, c)}"""

    elif pattern in ("xuan_paper", "parchment", "bubble"):
        # 语文/历史/英语温暖风：竖条 + 圆形装饰
        return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  <rect x="0" y="0" width="1280" height="3" fill="{c['primary']}" fill-opacity="0.5"/>
  <circle cx="200" cy="250" r="120" fill="{c['primary']}" fill-opacity="0.10"/>
  <circle cx="1050" cy="500" r="100" fill="{c['accent']}" fill-opacity="0.10"/>
  <rect x="60" y="260" width="4" height="120" rx="2" fill="{c['accent']}"/>
  <text x="80" y="330" font-family="{c['title_font']}" font-size="50" font-weight="bold" fill="{c['text']}">{topic}</text>
  <text x="80" y="380" font-family="{c['body_font']}" font-size="22" fill="{c['text_secondary']}">{subtitle}</text>
  <rect x="80" y="400" width="120" height="3" rx="1.5" fill="{c['accent']}" fill-opacity="0.4"/>
  <rect x="0" y="620" width="1280" height="100" fill="{c['primary']}" fill-opacity="0.10"/>
  <text x="80" y="660" font-family="{c['body_font']}" font-size="15" fill="{c['text_light']}">{info}</text>
  {_svg_footer(1, total, c)}"""

    elif header_h >= 60:
        # 学术深色header风：数学/物理/化学/生物/地理
        return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  <rect x="0" y="0" width="1280" height="{header_h}" fill="{c['header_bg']}" fill-opacity="0.95"/>
  <rect x="0" y="0" width="{c.get('accent_bar_w', 6)}" height="{header_h}" fill="{c['accent']}"/>
  <circle cx="1100" cy="360" r="200" fill="{c.get('accent2', c['accent'])}" fill-opacity="0.10"/>
  <circle cx="180" cy="300" r="100" fill="{c['primary']}" fill-opacity="0.10"/>
  <rect x="60" y="240" width="5" height="160" rx="2" fill="{c['accent']}"/>
  <text x="85" y="320" font-family="{c['title_font']}" font-size="54" font-weight="bold" fill="{c['text']}">{topic}</text>
  <text x="85" y="375" font-family="{c['body_font']}" font-size="22" fill="{c['text_secondary']}">{subtitle}</text>
  <rect x="85" y="395" width="100" height="3" rx="1.5" fill="{c.get('accent2', c['accent'])}" fill-opacity="0.5"/>
  <rect x="0" y="620" width="1280" height="100" fill="{c['primary']}" fill-opacity="0.12"/>
  <text x="85" y="660" font-family="{c['body_font']}" font-size="16" fill="{c['text_light']}">{info}</text>
  {_svg_footer(1, total, c)}"""

    else:
        # 默认学术风（增强版）
        return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {generate_enhanced_decorations(c, 'cover')}
  {_top_bar(c)}
  <rect x="80" y="220" width="6" height="180" rx="3" fill="{c['accent']}"/>
  <text x="110" y="300" font-family="{c['title_font']}" font-size="56" font-weight="bold" fill="{c['text']}">{topic}</text>
  <text x="110" y="360" font-family="{c['body_font']}" font-size="24" fill="{c['text_secondary']}">{subtitle}</text>
  <rect x="0" y="600" width="1280" height="120" fill="{c['primary']}" fill-opacity="0.14"/>
  <text x="110" y="650" font-family="{c['body_font']}" font-size="16" fill="{c['text_light']}">{info}</text>
  <rect x="110" y="670" width="120" height="3" rx="1.5" fill="{c['accent']}" fill-opacity="0.6"/>
  {_svg_footer(1, total, c)}"""


def generate_toc_svg(items: list, theme: dict, total: int) -> str:
    """目录页"""
    c = theme
    rows = ""
    for i, item in enumerate(items[:8]):
        y = 160 + i * 60
        rows += f"""  <rect x="60" y="{y}" width="1160" height="48" rx="8" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="0.5"/>
  <circle cx="110" cy="{y+24}" r="18" fill="{c['primary']}" fill-opacity="0.15"/>
  <text x="110" y="{y+30}" text-anchor="middle" font-family="{c['body_font']}" font-size="16" font-weight="bold" fill="{c['primary']}">{i+1:02d}</text>
  <text x="150" y="{y+30}" font-family="{c['title_font']}" font-size="22" fill="{c['text']}">{item}</text>
"""

    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {_top_bar(c)}
  {_page_title_block("目录", "list", c)}

{rows}
  {_svg_footer(2, total, c)}
"""


def generate_three_card_svg(title: str, icon: str, cards: list,
                            theme: dict, page_num: int, total: int) -> str:
    """三栏卡片布局 — 按 bg_pattern + header_h 生成不同结构"""
    c = theme
    pattern = c.get("bg_pattern", "none")
    header_h = c.get("header_h", 56)

    if pattern == "code_matrix":
        return _tech_three_card(title, icon, cards, c, page_num, total)
    elif pattern == "stripe":
        return _gov_three_card(title, icon, cards, c, page_num, total)
    elif pattern in ("xuan_paper", "parchment", "bubble"):
        return _warm_three_card(title, icon, cards, c, page_num, total)
    elif header_h >= 60:
        return _academic_three_card(title, icon, cards, c, page_num, total)
    else:
        return _warm_three_card(title, icon, cards, c, page_num, total)


def _academic_three_card(title, icon, cards, c, page_num, total):
    """学术风格：深色header + 结构化卡片"""
    card_w = 360
    gap = 30
    start_x = (1280 - 3 * card_w - 2 * gap) // 2
    cards_svg = ""
    for i, card in enumerate(cards[:3]):
        x = start_x + i * (card_w + gap)
        cards_svg += f"""
  <rect x="{x}" y="120" width="{card_w}" height="520" rx="12" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="1"/>
  <rect x="{x}" y="120" width="{card_w}" height="60" rx="12" fill="{c['primary']}" fill-opacity="0.12"/>
  <rect x="{x}" y="156" width="{card_w}" height="24" fill="{c['primary']}" fill-opacity="0.12"/>
  <circle cx="{x + card_w//2}" cy="150" r="22" fill="{c['primary']}" fill-opacity="0.2"/>
  <text x="{x + card_w//2}" y="158" text-anchor="middle" font-family="{c['title_font']}" font-size="20" font-weight="bold" fill="{c['primary']}">{card.get('number', str(i+1))}</text>
  <text x="{x + card_w//2}" y="210" text-anchor="middle" font-family="{c['title_font']}" font-size="22" font-weight="bold" fill="{c['text']}">{_escape_xml(card['title'])}</text>
  <rect x="{x + card_w//2 - 60}" y="225" width="120" height="2" fill="{c['accent']}" fill-opacity="0.4"/>
  <text x="{x + 30}" y="270" font-family="{c['body_font']}" font-size="16" fill="{c['text']}">"""
        wrapped = []
        for line in card.get('lines', []):
            wrapped.extend(_wrap_text(line, 18))
        for j, line in enumerate(wrapped[:10]):
            cards_svg += f'\n    <tspan x="{x+30}" dy="{0 if j==0 else 26}">{line}</tspan>'
        cards_svg += "\n  </text>"
    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {_top_bar(c)}
  {_page_title_block(title, icon, c)}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


def _gov_three_card(title, icon, cards, c, page_num, total):
    """政务风格：编号块 + 横向分割 + 庄重感"""
    section_y = 100
    cards_svg = ""
    for i, card in enumerate(cards[:3]):
        y = section_y + i * 190
        # 编号块
        cards_svg += f"""
  <rect x="60" y="{y}" width="50" height="50" rx="4" fill="{c['primary']}"/>
  <text x="85" y="{y+34}" text-anchor="middle" font-family="{c['title_font']}" font-size="24" font-weight="bold" fill="#FFFFFF">{card.get('number', str(i+1))}</text>
  <text x="130" y="{y+36}" font-family="{c['title_font']}" font-size="24" font-weight="bold" fill="{c['text']}">{_escape_xml(card['title'])}</text>
  <rect x="130" y="{y+48}" width="80" height="2" fill="{c['accent']}"/>
  <rect x="60" y="{y+60}" width="1160" height="110" rx="6" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="0.5"/>
  <text x="80" y="{y+90}" font-family="{c['body_font']}" font-size="16" fill="{c['text']}">"""
        wrapped = []
        for line in card.get('lines', []):
            wrapped.extend(_wrap_text(line, 40))
        for j, line in enumerate(wrapped[:3]):
            cards_svg += f'\n    <tspan x="80" dy="{0 if j==0 else 26}">{line}</tspan>'
        cards_svg += "\n  </text>"
    # 顶部装饰
    top = f"""  <rect x="0" y="0" width="1280" height="6" fill="{c['accent']}" fill-opacity="0.8"/>
  <rect x="0" y="6" width="1280" height="2" fill="{c['primary']}"/>
  <text x="60" y="50" font-family="{c['title_font']}" font-size="28" font-weight="bold" fill="{c['text']}">{title}</text>"""
    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {top}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


def _tech_three_card(title, icon, cards, c, page_num, total):
    """科技风格：深色背景 + 霓虹 + 终端感"""
    card_w = 360
    gap = 24
    start_x = (1280 - 3 * card_w - 2 * gap) // 2
    cards_svg = ""
    colors = [c['primary'], c['accent'], c['accent2']]
    for i, card in enumerate(cards[:3]):
        x = start_x + i * (card_w + gap)
        color = colors[i % 3]
        cards_svg += f"""
  <rect x="{x}" y="110" width="{card_w}" height="530" rx="4" fill="{c['card_bg']}" stroke="{color}" stroke-width="1" stroke-opacity="0.3"/>
  <rect x="{x}" y="110" width="{card_w}" height="4" fill="{color}" fill-opacity="0.8"/>
  <text x="{x+16}" y="150" font-family="Consolas, monospace" font-size="14" fill="{color}" fill-opacity="0.6">// {card.get('number', str(i+1))}</text>
  <text x="{x+16}" y="180" font-family="{c['title_font']}" font-size="22" font-weight="bold" fill="{color}">{_escape_xml(card['title'])}</text>
  <line x1="{x+16}" y1="192" x2="{x+card_w-16}" y2="192" stroke="{color}" stroke-opacity="0.2"/>
  <text x="{x+16}" y="220" font-family="{c['body_font']}" font-size="15" fill="{c['text']}">"""
        wrapped = []
        for line in card.get('lines', []):
            wrapped.extend(_wrap_text(line, 18))
        for j, line in enumerate(wrapped[:10]):
            cards_svg += f'\n    <tspan x="{x+16}" dy="{0 if j==0 else 24}">{line}</tspan>'
        cards_svg += "\n  </text>"
    # 终端风格 header
    top = f"""  <rect x="0" y="0" width="1280" height="4" fill="{c['primary']}" fill-opacity="0.8"/>
  <rect x="0" y="6" width="1280" height="2" fill="{c['primary']}" fill-opacity="0.4"/>
  <text x="60" y="40" font-family="Consolas, monospace" font-size="14" fill="{c['primary']}" fill-opacity="0.5">&gt; {title}.slide</text>
  <text x="60" y="75" font-family="Consolas, monospace" font-size="32" font-weight="bold" fill="{c['primary']}">{title}</text>
  <rect x="60" y="85" width="300" height="2" fill="{c['primary']}" fill-opacity="0.4"/>"""
    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {top}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


def _warm_three_card(title, icon, cards, c, page_num, total):
    """温暖风格：圆润卡片 + 暖色调 + 治愈感"""
    card_w = 350
    gap = 30
    start_x = (1280 - 3 * card_w - 2 * gap) // 2
    cards_svg = ""
    colors = [c['primary'], c['accent'], c['accent2']]
    for i, card in enumerate(cards[:3]):
        x = start_x + i * (card_w + gap)
        color = colors[i % 3]
        cards_svg += f"""
  <rect x="{x}" y="130" width="{card_w}" height="500" rx="20" fill="{c['card_bg']}" stroke="{color}" stroke-width="1.5" stroke-opacity="0.3"/>
  <circle cx="{x + card_w//2}" cy="170" r="28" fill="{color}" fill-opacity="0.15"/>
  <text x="{x + card_w//2}" y="178" text-anchor="middle" font-family="{c['title_font']}" font-size="20" font-weight="bold" fill="{color}">{card.get('number', str(i+1))}</text>
  <text x="{x + card_w//2}" y="225" text-anchor="middle" font-family="{c['title_font']}" font-size="22" font-weight="bold" fill="{c['text']}">{_escape_xml(card['title'])}</text>
  <rect x="{x + card_w//2 - 50}" y="240" width="100" height="3" rx="1.5" fill="{color}" fill-opacity="0.3"/>
  <text x="{x + 30}" y="280" font-family="{c['body_font']}" font-size="16" fill="{c['text']}">"""
        wrapped = []
        for line in card.get('lines', []):
            wrapped.extend(_wrap_text(line, 16))
        for j, line in enumerate(wrapped[:9]):
            cards_svg += f'\n    <tspan x="{x+30}" dy="{0 if j==0 else 26}">{line}</tspan>'
        cards_svg += "\n  </text>"
    # 温暖风格 header
    top = f"""  <rect x="0" y="0" width="1280" height="3" fill="{c['primary']}" fill-opacity="0.5"/>
  <rect x="60" y="20" width="4" height="40" rx="2" fill="{c['accent']}"/>
  <text x="76" y="56" font-family="{c['title_font']}" font-size="32" font-weight="bold" fill="{c['text']}">{title}</text>
  <rect x="76" y="66" width="160" height="2" rx="1" fill="{c['primary']}" fill-opacity="0.2"/>"""
    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {top}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


def _medical_three_card(title, icon, cards, c, page_num, total):
    """医学风格：蓝绿色header + 橙色accent + 生命科学感"""
    card_w = 360
    gap = 24
    start_x = (1280 - 3 * card_w - 2 * gap) // 2
    cards_svg = ""
    for i, card in enumerate(cards[:3]):
        x = start_x + i * (card_w + gap)
        # 左侧彩色竖条装饰
        bar_color = [c['primary'], c['accent'], c['accent2']][i % 3]
        cards_svg += f"""
  <rect x="{x}" y="120" width="{card_w}" height="520" rx="10" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="1"/>
  <rect x="{x}" y="120" width="5" height="520" rx="2" fill="{bar_color}"/>
  <text x="{x+24}" y="165" font-family="{c['title_font']}" font-size="22" font-weight="bold" fill="{c['text']}">{_escape_xml(card['title'])}</text>
  <rect x="{x+24}" y="178" width="60" height="2" fill="{bar_color}" fill-opacity="0.6"/>
  <text x="{x+24}" y="210" font-family="{c['body_font']}" font-size="16" fill="{c['text']}">"""
        wrapped = []
        for line in card.get('lines', []):
            wrapped.extend(_wrap_text(line, 17))
        for j, line in enumerate(wrapped[:10]):
            cards_svg += f'\n    <tspan x="{x+24}" dy="{0 if j==0 else 26}">{line}</tspan>'
        cards_svg += "\n  </text>"
    # 医学风格 header：蓝色条 + 橙色竖条
    top = f"""  <rect x="0" y="0" width="1280" height="70" fill="{c['header_bg']}" fill-opacity="0.95"/>
  <rect x="0" y="0" width="{c['accent_bar_w']}" height="70" fill="{c['accent']}"/>
  <text x="24" y="46" font-family="{c['title_font']}" font-size="26" font-weight="bold" fill="#FFFFFF">{title}</text>"""
    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {top}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_four_card_svg(title: str, icon: str, cards: list,
                           theme: dict, page_num: int, total: int) -> str:
    """四栏卡片布局 — 按 bg_pattern + header_h 生成不同结构"""
    c = theme
    pattern = c.get("bg_pattern", "none")
    header_h = c.get("header_h", 56)

    if pattern == "code_matrix":
        return _tech_four_card(title, icon, cards, c, page_num, total)
    elif pattern == "stripe":
        return _gov_four_card(title, icon, cards, c, page_num, total)
    elif pattern in ("xuan_paper", "parchment", "bubble"):
        return _warm_four_card(title, icon, cards, c, page_num, total)
    elif header_h >= 60:
        return _academic_four_card(title, icon, cards, c, page_num, total)
    else:
        return _warm_four_card(title, icon, cards, c, page_num, total)


def _academic_four_card(title, icon, cards, c, page_num, total):
    card_w = 280; gap = 20; start_x = (1280 - 4 * card_w - 3 * gap) // 2
    colors_cycle = [c['primary'], c['accent'], c['primary'], c['accent']]
    cards_svg = ""
    for i, card in enumerate(cards[:4]):
        x = start_x + i * (card_w + gap); color = colors_cycle[i % 4]
        cards_svg += f"""
  <rect x="{x}" y="110" width="{card_w}" height="520" rx="12" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="1"/>
  <rect x="{x}" y="110" width="{card_w}" height="60" rx="12" fill="{color}" fill-opacity="0.12"/>
  <circle cx="{x + card_w//2}" cy="140" r="22" fill="{color}" fill-opacity="0.2"/>
  <text x="{x + card_w//2}" y="148" text-anchor="middle" font-family="{c['title_font']}" font-size="20" font-weight="bold" fill="{color}">{card.get('number', ['一','二','三','四'][i])}</text>
  <text x="{x + card_w//2}" y="200" text-anchor="middle" font-family="{c['title_font']}" font-size="22" font-weight="bold" fill="{c['text']}">{_escape_xml(card['title'])}</text>
  <rect x="{x + card_w//2 - 60}" y="215" width="120" height="2" fill="{c['accent']}" fill-opacity="0.4"/>
  <text x="{x + 20}" y="260" font-family="{c['body_font']}" font-size="16" fill="{c['text']}">"""
        wrapped = []
        for line in card.get('lines', []): wrapped.extend(_wrap_text(line, 13))
        for j, line in enumerate(wrapped[:10]):
            cards_svg += f'\n    <tspan x="{x+20}" dy="{0 if j==0 else 26}">{line}</tspan>'
        cards_svg += "\n  </text>"
    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {_top_bar(c)}
  {_page_title_block(title, icon, c)}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


def _medical_four_card(title, icon, cards, c, page_num, total):
    card_w = 280; gap = 20; start_x = (1280 - 4 * card_w - 3 * gap) // 2
    bar_colors = [c['primary'], c['accent'], c['accent2'], c['primary']]
    cards_svg = ""
    for i, card in enumerate(cards[:4]):
        x = start_x + i * (card_w + gap); bar_color = bar_colors[i % 4]
        cards_svg += f"""
  <rect x="{x}" y="110" width="{card_w}" height="520" rx="10" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="1"/>
  <rect x="{x}" y="110" width="4" height="520" rx="2" fill="{bar_color}"/>
  <text x="{x+20}" y="155" font-family="{c['title_font']}" font-size="20" font-weight="bold" fill="{c['text']}">{_escape_xml(card['title'])}</text>
  <rect x="{x+20}" y="168" width="50" height="2" fill="{bar_color}" fill-opacity="0.6"/>
  <text x="{x+20}" y="200" font-family="{c['body_font']}" font-size="15" fill="{c['text']}">"""
        wrapped = []
        for line in card.get('lines', []): wrapped.extend(_wrap_text(line, 13))
        for j, line in enumerate(wrapped[:10]):
            cards_svg += f'\n    <tspan x="{x+20}" dy="{0 if j==0 else 24}">{line}</tspan>'
        cards_svg += "\n  </text>"
    top = f"""  <rect x="0" y="0" width="1280" height="70" fill="{c['header_bg']}" fill-opacity="0.95"/>
  <rect x="0" y="0" width="{c['accent_bar_w']}" height="70" fill="{c['accent']}"/>
  <text x="24" y="46" font-family="{c['title_font']}" font-size="26" font-weight="bold" fill="#FFFFFF">{title}</text>"""
    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {top}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


def _gov_four_card(title, icon, cards, c, page_num, total):
    cards_svg = ""
    for i, card in enumerate(cards[:4]):
        y = 100 + i * 140
        cards_svg += f"""
  <rect x="60" y="{y}" width="40" height="40" rx="4" fill="{c['primary']}"/>
  <text x="80" y="{y+28}" text-anchor="middle" font-family="{c['title_font']}" font-size="18" font-weight="bold" fill="#FFFFFF">{card.get('number', ['一','二','三','四'][i])}</text>
  <text x="115" y="{y+28}" font-family="{c['title_font']}" font-size="20" font-weight="bold" fill="{c['text']}">{_escape_xml(card['title'])}</text>
  <rect x="60" y="{y+48}" width="1160" height="80" rx="6" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="0.5"/>
  <text x="80" y="{y+75}" font-family="{c['body_font']}" font-size="15" fill="{c['text']}">"""
        wrapped = []
        for line in card.get('lines', []): wrapped.extend(_wrap_text(line, 42))
        for j, line in enumerate(wrapped[:2]):
            cards_svg += f'\n    <tspan x="80" dy="{0 if j==0 else 24}">{line}</tspan>'
        cards_svg += "\n  </text>"
    top = f"""  <rect x="0" y="0" width="1280" height="6" fill="{c['accent']}" fill-opacity="0.8"/>
  <rect x="0" y="6" width="1280" height="2" fill="{c['primary']}"/>
  <text x="60" y="50" font-family="{c['title_font']}" font-size="28" font-weight="bold" fill="{c['text']}">{title}</text>"""
    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {top}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


def _tech_four_card(title, icon, cards, c, page_num, total):
    card_w = 280; gap = 16; start_x = (1280 - 4 * card_w - 3 * gap) // 2
    colors = [c['primary'], c['accent'], c['accent2'], c['primary']]
    cards_svg = ""
    for i, card in enumerate(cards[:4]):
        x = start_x + i * (card_w + gap); color = colors[i % 4]
        cards_svg += f"""
  <rect x="{x}" y="110" width="{card_w}" height="530" rx="4" fill="{c['card_bg']}" stroke="{color}" stroke-width="1" stroke-opacity="0.3"/>
  <rect x="{x}" y="110" width="{card_w}" height="3" fill="{color}" fill-opacity="0.8"/>
  <text x="{x+12}" y="145" font-family="Consolas, monospace" font-size="13" fill="{color}" fill-opacity="0.5">[{card.get('number', ['A','B','C','D'][i])}]</text>
  <text x="{x+12}" y="175" font-family="{c['title_font']}" font-size="20" font-weight="bold" fill="{color}">{_escape_xml(card['title'])}</text>
  <text x="{x+12}" y="205" font-family="{c['body_font']}" font-size="14" fill="{c['text']}">"""
        wrapped = []
        for line in card.get('lines', []): wrapped.extend(_wrap_text(line, 14))
        for j, line in enumerate(wrapped[:10]):
            cards_svg += f'\n    <tspan x="{x+12}" dy="{0 if j==0 else 22}">{line}</tspan>'
        cards_svg += "\n  </text>"
    top = f"""  <rect x="0" y="0" width="1280" height="4" fill="{c['primary']}" fill-opacity="0.8"/>
  <rect x="0" y="6" width="1280" height="2" fill="{c['primary']}" fill-opacity="0.4"/>
  <text x="60" y="40" font-family="Consolas, monospace" font-size="14" fill="{c['primary']}" fill-opacity="0.5">&gt; {title}.exercises</text>
  <text x="60" y="75" font-family="Consolas, monospace" font-size="30" font-weight="bold" fill="{c['primary']}">{title}</text>
  <rect x="60" y="85" width="250" height="2" fill="{c['primary']}" fill-opacity="0.4"/>"""
    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {top}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


def _warm_four_card(title, icon, cards, c, page_num, total):
    card_w = 270; gap = 24; start_x = (1280 - 4 * card_w - 3 * gap) // 2
    colors = [c['primary'], c['accent'], c['accent2'], c['primary']]
    cards_svg = ""
    for i, card in enumerate(cards[:4]):
        x = start_x + i * (card_w + gap); color = colors[i % 4]
        cards_svg += f"""
  <rect x="{x}" y="120" width="{card_w}" height="510" rx="18" fill="{c['card_bg']}" stroke="{color}" stroke-width="1.5" stroke-opacity="0.25"/>
  <circle cx="{x + card_w//2}" cy="160" r="24" fill="{color}" fill-opacity="0.12"/>
  <text x="{x + card_w//2}" y="168" text-anchor="middle" font-family="{c['title_font']}" font-size="18" font-weight="bold" fill="{color}">{card.get('number', ['一','二','三','四'][i])}</text>
  <text x="{x + card_w//2}" y="210" text-anchor="middle" font-family="{c['title_font']}" font-size="20" font-weight="bold" fill="{c['text']}">{_escape_xml(card['title'])}</text>
  <rect x="{x + card_w//2 - 40}" y="224" width="80" height="2" rx="1" fill="{color}" fill-opacity="0.3"/>
  <text x="{x + 20}" y="260" font-family="{c['body_font']}" font-size="15" fill="{c['text']}">"""
        wrapped = []
        for line in card.get('lines', []): wrapped.extend(_wrap_text(line, 13))
        for j, line in enumerate(wrapped[:9]):
            cards_svg += f'\n    <tspan x="{x+20}" dy="{0 if j==0 else 24}">{line}</tspan>'
        cards_svg += "\n  </text>"
    top = f"""  <rect x="0" y="0" width="1280" height="3" fill="{c['primary']}" fill-opacity="0.5"/>
  <rect x="60" y="20" width="4" height="40" rx="2" fill="{c['accent']}"/>
  <text x="76" y="56" font-family="{c['title_font']}" font-size="32" font-weight="bold" fill="{c['text']}">{title}</text>
  <rect x="76" y="66" width="160" height="2" rx="1" fill="{c['primary']}" fill-opacity="0.2"/>"""
    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {top}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_grid_2x2_svg(title: str, icon: str, items: list,
                          theme: dict, page_num: int, total: int) -> str:
    """2x2 网格布局 — 按 bg_pattern + header_h 生成不同结构"""
    c = theme
    pattern = c.get("bg_pattern", "none")
    header_h = c.get("header_h", 56)

    if pattern == "code_matrix":
        return _tech_grid(title, icon, items, c, page_num, total)
    elif pattern == "stripe":
        return _gov_grid(title, icon, items, c, page_num, total)
    elif pattern in ("xuan_paper", "parchment", "bubble"):
        return _warm_grid(title, icon, items, c, page_num, total)
    elif header_h >= 60:
        return _academic_grid(title, icon, items, c, page_num, total)
    else:
        return _warm_grid(title, icon, items, c, page_num, total)


def _academic_grid(title, icon, items, c, page_num, total):
    positions = [(60, 110), (660, 110), (60, 400), (660, 400)]
    card_w, card_h = 560, 270
    colors_cycle = [c['primary'], c['accent'], c['primary'], c['accent']]
    cards_svg = ""
    for i, item in enumerate(items[:4]):
        x, y = positions[i]; color = colors_cycle[i]
        cards_svg += f"""
  <rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="12" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="1"/>
  <circle cx="{x+70}" cy="{y+60}" r="28" fill="{color}" fill-opacity="0.15"/>
  <text x="{x+70}" y="{y+70}" text-anchor="middle" font-family="{c['title_font']}" font-size="24" font-weight="bold" fill="{color}">{i+1}</text>
  <text x="{x+120}" y="{y+65}" font-family="{c['title_font']}" font-size="24" font-weight="bold" fill="{c['text']}">{_escape_xml(item['title'])}</text>
  <rect x="{x+40}" y="{y+90}" width="480" height="2" fill="{c['card_border']}" fill-opacity="0.5"/>
  <text x="{x+40}" y="{y+130}" font-family="{c['body_font']}" font-size="18" fill="{c['text']}">"""
        wrapped = []
        for line in item.get('lines', []): wrapped.extend(_wrap_text(line, 24))
        for j, line in enumerate(wrapped[:5]):
            cards_svg += f'\n    <tspan x="{x+40}" dy="{0 if j==0 else 28}">{line}</tspan>'
        cards_svg += "\n  </text>"
    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {_top_bar(c)}
  {_page_title_block(title, icon, c)}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


def _gov_grid(title, icon, items, c, page_num, total):
    positions = [(60, 90), (660, 90), (60, 400), (660, 400)]
    card_w, card_h = 560, 280
    cards_svg = ""
    for i, item in enumerate(items[:4]):
        x, y = positions[i]
        cards_svg += f"""
  <rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="6" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="0.5"/>
  <rect x="{x}" y="{y}" width="6" height="{card_h}" rx="3" fill="{c['primary']}"/>
  <text x="{x+24}" y="{y+35}" font-family="{c['title_font']}" font-size="22" font-weight="bold" fill="{c['text']}">{_escape_xml(item['title'])}</text>
  <rect x="{x+24}" y="{y+48}" width="80" height="2" fill="{c['accent']}"/>
  <text x="{x+24}" y="{y+80}" font-family="{c['body_font']}" font-size="16" fill="{c['text']}">"""
        wrapped = []
        for line in item.get('lines', []): wrapped.extend(_wrap_text(line, 24))
        for j, line in enumerate(wrapped[:5]):
            cards_svg += f'\n    <tspan x="{x+24}" dy="{0 if j==0 else 26}">{line}</tspan>'
        cards_svg += "\n  </text>"
    top = f"""  <rect x="0" y="0" width="1280" height="6" fill="{c['accent']}" fill-opacity="0.8"/>
  <rect x="0" y="6" width="1280" height="2" fill="{c['primary']}"/>
  <text x="60" y="50" font-family="{c['title_font']}" font-size="28" font-weight="bold" fill="{c['text']}">{title}</text>"""
    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {top}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


def _tech_grid(title, icon, items, c, page_num, total):
    positions = [(60, 100), (660, 100), (60, 400), (660, 400)]
    card_w, card_h = 560, 270
    colors = [c['primary'], c['accent'], c['accent2'], c['primary']]
    cards_svg = ""
    for i, item in enumerate(items[:4]):
        x, y = positions[i]; color = colors[i % 4]
        cards_svg += f"""
  <rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="4" fill="{c['card_bg']}" stroke="{color}" stroke-width="1" stroke-opacity="0.3"/>
  <rect x="{x}" y="{y}" width="{card_w}" height="3" fill="{color}" fill-opacity="0.7"/>
  <text x="{x+16}" y="{y+35}" font-family="Consolas, monospace" font-size="14" fill="{color}" fill-opacity="0.5">// {i+1}</text>
  <text x="{x+16}" y="{y+65}" font-family="{c['title_font']}" font-size="22" font-weight="bold" fill="{color}">{_escape_xml(item['title'])}</text>
  <text x="{x+16}" y="{y+95}" font-family="{c['body_font']}" font-size="15" fill="{c['text']}">"""
        wrapped = []
        for line in item.get('lines', []): wrapped.extend(_wrap_text(line, 24))
        for j, line in enumerate(wrapped[:5]):
            cards_svg += f'\n    <tspan x="{x+16}" dy="{0 if j==0 else 24}">{line}</tspan>'
        cards_svg += "\n  </text>"
    top = f"""  <rect x="0" y="0" width="1280" height="4" fill="{c['primary']}" fill-opacity="0.8"/>
  <rect x="0" y="6" width="1280" height="2" fill="{c['primary']}" fill-opacity="0.4"/>
  <text x="60" y="40" font-family="Consolas, monospace" font-size="14" fill="{c['primary']}" fill-opacity="0.5">&gt; {title}.analysis</text>
  <text x="60" y="75" font-family="Consolas, monospace" font-size="30" font-weight="bold" fill="{c['primary']}">{title}</text>
  <rect x="60" y="85" width="250" height="2" fill="{c['primary']}" fill-opacity="0.4"/>"""
    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {top}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


def _warm_grid(title, icon, items, c, page_num, total):
    positions = [(60, 110), (660, 110), (60, 400), (660, 400)]
    card_w, card_h = 560, 260
    colors = [c['primary'], c['accent'], c['accent2'], c['primary']]
    cards_svg = ""
    for i, item in enumerate(items[:4]):
        x, y = positions[i]; color = colors[i % 4]
        cards_svg += f"""
  <rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="20" fill="{c['card_bg']}" stroke="{color}" stroke-width="1.5" stroke-opacity="0.2"/>
  <circle cx="{x+50}" cy="{y+50}" r="22" fill="{color}" fill-opacity="0.12"/>
  <text x="{x+50}" y="{y+58}" text-anchor="middle" font-family="{c['title_font']}" font-size="18" font-weight="bold" fill="{color}">{i+1}</text>
  <text x="{x+90}" y="{y+58}" font-family="{c['title_font']}" font-size="22" font-weight="bold" fill="{c['text']}">{_escape_xml(item['title'])}</text>
  <rect x="{x+30}" y="{y+80}" width="500" height="2" rx="1" fill="{color}" fill-opacity="0.2"/>
  <text x="{x+30}" y="{y+110}" font-family="{c['body_font']}" font-size="16" fill="{c['text']}">"""
        wrapped = []
        for line in item.get('lines', []): wrapped.extend(_wrap_text(line, 24))
        for j, line in enumerate(wrapped[:4]):
            cards_svg += f'\n    <tspan x="{x+30}" dy="{0 if j==0 else 26}">{line}</tspan>'
        cards_svg += "\n  </text>"
    top = f"""  <rect x="0" y="0" width="1280" height="3" fill="{c['primary']}" fill-opacity="0.5"/>
  <rect x="60" y="20" width="4" height="40" rx="2" fill="{c['accent']}"/>
  <text x="76" y="56" font-family="{c['title_font']}" font-size="32" font-weight="bold" fill="{c['text']}">{title}</text>
  <rect x="76" y="66" width="160" height="2" rx="1" fill="{c['primary']}" fill-opacity="0.2"/>"""
    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {top}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


def _medical_grid(title, icon, items, c, page_num, total):
    positions = [(60, 110), (660, 110), (60, 400), (660, 400)]
    card_w, card_h = 560, 270
    bar_colors = [c['primary'], c['accent'], c['accent2'], c['primary']]
    cards_svg = ""
    for i, item in enumerate(items[:4]):
        x, y = positions[i]; bar_color = bar_colors[i % 4]
        cards_svg += f"""
  <rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="10" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="1"/>
  <rect x="{x}" y="{y}" width="5" height="{card_h}" rx="2" fill="{bar_color}"/>
  <text x="{x+24}" y="{y+35}" font-family="{c['title_font']}" font-size="22" font-weight="bold" fill="{c['text']}">{_escape_xml(item['title'])}</text>
  <rect x="{x+24}" y="{y+48}" width="60" height="2" fill="{bar_color}" fill-opacity="0.6"/>
  <text x="{x+24}" y="{y+80}" font-family="{c['body_font']}" font-size="16" fill="{c['text']}">"""
        wrapped = []
        for line in item.get('lines', []): wrapped.extend(_wrap_text(line, 24))
        for j, line in enumerate(wrapped[:5]):
            cards_svg += f'\n    <tspan x="{x+24}" dy="{0 if j==0 else 26}">{line}</tspan>'
        cards_svg += "\n  </text>"
    top = f"""  <rect x="0" y="0" width="1280" height="70" fill="{c['header_bg']}" fill-opacity="0.95"/>
  <rect x="0" y="0" width="{c['accent_bar_w']}" height="70" fill="{c['accent']}"/>
  <text x="24" y="46" font-family="{c['title_font']}" font-size="26" font-weight="bold" fill="#FFFFFF">{title}</text>"""
    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {top}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_split_svg(title: str, icon: str, left_content: dict,
                       right_cards: list, theme: dict, page_num: int, total: int) -> str:
    """左右分栏布局（30% / 70%）"""
    c = theme

    left_svg = f"""
  <rect x="60" y="110" width="380" height="540" rx="12" fill="{c['primary']}" fill-opacity="0.14" stroke="{c['primary']}" stroke-width="1" stroke-opacity="0.2"/>
  <circle cx="250" cy="250" r="60" fill="{c['primary']}" fill-opacity="0.1"/>
  <text x="250" y="260" text-anchor="middle" font-family="{c['title_font']}" font-size="40" fill="{c['primary']}" fill-opacity="0.25">{left_content.get('icon_text', '')}</text>
  <text x="250" y="360" text-anchor="middle" font-family="{c['title_font']}" font-size="28" font-weight="bold" fill="{c['text']}">{_escape_xml(left_content['name'])}</text>
  <text x="250" y="400" text-anchor="middle" font-family="{c['title_font']}" font-size="20" fill="{c['primary']}">{left_content.get('subtitle', '')}</text>
  <rect x="200" y="420" width="100" height="2" fill="{c['accent']}" fill-opacity="0.5"/>"""

    if left_content.get('desc'):
        left_svg += f"""
  <text x="250" y="460" text-anchor="middle" font-family="{c['body_font']}" font-size="16" fill="{c['text_secondary']}">
    <tspan x="250" dy="0">{left_content['desc']}</tspan>
  </text>"""

    right_svg = ""
    card_y = 110
    for card in right_cards[:3]:
        right_svg += f"""
  <rect x="480" y="{card_y}" width="740" height="160" rx="10" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="1"/>
  <text x="510" y="{card_y+35}" font-family="{c['title_font']}" font-size="22" font-weight="bold" fill="{c['text']}">{_escape_xml(card['title'])}</text>
  <text x="510" y="{card_y+70}" font-family="{c['body_font']}" font-size="18" fill="{c['text']}">"""
        wrapped_lines = []
        for line in card.get('lines', []):
            wrapped_lines.extend(_wrap_text(line, 35))
        for j, line in enumerate(wrapped_lines[:3]):
            if j == 0:
                right_svg += f'\n    <tspan x="510" dy="0">{line}</tspan>'
            else:
                right_svg += f'\n    <tspan x="510" dy="28">{line}</tspan>'
        right_svg += "\n  </text>"
        card_y += 180

    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {_top_bar(c)}
  {_page_title_block(title, icon, c)}
{left_svg}
{right_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_breathing_svg(title_lines: list, subtitle: str, points: list,
                           theme: dict, page_num: int, total: int,
                           quote: str = "") -> str:
    """留白呼吸页（主题思想、过渡页）"""
    c = theme

    points_svg = ""
    for i, point in enumerate(points):
        y = 300 + i * 60
        points_svg += f"""
  <text x="640" y="{y}" text-anchor="middle" font-family="{c['title_font']}" font-size="24" fill="{c['primary']}">{point}</text>"""

    quote_svg = ""
    if quote:
        quote_svg = f"""
  <rect x="440" y="560" width="400" height="2" fill="{c['accent']}" fill-opacity="0.4"/>
  <text x="640" y="610" text-anchor="middle" font-family="{c['title_font']}" font-size="20" fill="{c['text_secondary']}" font-style="italic">{quote}</text>"""

    title_text = title_lines[0] if title_lines else ""
    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {_top_bar(c)}

  <circle cx="640" cy="360" r="250" fill="{c['primary']}" fill-opacity="0.08"/>
  <circle cx="640" cy="360" r="180" fill="{c['accent']}" fill-opacity="0.08"/>

  <text x="640" y="240" text-anchor="middle" font-family="{c['title_font']}" font-size="44" font-weight="bold" fill="{c['text']}">{title_text}</text>
  <rect x="540" y="260" width="200" height="3" rx="1.5" fill="{c['primary']}"/>
{points_svg}
{quote_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_quote_svg(quote_lines: list, analysis_lines: list,
                       theme: dict, page_num: int, total: int) -> str:
    """引文页"""
    c = theme

    tf = c['title_font']
    bf = c['body_font']
    pf = c['primary']
    tc = c['text']

    quote_svg = ""
    for i, line in enumerate(quote_lines):
        y = 260 + i * 50
        quote_svg += f'\n  <text x="640" y="{y}" text-anchor="middle" font-family="{tf}" font-size="32" fill="{pf}" font-style="italic">{line}</text>'

    analysis_svg = ""
    for i, line in enumerate(analysis_lines):
        y = 430 + i * 36
        analysis_svg += f'\n  <text x="640" y="{y}" text-anchor="middle" font-family="{bf}" font-size="20" fill="{tc}">{line}</text>'

    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {_top_bar(c)}

  <circle cx="200" cy="200" r="120" fill="{c['primary']}" fill-opacity="0.10"/>
  <circle cx="1080" cy="520" r="100" fill="{c['accent']}" fill-opacity="0.10"/>
  <circle cx="640" cy="360" r="200" fill="{c['primary']}" fill-opacity="0.08"/>
{quote_svg}

  <rect x="520" y="340" width="240" height="3" rx="1.5" fill="{c['accent']}" fill-opacity="0.6"/>
{analysis_svg}
  {_svg_footer(page_num, total, c)}"""


def _get_ending_subtitle(subject: str, topic: str) -> str:
    """根据学科生成结束页副标题"""
    subject = subject or ""
    mapping = {
        "语文": "感受文学之美，品味语言之韵",
        "数学": "探索数学奥秘，培养逻辑思维",
        "英语": "Learning English, Exploring the World",
        "物理": "探索物理规律，理解自然世界",
        "化学": "探索物质变化，揭示化学奥秘",
        "生物": "探索生命奥秘，理解自然规律",
        "历史": "以史为鉴，面向未来",
        "地理": "认识世界，探索地球",
        "政治": "关注社会，塑造价值观",
        "音乐": "感受音乐之美，陶冶艺术情操",
        "美术": "发现美，创造美，感受艺术魅力",
        "体育": "强健体魄，全面发展",
        "科学": "探索科学奥秘，培养创新精神",
        "信息技术": "掌握数字技能，拥抱智能时代",
    }
    for kw, sub in mapping.items():
        if kw in subject:
            return sub
    return f"学习{topic}，探索知识世界"


def generate_ending_svg(theme: dict, page_num: int, total: int,
                        title: str = "谢谢观看",
                        subtitle: str = "", topic: str = "", subject: str = "") -> str:
    """结束页"""
    c = theme
    if not subtitle:
        subtitle = _get_ending_subtitle(subject, topic)
    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {_top_bar(c)}

  <circle cx="640" cy="340" r="280" fill="{c['primary']}" fill-opacity="0.08"/>
  <circle cx="640" cy="340" r="200" fill="{c['accent']}" fill-opacity="0.08"/>
  <circle cx="640" cy="340" r="120" fill="{c['primary']}" fill-opacity="0.02"/>

  <text x="640" y="300" text-anchor="middle" font-family="{c['title_font']}" font-size="56" font-weight="bold" fill="{c['text']}">{title}</text>
  <rect x="520" y="330" width="240" height="3" rx="1.5" fill="{c['primary']}"/>
  <text x="640" y="390" text-anchor="middle" font-family="{c['title_font']}" font-size="24" fill="{c['primary']}">{subtitle}</text>

  {_svg_footer(page_num, total, c)}"""


def generate_vocab_svg(title: str, vocab_items: list, theme: dict,
                       page_num: int, total: int) -> str:
    """字词卡片网格"""
    c = theme
    cols = 4
    card_w = 260
    card_h = 140
    gap = 20
    start_x = (1280 - cols * card_w - (cols - 1) * gap) // 2
    start_y = 120

    cards_svg = ""
    for i, item in enumerate(vocab_items[:12]):
        row = i // cols
        col = i % cols
        x = start_x + col * (card_w + gap)
        y = start_y + row * (card_h + gap)

        cards_svg += f"""
  <rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="10" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="1"/>
  <text x="{x + card_w//2}" y="{y+40}" text-anchor="middle" font-family="{c['body_font']}" font-size="14" fill="{c['primary']}">{item.get('pinyin', '')}</text>
  <text x="{x + card_w//2}" y="{y+80}" text-anchor="middle" font-family="{c['title_font']}" font-size="28" font-weight="bold" fill="{c['text']}">{item['word']}</text>
  <text x="{x + card_w//2}" y="{y+115}" text-anchor="middle" font-family="{c['body_font']}" font-size="14" fill="{c['text_secondary']}">{item.get('meaning', '')}</text>"""

    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  {_top_bar(c)}
  {_page_title_block(title, "book", c)}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


# ── 学科专属 SVG 布局生成器 ──

def generate_formula_step_svg(title: str, formula_data: dict,
                               theme: dict, page_num: int, total: int) -> str:
    """公式推导页（数学/物理）：左侧公式块 + 右侧步骤说明"""
    c = theme
    formula = _escape_xml(formula_data.get("formula", ""))
    steps = formula_data.get("steps", [])
    note = _escape_xml(formula_data.get("note", ""))

    formula_block = f"""
  <rect x="60" y="110" width="480" height="200" rx="12" fill="{c['primary']}" fill-opacity="0.14" stroke="{c['primary']}" stroke-width="1" stroke-opacity="0.15"/>
  <text x="300" y="200" text-anchor="middle" font-family="Consolas, 'Courier New', monospace" font-size="32" font-weight="bold" fill="{c['primary']}">{formula}</text>
  <rect x="60" y="330" width="480" height="2" fill="{c['accent']}" fill-opacity="0.3"/>"""
    if note:
        note_lines = _wrap_text(note, 22)
        for j, nl in enumerate(note_lines[:2]):
            formula_block += f"""
  <text x="300" y="{370 + j * 24}" text-anchor="middle" font-family="{c['body_font']}" font-size="16" fill="{c['text_secondary']}">{nl}</text>"""

    steps_svg = ""
    for i, step in enumerate(steps[:5]):
        y = 120 + i * 100
        steps_svg += f"""
  <rect x="570" y="{y}" width="40" height="40" rx="20" fill="{c['accent']}" fill-opacity="0.15"/>
  <text x="590" y="{y+26}" text-anchor="middle" font-family="{c['title_font']}" font-size="18" font-weight="bold" fill="{c['accent']}">{i+1}</text>"""
        wrapped = _wrap_text(step, 28)
        for j, line in enumerate(wrapped[:3]):
            steps_svg += f"""
  <text x="630" y="{y + 20 + j * 26}" font-family="{c['body_font']}" font-size="17" fill="{c['text']}">{line}</text>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "math")}
{formula_block}
{steps_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_graph_illustration_svg(title: str, graph_data: dict,
                                     theme: dict, page_num: int, total: int) -> str:
    """图解页（数学/物理）：坐标系/图形 + 要点说明"""
    c = theme
    points = graph_data.get("points", [])

    graph_svg = f"""
  <line x1="150" y1="550" x2="650" y2="550" stroke="{c['text_secondary']}" stroke-width="2"/>
  <line x1="150" y1="550" x2="150" y2="150" stroke="{c['text_secondary']}" stroke-width="2"/>
  <polygon points="650,550 640,545 640,555" fill="{c['text_secondary']}"/>
  <polygon points="150,150 145,160 155,160" fill="{c['text_secondary']}"/>
  <text x="660" y="555" font-family="{c['body_font']}" font-size="14" fill="{c['text_secondary']}">x</text>
  <text x="140" y="140" font-family="{c['body_font']}" font-size="14" fill="{c['text_secondary']}">y</text>"""

    points_svg = ""
    for i, point in enumerate(points[:5]):
        y = 150 + i * 80
        point_text = _escape_xml(point)
        points_svg += f"""
  <rect x="700" y="{y}" width="520" height="60" rx="8" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="0.5"/>
  <circle cx="730" cy="{y+30}" r="12" fill="{c['primary']}" fill-opacity="0.15"/>
  <text x="730" y="{y+35}" text-anchor="middle" font-family="{c['title_font']}" font-size="14" font-weight="bold" fill="{c['primary']}">{i+1}</text>
  <text x="755" y="{y+35}" font-family="{c['body_font']}" font-size="16" fill="{c['text']}">{point_text}</text>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "math")}
{graph_svg}
{points_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_poetry_vertical_svg(title: str, poetry_data: dict,
                                  theme: dict, page_num: int, total: int) -> str:
    """诗词赏析页（语文）：竖排版引文 + 右侧赏析"""
    c = theme
    lines = poetry_data.get("lines", [])
    analysis = poetry_data.get("analysis", [])
    author = _escape_xml(poetry_data.get("author", ""))

    poetry_svg = ""
    col_x = 900
    for col_i, line in enumerate(lines[:6]):
        x = col_x - col_i * 80
        chars = list(_escape_xml(line))
        for row_i, char in enumerate(chars[:12]):
            y = 160 + row_i * 42
            poetry_svg += f"""
  <text x="{x}" y="{y}" text-anchor="middle" font-family="KaiTi, SimSun, serif" font-size="28" fill="{c['primary']}">{char}</text>"""

    analysis_svg = ""
    for i, item in enumerate(analysis[:4]):
        y = 160 + i * 110
        item_text = _escape_xml(item)
        analysis_svg += f"""
  <rect x="60" y="{y}" width="480" height="90" rx="10" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="0.5"/>
  <text x="80" y="{y+30}" font-family="{c['body_font']}" font-size="16" fill="{c['text']}">{item_text}</text>"""

    if author:
        analysis_svg += f"""
  <text x="60" y="620" font-family="KaiTi, SimSun, serif" font-size="20" fill="{c['text_secondary']}">-- {author}</text>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "warm")}
{poetry_svg}
{analysis_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_timeline_svg(title: str, events: list,
                           theme: dict, page_num: int, total: int) -> str:
    """时间轴页（历史/地理）：横向时间线 + 事件卡片"""
    c = theme
    n = min(len(events), 5)
    if n == 0:
        n = 1

    line_y = 360
    line_svg = f"""
  <line x1="100" y1="{line_y}" x2="1180" y2="{line_y}" stroke="{c['primary']}" stroke-width="3" stroke-opacity="0.3"/>"""

    events_svg = ""
    step = 1080 // max(n, 1)
    for i, event in enumerate(events[:5]):
        x = 100 + i * step + step // 2
        year = _escape_xml(event.get("year", ""))
        desc = _escape_xml(event.get("desc", ""))
        color = [c['primary'], c['accent'], c.get('accent2', '#0066CC'), c['primary'], c['accent']][i % 5]

        events_svg += f"""
  <circle cx="{x}" cy="{line_y}" r="10" fill="{color}"/>
  <text x="{x}" y="{line_y - 20}" text-anchor="middle" font-family="{c['title_font']}" font-size="16" font-weight="bold" fill="{color}">{year}</text>"""

        card_y = line_y + 30 if i % 2 == 0 else line_y - 180
        events_svg += f"""
  <rect x="{x - 90}" y="{card_y}" width="180" height="130" rx="8" fill="{c['card_bg']}" stroke="{color}" stroke-width="1" stroke-opacity="0.3"/>
  <text x="{x}" y="{card_y + 30}" text-anchor="middle" font-family="{c['body_font']}" font-size="14" fill="{c['text']}">{desc}</text>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "government")}
{line_svg}
{events_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_comparison_table_svg(title: str, columns: list,
                                   theme: dict, page_num: int, total: int) -> str:
    """对比表格页（历史/地理）：双栏对比结构"""
    c = theme
    if len(columns) < 2:
        columns = columns + [{"title": "", "items": []}] * (2 - len(columns))

    col_w = 560
    col_svg = ""
    for ci, col in enumerate(columns[:2]):
        x = 60 + ci * (col_w + 60)
        col_title = _escape_xml(col.get("title", ""))
        items = col.get("items", [])
        color = [c['primary'], c['accent']][ci]

        col_svg += f"""
  <rect x="{x}" y="110" width="{col_w}" height="540" rx="10" fill="{c['card_bg']}" stroke="{color}" stroke-width="1.5" stroke-opacity="0.3"/>
  <rect x="{x}" y="110" width="{col_w}" height="50" rx="10" fill="{color}" fill-opacity="0.12"/>
  <text x="{x + col_w//2}" y="145" text-anchor="middle" font-family="{c['title_font']}" font-size="22" font-weight="bold" fill="{color}">{col_title}</text>"""

        for ri, item in enumerate(items[:6]):
            item_text = _escape_xml(item)
            item_y = 180 + ri * 75
            col_svg += f"""
  <rect x="{x + 20}" y="{item_y}" width="{col_w - 40}" height="55" rx="6" fill="{c['bg']}" stroke="{c['card_border']}" stroke-width="0.5"/>
  <text x="{x + 40}" y="{item_y + 32}" font-family="{c['body_font']}" font-size="16" fill="{c['text']}">{item_text}</text>"""

    col_svg += f"""
  <circle cx="640" cy="380" r="28" fill="{c['accent']}" fill-opacity="0.15"/>
  <text x="640" y="388" text-anchor="middle" font-family="{c['title_font']}" font-size="18" font-weight="bold" fill="{c['accent']}">VS</text>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "government")}
{col_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_experiment_flow_svg(title: str, steps: list,
                                  theme: dict, page_num: int, total: int) -> str:
    """实验流程页（生物/化学）：步骤箭头流程图"""
    c = theme
    n = min(len(steps), 5)
    if n == 0:
        n = 1

    step_w = 220
    gap = 20
    total_w = n * step_w + (n - 1) * gap
    start_x = (1280 - total_w) // 2

    flow_svg = ""
    for i, step in enumerate(steps[:5]):
        x = start_x + i * (step_w + gap)
        color = [c['primary'], c['accent'], c.get('accent2', '#00A86B'), c['primary'], c['accent']][i % 5]

        flow_svg += f"""
  <rect x="{x}" y="140" width="{step_w}" height="460" rx="12" fill="{c['card_bg']}" stroke="{color}" stroke-width="1.5"/>
  <circle cx="{x + step_w//2}" cy="200" r="22" fill="{color}" fill-opacity="0.15"/>
  <text x="{x + step_w//2}" y="208" text-anchor="middle" font-family="{c['title_font']}" font-size="20" font-weight="bold" fill="{color}">{i+1}</text>"""

        wrapped = _wrap_text(step, 10)
        for j, line in enumerate(wrapped[:6]):
            y = 260 + j * 30
            flow_svg += f"""
  <text x="{x + step_w//2}" y="{y}" text-anchor="middle" font-family="{c['body_font']}" font-size="15" fill="{c['text']}">{line}</text>"""

        if i < n - 1:
            arrow_x = x + step_w + 2
            flow_svg += f"""
  <line x1="{arrow_x}" y1="370" x2="{arrow_x + gap - 4}" y2="370" stroke="{c['text_secondary']}" stroke-width="2" stroke-opacity="0.4"/>
  <polygon points="{arrow_x + gap - 4},370 {arrow_x + gap - 12},365 {arrow_x + gap - 12},375" fill="{c['text_secondary']}" fill-opacity="0.4"/>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "medical")}
{flow_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_structure_diagram_svg(title: str, center_label: str, branches: list,
                                    theme: dict, page_num: int, total: int) -> str:
    """结构图页（生物/化学）：中心图 + 周围标注"""
    import math
    c = theme
    cx, cy = 640, 380

    diagram_svg = f"""
  <circle cx="{cx}" cy="{cy}" r="80" fill="{c['primary']}" fill-opacity="0.1" stroke="{c['primary']}" stroke-width="2"/>
  <text x="{cx}" y="{cy + 8}" text-anchor="middle" font-family="{c['title_font']}" font-size="22" font-weight="bold" fill="{c['primary']}">{_escape_xml(center_label)}</text>"""

    n = min(len(branches), 6)
    if n == 0:
        n = 1
    for i, branch in enumerate(branches[:6]):
        angle = (2 * math.pi * i / n) - math.pi / 2
        bx = cx + int(220 * math.cos(angle))
        by = cy + int(220 * math.sin(angle))
        label = _escape_xml(branch.get("label", ""))
        desc = _escape_xml(branch.get("desc", ""))
        color = [c['primary'], c['accent'], c.get('accent2', '#00A86B'), c['primary'], c['accent'], c.get('accent2', '#00A86B')][i % 6]

        diagram_svg += f"""
  <line x1="{cx}" y1="{cy}" x2="{bx}" y2="{by}" stroke="{color}" stroke-width="1.5" stroke-opacity="0.3"/>
  <circle cx="{bx}" cy="{by}" r="50" fill="{c['card_bg']}" stroke="{color}" stroke-width="1.5"/>
  <text x="{bx}" y="{by - 5}" text-anchor="middle" font-family="{c['title_font']}" font-size="14" font-weight="bold" fill="{color}">{label}</text>
  <text x="{bx}" y="{by + 15}" text-anchor="middle" font-family="{c['body_font']}" font-size="12" fill="{c['text_secondary']}">{desc}</text>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "medical")}
{diagram_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_code_block_svg(title: str, code_data: dict,
                             theme: dict, page_num: int, total: int) -> str:
    """代码块页（信息技术）：深色背景 + 语法高亮风格"""
    c = theme
    code_lines = code_data.get("code", [])
    language = _escape_xml(code_data.get("language", "python"))
    explanation = code_data.get("explanation", [])

    code_svg = f"""
  <rect x="60" y="110" width="700" height="520" rx="8" fill="#1E1E1E" stroke="{c['primary']}" stroke-width="1" stroke-opacity="0.2"/>
  <rect x="60" y="110" width="700" height="30" rx="8" fill="#2D2D2D"/>
  <circle cx="85" cy="125" r="5" fill="#FF5F56"/>
  <circle cx="105" cy="125" r="5" fill="#FFBD2E"/>
  <circle cx="125" cy="125" r="5" fill="#27C93F"/>
  <text x="140" y="130" font-family="Consolas, monospace" font-size="12" fill="#8B949E">{language}</text>"""

    for i, line in enumerate(code_lines[:14]):
        y = 165 + i * 32
        line_text = _escape_xml(line)
        if line_text.strip().startswith('#') or line_text.strip().startswith('//'):
            color = "#6A9955"
        elif line_text.strip().startswith('def ') or line_text.strip().startswith('function '):
            color = "#DCDCAA"
        else:
            color = "#D4D4D4"
        code_svg += f"""
  <text x="80" y="{y}" font-family="Consolas, monospace" font-size="14" fill="{color}">{line_text}</text>"""

    expl_svg = ""
    for i, item in enumerate(explanation[:4]):
        y = 130 + i * 120
        item_text = _escape_xml(item)
        expl_svg += f"""
  <rect x="800" y="{y}" width="420" height="100" rx="8" fill="{c['card_bg']}" stroke="{c['primary']}" stroke-width="1" stroke-opacity="0.15"/>
  <text x="820" y="{y + 35}" font-family="{c['body_font']}" font-size="15" fill="{c['text']}">{item_text}</text>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "tech")}
{code_svg}
{expl_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_terminal_output_svg(title: str, outputs: list,
                                  theme: dict, page_num: int, total: int) -> str:
    """终端输出页（信息技术）：模拟终端界面"""
    c = theme

    term_svg = f"""
  <rect x="60" y="100" width="1160" height="540" rx="10" fill="#0D1117" stroke="{c['primary']}" stroke-width="1" stroke-opacity="0.3"/>
  <rect x="60" y="100" width="1160" height="32" rx="10" fill="#161B22"/>
  <circle cx="85" cy="116" r="5" fill="#FF5F56"/>
  <circle cx="105" cy="116" r="5" fill="#FFBD2E"/>
  <circle cx="125" cy="116" r="5" fill="#27C93F"/>
  <text x="140" y="121" font-family="Consolas, monospace" font-size="12" fill="#8B949E">terminal</text>"""

    for i, output in enumerate(outputs[:14]):
        y = 160 + i * 34
        text = _escape_xml(output)
        if text.startswith('$') or text.startswith('>'):
            color = c['primary']
        else:
            color = "#C9D1D9"
        term_svg += f"""
  <text x="80" y="{y}" font-family="Consolas, monospace" font-size="14" fill="{color}">{text}</text>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "tech")}
{term_svg}
  {_svg_footer(page_num, total, c)}"""


# ── 新增专属布局 SVG 生成器 ──

def generate_text_analysis_svg(title: str, text_data: dict,
                                theme: dict, page_num: int, total: int) -> str:
    """文本分析页（语文）：左侧原文段落 + 右侧逐句赏析"""
    c = theme
    original_lines = text_data.get("original", [])
    analysis_items = text_data.get("analysis", [])

    # 左侧：原文段落（带引号装饰）
    left_svg = f"""
  <rect x="60" y="100" width="540" height="560" rx="12" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="1"/>
  <text x="80" y="140" font-family="{c['title_font']}" font-size="20" font-weight="bold" fill="{c['primary']}">原文</text>
  <rect x="80" y="155" width="40" height="2" fill="{c['accent']}" fill-opacity="0.5"/>"""

    for i, line in enumerate(original_lines[:6]):
        y = 190 + i * 70
        wrapped = _wrap_text(line, 18)
        for j, wl in enumerate(wrapped[:3]):
            left_svg += f"""
  <text x="90" y="{y + j * 26}" font-family="KaiTi, SimSun, serif" font-size="17" fill="{c['text']}">{wl}</text>"""

    # 右侧：赏析要点
    right_svg = ""
    for i, item in enumerate(analysis_items[:4]):
        y = 100 + i * 140
        label = _escape_xml(item.get("label", f"赏析{i+1}"))
        detail = _escape_xml(item.get("detail", ""))
        right_svg += f"""
  <rect x="620" y="{y}" width="600" height="125" rx="10" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="0.5"/>
  <rect x="620" y="{y}" width="4" height="125" rx="2" fill="{c['accent']}"/>
  <text x="640" y="{y + 30}" font-family="{c['title_font']}" font-size="18" font-weight="bold" fill="{c['primary']}">{label}</text>"""
        wrapped = _wrap_text(detail, 26)
        for j, wl in enumerate(wrapped[:3]):
            right_svg += f"""
  <text x="640" y="{y + 60 + j * 24}" font-family="{c['body_font']}" font-size="15" fill="{c['text']}">{wl}</text>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "warm")}
{left_svg}
{right_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_comparison_two_column_svg(title: str, columns: dict,
                                        theme: dict, page_num: int, total: int) -> str:
    """双栏对比页（语文/历史）：左右两栏对比分析"""
    c = theme
    left_col = columns.get("left", {})
    right_col = columns.get("right", {})

    def _render_column(col_data: dict, x: int, color: str) -> str:
        col_title = _escape_xml(col_data.get("title", ""))
        items = col_data.get("items", [])
        svg = f"""
  <rect x="{x}" y="100" width="560" height="560" rx="12" fill="{c['card_bg']}" stroke="{color}" stroke-width="1.5" stroke-opacity="0.3"/>
  <rect x="{x}" y="100" width="560" height="50" rx="12" fill="{color}" fill-opacity="0.1"/>
  <text x="{x + 280}" y="135" text-anchor="middle" font-family="{c['title_font']}" font-size="22" font-weight="bold" fill="{color}">{col_title}</text>"""
        for i, item in enumerate(items[:5]):
            y = 170 + i * 95
            svg += f"""
  <rect x="{x + 20}" y="{y}" width="520" height="80" rx="8" fill="{c['bg']}" stroke="{c['card_border']}" stroke-width="0.5"/>"""
            wrapped = _wrap_text(item, 24)
            for j, wl in enumerate(wrapped[:3]):
                svg += f"""
  <text x="{x + 40}" y="{y + 28 + j * 24}" font-family="{c['body_font']}" font-size="16" fill="{c['text']}">{_escape_xml(wl)}</text>"""
        return svg

    left_svg = _render_column(left_col, 60, c['primary'])
    right_svg = _render_column(right_col, 660, c['accent'])

    # VS 圆圈
    vs_svg = f"""
  <circle cx="640" cy="380" r="28" fill="{c['accent']}" fill-opacity="0.15"/>
  <text x="640" y="388" text-anchor="middle" font-family="{c['title_font']}" font-size="18" font-weight="bold" fill="{c['accent']}">VS</text>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "warm")}
{left_svg}
{right_svg}
{vs_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_proof_deduction_svg(title: str, proof_data: dict,
                                  theme: dict, page_num: int, total: int) -> str:
    """证明演绎页（数学）：左侧已知条件 + 右侧证明步骤（带编号和箭头）"""
    c = theme
    given = proof_data.get("given", [])
    steps = proof_data.get("steps", [])
    conclusion = _escape_xml(proof_data.get("conclusion", ""))

    # 已知条件
    given_svg = f"""
  <rect x="60" y="100" width="400" height="540" rx="12" fill="{c['card_bg']}" stroke="{c['primary']}" stroke-width="1" stroke-opacity="0.2"/>
  <text x="80" y="140" font-family="{c['title_font']}" font-size="20" font-weight="bold" fill="{c['primary']}">已知条件</text>
  <rect x="80" y="155" width="60" height="2" fill="{c['accent']}" fill-opacity="0.5"/>"""

    for i, g in enumerate(given[:5]):
        y = 190 + i * 80
        wrapped = _wrap_text(g, 18)
        for j, wl in enumerate(wrapped[:2]):
            given_svg += f"""
  <text x="80" y="{y + j * 26}" font-family="{c['body_font']}" font-size="17" fill="{c['text']}">• {wl}</text>"""

    # 证明步骤（带编号和箭头）
    steps_svg = ""
    for i, step in enumerate(steps[:5]):
        y = 100 + i * 100
        steps_svg += f"""
  <rect x="490" y="{y}" width="40" height="40" rx="20" fill="{c['primary']}" fill-opacity="0.15"/>
  <text x="510" y="{y + 26}" text-anchor="middle" font-family="{c['title_font']}" font-size="18" font-weight="bold" fill="{c['primary']}">{i+1}</text>"""
        wrapped = _wrap_text(step, 30)
        for j, wl in enumerate(wrapped[:3]):
            steps_svg += f"""
  <text x="550" y="{y + 20 + j * 26}" font-family="{c['body_font']}" font-size="16" fill="{c['text']}">{wl}</text>"""
        if i < len(steps[:5]) - 1:
            steps_svg += f"""
  <line x1="510" y1="{y + 42}" x2="510" y2="{y + 98}" stroke="{c['primary']}" stroke-width="1.5" stroke-opacity="0.3"/>
  <polygon points="510,{y + 98} 505,{y + 90} 515,{y + 90}" fill="{c['primary']}" fill-opacity="0.3"/>"""

    # 结论
    conclusion_svg = ""
    if conclusion:
        conclusion_svg += f"""
  <rect x="490" y="610" width="730" height="50" rx="10" fill="{c['primary']}" fill-opacity="0.08" stroke="{c['primary']}" stroke-width="1" stroke-opacity="0.2"/>
  <text x="510" y="642" font-family="{c['title_font']}" font-size="18" font-weight="bold" fill="{c['primary']}">∴ {conclusion}</text>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "math")}
{given_svg}
{steps_svg}
{conclusion_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_exercise_steps_svg(title: str, exercises: list,
                                 theme: dict, page_num: int, total: int) -> str:
    """解题步骤页（数学）：分步展示解题过程，带编号和格式化"""
    c = theme

    cards_svg = ""
    for i, ex in enumerate(exercises[:3]):
        x = 60 + i * 400
        question = _escape_xml(ex.get("question", ""))
        steps = ex.get("steps", [])
        answer = _escape_xml(ex.get("answer", ""))

        cards_svg += f"""
  <rect x="{x}" y="100" width="370" height="560" rx="12" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="1"/>
  <rect x="{x}" y="100" width="370" height="50" rx="12" fill="{c['primary']}" fill-opacity="0.1"/>
  <text x="{x + 185}" y="135" text-anchor="middle" font-family="{c['title_font']}" font-size="18" font-weight="bold" fill="{c['primary']}">例题 {i+1}</text>"""
        wrapped_q = _wrap_text(question, 16)
        for j, wl in enumerate(wrapped_q[:2]):
            cards_svg += f"""
  <text x="{x + 20}" y="{180 + j * 26}" font-family="{c['body_font']}" font-size="16" fill="{c['text']}">{wl}</text>"""

        for si, step in enumerate(steps[:6]):
            sy = 230 + si * 48
            wrapped_s = _wrap_text(step, 15)
            for j, wl in enumerate(wrapped_s[:2]):
                cards_svg += f"""
  <text x="{x + 20}" y="{sy + j * 22}" font-family="{c['body_font']}" font-size="14" fill="{c['text_secondary']}">{si+1}. {wl}</text>"""

        if answer:
            cards_svg += f"""
  <rect x="{x + 20}" y="520" width="330" height="40" rx="6" fill="{c['primary']}" fill-opacity="0.08"/>
  <text x="{x + 30}" y="546" font-family="{c['title_font']}" font-size="15" font-weight="bold" fill="{c['primary']}">答：{answer}</text>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "math")}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_vocab_cards_svg(title: str, vocab_items: list,
                              theme: dict, page_num: int, total: int) -> str:
    """词汇卡片页（英语）：卡片网格，每张卡片含单词、音标、释义、例句"""
    c = theme
    cols = 3
    card_w = 370
    card_h = 180
    gap = 20
    start_x = (1280 - cols * card_w - (cols - 1) * gap) // 2
    start_y = 110

    cards_svg = ""
    for i, item in enumerate(vocab_items[:9]):
        row = i // cols
        col = i % cols
        x = start_x + col * (card_w + gap)
        y = start_y + row * (card_h + gap)

        word = _escape_xml(item.get("word", ""))
        phonetic = _escape_xml(item.get("phonetic", ""))
        meaning = _escape_xml(item.get("meaning", ""))
        example = _escape_xml(item.get("example", ""))

        cards_svg += f"""
  <rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="12" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="1"/>
  <text x="{x + 20}" y="{y + 35}" font-family="{c['title_font']}" font-size="24" font-weight="bold" fill="{c['primary']}">{word}</text>
  <text x="{x + 20}" y="{y + 60}" font-family="{c['body_font']}" font-size="14" fill="{c['text_secondary']}">{phonetic}</text>
  <rect x="{x + 20}" y="{y + 70}" width="100" height="1" fill="{c['accent']}" fill-opacity="0.3"/>
  <text x="{x + 20}" y="{y + 95}" font-family="{c['body_font']}" font-size="15" fill="{c['text']}">{meaning}</text>"""
        if example:
            wrapped_ex = _wrap_text(example, 18)
            for j, wl in enumerate(wrapped_ex[:2]):
                cards_svg += f"""
  <text x="{x + 20}" y="{y + 125 + j * 22}" font-family="{c['body_font']}" font-size="13" fill="{c['text_secondary']}" font-style="italic">{wl}</text>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "warm")}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_role_dialogue_svg(title: str, dialogue_data: dict,
                                theme: dict, page_num: int, total: int) -> str:
    """角色对话页（英语）：模拟对话气泡"""
    c = theme
    dialogues = dialogue_data.get("dialogues", [])
    scene = _escape_xml(dialogue_data.get("scene", ""))

    # 场景描述
    scene_svg = ""
    if scene:
        scene_svg = f"""
  <rect x="60" y="100" width="1160" height="50" rx="10" fill="{c['primary']}" fill-opacity="0.14"/>
  <text x="640" y="132" text-anchor="middle" font-family="{c['body_font']}" font-size="16" fill="{c['text_secondary']}">Scene: {scene}</text>"""

    # 对话气泡
    dialogue_svg = ""
    for i, d in enumerate(dialogues[:8]):
        speaker = _escape_xml(d.get("speaker", ""))
        text = _escape_xml(d.get("text", ""))
        translation = _escape_xml(d.get("translation", ""))
        is_left = i % 2 == 0

        x = 100 if is_left else 680
        bg_color = c['primary'] if is_left else c['accent']
        y = 170 + i * 65

        dialogue_svg += f"""
  <rect x="{x}" y="{y}" width="500" height="55" rx="12" fill="{bg_color}" fill-opacity="0.08" stroke="{bg_color}" stroke-width="1" stroke-opacity="0.15"/>
  <text x="{x + 15}" y="{y + 22}" font-family="{c['title_font']}" font-size="14" font-weight="bold" fill="{bg_color}">{speaker}:</text>
  <text x="{x + 15}" y="{y + 42}" font-family="{c['body_font']}" font-size="15" fill="{c['text']}">{text}</text>"""
        if translation:
            dialogue_svg += f"""
  <text x="{x + 485}" y="{y + 42}" text-anchor="end" font-family="{c['body_font']}" font-size="12" fill="{c['text_light']}">{translation}</text>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "warm")}
{scene_svg}
{dialogue_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_sentence_pattern_svg(title: str, patterns: list,
                                   theme: dict, page_num: int, total: int) -> str:
    """句型练习页（英语）：句型结构 + 例句 + 替换练习"""
    c = theme

    cards_svg = ""
    for i, pat in enumerate(patterns[:4]):
        x = 60 if i % 2 == 0 else 660
        y = 110 + (i // 2) * 290

        pattern = _escape_xml(pat.get("pattern", ""))
        examples = pat.get("examples", [])
        practice = _escape_xml(pat.get("practice", ""))

        cards_svg += f"""
  <rect x="{x}" y="{y}" width="560" height="270" rx="12" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="1"/>
  <rect x="{x}" y="{y}" width="560" height="45" rx="12" fill="{c['primary']}" fill-opacity="0.1"/>
  <text x="{x + 280}" y="{y + 30}" text-anchor="middle" font-family="{c['title_font']}" font-size="18" font-weight="bold" fill="{c['primary']}">{pattern}</text>"""

        for j, ex in enumerate(examples[:3]):
            ey = y + 65 + j * 40
            cards_svg += f"""
  <text x="{x + 20}" y="{ey}" font-family="{c['body_font']}" font-size="15" fill="{c['text']}">• {_escape_xml(ex)}</text>"""

        if practice:
            cards_svg += f"""
  <rect x="{x + 20}" y="{y + 200}" width="520" height="50" rx="8" fill="{c['accent']}" fill-opacity="0.14"/>
  <text x="{x + 30}" y="{y + 228}" font-family="{c['body_font']}" font-size="14" fill="{c['accent']}">Practice: {practice}</text>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "warm")}
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_data_table_svg(title: str, table_data: dict,
                             theme: dict, page_num: int, total: int) -> str:
    """数据表格页（理科/历史）：结构化数据展示"""
    c = theme
    headers = table_data.get("headers", [])
    rows = table_data.get("rows", [])
    caption = _escape_xml(table_data.get("caption", ""))

    col_count = max(len(headers), 1)
    col_w = min(280, (1160) // col_count)
    start_x = (1280 - col_count * col_w) // 2
    row_h = 55

    # 表头
    table_svg = ""
    for i, h in enumerate(headers[:5]):
        x = start_x + i * col_w
        h_text = _escape_xml(h)
        table_svg += f"""
  <rect x="{x}" y="100" width="{col_w}" height="45" fill="{c['primary']}" fill-opacity="0.15"/>
  <text x="{x + col_w // 2}" y="130" text-anchor="middle" font-family="{c['title_font']}" font-size="15" font-weight="bold" fill="{c['primary']}">{h_text}</text>"""

    # 表格行（每行自动换行）
    max_rows = min(len(rows), 8)
    for ri in range(max_rows):
        row = rows[ri]
        y = 145 + ri * row_h
        # 计算这行需要的最大行数
        max_lines = 1
        for ci, cell in enumerate(row[:5]):
            wrapped = _wrap_text(str(cell), max(8, col_w // 14))
            max_lines = max(max_lines, len(wrapped))
        actual_h = max(row_h, 30 + max_lines * 22)

        for ci, cell in enumerate(row[:5]):
            x = start_x + ci * col_w
            bg = c['card_bg'] if ri % 2 == 0 else c['bg']
            table_svg += f"""
  <rect x="{x}" y="{y}" width="{col_w}" height="{actual_h}" fill="{bg}" stroke="{c['card_border']}" stroke-width="0.5"/>"""
            wrapped = _wrap_text(str(cell), max(8, col_w // 14))
            for j, line in enumerate(wrapped[:3]):
                table_svg += f"""
  <text x="{x + col_w // 2}" y="{y + 22 + j * 22}" text-anchor="middle" font-family="{c['body_font']}" font-size="13" fill="{c['text']}">{_escape_xml(line)}</text>"""

    # 表格说明
    if caption:
        table_svg += f"""
  <text x="640" y="{145 + max_rows * row_h + 25}" text-anchor="middle" font-family="{c['body_font']}" font-size="14" fill="{c['text_secondary']}">{caption}</text>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "government")}
{table_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_map_annotation_svg(title: str, map_data: dict,
                                 theme: dict, page_num: int, total: int) -> str:
    """地图标注页（历史/地理）：简化地图 + 标注点 + 说明"""
    c = theme
    locations = map_data.get("locations", [])
    description = _escape_xml(map_data.get("description", ""))

    # 简化地图背景（用圆形和线条模拟）
    map_svg = f"""
  <rect x="60" y="110" width="700" height="540" rx="12" fill="{c['card_bg']}" stroke="{c['card_border']}" stroke-width="1"/>
  <circle cx="400" cy="380" r="200" fill="none" stroke="{c['primary']}" stroke-width="1" stroke-opacity="0.15"/>
  <circle cx="400" cy="380" r="150" fill="none" stroke="{c['primary']}" stroke-width="0.5" stroke-opacity="0.1"/>
  <line x1="100" y1="380" x2="720" y2="380" stroke="{c['primary']}" stroke-width="0.5" stroke-opacity="0.1"/>
  <line x1="400" y1="140" x2="400" y2="620" stroke="{c['primary']}" stroke-width="0.5" stroke-opacity="0.1"/>"""

    # 标注点
    for i, loc in enumerate(locations[:6]):
        x = loc.get("x", 200 + i * 100)
        y = loc.get("y", 250 + (i % 3) * 80)
        label = _escape_xml(loc.get("label", ""))
        color = [c['primary'], c['accent'], c.get('accent2', '#0066CC')][i % 3]

        map_svg += f"""
  <circle cx="{x}" cy="{y}" r="8" fill="{color}" fill-opacity="0.6"/>
  <circle cx="{x}" cy="{y}" r="14" fill="none" stroke="{color}" stroke-width="1.5" stroke-opacity="0.4"/>
  <text x="{x}" y="{y - 20}" text-anchor="middle" font-family="{c['title_font']}" font-size="14" font-weight="bold" fill="{color}">{label}</text>"""

    # 右侧说明
    desc_svg = ""
    for i, loc in enumerate(locations[:6]):
        y = 110 + i * 85
        label = _escape_xml(loc.get("label", ""))
        detail = _escape_xml(loc.get("detail", ""))
        color = [c['primary'], c['accent'], c.get('accent2', '#0066CC')][i % 3]
        desc_svg += f"""
  <rect x="790" y="{y}" width="430" height="70" rx="8" fill="{c['card_bg']}" stroke="{color}" stroke-width="1" stroke-opacity="0.2"/>
  <circle cx="810" cy="{y + 35}" r="8" fill="{color}" fill-opacity="0.4"/>
  <text x="830" y="{y + 28}" font-family="{c['title_font']}" font-size="16" font-weight="bold" fill="{color}">{label}</text>
  <text x="830" y="{y + 50}" font-family="{c['body_font']}" font-size="13" fill="{c['text_secondary']}">{detail}</text>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "government")}
{map_svg}
{desc_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_flowchart_svg(title: str, flow_data: dict,
                            theme: dict, page_num: int, total: int) -> str:
    """流程图页（信息技术）：带箭头的流程图"""
    c = theme
    steps = flow_data.get("steps", [])
    n = min(len(steps), 5)
    if n == 0:
        n = 1

    # 垂直流程图
    step_h = 80
    gap = 25
    total_h = n * step_h + (n - 1) * gap
    start_y = max(100, (720 - total_h) // 2)

    flow_svg = ""
    for i, step in enumerate(steps[:5]):
        y = start_y + i * (step_h + gap)
        step_text = step.get("label", step if isinstance(step, str) else "")
        desc = step.get("desc", "") if isinstance(step, dict) else ""
        color = [c['primary'], c['accent'], c.get('accent2', '#00FF88')][i % 3]

        # 判断菱形（条件判断）还是矩形（步骤）
        if "判断" in step_text or "if" in step_text.lower() or "?" in step_text:
            cx, cy = 640, y + step_h // 2
            flow_svg += f"""
  <polygon points="{cx},{y} {cx + 100},{cy} {cx},{y + step_h} {cx - 100},{cy}"
           fill="{c['card_bg']}" stroke="{color}" stroke-width="2"/>
  <text x="{cx}" y="{cy + 6}" text-anchor="middle" font-family="{c['body_font']}" font-size="14" fill="{c['text']}">{_escape_xml(step_text)}</text>"""
        else:
            flow_svg += f"""
  <rect x="480" y="{y}" width="320" height="{step_h}" rx="10" fill="{c['card_bg']}" stroke="{color}" stroke-width="2"/>"""
            wrapped = _wrap_text(step_text, 16)
            for j, wl in enumerate(wrapped[:2]):
                flow_svg += f"""
  <text x="640" y="{y + 30 + j * 24}" text-anchor="middle" font-family="{c['title_font']}" font-size="15" font-weight="bold" fill="{color}">{_escape_xml(wl)}</text>"""
            if desc:
                desc_lines = _wrap_text(desc, 16)
                for j, dl in enumerate(desc_lines[:2]):
                    flow_svg += f"""
  <text x="640" y="{y + 50 + len(wrapped[:2]) * 10 + j * 20}" text-anchor="middle" font-family="{c['body_font']}" font-size="12" fill="{c['text_secondary']}">{_escape_xml(dl)}</text>"""

        # 箭头
        if i < n - 1:
            arrow_y = y + step_h + 3
            flow_svg += f"""
  <line x1="640" y1="{arrow_y}" x2="640" y2="{arrow_y + gap - 6}" stroke="{c['text_secondary']}" stroke-width="2" stroke-opacity="0.5"/>
  <polygon points="640,{arrow_y + gap - 6} 635,{arrow_y + gap - 14} 645,{arrow_y + gap - 14}" fill="{c['text_secondary']}" fill-opacity="0.5"/>"""

    return f"""{_svg_header()}
  {_render_background(c)}
  {_render_top_bar(c, title, "tech")}
{flow_svg}
  {_svg_footer(page_num, total, c)}"""


def generate_tech_dark_svg(title: str, content_data: dict,
                            theme: dict, page_num: int, total: int) -> str:
    """科技暗色页（信息技术）：深色背景 + 霓虹高亮 + 卡片"""
    c = theme
    items = content_data.get("items", [])

    cards_svg = ""
    colors = [c['primary'], c['accent'], c.get('accent2', '#FFD93D')]
    for i, item in enumerate(items[:4]):
        x = 60 if i % 2 == 0 else 660
        y = 110 + (i // 2) * 280
        color = colors[i % 3]
        label = _escape_xml(item.get("label", ""))
        detail = _escape_xml(item.get("detail", ""))

        cards_svg += f"""
  <rect x="{x}" y="{y}" width="560" height="260" rx="6" fill="{c['card_bg']}" stroke="{color}" stroke-width="1.5" stroke-opacity="0.3"/>
  <rect x="{x}" y="{y}" width="560" height="3" fill="{color}" fill-opacity="0.8"/>
  <text x="{x + 16}" y="{y + 30}" font-family="Consolas, monospace" font-size="13" fill="{color}" fill-opacity="0.6">// {i+1:02d}</text>
  <text x="{x + 16}" y="{y + 60}" font-family="{c['title_font']}" font-size="20" font-weight="bold" fill="{color}">{label}</text>
  <line x1="{x + 16}" y1="{y + 72}" x2="{x + 544}" y2="{y + 72}" stroke="{color}" stroke-opacity="0.2"/>"""
        wrapped = _wrap_text(detail, 24)
        for j, wl in enumerate(wrapped[:6]):
            cards_svg += f"""
  <text x="{x + 16}" y="{y + 100 + j * 24}" font-family="{c['body_font']}" font-size="15" fill="{c['text']}">{wl}</text>"""

    return f"""{_svg_header()}
  <rect width="1280" height="720" fill="{c['bg']}"/>
  <rect x="0" y="0" width="1280" height="4" fill="{c['primary']}" fill-opacity="0.8"/>
  <rect x="0" y="6" width="1280" height="2" fill="{c['primary']}" fill-opacity="0.4"/>
  <text x="60" y="40" font-family="Consolas, monospace" font-size="14" fill="{c['primary']}" fill-opacity="0.5">&gt; {title}.content</text>
  <text x="60" y="75" font-family="Consolas, monospace" font-size="30" font-weight="bold" fill="{c['primary']}">{title}</text>
  <rect x="60" y="85" width="300" height="2" fill="{c['primary']}" fill-opacity="0.4"/>
{cards_svg}
  {_svg_footer(page_num, total, c)}"""


# ─────────────────── AI 内容规划 ───────────────────

def _default_page_plan(topic: str, subject: str) -> list:
    """基于学科骨架生成默认页面规划，动态页数，全专属布局"""
    skeleton = get_skeleton(subject, topic)
    pages = skeleton["pages"]

    # 动态决定页数：取骨架的全部页面（去掉 optional 标记的页面如果内容量不够）
    # 但至少保留 min_pages - 2 个内容页（减去 cover 和 ending）
    content_pages = []
    for p in pages:
        page = {
            "title": p["title"],
            "rhythm": p["rhythm"],
            "layout": p["layout"],
            "content": p.get("desc", ""),
        }
        content_pages.append(page)

    # 组装完整页面：cover + 内容页 + ending
    result = [{"title": topic, "rhythm": "anchor", "layout": "cover", "content": "封面"}]

    # 页数 >= 8 时添加目录
    if len(content_pages) >= 6:
        result.append({"title": "目录", "rhythm": "anchor", "layout": "toc", "content": "目录"})

    result.extend(content_pages)
    result.append({"title": "谢谢观看", "rhythm": "anchor", "layout": "ending", "content": "结束"})

    return result


def _fix_titles(pages: list, skeleton: dict, topic: str) -> list:
    """修正 AI 输出的通用标题，强制使用学科骨架标题"""
    generic_titles = {
        "核心内容", "知识点", "重点讲解", "知识讲解", "内容分析",
        "课堂小结", "学习总结", "课后作业", "拓展阅读", "课堂练习",
        "复习巩固", "新课讲授", "导入新课", "教学过程", "课堂导入",
    }
    skeleton_pages = skeleton.get("pages", [])
    sk_idx = 0  # 骨架页面索引（跳过 cover/toc/ending）
    for page in pages:
        layout = page.get("layout", "")
        if layout in ("cover", "toc", "ending"):
            continue
        title = page.get("title", "")
        # 如果标题是通用标题或太短，用骨架标题替换
        if title in generic_titles or len(title) <= 2:
            if sk_idx < len(skeleton_pages):
                sk_title = skeleton_pages[sk_idx]["title"]
                # 尝试保留主题信息
                if topic and topic not in sk_title:
                    page["title"] = f"{sk_title}：{topic}"
                else:
                    page["title"] = sk_title
                logger.info(f"标题修正：「{title}」→「{page['title']}」")
        sk_idx += 1
    return pages


def plan_pages_with_ai(topic: str, subject: str, grade: str,
                       outline_markdown: str = "", search_context: str = "",
                       page_count_hint: int = None) -> list:
    """用 AI 规划每一页，根据内容自动决定页数，无硬性限制"""
    app_config = _config_module
    from openai import OpenAI

    client = OpenAI(api_key=app_config.OPENAI_API_KEY, base_url=app_config.OPENAI_BASE_URL)

    # 获取学科布局约束
    allowed_layouts = get_allowed_layouts(subject, topic)
    required_layouts = get_required_layouts(subject, topic)
    forbidden_layouts = get_forbidden_layouts(subject, topic)

    # 页数指导
    page_count_guide = ""
    if page_count_hint:
        page_count_guide = f"\n用户指定了页数：{page_count_hint}页，请尽量按照这个页数来规划。"
    else:
        page_count_guide = "\n根据内容自动决定页数，内容丰富就多页，内容精简就少页，不要人为限制。"

    system_prompt = f"""你是一个专业的教学课件内容规划师。

═══════════════════════════════════════════════════
【任务说明】
═══════════════════════════════════════════════════

根据主题和内容，规划PPT的每一页。页数由内容决定，不要人为限制。
内容丰富就多页，内容精简就少页。
{page_count_guide}

═══════════════════════════════════════════════════
【可用布局】
═══════════════════════════════════════════════════

通用布局：cover, toc, three_card, four_card, grid_2x2, split, quote, breathing, ending
学科专属布局：{', '.join(required_layouts) if required_layouts else '无'}

禁止使用的布局：{', '.join(forbidden_layouts) if forbidden_layouts else '无'}

═══════════════════════════════════════════════════
【规划规则】
═══════════════════════════════════════════════════

1. 第一页必须是 cover（封面）
2. 最后一页必须是 ending（结束）
3. 页数 >= 10 时添加 toc（目录）页
4. 根据内容选择合适的布局，不要全部使用相同的布局
5. 每页 content 字段包含 2-4 个具体要点
6. 标题要具体，不要使用"核心内容"、"知识点"等通用标题

═══════════════════════════════════════════════════
【输出格式】
═══════════════════════════════════════════════════

输出JSON数组，每个元素包含：
- title: 页面标题（具体、有意义）
- rhythm: "anchor" | "dense" | "breathing"
- layout: 布局类型
- content: 该页的核心内容（2-4个要点）

输出纯JSON，不要其他文字。"""

    user_msg = f"""主题：{topic}
学科：{subject}
年级：{grade}

{f'用户提供的大纲：\n{outline_markdown}' if outline_markdown else '请根据主题自行规划内容。'}

{f'教材参考内容（基于网络搜索）：\n{search_context}' if search_context else ''}

请规划PPT页面，输出JSON数组。"""

    response = client.chat.completions.create(
        model=app_config.OPENAI_MODEL,
        max_tokens=4096,
        temperature=0.7,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
    )

    content = response.choices[0].message.content

    # 解析 JSON
    try:
        json_str = _repair_json(content)
        pages = json.loads(json_str)
    except json.JSONDecodeError:
        pages = _default_page_plan(topic, subject)

    # ── 后处理：验证并修正布局和标题 ──
    logger.info(f"AI 返回 {len(pages)} 页: {[p.get('layout','?') for p in pages]}")
    pages = _validate_and_fix_layouts(pages, subject, topic, required_layouts, forbidden_layouts, allowed_layouts)
    logger.info(f"布局修正后 {len(pages)} 页: {[p.get('layout','?') for p in pages]}")

    # 确保第一页是 cover
    if pages and pages[0].get("layout") != "cover":
        pages.insert(0, {"title": topic, "rhythm": "anchor", "layout": "cover", "content": "封面"})

    # 确保最后一页是 ending
    if pages[-1].get("layout") != "ending":
        pages.append({"title": "谢谢观看", "rhythm": "anchor", "layout": "ending", "content": "结束"})

    # 页数 >= 8 时确保有目录（仅当还没有 toc 时）
    # content_page_count 只计内容页（排除 cover/toc/ending）
    structural_layouts = {"cover", "toc", "ending"}
    content_page_count = len([p for p in pages if p.get("layout") not in structural_layouts])
    has_toc = any(p.get("layout") == "toc" for p in pages)
    logger.info(f"目录判断：content_page_count={content_page_count}, has_toc={has_toc}")
    if content_page_count >= 8 and not has_toc:
        # 插入到 cover 之后
        insert_idx = 1 if pages[0].get("layout") == "cover" else 0
        pages.insert(insert_idx, {"title": "目录", "rhythm": "anchor", "layout": "toc", "content": "目录"})
        logger.info("后处理添加了目录页")

    # ── 最终去重：确保只有一个 toc 页 ──
    toc_indices = [i for i, p in enumerate(pages) if p.get("layout") == "toc"]
    logger.info(f"目录页检查：共 {len(toc_indices)} 个目录页，位置={toc_indices}")
    if len(toc_indices) > 1:
        # 保留第一个 toc，将后续 toc 转为 breathing 布局
        for idx in toc_indices[1:]:
            pages[idx]["layout"] = "breathing"
            pages[idx]["title"] = "章节过渡"
            logger.info(f"去重：移除多余的目录页（位置 {idx+1}）")

    # 打印最终页面规划
    for i, p in enumerate(pages):
        logger.info(f"  最终第{i+1}页: [{p['layout']}] {p['title']}")

    return pages


def _validate_and_fix_layouts(pages: list, subject: str, topic: str,
                                required_layouts: list, forbidden_layouts: list,
                                allowed_layouts: list) -> list:
    """验证并修正AI规划的布局"""
    fixed_pages = []
    required_used = set()
    last_layout = ""
    generic_layouts = {"three_card", "grid_2x2", "four_card", "split"}
    # 结构性页面和节奏页面允许使用通用布局
    exempt_layouts = {"cover", "toc", "ending", "breathing"}
    content_idx = 0  # 内容页计数（跳过 cover/toc/ending）

    # 通用标题集合（用于判断是否需要修正标题）
    generic_titles = {
        "核心内容", "知识点", "重点讲解", "知识讲解", "内容分析",
        "课堂小结", "学习总结", "课后作业", "拓展阅读", "课堂练习",
        "复习巩固", "新课讲授", "导入新课", "教学过程", "课堂导入",
    }

    # 布局→标题映射（用于布局替换时同步修正标题）
    layout_to_title = {
        "formula_step": "公式推导",
        "graph_illustration": "图解分析",
        "proof_deduction": "证明演绎",
        "exercise_steps": "例题解析",
        "data_table": "数据对比",
        "experiment_flow": "实验探究",
        "structure_diagram": "结构分析",
        "timeline": "时间线",
        "comparison_two_column": "对比分析",
        "text_analysis": "文本分析",
        "quote": "名句赏析",
        "poetry_vertical": "诗词品读",
        "vocab_cards": "词汇学习",
        "role_dialogue": "情景对话",
        "sentence_pattern": "句型练习",
        "code_block": "代码实现",
        "flowchart": "流程图",
        "terminal_output": "终端输出",
        "tech_dark": "技术探索",
        "map_annotation": "地图标注",
    }

    # 预检：是否已有 toc 页
    has_toc = any(p.get("layout") == "toc" for p in pages)

    for i, page in enumerate(pages):
        layout = page.get("layout", "")

        # 结构性页面保持不变
        if layout in ("cover", "ending"):
            fixed_pages.append(page)
            continue

        # toc 页保持不变（不强制第2页为 toc，由后处理统一管理）
        if layout == "toc":
            fixed_pages.append(page)
            continue

        old_layout = layout

        # 如果布局被禁止，替换
        if layout in forbidden_layouts:
            replacement = _find_replacement_layout(
                subject, topic, page.get("content", ""), required_layouts, required_used
            )
            page["layout"] = replacement
            layout = replacement
            logger.info(f"布局修正（禁止）：→ {replacement}")

        # 如果连续2次使用同一布局，换一个
        if layout == last_layout and layout not in exempt_layouts:
            replacement = _find_replacement_layout(
                subject, topic, page.get("content", ""), required_layouts, required_used
            )
            if replacement != layout:
                page["layout"] = replacement
                layout = replacement
                logger.info(f"布局修正（去重）：→ {replacement}")

        # 核心规则：内容页必须使用专属布局，不允许通用布局
        if layout in generic_layouts and layout not in exempt_layouts and required_layouts:
            unused_required = [r for r in required_layouts if r not in required_used]
            if unused_required:
                new_layout = unused_required[0]
                page["layout"] = new_layout
                layout = new_layout
                logger.info(f"布局强制替换：→ {new_layout}")

        # 布局被替换时，同步修正标题
        if layout != old_layout and layout in layout_to_title:
            title = page.get("title", "")
            if title in generic_titles or len(title) <= 2:
                sk_title = layout_to_title[layout]
                if topic and topic not in sk_title:
                    page["title"] = f"{sk_title}：{topic}"
                else:
                    page["title"] = sk_title
                logger.info(f"标题同步修正（布局替换）：→ {page['title']}")

        if layout in required_layouts:
            required_used.add(layout)

        last_layout = layout
        content_idx += 1
        fixed_pages.append(page)

    # 最终检查：确保所有必需布局至少使用一次
    if required_layouts:
        unused = [r for r in required_layouts if r not in required_used]
        for p in fixed_pages:
            if not unused:
                break
            if p.get("layout") in generic_layouts:
                new_layout = unused.pop(0)
                p["layout"] = new_layout
                logger.info(f"布局最终补充：→ {new_layout}")

    return fixed_pages


def _find_replacement_layout(subject: str, topic: str, content: str,
                              required_layouts: list, required_used: set) -> str:
    """为被禁止或重复的布局找到合适的替代"""
    # 优先使用未使用的必需布局
    unused = [r for r in required_layouts if r not in required_used]
    if unused:
        return unused[0]

    # 根据学科选择默认替代
    subject_group = get_subject_group(subject, topic)
    if subject_group == "math_physics":
        return "formula_step"
    elif subject_group in ("chinese_narrative", "chinese_other"):
        return "text_analysis"
    elif subject_group == "english":
        return "vocab_cards"
    elif subject_group == "history_geography":
        return "timeline"
    elif subject_group == "info_tech":
        return "flowchart"
    elif subject_group == "biology_chemistry":
        return "experiment_flow"
    return "three_card"


def _content_matches_layout(content: str, layout: str) -> str:
    """判断内容是否匹配某个布局类型"""
    content_lower = content.lower()
    matchers = {
        "formula_step": ["公式", "定理", "推导", "证明", "formula"],
        "graph_illustration": ["图形", "图像", "坐标", "函数", "图解"],
        "proof_deduction": ["证明", "推理", "已知", "求证"],
        "exercise_steps": ["例题", "解题", "计算", "练习"],
        "poetry_vertical": ["诗词", "古诗", "诗歌", "文言", "赏析"],
        "text_analysis": ["课文", "段落", "句子", "语句", "分析"],
        "comparison_two_column": ["对比", "比较", "异同", "区别"],
        "quote": ["名言", "格言", "引文", "引用"],
        "vocab_cards": ["单词", "词汇", "短语", "vocabulary"],
        "role_dialogue": ["对话", "情景", "dialogue"],
        "sentence_pattern": ["句型", "语法", "句式"],
        "timeline": ["时间", "历史", "事件", "朝代", "年代"],
        "map_annotation": ["地图", "地理", "位置", "区域"],
        "data_table": ["数据", "表格", "统计"],
        "experiment_flow": ["实验", "步骤", "操作", "流程"],
        "structure_diagram": ["结构", "体系", "组成"],
        "code_block": ["代码", "编程", "程序", "code"],
        "flowchart": ["流程", "算法", "判断", "循环"],
        "tech_dark": ["技术", "概念", "原理"],
        "terminal_output": ["命令", "终端", "shell"],
    }
    keywords = matchers.get(layout, [])
    for kw in keywords:
        if kw in content_lower:
            return True
    return False


def _repair_json(raw: str) -> str:
    """尝试修复 AI 返回的常见 JSON 格式问题"""
    s = raw.strip()
    # 去掉 markdown 代码块
    if "```json" in s:
        s = s.split("```json")[1].split("```")[0].strip()
    elif "```" in s:
        s = s.split("```")[1].split("```")[0].strip()
    # 去掉开头非 { [ 的字符
    for i, ch in enumerate(s):
        if ch in '{[':
            s = s[i:]
            break
    # 截断到最后一个 ] 或 }
    for i in range(len(s) - 1, -1, -1):
        if s[i] in '}]':
            s = s[:i + 1]
            break
    # 修复未转义的换行符在字符串中
    s = s.replace('\n', '\\n')
    # 修复尾部逗号
    s = re.sub(r',\s*([}\]])', r'\1', s)
    return s


def _parse_text_content(raw: str, layout: str) -> dict:
    """解析 AI 返回的纯文本格式内容"""
    lines = [l.strip() for l in raw.strip().split('\n') if l.strip()]

    if layout in ("three_card", "four_card"):
        cards = []
        current_card = None
        for line in lines:
            # 匹配 【一】标题 或 一、标题 或 1. 标题
            m = re.match(r'[【\[]?([一二三四五六七八九十\d])[】\].、]\s*(.*)', line)
            if m:
                if current_card:
                    cards.append(current_card)
                num_map = {"一": "一", "二": "二", "三": "三", "四": "四",
                           "1": "一", "2": "二", "3": "三", "4": "四"}
                current_card = {
                    "number": num_map.get(m.group(1), m.group(1)),
                    "title": m.group(2).strip(),
                    "lines": []
                }
            elif current_card and line.startswith(('-', '·', '•', '*')):
                current_card["lines"].append(line.lstrip('-·•* '))
            elif current_card and not line.startswith('#') and len(line) > 2:
                current_card["lines"].append(line)
        if current_card:
            cards.append(current_card)
        return {"cards": cards}

    if layout == "grid_2x2":
        items = []
        current_item = None
        for line in lines:
            m = re.match(r'[【\[]?([一二三四\d])[】\].、]\s*(.*)', line)
            if m:
                if current_item:
                    items.append(current_item)
                current_item = {"title": m.group(2).strip(), "lines": []}
            elif current_item and line.startswith(('-', '·', '•', '*')):
                current_item["lines"].append(line.lstrip('-·•* '))
            elif current_item and len(line) > 2:
                current_item["lines"].append(line)
        if current_item:
            items.append(current_item)
        return {"items": items}

    if layout == "split":
        left = {"name": "", "subtitle": "", "icon_text": "", "desc": ""}
        right = []
        current_section = None
        for line in lines:
            if re.match(r'[【\[]人物[】\]]', line) or re.match(r'[【\[]作者[】\]]', line):
                current_section = "left"
                continue
            m = re.match(r'[【\[](\d+|要点\d|一|二|三)[】\]]\s*(.*)', line)
            if m:
                current_section = "right"
                right.append({"title": m.group(2).strip(), "lines": []})
                continue
            if current_section == "left":
                parts = re.split(r'[|｜]', line)
                if len(parts) >= 1 and not left["name"]:
                    left["name"] = parts[0].strip()
                if len(parts) >= 2 and not left["subtitle"]:
                    left["subtitle"] = parts[1].strip()
                if len(parts) >= 3 and not left["desc"]:
                    left["desc"] = parts[2].strip()
                if not parts and len(line) > 2:
                    left["desc"] = line
            elif current_section == "right" and right:
                if line.startswith(('-', '·', '•', '*')):
                    right[-1]["lines"].append(line.lstrip('-·•* '))
                elif len(line) > 2:
                    right[-1]["lines"].append(line)
        if not left["name"]:
            left["name"] = "鲁迅"
        if not left["icon_text"]:
            left["icon_text"] = left["name"][0] if left["name"] else "文"
        return {"left": left, "right": right}

    if layout == "breathing":
        points = []
        quote = ""
        for line in lines:
            if line.startswith(('-', '·', '•', '*')):
                points.append(line.lstrip('-·•* '))
            elif 'quote' in line.lower() or '引用' in line:
                quote = line.split(':', 1)[-1].strip().strip('"')
            elif len(line) > 4 and not line.startswith('#'):
                points.append(line)
        return {"points": points[:4], "quote": quote}

    if layout == "quote":
        quote_lines = []
        analysis_lines = []
        section = "quote"
        for line in lines:
            if '分析' in line or '赏析' in line:
                section = "analysis"
                continue
            if section == "quote" and len(line) > 2:
                quote_lines.append(line)
            elif section == "analysis" and len(line) > 2:
                analysis_lines.append(line)
        return {"quote_lines": quote_lines[:3], "analysis_lines": analysis_lines[:4]}

    if layout == "vocab":
        items = []
        for line in lines:
            # 匹配: 字词 (拼音) 释义  或  字词 - 拼音 - 释义
            m = re.match(r'(\S+)\s*[（(](\S+)[）)]\s*(.*)', line)
            if m:
                items.append({"word": m.group(1), "pinyin": m.group(2), "meaning": m.group(3).strip()})
                continue
            parts = re.split(r'[-|｜]', line)
            if len(parts) >= 3:
                items.append({"word": parts[0].strip(), "pinyin": parts[1].strip(), "meaning": parts[2].strip()})
        return {"items": items}

    if layout == "formula_step":
        formula = ""
        steps = []
        note = ""
        for line in lines:
            if line.startswith("公式") or line.startswith("Formula"):
                formula = line.split(":", 1)[-1].strip() if ":" in line else line
            elif line.startswith("步骤") or line.startswith("Step"):
                steps.append(line.split(":", 1)[-1].strip() if ":" in line else line)
            elif line.startswith("注意") or line.startswith("说明"):
                note = line.split(":", 1)[-1].strip() if ":" in line else line
            elif not formula and len(line) > 2:
                formula = line
        return {"formula": formula, "steps": steps, "note": note}

    if layout == "graph_illustration":
        points = []
        for line in lines:
            if line.startswith(('-', '·', '•', '*')):
                points.append(line.lstrip('-·•* '))
            elif line.startswith("要点") or line.startswith("Point"):
                points.append(line.split(":", 1)[-1].strip() if ":" in line else line)
            elif len(line) > 4:
                points.append(line)
        return {"points": points[:5]}

    if layout == "poetry_vertical":
        poetry_lines = []
        analysis = []
        author = ""
        section = "poem"
        for line in lines:
            if "赏析" in line or "分析" in line:
                section = "analysis"
                continue
            if "作者" in line:
                author = line.split(":", 1)[-1].strip() if ":" in line else line.replace("作者：", "").replace("作者:", "").strip()
                continue
            if section == "poem" and len(line) > 1:
                poetry_lines.append(line)
            elif section == "analysis" and len(line) > 2:
                analysis.append(line.lstrip('-·•* '))
        return {"lines": poetry_lines[:6], "analysis": analysis[:4], "author": author}

    if layout == "timeline":
        events = []
        for line in lines:
            parts = re.split(r'[|｜]', line)
            if len(parts) >= 2:
                events.append({"year": parts[0].strip(), "desc": parts[1].strip()})
            elif len(line) > 4:
                events.append({"year": "", "desc": line})
        return {"events": events[:5]}

    if layout == "comparison_table":
        columns = []
        current_col = None
        for line in lines:
            m = re.match(r'[【\[](.*?)[】\]]', line)
            if m:
                if current_col:
                    columns.append(current_col)
                current_col = {"title": m.group(1), "items": []}
            elif current_col and line.startswith(('-', '·', '•', '*')):
                current_col["items"].append(line.lstrip('-·•* '))
            elif current_col and len(line) > 2:
                current_col["items"].append(line)
        if current_col:
            columns.append(current_col)
        return {"columns": columns[:2]}

    if layout == "experiment_flow":
        steps = []
        for line in lines:
            if line.startswith(('-', '·', '•', '*')):
                steps.append(line.lstrip('-·•* '))
            elif line.startswith("步骤") or line.startswith("Step"):
                steps.append(line.split(":", 1)[-1].strip() if ":" in line else line)
            elif len(line) > 2:
                steps.append(line)
        return {"steps": steps[:5]}

    if layout == "structure_diagram":
        center = ""
        branches = []
        for line in lines:
            if line.startswith("中心"):
                center = line.split(":", 1)[-1].strip() if ":" in line else line
            elif line.startswith("分支") or line.startswith("Branch"):
                parts = line.split(":", 1)[-1].strip() if ":" in line else line
                sub_parts = re.split(r'[|｜]', parts)
                if len(sub_parts) >= 2:
                    branches.append({"label": sub_parts[0].strip(), "desc": sub_parts[1].strip()})
                else:
                    branches.append({"label": parts, "desc": ""})
            elif len(line) > 2 and not center:
                center = line
        return {"center": center, "branches": branches[:6]}

    if layout == "code_block":
        code = []
        language = "python"
        explanation = []
        section = "code"
        for line in lines:
            if line.startswith("语言"):
                language = line.split(":", 1)[-1].strip() if ":" in line else line
                continue
            if "说明" in line or "解释" in line:
                section = "explain"
                explanation.append(line.split(":", 1)[-1].strip() if ":" in line else line)
                continue
            if section == "code":
                code.append(line)
            elif section == "explain":
                explanation.append(line.lstrip('-·•* '))
        return {"code": code[:14], "language": language, "explanation": explanation[:4]}

    if layout == "terminal_output":
        outputs = []
        for line in lines:
            outputs.append(line)
        return {"outputs": outputs[:14]}

    # ── 新增专属布局解析 ──

    if layout == "text_analysis":
        original = []
        analysis = []
        section = "original"
        for line in lines:
            if "赏析" in line or "分析" in line:
                section = "analysis"
                continue
            if section == "original" and len(line) > 2:
                original.append(line)
            elif section == "analysis" and len(line) > 2:
                parts = re.split(r'[|｜]', line, maxsplit=1)
                if len(parts) >= 2:
                    analysis.append({"label": parts[0].lstrip('-·•* 0123456789：:'), "detail": parts[1].strip()})
                else:
                    analysis.append({"label": f"赏析{len(analysis)+1}", "detail": line.lstrip('-·•* ')})
        return {"original": original[:8], "analysis": analysis[:4]}

    if layout == "comparison_two_column":
        left = {"title": "", "items": []}
        right = {"title": "", "items": []}
        current_col = None
        for line in lines:
            # 匹配左栏/右栏标题
            if re.match(r'左栏|左列|【左】', line):
                current_col = "left"
                left["title"] = re.sub(r'左栏|左列|【左】[:：]?\s*', '', line).strip()
                continue
            if re.match(r'右栏|右列|【右】', line):
                current_col = "right"
                right["title"] = re.sub(r'右栏|右列|【右】[:：]?\s*', '', line).strip()
                continue
            # 匹配标题行（没有前缀的第一行非列表项）
            if not left["title"] and not current_col and len(line) > 2 and not line.startswith(('-', '·', '•')):
                left["title"] = line.strip()
                current_col = "left"
                continue
            # 列表项
            if line.startswith(('-', '·', '•', '*')):
                item = line.lstrip('-·•* ')
                if current_col == "left":
                    left["items"].append(item)
                elif current_col == "right":
                    right["items"].append(item)
            elif len(line) > 2:
                if current_col == "left":
                    left["items"].append(line)
                elif current_col == "right":
                    right["items"].append(line)
        return {"left": left, "right": right}

    if layout == "proof_deduction":
        given = []
        steps = []
        conclusion = ""
        section = "given"
        for line in lines:
            if "结论" in line or "求证" in line or "∴" in line:
                section = "conclusion"
                conclusion = line.split(":", 1)[-1].strip() if ":" in line else line.replace("结论：", "").replace("∴", "").strip()
                continue
            if line.startswith("步骤") or re.match(r'Step\s*\d', line):
                section = "steps"
                steps.append(line.split(":", 1)[-1].strip() if ":" in line else line)
                continue
            if section == "given" and len(line) > 2:
                given.append(line.lstrip('-·•* '))
            elif section == "steps" and len(line) > 2:
                steps.append(line.lstrip('-·•* 0123456789'))
        return {"given": given[:4], "steps": steps[:6], "conclusion": conclusion}

    if layout == "exercise_steps":
        exercises = []
        current_ex = None
        for line in lines:
            if re.match(r'例题\s*\d|题目\s*\d|Exercise\s*\d', line):
                if current_ex:
                    exercises.append(current_ex)
                question = line.split(":", 1)[-1].strip() if ":" in line else line
                current_ex = {"question": question, "steps": [], "answer": ""}
                continue
            if current_ex and (line.startswith("答案") or line.startswith("Answer")):
                current_ex["answer"] = line.split(":", 1)[-1].strip() if ":" in line else line
                continue
            if current_ex and (line.startswith("步骤") or re.match(r'Step', line)):
                current_ex["steps"].append(line.split(":", 1)[-1].strip() if ":" in line else line)
                continue
            if current_ex and line.startswith(('-', '·', '•', '*')):
                current_ex["steps"].append(line.lstrip('-·•* '))
            elif current_ex and len(line) > 2:
                current_ex["steps"].append(line)
        if current_ex:
            exercises.append(current_ex)
        return {"exercises": exercises[:3]}

    if layout == "vocab_cards":
        items = []
        for line in lines:
            # 匹配: word (phonetic) meaning | example
            m = re.match(r'(\S+)\s*[（(]([^)）]+)[）)]\s*(.+?)(?:\s*[|｜]\s*(.+))?$', line)
            if m:
                items.append({
                    "word": m.group(1), "phonetic": m.group(2),
                    "meaning": m.group(3).strip(), "example": (m.group(4) or "").strip()
                })
                continue
            # 匹配: word - phonetic - meaning
            parts = re.split(r'\s*[-|｜]\s*', line)
            if len(parts) >= 3:
                items.append({
                    "word": parts[0].strip(), "phonetic": parts[1].strip(),
                    "meaning": parts[2].strip(), "example": parts[3].strip() if len(parts) > 3 else ""
                })
        return {"items": items[:9]}

    if layout == "role_dialogue":
        dialogues = []
        scene = ""
        for line in lines:
            if line.startswith("场景") or line.startswith("Scene"):
                scene = line.split(":", 1)[-1].strip() if ":" in line else line
                continue
            # 匹配: 角色A：英文 | 中文翻译
            m = re.match(r'([^：:]+)[：:]\s*(.+?)(?:\s*[|｜]\s*(.+))?$', line)
            if m:
                dialogues.append({
                    "speaker": m.group(1).strip(),
                    "text": m.group(2).strip(),
                    "translation": (m.group(3) or "").strip()
                })
        return {"scene": scene, "dialogues": dialogues[:8]}

    if layout == "sentence_pattern":
        patterns = []
        current_pat = None
        for line in lines:
            if line.startswith("句型") or line.startswith("Pattern"):
                if current_pat:
                    patterns.append(current_pat)
                pattern_text = line.split(":", 1)[-1].strip() if ":" in line else line
                current_pat = {"pattern": pattern_text, "examples": [], "practice": ""}
                continue
            if current_pat and (line.startswith("练习") or line.startswith("Practice")):
                current_pat["practice"] = line.split(":", 1)[-1].strip() if ":" in line else line
                continue
            if current_pat and (line.startswith("例句") or line.startswith("Example")):
                current_pat["examples"].append(line.split(":", 1)[-1].strip() if ":" in line else line)
                continue
            if current_pat and line.startswith(('-', '·', '•', '*')):
                current_pat["examples"].append(line.lstrip('-·•* '))
            elif current_pat and len(line) > 2 and not current_pat["examples"]:
                current_pat["examples"].append(line)
        if current_pat:
            patterns.append(current_pat)
        return {"patterns": patterns[:4]}

    if layout == "data_table":
        headers = []
        rows = []
        caption = ""
        for line in lines:
            if line.startswith("说明") or line.startswith("Caption"):
                caption = line.split(":", 1)[-1].strip() if ":" in line else line
                continue
            parts = re.split(r'\s*[|｜]\s*', line)
            if len(parts) >= 2:
                if not headers:
                    headers = [p.strip() for p in parts]
                else:
                    rows.append([p.strip() for p in parts])
        return {"headers": headers[:6], "rows": rows[:8], "caption": caption}

    if layout == "map_annotation":
        locations = []
        description = ""
        for line in lines:
            if line.startswith("描述") or line.startswith("Description"):
                description = line.split(":", 1)[-1].strip() if ":" in line else line
                continue
            m = re.match(r'标注\s*\d[：:]\s*(.+?)[|｜]\s*(.+)', line)
            if m:
                locations.append({
                    "label": m.group(1).strip(), "detail": m.group(2).strip(),
                    "x": 200 + len(locations) * 120, "y": 250 + (len(locations) % 3) * 80
                })
            elif "|" in line or "｜" in line:
                parts = re.split(r'[|｜]', line)
                if len(parts) >= 2:
                    locations.append({
                        "label": parts[0].strip(), "detail": parts[1].strip(),
                        "x": 200 + len(locations) * 120, "y": 250 + (len(locations) % 3) * 80
                    })
        return {"locations": locations[:6], "description": description}

    if layout == "flowchart":
        steps = []
        for line in lines:
            m = re.match(r'(?:步骤|Step)\s*\d[：:]\s*(.+?)(?:[|｜]\s*(.+))?$', line)
            if m:
                steps.append({"label": m.group(1).strip(), "desc": (m.group(2) or "").strip()})
            elif line.startswith("判断") or "?" in line:
                steps.append({"label": line.strip(), "desc": ""})
            elif line.startswith(('-', '·', '•', '*')):
                steps.append({"label": line.lstrip('-·•* '), "desc": ""})
            elif len(line) > 2:
                steps.append({"label": line.strip(), "desc": ""})
        return {"steps": steps[:6]}

    if layout == "tech_dark":
        items = []
        for line in lines:
            m = re.match(r'要点\s*\d[：:]\s*(.+?)[|｜]\s*(.+)', line)
            if m:
                items.append({"label": m.group(1).strip(), "detail": m.group(2).strip()})
            elif "|" in line or "｜" in line:
                parts = re.split(r'[|｜]', line)
                if len(parts) >= 2:
                    items.append({"label": parts[0].strip(), "detail": parts[1].strip()})
            elif len(line) > 4:
                items.append({"label": line.strip(), "detail": ""})
        return {"items": items[:6]}

    return {}


def generate_page_content_with_ai(page_spec: dict, topic: str, subject: str,
                                  theme: dict, page_num: int, total: int,
                                  search_context: str = "") -> str:
    """用 AI 为单页生成内容（纯文本格式，不依赖 JSON）"""
    app_config = _config_module
    from openai import OpenAI

    layout = page_spec["layout"]

    # ── 封面、结束页直接生成 ──
    if layout == "cover":
        subtitle = f"{subject} · 教学课件" if subject else "教学课件"
        info = f"{datetime.now().strftime('%Y年%m月%d日')}"
        return generate_cover_svg(topic, subtitle, info, theme, total)

    if layout == "ending":
        return generate_ending_svg(theme, page_num, total, topic=topic, subject=subject)

    # ── 目录页用 AI 生成目录项 ──
    if layout == "toc":
        toc_items = _generate_toc_items(topic, subject, page_spec)
        return generate_toc_svg(toc_items, theme, total)

    # ── 内容页：AI 生成纯文本内容 ──
    client = OpenAI(api_key=app_config.OPENAI_API_KEY, base_url=app_config.OPENAI_BASE_URL)

    layout_instructions = {
        "three_card": """输出3个卡片，每卡5-8行。格式：
【一】卡片标题
- 具体知识点1
- 具体知识点2
- 具体知识点3
- 具体知识点4
- 具体知识点5

【二】卡片标题
- 具体知识点1
- 具体知识点2
- 具体知识点3
- 具体知识点4

【三】卡片标题
- 具体知识点1
- 具体知识点2
- 具体知识点3
- 具体知识点4
- 具体知识点5""",

        "four_card": """输出4个卡片，每卡4-6行。格式：
【一】标题
- 内容要点1
- 内容要点2
- 内容要点3
- 内容要点4

【二】标题
- 内容要点1
- 内容要点2
- 内容要点3

【三】标题
- 内容要点1
- 内容要点2
- 内容要点3
- 内容要点4

【四】标题
- 内容要点1
- 内容要点2
- 内容要点3""",

        "grid_2x2": """输出4个分析点，每点4-5行。格式：
【一】标题
- 具体分析1
- 具体分析2
- 具体分析3
- 具体分析4

【二】标题
- 具体分析1
- 具体分析2
- 具体分析3

【三】标题
- 具体分析1
- 具体分析2
- 具体分析3
- 具体分析4

【四】标题
- 具体分析1
- 具体分析2
- 具体分析3""",

        "split": """输出人物+3个要点，每要点3-4行。格式：
【人物】
姓名 | 身份标签 | 一句话介绍

【一】要点标题
- 具体内容1
- 具体内容2
- 具体内容3

【二】要点标题
- 具体内容1
- 具体内容2
- 具体内容3

【三】要点标题
- 具体内容1
- 具体内容2
- 具体内容3""",

        "breathing": """输出4-5个核心观点+1句引用。格式：
- 核心观点1（具体阐释）
- 核心观点2（具体阐释）
- 核心观点3（具体阐释）
- 核心观点4（具体阐释）
引用：名言警句原文""",

        "quote": """输出引文+详细赏析。格式：
引文第一行
引文第二行
引文第三行

分析
- 赏析角度1：具体分析
- 赏析角度2：具体分析
- 赏析角度3：具体分析
- 赏析角度4：具体分析""",

        "vocab": """输出8-10个字词。格式（每行一个）：
字词 (拼音) 释义
字词 (拼音) 释义""",

        "formula_step": """输出公式+推导步骤。格式：
公式：y = kx + b

步骤1：具体推导过程
步骤2：具体推导过程
步骤3：具体推导过程
步骤4：具体推导过程

注意：说明公式中各变量的含义""",

        "graph_illustration": """输出图解要点。格式：
要点1：具体说明
要点2：具体说明
要点3：具体说明
要点4：具体说明
要点5：具体说明""",

        "poetry_vertical": """输出诗词+赏析。格式：
诗词第一行
诗词第二行
诗词第三行
诗词第四行
诗词第五行
诗词第六行

赏析1：具体分析
赏析2：具体分析
赏析3：具体分析
赏析4：具体分析

作者：诗人姓名""",

        "timeline": """输出时间轴事件。格式（每行一个事件）：
年份 | 事件描述
年份 | 事件描述
年份 | 事件描述
年份 | 事件描述
年份 | 事件描述""",

        "comparison_table": """输出对比内容。格式：
【左栏标题】
- 对比要点1
- 对比要点2
- 对比要点3
- 对比要点4
- 对比要点5
- 对比要点6

【右栏标题】
- 对比要点1
- 对比要点2
- 对比要点3
- 对比要点4
- 对比要点5
- 对比要点6""",

        "experiment_flow": """输出实验步骤。格式（每行一步）：
步骤名称1
步骤名称2
步骤名称3
步骤名称4
步骤名称5""",

        "structure_diagram": """输出结构图内容。格式：
中心：核心概念名称

分支1：标签 | 简要说明
分支2：标签 | 简要说明
分支3：标签 | 简要说明
分支4：标签 | 简要说明
分支5：标签 | 简要说明
分支6：标签 | 简要说明""",

        "code_block": """输出代码+说明。格式：
语言：python

代码第1行
代码第2行
代码第3行
...

说明1：解释代码功能
说明2：解释关键语法
说明3：解释运行结果""",

        "terminal_output": """输出终端模拟内容。格式（每行一条）：
$ 命令1
输出结果1
输出结果2
$ 命令2
输出结果3""",

        "text_analysis": """输出原文+赏析。格式：
原文
课文中的关键句子1
课文中的关键句子2
课文中的关键句子3
课文中的关键句子4

赏析1：标签 | 具体分析内容
赏析2：标签 | 具体分析内容
赏析3：标签 | 具体分析内容
赏析4：标签 | 具体分析内容""",

        "comparison_two_column": """输出双栏对比内容。格式：
左栏标题
- 对比要点1
- 对比要点2
- 对比要点3
- 对比要点4
- 对比要点5

右栏标题
- 对比要点1
- 对比要点2
- 对比要点3
- 对比要点4
- 对比要点5""",

        "proof_deduction": """输出已知条件+证明步骤。格式：
已知条件1
已知条件2
已知条件3

步骤1：具体推导过程
步骤2：具体推导过程
步骤3：具体推导过程
步骤4：具体推导过程
步骤5：具体推导过程

结论：最终结论""",

        "exercise_steps": """输出3道例题，每题含解题步骤。格式：
例题1：题目内容
步骤1-1：解题步骤
步骤1-2：解题步骤
步骤1-3：解题步骤
答案：最终答案

例题2：题目内容
步骤2-1：解题步骤
步骤2-2：解题步骤
答案：最终答案

例题3：题目内容
步骤3-1：解题步骤
步骤3-2：解题步骤
步骤3-3：解题步骤
答案：最终答案""",

        "vocab_cards": """输出8-10个英语词汇。格式（每行一个）：
单词 (音标) 中文释义 | 例句
单词 (音标) 中文释义 | 例句""",

        "role_dialogue": """输出角色对话。格式：
场景：对话场景描述

角色A：英文对话内容 | 中文翻译
角色B：英文对话内容 | 中文翻译
角色A：英文对话内容 | 中文翻译
角色B：英文对话内容 | 中文翻译
角色A：英文对话内容 | 中文翻译
角色B：英文对话内容 | 中文翻译""",

        "sentence_pattern": """输出4个句型，每个含例句和练习。格式：
句型：主语 + 谓语 + 宾语
例句1：具体例句
例句2：具体例句
例句3：具体例句
练习：替换练习题目

句型：There be + 名词 + 地点
例句1：具体例句
例句2：具体例句
练习：替换练习题目

句型：一般疑问句
例句1：具体例句
例句2：具体例句
练习：替换练习题目

句型：特殊疑问句
例句1：具体例句
例句2：具体例句
练习：替换练习题目""",

        "data_table": """输出表格数据。格式：
表头1 | 表头2 | 表头3 | 表头4
数据1 | 数据2 | 数据3 | 数据4
数据1 | 数据2 | 数据3 | 数据4
数据1 | 数据2 | 数据3 | 数据4
数据1 | 数据2 | 数据3 | 数据4
数据1 | 数据2 | 数据3 | 数据4

说明：表格数据的分析说明""",

        "map_annotation": """输出地图标注点。格式：
标注1：位置名称 | 具体说明
标注2：位置名称 | 具体说明
标注3：位置名称 | 具体说明
标注4：位置名称 | 具体说明
标注5：位置名称 | 具体说明

描述：整体地理/历史背景描述""",

        "flowchart": """输出流程图步骤。格式：
步骤1：步骤名称 | 具体说明
步骤2：步骤名称 | 具体说明
判断：判断条件
步骤3：步骤名称 | 具体说明
步骤4：步骤名称 | 具体说明
步骤5：步骤名称 | 具体说明""",

        "tech_dark": """输出技术要点卡片。格式：
要点1：标签 | 具体内容说明
要点2：标签 | 具体内容说明
要点3：标签 | 具体内容说明
要点4：标签 | 具体内容说明
要点5：标签 | 具体内容说明
要点6：标签 | 具体内容说明""",
    }

    system_prompt = f"""你是一个资深{subject or '语文'}教师，正在为《{topic}》这节课准备教学课件。
这个PPT将直接用于课堂教学，内容必须饱满、具体、有教学深度。

当前页面：{page_spec['title']}
页面说明：{page_spec.get('content', '')}

{f'教材参考内容（基于网络搜索）：\n{search_context}\n请优先使用以上内容中的真实知识点、公式和例题。\n' if search_context else ''}

{layout_instructions.get(layout, '输出相关内容，每行一条')}

要求：
1. 每行控制在25个汉字以内，内容简洁有力
2. 必须包含具体的知识点、例子、原文引用，不能泛泛而谈
3. 内容要有层次感：从具体到抽象，从表层到深层
4. 适合初中生理解水平，兼顾知识性和趣味性
5. 直接输出内容，不要编号以外的标记
6. 不要输出解释说明或多余的客套话"""

    user_msg = f"请为《{topic}》的「{page_spec['title']}」页面生成教学内容，要求内容饱满充实，可以直接用于课堂讲解。"

    raw_text = None
    data = {}
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=app_config.OPENAI_MODEL,
                max_tokens=2500,
                temperature=0.6 if attempt > 0 else 0.8,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
            )
            raw_text = response.choices[0].message.content
            if not raw_text or len(raw_text.strip()) < 10:
                logger.warning(f"AI 内容第{attempt+1}次返回过短: {len(raw_text or '')}字符")
                continue
            data = _parse_text_content(raw_text, layout)

            # 验证数据有效性
            if layout in ("three_card", "four_card") and data.get("cards") and len(data["cards"]) >= 2:
                break
            elif layout == "grid_2x2" and data.get("items") and len(data["items"]) >= 2:
                break
            elif layout == "split" and data.get("right") and len(data["right"]) >= 2:
                break
            elif layout == "breathing" and data.get("points") and len(data["points"]) >= 2:
                break
            elif layout in ("quote", "vocab") and data:
                break
            # 新增布局验证
            elif layout == "text_analysis" and data.get("original") and data.get("analysis"):
                break
            elif layout == "comparison_two_column" and data.get("left") and data.get("right"):
                break
            elif layout == "proof_deduction" and data.get("steps") and len(data["steps"]) >= 2:
                break
            elif layout == "exercise_steps" and data.get("exercises") and len(data["exercises"]) >= 1:
                break
            elif layout == "vocab_cards" and data.get("items") and len(data["items"]) >= 3:
                break
            elif layout == "role_dialogue" and data.get("dialogues") and len(data["dialogues"]) >= 3:
                break
            elif layout == "sentence_pattern" and data.get("patterns") and len(data["patterns"]) >= 2:
                break
            elif layout == "data_table" and data.get("headers") and data.get("rows"):
                break
            elif layout == "map_annotation" and data.get("locations") and len(data["locations"]) >= 2:
                break
            elif layout == "flowchart" and data.get("steps") and len(data["steps"]) >= 3:
                break
            elif layout == "tech_dark" and data.get("items") and len(data["items"]) >= 2:
                break
            else:
                logger.warning(f"AI 内容第{attempt+1}次解析结果不足: {list(data.keys())}")
        except Exception as e:
            logger.warning(f"AI 内容生成第{attempt+1}次失败: {e}")

    if raw_text is None or not data:
        logger.warning("AI 内容生成最终失败，使用智能默认")
        data = _smart_default(layout, page_spec, topic, subject)

    title = page_spec["title"]
    icon = _layout_icon(layout)

    if layout == "three_card":
        return generate_three_card_svg(title, icon, data.get("cards", []), theme, page_num, total)
    elif layout == "four_card":
        return generate_four_card_svg(title, icon, data.get("cards", []), theme, page_num, total)
    elif layout == "grid_2x2":
        return generate_grid_2x2_svg(title, icon, data.get("items", []), theme, page_num, total)
    elif layout == "split":
        return generate_split_svg(
            title, icon,
            data.get("left", {"name": "", "subtitle": ""}),
            data.get("right", []),
            theme, page_num, total,
        )
    elif layout == "breathing":
        return generate_breathing_svg(
            [title], "",
            data.get("points", []),
            theme, page_num, total,
            quote=data.get("quote", ""),
        )
    elif layout == "quote":
        return generate_quote_svg(
            data.get("quote_lines", []),
            data.get("analysis_lines", []),
            theme, page_num, total,
        )
    elif layout == "vocab":
        return generate_vocab_svg(title, data.get("items", []), theme, page_num, total)
    elif layout == "toc":
        return generate_toc_svg(data.get("items", []), theme, total)
    # ── 学科专属布局 ──
    elif layout == "formula_step":
        return generate_formula_step_svg(title, data, theme, page_num, total)
    elif layout == "graph_illustration":
        return generate_graph_illustration_svg(title, data, theme, page_num, total)
    elif layout == "poetry_vertical":
        return generate_poetry_vertical_svg(title, data, theme, page_num, total)
    elif layout == "timeline":
        return generate_timeline_svg(title, data.get("events", []), theme, page_num, total)
    elif layout == "comparison_table":
        return generate_comparison_table_svg(title, data.get("columns", []), theme, page_num, total)
    elif layout == "experiment_flow":
        return generate_experiment_flow_svg(title, data.get("steps", []), theme, page_num, total)
    elif layout == "structure_diagram":
        return generate_structure_diagram_svg(
            title, data.get("center", ""), data.get("branches", []),
            theme, page_num, total,
        )
    elif layout == "code_block":
        return generate_code_block_svg(title, data, theme, page_num, total)
    elif layout == "terminal_output":
        return generate_terminal_output_svg(title, data.get("outputs", []), theme, page_num, total)
    # ── 新增专属布局 ──
    elif layout == "text_analysis":
        return generate_text_analysis_svg(title, data, theme, page_num, total)
    elif layout == "comparison_two_column":
        return generate_comparison_two_column_svg(title, data, theme, page_num, total)
    elif layout == "proof_deduction":
        return generate_proof_deduction_svg(title, data, theme, page_num, total)
    elif layout == "exercise_steps":
        return generate_exercise_steps_svg(title, data.get("exercises", []), theme, page_num, total)
    elif layout == "vocab_cards":
        return generate_vocab_cards_svg(title, data.get("items", []), theme, page_num, total)
    elif layout == "role_dialogue":
        return generate_role_dialogue_svg(title, data, theme, page_num, total)
    elif layout == "sentence_pattern":
        return generate_sentence_pattern_svg(title, data.get("patterns", []), theme, page_num, total)
    elif layout == "data_table":
        return generate_data_table_svg(title, data, theme, page_num, total)
    elif layout == "map_annotation":
        return generate_map_annotation_svg(title, data, theme, page_num, total)
    elif layout == "flowchart":
        return generate_flowchart_svg(title, data, theme, page_num, total)
    elif layout == "tech_dark":
        return generate_tech_dark_svg(title, data, theme, page_num, total)
    else:
        return generate_three_card_svg(title, icon, data.get("cards", []), theme, page_num, total)


def _layout_icon(layout: str) -> str:
    """布局 → 图标名映射"""
    icons = {
        "three_card": "layout-grid",
        "four_card": "layout-grid",
        "grid_2x2": "layout-grid",
        "split": "layout-sidebar",
        "breathing": "heart",
        "quote": "quote",
        "vocab": "book",
        "vocab_cards": "book",
        "toc": "list",
        "formula_step": "math",
        "graph_illustration": "chart",
        "proof_deduction": "checklist",
        "exercise_steps": "list-checks",
        "poetry_vertical": "feather",
        "text_analysis": "search",
        "comparison_two_column": "columns",
        "role_dialogue": "messages",
        "sentence_pattern": "pilcrow",
        "timeline": "clock",
        "map_annotation": "map-pin",
        "data_table": "table",
        "experiment_flow": "flask",
        "structure_diagram": "network",
        "code_block": "code",
        "flowchart": "git-branch",
        "tech_dark": "cpu",
        "terminal_output": "terminal",
    }
    return icons.get(layout, "file-text")


def _generate_toc_items(topic: str, subject: str, page_spec: dict) -> list:
    """用 AI 生成目录项"""
    app_config = _config_module
    from openai import OpenAI
    client = OpenAI(api_key=app_config.OPENAI_API_KEY, base_url=app_config.OPENAI_BASE_URL)
    try:
        resp = client.chat.completions.create(
            model=app_config.OPENAI_MODEL,
            max_tokens=512,
            temperature=0.5,
            messages=[
                {"role": "system", "content": "输出一个JSON数组，包含8个目录项字符串，每项不超过10个字。只输出JSON。"},
                {"role": "user", "content": f"为《{topic}》这节{subject or '语文'}课设计目录，输出JSON数组。"},
            ],
        )
        raw = resp.choices[0].message.content
        items = json.loads(_repair_json(raw))
        if isinstance(items, list) and len(items) >= 4:
            return items[:8]
    except Exception as e:
        logger.warning(f"目录生成失败: {e}")
    return _default_toc_items(topic, subject)


def _default_toc_items(topic: str, subject: str) -> list:
    """按学科生成默认目录项"""
    if _is_math(subject):
        return ["概念导入", "公式定理", "推导过程", "典型例题", "解题方法", "易错分析", "巩固练习", "课堂总结"]
    if _is_science(subject):
        return ["知识要点", "基本原理", "实验探究", "数据分析", "应用实例", "解题策略", "巩固练习", "课堂总结"]
    if "英语" in subject:
        return ["词汇学习", "语法要点", "课文理解", "句型分析", "口语练习", "写作迁移", "巩固练习", "课堂总结"]
    if _is_humanities(subject):
        return ["时代背景", "核心内容", "重要事件", "因果分析", "多角度思考", "联系现实", "巩固练习", "课堂总结"]
    return ["学习目标", "知识要点", "核心内容", "方法技巧", "实践应用", "拓展提升", "巩固练习", "课堂总结"]


def _smart_default(layout: str, page_spec: dict, topic: str, subject: str) -> dict:
    """智能默认内容（基于学科和主题生成通用教学内容，不绑定具体课文）"""
    title = page_spec.get("title", "")
    subj = subject or ""

    # ── 三栏/四栏卡片布局 ──
    if layout in ("three_card", "four_card"):
        cards = _default_cards(title, topic, subj, layout)
        return {"cards": cards}

    # ── 2x2网格布局 ──
    if layout == "grid_2x2":
        return {"items": _default_grid_items(title, topic, subj)}

    # ── 左右分栏布局 ──
    if layout == "split":
        return _default_split(title, topic, subj)

    # ── 留白呼吸页 ──
    if layout == "breathing":
        return _default_breathing(title, topic, subj)

    # ── 引文页 ──
    if layout == "quote":
        return _default_quote(title, topic, subj)

    # ── 字词卡片 ──
    if layout == "vocab":
        return {"items": _default_vocab(topic, subj)}

    return {"cards": [{"number": "一", "title": "内容", "lines": [f"{title}相关内容"]}]}


def _is_math(subject: str) -> bool:
    return any(k in subject for k in ("数学", "几何", "代数"))

def _is_science(subject: str) -> bool:
    return any(k in subject for k in ("物理", "化学", "生物", "科学"))

def _is_language(subject: str) -> bool:
    return any(k in subject for k in ("语文", "英语", "外语"))

def _is_humanities(subject: str) -> bool:
    return any(k in subject for k in ("历史", "地理", "政治", "道德"))


def _default_cards(title: str, topic: str, subject: str, layout: str) -> list:
    """按学科生成三栏/四栏卡片默认内容"""

    # 数学
    if _is_math(subject):
        cards = [
            {"number": "一", "title": "概念导入", "lines": [
                f"{topic}的定义与基本概念",
                "从实际问题引出数学模型",
                "回顾相关前置知识",
                "明确学习目标与重难点",
            ]},
            {"number": "二", "title": "公式与定理", "lines": [
                f"{topic}的核心公式推导",
                "定理的条件与结论",
                "公式中各变量的含义",
                "常见变形与等价形式",
            ]},
            {"number": "三", "title": "典型例题", "lines": [
                "基础题：直接套用公式",
                "综合题：结合多个知识点",
                "应用题：解决实际问题",
                "解题步骤与规范书写",
            ]},
        ]
        if layout == "four_card":
            cards.append({"number": "四", "title": "巩固练习", "lines": [
                "基础计算练习",
                "变式训练与举一反三",
                "易错点辨析与纠正",
                "拓展提高题",
            ]})
        return cards

    # 物理/化学/生物/科学
    if _is_science(subject):
        cards = [
            {"number": "一", "title": "知识要点", "lines": [
                f"{topic}的核心概念",
                "基本原理与规律",
                "关键公式与定律",
                "适用条件与范围",
            ]},
            {"number": "二", "title": "实验探究", "lines": [
                "实验目的与原理",
                "实验步骤与操作",
                "数据记录与分析",
                "实验结论与误差",
            ]},
            {"number": "三", "title": "应用实例", "lines": [
                "生活中的实际应用",
                "科技前沿中的运用",
                "解题方法与技巧",
                "常见题型归纳",
            ]},
        ]
        if layout == "four_card":
            cards.append({"number": "四", "title": "巩固提高", "lines": [
                "基础概念练习",
                "实验设计题",
                "综合计算题",
                "拓展思考题",
            ]})
        return cards

    # 英语
    if "英语" in subject or "外语" in subject:
        cards = [
            {"number": "一", "title": "词汇学习", "lines": [
                f"{topic}相关核心词汇",
                "重点短语与搭配",
                "词汇的词性与用法",
                "例句与语境理解",
            ]},
            {"number": "二", "title": "语法要点", "lines": [
                "本课重点语法结构",
                "语法规则与例外",
                "典型句型分析",
                "常见错误辨析",
            ]},
            {"number": "三", "title": "阅读与表达", "lines": [
                "课文内容理解",
                "关键信息提取",
                "口语表达练习",
                "写作迁移应用",
            ]},
        ]
        if layout == "four_card":
            cards.append({"number": "四", "title": "练习巩固", "lines": [
                "词汇填空与选择",
                "语法专项练习",
                "阅读理解训练",
                "写作练习",
            ]})
        return cards

    # 历史/地理/政治
    if _is_humanities(subject):
        cards = [
            {"number": "一", "title": "背景知识", "lines": [
                f"{topic}的时代背景",
                "相关历史事件脉络",
                "重要人物与事件",
                "关键时间节点",
            ]},
            {"number": "二", "title": "核心内容", "lines": [
                f"{topic}的主要内容",
                "重要概念与观点",
                "因果关系分析",
                "核心知识点梳理",
            ]},
            {"number": "三", "title": "分析思考", "lines": [
                "多角度分析问题",
                "评价与反思",
                "联系现实思考",
                "拓展延伸阅读",
            ]},
        ]
        if layout == "four_card":
            cards.append({"number": "四", "title": "巩固练习", "lines": [
                "基础知识点填空",
                "材料分析题",
                "论述与评价题",
                "拓展思考题",
            ]})
        return cards

    # 语文（通用，不绑定具体课文）
    if "语文" in subject:
        cards = [
            {"number": "一", "title": "学习目标", "lines": [
                f"理解{topic}的主要内容",
                "掌握重点字词与语句",
                "体会作者的写作意图",
                "培养阅读理解能力",
            ]},
            {"number": "二", "title": "内容分析", "lines": [
                "梳理文章结构层次",
                "分析关键段落与语句",
                "理解写作手法与技巧",
                "品味语言特色与风格",
            ]},
            {"number": "三", "title": "拓展提升", "lines": [
                "联系生活实际思考",
                "比较阅读同类作品",
                "积累优美语言素材",
                "培养文学鉴赏能力",
            ]},
        ]
        if layout == "four_card":
            cards.append({"number": "四", "title": "课后练习", "lines": [
                "字词积累与运用",
                "阅读理解练习",
                "写作片段练习",
                "拓展阅读推荐",
            ]})
        return cards

    # 通用（其他学科）
    cards = [
        {"number": "一", "title": "知识要点", "lines": [
            f"理解{topic}的核心概念",
            "掌握基本原理与方法",
            "了解相关背景知识",
            "明确学习重点与难点",
        ]},
        {"number": "二", "title": "能力提升", "lines": [
            f"分析{topic}的实际应用",
            "培养解决问题的能力",
            "锻炼思维与表达能力",
            "学会举一反三",
        ]},
        {"number": "三", "title": "拓展延伸", "lines": [
            "联系实际生活思考",
            "跨学科知识整合",
            "自主探究与合作学习",
            "总结反思与提升",
        ]},
    ]
    if layout == "four_card":
        cards.append({"number": "四", "title": "巩固练习", "lines": [
            "基础知识点练习",
            "综合应用题",
            "拓展提高题",
            "自主探究题",
        ]})
    return cards

# ── 辅助函数：按学科生成默认内容 ──

def _default_grid_items(title: str, topic: str, subject: str) -> list:
    """按学科生成2x2网格默认内容"""
    if _is_math(subject):
        return [
            {"title": "概念理解", "lines": [f"{topic}的定义与内涵", "核心概念的辨析", "与相关概念的区别", "概念的实际意义"]},
            {"title": "公式推导", "lines": ["公式的推导过程", "各变量的含义", "公式的适用条件", "常见变形形式"]},
            {"title": "解题方法", "lines": ["审题与分析思路", "解题步骤与规范", "多种解法比较", "验算与检查方法"]},
            {"title": "易错分析", "lines": ["常见错误类型", "错误原因分析", "纠正方法与技巧", "防错策略总结"]},
        ]
    if _is_science(subject):
        return [
            {"title": "基本原理", "lines": [f"{topic}的核心原理", "基本规律与公式", "适用范围与条件", "物理/化学意义"]},
            {"title": "实验探究", "lines": ["实验设计思路", "操作步骤与要点", "数据处理方法", "结论与误差分析"]},
            {"title": "应用实例", "lines": ["生活中的应用", "科技领域的应用", "工程实践中的应用", "前沿研究动态"]},
            {"title": "解题策略", "lines": ["常见题型归纳", "解题思路与方法", "计算技巧与规范", "综合题分析策略"]},
        ]
    return [
        {"title": "内容梳理", "lines": [f"分析{topic}的核心内容", "梳理知识脉络", "把握重点与难点", "提炼关键信息"]},
        {"title": "方法技巧", "lines": ["学习方法与策略", "解题技巧与思路", "分析问题的角度", "总结归纳的方法"]},
        {"title": "实践应用", "lines": ["知识的实际运用", "联系生活实际", "解决实际问题", "拓展延伸思考"]},
        {"title": "总结反思", "lines": ["本课知识总结", "学习方法反思", "易错点整理", "下步学习计划"]},
    ]


def _default_split(title: str, topic: str, subject: str) -> dict:
    """按学科生成左右分栏默认内容"""
    if _is_math(subject):
        return {
            "left": {"name": topic, "subtitle": subject, "icon_text": "数", "desc": f"{subject}核心知识点"},
            "right": [
                {"title": "基本概念", "lines": [f"{topic}的定义与性质", "核心公式与定理", "概念间的联系与区别"]},
                {"title": "典型例题", "lines": ["基础题型解析", "综合应用题分析", "解题步骤与规范"]},
                {"title": "学习方法", "lines": ["理解记忆的技巧", "解题思维的培养", "常见错误的避免"]},
            ],
        }
    if _is_science(subject):
        return {
            "left": {"name": topic, "subtitle": subject, "icon_text": "科", "desc": f"{subject}核心知识"},
            "right": [
                {"title": "基本原理", "lines": [f"{topic}的核心原理", "基本规律与公式", "适用条件与范围"]},
                {"title": "实验探究", "lines": ["实验目的与方法", "操作步骤与要点", "数据分析与结论"]},
                {"title": "应用拓展", "lines": ["生活中的应用", "科技前沿动态", "跨学科联系"]},
            ],
        }
    return {
        "left": {"name": topic, "subtitle": subject or "教学内容", "icon_text": topic[0] if topic else "学", "desc": f"{subject}核心知识点"},
        "right": [
            {"title": "知识要点", "lines": [f"{topic}的核心概念", "基本原理与方法", "重点与难点分析"]},
            {"title": "学习方法", "lines": ["理解与记忆技巧", "分析与应用能力", "总结与反思方法"]},
            {"title": "拓展提升", "lines": ["知识的实际运用", "跨学科思考", "自主探究学习"]},
        ],
    }


def _default_breathing(title: str, topic: str, subject: str) -> dict:
    """按学科生成留白呼吸页默认内容"""
    if _is_math(subject):
        return {"points": [f"{topic}的核心数学思想", "逻辑推理与抽象思维的培养", "从特殊到一般的归纳方法", "数学之美在于简洁与严谨"], "quote": ""}
    if _is_science(subject):
        return {"points": [f"{topic}揭示的自然规律", "科学探究精神与方法", "理论与实践相结合", "科学改变世界的力量"], "quote": ""}
    if "英语" in subject:
        return {"points": [f"{topic}的语言学习价值", "语言是沟通世界的桥梁", "学好英语开阔国际视野", "坚持积累方能融会贯通"], "quote": ""}
    return {"points": [f"{topic}的核心学习价值", "知识与能力的双重提升", "学以致用的实践精神", "终身学习的成长态度"], "quote": ""}


def _default_quote(title: str, topic: str, subject: str) -> dict:
    """按学科生成引文页默认内容"""
    if _is_math(subject):
        return {
            "quote_lines": ["数学是科学的女王", "数论是数学的女王", "——高斯"],
            "analysis_lines": ["数学在科学体系中的核心地位", "数学为其他学科提供语言和工具", "学习数学培养严密的逻辑思维", "数学之美在于简洁与统一"],
        }
    if _is_science(subject):
        return {
            "quote_lines": ["科学的唯一目的是减轻人类生存的苦难", "科学家在这方面做出贡献", "——布莱希特"],
            "analysis_lines": ["科学研究的终极目标是服务人类", "科学家的社会责任与使命", f"{topic}的实际应用价值", "科学精神与人文关怀的统一"],
        }
    return {
        "quote_lines": ["学而不思则罔", "思而不学则殆", "——孔子"],
        "analysis_lines": ["学习与思考必须相结合", "只学不思则迷惑不解", "只思不学则陷入空想", "知行合一才是学习之道"],
    }


def _default_vocab(topic: str, subject: str) -> list:
    """按学科生成字词/术语卡片默认内容"""
    if _is_math(subject):
        return [
            {"word": "定义", "pinyin": "dìng yì", "meaning": "对数学对象本质特征的描述"},
            {"word": "定理", "pinyin": "dìng lǐ", "meaning": "经过证明的数学命题"},
            {"word": "公式", "pinyin": "gōng shì", "meaning": "用数学符号表示的关系式"},
            {"word": "推导", "pinyin": "tuī dǎo", "meaning": "根据已知命题推出新结论"},
            {"word": "证明", "pinyin": "zhèng míng", "meaning": "用逻辑推理验证命题正确性"},
            {"word": "逆命题", "pinyin": "nì mìng tí", "meaning": "将原命题条件和结论互换"},
        ]
    if "物理" in subject:
        return [
            {"word": "力", "pinyin": "lì", "meaning": "物体间的相互作用"},
            {"word": "速度", "pinyin": "sù dù", "meaning": "描述物体运动快慢的物理量"},
            {"word": "加速度", "pinyin": "jiā sù dù", "meaning": "速度变化量与时间的比值"},
            {"word": "功", "pinyin": "gōng", "meaning": "力与位移的乘积"},
            {"word": "能量", "pinyin": "néng liàng", "meaning": "物体做功的能力"},
            {"word": "压强", "pinyin": "yā qiáng", "meaning": "单位面积上受到的压力"},
        ]
    if "化学" in subject:
        return [
            {"word": "元素", "pinyin": "yuán sù", "meaning": "具有相同核电荷数的原子总称"},
            {"word": "分子", "pinyin": "fēn zǐ", "meaning": "保持物质化学性质的最小粒子"},
            {"word": "原子", "pinyin": "yuán zǐ", "meaning": "化学变化中的最小粒子"},
            {"word": "化合价", "pinyin": "huà hé jià", "meaning": "元素原子间结合的能力"},
            {"word": "氧化", "pinyin": "yǎng huà", "meaning": "物质与氧发生的化学反应"},
            {"word": "催化剂", "pinyin": "cuī huà jì", "meaning": "改变化学反应速率的物质"},
        ]
    if "英语" in subject:
        return [
            {"word": "vocabulary", "pinyin": "/vəˈkæbjəleri/", "meaning": "词汇，词汇量"},
            {"word": "grammar", "pinyin": "/ˈɡræmər/", "meaning": "语法"},
            {"word": "pronunciation", "pinyin": "/prəˌnʌnsiˈeɪʃn/", "meaning": "发音"},
            {"word": "sentence", "pinyin": "/ˈsentəns/", "meaning": "句子"},
            {"word": "paragraph", "pinyin": "/ˈpærəɡræf/", "meaning": "段落"},
            {"word": "expression", "pinyin": "/ɪkˈspreʃn/", "meaning": "表达，措辞"},
        ]
    return [
        {"word": "概念一", "pinyin": "gài niàn yī", "meaning": f"{topic}相关核心概念"},
        {"word": "概念二", "pinyin": "gài niàn èr", "meaning": f"{topic}相关核心概念"},
        {"word": "概念三", "pinyin": "gài niàn sān", "meaning": f"{topic}相关核心概念"},
        {"word": "概念四", "pinyin": "gài niàn sì", "meaning": f"{topic}相关核心概念"},
        {"word": "概念五", "pinyin": "gài niàn wǔ", "meaning": f"{topic}相关核心概念"},
        {"word": "概念六", "pinyin": "gài niàn liù", "meaning": f"{topic}相关核心概念"},
    ]


# ─────────────────── Executor 集成（ppt-master 原生流程） ───────────────────

# SVG 禁用特性列表（ppt-master shared-standards.md）
SVG_BANNED_FEATURES = [
    "<mask", "<style", "class=", "<foreignObject",
    "<symbol", "<use", "textPath", "@font-face",
    "<animate", "<script", "<iframe",
    "&mdash;", "&ndash;", "&copy;", "&reg;", "&rarr;", "&middot;", "&nbsp;",
]

# 页面节奏说明
PAGE_RHYTHM_DOCS = {
    "anchor": "结构性页面（封面/章节/目录/结束页）。严格遵循模板结构。",
    "dense": "信息密集页面。可用卡片网格、多栏布局、表格、图表等。这是默认行为。",
    "breathing": "低密度留白页面。避免多卡片网格布局，使用大段文字、引文、全屏图片、过渡页等。",
}

# ─────────────────── 质量校验增强（API 调用适配层） ───────────────────

class SVGQualityError(Exception):
    """SVG 质量校验失败"""
    pass


def validate_svg_strict(svg_content: str, page_spec: dict = None, theme: dict = None) -> tuple:
    """
    严格版 SVG 验证，确保对齐原生 IDE 环境质量

    增强点：
    1. viewBox 必须为 1280x720（不再容忍）
    2. 检查基本结构完整性
    """
    # 基础校验
    is_valid, error = validate_svg(svg_content)
    if not is_valid:
        return False, error

    # viewBox 必须精确（不再容忍）
    if 'viewBox="0 0 1280 720"' not in svg_content and "viewBox='0 0 1280 720'" not in svg_content:
        return False, "viewBox 不是 1280x720"

    # 检查 SVG 长度（太短可能有问题）
    if len(svg_content) < 500:
        return False, f"SVG 内容太短 ({len(svg_content)} 字节)"

    return True, ""


def repair_svg(svg_content: str, page_spec: dict, theme: dict = None) -> str:
    """
    自动修复常见的 SVG 问题

    修复项：
    1. 确保 viewBox 正确
    2. 修复 HTML 实体
    3. 确保页码存在
    4. 修复常见 XML 问题
    """
    import re

    # 确保 theme 不为 None
    if theme is None:
        theme = {}

    # 修复 HTML 实体
    svg_content = svg_content.replace("&mdash;", "—").replace("&ndash;", "–")
    svg_content = svg_content.replace("&copy;", "©").replace("&reg;", "®")
    svg_content = svg_content.replace("&rarr;", "→").replace("&middot;", "·")
    svg_content = svg_content.replace("&nbsp;", " ").replace("&hellip;", "…")
    svg_content = svg_content.replace("&bull;", "•")

    # 确保 viewBox 正确
    if 'viewBox="0 0 1280 720"' not in svg_content and "viewBox='0 0 1280 720'" not in svg_content:
        # 替换错误的 viewBox
        svg_content = re.sub(r'viewBox="[^"]*"', 'viewBox="0 0 1280 720"', svg_content)
        svg_content = re.sub(r"viewBox='[^']*'", "viewBox='0 0 1280 720'", svg_content)

    # 确保包含页码（如果缺少）
    page_num = page_spec.get("page_num", 1) if page_spec else 1
    total = page_spec.get("total", 1) if page_spec else 1
    page_code = f"{page_num:02d} / {total:02d}"
    if page_code not in svg_content and f"{page_num}/{total}" not in svg_content:
        # 在页脚区域添加页码
        footer_pattern = re.compile(r'(<g\s+id="footer[^"]*"[^>]*>)', re.IGNORECASE)
        match = footer_pattern.search(svg_content)
        if match:
            insert_pos = match.end()
            body_font = theme.get('body_font', 'Arial') if theme else 'Arial'
            text_light = theme.get('text_light', '#999999') if theme else '#999999'
            page_num_text = f'''<text x="640" y="695" text-anchor="middle" font-family="{body_font}" font-size="11" fill="{text_light}">{page_code}</text>'''
            svg_content = svg_content[:insert_pos] + "\n" + page_num_text + svg_content[insert_pos:]

    return svg_content


def generate_svg_with_quality_check(
    page_spec: dict,
    page_num: int,
    total: int,
    spec_lock_content: str,
    design_spec_content: str,
    theme: dict,
    topic: str,
    subject: str,
    search_context: str = "",
    template_svgs: dict = None,
    available_images: list = None,
    previous_svgs: list = None,
    max_retries: int = None,  # 修改：默认使用配置值
) -> str:
    """
    带质量回环的 SVG 生成（对齐原生 IDE 环境）

    与 generate_svg_with_executor 的区别：
    1. 使用严格校验（validate_svg_strict）
    2. 失败时自动修复（repair_svg）
    3. 修复后仍失败则返回（不重试，避免卡住）
    """
    app_config = _config_module
    from openai import OpenAI

    # 使用配置中的重试次数（如果未指定）
    if max_retries is None:
        max_retries = getattr(app_config, 'PPT_SVG_MAX_RETRIES', 3)

    # 确保 page_num 和 total 不为 None
    if page_num is None:
        page_num = 1
    if total is None:
        total = 1

    client = OpenAI(api_key=app_config.OPENAI_API_KEY, base_url=app_config.OPENAI_BASE_URL)

    for attempt in range(max_retries):
        # 构建 system prompt
        system_prompt = build_executor_prompt(
            spec_lock_content, design_spec_content, theme,
            page_num, total, page_spec, topic, subject, template_svgs,
            available_images, previous_svgs,
        )

        # 构建 user prompt
        layout = page_spec.get("layout", "three_card")
        title = page_spec.get("title", "")
        content_desc = page_spec.get("content", "")

        user_msg = f"""请为《{topic}》的第{page_num}页「{title}」手写 SVG。

页面布局: {layout}
{f'内容要点: {content_desc}' if content_desc else ''}
{f'教材参考: {search_context[:800]}' if search_context else ''}

要求：
- 完整的 SVG 代码，<svg> 开头，</svg> 结尾
- 不要 markdown 代码块，不要解释
- 严格使用上方配色方案中的颜色
- 每个内容区块用 <g id="xxx"> 包裹
- viewBox 必须是 "0 0 1280 720" """

        try:
            response = client.chat.completions.create(
                model=app_config.OPENAI_MODEL,
                max_tokens=8000,
                temperature=0.4 if attempt > 0 else 0.5,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
            )
            raw = response.choices[0].message.content
            svg = clean_svg_output(raw)

            # 严格校验
            is_valid, error = validate_svg_strict(svg, page_spec, theme)

            if is_valid:
                return svg

            # 校验失败，尝试修复
            logger.warning(f"SVG 校验失败 (尝试 {attempt+1}/{max_retries}): {error}")
            svg_repaired = repair_svg(svg, page_spec, theme)

            # 修复后返回（不再二次校验，避免卡住）
            return svg_repaired

        except Exception as e:
            logger.warning(f"API 调用失败 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                # 最后一次尝试失败，返回空 SVG
                logger.error(f"SVG 生成全部失败: {e}")
                return f'<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg"><text x="640" y="360" text-anchor="middle" font-size="24" fill="#666">生成失败</text></svg>'

    return svg if 'svg' in dir() else '<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg"><text x="640" y="360" text-anchor="middle" font-size="24" fill="#666">生成失败</text></svg>'


def build_executor_prompt(
    spec_lock_content: str,
    design_spec_content: str,
    theme: dict,
    page_num: int,
    total: int,
    page_spec: dict,
    topic: str,
    subject: str,
    template_svgs: dict = None,
    available_images: list = None,
    previous_svgs: list = None,
) -> str:
    """构建 Executor 角色的 system prompt，包含已生成的SVG上下文"""
    # 确保所有参数不为 None
    if theme is None:
        theme = {}
    if page_num is None:
        page_num = 1
    if total is None:
        total = 1

    layout = page_spec.get("layout", "three_card") if page_spec else "three_card"
    title = page_spec.get("title", "") if page_spec else ""
    rhythm = page_spec.get("rhythm", "dense") if page_spec else "dense"
    content_desc = page_spec.get("content", "") if page_spec else ""

    # 配色方案
    colors_section = f"""配色方案（严格使用，不得自行发明颜色）：
- 背景色: {theme.get('bg', '#FAFAFA')}
- 主色: {theme.get('primary', '#37474F')}
- 强调色: {theme.get('accent', '#CC0000')}
- 辅助色: {theme.get('accent2', '#0066CC')}
- 文字色: {theme.get('text', '#1A1A1A')}
- 次要文字: {theme.get('text_secondary', '#555555')}
- 浅色文字: {theme.get('text_light', '#999999')}
- 卡片背景: {theme.get('card_bg', '#FFFFFF')}
- 卡片边框: {theme.get('card_border', '#E0E0E0')}
- 页眉背景: {theme.get('header_bg', theme.get('primary', '#37474F'))}"""

    # 字体方案
    font_section = f"""字体方案：
- 标题字体: {theme.get('title_font', 'Microsoft YaHei, SimHei, Arial, sans-serif')}
- 正文字体: {theme.get('body_font', 'Microsoft YaHei, PingFang SC, Arial, sans-serif')}
- 基准字号: {theme.get('baseline', 20)}px
- 标题字号: 26-36px（页面标题）/ 48-56px（封面标题）
- 正文字号: 15-18px
- 注释字号: 12-14px"""

    # 模板 SVG 参考
    template_section = ""
    if template_svgs:
        template_section = "\n模板 SVG 参考（可继承结构，但内容区域自由设计）：\n"
        for name, svg_content in template_svgs.items():
            # 只取前 500 字符作为参考
            template_section += f"\n--- {name} ---\n{svg_content[:500]}\n"

    # 页面节奏说明
    rhythm_doc = PAGE_RHYTHM_DOCS.get(rhythm, PAGE_RHYTHM_DOCS["dense"])

    prompt = f"""你是 PPT Master 的 Executor 角色，负责为教学课件逐页手写 SVG。

═══════════════════════════════════════════════════
【画布规格】
═══════════════════════════════════════════════════
- 格式: PPT 16:9
- 尺寸: 1280 x 720 px
- viewBox: "0 0 1280 720"
- 页边距: 左右 40px, 上 0px（页眉占 70px）, 下 35px（页脚占 50px）
- 安全区域: x=40~1240, y=70~670

═══════════════════════════════════════════════════
【SVG 技术约束（必须严格遵守）】
═══════════════════════════════════════════════════

禁止使用以下特性（PPT 导出会崩溃）：
- <mask>, <style>, class=, <foreignObject>
- <symbol> + <use>, textPath, @font-face
- <animate*>, <set>, <script>, 事件属性
- <iframe>, 外部 CSS

文字规则：
- 所有文字必须是合法 XML（& 必须写成 &amp;，< 必须写成 &lt;）
- 禁止 HTML 实体（&mdash; &nbsp; 等），直接用 Unicode 字符（— · 等）

可用特性：
- <linearGradient>, <radialGradient>（渐变）
- clipPath（仅用于 <image> 裁切）
- marker-start/marker-end（箭头，需在 <defs> 中定义）
- <pattern>（图案填充，需标注 data-pptx-pattern）

装饰元素要求（提升视觉效果）：
- 封面页：使用渐变背景、装饰圆形、透明度效果
- 内容页：使用渐变线条、装饰圆形点缀
- 卡片布局：使用阴影效果（filter: drop-shadow）
- 所有页面：在 <defs> 中定义渐变，使用 url(#id) 引用

═══════════════════════════════════════════════════
【配色与字体】
═══════════════════════════════════════════════════

{colors_section}

{font_section}

═══════════════════════════════════════════════════
【当前页面信息】
═══════════════════════════════════════════════════

- 页码: P{page_num:02d} / 共 {total} 页
- 标题: {title}
- 布局类型: {layout}
- 页面节奏: {rhythm} — {rhythm_doc}
- 内容描述: {content_desc}

{f'学科: {subject}' if subject else ''}
{f'主题: {topic}' if topic else ''}

{'═══════════════════════════════════════════════════' if available_images else ''}
{'【可用图片】' if available_images else ''}
{'═══════════════════════════════════════════════════' if available_images else ''}
{'以下图片已下载到 images/ 目录，请在 SVG 中引用：' if available_images else ''}
{chr(10).join(f'- ../images/{img["filename"]} — {img["query"]}' for img in (available_images or []))}
{'图片引用格式：<image href="../images/文件名" x="坐标" y="坐标" width="宽度" height="高度" preserveAspectRatio="xMidYMid slice"/>' if available_images else ''}
{'图片必须放在安全区域内（x=40~1240, y=70~670）' if available_images else ''}

═══════════════════════════════════════════════════
【输出要求】
═══════════════════════════════════════════════════

1. 输出完整的 SVG 代码，以 <svg> 开头，以 </svg> 结尾
2. 不要输出 markdown 代码块（不要 ```svg）
3. 不要输出任何解释文字，只输出 SVG
4. 每个内容区块用 <g id="xxx"> 包裹（用于动画）
5. 页脚包含页码：{page_num:02d} / {total:02d}
6. 确保所有颜色来自上方配色方案
7. 确保所有文字是合法 XML
{'8. 有可用图片时，合理使用图片增强视觉效果' if available_images else ''}

{template_section}

{'═══════════════════════════════════════════════════' if previous_svgs else ''}
{'【已生成页面上下文】' if previous_svgs else ''}
{'═══════════════════════════════════════════════════' if previous_svgs else ''}
{'以下是已生成的前几页SVG，请保持视觉一致性（配色、字体、装饰元素、间距等）：' if previous_svgs else ''}
{chr(10).join(f'--- 第{svg["page_num"]}页: {svg["title"]} ---' + chr(10) + svg["svg"][:1500] + chr(10) + '...(截断)' if len(svg["svg"]) > 1500 else svg["svg"] for svg in (previous_svgs or []))}"""

    return prompt


def clean_svg_output(raw: str) -> str:
    """清理 AI 返回的 SVG 输出"""
    s = raw.strip()

    # 去掉 markdown 代码块包裹
    if "```svg" in s:
        s = s.split("```svg")[1].split("```")[0].strip()
    elif "```xml" in s:
        s = s.split("```xml")[1].split("```")[0].strip()
    elif "```" in s:
        parts = s.split("```")
        if len(parts) >= 3:
            s = parts[1].strip()
            # 如果第一行是语言标识，去掉
            if s.startswith(("svg", "xml", "html")):
                s = s.split("\n", 1)[1].strip()

    # 确保以 <svg 开头
    svg_start = s.find("<svg")
    if svg_start > 0:
        s = s[svg_start:]
    elif svg_start < 0:
        # 没找到 <svg，返回原内容让验证失败
        return s

    # 确保以 </svg> 结尾
    svg_end = s.rfind("</svg>")
    if svg_end >= 0:
        s = s[:svg_end + len("</svg>")]

    # 修复常见 XML 问题
    # 将 HTML 实体替换为 Unicode
    s = s.replace("&mdash;", "—").replace("&ndash;", "–")
    s = s.replace("&copy;", "©").replace("&reg;", "®")
    s = s.replace("&rarr;", "→").replace("&middot;", "·")
    s = s.replace("&nbsp;", " ").replace("&hellip;", "…")
    s = s.replace("&bull;", "•")

    return s


def validate_svg(svg_content: str) -> tuple:
    """验证 SVG 是否符合 ppt-master 规范，返回 (is_valid, error_msg)"""
    if not svg_content:
        return False, "SVG 内容为空"

    if "<svg" not in svg_content:
        return False, "缺少 <svg> 标签"

    if "</svg>" not in svg_content:
        return False, "缺少 </svg> 闭合标签"

    if 'viewBox="0 0 1280 720"' not in svg_content and "viewBox='0 0 1280 720'" not in svg_content:
        # 尝试容忍，但记录警告
        pass

    # 检查禁用特性
    for banned in SVG_BANNED_FEATURES:
        if banned in svg_content:
            return False, f"包含禁用特性: {banned}"

    # 检查基本结构
    if "<rect" not in svg_content and "<text" not in svg_content:
        return False, "SVG 缺少基本元素（rect/text）"

    return True, ""


def generate_svg_with_executor(
    page_spec: dict,
    page_num: int,
    total: int,
    spec_lock_content: str,
    design_spec_content: str,
    theme: dict,
    topic: str,
    subject: str,
    search_context: str = "",
    template_svgs: dict = None,
    available_images: list = None,
    previous_svgs: list = None,
    strict_mode: bool = True,  # 新增：严格模式开关
) -> str:
    """
    调用 OpenAI API 逐页生成 SVG（Executor 角色），保持上下文

    参数:
        strict_mode: 是否使用严格质量校验（默认开启，对齐原生 IDE 环境）
    """
    # 严格模式下使用增强版质量校验
    if strict_mode:
        return generate_svg_with_quality_check(
            page_spec=page_spec,
            page_num=page_num,
            total=total,
            spec_lock_content=spec_lock_content,
            design_spec_content=design_spec_content,
            theme=theme,
            topic=topic,
            subject=subject,
            search_context=search_context,
            template_svgs=template_svgs,
            available_images=available_images,
            previous_svgs=previous_svgs,
        )

    # 宽松模式（兼容旧逻辑）
    app_config = _config_module
    from openai import OpenAI

    client = OpenAI(api_key=app_config.OPENAI_API_KEY, base_url=app_config.OPENAI_BASE_URL)

    # 构建 system prompt（包含已生成SVG的上下文）
    system_prompt = build_executor_prompt(
        spec_lock_content, design_spec_content, theme,
        page_num, total, page_spec, topic, subject, template_svgs,
        available_images, previous_svgs,
    )

    # 构建 user prompt
    layout = page_spec.get("layout", "three_card")
    title = page_spec.get("title", "")
    content_desc = page_spec.get("content", "")

    user_msg = f"""请为《{topic}》的第{page_num}页「{title}」手写 SVG。

页面布局: {layout}
{f'内容要点: {content_desc}' if content_desc else ''}
{f'教材参考: {search_context[:800]}' if search_context else ''}

要求：
- 完整的 SVG 代码，<svg> 开头，</svg> 结尾
- 不要 markdown 代码块，不要解释
- 严格使用上方配色方案中的颜色
- 每个内容区块用 <g id="xxx"> 包裹"""

    # 尝试生成，失败则重试
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=app_config.OPENAI_MODEL,
                max_tokens=8000,
                temperature=0.4 if attempt > 0 else 0.5,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
            )
            raw = response.choices[0].message.content
            svg = clean_svg_output(raw)

            is_valid, error = validate_svg(svg)
            if is_valid:
                return svg
            else:
                logger.warning(f"SVG 验证失败 (尝试 {attempt+1}/3): {error}")
                if attempt == 2:
                    # 最后一次尝试，返回清理后的结果
                    logger.warning("使用验证失败的 SVG")
                    return svg
        except Exception as e:
            logger.warning(f"API 调用失败 (尝试 {attempt+1}/3): {e}")
            if attempt == 2:
                raise

    return svg


def read_spec_files(project_path: str) -> tuple:
    """读取 spec_lock.md 和 design_spec.md"""
    pp = Path(project_path)
    spec_lock = ""
    design_spec = ""

    lock_path = pp / "spec_lock.md"
    if lock_path.exists():
        spec_lock = lock_path.read_text(encoding="utf-8")

    spec_path = pp / "design_spec.md"
    if spec_path.exists():
        design_spec = spec_path.read_text(encoding="utf-8")

    return spec_lock, design_spec


def generate_image_queries(page_specs: list, topic: str, subject: str) -> list:
    """为每个页面生成图片搜索关键词"""
    app_config = _config_module
    from openai import OpenAI

    client = OpenAI(api_key=app_config.OPENAI_API_KEY, base_url=app_config.OPENAI_BASE_URL)

    # 收集需要图片的页面
    pages_needing_images = []
    for i, spec in enumerate(page_specs):
        layout = spec.get("layout", "")
        if layout in ("cover", "ending", "toc", "breathing"):
            continue
        pages_needing_images.append({"index": i, "title": spec.get("title", ""), "layout": layout})

    if not pages_needing_images:
        return []

    # 用 AI 生成搜索关键词
    pages_desc = "\n".join(f"- P{p['index']+1:02d}: {p['title']} ({p['layout']})" for p in pages_needing_images)

    try:
        response = client.chat.completions.create(
            model=app_config.OPENAI_MODEL,
            max_tokens=1500,
            temperature=0.5,
            messages=[
                {"role": "system", "content": """为教学课件页面生成图片搜索关键词。
输出JSON数组，每个元素格式：
{"page_index": 页码(从0开始), "filename": "描述性文件名.png", "query": "英文搜索关键词", "purpose": "用途说明"}

要求：
1. 每页1张图片
2. 搜索关键词用英文，简洁具体
3. 文件名用英文，有意义
4. 只输出JSON数组，不要其他文字"""},
                {"role": "user", "content": f"主题：{topic}\n学科：{subject}\n\n页面列表：\n{pages_desc}"},
            ],
        )
        raw = response.choices[0].message.content
        logger.debug(f"图片查询原始响应: {raw[:200]}...")

        # 解析 JSON - 更健壮的解析逻辑
        json_str = raw.strip()

        # 尝试提取 JSON 块
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0].strip()

        # 尝试找到 JSON 数组的开始和结束
        start_idx = json_str.find('[')
        end_idx = json_str.rfind(']')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = json_str[start_idx:end_idx + 1]

        import json
        queries = json.loads(json_str)

        # 验证并清理结果
        valid_queries = []
        for q in queries:
            if isinstance(q, dict) and 'query' in q and 'page_index' in q:
                # 确保 page_index 是整数
                q['page_index'] = int(q['page_index'])
                # 确保文件名存在
                if 'filename' not in q:
                    q['filename'] = f"page_{q['page_index'] + 1}.png"
                valid_queries.append(q)

        return valid_queries

    except json.JSONDecodeError as e:
        logger.warning(f"图片查询JSON解析失败: {e}")
        logger.debug(f"原始内容: {raw[:500]}")
        return []
    except Exception as e:
        logger.warning(f"生成图片查询失败: {e}")
        return []


def search_images_for_project(project_path: str, image_queries: list) -> list:
    """为项目搜索图片，返回成功下载的图片信息列表"""
    pp = Path(project_path)
    images_dir = pp / "images"
    images_dir.mkdir(exist_ok=True)

    results = []
    for query_info in image_queries:
        filename = query_info.get("filename", "image.png")
        search_query = query_info.get("query", "")
        page_index = query_info.get("page_index", 0)

        if not search_query:
            continue

        output_path = images_dir / filename
        if output_path.exists():
            # 图片已存在，跳过
            results.append({
                "filename": filename,
                "page_index": page_index,
                "status": "existing",
                "query": search_query,
            })
            continue

        logger.info(f"搜索图片: {search_query} -> {filename}")

        try:
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPTS_DIR / "image_search.py"),
                    search_query,
                    "--filename", filename,
                    "--orientation", "landscape",
                    "-o", str(images_dir),
                ],
                capture_output=True, text=True, timeout=30,
                cwd=str(PPT_MASTER_DIR),
            )

            if output_path.exists():
                results.append({
                    "filename": filename,
                    "page_index": page_index,
                    "status": "sourced",
                    "query": search_query,
                })
                logger.info(f"  图片下载成功: {filename}")
            else:
                logger.warning(f"  图片下载失败: {result.stderr[:200]}")
                results.append({
                    "filename": filename,
                    "page_index": page_index,
                    "status": "failed",
                    "query": search_query,
                })
        except subprocess.TimeoutExpired:
            logger.warning(f"  图片搜索超时: {search_query}")
            results.append({"filename": filename, "page_index": page_index, "status": "failed", "query": search_query})
        except Exception as e:
            logger.warning(f"  图片搜索异常: {e}")
            results.append({"filename": filename, "page_index": page_index, "status": "failed", "query": search_query})

    return results


def format_image_info_for_executor(image_results: list) -> str:
    """将图片搜索结果格式化为 Executor prompt 的一部分"""
    if not image_results:
        return ""

    lines = ["\n可用图片（在 SVG 中用 <image href=\"../images/文件名\" .../> 引用）："]
    for img in image_results:
        if img["status"] in ("sourced", "existing"):
            lines.append(f"  - {img['filename']}: {img['query']}（用于 P{img['page_index']+1:02d}）")
    return "\n".join(lines)


def read_template_svgs() -> dict:
    """读取模板 SVG 文件作为参考"""
    templates = {}
    template_files = {
        "cover": TEMPLATE_DIR / "01_cover.svg",
        "toc": TEMPLATE_DIR / "02_toc.svg",
        "content": TEMPLATE_DIR / "03_content.svg",
        "ending": TEMPLATE_DIR / "04_ending.svg",
    }
    for name, path in template_files.items():
        if path.exists():
            templates[name] = path.read_text(encoding="utf-8")
    return templates


# ─────────────────── 演讲备注生成 ───────────────────

def generate_speaker_notes(topic: str, page_specs: list, subject: str = "",
                           search_context: str = "") -> str:
    """用 AI 生成演讲备注"""
    app_config = _config_module
    from openai import OpenAI

    client = OpenAI(api_key=app_config.OPENAI_API_KEY, base_url=app_config.OPENAI_BASE_URL)

    page_list = "\n".join(
        f"第{i+1}页：{spec['title']} — {spec.get('content', '')}"
        for i, spec in enumerate(page_specs)
    )

    system_prompt = """你是一个教学课件演讲备注撰写者。为每一页PPT撰写简短的演讲备注。

要求：
1. 每页备注3-5句话
2. 语言自然、专业，适合课堂讲解
3. 包含关键知识点和讲解要点
4. 使用Markdown格式，每页一个##标题

输出格式：
## 第1页：标题
备注内容...

## 第2页：标题
备注内容..."""

    response = client.chat.completions.create(
        model=app_config.OPENAI_MODEL,
        max_tokens=3000,
        temperature=0.7,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"主题：{topic}\n学科：{subject}\n\n{f'教材参考内容：\n{search_context}\n\n' if search_context else ''}页面列表：\n{page_list}\n\n请撰写演讲备注。"},
        ],
    )

    return response.choices[0].message.content


# ─────────────────── 后处理流水线 ───────────────────

def run_post_processing(project_path: str) -> str:
    """运行后处理流水线，返回 PPTX 路径"""
    app_config = _config_module
    pp = Path(project_path)

    # 1. 拆分演讲备注（必须在 finalize 之前）
    logger.info("拆分演讲备注...")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "total_md_split.py"), str(pp)],
        capture_output=True, text=True, cwd=str(PPT_MASTER_DIR),
    )
    if result.returncode != 0:
        logger.warning(f"total_md_split 警告: {result.stderr[:200]}")

    # 2. 终结 SVG（图标嵌入、图片处理、文字扁平化、圆角转 path）
    # PPT_FORCE_FINALIZE 配置为 true 时，即使出错也继续
    force_finalize = getattr(app_config, 'PPT_FORCE_FINALIZE', True)
    logger.info("终结 SVG（finalize_svg）...")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "finalize_svg.py"), str(pp)],
        capture_output=True, text=True, cwd=str(PPT_MASTER_DIR),
    )
    logger.info(f"finalize_svg: {result.stdout[:300]}")
    if result.returncode != 0:
        if force_finalize:
            logger.warning(f"finalize_svg 警告（强制继续）: {result.stderr[:200]}")
        else:
            logger.warning(f"finalize_svg 警告: {result.stderr[:200]}")

    # 3. 转换 PPTX（带 fade 动画 + after-previous 级联）
    logger.info("转换 PPTX（带动画）...")
    result = subprocess.run(
        [
            sys.executable, str(SCRIPTS_DIR / "svg_to_pptx.py"), str(pp),
            "-s", "final",           # 使用 finalize 后的 svg_final
            "-t", "fade",            # 页面切换动画
            "-a", "auto",            # 元素入场动画（自动匹配）
            "--animation-trigger", "after-previous",  # 级联播放
        ],
        capture_output=True, text=True, cwd=str(PPT_MASTER_DIR),
    )
    if result.returncode != 0:
        # 如果 final 目录不存在，回退到 output
        logger.warning(f"svg_to_pptx (final) 失败，尝试 output: {result.stderr[:200]}")
        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS_DIR / "svg_to_pptx.py"), str(pp),
                "-s", "output",
                "-t", "fade",
                "-a", "auto",
                "--animation-trigger", "after-previous",
            ],
            capture_output=True, text=True, cwd=str(PPT_MASTER_DIR),
        )
    if result.returncode != 0:
        raise RuntimeError(f"PPTX 转换失败: {result.stderr[:500]}")
    logger.info(f"svg_to_pptx: {result.stdout[:300]}")

    # 查找 PPTX
    exports = list((pp / "exports").glob("*.pptx"))
    if not exports:
        raise RuntimeError("未找到生成的 PPTX 文件")

    return str(exports[0])


# ─────────────────── 主入口 ───────────────────

def generate_ppt_with_master(
    topic: str,
    subject: str = "",
    grade: str = "",
    outline_markdown: str = "",
    search_context: str = "",
    page_count: int = None,
) -> tuple:
    """
    使用 ppt-master 流水线生成 PPT

    参数:
        topic: 主题
        subject: 学科
        grade: 年级
        outline_markdown: 用户确认的大纲（可选）
        search_context: 搜索上下文（可选）
        page_count: 用户指定的页数（可选，不指定则由AI自动决定）

    返回:
        (pptx_path, title)
    """
    logger.info(f"=== PPT Master 流水线启动 ===")
    logger.info(f"主题: {topic}, 学科: {subject}, 年级: {grade}, 页数: {page_count or '自动'}")

    # 1. 选择配色（优先使用学科专属配色）
    if subject:
        theme = get_subject_theme(subject)
        logger.info(f"使用学科专属配色: {subject} -> {theme['primary']}")
    else:
        theme = pick_theme(subject, topic)
        logger.info(f"使用通用配色: {theme['primary']}")

    # 1.5 搜索教材内容（如果没有传入搜索结果）
    if not search_context:
        try:
            import asyncio
            from agent.web_search import search_textbook_content
            logger.info("搜索教材内容...")
            search_context = asyncio.run(search_textbook_content(topic, subject, grade))
            logger.info(f"搜索完成，获取到 {len(search_context)} 字符的教材内容")
        except Exception as e:
            logger.warning(f"搜索教材内容失败: {e}")
            search_context = ""

    # 2. AI 规划页面（传入页数提示）
    logger.info("AI 规划页面...")
    page_specs = plan_pages_with_ai(topic, subject, grade, outline_markdown, search_context, page_count)
    actual_page_count = len(page_specs)
    logger.info(f"规划了 {actual_page_count} 页")

    # 3. 创建项目
    project_name = f"{subject}_{topic}" if subject else topic
    project_path = create_project(project_name)
    logger.info(f"项目路径: {project_path}")

    # 4. 生成设计规范
    generate_design_spec(project_path, topic, page_specs, theme, subject, grade)
    generate_spec_lock(project_path, topic, page_specs, theme)
    logger.info("设计规范已生成")

    # 5. 搜索图片
    import shutil
    logger.info("搜索教学配图...")
    image_queries = generate_image_queries(page_specs, topic, subject)
    image_results = []
    if image_queries:
        image_results = search_images_for_project(project_path, image_queries)
        sourced = sum(1 for r in image_results if r["status"] in ("sourced", "existing"))
        logger.info(f"图片搜索完成: {sourced}/{len(image_results)} 张可用")
    image_info = format_image_info_for_executor(image_results)

    # 6. 读取 spec 文件和模板 SVG（供 Executor 使用）
    spec_lock_content, design_spec_content = read_spec_files(project_path)
    template_svgs = read_template_svgs()

    # 7. 清理旧 SVG 并逐页生成（保持上下文）
    svg_dir = Path(project_path) / "svg_output"
    if svg_dir.exists():
        try:
            for f in svg_dir.iterdir():
                if f.is_file():
                    f.unlink()
        except Exception:
            pass
        try:
            shutil.rmtree(str(svg_dir))
        except Exception:
            pass
    svg_dir.mkdir(parents=True, exist_ok=True)

    # 逐页生成SVG，保持上下文（已生成的SVG会传递给下一页）
    generated_svgs = []
    # 确保 page_count 不为 None
    if page_count is None:
        page_count = actual_page_count
    for i, spec in enumerate(page_specs):
        page_num = i + 1
        safe_title = spec['title'][:20].replace(' ', '_').replace('/', '_')
        filename = f"{page_num:02d}_{safe_title}.svg"
        logger.info(f"Executor 生成第 {page_num}/{page_count} 页: {spec['title']} ({spec['layout']})")

        # 找到当前页面的图片
        page_images = [r for r in image_results if r.get("page_index") == i and r["status"] in ("sourced", "existing")]

        svg_content = generate_svg_with_executor(
            page_spec=spec,
            page_num=page_num,
            total=page_count,
            spec_lock_content=spec_lock_content,
            design_spec_content=design_spec_content,
            theme=theme,
            topic=topic,
            subject=subject,
            search_context=search_context,
            template_svgs=template_svgs,
            available_images=page_images,
            previous_svgs=generated_svgs,  # 传递已生成的SVG，保持上下文
            strict_mode=True,  # 使用严格质量校验，对齐原生 IDE 环境
        )
        (svg_dir / filename).write_text(svg_content, encoding='utf-8')
        generated_svgs.append({'page_num': page_num, 'title': spec['title'], 'svg': svg_content})

    logger.info(f"SVG 生成完成: {page_count} 页")

    # 7. 生成演讲备注
    logger.info("生成演讲备注...")
    notes = generate_speaker_notes(topic, page_specs, subject, search_context)
    notes_dir = Path(project_path) / "notes"
    notes_dir.mkdir(exist_ok=True)
    (notes_dir / "total.md").write_text(notes, encoding='utf-8')

    # 8. 后处理（finalize_svg + svg_to_pptx 带动画）
    logger.info("运行后处理流水线...")
    pptx_path = run_post_processing(project_path)
    logger.info(f"=== PPT 生成完成: {pptx_path} ===")

    return pptx_path, topic


# ─────────────────── 便捷函数 ───────────────────

def generate_education_ppt_with_master(
    topic: str, subject: str = "", grade: str = "",
    difficulty: str = "中等", content_type: str = "课件",
) -> tuple:
    """兼容旧接口"""
    return generate_ppt_with_master(topic, subject, grade)


def generate_lesson_with_master(topic: str, subject: str, grade: str,
                                difficulty: str = "中等") -> tuple:
    return generate_ppt_with_master(topic, subject, grade)


def generate_courseware_with_master(topic: str, subject: str, grade: str,
                                    difficulty: str = "中等") -> tuple:
    return generate_ppt_with_master(topic, subject, grade)


def generate_speech_with_master(topic: str, subject: str, grade: str,
                                difficulty: str = "中等") -> tuple:
    return generate_ppt_with_master(topic, subject, grade)


def generate_reflection_with_master(topic: str, subject: str, grade: str,
                                    difficulty: str = "中等") -> tuple:
    return generate_ppt_with_master(topic, subject, grade)


if __name__ == "__main__":
    path, title = generate_ppt_with_master(
        topic="从百草园到三味书屋",
        subject="语文",
        grade="初中",
    )
    print(f"生成完成: {path}")
    print(f"标题: {title}")


# ─────────────────── 模板驱动渲染 ───────────────────

# 模板目录
TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "education"


def _get_template_placeholders(theme: dict, topic: str, subject: str) -> dict:
    """从 theme dict 提取模板占位符映射"""
    return {
        "BG_COLOR": theme["bg"],
        "PRIMARY": theme["primary"],
        "ACCENT": theme.get("accent", "#CC0000"),
        "HEADER_BG": theme.get("header_bg", theme["primary"]),
        "TEXT_COLOR": theme.get("text", "#1A1A1A"),
        "TEXT_SECONDARY": theme.get("text_secondary", "#555555"),
        "TEXT_LIGHT": theme.get("text_light", "#999999"),
        "TITLE_FONT": theme.get("title_font", "Microsoft YaHei, SimHei, Arial, sans-serif"),
        "BODY_FONT": theme.get("body_font", "Microsoft YaHei, PingFang SC, Arial, sans-serif"),
        "LOGO": subject or "教学课件",
    }


def _fill_template_svg(template_path: str, replacements: dict) -> str:
    """读取模板 SVG，替换所有 {{...}} 占位符"""
    svg = Path(template_path).read_text(encoding="utf-8")
    for key, value in replacements.items():
        svg = svg.replace("{{" + key + "}}", str(value))
    return svg


def _escape_svg_text(text: str) -> str:
    """转义 SVG 文本中的特殊字符"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _render_content_three_card(cards: list, theme: dict) -> str:
    """渲染三栏卡片布局的 SVG 内容片段"""
    primary = theme["primary"]
    accent = theme.get("accent", "#CC0000")
    card_bg = theme.get("card_bg", "#FFFFFF")
    card_border = theme.get("card_border", "#E0E0E0")
    text_color = theme.get("text", "#1A1A1A")
    text_secondary = theme.get("text_secondary", "#555555")
    title_font = theme.get("title_font", "Microsoft YaHei, SimHei, Arial, sans-serif")
    body_font = theme.get("body_font", "Microsoft YaHei, PingFang SC, Arial, sans-serif")

    card_w = 370
    gap = 25
    start_x = (1280 - 3 * card_w - 2 * gap) // 2
    svg = ""

    for i, card in enumerate(cards[:3]):
        x = start_x + i * (card_w + gap)
        title = _escape_svg_text(card.get("title", f"要点{i+1}"))
        lines = card.get("lines", [])

        # 卡片背景
        svg += f'\n  <g id="card-{i+1}">'
        svg += f'\n    <rect x="{x}" y="95" width="{card_w}" height="540" rx="12" fill="{card_bg}" stroke="{card_border}" stroke-width="1"/>'
        # 卡片头部
        svg += f'\n    <rect x="{x}" y="95" width="{card_w}" height="55" rx="12" fill="{primary}" fill-opacity="0.1"/>'
        svg += f'\n    <rect x="{x}" y="130" width="{card_w}" height="20" fill="{primary}" fill-opacity="0.1"/>'
        # 编号圆
        svg += f'\n    <circle cx="{x + card_w//2}" cy="122" r="20" fill="{primary}" fill-opacity="0.15"/>'
        svg += f'\n    <text x="{x + card_w//2}" y="130" text-anchor="middle" fill="{primary}" font-family="{title_font}" font-size="18" font-weight="bold">{i+1}</text>'
        # 标题
        svg += f'\n    <text x="{x + card_w//2}" y="180" text-anchor="middle" fill="{text_color}" font-family="{title_font}" font-size="20" font-weight="bold">{title}</text>'
        # 分割线
        svg += f'\n    <line x1="{x + card_w//2 - 50}" y1="195" x2="{x + card_w//2 + 50}" y2="195" stroke="{accent}" stroke-width="2" stroke-opacity="0.4"/>'

        # 内容行
        y = 225
        for line in lines[:8]:
            escaped = _escape_svg_text(line)
            svg += f'\n    <text x="{x + 25}" y="{y}" fill="{text_secondary}" font-family="{body_font}" font-size="15">{escaped}</text>'
            y += 28

        svg += f'\n  </g>'

    return svg


def _render_content_two_column(columns: dict, theme: dict) -> str:
    """渲染双栏对比布局的 SVG 内容片段"""
    primary = theme["primary"]
    accent = theme.get("accent", "#CC0000")
    card_bg = theme.get("card_bg", "#FFFFFF")
    card_border = theme.get("card_border", "#E0E0E0")
    text_color = theme.get("text", "#1A1A1A")
    text_secondary = theme.get("text_secondary", "#555555")
    title_font = theme.get("title_font", "Microsoft YaHei, SimHei, Arial, sans-serif")
    body_font = theme.get("body_font", "Microsoft YaHei, PingFang SC, Arial, sans-serif")

    left = columns.get("left", {"title": "", "lines": []})
    right = columns.get("right", {"title": "", "lines": []})

    svg = ""
    # 左栏
    svg += f'\n  <g id="column-left">'
    svg += f'\n    <rect x="40" y="95" width="580" height="540" rx="10" fill="{card_bg}" stroke="{card_border}" stroke-width="1"/>'
    svg += f'\n    <rect x="40" y="95" width="580" height="45" rx="10" fill="{primary}" fill-opacity="0.1"/>'
    svg += f'\n    <rect x="40" y="120" width="580" height="20" fill="{primary}" fill-opacity="0.1"/>'
    svg += f'\n    <text x="330" y="128" text-anchor="middle" fill="{primary}" font-family="{title_font}" font-size="20" font-weight="bold">{_escape_svg_text(left.get("title", ""))}</text>'

    y = 170
    for line in left.get("lines", [])[:10]:
        svg += f'\n    <text x="65" y="{y}" fill="{text_secondary}" font-family="{body_font}" font-size="15">{_escape_svg_text(line)}</text>'
        y += 28
    svg += f'\n  </g>'

    # 右栏
    svg += f'\n  <g id="column-right">'
    svg += f'\n    <rect x="660" y="95" width="580" height="540" rx="10" fill="{card_bg}" stroke="{card_border}" stroke-width="1"/>'
    svg += f'\n    <rect x="660" y="95" width="580" height="45" rx="10" fill="{accent}" fill-opacity="0.1"/>'
    svg += f'\n    <rect x="660" y="120" width="580" height="20" fill="{accent}" fill-opacity="0.1"/>'
    svg += f'\n    <text x="950" y="128" text-anchor="middle" fill="{accent}" font-family="{title_font}" font-size="20" font-weight="bold">{_escape_svg_text(right.get("title", ""))}</text>'

    y = 170
    for line in right.get("lines", [])[:10]:
        svg += f'\n    <text x="685" y="{y}" fill="{text_secondary}" font-family="{body_font}" font-size="15">{_escape_svg_text(line)}</text>'
        y += 28
    svg += f'\n  </g>'

    return svg


def _render_content_list(items: list, theme: dict) -> str:
    """渲染列表布局的 SVG 内容片段"""
    primary = theme["primary"]
    accent = theme.get("accent", "#CC0000")
    text_color = theme.get("text", "#1A1A1A")
    text_secondary = theme.get("text_secondary", "#555555")
    body_font = theme.get("body_font", "Microsoft YaHei, PingFang SC, Arial, sans-serif")

    svg = ""
    y = 110
    for i, item in enumerate(items[:10]):
        escaped = _escape_svg_text(item)
        # 编号圆
        svg += f'\n  <g id="item-{i+1}">'
        svg += f'\n    <circle cx="70" cy="{y + 8}" r="14" fill="{primary}" fill-opacity="0.12"/>'
        svg += f'\n    <text x="70" y="{y + 13}" text-anchor="middle" fill="{primary}" font-family="{body_font}" font-size="14" font-weight="bold">{i+1}</text>'
        svg += f'\n    <text x="100" y="{y + 13}" fill="{text_color}" font-family="{body_font}" font-size="17">{escaped}</text>'
        svg += f'\n  </g>'
        y += 50

    return svg


def _render_content_quote(quote_lines: list, analysis_lines: list, theme: dict) -> str:
    """渲染引文赏析布局的 SVG 内容片段"""
    primary = theme["primary"]
    accent = theme.get("accent", "#CC0000")
    text_color = theme.get("text", "#1A1A1A")
    text_secondary = theme.get("text_secondary", "#555555")
    title_font = theme.get("title_font", "Microsoft YaHei, SimHei, Arial, sans-serif")
    body_font = theme.get("body_font", "Microsoft YaHei, PingFang SC, Arial, sans-serif")
    card_bg = theme.get("card_bg", "#FFFFFF")

    svg = ""
    # 引文区域
    svg += f'\n  <g id="quote-block">'
    svg += f'\n    <rect x="80" y="95" width="1120" height="200" rx="10" fill="{primary}" fill-opacity="0.04"/>'
    svg += f'\n    <rect x="80" y="95" width="5" height="200" rx="2" fill="{accent}"/>'

    y = 135
    for line in quote_lines[:6]:
        svg += f'\n    <text x="120" y="{y}" fill="{primary}" font-family="{title_font}" font-size="22" font-style="italic">{_escape_svg_text(line)}</text>'
        y += 35
    svg += f'\n  </g>'

    # 赏析区域
    svg += f'\n  <g id="analysis-block">'
    y = 330
    for line in analysis_lines[:8]:
        escaped = _escape_svg_text(line)
        svg += f'\n    <text x="100" y="{y}" fill="{text_secondary}" font-family="{body_font}" font-size="16">{escaped}</text>'
        y += 40
    svg += f'\n  </g>'

    return svg


def _render_content_data_table(table_data: dict, theme: dict) -> str:
    """渲染数据表格布局的 SVG 内容片段"""
    primary = theme["primary"]
    accent = theme.get("accent", "#CC0000")
    card_bg = theme.get("card_bg", "#FFFFFF")
    card_border = theme.get("card_border", "#E0E0E0")
    text_color = theme.get("text", "#1A1A1A")
    text_secondary = theme.get("text_secondary", "#555555")
    body_font = theme.get("body_font", "Microsoft YaHei, PingFang SC, Arial, sans-serif")

    headers = table_data.get("headers", [])
    rows = table_data.get("rows", [])

    if not headers:
        return _render_content_list(table_data.get("items", ["暂无数据"]), theme)

    col_count = len(headers)
    table_w = 1120
    col_w = table_w // col_count
    start_x = 80

    svg = ""
    # 表头
    svg += f'\n  <g id="table-header">'
    svg += f'\n    <rect x="{start_x}" y="95" width="{table_w}" height="45" rx="8" fill="{primary}"/>'
    for j, h in enumerate(headers):
        x = start_x + j * col_w + col_w // 2
        svg += f'\n    <text x="{x}" y="125" text-anchor="middle" fill="#FFFFFF" font-family="{body_font}" font-size="16" font-weight="bold">{_escape_svg_text(str(h))}</text>'
    svg += f'\n  </g>'

    # 数据行
    for i, row in enumerate(rows[:10]):
        y = 145 + i * 45
        bg = card_bg if i % 2 == 0 else f'{primary}" fill-opacity="0.04'
        svg += f'\n  <g id="table-row-{i}">'
        svg += f'\n    <rect x="{start_x}" y="{y}" width="{table_w}" height="42" fill="{bg}"/>'
        for j, cell in enumerate(row):
            x = start_x + j * col_w + col_w // 2
            svg += f'\n    <text x="{x}" y="{y + 28}" text-anchor="middle" fill="{text_secondary}" font-family="{body_font}" font-size="14">{_escape_svg_text(str(cell))}</text>'
        svg += f'\n  </g>'

    # 说明
    if table_data.get("note"):
        svg += f'\n  <text x="{start_x}" y="{155 + len(rows[:10]) * 45 + 20}" fill="{text_secondary}" font-family="{body_font}" font-size="13">{_escape_svg_text(table_data["note"])}</text>'

    return svg


def _render_content_area(page_spec: dict, theme: dict, topic: str, subject: str, search_context: str = "") -> str:
    """根据布局类型生成 {{CONTENT_AREA}} 的 SVG 内容片段"""
    app_config = _config_module
    from openai import OpenAI

    layout = page_spec.get("layout", "three_card")
    title = page_spec.get("title", "")

    # 封面、目录、结束页不走这个函数
    if layout in ("cover", "toc", "ending"):
        return ""

    # 呼吸页/过渡页
    if layout == "breathing":
        return _render_content_breathing(title, theme)

    # 引文页
    if layout == "quote":
        return _render_content_quote_page(title, theme, topic, subject, search_context)

    # 其他布局：调用 AI 生成内容，然后渲染
    client = OpenAI(api_key=app_config.OPENAI_API_KEY, base_url=app_config.OPENAI_BASE_URL)

    layout_prompt = {
        "three_card": "输出3个卡片，每卡5-8行。格式：\n【一】卡片标题\n- 要点1\n- 要点2\n...",
        "comparison_two_column": "输出左右两栏对比。格式：\n【左栏标题】\n- 要点\n...\n【右栏标题】\n- 要点\n...",
        "text_analysis": "输出文本分析。格式：\n原文：xxx\n赏析：xxx\n...",
        "data_table": "输出表格数据。格式：\n表头1 | 表头2 | 表头3\n数据1 | 数据2 | 数据3\n...",
        "timeline": "输出时间轴。格式：\n年份 | 事件\n...",
        "formula_step": "输出公式/步骤。格式：\n步骤1：xxx\n步骤2：xxx\n...",
        "exercise_steps": "输出例题。格式：\n题目：xxx\n解：步骤1\n步骤2\n...",
        "structure_diagram": "输出结构图。格式：\n中心：概念\n分支1：说明\n...",
        "experiment_flow": "输出实验步骤。格式：\n步骤1\n步骤2\n...",
    }

    prompt = layout_prompt.get(layout, "输出相关内容，每行一条要点，共6-8条")

    system_prompt = f"""你是一个{subject or '语文'}教师，为《{topic}》准备课件内容。
当前页面：{title}
{f'教材参考：{search_context[:500]}' if search_context else ''}

{prompt}

要求：内容具体、有教学深度、每行不超过25字。直接输出内容，不要解释。"""

    try:
        response = client.chat.completions.create(
            model=app_config.OPENAI_MODEL,
            max_tokens=2000,
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"为《{topic}》的「{title}」页面生成教学内容"},
            ],
        )
        raw_text = response.choices[0].message.content
    except Exception as e:
        logger.warning(f"AI 内容生成失败: {e}")
        raw_text = ""

    # 解析 AI 输出并渲染为 SVG
    return _parse_and_render_content(raw_text, layout, theme)


def _parse_and_render_content(raw_text: str, layout: str, theme: dict) -> str:
    """解析 AI 文本输出并渲染为 SVG 内容片段"""
    if not raw_text:
        return _render_content_list(["暂无内容"], theme)

    lines = [l.strip() for l in raw_text.strip().split("\n") if l.strip()]

    if layout in ("three_card",):
        # 解析卡片格式
        cards = []
        current = None
        for line in lines:
            m = re.match(r"[【\[]?([一二三四\d])[】\].、]\s*(.*)", line)
            if m:
                if current:
                    cards.append(current)
                current = {"title": m.group(2).strip(), "lines": []}
            elif current and line.startswith(("-", "·", "•", "*")):
                current["lines"].append(line.lstrip("-·•* "))
            elif current and len(line) > 2:
                current["lines"].append(line)
        if current:
            cards.append(current)
        if cards:
            return _render_content_three_card(cards, theme)

    if layout in ("comparison_two_column",):
        # 解析双栏格式
        left = {"title": "", "lines": []}
        right = {"title": "", "lines": []}
        target = left
        for line in lines:
            m = re.match(r"[【\[](.+?)[】\]]", line)
            if m:
                if left["title"]:
                    right["title"] = m.group(1)
                    target = right
                else:
                    left["title"] = m.group(1)
                    target = left
            elif line.startswith(("-", "·", "•", "*")):
                target["lines"].append(line.lstrip("-·•* "))
            elif len(line) > 2:
                target["lines"].append(line)
        return _render_content_two_column({"left": left, "right": right}, theme)

    if layout in ("data_table",):
        # 解析表格格式
        headers = []
        rows = []
        for line in lines:
            if "|" in line or "｜" in line:
                parts = re.split(r"[|｜]", line)
                parts = [p.strip() for p in parts if p.strip()]
                if not headers:
                    headers = parts
                else:
                    rows.append(parts)
        if headers:
            return _render_content_data_table({"headers": headers, "rows": rows}, theme)

    if layout in ("quote",):
        # 解析引文格式
        quote_lines = []
        analysis_lines = []
        is_quote = True
        for line in lines:
            if "赏析" in line or "分析" in line:
                is_quote = False
            if is_quote and not line.startswith(("-", "·")):
                quote_lines.append(line)
            else:
                analysis_lines.append(line.lstrip("-·•* "))
        return _render_content_quote(quote_lines, analysis_lines, theme)

    # 默认列表布局
    items = []
    for line in lines:
        cleaned = line.lstrip("-·•* 0123456789.、")
        if cleaned and len(cleaned) > 1:
            items.append(cleaned)
    return _render_content_list(items[:10], theme)


def _render_content_breathing(title: str, theme: dict) -> str:
    """渲染呼吸/过渡页的 SVG 内容片段"""
    primary = theme["primary"]
    accent = theme.get("accent", "#CC0000")
    title_font = theme.get("title_font", "Microsoft YaHei, SimHei, Arial, sans-serif")
    body_font = theme.get("body_font", "Microsoft YaHei, PingFang SC, Arial, sans-serif")
    text_secondary = theme.get("text_secondary", "#555555")

    return f'''
  <g id="breathing">
    <circle cx="640" cy="320" r="180" fill="{primary}" fill-opacity="0.05"/>
    <circle cx="640" cy="320" r="120" fill="{accent}" fill-opacity="0.05"/>
    <circle cx="640" cy="320" r="60" fill="{primary}" fill-opacity="0.08"/>
    <text x="640" y="330" text-anchor="middle" fill="{primary}" font-family="{title_font}" font-size="36" font-weight="bold">{_escape_svg_text(title)}</text>
    <text x="640" y="380" text-anchor="middle" fill="{text_secondary}" font-family="{body_font}" font-size="18">— 思考与回顾 —</text>
  </g>'''


def _render_content_quote_page(title: str, theme: dict, topic: str, subject: str, search_context: str = "") -> str:
    """渲染引文/名句赏析页的 SVG 内容片段"""
    app_config = _config_module
    from openai import OpenAI

    client = OpenAI(api_key=app_config.OPENAI_API_KEY, base_url=app_config.OPENAI_BASE_URL)

    try:
        response = client.chat.completions.create(
            model=app_config.OPENAI_MODEL,
            max_tokens=1000,
            temperature=0.7,
            messages=[
                {"role": "system", "content": f"为《{topic}》({subject})找一段经典名句或引文，输出格式：\n引文内容（2-4行）\n赏析1：xxx\n赏析2：xxx"},
                {"role": "user", "content": f"为「{title}」页面提供引文和赏析"},
            ],
        )
        raw = response.choices[0].message.content
    except Exception:
        raw = ""

    quote_lines = []
    analysis_lines = []
    is_quote = True
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        if "赏析" in line or "分析" in line:
            is_quote = False
        if is_quote:
            quote_lines.append(line)
        else:
            analysis_lines.append(line.lstrip("-·•* "))

    if not quote_lines:
        quote_lines = [f"——《{topic}》经典名句"]

    return _render_content_quote(quote_lines, analysis_lines, theme)


def generate_page_from_template(page_spec: dict, topic: str, subject: str,
                                 theme: dict, page_num: int, total: int,
                                 search_context: str = "") -> str:
    """用模板生成单页 SVG"""
    # 确保参数不为 None
    if page_num is None:
        page_num = 1
    if total is None:
        total = 1

    layout = page_spec.get("layout", "three_card")
    title = page_spec.get("title", "")
    placeholders = _get_template_placeholders(theme, topic, subject)

    # 通用占位符
    placeholders["PAGE_TITLE"] = _escape_svg_text(title)
    placeholders["PAGE_NUM"] = f"{page_num:02d}"
    placeholders["TOTAL"] = f"{total:02d}"
    placeholders["SECTION_NAME"] = subject or ""
    placeholders["DATE"] = datetime.now().strftime("%Y年%m月%d日")

    if layout == "cover":
        placeholders["TITLE"] = _escape_svg_text(topic)
        placeholders["SUBTITLE"] = f"{subject} · 教学课件" if subject else "教学课件"
        placeholders["INFO"] = f"{grade}" if (grade := page_spec.get("grade", "")) else subject or ""
        template = TEMPLATE_DIR / "01_cover.svg"

    elif layout == "toc":
        # 获取目录项
        skeleton = get_skeleton(subject, topic)
        toc_pages = skeleton.get("pages", [])[:8]
        for i in range(8):
            key = f"TOC_ITEM_{i+1}"
            if i < len(toc_pages):
                placeholders[f"{key}_TITLE"] = _escape_svg_text(toc_pages[i]["title"])
                placeholders[f"{key}_DESC"] = _escape_svg_text(toc_pages[i].get("desc", ""))
            else:
                placeholders[f"{key}_TITLE"] = ""
                placeholders[f"{key}_DESC"] = ""
        template = TEMPLATE_DIR / "02_toc.svg"

    elif layout == "ending":
        placeholders["THANK_YOU"] = "谢谢观看"
        placeholders["SUBTITLE"] = f"{subject} · {topic}" if subject else topic
        placeholders["CONTACT_INFO"] = f"{subject}教学课件" if subject else "教学课件"
        placeholders["EXTRA_INFO"] = "欢迎交流讨论"
        template = TEMPLATE_DIR / "04_ending.svg"

    else:
        # 内容页
        content_svg = _render_content_area(page_spec, theme, topic, subject, search_context)
        placeholders["CONTENT_AREA"] = content_svg
        template = TEMPLATE_DIR / "03_content.svg"

    return _fill_template_svg(str(template), placeholders)
