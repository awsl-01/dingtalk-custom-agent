# 知识库检索过滤功能

## 功能概述

知识库现在支持多种过滤条件，可以精确筛选检索结果：

1. **按类别过滤**：只看课表、考试、通讯录等特定类型的内容
2. **按时间过滤**：只看近期（如最近一周、一个月）的内容
3. **按来源类型过滤**：只看文本、图片或文件

## 支持的过滤条件

### 1. 内容类别（category）

系统会自动对每条消息进行分类：

| 类别 ID | 中文名称 | 说明 | 示例关键词 |
|---------|----------|------|-----------|
| `schedule` | 课表 | 课程安排、教室、调课 | 课表、课程安排、周一第1节 |
| `exam` | 考试 | 考试安排、成绩 | 期中考试、期末考试、成绩 |
| `contact` | 通讯录 | 联系方式、电话 | 电话、手机、联系方式 |
| `homework` | 作业 | 作业布置、练习 | 作业、练习、习题 |
| `notice` | 通知 | 通知、公告 | 通知、公告、放假 |
| `teaching` | 教学 | 教案、课件 | 教案、课件、教学计划 |
| `student` | 学生 | 学生信息、考勤 | 学生名单、考勤、请假 |
| `other` | 其他 | 未分类内容 | - |

### 2. 时间过滤

- `start_time_filter`：开始时间（时间戳）
- `end_time_filter`：结束时间（时间戳）

### 3. 来源类型（source_type）

- `text`：文本消息
- `image`：图片（OCR 提取）
- `file`：文件（PDF、Word、Excel 等）

## 使用方法

### 1. 代码调用

```python
from agent.knowledge_base_v2 import get_knowledge_base
from datetime import datetime, timedelta
import time

kb = get_knowledge_base(school_dir, corp_id)

# 示例 1：只看课表类内容
results = await kb.search(
    "计算机2301班周一课程",
    category="schedule",
    top_k=5
)

# 示例 2：只看考试安排
results = await kb.search(
    "期中考试时间",
    category="exam",
    top_k=5
)

# 示例 3：只看近一周的内容
one_week_ago = time.time() - 7 * 24 * 3600
results = await kb.search(
    "课程安排",
    start_time_filter=one_week_ago,
    top_k=5
)

# 示例 4：只看通讯录信息
results = await kb.search(
    "张老师电话",
    category="contact",
    top_k=5
)

# 示例 5：只看文件类内容
results = await kb.search(
    "教学计划",
    source_type="file",
    top_k=5
)

# 示例 6：组合过滤 - 近期考试安排
results = await kb.search(
    "考试安排",
    category="exam",
    start_time_filter=one_week_ago,
    top_k=5
)

# 示例 7：禁用 Rerank，加快速度
results = await kb.search(
    "课程安排",
    category="schedule",
    use_rerank=False,
    top_k=5
)
```

### 2. 获取可用分类

```python
# 获取所有分类及其数量
categories = kb.get_categories()
print(categories)
# 输出：{'课表': 150, '考试': 80, '通知': 60, '通讯录': 40, '作业': 30, '教学': 20, '学生': 15, '其他': 50}

# 获取分类 ID 列表
category_ids = kb.get_available_category_ids()
print(category_ids)
# 输出：['schedule', 'exam', 'contact', 'homework', 'notice', 'teaching', 'student', 'other']
```

### 3. 查看分类统计

```python
# 获取知识库统计（包含分类统计）
stats = kb.get_stats()

print(f"总分块数: {stats.total_chunks}")
print(f"分类统计: {stats.categories}")
# 输出：{'课表': 150, '考试': 80, '通知': 60, ...}
```

## 典型使用场景

### 场景 1：查询课表

```python
# 用户问：计算机2301班周一有什么课？
results = await kb.search(
    "计算机2301班周一课程",
    category="schedule",
    top_k=3
)

# 返回结果只包含课表相关内容
for result in results:
    print(f"[{result.score:.2f}] {result.chunk.text[:100]}")
```

