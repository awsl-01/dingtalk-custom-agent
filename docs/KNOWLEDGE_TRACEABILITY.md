# 知识溯源功能

## 功能概述

知识库现在支持完整的知识溯源功能，可以追溯每条知识的来源：

1. **消息来源**：来自哪条消息、哪个会话、哪位用户
2. **文件来源**：来自哪个文件、文件类型、文件大小
3. **时间信息**：消息发送时间、入库时间、过期时间
4. **分块信息**：分块在原始消息中的位置

## 溯源字段说明

### DocumentChunk 新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `original_text` | str | 原始消息完整文本 |
| `message_timestamp` | float | 原始消息发送时间戳 |
| `conversation_type` | str | 会话类型：single/group |
| `conversation_name` | str | 会话名称（群名或单聊对象） |
| `sender_dept` | str | 发送者部门 |
| `file_size` | int | 文件大小（字节） |
| `file_type` | str | 文件类型（pdf/word/excel/image等） |
| `chunk_index` | int | 分块在原始消息中的索引 |
| `total_chunks` | int | 原始消息的总分块数 |

### 已有溯源字段

| 字段 | 说明 |
|------|------|
| `source_type` | 来源类型：text/image/file |
| `source_id` | 来源 ID（消息 ID 或文件 ID） |
| `sender_id` | 发送者 ID |
| `sender_nick` | 发送者昵称 |
| `conversation_id` | 会话 ID |
| `file_name` | 文件名 |
| `timestamp` | 入库时间戳 |

## 使用方法

### 1. 添加消息时传入溯源信息

```python
from agent.knowledge_base_v2 import get_knowledge_base

kb = get_knowledge_base(school_dir, corp_id)

# 添加消息时传入完整的溯源信息
await kb.add_message(
    text="计算机2301班周一第1-2节语文",
    source_type="text",
    source_id="msg_123456",
    sender_id="user_001",
    sender_nick="张老师",
    conversation_id="conv_001",
    message_type="text",
    # 溯源增强参数
    conversation_type="group",
    conversation_name="计算机2301班家长群",
    sender_dept="教务处",
    message_timestamp=1685500000.0,
)
```

### 2. 添加文件时传入溯源信息

```python
# 添加文件时传入完整的溯源信息
await kb.add_message(
    text="课表内容...",
    source_type="file",
    source_id="file_789",
    sender_id="user_002",
    sender_nick="李老师",
    conversation_id="conv_002",
    file_name="2026年春季课表.xlsx",
    # 溯源增强参数
    conversation_type="single",
    conversation_name="教务处工作群",
    sender_dept="教务处",
    file_size=102400,
    file_type="excel",
)
```

### 3. 追溯单个分块的来源

```python
# 追溯单个分块
trace_info = kb.trace_chunk("msg_123456_0")

print(f"分块ID: {trace_info['chunk_id']}")
print(f"内容预览: {trace_info['text_preview']}")
print(f"分类: {trace_info['category']}")

print(f"\n来源信息:")
print(f"  类型: {trace_info['source']['type']}")
print(f"  ID: {trace_info['source']['id']}")
print(f"  文件名: {trace_info['source']['file_name']}")

print(f"\n发送者信息:")
print(f"  ID: {trace_info['sender']['id']}")
print(f"  昵称: {trace_info['sender']['nick']}")
print(f"  部门: {trace_info['sender']['dept']}")

print(f"\n会话信息:")
print(f"  ID: {trace_info['conversation']['id']}")
print(f"  类型: {trace_info['conversation']['type']}")
print(f"  名称: {trace_info['conversation']['name']}")

print(f"\n时间信息:")
print(f"  入库时间: {trace_info['timing']['created']}")
print(f"  消息时间: {trace_info['timing']['message_time']}")
print(f"  过期时间: {trace_info['timing']['expires_at']}")
```

