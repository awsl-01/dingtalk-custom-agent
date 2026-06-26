"""
测试课表精确查询
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

from agent.knowledge_base_v2 import get_knowledge_base


async def test_schedule_search():
    """测试课表精确查询"""

    # 学校配置
    school_dir = "D:/claude/knowledge/ding3f80869f26d4bb44a39a90f97fcb1e09"
    corp_id = "ding3f80869f26d4bb44a39a90f97fcb1e09"

    # 获取知识库实例
    kb = get_knowledge_base(school_dir, corp_id)

    # 测试不同的查询
    queries = [
        "高一(1)班周一数学课",
        "高一(1)班周一有什么课",
        "高一(1)班课程表",
        "周一第2节是什么课",
        "数学老师教哪些班级",
    ]

    for query in queries:
        print(f"\n{'='*60}")
        print(f"[查询] {query}")
        print('='*60)

        search_result = await kb.search(
            query,
            top_k=3,
            method="hybrid"
        )

        results = search_result.get("results", []) if isinstance(search_result, dict) else search_result

        print(f"结果数量: {len(results)}")

        for i, r in enumerate(results[:3]):
            print(f"\n--- 结果 {i+1} ---")
            print(f"来源类型: {r.chunk.source_type}")
            print(f"文件名: {r.chunk.file_name or '(无)'}")
            print(f"分类: {r.chunk.category}")
            print(f"相似度: {r.score:.3f}")
            print(f"内容预览:")
            # 显示前300字符
            text_preview = r.chunk.text[:300].replace('\n', '\n  ')
            print(f"  {text_preview}")
            if len(r.chunk.text) > 300:
                print(f"  ... (共{len(r.chunk.text)}字符)")


if __name__ == "__main__":
    asyncio.run(test_schedule_search())
