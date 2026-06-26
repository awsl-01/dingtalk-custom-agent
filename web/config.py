"""
Web 管理后台配置
"""
import os

# 服务配置
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8913"))

# 数据库配置
WEB_DB_PATH = os.getenv("WEB_DB_PATH", "web/data/messages.db")

# 知识库路径（从主项目配置继承）
KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", "knowledge")

# JWT 密钥
WEB_SECRET_KEY = os.getenv("WEB_SECRET_KEY", "dingtalk-bot-secret-key-2024")
