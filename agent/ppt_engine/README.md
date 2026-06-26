# PPT Engine - 专业级PPT生成引擎

对标ppt-master完整能力，保留教育场景优势。

## 功能概览

### 已实现功能（6个阶段，全部完成）

| 阶段 | 功能 | 状态 |
|------|------|------|
| 第一阶段 | 项目管理、源文件处理、SVG生成、SVG转PPTX | ✅ 完成 |
| 第二阶段 | 设计规范、模板系统、布局模板库 | ✅ 完成 |
| 第三阶段 | AI图片生成、网络图片搜索、LaTeX公式渲染 | ✅ 完成 |
| 第四阶段 | 动画系统、实时预览 | ✅ 完成 |
| 第五阶段 | 质量检查、TTS音频、后处理流水线 | ✅ 完成 |
| 第六阶段 | 学科模板迁移、教育专项Workflow | ✅ 完成 |

## 模块结构

```
agent/ppt_engine/
├── __init__.py
├── project_manager.py          # 项目管理
├── source_converter/           # 源文件处理
│   ├── base_converter.py
│   ├── pdf_converter.py
│   ├── docx_converter.py
│   ├── html_converter.py
│   ├── excel_converter.py
│   ├── web_converter.py
│   └── source_to_md.py
├── svg_generator/              # SVG生成引擎
│   ├── base_generator.py
│   ├── page_builder.py
│   └── spec_lock_reader.py
├── svg_to_pptx/                # SVG转PPTX
│   ├── drawingml_converter.py
│   ├── pptx_builder.py
│   └── pptx_cli.py
├── design_spec/                # 设计规范
│   ├── strategist.py
│   └── spec_lock_generator.py
├── templates/                  # 模板系统
│   ├── brand_manager.py
│   ├── layout_manager.py
│   └── deck_manager.py
├── image_gen/                  # AI图片生成
│   └── image_generator.py
├── image_search/               # 网络图片搜索
│   └── image_searcher.py
├── latex_render/               # LaTeX公式渲染
│   └── latex_renderer.py
├── animations/                 # 动画系统
│   ├── transition_effects.py
│   └── entrance_animations.py
├── svg_editor/                 # 实时预览
│   └── server.py
├── quality/                    # 质量检查
│   └── svg_quality_checker.py
├── svg_finalize/               # 后处理流水线
│   └── finalize_svg.py
├── tts/                        # TTS音频
│   └── tts_generator.py
└── workflows/                  # 工作流
    └── education/
        ├── lesson_plan.py      # 教案生成
        ├── courseware.py        # 课件大纲
        ├── teaching_plan.py     # 说课稿
        └── teaching_reflection.py # 教学反思
```

## 功能详情

### 1. 项目管理

- 创建项目目录结构
- 导入源文件（支持移动/复制）
- 验证项目结构
- 查询项目信息

```python
from agent.ppt_engine.project_manager import init_project, import_sources

# 创建项目
project_dir = init_project('my_project', 'ppt169')

# 导入源文件
import_sources(str(project_dir), ['source.pdf', 'source.docx'])
```

### 2. 源文件处理

支持格式：
- PDF (PyMuPDF)
- DOCX (mammoth)
- HTML (markdownify + BeautifulSoup)
- EPUB (ebooklib)
- Excel (openpyxl)
- Web页面 (requests/curl_cffi)

```python
from agent.ppt_engine.source_converter import convert_source

# 转换PDF
result = convert_source('document.pdf', 'output/')

# 转换网页
result = convert_source('https://example.com', 'output/')
```

### 3. SVG生成引擎

- 逐页手写SVG，保证跨页视觉一致性
- 每页生成前重读spec_lock，抵抗上下文漂移
- 支持多种布局（封面、目录、内容、卡片等）

```python
from agent.ppt_engine.svg_generator import PageBuilder

builder = PageBuilder('project_path')
page = builder.generate_page(1, {
    'title': '封面',
    'layout': 'cover',
    'subtitle': '副标题'
})
```

### 4. 模板系统

三层架构：
- **brand**: 品牌标识（颜色/字体/Logo）
- **layout**: 布局结构（页面类型/SVG模板）
- **deck**: 完整套牌（brand + layout + 内容）

预设品牌：15个（5通用 + 10学科）
预设布局：28个（10通用 + 18学科）
预设套牌：4个

```python
from agent.ppt_engine.templates import BrandManager, LayoutManager

# 获取学科品牌
brand_manager = BrandManager()
math_brand = brand_manager.get_brand('math')

# 获取学科布局
layout_manager = LayoutManager()
math_layouts = layout_manager.get_subject_layouts('math')
```

### 5. AI图片生成

支持后端：
- Gemini (google-genai)
- OpenAI (dall-e-3)
- Qwen (wanx-v1)
- Zhipu (cogview-3)

