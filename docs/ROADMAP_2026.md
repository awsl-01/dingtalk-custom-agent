# RAG 知识库 2026 年功能路线图

## 一、功能优先级矩阵

| 优先级 | 方向 | 功能 | 价值 | 复杂度 | 建议阶段 |
|--------|------|------|------|--------|----------|
| 🔴 P0 | 主动智能 | 变更主动推送 | 高 | 中 | 第一阶段 |
| 🔴 P0 | 主动智能 | 周期性知识提醒 | 高 | 中 | 第一阶段 |
| 🔴 P0 | 检索体验 | 检索结果可解释 | 高 | 低 | 第一阶段 |
| 🟠 P1 | 主动智能 | 低质量知识预警 | 高 | 中 | 第二阶段 |
| 🟠 P1 | 检索体验 | 混合检索权重自适应 | 中 | 高 | 第二阶段 |
| 🟠 P1 | 检索体验 | 检索建议与纠错 | 中 | 中 | 第二阶段 |
| 🟠 P1 | 工程运维 | 知识快照与回滚 | 高 | 中 | 第二阶段 |
| 🟠 P1 | 工程运维 | 批量导入/导出接口 | 高 | 低 | 第二阶段 |
| 🟡 P2 | 多模态 | 图片内文字识别（OCR） | 高 | 高 | 第三阶段 |
| 🟡 P2 | 多模态 | 文件深度解析 | 中 | 高 | 第三阶段 |
| 🟡 P2 | 数据闭环 | 用户反馈循环 | 中 | 中 | 第三阶段 |
| 🟡 P2 | 数据闭环 | 检索失败分析 | 中 | 中 | 第三阶段 |
| 🟢 P3 | 多模态 | 音视频转写 | 中 | 很高 | 第四阶段 |
| 🟢 P3 | 数据闭环 | A/B测试能力 | 低 | 高 | 第四阶段 |
| 🟢 P3 | 工程运维 | 检索SLA监控 | 中 | 中 | 第四阶段 |

---

## 二、分阶段实现计划

### 第一阶段：核心价值（2-3周）

#### 1.1 变更主动推送

**目标**：当考试安排、课表发生冲突或更新时，自动通知相关用户

**设计**：
```python
class ChangeNotifier:
    """变更通知器"""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.subscribers = {}  # 订阅者配置

    def subscribe(self, user_id: str, categories: list, channels: list):
        """
        订阅变更通知

        参数:
            user_id: 用户ID
            categories: 关注的类别（schedule/exam/...）
            channels: 通知渠道（dingtalk/wechat/email）
        """
        pass

    async def notify_change(self, change_type: str, details: dict):
        """
        发送变更通知

        参数:
            change_type: 变更类型（update/conflict/expiry）
            details: 变更详情
        """
        pass

    async def notify_conflict(self, conflicts: list):
        """通知冲突"""
        pass

    async def notify_update(self, category: str, entity: str, old_value: str, new_value: str):
        """通知更新"""
        pass
```

**集成点**：
- `add_message()` → 检测变更 → 触发通知
- `update_schedule()` → 检测冲突 → 触发通知
- `add_exam()` → 检测冲突 → 触发通知

#### 1.2 周期性知识提醒

**目标**：根据知识内容与当前时间主动触发提醒

**设计**：
```python
class PeriodicReminder:
    """周期性提醒器"""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    async def check_reminders(self) -> list:
        """
        检查需要提醒的知识

        返回:
            提醒列表
        """
        reminders = []

        # 检查明天的考试
        tomorrow_exams = await self._get_exams_by_date(
            datetime.now() + timedelta(days=1)
        )
        for exam in tomorrow_exams:
            reminders.append({
                "type": "exam_tomorrow",
                "message": f"明天有{exam['course']}考试",
                "details": exam,
            })

        # 检查今天的课程变更
        today_changes = self._get_today_changes()
        for change in today_changes:
            reminders.append({
                "type": "schedule_change",
                "message": f"今日课程变更：{change['description']}",
                "details": change,
            })

        # 检查即将截止的作业
        upcoming_homework = self._get_upcoming_homework(days=3)
        for hw in upcoming_homework:
            reminders.append({
                "type": "homework_due",
                "message": f"作业即将截止：{hw['description']}",
                "details": hw,
            })

        return reminders

    async def _get_exams_by_date(self, date: datetime) -> list:
        """获取指定日期的考试"""
        pass

    def _get_today_changes(self) -> list:
        """获取今日变更"""
        pass

    def _get_upcoming_homework(self, days: int) -> list:
        """获取即将截止的作业"""
        pass
```

