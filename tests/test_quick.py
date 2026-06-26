"""
快速测试
"""
import os
import sys
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.template_design_ppt import TemplateDesignPPTGenerator

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 测试
template_path = "templates/default_template.pptx"
output_dir = "test_output"

os.makedirs(output_dir, exist_ok=True)

generator = TemplateDesignPPTGenerator(template_path)

# 简单测试内容
test_data = {
    "title": "测试PPT",
    "subtitle": "用于验证修复",
    "slides": [
        {
            "title": "第一章 概述",
            "content": ["要点1", "要点2", "要点3"],
            "layout_type": "chapter"
        },
        {
            "title": "核心内容",
            "content": ["详细说明1", "详细说明2", "详细说明3"],
            "layout_type": "content"
        },
        {
            "title": "总结",
            "content": ["总结要点1", "总结要点2"],
            "layout_type": "content"
        }
    ]
}

# 手动生成
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

generator._init_design_gene()

prs = Presentation()
prs.slide_width = Inches(generator.gene.slide_width)
prs.slide_height = Inches(generator.gene.slide_height)

# 创建封面
generator._create_cover_slide(prs, test_data)

# 创建内容页
from agent.template_design_ppt import SlideContent

for i, slide_data in enumerate(test_data["slides"]):
    layout_type = generator._map_layout_type(slide_data.get("layout_type", "content"))
    content = SlideContent(
        title=slide_data["title"],
        content=slide_data["content"],
        layout_type=layout_type
    )
    generator.slide_builder.build_slide(prs, content, i + 2)

# 创建结束页
generator._create_ending_slide(prs)

# 最终自查
generator._final_check(prs)

# 保存
output_path = os.path.join(output_dir, "quick_test.pptx")
prs.save(output_path)

print(f"\n生成成功: {output_path}")
