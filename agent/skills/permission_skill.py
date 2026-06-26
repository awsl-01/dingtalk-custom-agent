"""
权限管理技能
支持权限查询、访问申请、审批处理
"""
import logging
from typing import Optional
from .registry import BaseSkill, skill_registry

logger = logging.getLogger(__name__)


class PermissionQuerySkill(BaseSkill):
    """权限查询技能 - 显示当前用户的权限信息"""

    @property
    def name(self) -> str:
        return "权限查询"

    @property
    def description(self) -> str:
        return "查看当前用户的权限和角色信息"

    @property
    def keywords(self) -> list:
        return ["权限", "我的权限", "我能查什么", "角色", "我是谁"]

    @property
    def priority(self) -> int:
        return 40

    def can_handle(self, text: str) -> float:
        """判断是否是权限查询请求"""
        text_lower = text.lower()

        # 精确匹配
        exact_matches = ["我的权限", "我能查什么", "查看权限", "权限查询"]
        if text_lower in exact_matches:
            return 0.9

        # 关键词匹配
        if "权限" in text_lower and any(w in text_lower for w in ["查看", "查询", "我的", "什么"]):
            return 0.8

        if text_lower in ["我是谁", "我的角色"]:
            return 0.7

        return 0

    def extract_info(self, text: str) -> dict:
        return {}

    async def execute(self, text: str, context: dict) -> str:
        """执行权限查询"""
        from agent.permission_manager import get_permission_manager

        school_config = context.get("school_config")
        if not school_config:
            return "无法获取学校配置，请稍后再试。"

        user_id = context.get("user_id", "")
        user_nick = context.get("sender_nick", "")
        corp_id = context.get("corp_id", "")

        perm_manager = get_permission_manager(school_config.knowledge_dir, corp_id)

        # 获取用户信息
        user = perm_manager.get_user(user_id)
        if not user:
            # 自动注册新用户
            from agent.permission_manager import UserInfo
            user = UserInfo(
                user_id=user_id,
                name=user_nick,
                role="teacher",
                department="",
                manager_id=""
            )
            perm_manager.add_user(user)

        # 获取权限信息
        role_name = perm_manager.get_role_name(user.role)
        allowed_levels = perm_manager.get_allowed_access_levels(user_id)

        # 构建回复
        reply = f"👤 用户信息\n\n"
        reply += f"姓名：{user.name}\n"
        reply += f"角色：{role_name}\n"
        if user.department:
            reply += f"部门：{user.department}\n"

        # 上级信息
        manager = perm_manager.get_manager(user_id)
        if manager:
            reply += f"上级：{manager.name}\n"

        reply += f"\n🔑 权限信息\n\n"

        # 访问级别
        level_names = {
            "public": "公开",
            "internal": "内部",
            "confidential": "机密"
        }
        reply += "可访问内容：\n"
        for level in allowed_levels:
            reply += f"  ✅ {level_names.get(level, level)}\n"

        # 不可访问的级别
        all_levels = ["public", "internal", "confidential"]
        restricted = [l for l in all_levels if l not in allowed_levels]
        if restricted:
            reply += "\n需要审批的内容：\n"
            for level in restricted:
                reply += f"  🔒 {level_names.get(level, level)}\n"

        return reply


