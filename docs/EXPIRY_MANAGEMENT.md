# 知识库时效管理功能

## 功能概述

知识库现在支持智能时效管理，自动处理过期内容，避免误导用户。

### 核心功能

1. **自动过期检测**：根据内容类别和时间自动判断是否过期
2. **智能过期时间提取**：从文本中提取考试日期、作业截止日期等
3. **过期内容过滤**：检索时自动过滤掉过期内容
4. **过期统计与管理**：查看过期统计、手动设置过期时间、延长有效期

## 过期策略

### 默认过期时间

| 类别 | 默认过期时间 | 说明 |
|------|-------------|------|
| `exam`（考试） | 30 天 | 考试安排通常在考试结束后失效 |
| `notice`（通知） | 90 天 | 通知通常在一段时间后失效 |
| `homework`（作业） | 7 天 | 作业通常在交作业日期后失效 |
| `schedule`（课表） | 永不过期 | 课表通过版本控制更新 |
| `contact`（通讯录） | 永不过期 | 联系方式通常长期有效 |
| `teaching`（教学） | 365 天 | 教学资料通常一年内有效 |
| `student`（学生） | 永不过期 | 学生信息通常长期有效 |
| `other`（其他） | 180 天 | 其他内容默认 180 天 |

### 智能过期时间提取

系统会尝试从文本中提取具体的过期时间：

#### 考试安排

```
文本："三年级数学期中考试时间：2026年6月15日"
提取：考试日期 = 2026-06-15
过期时间：2026-06-16（考试结束后1天）
```

#### 作业布置

```
文本："今天作业：练习册第15-16页，下周一交"
提取：交作业日期 = 下周一
过期时间：下周一
```

#### 通知公告

```
文本："关于举办校园运动会的通知，报名截止日期：6月20日"
提取：截止日期 = 6月20日
过期时间：6月20日
```

### 配置方式

在 `.env` 文件中配置：

```env
# 启用时效管理
EXPIRY_ENABLED=true

# 各类别的默认过期时间（天数，0表示永不过期）
EXPIRY_DAYS_EXAM=30
EXPIRY_DAYS_NOTICE=90
EXPIRY_DAYS_HOMEWORK=7
EXPIRY_DAYS_SCHEDULE=0
EXPIRY_DAYS_CONTACT=0
EXPIRY_DAYS_TEACHING=365
EXPIRY_DAYS_STUDENT=0
EXPIRY_DAYS_OTHER=180

# 自动过期检查间隔（小时）
EXPIRY_CHECK_INTERVAL_HOURS=24

# 过期后是否自动删除（false则标记为过期但保留）
EXPIRY_AUTO_DELETE=false
```

## 使用方法

### 1. 自动过期检测

系统会在以下时机自动检测过期内容：

- **添加新内容时**：计算过期时间并保存
- **检索内容时**：自动过滤掉过期内容
- **定时检查**：按配置的间隔检查过期内容

### 2. 查看过期统计

```python
from agent.knowledge_base_v2 import get_knowledge_base

kb = get_knowledge_base(school_dir, corp_id)

# 获取过期统计
stats = kb.get_expiry_stats()

print(f"总分块数: {stats['total_chunks']}")
print(f"已过期: {stats['expired']}")
print(f"即将过期（7天内）: {stats['expiring_soon']}")

print("\n按类别统计:")
for cat, cat_stats in stats['by_category'].items():
    print(f"  {cat}:")
    print(f"    总数: {cat_stats['total']}")
    print(f"    已过期: {cat_stats['expired']}")
    print(f"    即将过期: {cat_stats['expiring_soon']}")
    print(f"    默认过期天数: {cat_stats['default_expiry_days']}")
```

**输出示例**：
```
总分块数: 1000
已过期: 50
即将过期（7天内）: 20

按类别统计:
  exam:
    总数: 200
    已过期: 30
    即将过期: 10
    默认过期天数: 30
  homework:
    总数: 150
    已过期: 20
    即将过期: 10
    默认过期天数: 7
  schedule:
    总数: 300
    已过期: 0
    即将过期: 0
    默认过期天数: 0
```

### 3. 手动检查过期内容

```python
# 检查并标记过期内容
expired_chunks = kb.check_expired_chunks()

print(f"新标记了 {len(expired_chunks)} 个过期分块")
for chunk in expired_chunks[:5]:  # 显示前5个
    print(f"  - {chunk.chunk_id}: {chunk.text[:50]}...")
    print(f"    过期时间: {datetime.fromtimestamp(chunk.expires_at).isoformat()}")
    print(f"    原因: {chunk.expiry_reason}")
```

### 4. 删除过期内容

```python
# 删除所有过期内容
deleted = kb.delete_expired_chunks()
print(f"删除了 {deleted} 个过期分块")

# 只删除超过30天的过期内容
deleted = kb.delete_expired_chunks(older_than_days=30)
print(f"删除了 {deleted} 个超过30天的过期分块")
```

### 5. 手动设置过期时间

```python
# 设置特定分块的过期时间
from datetime import datetime, timedelta

# 设置为7天后过期
expiry_time = (datetime.now() + timedelta(days=7)).timestamp()
success = kb.set_expiry(
    chunk_id="msg_123_0",
    expires_at=expiry_time,
    reason="手动设置：下周失效"
)

if success:
    print("设置成功")
else:
    print("分块不存在")
```

### 6. 延长有效期