**定时任务**：
```python
# 每天早上7点检查提醒
@schedule.cron("0 7 * * *")
async def daily_reminder_check():
    reminders = await periodic_reminder.check_reminders()
    if reminders:
        await notifier.send_daily_reminder(reminders)
```

#### 1.3 检索结果可解释

**目标**：返回每条结果时附带匹配原因

**设计**：
```python
@dataclass
class SearchResultWithExplanation:
    """带解释的搜索结果"""
    chunk: DocumentChunk
    score: float
    match_type: str
    highlights: list
    explanation: SearchExplanation  # 新增

@dataclass
class SearchExplanation:
    """搜索解释"""
    semantic_score: float = 0.0      # 语义相似度分数
    keyword_score: float = 0.0       # 关键词匹配分数
    matched_keywords: list = None    # 匹配的关键词
    keyword_positions: dict = None   # 关键词位置
    category_match: bool = False     # 类别是否匹配
    time_relevance: float = 0.0      # 时间相关性
    explanation_text: str = ""       # 解释文本

    def to_text(self) -> str:
        """生成可读的解释文本"""
        parts = []

        if self.semantic_score > 0:
            parts.append(f"语义相似度 {self.semantic_score:.2f}")

        if self.matched_keywords:
            kw_str = "、".join(self.matched_keywords[:3])
            parts.append(f"关键词「{kw_str}」匹配")

        if self.category_match:
            parts.append("类别匹配")

        if self.time_relevance > 0:
            parts.append(f"时间相关性 {self.time_relevance:.2f}")

        return "，".join(parts) if parts else "综合匹配"
```

**修改 `search()` 方法**：
```python
async def search(self, query: str, top_k: int = TOP_K,
                 method: str = "hybrid",
                 use_rerank: bool = True,
                 category: str = None,
                 include_explanation: bool = False,  # 新增参数
                 ...) -> List[SearchResult]:
    # ... 现有逻辑 ...

    if include_explanation:
        for result in results:
            result.explanation = self._generate_explanation(query, result)

    return results
```

---

### 第二阶段：体验优化（3-4周）

#### 2.1 低质量知识预警

**目标**：检测高负反馈知识，提示管理员修正

**设计**：
```python
@dataclass
class FeedbackRecord:
    """反馈记录"""
    chunk_id: str
    user_id: str
    feedback_type: str  # positive/negative/quick_leave
    query: str
    timestamp: float

class FeedbackTracker:
    """反馈追踪器"""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.feedback_db = []  # 反馈数据库

    def record_feedback(self, chunk_id: str, user_id: str,
                       feedback_type: str, query: str):
        """记录反馈"""
        pass

    def record_quick_leave(self, chunk_id: str, user_id: str,
                          query: str, dwell_time: float):
        """记录快速离开（用户点击后很快返回）"""
        if dwell_time < 5.0:  # 少于5秒
            self.record_feedback(chunk_id, user_id, "quick_leave", query)

    def get_low_quality_chunks(self, threshold: float = 0.3) -> list:
        """
        获取低质量知识块

        参数:
            threshold: 负反馈率阈值

        返回:
            低质量知识块列表
        """
        pass

    def get_quality_report(self) -> dict:
        """生成质量报告"""
        pass
```

#### 2.2 混合检索权重自适应

**目标**：根据历史检索成功率，动态调整权重

**设计**：
```python
class AdaptiveWeightOptimizer:
    """自适应权重优化器"""

    def __init__(self):
        self.search_history = []
        self.weights = {
            "semantic": 0.6,
            "keyword": 0.4,
        }

    def record_search(self, query: str, results: list,
                     clicked_index: int, feedback: str):
        """
        记录检索结果和用户反馈

        参数:
            query: 查询词
            results: 检索结果
            clicked_index: 用户点击的结果索引
            feedback: 用户反馈
        """
        pass

    def optimize_weights(self):
        """
        根据历史数据优化权重

        算法：
        1. 统计不同权重下的检索成功率
        2. 使用梯度上升优化权重
        3. 平滑更新，避免剧烈变化
        """
        pass

    def get_current_weights(self) -> dict:
        """获取当前权重"""
        return self.weights.copy()
```

