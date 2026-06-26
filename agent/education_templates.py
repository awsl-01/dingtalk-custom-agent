"""
教育行业多场景PPT模板矩阵
为不同学科、不同教学环节的老师提供专业模板
"""

# 模板矩阵配置
EDUCATION_TEMPLATES = {
    "1": {
        "id": "ink_painting",
        "name": "国风水墨",
        "style": "水墨丹青风格",
        "colors": {
            "primary": "#2C3E50",  # 墨色
            "secondary": "#8B4513",  # 赭石色
            "accent": "#C0392B",  # 朱砂红
            "background": "#F5F5DC"  # 米白色
        },
        "elements": ["卷轴", "印章", "毛笔", "水墨山水", "古典边框"],
        "subjects": ["语文", "历史", "政治"],
        "scenes": ["古诗文教学", "文言文讲解", "传统文化", "诗词鉴赏"],
        "stages": ["小学高年级", "初中", "高中", "大学"],
        "atmosphere": "古典雅致、文化底蕴浓厚",
        "design_suggestions": {
            "导入页": "水墨山水背景+卷轴展开动画",
            "知识点页": "竖排文字+印章点缀+留白设计",
            "练习页": "宣纸质感背景+毛笔字体",
            "互动页": "诗词填空+水墨插图",
            "总结页": "卷轴收起效果+古典边框"
        },
        "description": "适合语文古诗文教学、传统文化课程，营造古典雅致的学习氛围"
    },
    "2": {
        "id": "macaron_cartoon",
        "name": "马卡龙卡通",
        "style": "甜美卡通风格",
        "colors": {
            "primary": "#FF6B9D",  # 粉色
            "secondary": "#C9B1FF",  # 薰衣草紫
            "accent": "#FFD93D",  # 柠檬黄
            "background": "#FFF5F5"  # 浅粉色
        },
        "elements": ["卡通人物", "彩色气泡", "星星", "爱心", "彩虹"],
        "subjects": ["英语", "音乐", "美术", "小学语文", "小学数学"],
        "scenes": ["趣味教学", "启蒙教育", "互动课堂", "主题活动"],
        "stages": ["小学", "幼儿园"],
        "atmosphere": "活泼童趣、色彩缤纷",
        "design_suggestions": {
            "导入页": "卡通人物欢迎+彩色气泡飘动",
            "知识点页": "图文混排+卡通图标+圆角卡片",
            "练习页": "趣味题目+奖励贴纸",
            "互动页": "游戏化设计+进度条",
            "总结页": "星星评价+鼓励语"
        },
        "description": "适合小学低年级、幼儿园教学，营造轻松愉快的学习氛围"
    },
    "3": {
        "id": "hand_drawn",
        "name": "手绘插画",
        "style": "手绘涂鸦风格",
        "colors": {
            "primary": "#4A90E2",  # 天蓝色
            "secondary": "#7ED321",  # 草绿色
            "accent": "#F5A623",  # 橙色
            "background": "#FFFEF7"  # 米白色
        },
        "elements": ["手绘线条", "涂鸦图案", "便签纸", "图钉", "手写字体"],
        "subjects": ["美术", "综合实践", "班会", "德育"],
        "scenes": ["创意课程", "手工制作", "思维导图", "头脑风暴"],
        "stages": ["小学", "初中", "高中"],
        "atmosphere": "自由创意、亲切自然",
        "design_suggestions": {
            "导入页": "手绘标题+涂鸦背景",
            "知识点页": "便签纸布局+手绘图标",
            "练习页": "涂鸦式题目+手绘边框",
            "互动页": "思维导图+协作白板",
            "总结页": "手绘总结图+签名区"
        },
        "description": "适合美术、创意课程，营造自由创作的学习氛围"
    },
    "4": {
        "id": "fresh_forest",
        "name": "清新森系",
        "style": "自然清新风格",
        "colors": {
            "primary": "#2ECC71",  # 森林绿
            "secondary": "#87D37C",  # 浅绿色
            "accent": "#F39C12",  # 阳光橙
            "background": "#F8F9FA"  # 浅灰色
        },
        "elements": ["绿叶", "花朵", "阳光", "水滴", "木质纹理"],
        "subjects": ["生物", "地理", "科学", "环保教育"],
        "scenes": ["自然科学", "生态保护", "户外教学", "生命教育"],
        "stages": ["小学", "初中", "高中"],
        "atmosphere": "清新自然、生机勃勃",
        "design_suggestions": {
            "导入页": "绿叶背景+阳光光效",
            "知识点页": "卡片式布局+植物图标",
            "练习页": "自然主题题目+清新配色",
            "互动页": "生态拼图+知识树",
            "总结页": "成长树设计+收获展示"
        },
        "description": "适合生物、地理、科学课程，营造清新自然的学习氛围"
    },
    "5": {
        "id": "vintage_newspaper",
        "name": "复古报刊",
        "style": "复古报纸风格",
        "colors": {
            "primary": "#8B4513",  # 深棕色
            "secondary": "#D2691E",  # 巧克力色
            "accent": "#B22222",  # 深红色
            "background": "#FFF8DC"  # 玉米丝色
        },
        "elements": ["报纸纹理", "复古边框", "铅字体", "老照片", "印章"],
        "subjects": ["历史", "政治", "语文", "新闻写作"],
        "scenes": ["历史事件", "时事分析", "写作教学", "新闻素养"],
        "stages": ["初中", "高中", "大学"],
        "atmosphere": "复古怀旧、历史感强",
        "design_suggestions": {
            "导入页": "报纸头版设计+日期标题",
            "知识点页": "分栏布局+铅字体+复古配图",
            "练习页": "填字游戏+历史问答",
            "互动页": "时间线设计+事件排序",
            "总结页": "报纸总结+历史回顾"
        },
        "description": "适合历史、政治、新闻课程，营造复古怀旧的学习氛围"
    },
    "6": {
        "id": "guochao_illustration",
        "name": "国潮插画",
        "style": "国潮艺术风格",
        "colors": {
            "primary": "#E74C3C",  # 中国红
            "secondary": "#F1C40F",  # 明黄色
            "accent": "#1A5276",  # 深蓝色
            "background": "#FDFEFE"  # 白色
        },
        "elements": ["国潮插画", "祥云", "仙鹤", "牡丹", "传统纹样"],
        "subjects": ["语文", "历史", "政治", "传统文化"],
        "scenes": ["传统文化", "节日教学", "文化自信", "民族精神"],
        "stages": ["小学", "初中", "高中", "大学"],
        "atmosphere": "时尚国潮、文化自信",
        "design_suggestions": {
            "导入页": "国潮插画背景+动态祥云",
            "知识点页": "图文并茂+传统纹样边框",
            "练习页": "文化知识问答+国潮图标",
            "互动页": "文化拼图+传统元素配对",
            "总结页": "文化传承+现代演绎"
        },
        "description": "适合传统文化、节日教学，营造时尚国潮的学习氛围"
    },
    "7": {
        "id": "minimalist_ins",
        "name": "极简ins风",
        "style": "极简现代风格",
        "colors": {
            "primary": "#2C3E50",  # 深灰色
            "secondary": "#ECF0F1",  # 浅灰色
            "accent": "#E74C3C",  # 红色点缀
            "background": "#FFFFFF"  # 纯白色
        },
        "elements": ["极简线条", "几何图形", "留白设计", "高级灰", "细字体"],
        "subjects": ["数学", "物理", "化学", "信息技术"],
        "scenes": ["公式推导", "理论讲解", "技术培训", "学术汇报"],
        "stages": ["初中", "高中", "大学"],
        "atmosphere": "专业严谨、现代简约",
        "design_suggestions": {
            "导入页": "极简标题+留白设计",
            "知识点页": "大留白+重点突出+几何装饰",
            "练习页": "公式展示+图表分析",
            "互动页": "数据可视化+流程图",
            "总结页": "要点提炼+极简总结"
        },
        "description": "适合数学、理科、技术课程，营造专业严谨的学习氛围"
    },
    "8": {
        "id": "watercolor",
        "name": "水彩晕染",
        "style": "水彩艺术风格",
        "colors": {
            "primary": "#3498DB",  # 天蓝色
            "secondary": "#E91E63",  # 粉色
            "accent": "#FF9800",  # 橙色
            "background": "#FFFDE7"  # 浅黄色
        },
        "elements": ["水彩晕染", "手绘插画", "柔和渐变", "艺术字体", "水彩斑点"],
        "subjects": ["美术", "音乐", "语文", "英语"],
        "scenes": ["艺术鉴赏", "文学赏析", "创意写作", "情感教育"],
        "stages": ["小学", "初中", "高中"],
        "atmosphere": "艺术浪漫、温馨治愈",
        "design_suggestions": {
            "导入页": "水彩背景+艺术标题",
            "知识点页": "水彩卡片+手绘插图",
            "练习页": "创意题目+艺术边框",
            "互动页": "绘画创作+音乐欣赏",
            "总结页": "水彩总结+艺术签名"
        },
        "description": "适合艺术、文学课程，营造温馨浪漫的学习氛围"
    },
    "9": {
        "id": "tech_neon",
        "name": "科技霓虹",
        "style": "科技霓虹风格",
        "colors": {
            "primary": "#0D0D0D",  # 深黑色
            "secondary": "#1A1A1A",  # 深灰色
            "accent": "#00FF88",  # 霓虹绿
            "background": "#0D0D0D"  # 黑色背景
        },
        "elements": ["霓虹灯光", "科技线条", "数据流", "电路板", "未来感"],
        "subjects": ["信息技术", "编程", "人工智能", "科技创新"],
        "scenes": ["编程教学", "科技展示", "创客教育", "未来科技"],
        "stages": ["初中", "高中", "大学"],
        "atmosphere": "未来科技、酷炫动感",
        "design_suggestions": {
            "导入页": "霓虹标题+科技背景",
            "知识点页": "代码展示+电路装饰",
            "练习页": "编程题目+数据图表",
            "互动页": "代码演示+实时反馈",
            "总结页": "科技总结+未来展望"
        },
        "description": "适合信息技术、编程课程，营造科技未来的学习氛围"
    },
    "10": {
        "id": "warm_healing",
        "name": "暖黄治愈风",
        "style": "温暖治愈风格",
        "colors": {
            "primary": "#F39C12",  # 暖黄色
            "secondary": "#E67E22",  # 橙色
            "accent": "#27AE60",  # 绿色
            "background": "#FFF9E6"  # 浅黄色
        },
        "elements": ["阳光", "笑脸", "爱心", "彩虹", "治愈插画"],
        "subjects": ["班会", "德育", "心理健康", "生命教育"],
        "scenes": ["班会课", "心理健康", "德育教育", "成长分享"],
        "stages": ["小学", "初中", "高中"],
        "atmosphere": "温暖治愈、正能量满满",
        "design_suggestions": {
            "导入页": "阳光背景+笑脸欢迎",
            "知识点页": "温暖卡片+治愈插图",
            "练习页": "心灵问答+正能量语录",
            "互动页": "分享圈+感恩墙",
            "总结页": "成长寄语+温暖祝福"
        },
        "description": "适合班会、心理健康课程，营造温暖治愈的学习氛围"
    },
    "11": {
        "id": "european_fresh",
        "name": "清新欧美风",
        "style": "清新欧美风格",
        "colors": {
            "primary": "#2E86AB",  # 海蓝色
            "secondary": "#A23B72",  # 紫红色
            "accent": "#F18F01",  # 橙色
            "background": "#F5F5F5"  # 浅灰色
        },
        "elements": ["字母图案", "对话框", "插画人物", "欧美插画", "清新配色"],
        "subjects": ["英语", "外语"],
        "scenes": ["英语教学", "口语练习", "语法讲解", "阅读理解"],
        "stages": ["小学", "初中", "高中", "大学"],
        "atmosphere": "清新活泼、国际范儿",
        "design_suggestions": {
            "导入页": "字母背景+对话气泡",
            "知识点页": "图文并茂+对话框展示",
            "练习页": "填空选择+插画配图",
            "互动页": "角色扮演+情景对话",
            "总结页": "词汇总结+语法归纳"
        },
        "description": "适合英语教学，营造清新活泼的学习氛围"
    },
    "12": {
        "id": "lab_tech",
        "name": "实验室科技风",
        "style": "实验室科技风格",
        "colors": {
            "primary": "#1ABC9C",  # 青绿色
            "secondary": "#3498DB",  # 蓝色
            "accent": "#E74C3C",  # 红色
            "background": "#ECF0F1"  # 浅灰色
        },
        "elements": ["烧杯", "试管", "分子结构", "数据图表", "实验器材"],
        "subjects": ["物理", "化学", "生物", "科学"],
        "scenes": ["实验教学", "科学探究", "数据分析", "实验报告"],
        "stages": ["初中", "高中", "大学"],
        "atmosphere": "专业严谨、科学探究",
        "design_suggestions": {
            "导入页": "实验室背景+科学仪器",
            "知识点页": "图文混排+数据图表",
            "练习页": "实验步骤+数据记录",
            "互动页": "实验模拟+数据分析",
            "总结页": "实验结论+科学总结"
        },
        "description": "适合理科实验教学，营造专业严谨的科学探究氛围"
    },
    "13": {
        "id": "sports_energy",
        "name": "活力运动风",
        "style": "活力运动风格",
        "colors": {
            "primary": "#FF5722",  # 橙红色
            "secondary": "#4CAF50",  # 绿色
            "accent": "#2196F3",  # 蓝色
            "background": "#FFFFFF"  # 白色
        },
        "elements": ["运动器材", "活力人物", "动感线条", "奖杯", "能量符号"],
        "subjects": ["体育", "健康教育"],
        "scenes": ["体育教学", "运动训练", "健康知识", "团队活动"],
        "stages": ["小学", "初中", "高中"],
        "atmosphere": "活力四射、积极向上",
        "design_suggestions": {
            "导入页": "运动背景+活力标题",
            "知识点页": "动作分解+运动图标",
            "练习页": "运动计划+健康问答",
            "互动页": "团队游戏+运动挑战",
            "总结页": "运动成果+健康目标"
        },
        "description": "适合体育、健康教育课程，营造活力四射的学习氛围"
    },
    "14": {
        "id": "music_rhythm",
        "name": "音乐律动风",
        "style": "音乐律动风格",
        "colors": {
            "primary": "#9C27B0",  # 紫色
            "secondary": "#E91E63",  # 粉色
            "accent": "#FFEB3B",  # 黄色
            "background": "#F3E5F5"  # 浅紫色
        },
        "elements": ["音符", "五线谱", "乐器", "音乐符号", "律动线条"],
        "subjects": ["音乐", "艺术"],
        "scenes": ["音乐教学", "乐器介绍", "音乐欣赏", "合唱排练"],
        "stages": ["小学", "初中", "高中"],
        "atmosphere": "艺术浪漫、律动优美",
        "design_suggestions": {
            "导入页": "音符背景+音乐标题",
            "知识点页": "五线谱装饰+乐器图片",
            "练习页": "节奏练习+乐理知识",
            "互动页": "音乐游戏+节奏模仿",
            "总结页": "音乐欣赏+艺术感悟"
        },
        "description": "适合音乐、艺术课程，营造艺术浪漫的学习氛围"
    }
}


