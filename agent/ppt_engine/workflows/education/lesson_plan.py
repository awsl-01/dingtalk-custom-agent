"""
PPT Engine - 教案生成Workflow

根据学科、年级、章节生成完整教案。
支持学情分析、知识点提取、练习题生成。
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class LessonPlan:
    """教案"""
    title: str
    subject: str
    grade: str
    chapter: str
    duration: str = '2课时'

    # 学习目标
    objectives: Dict[str, List[str]] = field(default_factory=lambda: {
        'knowledge': [],  # 知识与技能
        'process': [],    # 过程与方法
        'emotion': []     # 情感态度价值观
    })

    # 重难点
    key_points: List[str] = field(default_factory=list)
    difficult_points: List[str] = field(default_factory=list)

    # 教学方法
    teaching_methods: List[str] = field(default_factory=list)

    # 学情分析
    student_analysis: Dict[str, Any] = field(default_factory=lambda: {
        'level': '',
        'prerequisites': [],
        'interests': []
    })

    # 教学过程
    teaching_process: Dict[str, Any] = field(default_factory=lambda: {
        'lead_in': {'duration': '5分钟', 'activities': [], 'design_intent': ''},
        'new_lesson': {'duration': '25分钟', 'activities': []},
        'practice': {'duration': '10分钟', 'exercises': []},
        'summary': {'duration': '3分钟', 'content': ''},
        'homework': {'required': [], 'optional': []}
    })

    # 板书设计
    board_design: Dict[str, Any] = field(default_factory=lambda: {
        'title': '',
        'structure': []
    })

    # 教学反思
    teaching_reflection: Dict[str, Any] = field(default_factory=lambda: {
        'highlights': [],
        'improvements': [],
        'student_feedback': ''
    })

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'subject': self.subject,
            'grade': self.grade,
            'chapter': self.chapter,
            'duration': self.duration,
            'objectives': self.objectives,
            'key_points': self.key_points,
            'difficult_points': self.difficult_points,
            'teaching_methods': self.teaching_methods,
            'student_analysis': self.student_analysis,
            'teaching_process': self.teaching_process,
            'board_design': self.board_design,
            'teaching_reflection': self.teaching_reflection
        }


class LessonPlanGenerator:
    """教案生成器"""

    # 学科默认教学方法
    SUBJECT_METHODS = {
        '数学': ['讲授法', '练习法', '讨论法', '启发式教学'],
        '物理': ['实验法', '讲授法', '探究式教学', '讨论法'],
        '化学': ['实验法', '讲授法', '探究式教学', '演示法'],
        '生物': ['实验法', '观察法', '讨论法', '探究式教学'],
        '语文': ['讲授法', '讨论法', '朗读法', '情境教学法'],
        '英语': ['交际法', '听说法', '情景教学法', '任务型教学'],
        '历史': ['讲授法', '讨论法', '史料分析法', '问题探究法'],
        '地理': ['讲授法', '读图分析法', '案例教学法', '实地考察法'],
        '信息技术': ['任务驱动法', '演示法', '实践操作法', '协作学习法'],
        '政治': ['讲授法', '讨论法', '案例分析法', '辩论法'],
    }

    # 学科默认学情
    SUBJECT_STUDENT_ANALYSIS = {
        '数学': {
            'level': '中等',
            'prerequisites': ['基础运算', '代数基础'],
            'interests': ['解题挑战', '实际应用']
        },
        '物理': {
            'level': '中等',
            'prerequisites': ['数学基础', '实验操作'],
            'interests': ['实验探究', '科技前沿']
        },
        '化学': {
            'level': '中等',
            'prerequisites': ['元素周期表', '化学方程式'],
            'interests': ['实验现象', '生活应用']
        },
        '生物': {
            'level': '中等',
            'prerequisites': ['细胞结构', '遗传基础'],
            'interests': ['生命现象', '生态保护']
        },
        '语文': {
            'level': '中等',
            'prerequisites': ['基础阅读', '写作能力'],
            'interests': ['文学欣赏', '写作表达']
        },
        '英语': {
            'level': '中等',
            'prerequisites': ['基础词汇', '简单语法'],
            'interests': ['口语交流', '文化了解']
        },
        '历史': {
            'level': '中等',
            'prerequisites': ['历史时间线', '基本史料'],
            'interests': ['历史故事', '人物评价']
        },
        '地理': {
            'level': '中等',
            'prerequisites': ['地图知识', '气候基础'],
            'interests': ['自然景观', '人文地理']
        },
        '信息技术': {
            'level': '中等',
            'prerequisites': ['计算机基础', '网络知识'],
            'interests': ['编程实践', '新技术']
        },
        '政治': {
            'level': '中等',
            'prerequisites': ['时事关注', '基础概念'],
            'interests': ['社会热点', '案例分析']
        },
    }

    def __init__(self, project_path: str = None):
        """
        初始化教案生成器

        参数:
            project_path: 项目路径（可选）
        """
        self.project_path = Path(project_path) if project_path else None

    def generate(self, subject: str, grade: str, chapter: str,
                content: Dict[str, Any] = None) -> LessonPlan:
        """
        生成教案

        参数:
            subject: 学科
            grade: 年级
            chapter: 章节
            content: 额外内容（可选）

        返回:
            LessonPlan对象
        """
        # 创建基础教案
        plan = LessonPlan(
            title=f"{subject} - {chapter}",
            subject=subject,
            grade=grade,
            chapter=chapter
        )

        # 设置教学方法
        plan.teaching_methods = self.SUBJECT_METHODS.get(subject, ['讲授法', '讨论法'])

        # 设置学情分析
        plan.student_analysis = self.SUBJECT_STUDENT_ANALYSIS.get(subject, {
            'level': '中等',
            'prerequisites': [],
            'interests': []
        })

        # 合并额外内容
        if content:
            self._merge_content(plan, content)

        # 生成默认内容（如果缺失）
        self._fill_defaults(plan)

        return plan

    def _merge_content(self, plan: LessonPlan, content: Dict[str, Any]):
        """合并额外内容"""
        if 'objectives' in content:
            plan.objectives.update(content['objectives'])

        if 'key_points' in content:
            plan.key_points = content['key_points']

        if 'difficult_points' in content:
            plan.difficult_points = content['difficult_points']

        if 'teaching_methods' in content:
            plan.teaching_methods = content['teaching_methods']

        if 'student_analysis' in content:
            plan.student_analysis.update(content['student_analysis'])

        if 'teaching_process' in content:
            plan.teaching_process.update(content['teaching_process'])

    def _fill_defaults(self, plan: LessonPlan):
        """填充默认内容"""
        # 默认学习目标
        if not plan.objectives['knowledge']:
            plan.objectives['knowledge'] = [
                f"掌握{plan.chapter}的基本概念",
                f"理解{plan.chapter}的核心原理"
            ]

        if not plan.objectives['process']:
            plan.objectives['process'] = [
                "通过探究学习，培养分析问题的能力",
                "通过合作讨论，提高交流表达能力"
            ]

        if not plan.objectives['emotion']:
            plan.objectives['emotion'] = [
                f"激发对{plan.subject}学科的学习兴趣",
                "培养严谨的科学态度"
            ]

        # 默认重难点
        if not plan.key_points:
            plan.key_points = [f"{plan.chapter}的核心概念和原理"]

        if not plan.difficult_points:
            plan.difficult_points = [f"{plan.chapter}的实际应用"]

        # 默认教学过程
        if not plan.teaching_process['lead_in']['activities']:
            plan.teaching_process['lead_in']['activities'] = [
                f"通过生活实例引入{plan.chapter}的话题",
                "提出问题，引发学生思考"
            ]
            plan.teaching_process['lead_in']['design_intent'] = '激发学习兴趣，建立知识联系'

        if not plan.teaching_process['new_lesson']['activities']:
            plan.teaching_process['new_lesson']['activities'] = [
                {'title': '概念讲解', 'duration': '10分钟', 'content': f'讲解{plan.chapter}的基本概念'},
                {'title': '原理分析', 'duration': '10分钟', 'content': f'分析{plan.chapter}的核心原理'},
                {'title': '例题演示', 'duration': '5分钟', 'content': '通过例题加深理解'}
            ]

        if not plan.teaching_process['practice']['exercises']:
            plan.teaching_process['practice']['exercises'] = [
                f"基础练习：{plan.chapter}基本概念填空",
                f"提高练习：{plan.chapter}应用题"
            ]

        if not plan.teaching_process['summary']['content']:
            plan.teaching_process['summary']['content'] = f"总结{plan.chapter}的重点内容，强调核心概念"

        if not plan.teaching_process['homework']['required']:
            plan.teaching_process['homework']['required'] = [
                f"完成{plan.chapter}课后习题"
            ]

        if not plan.teaching_process['homework']['optional']:
            plan.teaching_process['homework']['optional'] = [
                f"查阅{plan.chapter}相关拓展资料"
            ]

        # 默认板书设计
        if not plan.board_design['title']:
            plan.board_design['title'] = plan.title
            plan.board_design['structure'] = [
                f"一、{plan.chapter}的基本概念",
                f"二、{plan.chapter}的核心原理",
                "三、例题解析",
                "四、课堂小结"
            ]

    def to_markdown(self, plan: LessonPlan) -> str:
        """
        生成Markdown格式教案

        参数:
            plan: 教案对象

        返回:
            Markdown字符串
        """
        md = f"""# {plan.title}