**输出示例**：
```
分块ID: msg_123456_0
内容预览: 计算机2301班周一第1-2节语文...
分类: 课表

来源信息:
  类型: text
  ID: msg_123456
  文件名:

发送者信息:
  ID: user_001
  昵称: 张老师
  部门: 教务处

会话信息:
  ID: conv_001
  类型: group
  名称: 计算机2301班家长群

时间信息:
  入库时间: 2026-05-31T10:30:00
  消息时间: 2026-05-31T10:25:00
  过期时间: None
```

### 4. 追溯同一来源的所有分块

```python
# 追溯同一消息的所有分块
traces = kb.trace_by_source("msg_123456")

print(f"消息 msg_123456 共产生 {len(traces)} 个分块")
for trace in traces:
    print(f"  - {trace['chunk_id']}: {trace['text_preview'][:50]}...")
```

### 5. 追溯同一用户贡献的所有知识

```python
# 追溯张老师贡献的所有知识
traces = kb.trace_by_sender(sender_nick="张老师")

print(f"张老师共贡献了 {len(traces)} 条知识")
for trace in traces[:5]:  # 显示前5条
    print(f"  - [{trace['category']}] {trace['text_preview'][:50]}...")
```

### 6. 追溯同一会话产生的所有知识

```python
# 追溯家长群产生的所有知识
traces = kb.trace_by_conversation("conv_001")

print(f"家长群共产生了 {len(traces)} 条知识")
for trace in traces[:5]:
    print(f"  - [{trace['sender']['nick']}] {trace['text_preview'][:50]}...")
```

### 7. 获取溯源统计信息

```python
# 获取溯源统计
trace_stats = kb.get_trace_stats()

print(f"总分块数: {trace_stats['total_chunks']}")

print(f"\n按来源类型:")
for stype, count in trace_stats['by_source_type'].items():
    print(f"  {stype}: {count}")

print(f"\nTop 10 发送者:")
for sender, count in trace_stats['top_senders']:
    print(f"  {sender}: {count}")

print(f"\nTop 10 会话:")
for conv, count in trace_stats['top_conversations']:
    print(f"  {conv}: {count}")

print(f"\n按会话类型:")
for ctype, count in trace_stats['by_conversation_type'].items():
    print(f"  {ctype}: {count}")

print(f"\n按文件类型:")
for ftype, count in trace_stats['file_types'].items():
    print(f"  {ftype}: {count}")
```

**输出示例**：
```
总分块数: 1000

按来源类型:
  text: 600
  file: 300
  image: 100

Top 10 发送者:
  张老师: 150
  李老师: 120
  王老师: 100

Top 10 会话:
  计算机2301班家长群: 200
  教务处工作群: 150
  三年级教师群: 100

按会话类型:
  group: 800
  single: 200

按文件类型:
  excel: 150
  pdf: 100
  word: 50
```

### 8. 导出知识库（包含溯源信息）

```python
# 导出为 JSON（包含溯源信息）
count = kb.export_with_trace("export.json", format="json", include_trace=True)
print(f"导出了 {count} 条知识")

# 导出为 CSV（包含溯源信息）
count = kb.export_with_trace("export.csv", format="csv", include_trace=True)
print(f"导出了 {count} 条知识")
```

**CSV 导出字段**：
- chunk_id, text, category, source_type, source_id
- file_name, sender_id, sender_nick, sender_dept
- conversation_id, conversation_type, conversation_name
- created_at, message_time, expires_at, is_expired
- version, is_latest, keywords, summary

## 典型使用场景

### 场景 1：知识质量追溯

**需求**：发现某条知识有误，追溯是哪位用户在哪个会话中发送的

**流程**：
1. 发现有误的知识分块 ID
2. 调用 `trace_chunk()` 获取溯源信息
3. 找到发送者和会话
4. 联系发送者修正

**代码**：
```python
# 发现有误的知识
trace = kb.trace_chunk("msg_123456_0")

print(f"这条知识来自: {trace['sender']['nick']}")
print(f"在会话: {trace['conversation']['name']}")
print(f"发送时间: {trace['timing']['message_time']}")

# 联系发送者修正
```

