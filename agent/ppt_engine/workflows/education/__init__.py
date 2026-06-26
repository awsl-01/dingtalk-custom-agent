"""
PPT Engine - 教育专项Workflow

支持教育场景：
- 教案生成 (lesson_plan)
- 课件大纲 (courseware)
- 说课稿 (teaching_plan)
- 教学反思 (teaching_reflection)
"""

from .lesson_plan import LessonPlanGenerator
from .courseware import CoursewareGenerator
from .teaching_plan import TeachingPlanGenerator
from .teaching_reflection import TeachingReflectionGenerator

__all__ = [
    'LessonPlanGenerator',
    'CoursewareGenerator',
    'TeachingPlanGenerator',
    'TeachingReflectionGenerator'
]
