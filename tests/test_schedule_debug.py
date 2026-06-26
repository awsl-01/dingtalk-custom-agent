"""
调试课表存入和搜索问题
"""
import asyncio
import json
import os
import sys
import numpy as np

# 强制使用 UTF-8 编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.knowledge_base_v2 import get_knowledge_base, KnowledgeBase


async def test_schedule_debug():
    """调试课表存入和搜索问题"""

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
        print(f"  text preview: {chunk.text[:150]}...")

    # 检查这些分块的 embedding
    print("\n" + "=" * 60)
    print("[INFO] 检查 Embedding")
    print("=" * 60)

    if kb._embeddings is not None:
        # 查找系统分块的索引
        for i, chunk in enumerate(kb._chunks):
            if chunk.source_type == 'system':
                if i < len(kb._embeddings):
                    embedding = kb._embeddings[i]
                    print(f"分块 {chunk.chunk_id} 的 embedding:")
                    print(f"  形状: {embedding.shape}")
                    print(f"  均值: {np.mean(embedding):.6f}")
                    print(f"  标准差: {np.std(embedding):.6f}")
                    print(f"  前5个值: {embedding[:5]}")
                else:
                    print(f"分块 {chunk.chunk_id} 没有对应的 embedding!")

    # 测试搜索
    print("\n" + "=" * 60)
    print("[INFO] 测试搜索")
    print("=" * 60)

    query = "高一(1)班周一数学课"
    print(f"查询: {query}")

    # 使用语义搜索
    print("\n--- 语义搜索 ---")
    semantic_results = await kb._semantic_search(query, top_k=10)
    print(f"语义搜索结果数: {len(semantic_results)}")

    for i, result in enumerate(semantic_results[:5]):
        print(f"\n结果 {i+1}:")
        print(f"  chunk_id: {result.chunk.chunk_id}")
        print(f"  source_type: {result.chunk.source_type}")
        print(f"  score: {result.score:.4f}")
        print(f"  text preview: {result.chunk.text[:100]}...")

    # 使用关键词搜索
    print("\n--- 关键词搜索 ---")
    keyword_results = kb._keyword_search(query, top_k=10)
    print(f"关键词搜索结果数: {len(keyword_results)}")

    for i, result in enumerate(keyword_results[:5]):
        print(f"\n结果 {i+1}:")
        print(f"  chunk_id: {result.chunk.chunk_id}")
        print(f"  source_type: {result.chunk.source_type}")
        print(f"  score: {result.score:.4f}")
        print(f"  highlights: {result.highlights}")
        print(f"  text preview: {result.chunk.text[:100]}...")

    # 使用混合搜索
    print("\n--- 混合搜索 ---")
    hybrid_results = await kb._hybrid_search(query, top_k=10)
    print(f"混合搜索结果数: {len(hybrid_results)}")

    for i, result in enumerate(hybrid_results[:5]):
        print(f"\n结果 {i+1}:")
        print(f"  chunk_id: {result.chunk.chunk_id}")
        print(f"  source_type: {result.chunk.source_type}")
        print(f"  score: {result.score:.4f}")
        print(f"  match_type: {result.match_type}")
        print(f"  text preview: {result.chunk.text[:100]}...")


if __name__ == "__main__":
    asyncio.run(test_schedule_debug())
