# 🎓 学校智能助手 - 钉钉机器人

基于钉钉机器人的学校智能助手，集成 AI 对话、PPT 自动生成、知识库管理、资产管理等功能，为学校提供全方位的智能化服务。

## ✨ 核心功能

### 🤖 AI 智能对话
- **知识库增强**：基于 RAG 技术，自动检索相关知识回答问题
- **网络搜索**：支持百度、必应搜索引擎，获取实时信息
- **多轮对话**：支持上下文理解，提供连贯的对话体验
- **意图识别**：LLM 驱动的智能意图路由，准确理解用户需求

### 📊 PPT 自动生成
- **教育课件**：专为教学设计的课件模板
- **模板设计**：多种风格模板（清新欧美风、国风水墨、科技霓虹等）
- **SVG 流水线**：高质量 SVG 生成 + 自动转换 PPTX
- **批量生成**：支持批量创建课件、教案、教学反思

### 📚 知识库管理
- **混合检索**：语义检索 + 关键词检索，提高召回率
- **自动归档**：消息、文件自动存入知识库
- **版本控制**：支持知识更新和历史版本管理
- **多格式支持**：PDF、Word、Excel、PPT、图片等

### 🏫 资产管理
- **资产录入**：快速录入学校设备资产
- **资产查询**：按名称、类别、位置查询
- **借用归还**：完整的借用流程管理
- **统计报表**：资产使用情况统计分析

### 📅 课表管理
- **课表查询**：按班级、教师、时间查询
- **智能调课**：支持临时调课、永久调课
- **冲突检测**：自动检测课表冲突
- **导入导出**：支持 Excel 课表导入

### 🔍 智能巡检
- **巡检打卡**：支持教学楼、实验室等点位打卡
- **记录查询**：查看历史巡检记录
- **统计分析**：巡检完成率统计

## 🛠️ 技术栈

| 技术 | 说明 |
|------|------|
| **Python 3.10+** | 后端语言 |
| **FastAPI** | Web 框架 |
| **钉钉 Stream 模式** | 机器人集成 |
| **OpenAI API** | LLM 接口（兼容多种模型） |
| **Sentence Transformers** | 本地 Embedding 模型 |
| **Vue 3 + Element Plus** | 前端界面 |

## 📁 项目结构

```
dingtalk-custom-agent/
├── main.py                    # 钉钉机器人入口
├── config.py                  # 全局配置
├── agent/                     # 核心业务模块
│   ├── core.py               # 对话引擎
│   ├── knowledge_base_v2.py  # 知识库 V2
│   ├── ppt_master_integration.py  # PPT 生成
│   ├── intent_router.py      # 意图路由
│   └── skills/               # 技能系统
├── dingtalk/                  # 钉钉集成
│   └── bot.py                # 消息回复
├── web/                       # Web 后端
├── web-frontend/              # Web 前端
├── ppt-master/                # PPT 生成引擎
├── templates/                 # PPT 模板
├── knowledge/                 # 知识库数据
├── tests/                     # 测试脚本
└── docs/                      # 项目文档
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/awsl-01/dingtalk-custom-agent.git
cd dingtalk-custom-agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# 钉钉配置
DINGTALK_APP_KEY=your_app_key
DINGTALK_APP_SECRET=your_app_secret
DINGTALK_ROBOT_CODE=your_robot_code

# OpenAI 配置（兼容其他模型）
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://your-api-url/v1
OPENAI_MODEL=your_model_name
```

### 3. 启动服务

```bash
# 启动钉钉机器人
python main.py

# 或使用启动脚本（Windows）
start.bat
```

### 4. Web 管理界面（可选）

```bash
# 启动 Web 后端
python -m web.app

# 启动前端开发服务器
cd web-frontend
npm install
npm run dev
```

## 📖 使用示例

### 钉钉对话

在钉钉群或私聊中 @机器人：

```
用户：帮我做个 PPT，主题是人工智能发展趋势
机器人：正在为您生成 PPT...

用户：查询计算机2301班周一课表
机器人：计算机2301班周一课程安排如下...

用户：录入资产 投影仪 教学设备 301教室
机器人：资产录入成功！编号：AST-2026001

用户：搜索最新教育政策
机器人：为您搜索到以下相关信息...
```

### API 调用

```python
from agent.core import ChatEngine
from agent.intent_router import intent_router

# 识别意图
intent = await intent_router.classify("查看昨天的巡检记录")
print(intent.type)  # inspection
print(intent.action)  # query

# 对话
engine = ChatEngine()
response = await engine.chat("你好", context={"user_id": "123"})
```

## 🔧 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DINGTALK_APP_KEY` | 钉钉应用 Key | - |
| `DINGTALK_APP_SECRET` | 钉钉应用密钥 | - |
| `OPENAI_API_KEY` | LLM API 密钥 | - |
| `OPENAI_BASE_URL` | API 地址 | - |
| `OPENAI_MODEL` | 模型名称 | mimo-v2.5 |
| `KNOWLEDGE_DIR` | 知识库目录 | knowledge |
| `LOCAL_EMBEDDING_MODEL` | 本地 Embedding 模型 | BAAI/bge-small-zh-v1.5 |
| `PORT` | 服务端口 | 8913 |

### 技能开发

系统支持热插拔技能开发，无需修改主程序：

```python
# agent/skills/my_skill.py
from agent.skills.registry import BaseSkill, skill_registry

class MySkill(BaseSkill):
    @property
    def name(self) -> str:
        return "我的技能"

    def can_handle(self, text: str) -> float:
        if "关键词" in text:
            return 0.8
        return 0

    async def execute(self, text: str, context: dict) -> str:
        return "执行结果"

# 注册技能
skill_registry.register(MySkill())
```

## 📚 相关文档

- [使用说明](docs/USAGE.md)
- [搜索功能](docs/SEARCH_USAGE.md)
- [PPT 生成](docs/PPT_MASTER_USAGE.md)
- [教育 PPT](docs/EDUCATION_PPT_README.md)
- [资产管理](docs/ASSET_MANAGEMENT.md)
- [课表管理](docs/SCHEDULING_README.md)
- [知识库概览](docs/RAG_KNOWLEDGE_BASE_OVERVIEW.md)

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [钉钉开放平台](https://open.dingtalk.com/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Sentence Transformers](https://www.sbert.net/)
- [ppt-master](https://github.com/) - PPT 生成引擎

---

📧 联系方式：1636917928@qq.com

⭐ 如果这个项目对你有帮助，请给个 Star 支持一下！
