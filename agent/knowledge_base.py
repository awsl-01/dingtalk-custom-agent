"""
知识库核心模块
负责消息存档、文本分块、Embedding生成、向量检索
"""
import os
import json
import hashlib
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict

import numpy as np

import config

logger = logging.getLogger(__name__)

# 文本分块参数
CHUNK_SIZE = 500        # 每个分块的最大字符数
CHUNK_OVERLAP = 50      # 分块之间的重叠字符数
TOP_K = 5               # 检索返回的最大结果数
SIMILARITY_THRESHOLD = 0.3  # 相似度阈值，低于此值认为无相关内容


@dataclass
class DocumentChunk:
    """文档分块"""
    chunk_id: str              # 分块唯一ID
    text: str                  # 分块文本内容
    source_type: str           # 来源类型：text/image/file
    source_id: str             # 来源ID（消息ID或文件ID）
    sender_id: str = ""        # 发送者ID
    sender_nick: str = ""      # 发送者昵称
    corp_id: str = ""          # 企业ID
    timestamp: float = 0.0     # 时间戳
    conversation_id: str = ""  # 会话ID
    message_type: str = ""     # 消息类型
    file_name: str = ""        # 文件名（如果是文件）
    tags: list = field(default_factory=list)  # 标签


class KnowledgeBase:
    """单个学校的知识库"""

    def __init__(self, school_dir: str, corp_id: str):
        self._school_dir = school_dir
        self._corp_id = corp_id
        self._index_dir = os.path.join(school_dir, "index")
        self._messages_dir = os.path.join(school_dir, "messages")
        self._files_dir = os.path.join(school_dir, "files")
        self._structured_dir = os.path.join(school_dir, "structured")

        os.makedirs(self._index_dir, exist_ok=True)
        os.makedirs(self._messages_dir, exist_ok=True)
        os.makedirs(self._files_dir, exist_ok=True)
        os.makedirs(self._structured_dir, exist_ok=True)

        # 加载索引
        self._chunks: List[DocumentChunk] = []
        self._embeddings: Optional[np.ndarray] = None
        self._load_index()

    def _load_index(self):
        """从磁盘加载索引"""
        chunks_file = os.path.join(self._index_dir, "chunks.json")
        embeddings_file = os.path.join(self._index_dir, "embeddings.npy")

        if os.path.exists(chunks_file):
            try:
                with open(chunks_file, "r", encoding="utf-8") as f:
                    chunks_data = json.load(f)
                self._chunks = [DocumentChunk(**c) for c in chunks_data]
                logger.info(f"加载知识库索引: {len(self._chunks)} 个分块")
            except Exception as e:
                logger.warning(f"加载分块索引失败: {e}")
                self._chunks = []

        if os.path.exists(embeddings_file):
            try:
                self._embeddings = np.load(embeddings_file)
                logger.info(f"加载向量索引: {self._embeddings.shape}")
            except Exception as e:
                logger.warning(f"加载向量索引失败: {e}")
                self._embeddings = None

    def _save_index(self):
        """保存索引到磁盘"""
        chunks_file = os.path.join(self._index_dir, "chunks.json")
        embeddings_file = os.path.join(self._index_dir, "embeddings.npy")

        try:
            with open(chunks_file, "w", encoding="utf-8") as f:
                json.dump([asdict(c) for c in self._chunks], f,
                          ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存分块索引失败: {e}")

        if self._embeddings is not None:
            try:
                np.save(embeddings_file, self._embeddings)
            except Exception as e:
                logger.error(f"保存向量索引失败: {e}")

    async def add_message(
        self,
        text: str,
        source_type: str,
        source_id: str,
        sender_id: str = "",
        sender_nick: str = "",
        conversation_id: str = "",
        message_type: str = "",
        file_name: str = "",
        file_path: str = "",
        tags: list = None,
    ) -> List[DocumentChunk]:
        """
        将消息内容存入知识库

        参数:
            text: 提取的文本内容
            source_type: 来源类型 (text/image/file)
            source_id: 消息ID或文件ID
            sender_id: 发送者ID
            sender_nick: 发送者昵称
            conversation_id: 会话ID
            message_type: 消息类型
            file_name: 文件名
            file_path: 原始文件路径
            tags: 标签列表

        返回:
            生成的分块列表
        """
        if not text or not text.strip():
            logger.warning("空文本，跳过存档")
            return []

        timestamp = time.time()

        # 保存原始消息归档
        self._archive_message(
            text=text,
            source_type=source_type,
            source_id=source_id,
            sender_id=sender_id,
            sender_nick=sender_nick,
            conversation_id=conversation_id,
            message_type=message_type,
            file_name=file_name,
            file_path=file_path,
            timestamp=timestamp,
            tags=tags or [],
        )

        # 文本分块
        text_chunks = split_text(text)

        # 创建DocumentChunk对象
        new_chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunk_id = f"{source_id}_{i}"
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                text=chunk_text,
                source_type=source_type,
                source_id=source_id,
                sender_id=sender_id,
                sender_nick=sender_nick,
                corp_id=self._corp_id,
                timestamp=timestamp,
                conversation_id=conversation_id,
                message_type=message_type,
                file_name=file_name,
                tags=tags or [],
            )
            new_chunks.append(chunk)

        # 生成Embedding并更新索引
        if new_chunks:
            new_texts = [c.text for c in new_chunks]
            new_embeddings = await get_embeddings(new_texts)

            if new_embeddings is not None:
                self._chunks.extend(new_chunks)
                if self._embeddings is None:
                    self._embeddings = new_embeddings
                else:
                    self._embeddings = np.vstack([self._embeddings, new_embeddings])
            else:
                # Embedding失败，仍然保存分块（仅支持关键词检索）
                self._chunks.extend(new_chunks)

            self._save_index()
            logger.info(f"知识库新增 {len(new_chunks)} 个分块，总计 {len(self._chunks)} 个")

        return new_chunks

    async def search(self, query: str, top_k: int = TOP_K) -> List[Tuple[DocumentChunk, float]]:
        """
        语义检索：使用Embedding向量相似度搜索

        参数:
            query: 查询文本
            top_k: 返回结果数量

        返回:
            [(分块, 相似度分数), ...] 按相似度降序排列
        """
        if not self._chunks:
            return []

        # 生成查询的Embedding
        query_embedding = await get_embeddings([query])
        if query_embedding is None:
            logger.warning("Embedding生成失败，回退到关键词检索")
            return self.keyword_search(query, top_k)

        if self._embeddings is None or len(self._embeddings) == 0:
            logger.warning("向量索引为空，回退到关键词检索")
            return self.keyword_search(query, top_k)

        # 计算余弦相似度
        similarities = cosine_similarity(query_embedding[0], self._embeddings)

        # 取Top-K
        if len(similarities) <= top_k:
            top_indices = np.argsort(similarities)[::-1]
        else:
            top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score >= SIMILARITY_THRESHOLD:
                results.append((self._chunks[idx], score))

        return results

    def keyword_search(self, query: str, top_k: int = TOP_K) -> List[Tuple[DocumentChunk, float]]:
        """
        关键词检索（备用方案）

        参数:
            query: 查询文本
            top_k: 返回结果数量

        返回:
            [(分块, 匹配分数), ...]
        """
        if not self._chunks:
            return []

        # 简单的关键词匹配
        query_lower = query.lower()
        query_chars = set(query_lower)

        results = []
        for chunk in self._chunks:
            chunk_lower = chunk.text.lower()

            # 计算匹配分数
            score = 0.0

            # 完全包含查询
            if query_lower in chunk_lower:
                score += 1.0
            else:
                # 字符重叠比例
                chunk_chars = set(chunk_lower)
                overlap = len(query_chars & chunk_chars)
                score += overlap / max(len(query_chars), 1) * 0.5

                # 部分关键词匹配
                for word in query_lower.split():
                    if word in chunk_lower:
                        score += 0.3

            if score > 0.1:
                results.append((chunk, score))

        # 按分数降序排列
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _archive_message(self, text: str, source_type: str, source_id: str,
                         sender_id: str, sender_nick: str, conversation_id: str,
                         message_type: str, file_name: str, file_path: str,
                         timestamp: float, tags: list):
        """保存原始消息归档"""
        today = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
        day_dir = os.path.join(self._messages_dir, today)
        os.makedirs(day_dir, exist_ok=True)

        archive = {
            "source_id": source_id,
            "source_type": source_type,
            "text": text,
            "sender_id": sender_id,
            "sender_nick": sender_nick,
            "corp_id": self._corp_id,
            "conversation_id": conversation_id,
            "message_type": message_type,
            "file_name": file_name,
            "file_path": file_path,
            "timestamp": timestamp,
            "archived_at": datetime.now().isoformat(),
            "tags": tags,
        }

        archive_path = os.path.join(day_dir, f"{source_id}.json")
        try:
            with open(archive_path, "w", encoding="utf-8") as f:
                json.dump(archive, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存消息归档失败: {e}")

    def get_structured_data(self, data_type: str) -> list:
        """获取结构化数据（课表、考试、通讯录等）"""
        file_path = os.path.join(self._structured_dir, f"{data_type}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"读取结构化数据失败: {e}")
        return []

    def save_structured_data(self, data_type: str, data: list):
        """保存结构化数据"""
        file_path = os.path.join(self._structured_dir, f"{data_type}.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存结构化数据失败: {e}")

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)


def split_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    将文本分割为多个分块

    策略：优先按段落分割，段落过长时按固定长度分割

    参数:
        text: 原始文本
        chunk_size: 每个分块的最大字符数
        overlap: 分块之间的重叠字符数

    返回:
        分块列表
    """
    if not text or not text.strip():
        return []

    # 先按段落分割
    paragraphs = text.split("\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # 如果当前分块加上新段落不超过限制，合并
        if len(current_chunk) + len(para) + 1 <= chunk_size:
            current_chunk = f"{current_chunk}\n{para}" if current_chunk else para
        else:
            # 保存当前分块
            if current_chunk:
                chunks.append(current_chunk)

            # 如果段落本身超过限制，按固定长度分割
            if len(para) > chunk_size:
                sub_chunks = _split_long_text(para, chunk_size, overlap)
                chunks.extend(sub_chunks[:-1])
                current_chunk = sub_chunks[-1] if sub_chunks else ""
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _split_long_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """将长文本按固定长度分割"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
    return chunks


# 本地Embedding模型缓存
_local_embedding_model = None


def _get_local_embedding_model():
    """获取本地Embedding模型（懒加载）"""
    global _local_embedding_model
    if _local_embedding_model is None:
        try:
            # 设置HuggingFace镜像
            hf_endpoint = getattr(config, 'HF_ENDPOINT', '')
            if hf_endpoint:
                os.environ['HF_ENDPOINT'] = hf_endpoint

            from sentence_transformers import SentenceTransformer
            model_name = getattr(config, 'LOCAL_EMBEDDING_MODEL',
                                 'BAAI/bge-small-zh-v1.5')
            logger.info(f"加载本地Embedding模型: {model_name}")
            _local_embedding_model = SentenceTransformer(model_name)
            logger.info(f"本地Embedding模型加载完成")
        except Exception as e:
            logger.error(f"加载本地Embedding模型失败: {e}")
            _local_embedding_model = None
    return _local_embedding_model


async def get_embeddings(texts: List[str]) -> Optional[np.ndarray]:
    """
    生成文本的Embedding向量
    优先使用本地模型，失败则尝试远程API

    参数:
        texts: 文本列表

    返回:
        numpy数组，shape为 (len(texts), embedding_dim)
    """
    if not texts:
        return None

    # 优先使用本地模型
    model = _get_local_embedding_model()
    if model is not None:
        try:
            embeddings = model.encode(texts, normalize_embeddings=True)
            return np.array(embeddings, dtype=np.float32)
        except Exception as e:
            logger.warning(f"本地Embedding生成失败，尝试远程API: {e}")

    # 备用：远程API
    from openai import OpenAI
    api_key = getattr(config, 'EMBEDDING_API_KEY', '') or config.OPENAI_API_KEY
    base_url = getattr(config, 'EMBEDDING_BASE_URL', '') or config.OPENAI_BASE_URL
    model_name = getattr(config, 'EMBEDDING_MODEL', 'text-embedding-3-small')

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.embeddings.create(
            model=model_name,
            input=texts,
        )
        embeddings = [item.embedding for item in response.data]
        return np.array(embeddings, dtype=np.float32)
    except Exception as e:
        logger.error(f"远程Embedding也失败: {e}")
        return None


def cosine_similarity(query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
    """
    计算余弦相似度

    参数:
        query_vec: 查询向量，shape (dim,)
        doc_vecs: 文档向量矩阵，shape (n, dim)

    返回:
        相似度数组，shape (n,)
    """
    # 归一化
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    doc_norms = doc_vecs / (np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-10)

    # 计算余弦相似度
    similarities = np.dot(doc_norms, query_norm)
    return similarities


# 全局知识库实例缓存
_kb_cache: Dict[str, KnowledgeBase] = {}


def get_knowledge_base(school_dir: str, corp_id: str) -> KnowledgeBase:
    """获取或创建知识库实例（带缓存）"""
    if corp_id not in _kb_cache:
        _kb_cache[corp_id] = KnowledgeBase(school_dir, corp_id)
    return _kb_cache[corp_id]
