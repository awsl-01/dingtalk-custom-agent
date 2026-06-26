"""
权限管理技能
支持通过钉钉命令设置文件权限和用户权限等级
"""
import re
import logging
from typing import Optional
from .registry import BaseSkill, skill_registry

logger = logging.getLogger(__name__)


class SetFilePermissionSkill(BaseSkill):
    """设置文件权限技能"""

    @property
    def name(self) -> str:
        return "设置文件权限"

    @property
    def description(self) -> str:
        return "设置知识库内容的访问权限级别"

    @property
    def keywords(self) -> list:
        return ["设置权限", "文件权限", "权限设置", "设为机密", "设为内部", "设为公开",
                "只有管理员", "只有校长", "需要申请", "无法查询"]

    @property
    def priority(self) -> int:
        return 35

    def can_handle(self, text: str) -> float:
        """判断是否是设置文件权限请求"""
        text_lower = text.lower()

        # 明确的权限设置命令
        if any(kw in text_lower for kw in ["设置权限", "文件权限", "权限设置"]):
            return 0.9

        # 包含权限级别和设置意图的表达
        level_keywords = ["机密", "内部", "公开", "confidential", "internal", "public"]
        set_keywords = ["设置", "设为", "设成", "改成", "改为", "设成", "标记为"]

        has_level = any(kw in text_lower for kw in level_keywords)
        has_set = any(kw in text_lower for kw in set_keywords)

        if has_level and has_set:
            return 0.9

        # 包含"只有XX能看"、"需要申请"等表达
        access_patterns = ["只有.*能看", "只有.*能查", "需要申请", "无法查询", "不能查",
                          "禁止查询", "限制访问", "保密", "私密"]
        for pattern in access_patterns:
            if re.search(pattern, text):
                return 0.85

        # 包含"设置"和权限相关词
        if "设置" in text_lower and any(w in text_lower for w in ["权限", "访问", "查看"]):
            return 0.8

        return 0

    def extract_info(self, text: str) -> dict:
        """提取设置信息"""
        info = {
            "action": "unknown",
            "target": "",
            "level": ""
        }

        # 提取权限级别
        if any(w in text for w in ["机密", "confidential", "保密", "私密", "只有管理员", "只有校长"]):
            info["level"] = "confidential"
        elif any(w in text for w in ["内部", "internal", "只有教师", "只有老师"]):
            info["level"] = "internal"
        elif any(w in text for w in ["公开", "public", "所有人"]):
            info["level"] = "public"

        # 特殊处理"需要申请"、"无法查询"等表达
        if any(w in text for w in ["需要申请", "无法查询", "不能查", "禁止查询"]):
            if not info["level"]:
                info["level"] = "confidential"  # 默认设为机密

        # 提取目标（内容关键词）
        # 优先使用正则表达式提取有意义的词组
        # 注意：需要排除"设置"、"把"、"将"等动词
        target_patterns = [
            r'(?:设置|设|把|将)?\s*([一-龥]+?)(?:信息|资料|数据|方案|计划|文件|档案|记录)',  # XX信息、XX资料等
            r'(?:把|将)\s*([一-龥]+?)\s*(?:设为|设成|改成|改为)',  # 把XX设为
            r'(?:设置|设)\s*([一-龥]+?)\s*(?:为|成)',  # 设置XX为
            r'([一-龥]{2,8})\s*(?:设为|设成|改成|改为|标记为|设置为)',  # XX设为
            r'([一-龥]+?)(?:需要申请|只有|无法查询|不能查)',  # XX需要申请
        ]

        for pattern in target_patterns:
            match = re.search(pattern, text)
            if match:
                potential_target = match.group(1).strip()
                # 如果匹配到的是"XX信息"的模式，需要加上后缀
                suffixes = ['信息', '资料', '数据', '方案', '计划', '文件', '档案', '记录']
                for suffix in suffixes:
                    if suffix in pattern and suffix not in potential_target:
                        # 检查原文中是否有后缀
                        if suffix in text:
                            potential_target = potential_target + suffix
                            break
                # 过滤掉太短或无意义的词
                if len(potential_target) >= 2 and potential_target not in ["信息", "资料", "数据", "才看", "设置", "把", "将"]:
                    info["target"] = potential_target
                    break

        # 如果正则没有匹配到，使用移除关键词的方式
        if not info["target"]:
            clean_text = text
            remove_keywords = [
                "设置权限", "文件权限", "权限设置", "设置", "权限",
                "为", "设为", "设成", "改成", "改为", "标记为", "设置为",
                "只有", "能看", "能查", "需要申请", "无法查询", "不能查",
                "禁止查询", "限制访问", "保密", "私密",
                "除了我", "其余人", "其他人", "别人", "除了", "以外",
                "要查询", "需要向我申请", "向我申请", "才能查看", "才能查",
                "把", "将"
            ]
            for keyword in remove_keywords:
                clean_text = clean_text.replace(keyword, "")

            # 移除权限级别词
            level_words = ["机密", "内部", "公开", "confidential", "internal", "public",
                          "管理员", "校长", "主任", "教师", "老师", "学生"]
            for level_word in level_words:
                clean_text = clean_text.replace(level_word, "")

            # 清理标点和空白
            clean_text = re.sub(r'[，。、；：""''！？,.;:!?]', '', clean_text)
            clean_text = clean_text.strip()

            if clean_text and len(clean_text) >= 2:
                info["target"] = clean_text

        return info

    async def execute(self, text: str, context: dict) -> str:
        """执行设置文件权限"""
        from agent.permission_manager import get_permission_manager
        from agent.knowledge_base_v2 import get_knowledge_base

        school_config = context.get("school_config")
        if not school_config:
            return "无法获取学校配置，请稍后再试。"

        user_id = context.get("user_id", "")
        corp_id = context.get("corp_id", "")

        # 检查权限（只有管理员可以设置文件权限）
        perm_manager = get_permission_manager(school_config.knowledge_dir, corp_id)
        user_role = perm_manager.get_user_role(user_id)

        if user_role not in ["admin", "principal"]:
            return "❌ 权限不足：只有管理员可以设置文件权限。"

        info = self.extract_info(text)

        if not info["target"]:
            return "📝 设置文件权限命令格式：\n\n" \
                   "设置权限 [文件名/关键词] 为 [权限级别]\n\n" \
                   "权限级别：\n" \
                   "• 公开 (public) - 所有人可访问\n" \
                   "• 内部 (internal) - 教师及以上可访问\n" \
                   "• 机密 (confidential) - 仅管理员/校长可访问\n\n" \
                   "示例：\n" \
                   "• 设置权限 薪资方案 为 机密\n" \
                   "• 设置权限 课表 为 内部\n" \
                   "• 设置权限 通知 为 公开"

        if not info["level"]:
            return "❌ 请指定权限级别：公开、内部、机密"

        # 更新知识库中的文件权限
        kb = get_knowledge_base(school_config.knowledge_dir, corp_id)

        # 查找匹配的知识块
        target = info["target"]
        level = info["level"]
        updated_count = 0

        # 提取关键词用于匹配
        # 例如 "老师信息" -> ["老师", "教授", "教师", "讲师"]
        keywords = [target]
        if "老师" in target or "教师" in target:
            keywords.extend(["老师", "教授", "教师", "讲师", "副教授"])
        elif "学生" in target:
            keywords.extend(["学生", "同学"])
        elif "课表" in target or "课程" in target:
            keywords.extend(["课表", "课程", "上课", "节次"])
        elif "成绩" in target:
            keywords.extend(["成绩", "分数", "考试"])
        elif "薪资" in target or "工资" in target:
            keywords.extend(["薪资", "工资", "待遇", "薪酬"])

        for chunk in kb._chunks:
            # 匹配文件名或内容
            should_update = False

            # 检查是否包含目标关键词
            for keyword in keywords:
                if (keyword in (chunk.file_name or "") or
                    keyword in chunk.text or
                    keyword in (chunk.summary or "")):
                    should_update = True
                    break

            if should_update:
                chunk.access_level = level
                updated_count += 1

        if updated_count == 0:
            return f"❌ 未找到包含「{target}」的知识内容。"

        # 保存更新
        kb._save_index()

        level_names = {
            "public": "公开",
            "internal": "内部",
            "confidential": "机密"
        }

        return f"✅ 权限设置成功\n\n" \
               f"目标：{target}\n" \
               f"权限级别：{level_names.get(level, level)}\n" \
               f"更新分块数：{updated_count}"


