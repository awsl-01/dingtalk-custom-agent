# 结构化数据冲突检测

## 功能概述

知识库现在支持对课表和考试安排进行冲突检测，当出现以下情况时主动告警：

1. **课表冲突**：同一班级同一时间段有多门课
2. **考试冲突**：同一时间有多场考试
3. **教室冲突**：同一教室同一时间有多场考试
4. **时间重叠**：考试时间与上课时间重叠

## 检测类型

### 1. 课表冲突

| 冲突类型 | 严重程度 | 示例 |
|----------|----------|------|
| 同班同时间段多课 | ❌ 错误 | 计算机2301班周一第1节同时有语文和数学 |
| 同教师同时间段多课 | ⚠️ 警告 | 张老师周一第1节在不同班级上课 |
| 同教室同时间段多课 | ⚠️ 警告 | 教二楼301周一第1节有两个班上课 |

### 2. 考试冲突

| 冲突类型 | 严重程度 | 示例 |
|----------|----------|------|
| 同时间多场考试 | ❌ 错误 | 6月15日上午9:00同时有数学和英语考试 |
| 同教室多场考试 | ⚠️ 警告 | 教二楼301在6月15日上午9:00有两场考试 |

### 3. 时间重叠

| 冲突类型 | 严重程度 | 示例 |
|----------|----------|------|
| 考试与上课重叠 | ⚠️ 警告 | 计算机2301班周一有课，同时周一有考试 |

## 使用方法

### 1. 检测所有冲突

```python
from agent.knowledge_base_v2 import get_knowledge_base

kb = get_knowledge_base(school_dir, corp_id)

# 检测所有冲突
result = kb.detect_conflicts()

print(f"是否有冲突: {result['has_conflicts']}")
print(f"总冲突数: {result['total']}")
print(f"错误数: {result['errors']}")
print(f"警告数: {result['warnings']}")

# 打印详细报告
print(result['report'])
```

**输出示例**：
```
⚠️ 发现 3 个冲突（1 个错误，2 个警告）

📚 课表冲突：
  ❌ 【课表冲突】计算机2301班 周一第1节 有多门课程：语文, 数学

📝 考试冲突：
  ❌ 【考试冲突】2026-06-15 09:00-11:00 有多场考试：高等数学, 大学英语
  ⚠️ 【教室冲突】教二楼301 在 2026-06-15 09:00-11:00 有多场考试：高等数学, 大学英语
```

### 2. 检测指定班级的课表冲突

```python
# 检测计算机2301班的课表冲突
result = kb.detect_schedule_conflicts_for_class("计算机2301")

if result['has_conflicts']:
    print(f"发现 {result['total']} 个冲突")
    print(result['report'])
else:
    print("未发现冲突")
```

### 3. 检测指定课程的考试冲突

```python
# 检测高等数学的考试冲突
result = kb.detect_exam_conflicts_for_course("高等数学")

if result['has_conflicts']:
    print(f"发现 {result['total']} 个冲突")
    print(result['report'])
else:
    print("未发现冲突")
```

### 4. 添加课表（带冲突检测）

```python
# 添加课表
schedule_data = {
    "class": "计算机2301",
    "schedule": {
        "周一": {"第1节": "语文", "第2节": "数学", "第3节": "英语"},
        "周二": {"第1节": "物理", "第2节": "化学", "第3节": "生物"},
        # ...
    }
}

result = kb.add_schedule(schedule_data, check_conflicts=True)

if result['success']:
    print("课表添加成功")
    if result['conflicts']:
        print(f"⚠️ 有 {len(result['conflicts'])} 个警告：")
        print(result['conflict_report'])
else:
    print(f"❌ 课表添加失败: {result['message']}")
    if result['conflicts']:
        print(result['conflict_report'])
```

### 5. 添加考试安排（带冲突检测）

```python
# 添加考试安排
exam_data = {
    "course": "高等数学",
    "exam_type": "期末考试",
    "date": "2026-06-15",
    "time": "09:00-11:00",
    "classroom": "教二楼301"
}

result = kb.add_exam(exam_data, check_conflicts=True)

if result['success']:
    print("考试安排添加成功")
    if result['conflicts']:
        print(f"⚠️ 有 {len(result['conflicts'])} 个警告：")
        print(result['conflict_report'])
else:
    print(f"❌ 考试安排添加失败: {result['message']}")
    if result['conflicts']:
        print(result['conflict_report'])
```

### 6. 调课后自动检测冲突

```python
# 调课
result = kb.update_schedule(
    class_name="计算机2301",
    day1="周一", period1="第1节",
    day2="周二", period2="第1节"
)

if result['success']:
    print(f"✅ {result['message']}")

    # 调课后检测冲突
    conflicts = kb.detect_schedule_conflicts_for_class("计算机2301")
    if conflicts['has_conflicts']:
        print(f"⚠️ 调课后发现 {conflicts['total']} 个冲突：")
        print(conflicts['report'])
    else:
        print("✅ 调课后未发现冲突")
else:
    print(f"❌ {result['message']}")
```

## 典型使用场景

### 场景 1：学期初课表录入

**需求**：录入新学期课表时，自动检测是否有冲突

**流程**：
1. 用户上传课表数据
2. 系统调用 `add_schedule()` 并启用冲突检测
3. 如果发现冲突，返回冲突详情，阻止添加
4. 用户根据冲突报告修正课表
5. 重新添加，直到无冲突

