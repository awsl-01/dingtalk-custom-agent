"""
测试课表搜索（修复后）
"""
import asyncio
import os
import sys

# 强制使用 UTF-8 编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.knowledge_base_v2 import get_knowledge_base


async def test_schedule_search_v2():
    """测试课表搜索（修复后）"""

    # 学校配置
    school_dir = "D:/claude/knowledge/ding3f80869f26d4bb44a39a90f97fcb1e09"
    corp_id = "ding3f80869f26d4bb44a39a90f97fcb1e09"

    # 获取知识库实例
    kb = get_knowledge_base(school_dir, corp_id)

    print("=" * 60)
    print("[INFO] 知识库状态")
    print("=" * 60)
    print(f"分块数量: {len(kb._chunks)}")
    print(f"Embedding 形状: {kb._embeddings.shape if kb._embeddings is not None else 'None'}")

    # 查找系统生成的分块
    system_chunks = [c for c in kb._chunks if c.source_type == 'system']
    print(f"系统生成的分块数: {len(system_chunks)}")

    for i, chunk in enumerate(system_chunks):
        print(f"\n--- 系统分块 {i+1} ---")
        print(f"  chunk_id: {chunk.chunk_id}")
        print(f"  source_id: {chunk.source_id}")
        print(f"  file_name: {chunk.file_name}")
        print(f"  category: {chunk.category}")
        print(f"  text preview: {chunk.text[:200]}...")

    # 测试不同的查询
    queries = [
        "高一(1)班周一数学课",
        "高一(1)班课程表",
        "高一(1)班周一有什么课",
        "第2节是什么课",
    ]

    for query in queries:
        print(f"\n{'='*60}")
        print(f"[查询] {query}")
        print('='*60)

        # 使用语义搜索
        semantic_results = await kb._semantic_search(query, top_k=10)
        print(f"语义搜索结果数: {len(semantic_results)}")

        # 检查是否有系统分块
        system_results = [r for r in semantic_results if r.chunk.source_type == 'system']
        print(f"其中系统分块数: {len(system_results)}")

        for i, result in enumerate(semantic_results[:5]):
            source_tag = "[系统]" if result.chunk.source_type == 'system' else ""
            print(f"\n结果 {i+1} {source_tag}:")
            print(f"  chunk_id: {result.chunk.chunk_id}")
            print(f"  score: {result.score:.4f}")
            print(f"  text preview: {result.chunk.text[:100]}...")

        # 使用关键词搜索
        keyword_results = kb._keyword_search(query, top_k=10)
        print(f"\n关键词搜索结果数: {len(keyword_results)}")

        system_keyword_results = [r for r in keyword_results if r.chunk.source_type == 'system']
        print(f"其中系统分块数: {len(system_keyword_results)}")

        for i, result in enumerate(keyword_results[:3]):
            source_tag = "[系统]" if result.chunk.source_type == 'system' else ""
            print(f"\n结果 {i+1} {source_tag}:")
            print(f"  chunk_id: {result.chunk.chunk_id}")
            print(f"  score: {result.score:.4f}")
            print(f"  highlights: {result.highlights}")


if __name__ == "__main__":
    asyncio.run(test_schedule_search_v2())