class SetUserRoleSkill(BaseSkill):
    """设置用户角色技能"""

    @property
    def name(self) -> str:
        return "设置用户角色"

    @property
    def description(self) -> str:
        return "设置用户的权限角色"

    @property
    def keywords(self) -> list:
        return ["设置角色", "用户角色", "角色设置"]

    @property
    def priority(self) -> int:
        return 36

    def can_handle(self, text: str) -> float:
        """判断是否是设置用户角色请求"""
        text_lower = text.lower()

        if "设置角色" in text_lower or "用户角色" in text_lower:
            return 0.9

        if "角色" in text_lower and any(w in text_lower for w in ["设置", "修改", "更改"]):
            return 0.8

        return 0

    def extract_info(self, text: str) -> dict:
        """提取设置信息"""
        info = {
            "user_name": "",
            "role": "",
            "department": "",
            "manager": ""
        }

        # 提取角色
        role_map = {
            "管理员": "admin",
            "校长": "principal",
            "主任": "director",
            "教师": "teacher",
            "学生": "student"
        }
        for cn_name, en_name in role_map.items():
            if cn_name in text:
                info["role"] = en_name
                break

        # 提取用户名（在"设置角色"和角色名之间）
        clean_text = text
        for keyword in ["设置角色", "用户角色", "角色设置", "设置"]:
            clean_text = clean_text.replace(keyword, "")

        # 移除角色词
        for cn_name in role_map.keys():
            clean_text = clean_text.replace(cn_name, "")

        # 提取部门
        dept_match = re.search(r'部门[：:]\s*(\S+)', text)
        if dept_match:
            info["department"] = dept_match.group(1)

        # 提取上级
        manager_match = re.search(r'上级[：:]\s*(\S+)', text)
        if manager_match:
            info["manager"] = manager_match.group(1)

        # 用户名是剩余的文本
        info["user_name"] = clean_text.strip()

        return info

    async def execute(self, text: str, context: dict) -> str:
        """执行设置用户角色"""
        from agent.permission_manager import get_permission_manager

        school_config = context.get("school_config")
        if not school_config:
            return "无法获取学校配置，请稍后再试。"

        user_id = context.get("user_id", "")
        corp_id = context.get("corp_id", "")

        # 检查权限（只有管理员可以设置用户角色）
        perm_manager = get_permission_manager(school_config.knowledge_dir, corp_id)
        user_role = perm_manager.get_user_role(user_id)

        if user_role not in ["admin", "principal"]:
            return "❌ 权限不足：只有管理员可以设置用户角色。"

        info = self.extract_info(text)

        if not info["user_name"]:
            return "📝 设置用户角色命令格式：\n\n" \
                   "设置角色 [用户名] [角色]\n\n" \
                   "角色类型：\n" \
                   "• 管理员 (admin) - 最高权限\n" \
                   "• 校长 (principal) - 最高权限\n" \
                   "• 主任 (director) - 可访问机密内容\n" \
                   "• 教师 (teacher) - 可访问内部内容\n" \
                   "• 学生 (student) - 仅可访问公开内容\n\n" \
                   "示例：\n" \
                   "• 设置角色 张三 教师\n" \
                   "• 设置角色 李四 主任 部门:教务处 上级:张三"

        if not info["role"]:
            return "❌ 请指定角色：管理员、校长、主任、教师、学生"

        # 查找用户
        target_user = None
        for user in perm_manager.list_users():
            if info["user_name"] in user.name or info["user_name"] == user.user_id:
                target_user = user
                break

        if not target_user:
            return f"❌ 未找到用户「{info['user_name']}」。\n\n" \
                   f"💡 请先使用「添加用户」命令添加用户。"

        # 更新用户信息
        updates = {"role": info["role"]}
        if info["department"]:
            updates["department"] = info["department"]
        if info["manager"]:
            # 查找上级用户
            manager_user = None
            for user in perm_manager.list_users():
                if info["manager"] in user.name or info["manager"] == user.user_id:
                    manager_user = user
                    break
            if manager_user:
                updates["manager_id"] = manager_user.user_id

        perm_manager.update_user(target_user.user_id, **updates)

        role_names = {
            "admin": "管理员",
            "principal": "校长",
            "director": "主任",
            "teacher": "教师",
            "student": "学生"
        }

        reply = f"✅ 用户角色设置成功\n\n"
        reply += f"用户：{target_user.name}\n"
        reply += f"角色：{role_names.get(info['role'], info['role'])}\n"
        if info["department"]:
            reply += f"部门：{info['department']}\n"
        if "manager_id" in updates:
            manager_name = perm_manager.get_user_name(updates["manager_id"])
            reply += f"上级：{manager_name}\n"

        return reply