```python
from agent.ppt_engine.image_gen import ImageGenerator, ImageRequest

generator = ImageGenerator()
result = generator.generate(
    ImageRequest(prompt="A classroom scene", filename="classroom.png"),
    "output/"
)
```

### 6. 网络图片搜索

支持Provider：
- Openverse (CC授权)
- Wikimedia (公共领域)
- Pexels (免费授权)
- Pixabay (免费授权)

```python
from agent.ppt_engine.image_search import ImageSearcher, SearchRequest

searcher = ImageSearcher()
result = searcher.search_and_download(
    SearchRequest(query="mountain landscape"),
    "output/"
)
```

### 7. LaTeX公式渲染

支持Provider链：
- codecogs (默认)
- quicklatex
- mathpad
- wikimedia (备用)

```python
from agent.ppt_engine.latex_render import LaTeXRenderer, FormulaRequest

renderer = LaTeXRenderer()
result = renderer.render(
    FormulaRequest(formula="E = mc^2"),
    "output/"
)
```

### 8. 动画系统

转场效果：fade, push, wipe, split, strips, cover, random
入场动画：appear, fade, fly, zoom, wipe, dissolve, box, circle, diamond, wheel

```python
from agent.ppt_engine.animations import TransitionEffect, EntranceAnimation

# 创建转场
transition = TransitionEffect('fade')
xml = transition.to_xml()

# 创建入场动画
animation = EntranceAnimation('auto')
xml = animation.to_xml(shape_id=100)
```

### 9. 实时预览

Flask Web服务器，提供SVG实时预览和标注功能。

```python
from agent.ppt_engine.svg_editor import run_server

run_server('project_path', port=5050, live=True)
```

### 10. 质量检查

检查规则：
- viewBox完整性
- 禁止特性（外部引用、JS）
- 颜色漂移
- 字号范围
- 动画分组
- 图片引用
- 文本溢出

```python
from agent.ppt_engine.quality import SVGQualityChecker

checker = SVGQualityChecker('spec_lock.md')
issues = checker.check_directory('svg_output/')
summary = checker.get_summary(issues)
```

### 11. TTS音频生成

支持后端：
- Edge-TTS (默认，无需API Key)
- ElevenLabs
- MiniMax
- Qwen
- CosyVoice

```python
from agent.ppt_engine.tts import TTSGenerator, AudioRequest

generator = TTSGenerator()
result = generator.generate(
    AudioRequest(text="Hello World", voice="zh-CN-XiaoxiaoNeural"),
    "output/"
)
```

### 12. 教育专项Workflow

支持教育场景：
- 教案生成 (lesson_plan)
- 课件大纲 (courseware)
- 说课稿 (teaching_plan)
- 教学反思 (teaching_reflection)

```python
from agent.ppt_engine.workflows.education import (
    LessonPlanGenerator,
    CoursewareGenerator,
    TeachingPlanGenerator,
    TeachingReflectionGenerator
)

# 生成教案
plan = LessonPlanGenerator().generate('数学', '高一', '三角函数')

# 生成课件大纲
courseware = CoursewareGenerator().generate_from_lesson_plan(plan)

# 生成说课稿
teaching_plan = TeachingPlanGenerator().generate_from_lesson_plan(plan)

# 生成教学反思
reflection = TeachingReflectionGenerator().generate_from_lesson_plan(plan)
```

## 依赖安装

```bash
pip install python-pptx PyMuPDF mammoth markdownify ebooklib openpyxl
pip install requests beautifulsoup4 svglib reportlab
pip install google-genai openai Pillow numpy flask edge-tts
```

## 测试

```bash
# 运行所有测试
python tests/test_ppt_engine.py
python tests/test_ppt_engine_phase2.py
python tests/test_ppt_engine_phase3.py
python tests/test_ppt_engine_phase4.py
python tests/test_ppt_engine_phase5.py
python tests/test_ppt_engine_phase6.py
```

## 与ppt-master对比

| 功能 | ppt-master | PPT Engine | 状态 |
|------|------------|------------|------|
| 源文件处理 | ✅ | ✅ | 完成 |
| 设计质量 | ✅ | ✅ | 完成 |
| 模板系统 | ✅ | ✅ | 完成 |
| 学科适配 | ❌ | ✅ | 优势 |
| 页面布局 | ✅ | ✅ | 完成 |
| 动画效果 | ✅ | ✅ | 完成 |
| 实时预览 | ✅ | ✅ | 完成 |
| 质量检查 | ✅ | ✅ | 完成 |
| 演讲备注 | ✅ | ✅ | 完成 |
| 图片处理 | ✅ | ✅ | 完成 |
| LaTeX公式 | ✅ | ✅ | 完成 |
| 教育场景 | ❌ | ✅ | 优势 |

## 许可证

内部项目，仅供学校AI助手使用。