#### 2.3 检索建议与纠错

**目标**：自动补全和错词修正

**设计**：
```python
class SearchSuggestion:
    """检索建议器"""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.query_history = []  # 查询历史
        self.vocabulary = set()  # 词库

    def suggest(self, partial_query: str, top_k: int = 5) -> list:
        """
        提供检索建议

        参数:
            partial_query: 部分查询词
            top_k: 返回建议数量

        返回:
            建议列表
        """
        suggestions = []

        # 1. 基于查询历史的建议
        history_suggestions = self._suggest_from_history(partial_query)
        suggestions.extend(history_suggestions)

        # 2. 基于知识库内容的建议
        content_suggestions = self._suggest_from_content(partial_query)
        suggestions.extend(content_suggestions)

        # 3. 基于热词的建议
        hot_suggestions = self._suggest_from_hot_queries(partial_query)
        suggestions.extend(hot_suggestions)

        # 去重并返回 Top-K
        return list(dict.fromkeys(suggestions))[:top_k]

    def correct(self, query: str) -> dict:
        """
        纠错建议

        参数:
            query: 原始查询

        返回:
            {
                "original": "下周三考数",
                "corrected": "下周三数学考试",
                "corrections": [
                    {"original": "考数", "corrected": "数学考试", "type": "auto"}
                ]
            }
        """
        pass

    def _suggest_from_history(self, partial: str) -> list:
        """从历史查询中建议"""
        pass

    def _suggest_from_content(self, partial: str) -> list:
        """从知识库内容中建议"""
        pass

    def _suggest_from_hot_queries(self, partial: str) -> list:
        """从热词中建议"""
        pass
```

#### 2.4 知识快照与回滚

**目标**：支持按时间点回滚整个知识库

**设计**：
```python
class KnowledgeSnapshot:
    """知识快照管理器"""

    def __init__(self, kb: KnowledgeBase, snapshot_dir: str):
        self.kb = kb
        self.snapshot_dir = snapshot_dir
        os.makedirs(snapshot_dir, exist_ok=True)

    def create_snapshot(self, description: str = "") -> str:
        """
        创建快照

        参数:
            description: 快照描述

        返回:
            快照ID
        """
        snapshot_id = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 备份索引文件
        # 备份结构化数据
        # 备份操作日志
        # 保存快照元信息

        return snapshot_id

    def list_snapshots(self) -> list:
        """列出所有快照"""
        pass

    def restore_snapshot(self, snapshot_id: str, dry_run: bool = True) -> dict:
        """
        恢复快照

        参数:
            snapshot_id: 快照ID
            dry_run: 是否为试运行

        返回:
            恢复结果
        """
        pass

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """删除快照"""
        pass

    def compare_snapshots(self, snapshot_id1: str, snapshot_id2: str) -> dict:
        """比较两个快照的差异"""
        pass
```

#### 2.5 批量导入/导出接口

**目标**：支持 Excel/CSV 格式批量导入导出

**设计**：
```python
class BatchImporter:
    """批量导入器"""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    async def import_from_excel(self, file_path: str,
                               sheet_name: str = None,
                               mapping: dict = None) -> dict:
        """
        从 Excel 导入

        参数:
            file_path: Excel 文件路径
            sheet_name: 工作表名称
            mapping: 字段映射

        返回:
            导入结果
        """
        pass

    async def import_from_csv(self, file_path: str,
                             encoding: str = "utf-8",
                             mapping: dict = None) -> dict:
        """从 CSV 导入"""
        pass

    async def import_schedules(self, file_path: str,
                              format: str = "auto") -> dict:
        """
        批量导入课表

        支持格式：
        - 标准课表格式（周一~周五，第1~8节）
        - 自由格式（LLM解析）
        """
        pass

    async def import_exams(self, file_path: str) -> dict:
        """批量导入考试安排"""
        pass

    async def import_contacts(self, file_path: str) -> dict:
        """批量导入通讯录"""
        pass


class BatchExporter:
    """批量导出器"""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    def export_to_excel(self, output_path: str,
                       include_trace: bool = True) -> int:
        """
        导出为 Excel

        参数:
            output_path: 输出路径
            include_trace: 是否包含溯源信息

        返回:
            导出数量
        """
        pass

    def export_to_csv(self, output_path: str,
                     include_trace: bool = True) -> int:
        """导出为 CSV"""
        pass

    def export_report(self, output_path: str,
                     report_type: str = "full") -> str:
        """
        导出报告

        参数:
            output_path: 输出路径
            report_type: 报告类型（full/summary/maintenance）

        返回:
            报告路径
        """
        pass
```

