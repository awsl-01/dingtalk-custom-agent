# 知识库维护提醒功能

## 功能概述

知识库现在支持智能维护提醒，自动检测低频和无效知识块，帮助管理员保持知识库质量。

### 核心功能

1. **使用统计**：记录每个知识块的访问次数和最后访问时间
2. **低频检测**：识别超过指定天数未被检索的知识块
3. **无效检测**：识别长期未被使用的知识块
4. **维护报告**：生成详细的维护建议报告
5. **批量清理**：支持试运行和实际清理低频知识块

## 配置参数

```env
# 启用使用统计
USAGE_STATS_ENABLED=true

# 低频知识阈值（天数）：超过此天数未被检索的知识块视为低频
LOW_FREQUENCY_DAYS=30

# 无效知识阈值（天数）：超过此天数未被检索的知识块视为无效
USELESS_DAYS=90

# 最小访问次数：低于此次数且超过低频阈值的知识块需要审核
MIN_ACCESS_COUNT=3

# 维护提醒检查间隔（小时，默认7天）
MAINTENANCE_CHECK_INTERVAL_HOURS=168
```

## 使用方法

### 1. 查看使用统计

```python
from agent.knowledge_base_v2 import get_knowledge_base

kb = get_knowledge_base(school_dir, corp_id)

# 获取使用统计
stats = kb.get_usage_stats()

print(f"总分块数: {stats['total_chunks']}")
print(f"从未访问: {stats['never_accessed']}")
print(f"低频知识: {stats['low_frequency']}")
print(f"无效知识: {stats['useless']}")

print(f"\n按访问次数分布:")
for range_str, count in stats['by_access_count'].items():
    print(f"  {range_str}: {count}")

print(f"\n访问次数 Top 10:")
for item in stats['top_accessed']:
    print(f"  {item['text_preview'][:50]}... ({item['access_count']}次)")

print(f"\n最近访问 Top 10:")
for item in stats['recently_accessed']:
    print(f"  {item['text_preview'][:50]}... ({item['last_accessed']})")
```

**输出示例**：
```
总分块数: 1000
从未访问: 150
低频知识: 80
无效知识: 30

按访问次数分布:
  0: 150
  1-5: 400
  6-20: 300
  21-100: 120
  100+: 30

访问次数 Top 10:
  计算机2301班周一课表... (256次)
  三年级数学期中考试安排... (189次)
  教师通讯录... (145次)
  ...
```

### 2. 检查是否需要维护

```python
# 检查是否需要维护
suggestions = kb.check_maintenance_needed()

print(suggestions['summary'])

print(f"\n需要人工审核: {len(suggestions['needs_review'])} 个")
print(f"建议清理: {len(suggestions['useless'])} 个")
print(f"从未访问: {len(suggestions['never_accessed_old'])} 个")
```

**输出示例**：
```
⚠️ 发现 45 个需要关注的知识块：

📋 需要人工审核：20 个
   （访问次数少于 3 次，且超过 30 天未访问）

🗑️ 建议清理：15 个
   （超过 90 天未访问）

❓ 从未访问：10 个
   （创建超过 30 天，从未被检索到）
```

### 3. 生成维护报告

```python
# 生成详细维护报告
report = kb.get_maintenance_report()
print(report)
```

**输出示例**：
```
============================================================
  知识库维护报告
============================================================

⚠️ 发现 45 个需要关注的知识块：

📋 需要人工审核：20 个
   （访问次数少于 3 次，且超过 30 天未访问）

🗑️ 建议清理：15 个
   （超过 90 天未访问）

❓ 从未访问：10 个
   （创建超过 30 天，从未被检索到）

------------------------------------------------------------
📋 需要人工审核的知识块（20 个）
------------------------------------------------------------
1. [课表] 计算机2302班周一第1-2节英语...
   访问次数: 1, 最后访问: 45 天前
   最后查询: 计算机2302课表

2. [考试] 四年级语文单元测验安排...
   访问次数: 0, 最后访问: 60 天前

...

------------------------------------------------------------
🗑️ 建议清理的知识块（15 个）
------------------------------------------------------------
1. [通知] 关于举办校园运动会的通知...
   访问次数: 2, 最后访问: 95 天前

...

------------------------------------------------------------
❓ 从未访问的知识块（10 个）
------------------------------------------------------------
1. [其他] 学校简介...
   创建于 45 天前, 来源: 李老师

...

============================================================
  维护建议
============================================================

1. 对「需要审核」的知识块，建议人工检查内容是否准确、是否有用
2. 对「建议清理」的知识块，如果确认无用可以删除
3. 对「从未访问」的知识块，考虑是否需要优化关键词或删除
4. 定期运行维护检查，保持知识库质量
```

### 4. 清理低频知识块

#### 试运行（推荐）

```python
# 试运行：查看哪些知识块会被清理
result = kb.cleanup_low_frequency(
    days=30,              # 超过30天未访问
    min_access_count=3,   # 访问次数少于3次
    dry_run=True          # 试运行，不实际删除
)

print(f"发现 {result['total_candidates']} 个候选知识块")
for chunk in result['chunks'][:10]:
    print(f"  - {chunk['text_preview'][:50]}... (访问{chunk['access_count']}次)")
```

#### 实际清理