## 基本信息

- 学科：{plan.subject}
- 年级：{plan.grade}
- 章节：{plan.chapter}
- 课时：{plan.duration}

## 学习目标

### 知识与技能
{self._list_to_md(plan.objectives['knowledge'])}

### 过程与方法
{self._list_to_md(plan.objectives['process'])}

### 情感态度价值观
{self._list_to_md(plan.objectives['emotion'])}

## 教学重难点

### 教学重点
{self._list_to_md(plan.key_points)}

### 教学难点
{self._list_to_md(plan.difficult_points)}

## 教学方法

{self._list_to_md(plan.teaching_methods)}

## 学情分析

- 学习水平：{plan.student_analysis.get('level', '中等')}
- 前置知识：{', '.join(plan.student_analysis.get('prerequisites', []))}
- 学习兴趣：{', '.join(plan.student_analysis.get('interests', []))}

## 教学过程

### 一、导入（{plan.teaching_process['lead_in']['duration']}）

**活动：**
{self._list_to_md(plan.teaching_process['lead_in']['activities'])}

**设计意图：** {plan.teaching_process['lead_in']['design_intent']}

### 二、新课讲授（{plan.teaching_process['new_lesson']['duration']}）

{self._activities_to_md(plan.teaching_process['new_lesson']['activities'])}

