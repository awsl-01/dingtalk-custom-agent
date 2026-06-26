"""
PPT Engine - 说课稿生成Workflow

根据教案生成说课稿。
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .lesson_plan import LessonPlan


@dataclass
class TeachingPlan:
    """说课稿"""
    title: str
    subject: str
    grade: str
    chapter: str

    # 说教材
    textbook_analysis: str = ''
    textbook_position: str = ''
    content_analysis: str = ''

    # 说学情
    student_analysis: str = ''
    learning_difficulties: str = ''

    # 说教法
    teaching_methods: str = ''
    method_reasons: str = ''

    # 说学法
    learning_methods: str = ''
    method_guidance: str = ''

    # 说教学过程
    teaching_process: str = ''
    design_intent: str = ''

    # 说板书设计
    board_design: str = ''

    # 说教学反思
    expected_effects: str = ''
    improvement_plan: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'subject': self.subject,
            'grade': self.grade,
            'chapter': self.chapter,
            'textbook_analysis': self.textbook_analysis,
            'textbook_position': self.textbook_position,
            'content_analysis': self.content_analysis,
            'student_analysis': self.student_analysis,
            'learning_difficulties': self.learning_difficulties,
            'teaching_methods': self.teaching_methods,
            'method_reasons': self.method_reasons,
            'learning_methods': self.learning_methods,
            'method_guidance': self.method_guidance,
            'teaching_process': self.teaching_process,
            'design_intent': self.design_intent,
            'board_design': self.board_design,
            'expected_effects': self.expected_effects,
            'improvement_plan': self.improvement_plan
        }


class TeachingPlanGenerator:
    """说课稿生成器"""

    # 学科教材分析模板
    SUBJECT_TEXTBOOK_ANALYSIS = {
        '数学': '本节课是{grade}{subject}的重要内容，属于{chapter}章节。该内容在数学知识体系中起到承上启下的作用，是后续学习的基础。',
        '物理': '本节课是{grade}{subject}的核心内容，{chapter}是物理学的重要概念。通过学习，学生能够理解物理规律，培养科学思维。',
        '化学': '本节课是{grade}{subject}的基础内容，{chapter}是化学学习的关键。学生通过学习能够掌握化学原理，提高实验能力。',
        '生物': '本节课是{grade}{subject}的重要内容，{chapter}是生物学的核心概念。通过学习，学生能够理解生命现象，培养科学素养。',
        '语文': '本节课是{grade}{subject}的经典篇目，{chapter}具有重要的文学价值和教育意义。通过学习，学生能够提高语文素养。',
        '英语': '本节课是{grade}{subject}的重点内容，{chapter}是英语学习的重要环节。通过学习，学生能够提高语言运用能力。',
        '历史': '本节课是{grade}{subject}的重要内容，{chapter}是历史发展的关键时期。通过学习，学生能够理解历史规律。',
        '地理': '本节课是{grade}{subject}的核心内容，{chapter}是地理学习的重要组成部分。通过学习，学生能够认识地理环境。',
        '信息技术': '本节课是{grade}{subject}的基础内容，{chapter}是信息技术的核心技能。通过学习，学生能够掌握信息技术。',
        '政治': '本节课是{grade}{subject}的重要内容，{chapter}是思想政治教育的核心。通过学习，学生能够树立正确价值观。',
    }

    def __init__(self, project_path: str = None):
        """
        初始化说课稿生成器

        参数:
            project_path: 项目路径（可选）
        """
        self.project_path = Path(project_path) if project_path else None

    def generate_from_lesson_plan(self, lesson_plan: LessonPlan) -> TeachingPlan:
        """
        从教案生成说课稿

        参数:
            lesson_plan: 教案对象

        返回:
            TeachingPlan对象
        """
        teaching_plan = TeachingPlan(
            title=f"{lesson_plan.title} - 说课稿",
            subject=lesson_plan.subject,
            grade=lesson_plan.grade,
            chapter=lesson_plan.chapter
        )

        # 说教材
        template = self.SUBJECT_TEXTBOOK_ANALYSIS.get(
            lesson_plan.subject,
            '本节课是{grade}{subject}的重要内容，{chapter}是核心知识点。'
        )
        teaching_plan.textbook_analysis = template.format(
            grade=lesson_plan.grade,
            subject=lesson_plan.subject,
            chapter=lesson_plan.chapter
        )

        teaching_plan.textbook_position = f"{lesson_plan.chapter}在{lesson_plan.subject}知识体系中处于重要地位，是后续学习的基础。"

        teaching_plan.content_analysis = f"本节课主要内容包括：{', '.join(lesson_plan.key_points[:3])}"

        # 说学情
        student_analysis = lesson_plan.student_analysis
        teaching_plan.student_analysis = f"学生整体水平{student_analysis.get('level', '中等')}，已掌握{', '.join(student_analysis.get('prerequisites', [])[:2])}等前置知识。"
        teaching_plan.learning_difficulties = f"本节课的难点在于：{', '.join(lesson_plan.difficult_points[:2])}"

        # 说教法
        methods = lesson_plan.teaching_methods[:3]
        teaching_plan.teaching_methods = f"本节课主要采用{', '.join(methods)}等教学方法。"
        teaching_plan.method_reasons = "这些方法能够激发学生学习兴趣，提高课堂教学效率。"

        # 说学法
        teaching_plan.learning_methods = "引导学生采用自主学习、合作探究、实践操作等学习方法。"
        teaching_plan.method_guidance = "通过教师引导，学生能够主动参与学习过程，提高学习效果。"

        # 说教学过程
        process_parts = []
        lead_in = lesson_plan.teaching_process.get('lead_in', {})
        process_parts.append(f"1. 导入环节（{lead_in.get('duration', '5分钟')}）：{lead_in.get('design_intent', '激发学习兴趣')}")

        new_lesson = lesson_plan.teaching_process.get('new_lesson', {})
        process_parts.append(f"2. 新课讲授（{new_lesson.get('duration', '25分钟')}）：通过讲解和演示，帮助学生理解核心概念")

        practice = lesson_plan.teaching_process.get('practice', {})
        process_parts.append(f"3. 课堂练习（{practice.get('duration', '10分钟')}）：通过练习巩固所学知识")

        summary = lesson_plan.teaching_process.get('summary', {})
        process_parts.append(f"4. 课堂小结（{summary.get('duration', '3分钟')}）：总结本节课重点内容")

        teaching_plan.teaching_process = '\n'.join(process_parts)
        teaching_plan.design_intent = "通过以上环节的设计，旨在提高学生的学习兴趣和参与度，达到良好的教学效果。"

        # 说板书设计
        board = lesson_plan.board_design
        teaching_plan.board_design = f"板书设计以{board.get('title', lesson_plan.title)}为中心，层次分明，重点突出。"

        # 说教学反思
        teaching_plan.expected_effects = "预计通过本节课的学习，学生能够掌握核心概念，提高分析问题的能力。"
        teaching_plan.improvement_plan = "在今后的教学中，将进一步优化教学设计，提高课堂教学效率。"

        return teaching_plan

    def to_markdown(self, teaching_plan: TeachingPlan) -> str:
        """
        生成Markdown格式说课稿

        参数:
            teaching_plan: 说课稿对象

        返回:
            Markdown字符串
        """
        md = f"""# {teaching_plan.title}

