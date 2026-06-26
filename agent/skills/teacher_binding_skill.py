"""
教师绑定技能 - 管理教师与钉钉用户的绑定关系

功能：
1. 自动匹配教师与钉钉用户
2. 处理重名教师的匹配
3. 手动绑定/解绑教师
4. 查看绑定状态

使用方式：
- "绑定教师"：开始绑定流程
- "查看绑定"：查看当前绑定状态
- "解绑教师 张老师"：解绑指定教师
"""
import os
import json
import time
import logging
import re
from typing import List, Dict, Optional, Tuple
from .registry import BaseSkill, skill_registry

logger = logging.getLogger(__name__)


class TeacherBindingSkill(BaseSkill):
    """教师绑定技能"""

    @property
    def name(self) -> str:
        return "教师绑定"

    @property
    def description(self) -> str:
        return "管理教师与钉钉用户的绑定关系"

    @property
    def keywords(self) -> list:
        return ["绑定教师", "教师绑定", "绑定钉钉", "教师账号", "查看绑定", "解绑教师"]

    @property
    def priority(self) -> int:
        return 60  # 优先级高于课表管理

    def can_handle(self, text: str) -> float:
        """判断是否是教师绑定相关请求"""
        text_lower = text.lower()

        # 绑定关键词
        bind_keywords = ["绑定教师", "教师绑定", "绑定钉钉", "教师账号"]
        for keyword in bind_keywords:
            if keyword in text_lower:
                return 0.9

        # 查看绑定
        if "查看绑定" in text_lower or "绑定状态" in text_lower:
            return 0.85

        # 解绑
        if "解绑教师" in text_lower or "解绑" in text_lower:
            return 0.85

        return 0

    async def execute(self, text: str, context: dict) -> str:
        """执行教师绑定操作"""
        import logging
        logger = logging.getLogger(__name__)

        try:
            school_config = context.get("school_config")
            if not school_config:
                return "无法获取学校配置，请稍后再试。"

            user_id = context.get("user_id", "")
            user_nick = context.get("sender_nick", "")

            # 检查用户权限
            from agent.permission_manager import get_permission_manager
            perm_manager = get_permission_manager(school_config.knowledge_dir, school_config.corp_id)
            user_role = perm_manager.get_user_role(user_id)

            if user_role not in ["admin", "principal", "director"]:
                return "❌ 只有管理员、校长或主任才能进行教师绑定操作。"

            # 解析操作类型
            text_lower = text.strip().lower()

            if "查看绑定" in text_lower or "绑定状态" in text_lower:
                return await self._handle_view_bindings(school_config)
            elif "解绑教师" in text_lower or "解绑" in text_lower:
                teacher_name = self._extract_teacher_name(text)
                return await self._handle_unbind(teacher_name, school_config, user_id, user_nick)
            else:
                return await self._handle_bind_flow(school_config, user_id, user_nick)

        except Exception as e:
            logger.error(f"教师绑定操作失败: {e}", exc_info=True)
            return f"教师绑定操作出错：{str(e)}"

    def _extract_teacher_name(self, text: str) -> str:
        """从文本中提取教师名"""
        # 匹配 "解绑教师 张老师" 或 "解绑 张老师"
        patterns = [
            r'解绑教师\s*([一-龥]+(?:老师|教授|教师))',
            r'解绑\s*([一-龥]+(?:老师|教授|教师))',
            r'([一-龥]+(?:老师|教授|教师))',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return ""

    async def _handle_view_bindings(self, school_config) -> str:
        """查看绑定状态"""
        data_file = os.path.join(school_config.knowledge_dir, "scheduling", "scheduling_data.json")
        if not os.path.exists(data_file):
            return "❌ 排课数据不存在。"

        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        teachers = data.get("teachers", [])
        if not teachers:
            return "❌ 没有教师数据。"

        # 获取钉钉用户列表
        from agent.permission_manager import get_permission_manager
        perm_manager = get_permission_manager(school_config.knowledge_dir, school_config.corp_id)
        users = perm_manager._users

        # 统计绑定状态
        bound_count = sum(1 for t in teachers if t.get("dingtalk_user_id"))
        unbound_count = len(teachers) - bound_count

        response = "📋 教师绑定状态\n\n"
        response += f"  总计：{len(teachers)} 位教师\n"
        response += f"  已绑定：{bound_count} 位\n"
        response += f"  未绑定：{unbound_count} 位\n\n"

        # 显示详细绑定信息
        response += "📖 详细绑定信息：\n"
        for i, teacher in enumerate(teachers, 1):
            name = teacher.get("name", "")
            subjects = ", ".join(teacher.get("subjects", []))
            dingtalk_id = teacher.get("dingtalk_user_id", "")
            dingtalk_nick = teacher.get("dingtalk_user_nick", "")
            binding_status = teacher.get("binding_status", "未绑定")

            if dingtalk_id:
                response += f"  {i}. {name}（{subjects}）→ 已绑定 [{dingtalk_nick}]\n"
            else:
                response += f"  {i}. {name}（{subjects}）→ 未绑定\n"

        response += "\n💡 发送「绑定教师」开始绑定流程"
        return response

    async def _handle_unbind(self, teacher_name: str, school_config, user_id: str, user_nick: str) -> str:
        """解绑教师"""
        if not teacher_name:
            return "❌ 请指定要解绑的教师，例如：「解绑教师 张老师」"

        data_file = os.path.join(school_config.knowledge_dir, "scheduling", "scheduling_data.json")
        if not os.path.exists(data_file):
            return "❌ 排课数据不存在。"

        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 查找教师
        teacher_found = False
        for teacher in data.get("teachers", []):
            if teacher["name"] == teacher_name:
                if not teacher.get("dingtalk_user_id"):
                    return f"❌ {teacher_name} 未绑定钉钉账号。"

                # 解绑
                teacher["dingtalk_user_id"] = ""
                teacher["dingtalk_user_nick"] = ""
                teacher["binding_status"] = "未绑定"
                teacher["binding_updated_at"] = time.time()
                teacher_found = True
                break

        if not teacher_found:
            return f"❌ 未找到教师「{teacher_name}」。"

        # 保存数据
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return f"✅ 已解绑 {teacher_name} 的钉钉账号。"

    async def _handle_bind_flow(self, school_config, user_id: str, user_nick: str) -> str:
        """处理绑定流程"""
        data_file = os.path.join(school_config.knowledge_dir, "scheduling", "scheduling_data.json")
        if not os.path.exists(data_file):
            return "❌ 排课数据不存在。"

        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        teachers = data.get("teachers", [])
        if not teachers:
            return "❌ 没有教师数据。"

        # 获取钉钉用户列表
        from agent.permission_manager import get_permission_manager
        perm_manager = get_permission_manager(school_config.knowledge_dir, school_config.corp_id)
        users = perm_manager._users

        if not users:
            return "❌ 没有钉钉用户数据。请先添加用户。"

        # 自动匹配教师与钉钉用户
        matches = self._auto_match_teachers(teachers, users)

        # 统计结果
        auto_matched = [m for m in matches if m['status'] == 'auto_matched']
        duplicate_names = [m for m in matches if m['status'] == 'duplicate_names']
        no_match = [m for m in matches if m['status'] == 'no_match']

        response = "🔗 教师绑定流程\n\n"

        if auto_matched:
            response += f"✅ 自动匹配成功：{len(auto_matched)} 位\n"
            for m in auto_matched:
                teacher = m['teacher']
                user = m['user']
                subjects = ", ".join(teacher.get("subjects", []))
                response += f"  • {teacher['name']}（{subjects}）→ {user.name}\n"

            # 保存自动匹配结果
            for m in auto_matched:
                teacher = m['teacher']
                user = m['user']
                for t in data['teachers']:
                    if t['id'] == teacher['id']:
                        t['dingtalk_user_id'] = user.user_id
                        t['dingtalk_user_nick'] = user.name
                        t['binding_status'] = 'auto_matched'
                        t['binding_updated_at'] = time.time()
                        break

        if duplicate_names:
            response += f"\n⚠️ 需要手动确认（重名）：{len(duplicate_names)} 位\n"
            for m in duplicate_names:
                teacher = m['teacher']
                subjects = ", ".join(teacher.get("subjects", []))
                candidates = m['candidates']
                response += f"  • {teacher['name']}（{subjects}）\n"
                response += f"    可选用户：\n"
                for i, user in enumerate(candidates, 1):
                    response += f"      {i}. {user.name}（ID: {user.user_id}）\n"
                response += f"    请回复「绑定 {teacher['name']} 1」选择用户\n"

        if no_match:
            response += f"\n❌ 未找到匹配：{len(no_match)} 位\n"
            for m in no_match:
                teacher = m['teacher']
                subjects = ", ".join(teacher.get("subjects", []))
                response += f"  • {teacher['name']}（{subjects}）\n"

        # 保存数据
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if not duplicate_names:
            response += "\n✅ 绑定流程完成！"

        return response

    def _auto_match_teachers(self, teachers: List[Dict], users: List) -> List[Dict]:
        """自动匹配教师与钉钉用户"""
        matches = []

        for teacher in teachers:
            teacher_name = teacher['name']

            # 跳过已绑定的教师
            if teacher.get('dingtalk_user_id'):
                matches.append({
                    'teacher': teacher,
                    'status': 'already_bound'
                })
                continue

            # 精确匹配姓名
            exact_matches = [u for u in users if u.name == teacher_name]

            if len(exact_matches) == 1:
                # 唯一匹配，自动绑定
                matches.append({
                    'teacher': teacher,
                    'user': exact_matches[0],
                    'status': 'auto_matched'
                })
            elif len(exact_matches) > 1:
                # 重名，需要用户选择
                matches.append({
                    'teacher': teacher,
                    'candidates': exact_matches,
                    'status': 'duplicate_names'
                })
            else:
                # 无匹配，需要手动绑定
                matches.append({
                    'teacher': teacher,
                    'status': 'no_match'
                })

        return matches


# 注册技能
skill_registry.register(TeacherBindingSkill())