### 三、课堂练习（{plan.teaching_process['practice']['duration']}）

{self._list_to_md(plan.teaching_process['practice']['exercises'])}

### 四、课堂小结（{plan.teaching_process['summary']['duration']}）

{plan.teaching_process['summary']['content']}

### 五、作业布置

**必做：**
{self._list_to_md(plan.teaching_process['homework']['required'])}

**选做：**
{self._list_to_md(plan.teaching_process['homework']['optional'])}

## 板书设计

**{plan.board_design['title']}**

{self._list_to_md(plan.board_design['structure'])}

## 教学反思

### 教学亮点
{self._list_to_md(plan.teaching_reflection.get('highlights', []))}

### 改进措施
{self._list_to_md(plan.teaching_reflection.get('improvements', []))}

---
*Generated by PPT Engine*
"""
        return md

    def _list_to_md(self, items: list) -> str:
        """列表转Markdown"""
        if not items:
            return "- （待补充）"
        return '\n'.join(f"- {item}" for item in items)

    def _activities_to_md(self, activities: list) -> str:
        """活动列表转Markdown"""
        if not activities:
            return "- （待补充）"

        lines = []
        for i, activity in enumerate(activities, 1):
            if isinstance(activity, dict):
                title = activity.get('title', f'活动{i}')
                duration = activity.get('duration', '')
                content = activity.get('content', '')
                lines.append(f"**{title}**（{duration}）")
                lines.append(f"{content}")
                lines.append("")
            else:
                lines.append(f"- {activity}")

        return '\n'.join(lines)

    def save(self, plan: LessonPlan, output_path: str = None) -> Path:
        """
        保存教案

        参数:
            plan: 教案对象
            output_path: 输出路径

        返回:
            保存路径
        """
        if output_path is None:
            if self.project_path:
                output_path = self.project_path / 'notes' / 'lesson_plan.md'
            else:
                output_path = Path('lesson_plan.md')
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        md_content = self.to_markdown(plan)
        output_path.write_text(md_content, encoding='utf-8')

        print(f"[OK] Lesson plan saved: {output_path}")
        return output_path


def generate_lesson_plan(subject: str, grade: str, chapter: str,
                        output_path: str = None) -> LessonPlan:
    """
    生成教案（便捷函数）

    参数:
        subject: 学科
        grade: 年级
        chapter: 章节
        output_path: 输出路径

    返回:
        LessonPlan对象
    """
    generator = LessonPlanGenerator()
    plan = generator.generate(subject, grade, chapter)
    generator.save(plan, output_path)
    return plan