### 场景 2：用户贡献统计

**需求**：统计每位教师贡献了多少知识

**流程**：
1. 调用 `get_trace_stats()` 获取统计信息
2. 查看 `top_senders` 排行榜
3. 可以按用户进一步追溯

**代码**：
```python
stats = kb.get_trace_stats()

print("教师知识贡献排行榜:")
for i, (sender, count) in enumerate(stats['top_senders'], 1):
    print(f"  {i}. {sender}: {count} 条")
```

### 场景 3：会话知识审计

**需求**：审计某个群聊产生了哪些知识

**流程**：
1. 调用 `trace_by_conversation()` 获取会话的所有知识
2. 分析知识内容和来源
3. 如有需要，删除不当内容

**代码**：
```python
# 审计家长群的知识
traces = kb.trace_by_conversation("conv_001")

print(f"家长群共产生了 {len(traces)} 条知识:")
for trace in traces:
    print(f"  [{trace['timing']['message_time']}] {trace['sender']['nick']}: {trace['text_preview'][:50]}...")
```

### 场景 4：文件来源追溯

**需求**：追溯某个文件的知识被谁下载或引用

**流程**：
1. 调用 `trace_by_source()` 获取文件的所有分块
2. 查看分块的溯源信息
3. 了解文件的使用情况

### 场景 5：知识生命周期管理

**需求**：管理知识的完整生命周期（创建、更新、过期、删除）

**流程**：
1. 创建时记录完整的溯源信息
2. 通过版本控制追踪更新历史
3. 通过时效管理自动过期
4. 删除时保留操作日志

## 统计增强

### get_stats() 返回新增字段

```python
stats = kb.get_stats()

# 已有字段
print(f"总分块数: {stats.total_chunks}")
print(f"按类别统计: {stats.categories}")
print(f"按来源类型统计: {stats.source_types}")
print(f"Top发送者: {stats.top_senders}")

# 新增溯源字段
print(f"按会话统计: {stats.conversations}")
print(f"按会话类型统计: {stats.conversation_types}")
print(f"按文件类型统计: {stats.file_types}")
```

## 性能说明

| 操作 | 耗时 | 说明 |
|------|------|------|
| 追溯单个分块 | O(1) | 直接查找 |
| 追溯同一来源 | O(n) | 遍历所有分块 |
| 追溯同一用户 | O(n) | 遍历所有分块 |
| 追溯同一会话 | O(n) | 遍历所有分块 |
| 溯源统计 | O(n) | 遍历所有分块 |
| 导出（含溯源） | O(n) | 序列化所有分块 |

## 代码变更

### DocumentChunk 新增字段

- `original_text`: 原始消息完整文本
- `message_timestamp`: 原始消息发送时间
- `conversation_type`: 会话类型
- `conversation_name`: 会话名称
- `sender_dept`: 发送者部门
- `file_size`: 文件大小
- `file_type`: 文件类型
- `chunk_index`: 分块索引
- `total_chunks`: 总分块数

### KnowledgeBase 新增方法

- `trace_chunk()`: 追溯单个分块
- `trace_by_source()`: 追溯同一来源
- `trace_by_sender()`: 追溯同一用户
- `trace_by_conversation()`: 追溯同一会话
- `get_trace_stats()`: 获取溯源统计
- `export_with_trace()`: 导出（含溯源）
- `_format_trace_info()`: 格式化溯源信息
- `_detect_file_type()`: 检测文件类型

### KnowledgeStats 新增字段

- `conversations`: 按会话统计
- `conversation_types`: 按会话类型统计
- `file_types`: 按文件类型统计

## 相关文档

- [操作日志功能](OPERATION_LOGS.md)
- [去重与版本控制](DEDUP_VERSIONING.md)
- [时效管理功能](EXPIRY_MANAGEMENT.md)
- [检索过滤功能](SEARCH_FILTERS.md)
