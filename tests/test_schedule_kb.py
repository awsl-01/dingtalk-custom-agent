"""
测试排课系统课表存入知识库
"""
import asyncio
import json
import os
import sys

# 强制使用 UTF-8 编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.knowledge_base_v2 import get_knowledge_base, classify_text, extract_entity_key


async def test_schedule_to_kb():
    """测试将排课系统生成的课表存入知识库"""

    # 学校配置
    school_dir = "D:/claude/knowledge/ding3f80869f26d4bb44a39a90f97fcb1e09"
    corp_id = "ding3f80869f26d4bb44a39a90f97fcb1e09"

    # 获取知识库实例
    kb = get_knowledge_base(school_dir, corp_id)

    # 加载排课数据
    schedule_file = os.path.join(school_dir, "scheduling", "schedule_result.json")
    data_file = os.path.join(school_dir, "scheduling", "scheduling_data.json")

    if not os.path.exists(schedule_file) or not os.path.exists(data_file):
        print("[ERROR] 排课数据不存在")
        return

    with open(schedule_file, 'r', encoding='utf-8') as f:
        schedule_data = json.load(f)

    with open(data_file, 'r', encoding='utf-8') as f:
        scheduling_data = json.load(f)

    # 测试：为高一(1)班生成课表文本
    class_id = "class_01"
    class_name = "高一(1)班"

    # 查找该班级的所有课程
    class_entries = [e for e in schedule_data.get('entries', []) if e.get('class_id') == class_id]

    if not class_entries:
        print(f"[ERROR] 未找到 {class_name} 的课程数据")
        return

    print(f"[OK] 找到 {class_name} 的 {len(class_entries)} 节课")

    # 生成课表文本（Markdown 表格格式）
    weekdays = ['周一', '周二', '周三', '周四', '周五']
    periods = ['第1节', '第2节', '第3节', '第4节', '第5节', '第6节', '第7节', '第8节']

    # 创建课表字典
    schedule_dict = {}
    for entry in class_entries:
        weekday = entry['time_slot']['weekday']
        period = f"第{entry['time_slot']['period']}节"
        course_id = entry['course_id']
        teacher_id = entry.get('teacher_id', '')
        classroom_id = entry.get('classroom_id', '')

        # 获取课程名称
        course_name = course_id
        for c in scheduling_data.get('courses', []):
            if c['id'] == course_id:
                course_name = c.get('name', course_id)
                break

        # 获取教师名称
        teacher_name = ""
        for t in scheduling_data.get('teachers', []):
            if t['id'] == teacher_id:
                teacher_name = t.get('name', '')
                break

        # 获取教室名称
        classroom_name = ""
        for r in scheduling_data.get('classrooms', []):
            if r['id'] == classroom_id:
                classroom_name = r.get('name', '')
                break

        if weekday not in schedule_dict:
            schedule_dict[weekday] = {}

        # 格式：课程(教师@教室)
        cell = course_name
        if teacher_name:
            cell += f"({teacher_name}"
            if classroom_name:
                cell += f"@{classroom_name}"
            cell += ")"

        schedule_dict[weekday][period] = cell

    # 生成 Markdown 表格
    schedule_text = f"【{class_name} 课程表】\n\n"
    schedule_text += "| 节次 | 周一 | 周二 | 周三 | 周四 | 周五 |\n"
    schedule_text += "|------|------|------|------|------|------|\n"

    for period in periods:
        row = [period]
        for weekday in weekdays:
            cell = schedule_dict.get(weekday, {}).get(period, "")
            row.append(cell)
        schedule_text += "| " + " | ".join(row) + " |\n"

    print("\n[INFO] 生成的课表文本：")
    print(schedule_text[:500])
    print("...\n")

    # 测试分类
    category = classify_text(schedule_text)
    print(f"[INFO] 文本分类结果: {category}")

    # 测试实体键提取
    entity_key = extract_entity_key(schedule_text, category)
    print(f"[INFO] 实体键: {entity_key}")

    # 存入知识库
    print("\n[INFO] 正在存入知识库...")
    try:
        chunks = await kb.add_message(
            schedule_text,
            source_type="system",
            source_id=f"schedule_{class_id}",
            file_name=f"{class_name}课程表",
        )
        print(f"[OK] 成功存入 {len(chunks)} 个分块")
    except Exception as e:
        print(f"[ERROR] 存入失败: {e}")
        import traceback
        traceback.print_exc()

    # 验证：从知识库搜索
    print("\n[INFO] 验证：搜索知识库...")
    search_result = await kb.search(
        f"{class_name} 周一 数学",
        top_k=5,
        method="hybrid"
    )

    results = search_result.get("results", []) if isinstance(search_result, dict) else search_result

    print(f"搜索结果数量: {len(results)}")
    for i, r in enumerate(results[:3]):
        print(f"\n结果 {i+1}:")
        print(f"  来源: {r.chunk.source_type}")
        print(f"  文件: {r.chunk.file_name}")
        print(f"  内容预览: {r.chunk.text[:150]}...")


if __name__ == "__main__":
    asyncio.run(test_schedule_to_kb())