---

### 第三阶段：多模态增强（4-6周）

#### 3.1 图片内文字识别（OCR）

**目标**：从截图、黑板照片、手写通知中提取文字

**设计**：
```python
class OCREngine:
    """OCR 引擎"""

    def __init__(self):
        self.strategies = {
            "local": self._ocr_local,
            "api": self._ocr_api,
            "llm": self._ocr_llm,
        }

    async def recognize(self, image_path: str,
                       strategy: str = "llm") -> dict:
        """
        识别图片中的文字

        参数:
            image_path: 图片路径
            strategy: 识别策略

        返回:
            {
                "text": "识别的文字",
                "confidence": 0.95,
                "regions": [...]  # 文字区域
            }
        """
        pass

    async def _ocr_local(self, image_path: str) -> dict:
        """本地 OCR（PaddleOCR）"""
        pass

    async def _ocr_api(self, image_path: str) -> dict:
        """API OCR（百度/腾讯）"""
        pass

    async def _ocr_llm(self, image_path: str) -> dict:
        """LLM OCR（多模态模型）"""
        pass
```

**集成到 `add_message()`**：
```python
if source_type == "image":
    # 自动 OCR
    ocr_result = await ocr_engine.recognize(file_path)
    text = ocr_result["text"]
```

#### 3.2 文件深度解析

**目标**：对 PDF/Word/PPT 中的表格、图表进行结构化抽取

**设计**：
```python
class DeepFileParser:
    """深度文件解析器"""

    async def parse_pdf(self, file_path: str) -> dict:
        """
        深度解析 PDF

        返回:
            {
                "text": "全文文本",
                "tables": [...],      # 表格数据
                "images": [...],      # 图片
                "headers": [...],     # 页眉
                "footers": [...],     # 页脚
                "metadata": {...}     # 元数据
            }
        """
        pass

    async def parse_word(self, file_path: str) -> dict:
        """深度解析 Word"""
        pass

    async def parse_ppt(self, file_path: str) -> dict:
        """深度解析 PPT"""
        pass

    async def parse_excel(self, file_path: str) -> dict:
        """深度解析 Excel"""
        pass
```

#### 3.3 音视频转写

**目标**：自动转写网课片段或语音通知

**设计**：
```python
class AudioTranscriber:
    """音频转写器"""

    async def transcribe(self, audio_path: str,
                        language: str = "zh") -> dict:
        """
        转写音频

        参数:
            audio_path: 音频路径
            language: 语言

        返回:
            {
                "text": "转写文字",
                "segments": [...],  # 时间段
                "duration": 120.5   # 时长
            }
        """
        pass


class VideoTranscriber:
    """视频转写器"""

    async def transcribe(self, video_path: str,
                        extract_audio: bool = True) -> dict:
        """
        转写视频

        参数:
            video_path: 视频路径
            extract_audio: 是否提取音频

        返回:
            {
                "text": "转写文字",
                "frames": [...],    # 关键帧
                "duration": 3600.0  # 时长
            }
        """
        pass
```

---

### 第四阶段：数据闭环（3-4周）

#### 4.1 用户反馈循环

**目标**：检索结果支持 👍/👎，反馈数据用于优化

**设计**：
```python
class FeedbackCollector:
    """反馈收集器"""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    def record_feedback(self, query: str, chunk_id: str,
                       user_id: str, feedback: str,
                       dwell_time: float = 0):
        """
        记录反馈

        参数:
            query: 查询词
            chunk_id: 知识块ID
            user_id: 用户ID
            feedback: positive/negative
            dwell_time: 停留时间
        """
        pass

    def get_feedback_stats(self) -> dict:
        """获取反馈统计"""
        pass

    def get_improvement_suggestions(self) -> list:
        """生成改进建议"""
        pass
```

#### 4.2 检索失败分析

**目标**：统计哪些查询得不到满意结果，自动聚类为"知识缺口"