### 场景 2：查询考试安排

```python
# 用户问：五年级数学期末考试是什么时候？
results = await kb.search(
    "五年级数学期末考试时间",
    category="exam",
    top_k=3
)

# 返回结果只包含考试相关内容
for result in results:
    print(f"[{result.score:.2f}] {result.chunk.text[:100]}")
```

### 场景 3：查询联系方式

```python
# 用户问：张老师的电话是多少？
results = await kb.search(
    "张老师联系方式",
    category="contact",
    top_k=3
)

# 返回结果只包含通讯录相关内容
for result in results:
    print(f"[{result.score:.2f}] {result.chunk.text[:100]}")
```

### 场景 4：查询近期通知

```python
# 用户问：最近有什么通知？
one_week_ago = time.time() - 7 * 24 * 3600
results = await kb.search(
    "通知",
    category="notice",
    start_time_filter=one_week_ago,
    top_k=5
)

# 返回结果只包含近一周的通知
for result in results:
    print(f"[{result.score:.2f}] {result.chunk.text[:100]}")
```

### 场景 5：查询作业

```python
# 用户问：今天布置了什么作业？
today_start = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
results = await kb.search(
    "作业布置",
    category="homework",
    start_time_filter=today_start,
    top_k=3
)

# 返回结果只包含今天的作业
for result in results:
    print(f"[{result.score:.2f}] {result.chunk.text[:100]}")
```

## 自动分类说明

### 分类原理

系统使用关键词匹配和正则表达式对文本进行自动分类：

1. **关键词匹配**：检查文本中是否包含特定类别的关键词
2. **正则匹配**：使用正则表达式匹配特定模式（权重更高）
3. **得分排序**：选择得分最高的分类

### 分类示例

| 文本内容 | 分类结果 | 原因 |
|----------|----------|------|
| "计算机2301班周一第1-2节语文，第3-4节数学" | schedule | 包含"班"、"周一"、"第1-2节"等关键词 |
| "五年级数学期中考试时间：11月15日上午9:00" | exam | 包含"期中考试"、"时间"等关键词 |
| "张老师电话：13800138000" | contact | 包含"电话"、手机号模式 |
| "今天作业：练习册第15-16页" | homework | 包含"作业"、"练习册"等关键词 |
| "关于举办校园运动会的通知" | notice | 包含"通知"、"举办"等关键词 |
| "三年级数学教案-分数的认识" | teaching | 包含"教案"等关键词 |
| "计算机2301班学生名单" | student | 包含"学生名单"等关键词 |

### 提高分类准确率

1. **消息归档时保留原文**：分类基于原始文本，而非清洗后的文本
2. **关键词覆盖全面**：配置文件中包含常见关键词和模式
3. **正则表达式精确匹配**：如手机号、日期格式等

## 性能说明

### 过滤对性能的影响

| 过滤条件 | 额外开销 | 说明 |
|----------|----------|------|
| category | <1ms | 内存中过滤，几乎无开销 |
| time_filter | <1ms | 内存中过滤，几乎无开销 |
| source_type | <1ms | 内存中过滤，几乎无开销 |

### 检索流程

```
用户查询 + 过滤条件
    ↓
第一阶段：召回（多取 5 倍结果）
    ├── 语义检索
    └── 关键词检索
    ↓
第二阶段：过滤
    ├── 按类别过滤
    ├── 按时间过滤
    └── 按来源类型过滤
    ↓
第三阶段：Rerank 精排（可选）
    ↓
返回 Top-K 结果
```

## 代码变更

1. **DocumentChunk**: 新增 `category` 字段
2. **classify_text()**: 新增自动分类函数
3. **search()**: 新增过滤参数
4. **_filter_results()**: 新增过滤方法
5. **get_categories()**: 新增获取分类列表
6. **get_stats()**: 新增分类统计

## 相关文档

- [Rerank 功能说明](RERANK.md)
- [操作日志功能](OPERATION_LOGS.md)