class AddUserSkill(BaseSkill):
    """添加用户技能"""

    @property
    def name(self) -> str:
        return "添加用户"

    @property
    def description(self) -> str:
        return "添加新用户到系统"

    @property
    def keywords(self) -> list:
        return ["添加用户", "新增用户", "注册用户"]

    @property
    def priority(self) -> int:
        return 37

    def can_handle(self, text: str) -> float:
        """判断是否是添加用户请求"""
        text_lower = text.lower()

        if any(kw in text_lower for kw in ["添加用户", "新增用户", "注册用户"]):
            return 0.9

        return 0

    def extract_info(self, text: str) -> dict:
        """提取用户信息"""
        info = {
            "user_id": "",
            "name": "",
            "role": "teacher",
            "department": "",
            "manager": ""
        }

        # 提取用户ID
        id_match = re.search(r'ID[：:]\s*(\S+)', text)
        if id_match:
            info["user_id"] = id_match.group(1)

        # 提取用户名
        name_match = re.search(r'姓名[：:]\s*(\S+)', text)
        if name_match:
            info["name"] = name_match.group(1)

        # 提取角色
        role_map = {
            "管理员": "admin",
            "校长": "principal",
            "主任": "director",
            "教师": "teacher",
            "学生": "student"
        }
        for cn_name, en_name in role_map.items():
            if cn_name in text:
                info["role"] = en_name
                break

        # 提取部门
        dept_match = re.search(r'部门[：:]\s*(\S+)', text)
        if dept_match:
            info["department"] = dept_match.group(1)

        # 提取上级
        manager_match = re.search(r'上级[：:]\s*(\S+)', text)
        if manager_match:
            info["manager"] = manager_match.group(1)

        return info

    async def execute(self, text: str, context: dict) -> str:
        """执行添加用户"""
        from agent.permission_manager import get_permission_manager, UserInfo

        school_config = context.get("school_config")
        if not school_config:
            return "无法获取学校配置，请稍后再试。"

        user_id = context.get("user_id", "")
        corp_id = context.get("corp_id", "")

        # 检查权限（只有管理员可以添加用户）
        perm_manager = get_permission_manager(school_config.knowledge_dir, corp_id)
        user_role = perm_manager.get_user_role(user_id)

        if user_role not in ["admin", "principal"]:
            return "❌ 权限不足：只有管理员可以添加用户。"

        info = self.extract_info(text)

        if not info["name"]:
            return "📝 添加用户命令格式：\n\n" \
                   "添加用户 姓名:[用户名] ID:[用户ID] 角色:[角色] 部门:[部门] 上级:[上级姓名]\n\n" \
                   "示例：\n" \
                   "• 添加用户 姓名:张三 ID:123456 角色:教师 部门:教务处 上级:李四\n" \
                   "• 添加用户 姓名:李四 ID:789012 角色:主任"

        # 如果没有提供用户ID，使用姓名的hash作为ID
        if not info["user_id"]:
            import hashlib
            info["user_id"] = hashlib.md5(info["name"].encode()).hexdigest()[:16]

        # 查找上级
        manager_id = ""
        if info["manager"]:
            for user in perm_manager.list_users():
                if info["manager"] in user.name:
                    manager_id = user.user_id
                    break

        # 创建用户
        new_user = UserInfo(
            user_id=info["user_id"],
            name=info["name"],
            role=info["role"],
            department=info["department"],
            manager_id=manager_id
        )

        if perm_manager.add_user(new_user):
            role_names = {
                "admin": "管理员",
                "principal": "校长",
                "director": "主任",
                "teacher": "教师",
                "student": "学生"
            }

            reply = f"✅ 用户添加成功\n\n"
            reply += f"姓名：{info['name']}\n"
            reply += f"ID：{info['user_id']}\n"
            reply += f"角色：{role_names.get(info['role'], info['role'])}\n"
            if info["department"]:
                reply += f"部门：{info['department']}\n"
            if manager_id:
                manager_name = perm_manager.get_user_name(manager_id)
                reply += f"上级：{manager_name}\n"

            return reply
        else:
            return f"❌ 添加用户失败，用户ID可能已存在。"