class AccessRequestSkill(BaseSkill):
    """访问申请技能 - 申请访问受限内容"""

    @property
    def name(self) -> str:
        return "访问申请"

    @property
    def description(self) -> str:
        return "申请访问需要审批的内容"

    @property
    def keywords(self) -> list:
        return ["申请", "申请查询", "申请访问", "申请权限"]

    @property
    def priority(self) -> int:
        return 45

    def can_handle(self, text: str) -> float:
        """判断是否是访问申请请求"""
        text_lower = text.lower()

        # 明确的申请请求
        if "申请" in text_lower and any(w in text_lower for w in ["查询", "访问", "查看"]):
            return 0.9

        # 包含"申请"和"权限"
        if "申请" in text_lower and "权限" in text_lower:
            return 0.85

        # 包含"向上级申请"、"向...申请"等
        if "申请" in text_lower and any(w in text_lower for w in ["向上级", "向", "上级"]):
            return 0.9

        if text_lower in ["申请", "我要申请"]:
            return 0.6

        return 0

    def extract_info(self, text: str) -> dict:
        return {"query": text}

    async def execute(self, text: str, context: dict) -> str:
        """执行访问申请"""
        from agent.permission_manager import get_permission_manager, AccessLevel

        school_config = context.get("school_config")
        if not school_config:
            return "无法获取学校配置，请稍后再试。"

        user_id = context.get("user_id", "")
        user_nick = context.get("sender_nick", "")
        corp_id = context.get("corp_id", "")

        perm_manager = get_permission_manager(school_config.knowledge_dir, corp_id)

        # 检查用户是否有上级
        manager = perm_manager.get_manager(user_id)
        if not manager:
            return "❌ 无法发起申请：您没有设置上级。\n\n请联系管理员设置您的上级关系。"

        # 检查是否有待审批的请求
        existing_request = perm_manager.get_user_pending_request(user_id, "confidential")
        if existing_request:
            return f"⏳ 您已有一个待审批的申请\n\n申请内容：{existing_request.query}\n请等待上级审批。"

        # 创建审批请求
        request = perm_manager.create_approval_request(
            user_id=user_id,
            query=text,
            access_level="confidential"  # 默认申请机密级别
        )

        if not request:
            return "❌ 创建申请失败，请稍后再试。"

        # 发送通知给上级
        try:
            from dingtalk.bot import reply_text as send_message

            notification = f"📋 访问审批请求\n\n"
            notification += f"申请人：{user_nick}\n"
            notification += f"申请内容：查询机密级别知识库\n"
            notification += f"查询关键词：{text}\n\n"
            notification += f"请回复「同意 {request.request_id}」或「拒绝 {request.request_id}」"

            # 发送单聊消息给上级
            logger.info(f"准备发送审批通知给上级: {manager.name} ({manager.user_id})")
            result = await send_message(
                conversation_id="",  # 单聊不需要 conversation_id
                sender_id=manager.user_id,
                text=notification
            )
            logger.info(f"审批通知发送结果: {result}")

        except Exception as e:
            logger.error(f"发送审批通知失败: {e}")

        reply = f"✅ 申请已提交\n\n"
        reply += f"申请编号：{request.request_id}\n"
        reply += f"审批人：{manager.name}\n"
        reply += f"申请内容：{text}\n\n"
        reply += f"📌 审批方式：\n"
        reply += f"请让审批人（{manager.name}）私聊机器人，发送以下命令：\n"
        reply += f"• 「审批」- 查看待审批列表\n"
        reply += f"• 「同意 {request.request_id}」- 批准申请\n"
        reply += f"• 「拒绝 {request.request_id}」- 拒绝申请"

        return reply