def get_template_list():
    """获取模板列表，用于展示给用户"""
    template_list = []
    for key, template in EDUCATION_TEMPLATES.items():
        template_list.append({
            "number": key,
            "name": template["name"],
            "style": template["style"],
            "colors": template["colors"],
            "subjects": template["subjects"],
            "scenes": template["scenes"],
            "stages": template["stages"],
            "atmosphere": template["atmosphere"],
            "description": template["description"]
        })
    return template_list


def get_template_by_number(number: str):
    """根据编号获取模板"""
    return EDUCATION_TEMPLATES.get(number)


def get_template_by_name(name: str):
    """根据名称获取模板"""
    # 精确匹配
    for template in EDUCATION_TEMPLATES.values():
        if name == template["name"] or name == template["id"]:
            return template

    # 模糊匹配
    for template in EDUCATION_TEMPLATES.values():
        if name in template["name"] or template["name"] in name:
            return template
        if name in template["id"]:
            return template

    return None


def get_templates_by_subject(subject: str):
    """根据学科获取推荐模板"""
    recommendations = []
    for template in EDUCATION_TEMPLATES.values():
        if subject in template["subjects"]:
            recommendations.append(template)
    return recommendations


def get_templates_by_stage(stage: str):
    """根据学段获取推荐模板"""
    recommendations = []
    for template in EDUCATION_TEMPLATES.values():
        if stage in template["stages"]:
            recommendations.append(template)
    return recommendations


