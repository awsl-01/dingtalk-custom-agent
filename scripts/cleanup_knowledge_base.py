"""
知识库清理脚本

清理无意义的分块：
- 文本过短（≤5字符）
- 匹配 SKIP_EXACT（确认、好的等）
- 纯问题/指令类消息
- 重复分块（content_hash 相同）
- 未分类且无实质内容的消息
"""
import os
import sys
import json
import re
import hashlib

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def compute_content_hash(text: str) -> str:
    """计算内容哈希"""
    cleaned = re.sub(r'\s+', '', text.strip())
    return hashlib.md5(cleaned.encode('utf-8')).hexdigest()


# 需要删除的精确匹配文本
JUNK_EXACT = {
    '确认', '确定', '好的', '可以', '没问题', '同意', 'ok', 'yes',
    '取消', '不要了', '算了', '放弃',
    '谢谢', '感谢', 'thank', 'thanks', '3q',
    '哈哈哈', '呵呵呵', '嘻嘻', '哈哈', '呵呵', '嘿嘿', '666',
    '开始排课', '开始', '导出', '优化',
    '课表查询', '查看课表', '排课模板',
}

# 问题/指令类模式
JUNK_PATTERNS = [
    r'^.*[？?]$',                          # 以?或？结尾
    r'^什么|^怎么|^为什么|^哪些|^如何|^是否|^能否',  # 疑问词开头
    r'^帮我|^请|^开始|^查看|^导出|^发送|^下载',      # 指令类
    r'^.*调课$|^.*换课$|^.*调换$',                    # 调课指令
    r'^确认.*|^好的.*|^可以.*',                       # 确认类
]


def is_junk_chunk(chunk: dict) -> tuple:
    """
    判断分块是否是垃圾数据

    返回: (是否垃圾, 原因)
    """
    text = chunk.get('text', '').strip()
    category = chunk.get('category', '')
    source_type = chunk.get('source_type', '')

    # 1. 系统生成的内容（排课结果等）永远保留
    if source_type == 'system':
        return False, ''

    # 2. 文件来源的内容保留（可能是上传的文档）
    if source_type == 'file':
        # 但文件来源中过短的也删除
        if len(text) <= 10:
            return True, '文件内容过短'
        return False, ''

    # 3. 文本过短
    if len(text) <= 5:
        return True, f'文本过短({len(text)}字符)'

    # 4. 精确匹配垃圾列表
    if text in JUNK_EXACT:
        return True, '精确匹配垃圾列表'

    # 5. 匹配问题/指令类模式
    for pattern in JUNK_PATTERNS:
        if re.match(pattern, text):
            return True, f'匹配模式: {pattern}'

    # 6. 未分类且文本很短
    if not category and len(text) < 20:
        return True, '未分类且文本短'

    # 7. 包含大量重复内容（同一消息被分块多次）
    if text.startswith('确认') or text.startswith('好的'):
        return True, '确认/好的类消息'

    return False, ''


