import os
from dotenv import load_dotenv

load_dotenv()

DINGTALK_APP_KEY = os.getenv("DINGTALK_APP_KEY", "")
DINGTALK_APP_SECRET = os.getenv("DINGTALK_APP_SECRET", "")
DINGTALK_ROBOT_CODE = os.getenv("DINGTALK_ROBOT_CODE", "")

# LLM 优化配置
# 是否启用 LLM 智能分类（关闭后使用纯关键词匹配）
LLM_CLASSIFICATION_ENABLED = os.getenv("LLM_CLASSIFICATION_ENABLED", "false").lower() == "true"
# 是否启用 LLM 智能过滤（关闭后使用纯规则过滤）
LLM_FILTERING_ENABLED = os.getenv("LLM_FILTERING_ENABLED", "false").lower() == "true"
# 是否启用 LLM 意图理解（关闭后不进行意图识别）
LLM_INTENT_ENABLED = os.getenv("LLM_INTENT_ENABLED", "false").lower() == "true"
# LLM 调用超时时间（秒）
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "10"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "mimo-v2.5-pro")

PORT = int(os.getenv("PORT", "8913"))

# 知识库配置
KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", "knowledge")

# Embedding配置
# 本地模型（优先使用，无需API）
LOCAL_EMBEDDING_MODEL = os.getenv("LOCAL_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
# HuggingFace镜像（国内网络需要）
HF_ENDPOINT = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
# 远程API（备用）
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# Rerank配置
# 启用Rerank（默认关闭，需要额外依赖）
RERANK_ENABLED = os.getenv("RERANK_ENABLED", "false").lower() == "true"
# Rerank策略：local（本地cross-encoder）、llm（使用LLM）、api（第三方API）
RERANK_STRATEGY = os.getenv("RERANK_STRATEGY", "llm")
# 本地Cross-encoder模型
LOCAL_RERANK_MODEL = os.getenv("LOCAL_RERANK_MODEL", "BAAI/bge-reranker-base")
# Rerank API配置
RERANK_API_KEY = os.getenv("RERANK_API_KEY", "")
RERANK_BASE_URL = os.getenv("RERANK_BASE_URL", "")
RERANK_MODEL = os.getenv("RERANK_MODEL", "")
# Rerank返回数量
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "3"))

# 主动智能配置
# 启用主动通知
PROACTIVE_NOTIFICATIONS_ENABLED = os.getenv("PROACTIVE_NOTIFICATIONS_ENABLED", "true").lower() == "true"
# 启用周期性提醒
PROACTIVE_REMINDER_ENABLED = os.getenv("PROACTIVE_REMINDER_ENABLED", "true").lower() == "true"
# 提醒检查时间（cron表达式）
PROACTIVE_REMINDER_CRON = os.getenv("PROACTIVE_REMINDER_CRON", "0 7 * * *")

# 检索增强配置
# 启用搜索解释
SEARCH_EXPLANATION_ENABLED = os.getenv("SEARCH_EXPLANATION_ENABLED", "true").lower() == "true"
# 启用搜索建议
SEARCH_SUGGESTION_ENABLED = os.getenv("SEARCH_SUGGESTION_ENABLED", "true").lower() == "true"

# PPT 质量配置
# 严格模式：启用增强版 SVG 质量校验（对齐原生 IDE 环境）
# 关闭后使用宽松模式，生成速度更快但质量可能下降
PPT_STRICT_MODE = os.getenv("PPT_STRICT_MODE", "true").lower() == "true"
# SVG 生成最大重试次数
PPT_SVG_MAX_RETRIES = int(os.getenv("PPT_SVG_MAX_RETRIES", "3"))
# 后处理流水线：是否强制执行 finalize_svg
PPT_FORCE_FINALIZE = os.getenv("PPT_FORCE_FINALIZE", "true").lower() == "true"

# Web 应用配置
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8913"))
WEB_SECRET_KEY = os.getenv("WEB_SECRET_KEY", "dingtalk-bot-secret-key-2024")
DINGTALK_REDIRECT_URI = os.getenv("DINGTALK_REDIRECT_URI", "http://localhost:8913/api/auth/callback")
