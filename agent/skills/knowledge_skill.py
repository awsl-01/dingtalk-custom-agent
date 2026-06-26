"""
知识库技能 - 提供知识库查询和管理功能

支持：
- 查询知识库内容
- 查看知识库统计
- 导出知识库
- 删除指定来源的内容
"""
import re
import logging
from typing import Optional
from .registry import BaseSkill, skill_registry

logger = logging.getLogger(__name__)


class KnowledgeQuerySkill(BaseSkill):
    """知识库查询技能"""

    @property
    def name(self) -> str:
        return "知识库查询"

    @property
    def description(self) -> str:
        return "查询学校知识库中的信息"

    @property
    def keywords(self) -> list:
        return ["知识库", "查询", "检索", "搜索知识", "找一下", "有没有"]

    @property
    def priority(self) -> int:
        return 60

    def can_handle(self, text: str) -> float:
        """判断是否是知识库查询请求"""
        text_lower = text.lower()

        # 明确提到知识库
        if "知识库" in text_lower:
            return 0.9

        # 查询类关键词
        query_keywords = ["查询", "检索", "有没有", "找一下", "搜一下", "帮我查"]
        for keyword in query_keywords:
            if keyword in text_lower:
                # 排除 PPT 和搜索请求
                ppt_keywords = ["ppt", "幻灯片", "演示文稿"]
                search_keywords = ["百度", "谷歌", "网络搜索", "网上"]
                if not any(kw in text_lower for kw in ppt_keywords + search_keywords):
                    return 0.8

        return 0

    def extract_info(self, text: str) -> dict:
        """提取查询信息"""
        # 提取查询内容
        query = text
        for keyword in ["知识库", "查询", "检索", "有没有", "找一下", "帮我查", "一下"]:
            query = query.replace(keyword, "")
        query = query.strip()

        return {
            "query": query if query else text,
        }

    async def execute(self, text: str, context: dict) -> str:
        """执行知识库查询"""
        from agent.knowledge_base_v2 import get_knowledge_base

        info = self.extract_info(text)
        query = info["query"]

        if not query:
            return "请告诉我您想查询什么内容。"

        school_config = context.get("school_config")
        if not school_config:
            return "无法获取学校配置，请稍后再试。"

        # 获取用户信息
        user_id = context.get("user_id", "")
        user_nick = context.get("sender_nick", "")
        user_role = context.get("user_role", "teacher")

        try:
            kb = get_knowledge_base(school_config.knowledge_dir, school_config.corp_id)
            search_result = await kb.search(
                query, top_k=5, method="hybrid",
                user_id=user_id, user_nick=user_nick,
                user_role=user_role
            )
            results = search_result.get("results", []) if isinstance(search_result, dict) else search_result
            permission_info = search_result.get("permission_info", {})

            if not results:
                # 检查是否有受限内容
                if permission_info.get("has_restricted"):
                    restricted_count = permission_info.get("restricted_count", 0)
                    return f"⚠️ 找到 {restricted_count} 条相关内容，但您的权限不足无法查看。\n\n" \
                           f"💡 如需查看受限内容，请回复「申请查询 {query}」发起权限申请。"
                return f"在知识库中未找到与「{query}」相关的内容。\n\n💡 提示：您可以发送文件、图片或文字消息给我，我会自动存入知识库。"

            # 构建回复
            reply = f"📚 知识库检索结果（共 {len(results)} 条）：\n\n"

            for i, result in enumerate(results, 1):
                chunk = result.chunk
                score = result.score
                match_type = result.match_type

                # 来源信息
                source_info = ""
                if chunk.sender_nick:
                    source_info = f"（来自：{chunk.sender_nick}）"

                # 摘要或正文
                text_preview = chunk.summary if chunk.summary else chunk.text[:200]

                reply += f"{i}. {text_preview}{source_info}\n"
                reply += f"   [相关度：{score:.2f} | 匹配：{match_type}]\n\n"

            # 添加权限提示
            if permission_info.get("has_restricted"):
                restricted_count = permission_info.get("restricted_count", 0)
                reply += f"\n⚠️ 注意：有 {restricted_count} 条受限内容未显示。"
                reply += f"\n💡 如需查看受限内容，请回复「申请查询 {query}」发起权限申请。"

            # 添加管理提示
            reply += "\n💡 您可以发送新内容给我，我会自动存入知识库。"

            return reply

        except Exception as e:
            logger.error(f"知识库查询失败: {e}", exc_info=True)
            return f"查询知识库时出现错误：{str(e)}"


class KnowledgeStatsSkill(BaseSkill):
    """知识库统计技能"""

    @property
    def name(self) -> str:
        return "知识库统计"

    @property
    def description(self) -> str:
        return "查看知识库的统计信息"

    @property
    def keywords(self) -> list:
        return ["知识库统计", "知识库状态", "有多少内容"]

    @property
    def priority(self) -> int:
        return 65

    def can_handle(self, text: str) -> float:
        """判断是否是统计请求"""
        text_lower = text.lower()

        if "知识库" in text_lower and any(kw in text_lower for kw in ["统计", "状态", "多少", "概况"]):
            return 0.9

        return 0

    def extract_info(self, text: str) -> dict:
        return {}

    async def execute(self, text: str, context: dict) -> str:
        """执行统计查询"""
        from agent.knowledge_base_v2 import get_knowledge_base

        school_config = context.get("school_config")
        if not school_config:
            return "无法获取学校配置，请稍后再试。"

        try:
            kb = get_knowledge_base(school_config.knowledge_dir, school_config.corp_id)
            stats = kb.get_stats()

            reply = f"""📊 知识库统计信息

📁 分块总数：{stats.total_chunks} 个
💬 消息总数：{stats.total_messages} 条
💾 索引大小：{stats.index_size_mb:.2f} MB

📋 来源类型：
"""
            for source_type, count in stats.source_types.items():
                type_name = {"text": "文本", "image": "图片", "file": "文件"}.get(source_type, source_type)
                reply += f"  • {type_name}：{count} 个\n"

            if stats.top_senders:
                reply += "\n👤 活跃贡献者：\n"
                for sender, count in stats.top_senders[:5]:
                    reply += f"  • {sender}：{count} 条\n"

            if stats.date_range:
                reply += f"\n📅 时间范围：\n"
                reply += f"  • 最早：{stats.date_range.get('earliest', '无')}\n"
                reply += f"  • 最新：{stats.date_range.get('latest', '无')}\n"

            return reply

        except Exception as e:
            logger.error(f"获取知识库统计失败: {e}", exc_info=True)
            return f"获取统计信息时出现错误：{str(e)}"


# 注册技能
skill_registry.register(KnowledgeQuerySkill())
skill_registry.register(KnowledgeStatsSkill())