def format_template_message():
    """格式化模板选择消息"""
    message = "很好！大纲已确认。现在请选择PPT风格模板：\n\n"
    message += "🎨 **教育行业专用模板矩阵**\n\n"

    for key, template in EDUCATION_TEMPLATES.items():
        # 获取主色调
        primary_color = template["colors"]["primary"]
        secondary_color = template["colors"]["secondary"]

        message += f"{key}️⃣ **{template['name']}** - {template['style']}\n"
        message += f"   🎨 主色调：{primary_color} + {secondary_color}\n"
        message += f"   📚 适合学科：{'、'.join(template['subjects'][:3])}\n"
        message += f"   🎯 适用场景：{'、'.join(template['scenes'][:2])}\n"
        message += f"   🏫 适用学段：{'、'.join(template['stages'])}\n"
        message += f"   ✨ 氛围特点：{template['atmosphere']}\n"
        message += f"   💡 {template['description']}\n\n"

    message += "---\n"
    message += "请回复数字（1-14）选择模板，或回复风格名称（如\"国风\"、\"卡通\"、\"科技\"等）。\n"
    message += "也可以告诉我学科和场景，我为您推荐最合适的模板！"

    return message


def format_template_recommendation(templates):
    """格式化模板推荐消息"""
    if not templates:
        return "抱歉，没有找到匹配的模板。请尝试其他关键词。"

    message = "为您推荐以下模板：\n\n"

    for i, template in enumerate(templates[:3], 1):
        message += f"{i}. **{template['name']}** - {template['style']}\n"
        message += f"   氛围：{template['atmosphere']}\n"
        message += f"   适合：{template['description']}\n\n"

    message += "请回复模板名称或告诉我您的具体需求，我为您选择最合适的模板！"

    return message
