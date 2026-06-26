"""
PPT Engine - 教学反思生成Workflow

根据教案和教学过程生成教学反思。
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .lesson_plan import LessonPlan


@dataclass
class TeachingReflection:
    """教学反思"""
    title: str
    subject: str
    grade: str
    chapter: str

    # 教学目标达成情况
    objective_achievement: Dict[str, str] = field(default_factory=lambda: {
        'knowledge': '',
        'process': '',
        'emotion': ''
    })

    # 教学亮点
    highlights: List[str] = field(default_factory=list)

    # 不足之处
    shortcomings: List[str] = field(default_factory=list)

    # 改进措施
    improvements: List[str] = field(default_factory=list)

    # 学生反馈
    student_feedback: str = ''

    # 后续教学计划
    follow_up_plan: str = ''

    # 总结
    summary: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'subject': self.subject,
            'grade': self.grade,
            'chapter': self.chapter,
            'objective_achievement': self.objective_achievement,
            'highlights': self.highlights,
            'shortcomings': self.shortcomings,
            'improvements': self.improvements,
            'student_feedback': self.student_feedback,
            'follow_up_plan': self.follow_up_plan,
            'summary': self.summary
        }


class TeachingReflectionGenerator:
    """教学反思生成器"""

    # 学科默认亮点
    SUBJECT_HIGHLIGHTS = {
        '数学': [
            '通过例题讲解，学生能够掌握解题方法',
            '课堂练习环节，学生参与度较高',
            '板书设计清晰，便于学生理解'
        ],
        '物理': [
            '实验演示直观，学生印象深刻',
            '通过问题引导，学生积极思考',
            '理论联系实际，学生兴趣浓厚'
        ],
        '化学': [
            '实验操作规范，学生观察仔细',
            '化学方程式讲解清晰',
            '安全教育到位，学生意识增强'
        ],
        '生物': [
            '图片展示生动，学生理解透彻',
            '实验探究环节，学生动手能力强',
            '生命教育渗透，情感目标达成'
        ],
        '语文': [
            '朗读指导到位，学生语感增强',
            '文本分析深入，学生理解深刻',
            '写作指导实用，学生收获较大'
        ],
        '英语': [
            '情景创设真实，学生口语表达流利',
            '词汇教学方法多样，学生记忆牢固',
            '文化渗透自然，学生视野开阔'
        ],
        '历史': [
            '史料运用恰当，学生分析能力提高',
            '时间线索清晰，学生掌握较好',
            '历史评价客观，学生思维活跃'
        ],
        '地理': [
            '地图运用熟练，学生读图能力增强',
            '案例分析典型，学生理解透彻',
            '环保教育渗透，学生意识提高'
        ],
        '信息技术': [
            '任务设计合理，学生操作规范',
            '代码讲解清晰，学生掌握扎实',
            '网络安全教育到位'
        ],
        '政治': [
            '案例选取典型，学生分析深入',
            '价值观引导自然，学生认同度高',
            '时事结合紧密，学生关注度高'
        ],
    }

    # 学科默认不足
    SUBJECT_SHORTCOMINGS = [
        '课堂时间分配还需优化',
        '个别学生关注不够',
        '练习难度梯度设计可改进'
    ]

    # 学科默认改进措施
    SUBJECT_IMPROVEMENTS = [
        '加强课堂时间管理，提高教学效率',
        '关注每一位学生，特别是学困生',
        '设计分层练习，满足不同学生需求'
    ]

    def __init__(self, project_path: str = None):
        """
        初始化教学反思生成器

        参数:
            project_path: 项目路径（可选）
        """
        self.project_path = Path(project_path) if project_path else None

    def generate_from_lesson_plan(self, lesson_plan: LessonPlan,
                                 highlights: List[str] = None,
                                 shortcomings: List[str] = None) -> TeachingReflection:
        """
        从教案生成教学反思

        参数:
            lesson_plan: 教案对象
            highlights: 教学亮点（可选）
            shortcomings: 不足之处（可选）

        返回:
            TeachingReflection对象
        """
        reflection = TeachingReflection(
            title=f"{lesson_plan.title} - 教学反思",
            subject=lesson_plan.subject,
            grade=lesson_plan.grade,
            chapter=lesson_plan.chapter
        )

        # 教学目标达成情况
        reflection.objective_achievement = {
            'knowledge': f"通过本节课学习，学生基本掌握了{lesson_plan.chapter}的核心概念，知识目标达成度较高。",
            'process': f"学生通过{', '.join(lesson_plan.teaching_methods[:2])}等方法，提高了分析问题的能力。",
            'emotion': f"学生对{lesson_plan.subject}学科的学习兴趣有所提高，情感目标基本达成。"
        }

        # 教学亮点
        reflection.highlights = highlights or self.SUBJECT_HIGHLIGHTS.get(
            lesson_plan.subject,
            self.SUBJECT_HIGHLIGHTS['数学']
        )

        # 不足之处
        reflection.shortcomings = shortcomings or self.SUBJECT_SHORTCOMINGS

        # 改进措施
        reflection.improvements = self.SUBJECT_IMPROVEMENTS

        # 学生反馈
        reflection.student_feedback = "学生普遍反映本节课内容充实，讲解清晰，课堂氛围良好。"

        # 后续教学计划
        reflection.follow_up_plan = f"在后续教学中，将结合本节课内容，继续深入讲解{lesson_plan.chapter}的相关知识。"

        # 总结
        reflection.summary = f"总体而言，本节课达到了预期教学目标，学生对{lesson_plan.chapter}有了较好的理解。"

        return reflection

    def to_markdown(self, reflection: TeachingReflection) -> str:
        """
        生成Markdown格式教学反思

        参数:
            reflection: 教学反思对象

        返回:
            Markdown字符串
        """
        md = f"""# {reflection.title}