class ApprovalSkill(BaseSkill):
    """审批技能 - 处理审批请求"""

    @property
    def name(self) -> str:
        return "审批处理"

    @property
    def description(self) -> str:
        return "处理访问审批请求"

    @property
    def keywords(self) -> list:
        return ["同意", "拒绝", "批准", "驳回", "审批"]

    @property
    def priority(self) -> int:
        return 42

    def can_handle(self, text: str) -> float:
        """判断是否是审批请求"""
        text_lower = text.lower()

        # 包含审批关键词
        approval_keywords = ["同意", "拒绝", "批准", "驳回"]
        for keyword in approval_keywords:
            if keyword in text_lower:
                # 检查是否包含申请ID格式
                if "approval_" in text_lower:
                    return 0.9
                # 可能是回复审批
                if len(text_lower) < 20:
                    return 0.6

        return 0

    def extract_info(self, text: str) -> dict:
        """提取审批信息"""
        import re

        info = {
            "action": "unknown",
            "request_id": "",
            "reason": ""
        }

        # 提取申请ID
        id_match = re.search(r'approval_\d+', text)
        if id_match:
            info["request_id"] = id_match.group()

        # 判断动作
        text_lower = text.lower()
        if any(w in text_lower for w in ["同意", "批准"]):
            info["action"] = "approve"
        elif any(w in text_lower for w in ["拒绝", "驳回"]):
            info["action"] = "reject"
            # 提取拒绝原因
            for keyword in ["拒绝", "驳回", "因为", "原因"]:
                text = text.replace(keyword, "")
            info["reason"] = text.strip()

        return info

    async def execute(self, text: str, context: dict) -> str:
        """执行审批处理"""
        from agent.permission_manager import get_permission_manager

        school_config = context.get("school_config")
        if not school_config:
            return "无法获取学校配置，请稍后再试。"

        user_id = context.get("user_id", "")
        user_nick = context.get("sender_nick", "")
        corp_id = context.get("corp_id", "")

        perm_manager = get_permission_manager(school_config.knowledge_dir, corp_id)

        info = self.extract_info(text)
        request_id = info.get("request_id", "")

        # 如果没有指定申请ID，显示待审批列表
        if not request_id:
            pending_approvals = perm_manager.get_pending_approvals(user_id)

            if not pending_approvals:
                return "📋 当前没有待审批的申请。"

            reply = f"📋 待审批列表（共 {len(pending_approvals)} 条）\n\n"
            for i, req in enumerate(pending_approvals, 1):
                reply += f"{i}. 申请人：{req.user_name}\n"
                reply += f"   查询内容：{req.query}\n"
                reply += f"   申请编号：{req.request_id}\n\n"

            reply += "请回复「同意 申请编号」或「拒绝 申请编号」进行审批。"
            return reply

        # 处理指定的审批请求
        request = perm_manager.get_approval_by_id(request_id)
        if not request:
            return f"❌ 未找到申请 {request_id}"

        # 检查是否是审批人
        if request.manager_id != user_id:
            return "❌ 您不是该申请的审批人。"

        # 检查申请状态
        if request.status != "pending":
            return f"⏳ 该申请已处理，状态：{request.status}"

        # 处理审批
        if info["action"] == "approve":
            perm_manager.approve_request(request_id, user_id)

            reply = f"✅ 审批通过\n\n"
            reply += f"申请人：{request.user_name}\n"
            reply += f"查询内容：{request.query}\n\n"
            reply += f"已通知申请人查询结果。"

            # 通知申请人审批通过，并执行查询
            try:
                from dingtalk.bot import reply_text as send_message
                from agent.knowledge_base_v2 import get_knowledge_base
                from agent.core import chat_with_knowledge

                # 发送通知给申请人
                notification = f"✅ 您的访问申请已通过\n\n"
                notification += f"审批人：{user_nick}\n"
                notification += f"申请内容：{request.query}\n\n"
                notification += f"正在为您查询，请稍候..."

                logger.info(f"准备发送审批通过通知给申请人: {request.user_name} ({request.user_id})")
                result = await send_message(
                    conversation_id="",
                    sender_id=request.user_id,
                    text=notification
                )
                logger.info(f"审批通过通知发送结果: {result}")

                # 执行知识库查询
                kb = get_knowledge_base(school_config.knowledge_dir, corp_id)

                # 提取查询关键词（移除"帮我向XX申请查看权限"等前缀）
                query_text = request.query
                # 清理查询文本
                clean_keywords = ["帮我向", "申请查看权限", "申请查询", "申请访问", "向", "申请"]
                for keyword in clean_keywords:
                    query_text = query_text.replace(keyword, "")
                query_text = query_text.strip()

                if query_text:
                    # 执行搜索
                    logger.info(f"执行知识库查询: query_text='{query_text}'")
                    search_response = await kb.search(query_text, top_k=3, method="hybrid")
                    search_results = search_response.get("results", [])
                    logger.info(f"搜索结果数量: {len(search_results)}")

                    if search_results:
                        # 构建知识库上下文
                        knowledge_context = ""
                        for i, result in enumerate(search_results, 1):
                            knowledge_context += f"[{i}] {result.chunk.text}\n\n"

                        # 调用 AI 生成回复
                        ai_reply = await chat_with_knowledge(
                            query_text,
                            knowledge_context=knowledge_context,
                            need_web_search=False
                        )

                        logger.info(f"准备发送查询结果给申请人: {request.user_name}")
                        result = await send_message(
                            conversation_id="",
                            sender_id=request.user_id,
                            text=ai_reply
                        )
                        logger.info(f"查询结果发送结果: {result}")
                    else:
                        no_result_msg = f"📋 查询结果\n\n"
                        no_result_msg += f"查询内容：{query_text}\n"
                        no_result_msg += f"未找到相关内容。"

                        logger.info(f"准备发送无结果通知给申请人: {request.user_name}")
                        result = await send_message(
                            conversation_id="",
                            sender_id=request.user_id,
                            text=no_result_msg
                        )
                        logger.info(f"无结果通知发送结果: {result}")

                logger.info(f"已通知申请人 {request.user_name} 审批通过并执行查询")

            except Exception as e:
                logger.error(f"通知申请人失败: {e}")

            return reply

        elif info["action"] == "reject":
            reason = info.get("reason", "未说明原因")
            perm_manager.reject_request(request_id, user_id, reason)

            reply = f"❌ 已拒绝\n\n"
            reply += f"申请人：{request.user_name}\n"
            reply += f"查询内容：{request.query}\n"
            reply += f"拒绝原因：{reason}\n\n"
            reply += f"已通知申请人审批结果。"

            # 通知申请人审批被拒绝
            try:
                from dingtalk.bot import reply_text as send_message

                notification = f"❌ 您的访问申请已被拒绝\n\n"
                notification += f"审批人：{user_nick}\n"
                notification += f"申请内容：{request.query}\n"
                notification += f"拒绝原因：{reason}"

                logger.info(f"准备发送审批拒绝通知给申请人: {request.user_name} ({request.user_id})")
                result = await send_message(
                    conversation_id="",
                    sender_id=request.user_id,
                    text=notification
                )
                logger.info(f"审批拒绝通知发送结果: {result}")
                logger.info(f"已通知申请人 {request.user_name} 审批被拒绝")

            except Exception as e:
                logger.error(f"通知申请人失败: {e}")

            return reply

        else:
            return "❓ 无法识别操作，请回复「同意 申请编号」或「拒绝 申请编号」。"


