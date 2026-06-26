# 学校智能助手 - 项目文档

## 项目概述

基于钉钉机器人的学校智能助手，支持：
- AI 对话（知识库增强 + 网络搜索）
- PPT 自动生成（教育课件、模板设计）
- 教学资源搜索（习题、素材、新闻）
- 消息自动归档（文本/图片/文件 → 知识库）
- 结构化数据解析（课表、考试、通讯录）
- 资产管理（录入、查询、借用、归还、统计）

## 目录结构与职责

```
d:/claude/
├── main.py                    # 钉钉机器人入口（Stream 模式）
├── config.py                  # 全局配置（环境变量加载）
├── requirements.txt           # Python 依赖
├── start.bat                  # Windows 启动脚本
├── .env / .env.example        # 环境变量（钉钉密钥、API Key）
├── CLAUDE.md                  # 本文件
├── CHANGELOG.md               # 更新日志
│
├── agent/                     # 核心业务模块
│   ├── core.py                # 对话引擎（OpenAI API 调用）
│   ├── knowledge_base.py      # 知识库 V1（基础版）
│   ├── knowledge_base_v2.py   # 知识库 V2（优化版：混合检索、缓存、管理功能）
│   ├── media_handler.py       # 媒体处理（下载、OCR、文件提取）
│   ├── structured_data.py     # 结构化数据（课表、考试、通讯录）
│   ├── web_search.py          # 网络搜索（百度/必应）
│   ├── conversation_state.py  # 会话状态管理（PPT 确认流程）
│   ├── school_config.py       # 多学校配置管理
│   ├── ppt_master_integration.py  # PPT 生成主模块（SVG 流水线）
│   ├── ppt_generator.py       # PPT 基础生成器
│   ├── enhanced_ppt_generator.py  # PPT 增强生成器
│   ├── education_ppt_generator.py # 教育 PPT 生成器
│   ├── education_templates.py # 教育模板库
│   ├── template_based_ppt.py  # 模板 PPT 生成器
│   ├── template_design_ppt.py # 模板设计 PPT 生成器
│   ├── intent_router.py       # LLM 意图路由器（自然语言理解）
│   ├── intent_monitor.py      # 意图识别监控（性能、准确性）
│   └── skills/                # 技能系统
│       ├── registry.py        # 技能注册中心
│       ├── loader.py          # 技能自动加载器
│       ├── example_skill.py   # 示例技能（天气查询）
│       ├── knowledge_skill.py # 知识库技能（查询、统计）
│       └── asset_skill.py     # 资产管理技能（录入、查询、借还、统计）
│
├── dingtalk/                  # 钉钉集成
│   └── bot.py                 # 消息回复（access_token、群聊/单聊）
│
├── docs/                      # 项目文档
│   ├── USAGE.md               # 使用说明
│   ├── SEARCH_USAGE.md        # 搜索功能说明
│   ├── PPT_MASTER_USAGE.md    # PPT Master 说明
│   ├── EDUCATION_PPT_README.md    # 教育 PPT 说明
│   ├── TEMPLATE_PPT_README.md     # 模板 PPT 说明
│   ├── TEMPLATE_PPT_COMPLETE.md   # 模板 PPT 完成总结
│   ├── COMPARISON.md          # PPT 方法对比
│   ├── FINAL_SUMMARY.md       # 最终总结
│   └── FIX_SUMMARY.md         # 修复总结
│
├── tests/                     # 测试脚本
│   ├── test_api.py            # API 测试
│   ├── test_education_ppt.py  # 教育 PPT 测试
│   ├── test_final.py          # 最终测试
│   ├── test_font_size.py      # 字体大小测试
│   ├── test_font_size2.py     # 字体大小测试 2
│   ├── test_fresh_european.py # 清新欧美风测试
│   ├── test_full_generation.py    # 完整生成测试
│   ├── test_keywords.py       # 关键词识别测试
│   ├── test_quick.py          # 快速测试
│   ├── test_template_based.py # 模板 PPT 测试
│   ├── test_template_ppt.py   # 模板设计 PPT 测试
│   └── quick_test.py          # 快速验证
│
├── examples/                  # 使用示例
│   ├── example_education_ppt.py   # 教育 PPT 示例
│   ├── example_template_ppt.py    # 模板 PPT 示例
│   └── example_usage.py       # 通用使用示例
│
├── scripts/                   # 工具脚本
│   ├── create_education_templates.py  # 创建教育模板
│   ├── create_template.py     # 创建示例模板
│   ├── debug_modify.py        # 调试文本修改
│   ├── debug_template_structure.py    # 调试模板结构
│   ├── diagnose_template.py   # 诊断模板问题
│   ├── compare_ppt.py         # 对比 PPT 文件
│   └── check_fresh_european.py    # 检查清新欧美风模板
│
├── templates/                 # PPT 模板文件（.pptx）
├── knowledge/                 # 知识库数据（按学校隔离）
├── projects/                  # PPT 项目输出
├── test_output/               # 测试输出 PPT
└── ppt-master/                # PPT Master 依赖（子模块）
```

