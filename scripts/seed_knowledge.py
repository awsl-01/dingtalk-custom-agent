"""
预置结构化知识到知识库

将排课系统使用说明、课表查询方法、知识库使用指南等
作为系统知识写入知识库，确保用户提问时能检索到正确的使用说明。
"""
import os
import sys
import asyncio
import json
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.knowledge_base_v2 import get_knowledge_base, compute_content_hash

# 设置 UTF-8 输出
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# ========== 预置知识内容 ==========

SEED_KNOWLEDGE = [
    # ── 排课系统使用指南 ──
    {
        "text": """【排课系统使用指南】

排课系统支持自动排课、冲突检测、课表优化等功能。

使用步骤：
1. 发送「排课模板」获取 Excel 模板
2. 下载并填写模板（班级信息、教师信息、课程信息、教室信息）
3. 将填写好的 Excel 文件发送给我
4. 发送「开始排课」执行自动排课

也可以直接发送文字格式的数据，例如：
班级：高一(1)班、高一(2)班
教师：张老师(数学)、李老师(语文)
课程：数学(5课时/周)、语文(5课时/周)

教室分配：
在 Excel 模板的「班级信息」表中，有一列「固定教室」，可以指定每个班级使用的教室。
例如：高一(1)班 固定教室填 101教室,102教室
这样排课时该班级会优先使用 101 和 102 教室。
如果不填，系统会自动分配空闲教室。

排课完成后可用的命令：
- 查看课表 高一(1)班 — 查看指定班级课表
- 优化课表 — 优化课表质量
- 导出课表 — 导出为 Excel 文件""",
        "source_type": "system",
        "source_id": "seed_scheduling_guide",
        "tags": ["排课", "使用指南", "系统功能"],
    },
    # ── 课表查询指南 ──
    {
        "text": """【课表查询方法】

支持多种查询方式：

按班级查询：
- 高一(1)班课表
- 查看高一(1)班的课程表

按日期查询：
- 高一(1)班周一有什么课
- 周三第3-4节是什么课

按教师查询：
- 张老师的课表
- 数学老师本周课表

按教室查询：
- 102教室今天有什么课
- 实验室的课程安排

按科目查询：
- 高一(1)班数学课安排
- 英语课都在什么时候

返回结果包含：课程名称、授课教师、上课教室、节次信息。
如果排课系统已生成课表，会优先使用排课系统的结果。
如果排课系统没有结果，会从知识库中搜索相关的课表文件。""",
        "source_type": "system",
        "source_id": "seed_schedule_query_guide",
        "tags": ["课表", "查询", "使用指南"],
    },
    # ── 调课操作指南 ──
    {
        "text": """【调课操作指南】

调课方式：
1. 按节次调课：高一(1)班周一第1节和周三第3节调课
2. 按科目调课：高一(1)班周一数学课和周三物理课调换
3. 教师调课：张老师周一第1节和周三第1节调课
4. 临时调课：临时调课 高一(1)班周一和周三调换

调课规则：
- 需要指定两天和对应的节次或科目
- 永久调课会修改课表数据
- 临时调课只做记录，不修改课表
- 调课后会自动生成调课通知

注意事项：
- 调课前请确认教师时间是否冲突
- 调课后受影响的教师会收到通知
- 调课记录保存在调课日志中，可以查询历史""",
        "source_type": "system",
        "source_id": "seed_swap_guide",
        "tags": ["调课", "换课", "操作指南"],
    },
    # ── 知识库使用指南 ──
    {
        "text": """【知识库功能说明】

知识库可以自动存储和检索学校的各种信息。

支持存储的内容：
- 文本消息：老师之间的交流内容
- 图片：拍照上传的文档、课件等（自动OCR识别）
- 文件：Word、Excel、PPT、PDF、TXT等文档
- 课表：排课系统生成的课表数据

支持的查询方式：
- 直接提问：学校有什么通知
- 关键词搜索：搜索 课程安排
- 文件查询：查找 XXX文件

自动存储规则：
- 有实质内容的消息会自动存入知识库
- 简单的确认、感谢等消息不会存储
- 上传的文件会自动提取文字并存储
- 图片会自动OCR识别后存储

使用技巧：
- 上传文件后，文件内容会被自动索引
- 可以用自然语言提问，系统会从知识库中检索相关信息
- 知识库支持按时间、来源、类别等条件筛选""",
        "source_type": "system",
        "source_id": "seed_kb_guide",
        "tags": ["知识库", "使用指南", "系统功能"],
    },
    # ── PPT生成指南 ──
    {
        "text": """【PPT课件生成指南】

PPT生成功能可以自动生成教学课件。

使用方法：
- 帮我生成一个XX主题的PPT
- 制作一个关于XX的教学课件
- 生成XX年级XX学科的幻灯片

支持的参数：
- 主题：如"光合作用"、"二次函数"
- 学科：语文、数学、英语、物理、化学等
- 年级：小学、初中、高中各年级
- 页数：默认10-15页，可以指定

生成流程：
1. 系统根据主题生成PPT大纲
2. 用户确认或修改大纲
3. 确认后自动生成PPT文件
4. 生成完成后发送PPT文件

注意事项：
- PPT生成约需1-2分钟
- 可以在确认前修改大纲内容
- 生成的PPT包含标题页、目录、正文、总结等""",
        "source_type": "system",
        "source_id": "seed_ppt_guide",
        "tags": ["PPT", "课件", "生成", "使用指南"],
    },
]


async def seed_knowledge(kb_dir: str, corp_id: str):
    """
    将预置知识写入知识库

    参数:
        kb_dir: 学校知识库目录
        corp_id: 企业ID
    """
    kb = get_knowledge_base(kb_dir, corp_id)

    # 检查是否已经预置过
    existing_ids = set()
    for chunk in kb._chunks:
        if chunk.source_id and chunk.source_id.startswith('seed_'):
            existing_ids.add(chunk.source_id)

    added_count = 0
    skipped_count = 0

    for item in SEED_KNOWLEDGE:
        source_id = item["source_id"]

        # 跳过已存在的
        if source_id in existing_ids:
            print(f"  ⏭️ 已存在: {source_id}")
            skipped_count += 1
            continue

        # 写入知识库
        chunks = await kb.add_message(
            text=item["text"],
            source_type=item["source_type"],
            source_id=source_id,
            tags=item.get("tags", []),
        )

        if chunks:
            print(f"  ✅ 已添加: {source_id} ({len(chunks)} 个分块)")
            added_count += 1
        else:
            print(f"  ⚠️ 添加失败或被过滤: {source_id}")

    print(f"\n📊 结果: 新增 {added_count} 条, 跳过 {skipped_count} 条")
    print(f"   知识库当前共 {len(kb._chunks)} 个分块")


async def main():
    """主函数"""
    knowledge_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'knowledge')

    if not os.path.exists(knowledge_dir):
        print(f"❌ 未找到知识库目录: {knowledge_dir}")
        return

    # 查找所有学校
    schools = [d for d in os.listdir(knowledge_dir)
               if os.path.isdir(os.path.join(knowledge_dir, d))]

    if not schools:
        print("❌ 未找到任何学校数据")
        return

    for school_id in schools:
        print(f"\n{'='*60}")
        print(f"  预置知识: {school_id}")
        print(f"{'='*60}")

        kb_dir = os.path.join(knowledge_dir, school_id)
        await seed_knowledge(kb_dir, school_id)


if __name__ == '__main__':
    asyncio.run(main())