**设计**：
```python
class SearchFailureAnalyzer:
    """检索失败分析器"""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    def record_failure(self, query: str, user_id: str,
                      result_count: int, clicked: bool):
        """记录检索失败"""
        pass

    def analyze_failures(self, days: int = 30) -> dict:
        """
        分析检索失败

        返回:
            {
                "total_failures": 150,
                "top_failed_queries": [...],
                "knowledge_gaps": [...],  # 知识缺口聚类
                "suggestions": [...]      # 补充建议
            }
        """
        pass

    def cluster_failures(self, failures: list) -> list:
        """聚类失败查询"""
        pass
```

#### 4.3 A/B 测试能力

**目标**：对不同检索策略进行效果对比

**设计**：
```python
class ABTestManager:
    """A/B 测试管理器"""

    def __init__(self):
        self.experiments = {}

    def create_experiment(self, name: str,
                         variants: list,
                         traffic_split: list) -> str:
        """
        创建实验

        参数:
            name: 实验名称
            variants: 变体配置
            traffic_split: 流量分配

        返回:
            实验ID
        """
        pass

    def get_variant(self, experiment_id: str,
                   user_id: str) -> dict:
        """获取用户对应的变体"""
        pass

    def record_metric(self, experiment_id: str,
                     variant: str, metric: str, value: float):
        """记录指标"""
        pass

    def analyze_results(self, experiment_id: str) -> dict:
        """分析实验结果"""
        pass
```

---

### 第五阶段：运维监控（2-3周）

#### 5.1 检索 SLA 监控

**目标**：监控 P99 延迟、索引更新延迟、向量库健康状态

**设计**：
```python
class SLAMonitor:
    """SLA 监控器"""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.metrics = {
            "search_latency": [],
            "index_update_latency": [],
            "error_rate": [],
        }

    def record_search_latency(self, latency: float):
        """记录检索延迟"""
        pass

    def record_index_update_latency(self, latency: float):
        """记录索引更新延迟"""
        pass

    def check_health(self) -> dict:
        """
        健康检查

        返回:
            {
                "status": "healthy/degraded/unhealthy",
                "search_p99": 0.5,
                "index_update_p99": 2.0,
                "error_rate": 0.01,
                "vector_db_status": "ok",
                "issues": []
            }
        """
        pass

    def get_sla_report(self, days: int = 7) -> dict:
        """生成 SLA 报告"""
        pass

    def alert_if_needed(self, health: dict):
        """根据健康状态发送告警"""
        pass
```

---

## 三、技术架构建议

### 3.1 模块化设计

```
agent/
├── knowledge_base_v2.py      # 核心知识库
├── proactive/                # 主动智能模块（新增）
│   ├── __init__.py
│   ├── notifier.py           # 变更通知器
│   ├── reminder.py           # 周期提醒器
│   └── feedback.py           # 反馈追踪器
├── search/                   # 检索增强模块（新增）
│   ├── __init__.py
│   ├── explainer.py          # 结果解释器
│   ├── suggester.py          # 检索建议器
│   └── optimizer.py          # 权重优化器
├── multimodal/               # 多模态模块（新增）
│   ├── __init__.py
│   ├── ocr.py                # OCR 引擎
│   ├── parser.py             # 文件深度解析
│   └── transcriber.py        # 音视频转写
├── maintenance/              # 运维模块（新增）
│   ├── __init__.py
│   ├── snapshot.py           # 快照管理
│   ├── batch.py              # 批量导入导出
│   └── monitor.py            # SLA 监控
└── structured_data.py        # 结构化数据处理
```

### 3.2 配置管理

```env
# 主动智能配置
PROACTIVE_NOTIFICATIONS_ENABLED=true
PROACTIVE_REMINDER_ENABLED=true
PROACTIVE_REMINDER_CRON="0 7 * * *"

# 检索增强配置
SEARCH_EXPLANATION_ENABLED=true
SEARCH_SUGGESTION_ENABLED=true
SEARCH_WEIGHT_ADAPTIVE_ENABLED=true

# 多模态配置
MULTIMODAL_OCR_ENABLED=true
MULTIMODAL_OCR_STRATEGY=llm
MULTIMODAL_AUDIO_ENABLED=false

# 运维配置
SNAPSHOT_ENABLED=true
SNAPSHOT_MAX_COUNT=10
SLA_MONITOR_ENABLED=true
SLA_P99_THRESHOLD=2.0
```

### 3.3 依赖管理

