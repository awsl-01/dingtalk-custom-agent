#!/usr/bin/env python
"""
删除指定文件脚本
删除以下文件及其在知识库中的索引：
- image_d38df775.jpg
- 排课模板.xlsx
- 高中教师信息_排课模板_豆包AI生成.xlsx
- 湖北高中排课模板_*.xlsx (所有版本)
"""
import os
import sys
import shutil
import json
from pathlib import Path

# 配置路径
KNOWLEDGE_DIR = "d:/claude/knowledge/ding3f80869f26d4bb44a39a90f97fcb1e09"
FILES_DIR = os.path.join(KNOWLEDGE_DIR, "files")
INDEX_FILE = os.path.join(KNOWLEDGE_DIR, "index", "chunks.json")
INDEX_META_FILE = os.path.join(KNOWLEDGE_DIR, "index", "index_meta.json")

# 要删除的文件名模式
DELETE_PATTERNS = [
    "image_d38df775.jpg",
    "排课模板.xlsx",
    "高中教师信息_排课模板_豆包AI生成.xlsx",
    "湖北高中排课模板_",  # 匹配所有湖北高中排课模板开头的文件
]


def find_files_to_delete():
    """查找所有需要删除的文件"""
    files_to_delete = []

    for root, dirs, files in os.walk(FILES_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            for pattern in DELETE_PATTERNS:
                if file.startswith(pattern) or file == pattern:
                    files_to_delete.append(file_path)
                    break

    return files_to_delete


def delete_physical_files(file_list):
    """删除物理文件"""
    deleted_count = 0
    for file_path in file_list:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"✅ 已删除: {os.path.basename(file_path)}")
                deleted_count += 1
            else:
                print(f"⚠️  文件不存在: {file_path}")
        except Exception as e:
            print(f"❌ 删除失败 {file_path}: {e}")

    return deleted_count


def delete_index_chunks():
    """删除索引中对应的分块"""
    if not os.path.exists(INDEX_FILE):
        print("⚠️  索引文件不存在，跳过")
        return 0

    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            chunks = json.load(f)

        original_count = len(chunks)

        # 过滤掉需要删除的分块
        filtered_chunks = []
        for chunk in chunks:
            file_name = chunk.get("file_name", "")
            should_delete = False

            for pattern in DELETE_PATTERNS:
                if file_name.startswith(pattern) or file_name == pattern:
                    should_delete = True
                    break

            if not should_delete:
                filtered_chunks.append(chunk)

        deleted_count = original_count - len(filtered_chunks)

        # 保存过滤后的索引
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(filtered_chunks, f, ensure_ascii=False, indent=2)

        # 更新索引元数据
        if os.path.exists(INDEX_META_FILE):
            with open(INDEX_META_FILE, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            meta["total_chunks"] = len(filtered_chunks)
            with open(INDEX_META_FILE, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

        print(f"✅ 已从索引中删除 {deleted_count} 个分块")
        return deleted_count

    except Exception as e:
        print(f"❌ 删除索引分块失败: {e}")
        return 0


def delete_page_files():
    """删除分页索引文件"""
    index_dir = os.path.join(KNOWLEDGE_DIR, "index")
    deleted_count = 0

    for file in os.listdir(index_dir):
        if file.startswith("chunks_page_") and file.endswith(".json"):
            file_path = os.path.join(index_dir, file)
            try:
                os.remove(file_path)
                print(f"✅ 已删除分页索引: {file}")
                deleted_count += 1
            except Exception as e:
                print(f"❌ 删除分页索引失败 {file}: {e}")

    return deleted_count


def clean_empty_dirs():
    """清理空目录"""
    for root, dirs, files in os.walk(FILES_DIR, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    print(f"✅ 已删除空目录: {dir_name}")
            except:
                pass


def main():
    print("=" * 60)
    print("🗑️  知识库文件删除脚本")
    print("=" * 60)

    # 1. 查找要删除的文件
    print("\n📋 查找要删除的文件...")
    files_to_delete = find_files_to_delete()

    if not files_to_delete:
        print("⚠️  未找到匹配的文件")
        return

    print(f"\n找到 {len(files_to_delete)} 个文件:")
    for f in files_to_delete:
        print(f"  • {os.path.basename(f)}")

    # 2. 确认删除
    print("\n" + "=" * 60)
    response = input("确认删除这些文件？(输入 yes 确认): ")
    if response.lower() != 'yes':
        print("❌ 已取消删除")
        return

    # 3. 删除物理文件
    print("\n📁 删除物理文件...")
    deleted_files = delete_physical_files(files_to_delete)

    # 4. 删除索引分块
    print("\n📇 删除索引分块...")
    deleted_chunks = delete_index_chunks()

    # 5. 删除分页索引文件
    print("\n📄 删除分页索引文件...")
    deleted_pages = delete_page_files()

    # 6. 清理空目录
    print("\n🧹 清理空目录...")
    clean_empty_dirs()

    # 7. 汇总
    print("\n" + "=" * 60)
    print("✅ 删除完成！")
    print(f"  • 删除文件: {deleted_files} 个")
    print(f"  • 删除索引: {deleted_chunks} 个")
    print(f"  • 删除分页索引: {deleted_pages} 个")
    print("=" * 60)
    print("\n💡 建议重启服务以确保索引完全重建")


if __name__ == "__main__":
    main()