## 基本信息

- 学科：{reflection.subject}
- 年级：{reflection.grade}
- 章节：{reflection.chapter}

## 一、教学目标达成情况

### 1.1 知识与技能目标

{reflection.objective_achievement.get('knowledge', '')}

### 1.2 过程与方法目标

{reflection.objective_achievement.get('process', '')}

### 1.3 情感态度价值观目标

{reflection.objective_achievement.get('emotion', '')}

## 二、教学亮点

{self._list_to_md(reflection.highlights)}

## 三、不足之处

{self._list_to_md(reflection.shortcomings)}

## 四、改进措施

{self._list_to_md(reflection.improvements)}

## 五、学生反馈

{reflection.student_feedback}

## 六、后续教学计划

{reflection.follow_up_plan}

## 七、总结

{reflection.summary}

---
*Generated by PPT Engine TeachingReflectionGenerator*
"""
        return md

    def _list_to_md(self, items: list) -> str:
        """列表转Markdown"""
        if not items:
            return "- （待补充）"
        return '\n'.join(f"- {item}" for item in items)

    def save(self, reflection: TeachingReflection, output_path: str = None) -> Path:
        """
        保存教学反思

        参数:
            reflection: 教学反思对象
            output_path: 输出路径

        返回:
            保存路径
        """
        if output_path is None:
            if self.project_path:
                output_path = self.project_path / 'notes' / 'teaching_reflection.md'
            else:
                output_path = Path('teaching_reflection.md')
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        md_content = self.to_markdown(reflection)
        output_path.write_text(md_content, encoding='utf-8')

        print(f"[OK] Teaching reflection saved: {output_path}")
        return output_path


def generate_teaching_reflection(subject: str, grade: str, chapter: str,
                                lesson_plan: LessonPlan = None,
                                output_path: str = None) -> TeachingReflection:
    """
    生成教学反思（便捷函数）

    参数:
        subject: 学科
        grade: 年级
        chapter: 章节
        lesson_plan: 教案对象（可选）
        output_path: 输出路径

    返回:
        TeachingReflection对象
    """
    from .lesson_plan import LessonPlanGenerator

    generator = TeachingReflectionGenerator()

    # 如果没有提供教案，先生成教案
    if lesson_plan is None:
        plan_generator = LessonPlanGenerator()
        lesson_plan = plan_generator.generate(subject, grade, chapter)

    reflection = generator.generate_from_lesson_plan(lesson_plan)
    generator.save(reflection, output_path)
    return reflection
