# Rerank（重排序）功能说明

## 功能概述

Rerank 是检索增强生成（RAG）流程中的精排环节，用于提升 Top-K 结果的准确率。

### 检索流程

```
用户查询
    ↓
第一阶段：召回（Recall）
    ├── 语义检索（Embedding 相似度）
    └── 关键词检索（倒排索引）
    ↓
第二阶段：精排（Rerank）← 新增
    ├── 本地 Cross-encoder 模型
    ├── LLM 重排序
    └── 第三方 Rerank API
    ↓
返回 Top-K 结果
```

## 为什么需要 Rerank？

1. **召回阶段的局限性**：
   - Embedding 模型擅长捕捉语义相似性，但可能忽略精确匹配
   - 关键词检索擅长精确匹配，但可能忽略语义相关性
   - 两者结合（混合检索）可以互补，但仍有提升空间

2. **Rerank 的优势**：
   - 使用更强大的模型（Cross-encoder）对 query-document 对进行精细打分
   - 考虑 query 和 document 的交互信息，而非独立编码
   - 显著提升 Top-K 结果的准确率

## 支持的 Rerank 策略

### 1. 规则重排序（rule）- 默认

基于规则的轻量级重排序，无需额外依赖。

**特点**：
- 无需安装额外依赖
- 速度最快
- 准确率提升有限

**评分规则**：
- 关键词出现在文本前半部分：+0.1
- 关键词密度：每个关键词 +0.05
- 有摘要：+0.05
- 有高亮：+0.05
- 文本长度适中（100-500字符）：+0.03

### 2. 本地 Cross-encoder（local）

使用本地的 Cross-encoder 模型进行重排序。

**推荐模型**：
- `BAAI/bge-reranker-base`：中文效果好，速度适中
- `BAAI/bge-reranker-large`：效果更好，但更慢
- `cross-encoder/ms-marco-MiniLM-L-6-v2`：英文效果好，速度快

**安装依赖**：
```bash
pip install sentence-transformers
```

**配置**：
```env
RERANK_ENABLED=true
RERANK_STRATEGY=local
LOCAL_RERANK_MODEL=BAAI/bge-reranker-base
```

**特点**：
- 效果好（Cross-encoder 考虑 query-document 交互）
- 需要下载模型（首次运行约 400MB）
- 推理速度较慢（CPU 上约 100-500ms/query）

### 3. LLM 重排序（llm）

使用 LLM（如 GPT、Claude）进行重排序。

**工作原理**：
1. 将检索结果列表发送给 LLM
2. LLM 根据与查询的相关性对结果进行排序
3. 返回排序后的结果

**配置**：
```env
RERANK_ENABLED=true
RERANK_STRATEGY=llm
```

**特点**：
- 效果最好（利用 LLM 的强大理解能力）
- 需要调用 LLM API（有成本）
- 速度较慢（需要等待 LLM 响应）
- 适合对准确率要求高的场景

### 4. 第三方 Rerank API（api）

使用专业的 Rerank API 服务。

**支持的服务**：
- Cohere Rerank：https://cohere.com/rerank
- Jina Rerank：https://jina.ai/reranker
- 其他兼容 Cohere API 格式的服务

**配置**：
```env
RERANK_ENABLED=true
RERANK_STRATEGY=api
RERANK_API_KEY=your_api_key
RERANK_BASE_URL=https://api.cohere.ai/v1/rerank
RERANK_MODEL=rerank-multilingual-v3.0
```

**特点**：
- 效果好（专业 Rerank 模型）
- 速度快（专门优化的推理服务）
- 需要 API 费用
- 适合生产环境

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| RERANK_ENABLED | 是否启用 Rerank | false |
| RERANK_STRATEGY | Rerank 策略 | llm |
| LOCAL_RERANK_MODEL | 本地 Cross-encoder 模型 | BAAI/bge-reranker-base |
| RERANK_API_KEY | Rerank API 密钥 | - |
| RERANK_BASE_URL | Rerank API 地址 | - |
| RERANK_MODEL | Rerank 模型名称 | - |
| RERANK_TOP_K | Rerank 返回数量 | 3 |