```txt
# 多模态处理
paddleocr>=2.7.0
paddlepaddle>=2.5.0
whisper>=1.0.0
python-docx>=0.8.11
python-pptx>=0.6.21
PyMuPDF>=1.23.0

# 数据处理
pandas>=2.0.0
openpyxl>=3.1.0

# 监控
prometheus-client>=0.17.0
```

---

## 四、实施建议

### 4.1 第一阶段（2-3周）

**重点**：主动智能 + 检索可解释

1. **Week 1**：实现变更主动推送
   - 创建 `proactive/notifier.py`
   - 集成到 `add_message()` 和 `update_schedule()`
   - 钉钉消息推送

2. **Week 2**：实现周期性知识提醒
   - 创建 `proactive/reminder.py`
   - 定时任务调度
   - 提醒消息模板

3. **Week 3**：实现检索结果可解释
   - 创建 `search/explainer.py`
   - 修改 `search()` 返回结构
   - 前端展示适配

### 4.2 第二阶段（3-4周）

**重点**：体验优化 + 工程能力

1. **Week 4-5**：低质量知识预警 + 反馈收集
   - 创建 `proactive/feedback.py`
   - 反馈数据存储
   - 质量报告生成

2. **Week 6**：权重自适应 + 检索建议
   - 创建 `search/optimizer.py`
   - 创建 `search/suggester.py`
   - A/B 测试框架

3. **Week 7**：快照回滚 + 批量导入导出
   - 创建 `maintenance/snapshot.py`
   - 创建 `maintenance/batch.py`
   - Excel/CSV 支持

### 4.3 第三阶段（4-6周）

**重点**：多模态能力

1. **Week 8-10**：OCR 集成
   - 创建 `multimodal/ocr.py`
   - 集成 PaddleOCR 或 LLM OCR
   - 图片消息自动识别

2. **Week 11-12**：文件深度解析
   - 创建 `multimodal/parser.py`
   - PDF/Word/PPT 表格提取
   - 结构化数据生成

3. **Week 13**：音视频转写
   - 创建 `multimodal/transcriber.py`
   - Whisper 集成
   - 视频关键帧提取

### 4.4 第四阶段（3-4周）

**重点**：数据闭环

1. **Week 14-15**：用户反馈循环
   - 反馈数据持久化
   - 反馈分析报告
   - 改进建议生成

2. **Week 16**：检索失败分析
   - 失败查询聚类
   - 知识缺口识别
   - 补充建议生成

3. **Week 17**：A/B 测试
   - 实验管理框架
   - 指标收集
   - 结果分析

### 4.5 第五阶段（2-3周）

**重点**：运维监控

1. **Week 18-19**：SLA 监控
   - 创建 `maintenance/monitor.py`
   - 指标收集
   - 告警规则

2. **Week 20**：完善与测试
   - 集成测试
   - 性能优化
   - 文档完善

---

## 五、风险与挑战

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| OCR 准确率不足 | 知识质量下降 | 多策略融合，人工校验 |
| 权重自适应不稳定 | 检索效果波动 | 平滑更新，设置边界 |
| 音视频转写成本高 | 运营成本增加 | 按需启用，缓存结果 |
| A/B 测试样本不足 | 结论不可靠 | 长期运行，积累数据 |
| 快照占用存储空间 | 存储成本增加 | 限制快照数量，定期清理 |

---

## 六、成功指标

| 指标 | 当前基线 | 目标值 | 衡量方式 |
|------|----------|--------|----------|
| 检索准确率 | 70-80% | 90%+ | 人工评估 |
| 用户满意度 | - | 85%+ | 反馈统计 |
| 知识利用率 | - | 60%+ | 访问统计 |
| 检索延迟 P99 | - | <2s | 监控系统 |
| 主动提醒覆盖率 | 0% | 90%+ | 提醒统计 |
| 知识新鲜度 | - | 95%+ | 过期统计 |

---

## 七、总结

本路线图规划了 **5 个阶段、15 个核心功能**，预计 **16-20 周**完成：

1. **第一阶段**（2-3周）：主动智能 + 检索可解释 → **核心价值**
2. **第二阶段**（3-4周）：体验优化 + 工程能力 → **用户体验**
3. **第三阶段**（4-6周）：多模态能力 → **数据来源**
4. **第四阶段**（3-4周）：数据闭环 → **持续优化**
5. **第五阶段**（2-3周）：运维监控 → **系统稳定**

**建议优先实施第一阶段**，快速交付核心价值，然后根据用户反馈调整后续优先级。
