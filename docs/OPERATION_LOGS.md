# 知识库操作日志功能

## 功能概述

知识库现在支持操作日志功能，可以记录以下操作：
- **add**: 添加消息到知识库
- **search**: 搜索知识库
- **delete**: 删除知识库内容
- **export**: 导出知识库
- **update_schedule**: 更新课表

## 日志存储位置

操作日志存储在各学校的 `logs` 目录下：
```
knowledge/
└── {corp_id}/
    └── logs/
        └── operation_logs.jsonl
```

## 查看日志的方法

### 1. 通过钉钉机器人命令

用户可以通过发送以下命令查看日志：

- **查看操作统计**：`知识库日志统计` 或 `操作日志统计`
- **查看最近操作**：`知识库日志` 或 `操作日志`
- **查看指定类型操作**：`搜索日志`、`添加日志`、`删除日志`

### 2. 通过代码查询

```python
from agent.knowledge_base_v2 import get_knowledge_base

# 获取知识库实例
kb = get_knowledge_base(school_dir, corp_id)

# 查询最近 100 条日志
logs = kb.query_operation_logs(limit=100)

# 查询指定操作类型的日志
search_logs = kb.query_operation_logs(operation="search", limit=50)

# 查询指定用户的操作
user_logs = kb.query_operation_logs(user_id="user123", limit=50)

# 查询时间范围内的日志
from datetime import datetime, timedelta
start = (datetime.now() - timedelta(days=7)).isoformat()
recent_logs = kb.query_operation_logs(start_time=start, limit=1000)

# 获取操作统计
stats = kb.get_operation_stats(days=7)
print(stats)
# 输出示例:
# {
#     "total_operations": 150,
#     "by_operation": {"search": 100, "add": 30, "delete": 5, "export": 15},
#     "by_user": {"张老师": 80, "李老师": 70},
#     "by_status": {"success": 145, "failed": 5},
#     "daily": {"2026-05-30": 20, "2026-05-31": 30, ...}
# }
```

### 3. 导出日志

```python
# 导出为 JSON 格式
kb.export_operation_logs("logs_export.json", format="json")

# 导出为 CSV 格式（可用 Excel 打开）
kb.export_operation_logs("logs_export.csv", format="csv")
```

### 4. 清理旧日志

```python
# 清理 90 天前的日志
cleared = kb.clear_old_operation_logs(days=90)
print(f"清理了 {cleared} 条旧日志")
```

## 日志字段说明

每条日志包含以下字段：

| 字段 | 说明 | 示例 |
|------|------|------|
| timestamp | 操作时间 | 2026-05-31T10:30:00.123456 |
| operation | 操作类型 | search |
| user_id | 用户 ID | user123 |
| user_nick | 用户昵称 | 张老师 |
| query | 查询内容（搜索时） | 课程安排 |
| source_type | 来源类型（添加时） | text/image/file |
| source_id | 来源 ID | msg_123456 |
| file_name | 文件名 | 课表.xlsx |
| result_count | 结果数量 | 5 |
| details | 其他详情 | 方法=hybrid, 耗时=0.5s |
| status | 操作状态 | success/failed/skipped |

## 使用场景

1. **审计追踪**：查看谁在什么时候查询了什么内容
2. **使用统计**：了解知识库的使用频率和热门查询
3. **问题排查**：当出现问题时，查看相关操作记录
4. **容量规划**：根据使用情况调整知识库配置

## 注意事项

1. 日志文件会持续增长，建议定期清理旧日志
2. 日志记录是异步写入的，不会影响主要功能的性能
3. 敏感信息（如查询内容）会被记录，请注意隐私保护
4. 导出 CSV 格式时，使用 UTF-8-BOM 编码，可直接用 Excel 打开

---

## 管理员终端查看工具

### 工具位置

`scripts/view_logs.py`

### 使用方法

#### 1. 查看所有可用的企业 ID
```bash
python scripts/view_logs.py --list
```

#### 2. 查看所有企业汇总统计（管理员模式）
```bash
python scripts/view_logs.py --all --stats
```

输出示例：
```
============================================================
  所有企业知识库操作统计 (最近 7 天)
============================================================

  总操作数: 350

  按企业:
    corp_001                       200 次
    corp_002                       150 次

  按操作类型:
    search                       200 次
    add                          100 次
    export                        30 次
    delete                        20 次

  按用户 (Top 10):
    张老师                       120 次
    李老师                       100 次
    王老师                        80 次
```

#### 3. 查看所有企业操作记录
```bash
python scripts/view_logs.py --all
```

#### 4. 按操作类型过滤
```bash
# 只看搜索操作
python scripts/view_logs.py --all --operation search

# 只看添加操作
python scripts/view_logs.py --all --operation add
```

#### 5. 按用户过滤
```bash
python scripts/view_logs.py --all --user 用户ID
```

#### 6. 调整时间范围和显示数量
```bash
# 查看最近 30 天，最多 200 条
python scripts/view_logs.py --all --days 30 --limit 200
```

#### 7. 导出所有企业日志
```bash
# 导出为 CSV（可用 Excel 打开）
python scripts/view_logs.py --all --export all_logs.csv

# 导出为 JSON
python scripts/view_logs.py --all --export all_logs.json
```

#### 8. 清理所有企业的旧日志
```bash
# 清理 90 天前的日志
python scripts/view_logs.py --all --clear 90
```

#### 9. 查看单个企业日志
```bash
# 查看指定企业的统计
python scripts/view_logs.py --corp_id 你的企业ID --stats

# 查看指定企业的操作记录
python scripts/view_logs.py --corp_id 你的企业ID
```

### 快捷方式（Windows）

创建 `view_logs.bat` 文件：
```bat
@echo off
D:\miniconda\python.exe d:\claude\scripts\view_logs.py %*
```

然后直接使用：
```bash
view_logs.bat --all --stats
view_logs.bat --all
view_logs.bat --list
```