## 并行开发模块边界

| 模块 | 关键文件 | 独立性说明 |
|------|----------|-----------|
| **PPT 优化** | `agent/ppt_master_integration.py` | 只修改此文件和 `agent/` 下的 PPT 相关文件 |
| **知识库搭建** | `agent/knowledge_base.py` | 只修改知识库相关文件 |
| **钉钉集成** | `dingtalk/bot.py` + `main.py` | 消息处理逻辑 |
| **网络搜索** | `agent/web_search.py` | 搜索功能独立 |
| **学校配置** | `agent/school_config.py` | 多学校隔离 |
| **新技能开发** | `agent/skills/` 目录 | 独立文件，无需修改 main.py |
| **知识库优化** | `agent/knowledge_base_v2.py` | V2 版本：混合检索、Embedding 缓存、管理功能 |
| **课表管理** | `agent/skills/schedule_skill.py` | 支持调课、查询课表 |
| **资产管理** | `agent/skills/asset_skill.py` | 资产录入、查询、借还、统计 |
| **LLM 意图识别** | `agent/intent_router.py` | 自然语言理解，智能意图识别 |

## LLM 意图路由系统

### 概述

系统采用 LLM（大语言模型）进行自然语言意图识别，替代传统的关键词匹配方式，大幅提升用户体验。

### 架构

```
用户消息
    ↓
┌─────────────────────────────────────────┐
│         LLM 意图路由器                    │
│  - 理解自然语言                          │
│  - 识别意图类型                          │
│  - 提取所有参数                          │
│  - 处理上下文和指代                       │
└─────────────────────────────────────────┘
    ↓
{
  "intent": "inspection",
  "action": "query",
  "params": {"time": "yesterday"}
}
    ↓
┌─────────────────────────────────────────┐
│         技能执行器                        │
│  - 调用对应技能                          │
│  - 传入动态参数                          │
└─────────────────────────────────────────┘
```

### 支持的意图类型

| 意图类型 | 说明 | 示例 |
|---------|------|------|
| inspection | 巡检管理 | "查看昨天的巡检记录"、"帮我打卡教学楼A" |
| ppt | PPT生成 | "帮我做个PPT"、"生成15页的课件" |
| asset | 资产管理 | "录入资产 投影仪 3个"、"查询资产" |
| schedule | 课表管理 | "查询课表"、"调课 周一和周二" |
| search | 搜索查询 | "搜索北京天气"、"查找教学资源" |
| knowledge | 知识库 | "查询知识库"、"知识库统计" |
| chat | 普通对话 | "你好"、"你是谁" |

### 使用方式

```python
from agent.intent_router import intent_router

# 识别意图
intent = await intent_router.classify("查看昨天的巡检记录")

# 结果
# intent.type = "inspection"
# intent.action = "query"
# intent.params = {"time": "yesterday"}
# intent.confidence = 0.95
```

### 监控功能

系统提供完整的监控功能：

```python
from agent.intent_monitor import intent_monitor

# 获取统计信息
stats = intent_monitor.get_stats()

# 获取最近记录
records = intent_monitor.get_recent_records(limit=100)

# 获取错误记录
errors = intent_monitor.get_error_records()

# 导出记录
intent_monitor.export_records("intent_logs.json")
```

### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/intent/classify` | POST | 识别用户意图 |
| `/api/intent/stats` | GET | 获取统计信息 |
| `/api/intent/recent` | GET | 获取最近记录 |
| `/api/intent/errors` | GET | 获取错误记录 |
| `/api/intent/slow` | GET | 获取慢调用记录 |
| `/api/intent/hourly` | GET | 获取每小时统计 |
| `/api/intent/clear-cache` | POST | 清空缓存 |
| `/api/intent/clear-records` | POST | 清空监控记录 |

### 配置项

在 `config.py` 中可以配置：

```python
# LLM 意图识别
LLM_INTENT_ENABLED = os.getenv("LLM_INTENT_ENABLED", "true").lower() == "true"
```

### 缓存机制

- LRU 缓存：最多缓存 1000 条常见意图
- TTL：缓存有效期 5 分钟
- 自动清理：过期自动删除

### 降级策略

当 LLM 调用失败时，系统会自动降级到关键词匹配：

```python
# 降级关键词
- 巡检、打卡、签到 → inspection
- ppt、课件、幻灯片 → ppt
- 资产、设备 → asset
- 课表、调课 → schedule
- 搜索、查询、查找 → search
```

### 测试

运行测试脚本：

```bash
# 测试意图路由器
python tests/test_intent_router.py

# 测试技能集成
python tests/test_skill_integration.py
```

## 技能开发指南

### 创建新技能（无需修改 main.py）

1. 在 `agent/skills/` 目录下创建新文件，例如 `weather_skill.py`
2. 继承 `BaseSkill` 类，实现必要方法
3. 在文件末尾调用 `skill_registry.register()` 注册技能
4. 重启服务即可生效

### 技能模板

```python
"""
技能名称：天气查询
功能：查询指定城市的天气信息
"""
from agent.skills.registry import BaseSkill, skill_registry

class WeatherSkill(BaseSkill):

    @property
    def name(self) -> str:
        return "天气查询"

    @property
    def description(self) -> str:
        return "查询指定城市的天气信息"

    @property
    def keywords(self) -> list:
        return ["天气", "气温", "温度"]

    @property
    def priority(self) -> int:
        return 50  # 数字越小越优先

    def can_handle(self, text: str) -> float:
        """
        判断是否能处理此消息

        返回: 0-1 的置信度
        - 0: 不能处理
        - 0.5: 可能匹配
        - 0.9: 完全匹配
        """
        for keyword in self.keywords:
            if keyword in text:
                return 0.8
        return 0

    def extract_info(self, text: str) -> dict:
        """从消息中提取信息"""
        return {"city": "北京"}  # 示例

    async def execute(self, text: str, context: dict) -> str:
        """
        执行技能

        参数:
            text: 用户消息
            context: 上下文信息
                - sender_nick: 发送者昵称
                - user_id: 用户ID
                - conversation_id: 会话ID
                - corp_id: 企业ID
                - school_config: 学校配置
                - message: 原始消息对象

        返回: 回复文本
        """
        info = self.extract_info(text)
        return f"{info['city']}今天天气晴朗，气温22-28°C"

# 注册技能（必须）
skill_registry.register(WeatherSkill())
```

### 技能优先级

- 内置技能（PPT、搜索等）：优先级 100
- 自定义技能：建议设置 50-90，确保优先于内置技能
- 技能匹配阈值：置信度 >= 0.7 才会触发

## 知识库 V2 优化说明

### 主要改进

1. **混合检索**：结合语义检索（Embedding）和关键词检索，提高召回率
2. **Embedding 缓存**：避免重复计算，提升响应速度
3. **关键词倒排索引**：快速定位候选文档
4. **智能分块**：提取关键词和摘要，优化检索质量
5. **管理功能**：支持统计、导出、删除操作

### 使用方式

```python
from agent.knowledge_base_v2 import get_knowledge_base

# 获取知识库实例
kb = get_knowledge_base(school_dir, corp_id)

# 添加消息
await kb.add_message(text, source_type, source_id, ...)

# 混合检索（默认）
results = await kb.search(query, top_k=5, method="hybrid")

# 语义检索
results = await kb.search(query, method="semantic")

# 关键词检索
results = await kb.search(query, method="keyword")

# 重排序
results = await kb.rerank(query, results, top_k=3)

# 获取统计
stats = kb.get_stats()

# 导出知识库
kb.export_chunks("output.json", format="json")

# 删除指定来源
kb.delete_by_source(source_id)
```