## 一、说教材

### 1.1 教材分析

{teaching_plan.textbook_analysis}

### 1.2 教材地位

{teaching_plan.textbook_position}

### 1.3 内容分析

{teaching_plan.content_analysis}

## 二、说学情

### 2.1 学生情况

{teaching_plan.student_analysis}

### 2.2 学习难点

{teaching_plan.learning_difficulties}

## 三、说教法

### 3.1 教学方法

{teaching_plan.teaching_methods}

### 3.2 方法依据

{teaching_plan.method_reasons}

## 四、说学法

### 4.1 学习方法

{teaching_plan.learning_methods}

### 4.2 方法指导

{teaching_plan.method_guidance}

## 五、说教学过程

{teaching_plan.teaching_process}

### 设计意图

{teaching_plan.design_intent}

## 六、说板书设计

{teaching_plan.board_design}

## 七、说教学反思

### 7.1 预期效果

{teaching_plan.expected_effects}

### 7.2 改进计划

{teaching_plan.improvement_plan}

---
*Generated by PPT Engine TeachingPlanGenerator*
"""
        return md

    def save(self, teaching_plan: TeachingPlan, output_path: str = None) -> Path:
        """
        保存说课稿

        参数:
            teaching_plan: 说课稿对象
            output_path: 输出路径

        返回:
            保存路径
        """
        if output_path is None:
            if self.project_path:
                output_path = self.project_path / 'notes' / 'teaching_plan.md'
            else:
                output_path = Path('teaching_plan.md')
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        md_content = self.to_markdown(teaching_plan)
        output_path.write_text(md_content, encoding='utf-8')

        print(f"[OK] Teaching plan saved: {output_path}")
        return output_path


def generate_teaching_plan(subject: str, grade: str, chapter: str,
                          lesson_plan: LessonPlan = None,
                          output_path: str = None) -> TeachingPlan:
    """
    生成说课稿（便捷函数）

    参数:
        subject: 学科
        grade: 年级
        chapter: 章节
        lesson_plan: 教案对象（可选）
        output_path: 输出路径

    返回:
        TeachingPlan对象
    """
    from .lesson_plan import LessonPlanGenerator

    generator = TeachingPlanGenerator()

    # 如果没有提供教案，先生成教案
    if lesson_plan is None:
        plan_generator = LessonPlanGenerator()
        lesson_plan = plan_generator.generate(subject, grade, chapter)

    teaching_plan = generator.generate_from_lesson_plan(lesson_plan)
    generator.save(teaching_plan, output_path)
    return teaching_plan
