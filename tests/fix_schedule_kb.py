"""
修复课表知识库：为缺失 embedding 的分块重新生成 embedding
"""
import asyncio
import os
import sys
import numpy as np

# 强制使用 UTF-8 编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.knowledge_base_v2 import get_knowledge_base, get_embeddings


async def fix_schedule_kb():
    """修复课表知识库"""

    # 学校配置
    school_dir = "D:/claude/knowledge/ding3f80869f26d4bb44a39a90f97fcb1e09"
    corp_id = "ding3f80869f26d4bb44a39a90f97fcb1e09"

    # 获取知识库实例
    kb = get_knowledge_base(school_dir, corp_id)

    print("=" * 60)
    print("[INFO] 修复前的状态")
    print("=" * 60)
    print(f"分块数量: {len(kb._chunks)}")
    print(f"Embedding 形状: {kb._embeddings.shape if kb._embeddings is not None else 'None'}")

    # 检查分块和 embedding 的对应关系
    if kb._embeddings is not None and len(kb._chunks) != kb._embeddings.shape[0]:
        print(f"\n[WARNING] 分块数 ({len(kb._chunks)}) 和 Embedding 数 ({kb._embeddings.shape[0]}) 不匹配!")

        # 找出缺失 embedding 的分块
        missing_indices = []
        for i in range(len(kb._chunks)):
            if i >= kb._embeddings.shape[0]:
                missing_indices.append(i)

        print(f"缺失 embedding 的分块索引: {missing_indices}")

        # 获取这些分块的文本
        missing_texts = [kb._chunks[i].text for i in missing_indices]
        print(f"缺失 embedding 的分块数量: {len(missing_texts)}")

        # 生成新的 embeddings
        print("\n[INFO] 为缺失的分块生成 embedding...")
        new_embeddings = await get_embeddings(missing_texts, use_cache=False)

        if new_embeddings is not None:
            print(f"[OK] 成功生成 {new_embeddings.shape[0]} 个 embedding")

            # 合并 embeddings
            kb._embeddings = np.vstack([kb._embeddings, new_embeddings])
            print(f"[OK] 合并后的 Embedding 形状: {kb._embeddings.shape}")

            # 保存索引
            kb._save_index()
            print("[OK] 索引已保存")
        else:
            print("[ERROR] 生成 embedding 失败")
            return

    # 验证修复结果
    print("\n" + "=" * 60)
    print("[INFO] 修复后的状态")
    print("=" * 60)
    print(f"分块数量: {len(kb._chunks)}")
    print(f"Embedding 形状: {kb._embeddings.shape if kb._embeddings is not None else 'None'}")

    if kb._embeddings is not None and len(kb._chunks) == kb._embeddings.shape[0]:
        print("[OK] 分块数和 Embedding 数匹配!")
    else:
        print("[ERROR] 修复失败!")

    # 测试搜索
    print("\n" + "=" * 60)
    print("[INFO] 测试搜索")
    print("=" * 60)

    query = "高一(1)班周一数学课"
    print(f"查询: {query}")

    search_result = await kb.search(
        query,
        top_k=5,
        method="hybrid"
    )

    results = search_result.get("results", []) if isinstance(search_result, dict) else search_result

    print(f"搜索结果数: {len(results)}")

    for i, result in enumerate(results[:5]):
        print(f"\n结果 {i+1}:")
        print(f"  chunk_id: {result.chunk.chunk_id}")
        print(f"  source_type: {result.chunk.source_type}")
        print(f"  score: {result.score:.4f}")
        print(f"  text preview: {result.chunk.text[:150]}...")


if __name__ == "__main__":
    asyncio.run(fix_schedule_kb())