```python
# 延长特定分块的有效期
success = kb.extend_expiry(
    chunk_id="msg_123_0",
    days=30  # 延长30天
)

if success:
    print("延长成功")
else:
    print("分块不存在")
```

### 7. 包含过期内容的检索

默认情况下，检索会自动过滤掉过期内容。如果需要查看过期内容：

```python
# 检索时包含过期内容
results = await kb.search(
    "考试安排",
    category="exam",
    include_expired=True,  # 包含过期内容
    top_k=10
)

# 在过滤方法中也可以指定
results = kb._filter_results(
    results,
    category="exam",
    include_expired=True
)
```

## 典型使用场景

### 场景 1：考试结束后自动失效

**需求**：期中考试结束后，考试安排自动失效

**流程**：
1. 系统接收到考试安排："三年级数学期中考试时间：2026年6月15日"
2. 提取考试日期：2026-06-15
3. 设置过期时间：2026-06-16（考试结束后1天）
4. 6月16日之后，该内容自动标记为过期
5. 检索时自动过滤掉该内容

**效果**：
- 考试前：检索"期中考试"可以找到该内容
- 考试后：检索"期中考试"找不到该内容，避免误导

### 场景 2：作业截止后自动失效

**需求**：作业交作业日期过后，作业布置自动失效

**流程**：
1. 系统接收到作业："今天作业：练习册第15-16页，下周一交"
2. 提取交作业日期：下周一
3. 设置过期时间：下周一
4. 下周一之后，该内容自动标记为过期
5. 检索时自动过滤掉该内容

**效果**：
- 交作业前：检索"作业"可以找到该内容
- 交作业后：检索"作业"找不到该内容，避免误导

### 场景 3：通知过期后自动失效

**需求**：通知在截止日期后自动失效

**流程**：
1. 系统接收到通知："关于举办校园运动会的通知，报名截止日期：6月20日"
2. 提取截止日期：6月20日
3. 设置过期时间：6月20日
4. 6月20日之后，该内容自动标记为过期
5. 检索时自动过滤掉该内容

**效果**：
- 截止前：检索"运动会"可以找到该内容
- 截止后：检索"运动会"找不到该内容，避免误导

### 场景 4：课表长期有效

**需求**：课表长期有效，通过版本控制更新

**流程**：
1. 系统接收到课表："计算机2301班周一第1-2节语文"
2. 设置过期时间：永不过期（0）
3. 课表通过版本控制更新，旧版本被覆盖或保留历史
4. 检索时始终可以找到课表内容

**效果**：
- 课表始终有效，不会被误删
- 通过版本控制管理课表更新

## 过期内容处理策略

### 策略 1：标记但不删除（推荐）

```env
EXPIRY_AUTO_DELETE=false
```

**优点**：
- 保留历史记录
- 可以手动恢复误过期的内容
- 存储空间充足时推荐使用

**处理方式**：
- 过期内容标记为 `is_expired=True`
- 检索时自动过滤掉
- 可以通过 `include_expired=True` 查看

### 策略 2：自动删除

```env
EXPIRY_AUTO_DELETE=true
```

**优点**：
- 节省存储空间
- 自动清理过期内容

**处理方式**：
- 过期内容自动删除
- 无法恢复
- 存储空间有限时推荐使用

### 策略 3：定期清理

```python
# 每天检查过期内容
expired = kb.check_expired_chunks()
print(f"标记了 {len(expired)} 个过期分块")

# 每月删除超过30天的过期内容
deleted = kb.delete_expired_chunks(older_than_days=30)
print(f"删除了 {deleted} 个过期分块")
```

## 性能说明

### 过期检测性能

| 操作 | 耗时 | 说明 |
|------|------|------|
| 计算过期时间 | <1ms | 在添加内容时计算 |
| 检查过期状态 | O(n) | 遍历所有分块 |
| 标记过期内容 | O(n) | 需要保存索引 |

### 检索性能影响

| 场景 | 额外开销 | 说明 |
|------|----------|------|
| 无过期内容 | 0ms | 无额外开销 |
| 有过期内容 | <1ms | 内存中过滤，几乎无开销 |

### 优化建议

1. **定期检查过期**：按配置的间隔检查，避免每次检索都检查
2. **批量处理**：一次性标记或删除多个过期内容
3. **合理设置过期时间**：避免过短导致频繁过期，过长导致内容过时

## 代码变更

### 新增字段

- `expires_at`: 过期时间戳（0表示永不过期）
- `is_expired`: 是否已过期
- `expiry_reason`: 过期原因

### 新增方法

- `check_expired_chunks()`: 检查并标记过期分块
- `delete_expired_chunks()`: 删除过期分块
- `get_expiry_stats()`: 获取过期统计
- `set_expiry()`: 手动设置过期时间
- `extend_expiry()`: 延长有效期

### 新增配置

- `EXPIRY_ENABLED`: 是否启用时效管理
- `EXPIRY_DAYS_*`: 各类别的默认过期时间
- `EXPIRY_CHECK_INTERVAL_HOURS`: 自动检查间隔
- `EXPIRY_AUTO_DELETE`: 是否自动删除

## 相关文档

- [去重与版本控制](DEDUP_VERSIONING.md)
- [检索过滤功能](SEARCH_FILTERS.md)
- [Rerank 功能](RERANK.md)
- [操作日志功能](OPERATION_LOGS.md)