class UserManageSkill(BaseSkill):
    """用户管理技能 - 管理员专用"""

    @property
    def name(self) -> str:
        return "用户管理"

    @property
    def description(self) -> str:
        return "管理用户信息（管理员专用）"

    @property
    def keywords(self) -> list:
        return ["用户管理", "添加用户", "设置角色", "设置上级"]

    @property
    def priority(self) -> int:
        return 38

    def can_handle(self, text: str) -> float:
        """判断是否是用户管理请求"""
        text_lower = text.lower()

        manage_keywords = ["用户管理", "添加用户", "设置角色", "设置上级", "用户列表"]
        for keyword in manage_keywords:
            if keyword in text_lower:
                return 0.9

        return 0

    def extract_info(self, text: str) -> dict:
        return {"action": text}

    async def execute(self, text: str, context: dict) -> str:
        """执行用户管理"""
        from agent.permission_manager import get_permission_manager, UserInfo

        school_config = context.get("school_config")
        if not school_config:
            return "无法获取学校配置，请稍后再试。"

        user_id = context.get("user_id", "")
        user_nick = context.get("sender_nick", "")
        corp_id = context.get("corp_id", "")

        perm_manager = get_permission_manager(school_config.knowledge_dir, corp_id)

        # 检查权限（只有管理员可以管理用户）
        user_role = perm_manager.get_user_role(user_id)
        if user_role not in ["admin", "principal"]:
            return "❌ 权限不足：只有管理员可以管理用户。"

        text_lower = text.lower()

        # 用户列表
        if "用户列表" in text_lower or "查看用户" in text_lower:
            users = perm_manager.list_users()
            if not users:
                return "📋 当前没有用户信息。"

            reply = f"👥 用户列表（共 {len(users)} 人）\n\n"
            for user in users:
                role_name = perm_manager.get_role_name(user.role)
                reply += f"• {user.name}\n"
                reply += f"  角色：{role_name}\n"
                if user.department:
                    reply += f"  部门：{user.department}\n"
                if user.manager_id:
                    manager_name = perm_manager.get_user_name(user.manager_id)
                    reply += f"  上级：{manager_name}\n"
                reply += "\n"

            return reply

        # 其他管理功能需要更复杂的解析，暂时返回帮助信息
        return f"📋 用户管理功能\n\n" \
               f"支持的命令：\n" \
               f"• 用户列表 - 查看所有用户\n" \
               f"• 设置角色 [用户名] [角色] - 设置用户角色\n" \
               f"• 设置上级 [用户名] [上级用户名] - 设置用户上级\n\n" \
               f"角色类型：admin（管理员）、principal（校长）、director（主任）、teacher（教师）、student（学生）"


# 注册技能
skill_registry.register(PermissionQuerySkill())
skill_registry.register(AccessRequestSkill())
skill_registry.register(ApprovalSkill())
skill_registry.register(UserManageSkill())
