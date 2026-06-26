"""
PPT Engine 集成模块

将PPT Engine集成到钉钉机器人，支持教育工作流。
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.ppt_engine.project_manager import init_project, import_sources
from agent.ppt_engine.design_spec.strategist import Strategist, create_design_spec
from agent.ppt_engine.design_spec.spec_lock_generator import generate_spec_lock
from agent.ppt_engine.svg_generator.page_builder import PageBuilder
from agent.ppt_engine.svg_to_pptx.pptx_builder import PPTXBuilder
from agent.ppt_engine.quality.svg_quality_checker import SVGQualityChecker
from agent.ppt_engine.svg_finalize.finalize_svg import SVGFinalizer
from agent.ppt_engine.templates.brand_manager import BrandManager
from agent.ppt_engine.templates.layout_manager import LayoutManager
from agent.ppt_engine.workflows.education.lesson_plan import LessonPlanGenerator
from agent.ppt_engine.workflows.education.courseware import CoursewareGenerator
from agent.ppt_engine.workflows.education.teaching_plan import TeachingPlanGenerator
from agent.ppt_engine.workflows.education.teaching_reflection import TeachingReflectionGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class PPTEngineIntegration:
    """PPT Engine集成类"""

    def __init__(self, projects_dir: str = None):
        """
        初始化集成

        参数:
            projects_dir: 项目目录路径
        """
        if projects_dir:
            self.projects_dir = Path(projects_dir)
        else:
            self.projects_dir = Path(__file__).parent.parent / 'projects'

        self.projects_dir.mkdir(parents=True, exist_ok=True)

        # 初始化管理器
        self.brand_manager = BrandManager()
        self.layout_manager = LayoutManager()

    def generate_education_ppt(
        self,
        subject: str,
        grade: str,
        chapter: str,
        content_type: str = '课件',
        difficulty: str = '中等',
        topic: str = ''
    ) -> Tuple[str, str]:
        """
        生成教育PPT

        参数:
            subject: 学科
            grade: 年级
            chapter: 章节
            content_type: 内容类型（教案/课件/说课稿/反思）
            difficulty: 难度
            topic: 主题

        返回:
            (PPT文件路径, PPT标题)
        """
        # 生成项目名称
        project_name = f"{subject}_{grade}_{chapter}_{content_type}"
        project_name = project_name.replace(' ', '_')[:50]

        logger.info(f"[PPT Engine] Start generating: {project_name}")

        try:
            # 1. 创建项目
            project_path = init_project(project_name, 'ppt169')
            logger.info(f"[OK] Project created: {project_path}")

            # 2. 生成教案
            lesson_plan = LessonPlanGenerator().generate(subject, grade, chapter)
            logger.info(f"[OK] Lesson plan generated")

            # 3. 生成课件大纲
            courseware = CoursewareGenerator().generate_from_lesson_plan(lesson_plan)
            logger.info(f"[OK] Courseware outline generated: {len(courseware.pages)} pages")

            # 4. 创建设计规范
            design_spec = create_design_spec(str(project_path), {
                'title': f"{subject} - {chapter}",
                'subtitle': f"{grade} - {content_type}",
                'subject': subject,
                'canvas_format': 'ppt169',
                'page_count': len(courseware.pages),
                'pages': [p.to_dict() for p in courseware.pages]
            })
            logger.info(f"[OK] Design spec created")

            # 5. 生成spec_lock
            spec_lock_path = generate_spec_lock(str(project_path), design_spec)
            logger.info(f"[OK] Spec lock generated")

            # 6. 生成SVG页面
            builder = PageBuilder(str(project_path))
            pages_content = []

            for page in courseware.pages:
                pages_content.append({
                    'title': page.title,
                    'layout': page.layout,
                    'rhythm': page.rhythm,
                    **page.content
                })

            svg_pages = builder.generate_pages(pages_content)
            builder.save_pages(svg_pages)
            logger.info(f"[OK] SVG pages generated: {len(svg_pages)}")

            # 7. 质量检查
            checker = SVGQualityChecker(str(spec_lock_path))
            issues = checker.check_directory(str(project_path / 'svg_output'))
            summary = checker.get_summary(issues)
            logger.info(f"[OK] Quality check: {summary['errors']} errors, {summary['warnings']} warnings")

            # 8. 后处理
            finalizer = SVGFinalizer(str(project_path))
            finalizer.process_all()
            logger.info(f"[OK] SVG finalized")

            # 9. 导出PPTX
            pptx_builder = PPTXBuilder('ppt169')
            output_path = pptx_builder.build_from_svg_dir(
                str(project_path / 'svg_final'),
                str(project_path / 'notes')
            )
            logger.info(f"[OK] PPTX exported: {output_path}")

            # 10. 生成教育文档
            self._generate_education_docs(project_path, subject, grade, chapter, lesson_plan)

            # 获取PPT标题
            ppt_title = f"{subject} - {chapter}"

            return output_path, ppt_title

        except Exception as e:
            logger.error(f"[ERROR] Generate PPT failed: {e}")
            raise

    def _generate_education_docs(
        self,
        project_path: Path,
        subject: str,
        grade: str,
        chapter: str,
        lesson_plan: Any
    ):
        """生成教育文档"""
        notes_dir = project_path / 'notes'
        notes_dir.mkdir(parents=True, exist_ok=True)

        # 生成教案
        lesson_plan_generator = LessonPlanGenerator()
        lesson_plan_generator.save(lesson_plan, str(notes_dir / 'lesson_plan.md'))
        logger.info(f"[OK] Lesson plan saved")

        # 生成说课稿
        teaching_plan = TeachingPlanGenerator().generate_from_lesson_plan(lesson_plan)
        TeachingPlanGenerator().save(teaching_plan, str(notes_dir / 'teaching_plan.md'))
        logger.info(f"[OK] Teaching plan saved")

        # 生成教学反思
        reflection = TeachingReflectionGenerator().generate_from_lesson_plan(lesson_plan)
        TeachingReflectionGenerator().save(reflection, str(notes_dir / 'teaching_reflection.md'))
        logger.info(f"[OK] Teaching reflection saved")

    def generate_from_outline(
        self,
        outline: str,
        subject: str = '',
        grade: str = '',
        chapter: str = ''
    ) -> Tuple[str, str]:
        """
        从大纲生成PPT

        参数:
            outline: Markdown格式大纲
            subject: 学科
            grade: 年级
            chapter: 章节

        返回:
            (PPT文件路径, PPT标题)
        """
        # 解析大纲
        pages = self._parse_outline(outline)

        # 生成项目名称
        project_name = f"outline_{subject}_{chapter}"
        project_name = project_name.replace(' ', '_')[:50]

        logger.info(f"[PPT Engine] Start generating from outline: {project_name}")

        try:
            # 1. 创建项目
            project_path = init_project(project_name, 'ppt169')

            # 2. 创建设计规范
            design_spec = create_design_spec(str(project_path), {
                'title': chapter or 'PPT',
                'subtitle': f"{grade} - {subject}",
                'subject': subject,
                'canvas_format': 'ppt169',
                'page_count': len(pages),
                'pages': pages
            })

            # 3. 生成spec_lock
            spec_lock_path = generate_spec_lock(str(project_path), design_spec)

            # 4. 生成SVG页面
            builder = PageBuilder(str(project_path))
            svg_pages = builder.generate_pages(pages)
            builder.save_pages(svg_pages)

            # 5. 质量检查
            checker = SVGQualityChecker(str(spec_lock_path))
            issues = checker.check_directory(str(project_path / 'svg_output'))

            # 6. 后处理
            finalizer = SVGFinalizer(str(project_path))
            finalizer.process_all()

            # 7. 导出PPTX
            pptx_builder = PPTXBuilder('ppt169')
            output_path = pptx_builder.build_from_svg_dir(
                str(project_path / 'svg_final')
            )

            ppt_title = chapter or 'PPT'
            return output_path, ppt_title

        except Exception as e:
            logger.error(f"[ERROR] Generate PPT from outline failed: {e}")
            raise

    def _parse_outline(self, outline: str) -> List[Dict[str, Any]]:
        """解析Markdown大纲为页面列表"""
        pages = []
        current_page = None

        for line in outline.split('\n'):
            line = line.strip()

            # 一级标题作为页面标题
            if line.startswith('# ') and not line.startswith('## '):
                if current_page:
                    pages.append(current_page)

                title = line[2:].strip()
                current_page = {
                    'title': title,
                    'layout': 'cover' if len(pages) == 0 else 'content',
                    'rhythm': 'anchor' if len(pages) == 0 else 'dense',
                    'content': {'title': title, 'body': '', 'bullets': []}
                }

            # 二级标题作为要点
            elif line.startswith('## ') or line.startswith('### '):
                if current_page:
                    title = line.lstrip('#').strip()
                    current_page['content']['bullets'].append(title)

            # 列表项作为要点
            elif line.startswith('- ') or line.startswith('* '):
                if current_page:
                    item = line[2:].strip()
                    current_page['content']['bullets'].append(item)

            # 普通文本作为内容
            elif line and current_page:
                if current_page['content']['body']:
                    current_page['content']['body'] += '\n'
                current_page['content']['body'] += line

        # 添加最后一个页面
        if current_page:
            pages.append(current_page)

        # 如果没有解析到页面，创建默认页面
        if not pages:
            pages = [
                {'title': '封面', 'layout': 'cover', 'rhythm': 'anchor',
                 'content': {'title': 'PPT', 'subtitle': ''}},
                {'title': '内容', 'layout': 'content', 'rhythm': 'dense',
                 'content': {'title': '内容', 'body': outline[:500]}},
                {'title': '结束', 'layout': 'ending', 'rhythm': 'breathing',
                 'content': {'title': '谢谢', 'subtitle': ''}}
            ]

        # 添加结束页
        if pages and pages[-1]['layout'] != 'ending':
            pages.append({
                'title': '结束',
                'layout': 'ending',
                'rhythm': 'breathing',
                'content': {'title': '谢谢', 'subtitle': ''}
            })

        return pages

    def list_subjects(self) -> List[str]:
        """列出支持的学科"""
        return list(BrandManager.SUBJECT_BRANDS.keys())

    def list_content_types(self) -> List[str]:
        """列出支持的内容类型"""
        return ['教案', '课件', '说课稿', '反思']


# 全局实例
_integration = None


def get_integration() -> PPTEngineIntegration:
    """获取集成实例"""
    global _integration
    if _integration is None:
        _integration = PPTEngineIntegration()
    return _integration


def generate_education_ppt(
    subject: str,
    grade: str,
    chapter: str,
    content_type: str = '课件',
    difficulty: str = '中等',
    topic: str = ''
) -> Tuple[str, str]:
    """
    生成教育PPT（便捷函数）

    参数:
        subject: 学科
        grade: 年级
        chapter: 章节
        content_type: 内容类型
        difficulty: 难度
        topic: 主题

    返回:
        (PPT文件路径, PPT标题)
    """
    integration = get_integration()
    return integration.generate_education_ppt(
        subject, grade, chapter, content_type, difficulty, topic
    )


def generate_from_outline(
    outline: str,
    subject: str = '',
    grade: str = '',
    chapter: str = ''
) -> Tuple[str, str]:
    """
    从大纲生成PPT（便捷函数）

    参数:
        outline: Markdown格式大纲
        subject: 学科
        grade: 年级
        chapter: 章节

    返回:
        (PPT文件路径, PPT标题)
    """
    integration = get_integration()
    return integration.generate_from_outline(outline, subject, grade, chapter)
