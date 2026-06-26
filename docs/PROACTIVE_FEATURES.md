# 主动智能与检索增强功能

## 功能概览

第一阶段实现的核心功能：

| 功能 | 模块 | 说明 |
|------|------|------|
| 变更主动推送 | `proactive/notifier.py` | 当考试安排、课表发生冲突或更新时，自动通知相关用户 |
| 周期性知识提醒 | `proactive/reminder.py` | 根据知识内容与当前时间主动触发提醒 |
| 低质量知识预警 | `proactive/feedback.py` | 检测高负反馈知识，提示管理员修正 |
| 检索结果可解释 | `search/explainer.py` | 返回每条结果时附带匹配原因 |
| 检索建议与纠错 | `search/suggester.py` | 自动补全和错词修正 |

---

## 一、变更主动推送

### 功能说明

当知识库中的内容发生变更时，自动通知订阅了相关类别的用户。

### 支持的变更类型

| 变更类型 | 说明 | 示例 |
|----------|------|------|
| `update` | 内容更新 | 课表变更、考试时间调整 |
| `conflict` | 冲突检测 | 同一时间段有多门课 |
| `expiry` | 即将过期 | 通知即将过期 |

### 使用方法

#### 1. 订阅变更通知

```python
from agent.knowledge_base_v2 import get_knowledge_base

kb = get_knowledge_base(school_dir, corp_id)

# 订阅课表和考试变更
await kb.subscribe_notifications(
    user_id="user_001",
    categories=["schedule", "exam"],
    channels=["dingtalk"],
    user_nick="张老师",
    conversation_id="conv_001"
)
```

#### 2. 取消订阅

```python
await kb.unsubscribe_notifications("user_001")
```

#### 3. 触发通知（自动）

当调用以下方法时，会自动触发通知：

```python
# 添加消息时检测变更
await kb.add_message(...)

# 更新课表时检测冲突
kb.update_schedule(...)

# 添加考试时检测冲突
kb.add_exam(...)
```

#### 4. 手动发送每日摘要

```python
notifier = kb.get_notifier()
await notifier.send_daily_summary()
```

### 通知消息示例

```
📚 课表变更通知 - 计算机2301班

计算机2301班 周一第1-2节 课程变更：语文 → 数学

更新者：张老师
更新时间：2026-05-31 10:30:00
```

---

## 二、周期性知识提醒

### 功能说明

根据知识内容与当前时间，主动触发提醒，例如：
- "明天有数学期中考试"
- "本周三下午体育课停课"
- "作业将在明天截止"

### 提醒类型

| 类型 | 说明 | 触发条件 |
|------|------|----------|
| `exam_tomorrow` | 明日考试提醒 | 考试日期 = 明天 |
| `schedule_change` | 今日课程变更 | 今日有课表更新 |
| `homework_due` | 作业即将截止 | 作业截止日期 ≤ 3天后 |
| `notice_deadline` | 通知即将过期 | 通知过期日期 ≤ 7天后 |

### 使用方法

#### 1. 检查提醒

```python
reminder = kb.get_reminder()

# 检查需要提醒的内容
reminders = await reminder.check_reminders()

for r in reminders:
    print(f"[{r.reminder_type}] {r.message}")
```

#### 2. 发送提醒

```python
# 检查并发送提醒
count = await kb.check_and_send_reminders()
print(f"发送了 {count} 条提醒")
```

#### 3. 获取提醒历史

```python
reminder = kb.get_reminder()

# 获取最近的提醒
history = reminder.get_reminder_history(limit=50)

# 按类型过滤
exam_reminders = reminder.get_reminder_history(reminder_type="exam_tomorrow")
```

### 提醒消息示例

```
📅 每日知识提醒 (2026-05-31)

📝 明日考试：
  • 明天有 数学期中 考试，时间：09:00-11:00，地点：教二楼301

✏️ 即将截止的作业：
  • 作业「练习册第15-16页」将在明天截止

📢 即将过期的通知：
  • 通知「校园运动会报名」将在3天后过期
```

---

## 三、低质量知识预警

### 功能说明

通过收集用户反馈（👍/👎/快速离开），识别低质量知识块，提示管理员修正。

### 反馈类型

| 类型 | 说明 | 触发条件 |
|------|------|----------|
| `positive` | 正面反馈 | 用户点击 👍 |
| `negative` | 负面反馈 | 用户点击 👎 |
| `quick_leave` | 快速离开 | 用户点击后 < 5秒返回 |

### 使用方法

#### 1. 记录反馈

```python
# 记录正面反馈
kb.record_feedback(
    chunk_id="msg_123_0",
    user_id="user_001",
    query="课程安排",
    feedback_type="positive",
    dwell_time=30.5
)

# 记录负面反馈
kb.record_feedback(
    chunk_id="msg_123_0",
    user_id="user_002",
    query="课程安排",
    feedback_type="negative"
)

# 记录快速离开
kb.record_feedback(
    chunk_id="msg_123_0",
    user_id="user_003",
    query="课程安排",
    feedback_type="quick_leave",
    dwell_time=2.5
)
```

#### 2. 获取低质量知识块

```python
# 获取低质量知识块（负反馈率 > 30%，且至少 3 次反馈）
low_quality = kb.get_low_quality_chunks(threshold=0.3, min_feedbacks=3)

for chunk in low_quality:
    print(f"知识块: {chunk['chunk_id']}")
    print(f"  负反馈率: {chunk['negative_rate']:.2%}")
    print(f"  总反馈数: {chunk['total_feedbacks']}")
```

#### 3. 获取质量报告