### 配置示例

#### 场景 1：开发环境（无需额外依赖）

```env
RERANK_ENABLED=false
```

使用默认的规则重排序，无需安装额外依赖。

#### 场景 2：本地部署（追求效果）

```env
RERANK_ENABLED=true
RERANK_STRATEGY=local
LOCAL_RERANK_MODEL=BAAI/bge-reranker-base
```

使用本地 Cross-encoder 模型，效果好，无 API 费用。

#### 场景 3：生产环境（追求速度和效果）

```env
RERANK_ENABLED=true
RERANK_STRATEGY=api
RERANK_API_KEY=your_cohere_api_key
RERANK_BASE_URL=https://api.cohere.ai/v1/rerank
RERANK_MODEL=rerank-multilingual-v3.0
```

使用 Cohere Rerank API，速度快，效果好。

#### 场景 4：已有 LLM API（无需额外费用）

```env
RERANK_ENABLED=true
RERANK_STRATEGY=llm
```

使用现有的 LLM API 进行重排序，无需额外 API 费用。

## 性能对比

| 策略 | 准确率 | 速度 | 成本 | 依赖 |
|------|--------|------|------|------|
| rule | ★★☆ | ★★★★★ | 无 | 无 |
| local | ★★★★ | ★★★☆ | 无 | sentence-transformers |
| llm | ★★★★★ | ★★☆ | LLM API 费用 | OpenAI SDK |
| api | ★★★★☆ | ★★★★ | API 费用 | httpx |

## 使用建议

### 何时启用 Rerank？

1. **检索结果不理想**：如果 Top-K 结果中经常出现不相关的内容
2. **对准确率要求高**：如教育、医疗等专业领域
3. **用户反馈问题**：用户经常抱怨找不到想要的内容

### 选择哪种策略？

1. **开发测试**：使用 `rule`（默认），无需额外配置
2. **本地部署**：使用 `local`，效果好，无 API 费用
3. **生产环境**：使用 `api`（如 Cohere），速度快，效果稳定
4. **已有 LLM API**：使用 `llm`，无需额外费用

### 优化建议

1. **召回数量**：Rerank 前会多召回 3 倍的结果（`top_k * 3`），确保有足够的候选
2. **模型选择**：中文场景优先选择 `BAAI/bge-reranker-base`
3. **API 选择**：Cohere Rerank 支持多语言，效果好
4. **成本控制**：可以只对高价值查询启用 Rerank

## 常见问题

### Q1: Rerank 会增加多少延迟？

- **rule**: <1ms
- **local**: 100-500ms（CPU），10-50ms（GPU）
- **llm**: 500-2000ms（取决于 LLM 响应速度）
- **api**: 50-200ms

### Q2: Rerank 需要额外的内存吗？

- **local**: 需要约 500MB-1GB（取决于模型大小）
- **其他**: 几乎不需要额外内存

### Q3: 如何测试 Rerank 的效果？

1. 准备一组测试查询和期望结果
2. 分别在启用/禁用 Rerank 的情况下运行
3. 对比 Top-K 结果的准确率

### Q4: Rerank 失败会怎样？

如果 Rerank 失败（如 API 超时、模型加载失败），系统会自动回退到规则重排序，确保检索功能正常。

## 代码示例

### 手动调用 Rerank

```python
from agent.knowledge_base_v2 import get_knowledge_base, get_reranker

# 获取知识库实例
kb = get_knowledge_base(school_dir, corp_id)

# 执行检索（自动 Rerank）
results = await kb.search("课程安排", top_k=5, use_rerank=True)

# 或者手动调用 Rerank
reranker = get_reranker()
results = await kb.search("课程安排", top_k=15, use_rerank=False)
reranked = await reranker.rerank("课程安排", results, top_k=5)
```

### 禁用 Rerank

```python
# 单次查询禁用 Rerank
results = await kb.search("课程安排", top_k=5, use_rerank=False)
```

## 相关文档

- [知识库操作日志](OPERATION_LOGS.md)
- [知识库 V2 优化说明](../CLAUDE.md#知识库-v2-优化说明)