### 钉钉机器人使用

用户可以通过钉钉发送以下指令：

- **查询知识库**：「知识库 查询 课程安排」「有没有 请假流程」
- **查看统计**：「知识库统计」「知识库状态」
- **课表查询**：「计算机2301班周一有什么课？」「查询课表」
- **调课操作**：「计算机2301班周一上午和周二上午调课」「永久调课：张老师周一第1节和周三第1节」
- **资产管理**：「录入资产 投影仪 教学设备 301教室」「查询资产 投影仪」「资产统计」

### 消息过滤规则

以下消息不会存入知识库：
- 简单确认/取消：确认、好的、可以、取消、算了...
- 简单感谢：谢谢、感谢、thank...
- 表情/无意义：哈哈哈、666、👍...
- 太短消息：1-3个字符
- 空白消息

以下消息会保留（包含关键词）：
- PPT 相关：ppt、幻灯片、课件...
- 搜索相关：搜索、查询、查找...
- 学科相关：语文、数学、英语...
- 年级相关：小学、初中、高中...

### 文本清洗

知识库会对文本进行两级清洗：

**基础清洗 (clean_text)**：
- 移除控制字符（保留换行和制表符）
- 移除零宽字符
- 标准化标点（全角→半角）
- 合并多个空格/换行
- 移除行尾空白

**深度清洗 (clean_for_indexing)**：
- 包含基础清洗所有功能
- 移除页眉页脚、页码
- 移除版权声明、免责声明
- 移除纯标点行
- 用于生成 Embedding 和关键词提取

**注意**：归档文件保留原始文本，便于人类查看；索引使用清洗后的文本，提升检索质量。

### 存储容量配置

在 `agent/knowledge_base_v2.py` 中可调整：

```python
MAX_CHUNKS = 100000      # 最大分块数量（默认10万）
MAX_MEMORY_MB = 512      # 最大内存占用（MB）
MAX_FILE_SIZE_MB = 50    # 单文件最大大小（MB）
AUTO_CLEANUP_DAYS = 365  # 自动清理天数（0表示不清理）
```

**扩展存储**：
1. 增加 `MAX_CHUNKS` 值（需相应增加内存）
2. 使用远程 Embedding API 替代本地模型（减少内存占用）
3. 启用自动清理过期数据

### 存储格式

知识库支持两种存储格式：
- **JSON**：结构化存储，便于程序处理
- **Markdown**：人类可读，便于查看和导出

默认使用 Markdown 格式存储。

### 支持的文件格式

| 类型 | 格式 | 提取方式 |
|------|------|----------|
| **图片** | jpg, jpeg, png, gif, webp, bmp, tiff | OCR（多模态 LLM） |
| **PDF** | pdf | PyMuPDF / PyPDF2 |
| **Word** | doc, docx | python-docx |
| **Excel** | xls, xlsx | openpyxl |
| **PPT** | ppt, pptx | python-pptx |
| **文本** | txt | 直接读取 |
| **Markdown** | md, markdown | 解析标记，提取纯文本 |
| **CSV** | csv | 解析表格数据 |
| **JSON** | json | 递归提取字符串值 |
| **HTML** | html, htm | BeautifulSoup / 正则提取 |
| **XML** | xml | ElementTree 解析 |
| **RTF** | rtf | 移除控制字 |
| **配置文件** | ini, cfg, conf, properties | configparser 解析 |
| **代码文件** | py, js, java, c, cpp, go, rs, rb, php, sql, sh 等 | 直接读取 |

## 运行方式

```bash
# 启动钉钉机器人
python main.py

# 或使用启动脚本
start.bat
```

## 关键约束

- 所有 `from agent.xxx import ...` 导入基于项目根目录
- 测试/示例/脚本文件已添加 `sys.path` 修正，可从任意目录运行
- `ppt-master/` 为外部依赖，不要修改其中的文件
- `knowledge/` 目录按 `corp_id` 隔离不同学校的数据