class ListPermissionsSkill(BaseSkill):
    """查看权限配置技能"""

    @property
    def name(self) -> str:
        return "查看权限配置"

    @property
    def description(self) -> str:
        return "查看当前组织的权限配置"

    @property
    def keywords(self) -> list:
        return ["权限配置", "查看配置", "权限列表"]

    @property
    def priority(self) -> int:
        return 34

    def can_handle(self, text: str) -> float:
        """判断是否是查看权限配置请求"""
        text_lower = text.lower()

        if any(kw in text_lower for kw in ["权限配置", "查看配置", "权限列表"]):
            return 0.9

        return 0

    def extract_info(self, text: str) -> dict:
        return {}

    async def execute(self, text: str, context: dict) -> str:
        """执行查看权限配置"""
        from agent.permission_manager import get_permission_manager

        school_config = context.get("school_config")
        if not school_config:
            return "无法获取学校配置，请稍后再试。"

        corp_id = context.get("corp_id", "")
        perm_manager = get_permission_manager(school_config.knowledge_dir, corp_id)

        # 获取角色配置
        roles_config = perm_manager._roles_config

        reply = "📋 权限配置\n\n"

        reply += "👥 角色权限：\n"
        for role_id, role_config in roles_config.items():
            role_name = role_config.get("name", role_id)
            permissions = role_config.get("search_permissions", [])
            need_approval = role_config.get("need_approval", False)

            reply += f"\n• {role_name} ({role_id})\n"
            reply += f"  权限：{', '.join(permissions)}\n"
            if need_approval:
                approval_for = role_config.get("approval_for", [])
                reply += f"  需要审批：{', '.join(approval_for)}\n"

        reply += "\n📂 访问级别：\n"
        reply += "• 公开 (public) - 所有人可访问\n"
        reply += "• 内部 (internal) - 教师及以上可访问\n"
        reply += "• 机密 (confidential) - 仅管理员/校长/主任可访问\n"

        # 显示用户统计
        users = perm_manager.list_users()
        reply += f"\n👤 用户统计：共 {len(users)} 人\n"
        role_counts = {}
        for user in users:
            role_counts[user.role] = role_counts.get(user.role, 0) + 1
        for role, count in role_counts.items():
            role_name = perm_manager.get_role_name(role)
            reply += f"• {role_name}：{count} 人\n"

        return reply


# 注册技能
skill_registry.register(SetFilePermissionSkill())
skill_registry.register(SetUserRoleSkill())
skill_registry.register(AddUserSkill())
skill_registry.register(ListPermissionsSkill())