```python
report = kb.get_quality_report()

print(f"总反馈数: {report['total_feedbacks']}")
print(f"低质量知识块: {report['low_quality_count']}")
print(f"高频失败查询: {report['top_failed_queries']}")
```

---

## 四、检索结果可解释

### 功能说明

返回每条结果时附带匹配原因，帮助用户理解为什么这条结果被返回。

### 解释维度

| 维度 | 说明 | 分数范围 |
|------|------|----------|
| `semantic` | 语义相似度 | 0-1 |
| `keyword` | 关键词匹配 | 0-1 |
| `category` | 类别匹配 | 0/1 |
| `time` | 时间相关性 | 0-1 |
| `popularity` | 热度 | 0-1 |

### 使用方法

#### 1. 带解释的检索

```python
# 启用搜索解释
result = await kb.search(
    query="课程安排",
    category="schedule",
    include_explanation=True,
    top_k=5
)

# 获取结果
results = result["results"]
explanations = result["explanations"]

# 显示结果和解释
for i, (r, e) in enumerate(zip(results, explanations)):
    print(f"{i+1}. {r.chunk.text[:50]}...")
    print(f"   匹配原因: {e['explanation_text']}")
    print(f"   语义相似度: {e['scores']['semantic']:.2f}")
    print(f"   关键词匹配: {e['scores']['keyword']:.2f}")
    print()
```

#### 2. 解释文本示例

```
1. 计算机2301班周一第1-2节语文，第3-4节数学...
   匹配原因: 语义相似度 0.85，关键词「课程」「安排」匹配，类别匹配
   语义相似度: 0.85
   关键词匹配: 0.72

2. 三年级数学课表...
   匹配原因: 关键词「课表」匹配，时间相关
   语义相似度: 0.65
   关键词匹配: 0.45
```

---

## 五、检索建议与纠错

### 功能说明

1. **自动补全**：用户输入"下周三考数" → 自动补全"下周三数学考试安排"
2. **错词修正**：用户输入"棵表" → 提示"您是否要搜索：课表"
3. **热门建议**：根据历史查询提供热门搜索建议

### 建议来源

| 来源 | 说明 | 优先级 |
|------|------|--------|
| `correction` | 纠错建议 | 最高 |
| `history` | 查询历史 | 高 |
| `content` | 知识库内容 | 中 |
| `hot` | 热门查询 | 低 |

### 使用方法

#### 1. 获取检索建议

```python
# 获取建议
suggestions = kb.get_search_suggestions("下周三考", top_k=5)

for s in suggestions:
    print(f"[{s['source']}] {s['text']}")
```

#### 2. 纠错建议

```python
# 纠错
correction = kb.correct_query("棵表")

if correction["has_correction"]:
    print(f"原始查询: {correction['original']}")
    print(f"纠正后: {correction['corrected']}")
    print(f"纠正内容: {correction['corrections']}")
```

#### 3. 获取热门查询

```python
suggester = kb.get_search_suggester()
hot_queries = suggester.get_hot_queries(top_k=10)

for q in hot_queries:
    print(f"{q['query']}: {q['count']}次")
```

### 建议消息示例

```
输入: "下周三考"

建议:
1. [correction] 下周三数学考试
2. [history] 下周三考试安排
3. [content] 下周三数学期中考试
```

---

## 六、配置参数

### .env 配置

```env
# 主动智能配置
PROACTIVE_NOTIFICATIONS_ENABLED=true
PROACTIVE_REMINDER_ENABLED=true
PROACTIVE_REMINDER_CRON=0 7 * * *

# 检索增强配置
SEARCH_EXPLANATION_ENABLED=true
SEARCH_SUGGESTION_ENABLED=true
```

---

## 七、模块结构

```
agent/
├── knowledge_base_v2.py      # 核心知识库（已集成）
├── proactive/                # 主动智能模块
│   ├── __init__.py
│   ├── notifier.py           # 变更通知器
│   ├── reminder.py           # 周期提醒器
│   └── feedback.py           # 反馈追踪器
└── search/                   # 检索增强模块
    ├── __init__.py
    ├── explainer.py          # 结果解释器
    └── suggester.py          # 检索建议器
```

---

## 八、使用示例

### 完整使用流程

```python
from agent.knowledge_base_v2 import get_knowledge_base

# 1. 获取知识库实例
kb = get_knowledge_base(school_dir, corp_id)

# 2. 订阅变更通知
await kb.subscribe_notifications(
    user_id="user_001",
    categories=["schedule", "exam"],
    channels=["dingtalk"],
    user_nick="张老师"
)

# 3. 添加消息（自动触发变更检测）
await kb.add_message(
    text="计算机2301班周一第1-2节数学",
    source_type="text",
    source_id="msg_123",
    sender_nick="张老师"
)

# 4. 带解释的检索
result = await kb.search(
    query="课程安排",
    category="schedule",
    include_explanation=True,
    top_k=5
)

# 5. 记录用户反馈
kb.record_feedback(
    chunk_id=result["results"][0].chunk.chunk_id,
    user_id="user_001",
    query="课程安排",
    feedback_type="positive",
    dwell_time=30.0
)

# 6. 获取检索建议
suggestions = kb.get_search_suggestions("下周三")

# 7. 检查并发送提醒
await kb.check_and_send_reminders()

# 8. 获取质量报告
report = kb.get_quality_report()
```

---

## 九、相关文档

- [RAG 知识库完整功能汇报](RAG_KNOWLEDGE_BASE_OVERVIEW.md)
- [2026年功能路线图](ROADMAP_2026.md)
- [操作日志功能](OPERATION_LOGS.md)