def cleanup_knowledge_base(kb_dir: str, dry_run: bool = True):
    """
    清理知识库

    参数:
        kb_dir: 知识库目录（如 knowledge/ding3f80...）
        dry_run: 是否为试运行（不实际删除）
    """
    index_dir = os.path.join(kb_dir, 'index')
    chunks_file = os.path.join(index_dir, 'chunks.json')
    embeddings_file = os.path.join(index_dir, 'embeddings.npy')

    if not os.path.exists(chunks_file):
        print(f"❌ 未找到索引文件: {chunks_file}")
        return

    # 加载分块
    with open(chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    print(f"📊 加载 {len(chunks)} 个分块")

    # 加载 embeddings
    import numpy as np
    embeddings = None
    if os.path.exists(embeddings_file):
        embeddings = np.load(embeddings_file)
        print(f"📊 加载向量索引: {embeddings.shape}")

    # 识别垃圾分块
    junk_indices = []
    junk_reasons = []

    for i, chunk in enumerate(chunks):
        is_junk, reason = is_junk_chunk(chunk)
        if is_junk:
            junk_indices.append(i)
            junk_reasons.append(reason)

    print(f"\n🗑️ 发现 {len(junk_indices)} 个垃圾分块:")
    print(f"   保留 {len(chunks) - len(junk_indices)} 个分块")

    # 按原因统计
    reason_counts = {}
    for reason in junk_reasons:
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    print("\n📋 垃圾原因统计:")
    for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
        print(f"   {reason}: {count} 个")

    # 显示要删除的分块（前10个）
    print(f"\n📝 待删除分块预览（前10个）:")
    for idx, reason in zip(junk_indices[:10], junk_reasons[:10]):
        text = chunks[idx].get('text', '')[:80]
        print(f"   [{reason}] {text}...")

    if dry_run:
        print(f"\n⚠️ 试运行模式，未实际删除")
        print(f"   运行 cleanup_knowledge_base(kb_dir, dry_run=False) 执行清理")
        return

    # 执行清理
    # 1. 删除垃圾分块
    keep_indices = [i for i in range(len(chunks)) if i not in junk_indices]
    clean_chunks = [chunks[i] for i in keep_indices]

    # 2. 清理 embeddings
    if embeddings is not None and len(junk_indices) > 0:
        # 需要保留的索引
        keep_mask = np.ones(len(chunks), dtype=bool)
        keep_mask[junk_indices] = False
        clean_embeddings = embeddings[keep_mask]
    else:
        clean_embeddings = embeddings

    # 3. 去重（基于 content_hash）
    seen_hashes = {}
    deduped_chunks = []
    deduped_indices = []

    for i, chunk in enumerate(clean_chunks):
        text = chunk.get('text', '')
        content_hash = compute_content_hash(text)

        if content_hash in seen_hashes:
            # 重复，跳过
            continue

        seen_hashes[content_hash] = True
        deduped_chunks.append(chunk)
        deduped_indices.append(i)

    if len(clean_chunks) != len(deduped_chunks):
        print(f"\n🔄 去重: {len(clean_chunks)} → {len(deduped_chunks)}")

    # 4. 更新 embeddings（去重后）
    if clean_embeddings is not None and len(deduped_indices) != len(clean_embeddings):
        clean_embeddings = clean_embeddings[deduped_indices]

    # 5. 保存
    with open(chunks_file, 'w', encoding='utf-8') as f:
        json.dump(deduped_chunks, f, ensure_ascii=False, indent=2)

    if clean_embeddings is not None:
        np.save(embeddings_file, clean_embeddings)

    # 6. 删除分页文件（需要重新生成）
    for f in os.listdir(index_dir):
        if f.startswith('chunks_page_') and f.endswith('.json'):
            os.remove(os.path.join(index_dir, f))

    # 7. 更新元信息
    meta_file = os.path.join(index_dir, 'index_meta.json')
    meta = {
        'total_chunks': len(deduped_chunks),
        'total_pages': 0,
        'page_size': 100,
        'cleaned_at': __import__('datetime').datetime.now().isoformat(),
        'cleanup_stats': {
            'original_count': len(chunks),
            'junk_removed': len(junk_indices),
            'duplicates_removed': len(clean_chunks) - len(deduped_chunks),
            'final_count': len(deduped_chunks),
        }
    }
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 清理完成！")
    print(f"   原始: {len(chunks)} 个分块")
    print(f"   删除垃圾: {len(junk_indices)} 个")
    print(f"   去重删除: {len(clean_chunks) - len(deduped_chunks)} 个")
    print(f"   最终: {len(deduped_chunks)} 个分块")


# 设置 UTF-8 输出
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


if __name__ == '__main__':
    # 查找所有学校的知识库
    knowledge_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'knowledge')

    if not os.path.exists(knowledge_dir):
        print(f"❌ 未找到知识库目录: {knowledge_dir}")
        sys.exit(1)

    # 获取 dry_run 参数
    dry_run = '--execute' not in sys.argv

    for school_id in os.listdir(knowledge_dir):
        school_path = os.path.join(knowledge_dir, school_id)
        if os.path.isdir(school_path):
            print(f"\n{'='*60}")
            print(f"  清理学校: {school_id}")
            print(f"{'='*60}")
            cleanup_knowledge_base(school_path, dry_run=dry_run)