```python
# 实际清理
result = kb.cleanup_low_frequency(
    days=30,
    min_access_count=3,
    dry_run=False  # 实际删除
)

print(f"已清理 {result['deleted']} 个低频知识块")
```

## 自动维护提醒

### 配置定时任务

可以在钉钉机器人中配置定时任务，定期检查并发送提醒：

```python
import asyncio
from datetime import datetime

async def maintenance_check_task():
    """定期维护检查任务"""
    while True:
        try:
            # 检查是否需要维护
            suggestions = kb.check_maintenance_needed()

            total_issues = (
                len(suggestions['needs_review']) +
                len(suggestions['useless']) +
                len(suggestions['never_accessed_old'])
            )

            if total_issues > 0:
                # 发送提醒
                message = f"📚 知识库维护提醒\n\n{suggestions['summary']}"
                # 通过钉钉发送消息...

            # 等待下次检查
            await asyncio.sleep(MAINTENANCE_CHECK_INTERVAL_HOURS * 3600)

        except Exception as e:
            logger.error(f"维护检查失败: {e}")
            await asyncio.sleep(3600)  # 失败后1小时重试
```

### 钉钉机器人命令

用户可以通过钉钉发送以下命令：

- `知识库维护报告`：查看完整维护报告
- `知识库使用统计`：查看使用统计
- `清理低频知识`：清理低频知识块（需要确认）

## 知识块生命周期

### 生命周期阶段

```
创建 → 活跃 → 低频 → 无效 → 清理
  ↓      ↓      ↓      ↓
  0天   被频繁   30天    90天
        检索    未访问   未访问
```

### 各阶段处理建议

| 阶段 | 特征 | 处理建议 |
|------|------|----------|
| **创建** | 新添加的知识 | 等待被检索 |
| **活跃** | 频繁被检索 | 正常使用 |
| **低频** | 超过30天未访问 | 人工审核，考虑优化关键词 |
| **无效** | 超过90天未访问 | 考虑删除或归档 |
| **清理** | 已删除 | 从索引中移除 |

## 统计指标说明

### 访问次数分布

| 范围 | 说明 |
|------|------|
| 0 | 从未被检索到 |
| 1-5 | 低频使用 |
| 6-20 | 中等使用 |
| 21-100 | 高频使用 |
| 100+ | 热门知识 |

### 低频知识判定

满足以下条件之一即为低频知识：

1. **从未访问**：创建超过 `LOW_FREQUENCY_DAYS` 天，且从未被检索到
2. **访问次数少**：访问次数少于 `MIN_ACCESS_COUNT` 次，且超过 `LOW_FREQUENCY_DAYS` 天未访问

### 无效知识判定

满足以下条件即为无效知识：

- 超过 `USELESS_DAYS` 天未被访问

## 最佳实践

### 1. 定期检查

建议每周运行一次维护检查：

```python
# 每周一早上检查
if datetime.now().weekday() == 0:  # 周一
    report = kb.get_maintenance_report()
    # 发送报告...
```

### 2. 分批清理

不要一次性清理太多知识块，建议分批进行：

```python
# 先清理最无效的（90天以上）
result = kb.cleanup_low_frequency(days=90, dry_run=False)

# 观察一周后，再清理低频的（30天以上）
result = kb.cleanup_low_frequency(days=30, min_access_count=3, dry_run=False)
```

### 3. 保留备份

清理前先导出备份：

```python
# 导出备份
kb.export_with_trace("backup_before_cleanup.json", format="json")

# 然后再清理
result = kb.cleanup_low_frequency(days=90, dry_run=False)
```

### 4. 人工审核

对于「需要审核」的知识块，建议人工检查：

```python
suggestions = kb.check_maintenance_needed()

for item in suggestions['needs_review']:
    print(f"审核: {item['text_preview']}")
    # 人工判断是否保留...
```

## 性能说明

| 操作 | 耗时 | 说明 |
|------|------|------|
| 更新访问统计 | <1ms | 在检索时自动更新 |
| 获取使用统计 | O(n) | 遍历所有分块 |
| 检查维护需求 | O(n) | 遍历所有分块 |
| 清理低频知识 | O(n) | 需要重建索引 |

## 代码变更

### DocumentChunk 新增字段

- `last_accessed_at`: 最后访问时间
- `access_count`: 访问次数
- `last_query`: 最后一次查询词

### KnowledgeBase 新增方法

- `_update_access_stats()`: 更新访问统计
- `get_usage_stats()`: 获取使用统计
- `check_maintenance_needed()`: 检查是否需要维护
- `get_maintenance_report()`: 生成维护报告
- `cleanup_low_frequency()`: 清理低频知识块

### 新增配置

- `USAGE_STATS_ENABLED`: 启用使用统计
- `LOW_FREQUENCY_DAYS`: 低频知识阈值（天数）
- `USELESS_DAYS`: 无效知识阈值（天数）
- `MIN_ACCESS_COUNT`: 最小访问次数
- `MAINTENANCE_CHECK_INTERVAL_HOURS`: 维护检查间隔

## 相关文档

- [时效管理功能](EXPIRY_MANAGEMENT.md)
- [知识溯源功能](KNOWLEDGE_TRACEABILITY.md)
- [操作日志功能](OPERATION_LOGS.md)
