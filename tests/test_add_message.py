"""
测试 add_message 方法
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

from agent.knowledge_base_v2 import get_knowledge_base


async def test_add_message():
    """测试 add_message 方法"""

    # 学校配置
    school_dir = "D:/claude/knowledge/ding3f80869f26d4bb44a39a90f97fcb1e09"
    corp_id = "ding3f80869f26d4bb44a39a90f97fcb1e09"

    # 获取知识库实例
    kb = get_knowledge_base(school_dir, corp_id)

    print("=" * 60)
    print("[INFO] 添加前的状态")
    print("=" * 60)
    print(f"分块数量: {len(kb._chunks)}")
    print(f"Embedding 形状: {kb._embeddings.shape if kb._embeddings is not None else 'None'}")

    # 测试文本
    test_text = """【高一(2)班 课程表】

| 节次 | 周一 | 周二 | 周三 | 周四 | 周五 |
|------|------|------|------|------|------|
| 第1节 | 测试课程1 | 测试课程2 | 测试课程3 | 测试课程4 | 测试课程5 |
| 第2节 | 测试课程6 | 测试课程7 | 测试课程8 | 测试课程9 | 测试课程10 |"""

    print("\n" + "=" * 60)
    print("[INFO] 添加测试课表")
    print("=" * 60)

    try:
        chunks = await kb.add_message(
            test_text,
            source_type="system",
            source_id="schedule_class_02_test",
            file_name="高一(2)班课程表(测试)",
        )
        print(f"[OK] 成功添加 {len(chunks)} 个分块")
    except Exception as e:
        print(f"[ERROR] 添加失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("[INFO] 添加后的状态")
    print("=" * 60)
    print(f"分块数量: {len(kb._chunks)}")
    print(f"Embedding 形状: {kb._embeddings.shape if kb._embeddings is not None else 'None'}")

    # 检查新添加的分块
    system_chunks = [c for c in kb._chunks if c.source_type == 'system']
    print(f"系统生成的分块数: {len(system_chunks)}")

    # 检查 embedding 对应关系
    if kb._embeddings is not None:
        print(f"\n分块数 vs Embedding 数: {len(kb._chunks)} vs {kb._embeddings.shape[0]}")
        if len(kb._chunks) != kb._embeddings.shape[0]:
            print("[WARNING] 分块数和 Embedding 数不匹配!")


if __name__ == "__main__":
    asyncio.run(test_add_message())
