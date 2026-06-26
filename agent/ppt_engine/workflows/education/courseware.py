"""
PPT Engine - 课件大纲生成Workflow

根据教案生成课件大纲和SVG页面规划。
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .lesson_plan import LessonPlan


@dataclass
class CoursewarePage:
    """课件页面"""
    page_num: int
    title: str
    layout: str = 'content'
    rhythm: str = 'dense'
    content: Dict[str, Any] = field(default_factory=dict)
    notes: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return {
            'page_num': self.page_num,
            'title': self.title,
            'layout': self.layout,
            'rhythm': self.rhythm,
            'content': self.content,
            'notes': self.notes
        }


@dataclass
class Courseware:
    """课件大纲"""
    title: str
    subject: str
    grade: str
    chapter: str
    pages: List[CoursewarePage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'subject': self.subject,
            'grade': self.grade,
            'chapter': self.chapter,
            'pages': [p.to_dict() for p in self.pages],
            'metadata': self.metadata
        }


class CoursewareGenerator:
    """课件大纲生成器"""

    # 学科默认布局映射
    SUBJECT_LAYOUTS = {
        '数学': {
            'cover': 'cover',
            'objectives': 'three_card',
            'definition': 'formula_step',
            'graph': 'graph_illustration',
            'example': 'exercise_steps',
            'practice': 'exercise_steps',
            'summary': 'content',
            'ending': 'ending'
        },
        '物理': {
            'cover': 'cover',
            'objectives': 'three_card',
            'phenomenon': 'experiment_flow',
            'experiment': 'experiment_flow',
            'law': 'formula_step',
            'application': 'structure_diagram',
            'summary': 'content',
            'ending': 'ending'
        },
        '化学': {
            'cover': 'cover',
            'objectives': 'three_card',
            'introduction': 'experiment_flow',
            'principle': 'structure_diagram',
            'experiment': 'experiment_flow',
            'equation': 'formula_step',
            'summary': 'content',
            'ending': 'ending'
        },
        '生物': {
            'cover': 'cover',
            'objectives': 'three_card',
            'introduction': 'content',
            'structure': 'structure_diagram',
            'process': 'experiment_flow',
            'application': 'content',
            'summary': 'content',
            'ending': 'ending'
        },
        '语文': {
            'cover': 'cover',
            'objectives': 'three_card',
            'background': 'text_analysis',
            'reading': 'poetry_vertical',
            'analysis': 'comparison_two_column',
            'appreciation': 'quote',
            'summary': 'content',
            'ending': 'ending'
        },
        '英语': {
            'cover': 'cover',
            'objectives': 'three_card',
            'warmup': 'role_dialogue',
            'vocabulary': 'vocab_cards',
            'pattern': 'sentence_pattern',
            'practice': 'role_dialogue',
            'summary': 'content',
            'ending': 'ending'
        },
        '历史': {
            'cover': 'cover',
            'objectives': 'three_card',
            'background': 'content',
            'timeline': 'timeline',
            'analysis': 'comparison_two_column',
            'impact': 'data_table',
            'summary': 'content',
            'ending': 'ending'
        },
        '地理': {
            'cover': 'cover',
            'objectives': 'three_card',
            'location': 'map_annotation',
            'features': 'content',
            'data': 'data_table',
            'analysis': 'comparison_two_column',
            'summary': 'content',
            'ending': 'ending'
        },
        '信息技术': {
            'cover': 'cover',
            'objectives': 'three_card',
            'concept': 'content',
            'code': 'code_block',
            'flowchart': 'flowchart',
            'practice': 'terminal_output',
            'summary': 'content',
            'ending': 'ending'
        },
        '政治': {
            'cover': 'cover',
            'objectives': 'three_card',
            'concept': 'content',
            'case': 'comparison_two_column',
            'analysis': 'data_table',
            'discussion': 'content',
            'summary': 'content',
            'ending': 'ending'
        },
    }

    def __init__(self, project_path: str = None):
        """
        初始化课件大纲生成器

        参数:
            project_path: 项目路径（可选）
        """
        self.project_path = Path(project_path) if project_path else None

    def generate_from_lesson_plan(self, lesson_plan: LessonPlan) -> Courseware:
        """
        从教案生成课件大纲

        参数:
            lesson_plan: 教案对象

        返回:
            Courseware对象
        """
        courseware = Courseware(
            title=lesson_plan.title,
            subject=lesson_plan.subject,
            grade=lesson_plan.grade,
            chapter=lesson_plan.chapter
        )

        # 获取学科布局
        layouts = self.SUBJECT_LAYOUTS.get(lesson_plan.subject, self.SUBJECT_LAYOUTS['数学'])

        # 生成页面
        pages = []
        page_num = 1

        # 1. 封面
        pages.append(CoursewarePage(
            page_num=page_num,
            title='封面',
            layout=layouts.get('cover', 'cover'),
            rhythm='anchor',
            content={
                'title': lesson_plan.title,
                'subtitle': f"{lesson_plan.grade} - {lesson_plan.subject}",
                'author': '教师姓名',
                'date': '2026-06-04'
            },
            notes='开场介绍课程主题和目标'
        ))
        page_num += 1

        # 2. 学习目标
        pages.append(CoursewarePage(
            page_num=page_num,
            title='学习目标',
            layout=layouts.get('objectives', 'three_card'),
            rhythm='dense',
            content={
                'title': '学习目标',
                'cards': [
                    {'title': '知识与技能', 'content': '\n'.join(lesson_plan.objectives['knowledge'][:2])},
                    {'title': '过程与方法', 'content': '\n'.join(lesson_plan.objectives['process'][:2])},
                    {'title': '情感态度', 'content': '\n'.join(lesson_plan.objectives['emotion'][:2])}
                ]
            },
            notes='明确本节课的学习目标'
        ))
        page_num += 1

        # 3. 导入环节
        lead_in = lesson_plan.teaching_process.get('lead_in', {})
        pages.append(CoursewarePage(
            page_num=page_num,
            title='课程导入',
            layout='content',
            rhythm='dense',
            content={
                'title': '课程导入',
                'body': lead_in.get('design_intent', ''),
                'bullets': lead_in.get('activities', [])
            },
            notes='通过实例引入课题'
        ))
        page_num += 1

        # 4. 新课讲授（根据教案活动生成多页）
        new_lesson = lesson_plan.teaching_process.get('new_lesson', {})
        activities = new_lesson.get('activities', [])

        for activity in activities:
            if isinstance(activity, dict):
                title = activity.get('title', '新课讲授')
                content = activity.get('content', '')

                # 根据内容类型选择布局
                layout = self._select_layout_for_content(title, lesson_plan.subject)

                pages.append(CoursewarePage(
                    page_num=page_num,
                    title=title,
                    layout=layout,
                    rhythm='dense',
                    content={
                        'title': title,
                        'body': content
                    },
                    notes=f'讲解{title}'
                ))
                page_num += 1

        # 5. 课堂练习
        practice = lesson_plan.teaching_process.get('practice', {})
        exercises = practice.get('exercises', [])

        if exercises:
            pages.append(CoursewarePage(
                page_num=page_num,
                title='课堂练习',
                layout='exercise_steps',
                rhythm='dense',
                content={
                    'title': '课堂练习',
                    'bullets': exercises
                },
                notes='学生独立完成练习'
            ))
            page_num += 1

        # 6. 课堂小结
        summary = lesson_plan.teaching_process.get('summary', {})
        pages.append(CoursewarePage(
            page_num=page_num,
            title='课堂小结',
            layout='content',
            rhythm='dense',
            content={
                'title': '课堂小结',
                'body': summary.get('content', '')
            },
            notes='总结本节课重点'
        ))
        page_num += 1

        # 7. 作业布置
        homework = lesson_plan.teaching_process.get('homework', {})
        pages.append(CoursewarePage(
            page_num=page_num,
            title='作业布置',
            layout='two_card',
            rhythm='dense',
            content={
                'title': '作业布置',
                'cards': [
                    {'title': '必做作业', 'content': '\n'.join(homework.get('required', []))},
                    {'title': '选做作业', 'content': '\n'.join(homework.get('optional', []))}
                ]
            },
            notes='布置课后作业'
        ))
        page_num += 1

        # 8. 结束页
        pages.append(CoursewarePage(
            page_num=page_num,
            title='谢谢',
            layout=layouts.get('ending', 'ending'),
            rhythm='breathing',
            content={
                'title': '谢谢',
                'subtitle': '欢迎提问交流'
            },
            notes='结束课程'
        ))

        courseware.pages = pages
        return courseware

    def _select_layout_for_content(self, title: str, subject: str) -> str:
        """根据内容标题选择布局"""
        title_lower = title.lower()

        # 关键词匹配
        if any(kw in title_lower for kw in ['公式', '定理', '定义']):
            return 'formula_step'
        elif any(kw in title_lower for kw in ['图', '表', '示意']):
            return 'graph_illustration'
        elif any(kw in title_lower for kw in ['例题', '练习', '解']):
            return 'exercise_steps'
        elif any(kw in title_lower for kw in ['实验', '步骤']):
            return 'experiment_flow'
        elif any(kw in title_lower for kw in ['结构', '模型']):
            return 'structure_diagram'
        elif any(kw in title_lower for kw in ['对比', '比较']):
            return 'comparison_two_column'
        elif any(kw in title_lower for kw in ['时间', '历史']):
            return 'timeline'
        elif any(kw in title_lower for kw in ['代码', '程序']):
            return 'code_block'
        else:
            return 'content'

    def to_markdown(self, courseware: Courseware) -> str:
        """
        生成Markdown格式课件大纲

        参数:
            courseware: 课件对象

        返回:
            Markdown字符串
        """
        md = f"""# {courseware.title}