**代码**：
```python
# 批量添加课表
schedules = [
    {"class": "计算机2301", "schedule": {...}},
    {"class": "计算机2302", "schedule": {...}},
]

for schedule in schedules:
    result = kb.add_schedule(schedule, check_conflicts=True)
    if not result['success']:
        print(f"❌ {schedule['class']}: {result['message']}")
        print(result['conflict_report'])
    else:
        print(f"✅ {schedule['class']}: 添加成功")
```

### 场景 2：考试安排录入

**需求**：录入考试安排时，自动检测是否有时间冲突

**流程**：
1. 用户上传考试安排
2. 系统调用 `add_exam()` 并启用冲突检测
3. 如果发现同一时间有多场考试，返回冲突详情
4. 用户根据冲突报告调整考试时间
5. 重新添加，直到无冲突

### 场景 3：调课后检查

**需求**：调课后自动检查是否产生新的冲突

**流程**：
1. 用户执行调课操作
2. 系统调用 `update_schedule()` 执行调课
3. 调课后自动检测冲突
4. 如果发现冲突，返回冲突详情
5. 用户根据冲突报告决定是否保留调课

### 场景 4：定期冲突巡检

**需求**：定期检查所有课表和考试安排是否有冲突

**流程**：
1. 定时任务调用 `detect_conflicts()`
2. 系统检测所有课表和考试安排
3. 生成冲突报告
4. 发送告警通知（如钉钉消息）

**代码**：
```python
# 定期冲突巡检
result = kb.detect_conflicts()

if result['has_conflicts']:
    # 发送告警
    alert_message = f"⚠️ 发现 {result['total']} 个冲突\n\n{result['report']}"
    # 通过钉钉发送告警...
```

## 冲突报告格式

### 文本格式

```
⚠️ 发现 3 个冲突（1 个错误，2 个警告）

📚 课表冲突：
  ❌ 【课表冲突】计算机2301班 周一第1节 有多门课程：语文, 数学

📝 考试冲突：
  ❌ 【考试冲突】2026-06-15 09:00-11:00 有多场考试：高等数学, 大学英语
  ⚠️ 【教室冲突】教二楼301 在 2026-06-15 09:00-11:00 有多场考试：高等数学, 大学英语
```

### JSON 格式

```json
{
  "has_conflicts": true,
  "total": 3,
  "errors": 1,
  "warnings": 2,
  "conflicts": [
    {
      "type": "schedule",
      "severity": "error",
      "message": "【课表冲突】计算机2301班 周一第1节 有多门课程：语文, 数学",
      "details": {
        "class": "计算机2301",
        "day": "周一",
        "period": "第1节",
        "courses": ["语文", "数学"]
      }
    },
    {
      "type": "exam",
      "severity": "error",
      "message": "【考试冲突】2026-06-15 09:00-11:00 有多场考试：高等数学, 大学英语",
      "details": {
        "date": "2026-06-15",
        "time": "09:00-11:00",
        "courses": ["高等数学", "大学英语"],
        "count": 2
      }
    }
  ],
  "report": "⚠️ 发现 3 个冲突..."
}
```

## 数据结构

### 课表数据格式

```json
{
  "class": "计算机2301",
  "schedule": {
    "周一": {
      "第1节": "语文",
      "第2节": "数学",
      "第3节": "英语",
      "第4节": "物理"
    },
    "周二": {
      "第1节": "化学",
      "第2节": "生物",
      "第3节": "历史",
      "第4节": "地理"
    }
  },
  "last_updated": "2026-05-31T10:30:00",
  "update_type": "permanent_swap"
}
```

### 考试数据格式

```json
{
  "course": "高等数学",
  "exam_type": "期末考试",
  "date": "2026-06-15",
  "time": "09:00-11:00",
  "classroom": "教二楼301",
  "seat": "",
  "note": ""
}
```

## 性能说明

| 操作 | 耗时 | 说明 |
|------|------|------|
| 检测单班级课表冲突 | <10ms | 内存中检测 |
| 检测所有课表冲突 | O(n²) | n 为课表数量 |
| 检测考试冲突 | O(n²) | n 为考试数量 |
| 添加课表（带检测） | <50ms | 包含冲突检测 |

## 代码变更

### structured_data.py

新增：
- `Conflict` 数据类
- `ConflictDetector` 类
  - `detect_schedule_conflicts()`: 检测课表冲突
  - `detect_exam_conflicts()`: 检测考试冲突
  - `check_schedule_exam_overlap()`: 检测课表与考试重叠
  - `format_conflicts_report()`: 格式化冲突报告

### knowledge_base_v2.py

新增方法：
- `detect_conflicts()`: 检测所有冲突
- `detect_schedule_conflicts_for_class()`: 检测指定班级课表冲突
- `detect_exam_conflicts_for_course()`: 检测指定课程考试冲突
- `add_schedule()`: 添加课表（带冲突检测）
- `add_exam()`: 添加考试安排（带冲突检测）

修改：
- `update_schedule()`: 调课后可选冲突检测

## 相关文档

- [结构化数据存储](SEARCH_FILTERS.md)
- [去重与版本控制](DEDUP_VERSIONING.md)
- [操作日志功能](OPERATION_LOGS.md)
