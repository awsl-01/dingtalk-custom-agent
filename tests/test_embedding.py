"""
测试 Embedding 生成
"""
import asyncio
import os
import sys

# 强制使用 UTF-8 编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.knowledge_base_v2 import get_embeddings, _get_local_embedding_model


async def test_embedding():
    """测试 Embedding 生成"""

    # 测试文本
    test_texts = [
        "【高一(1)班 课程表】",
        "| 节次 | 周一 | 周二 | 周三 | 周四 | 周五 |",
        "| 第1节 | 高一语文(李老师@101教室) | 高一数学(数学老师4@104教室) |",
    ]

    print("=" * 60)
    print("[INFO] 测试 Embedding 生成")
    print("=" * 60)

    # 检查本地模型
    model = _get_local_embedding_model()
    if model is not None:
        print("[OK] 本地 Embedding 模型已加载")
    else:
        print("[WARNING] 本地 Embedding 模型未加载")

    # 生成 embeddings
    print("\n[INFO] 生成 embeddings...")
    embeddings = await get_embeddings(test_texts, use_cache=False)

    if embeddings is not None:
        print(f"[OK] 成功生成 embeddings")
        print(f"  形状: {embeddings.shape}")
        print(f"  数据类型: {embeddings.dtype}")
        for i, emb in enumerate(embeddings):
            print(f"  文本 {i+1} 的 embedding: 均值={emb.mean():.6f}, 标准差={emb.std():.6f}")
    else:
        print("[ERROR] 生成 embeddings 失败")

    # 测试长文本
    print("\n[INFO] 测试长文本 embedding...")
    long_text = """【高一(1)班 课程表】

| 节次 | 周一 | 周二 | 周三 | 周四 | 周五 |
|------|------|------|------|------|------|
| 第1节 | 高一语文(李老师@101教室) | 高一语文(语文老师4@106教室) | 高一语文(陈老师@通用技术教室) | 高一数学(刘老师@105教室) | 高一数学(刘老师@美术教室) |
| 第2节 | 高一数学(数学老师4@104教室) | 高一数学(数学老师4@107教室) | 高一数学(数学老师4@美术教室) | 高一语文(语文老师4@103教室) | 高一英语(英语老师4@108教室) |"""

    long_embedding = await get_embeddings([long_text], use_cache=False)
    if long_embedding is not None:
        print(f"[OK] 长文本 embedding 生成成功")
        print(f"  形状: {long_embedding.shape}")
    else:
        print("[ERROR] 长文本 embedding 生成失败")


if __name__ == "__main__":
    asyncio.run(test_embedding())