## 基本信息

- 学科：{courseware.subject}
- 年级：{courseware.grade}
- 章节：{courseware.chapter}
- 总页数：{len(courseware.pages)}

## 页面大纲

"""
        for page in courseware.pages:
            md += f"""### 第{page.page_num}页：{page.title}

- 布局：{page.layout}
- 节奏：{page.rhythm}
- 备注：{page.notes}

"""
            # 添加内容摘要
            if 'title' in page.content:
                md += f"**标题：** {page.content['title']}\n\n"
            if 'body' in page.content:
                body = page.content['body'][:100] + '...' if len(page.content['body']) > 100 else page.content['body']
                md += f"**内容：** {body}\n\n"
            if 'bullets' in page.content:
                md += "**要点：**\n"
                for bullet in page.content['bullets'][:3]:
                    md += f"- {bullet}\n"
                md += "\n"

        md += """---
*Generated by PPT Engine CoursewareGenerator*
"""
        return md

    def save(self, courseware: Courseware, output_path: str = None) -> Path:
        """
        保存课件大纲

        参数:
            courseware: 课件对象
            output_path: 输出路径

        返回:
            保存路径
        """
        if output_path is None:
            if self.project_path:
                output_path = self.project_path / 'notes' / 'courseware_outline.md'
            else:
                output_path = Path('courseware_outline.md')
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        md_content = self.to_markdown(courseware)
        output_path.write_text(md_content, encoding='utf-8')

        print(f"[OK] Courseware outline saved: {output_path}")
        return output_path


def generate_courseware(subject: str, grade: str, chapter: str,
                      lesson_plan: LessonPlan = None,
                      output_path: str = None) -> Courseware:
    """
    生成课件大纲（便捷函数）

    参数:
        subject: 学科
        grade: 年级
        chapter: 章节
        lesson_plan: 教案对象（可选）
        output_path: 输出路径

    返回:
        Courseware对象
    """
    from .lesson_plan import LessonPlanGenerator

    generator = CoursewareGenerator()

    # 如果没有提供教案，先生成教案
    if lesson_plan is None:
        plan_generator = LessonPlanGenerator()
        lesson_plan = plan_generator.generate(subject, grade, chapter)

    courseware = generator.generate_from_lesson_plan(lesson_plan)
    generator.save(courseware, output_path)
    return courseware
