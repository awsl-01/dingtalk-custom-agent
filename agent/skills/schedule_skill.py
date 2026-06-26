"""
课表管理技能 - 支持调课、查询课表等功能

用法示例：
- "计算机2301班周一上午的课和周二上午的课调换"
- "永久调课：张老师周一第1节和周三第1节"
- "查询计算机2301班的课表"
"""
import re
from typing import Optional, Tuple
from .registry import BaseSkill, skill_registry


class ScheduleSkill(BaseSkill):
    """课表管理技能"""

    @property
    def name(self) -> str:
        return "课表管理"

    @property
    def description(self) -> str:
        return "管理学校课表，支持调课、查询等功能"

    @property
    def keywords(self) -> list:
        return ["课表", "调课", "换课", "课程表", "上课", "第几节"]

    @property
    def priority(self) -> int:
        return 55

    def can_handle(self, text: str) -> float:
        """判断是否是课表相关请求"""
        text_lower = text.lower()

        # 调课关键词
        swap_keywords = ["调课", "换课", "调换", "交换", "对调"]
        for keyword in swap_keywords:
            if keyword in text_lower:
                return 0.9

        # 调课流程关键词（需要配合pending_swap使用）
        swap_flow_keywords = ["永久", "临时", "同意", "拒绝", "取消", "确定", "好的", "确认"]
        for keyword in swap_flow_keywords:
            if text_lower == keyword:  # 精确匹配单个词
                return 0.85

        # 教师名关键词（支持"张老师"、"张老师（数学）"等格式）
        # 但排除个人信息查询场景
        import re
        teacher_pattern = r'[一-龥]+(?:老师|教授|教师)'
        if re.match(teacher_pattern, text.strip()):
            # 排除非课表查询场景
            non_schedule_keywords = ["个人信息", "简介", "介绍", "背景", "资料", "履历",
                                     "职称", "学历", "学位", "研究方向", "论文", "著作",
                                     "联系方式", "电话", "邮箱", "邮箱地址"]
            for keyword in non_schedule_keywords:
                if keyword in text:
                    return 0  # 非课表查询，不匹配
            return 0.85

        # 图片/照片相关关键词（高优先级）
        image_keywords = ["照片", "图片", "图像", "截图", "发给我", "发送"]
        for keyword in image_keywords:
            if keyword in text_lower and ("课" in text_lower or "课表" in text_lower):
                return 0.95

        # 教室查询关键词（高优先级）
        import re
        classroom_patterns = [
            r'\d+\s*教室',  # 102教室、102 教室
            r'实验室\d*',  # 实验室、实验室1
            r'微机室\d*',  # 微机室、微机室2
            r'音乐教室',
            r'美术教室',
            r'通用技术教室',
            r'操场',
        ]
        for pattern in classroom_patterns:
            if re.search(pattern, text):
                # 教室查询需要包含"课"或"课程"等关键词
                if any(w in text for w in ["课", "课程", "上什么", "有什么", "安排"]):
                    return 0.85

        # 查询关键词（精确短语）
        query_keywords = ["课表", "课程表", "上课", "第几节", "什么课", "有哪些课", "都有什么课", "有什么课"]
        for keyword in query_keywords:
            if keyword in text_lower:
                return 0.7

        # 模式匹配：包含"课"且包含班级名或"什么/哪些/几"
        if "课" in text_lower:
            # 支持多种班级名格式：高一(1)班、高一1班、计算机2301班等
            class_patterns = [
                r'[高初][一二三]\s*[（(]\d+[）)]\s*班',  # 高一(1)班、高一（1）班
                r'[高初][一二三]\d+\s*班',  # 高一1班
                r'[一-龥]+\d{4}\s*班',  # 计算机2301班
                r'[一-龥]+\d+\s*班',  # 三年级2班
            ]
            for pattern in class_patterns:
                if re.search(pattern, text):
                    return 0.8  # 匹配到班级名，返回较高置信度
            # 包含"什么/哪些/几/有"等查询词
            if any(w in text for w in ["什么", "哪些", "几", "有"]):
                return 0.7

        return 0

    def extract_info(self, text: str) -> dict:
        """提取调课信息"""
        info = {
            "action": "query",  # query, swap
            "class_name": "",
            "day1": "",
            "period1": "",
            "day2": "",
            "period2": "",
            "permanent": None,  # None 表示未指定，需要询问用户
            "teacher1": "",
            "teacher2": "",
            "course1": "",
            "course2": "",
        }

        # 提取班级（支持多种格式）
        class_patterns = [
            r'([高初][一二三])\s*[（(](\d+)[）)]\s*班',  # 高一(1)班
            r'([高初][一二三])(\d+)\s*班',  # 高一1班
            r'([一-龥]+\d{4}班)',
            r'([一-龥]+(?:科学与技术)?\d{4}班)',
            r'(\d{4}[一-龥]+班)',
            r'([一-龥]+[一二三四五六七八九十]年级[一-龥]+班)',
        ]
        for pattern in class_patterns:
            class_match = re.search(pattern, text)
            if class_match:
                if class_match.lastindex and class_match.lastindex >= 2:
                    # 格式: 高一(1)班 -> 高一(1)班
                    info["class_name"] = f"{class_match.group(1)}({class_match.group(2)})班"
                else:
                    info["class_name"] = class_match.group(1)
                break

        # 提取教师（支持"张教授"、"王老师"等格式）
        teacher_patterns = [
            r'([一-龥]+)(?:教授|老师|教师)',
            r'（([一-龥]+)）',  # 中文括号中的名字
            r'\(([一-龥]+)\)',  # 英文括号中的名字
        ]
        teachers = []
        for pattern in teacher_patterns:
            matches = re.findall(pattern, text)
            teachers.extend([t for t in matches if t])

        if len(teachers) >= 2:
            info["teacher1"] = teachers[0]
            info["teacher2"] = teachers[1]
        elif len(teachers) == 1:
            info["teacher1"] = teachers[0]

        # 提取课程名称（在"节"和"（"之间）
        course_pattern = r'节\s*([一-龥A-Z]+)\s*[（(]'
        courses = re.findall(course_pattern, text)

        if len(courses) >= 2:
            info["course1"] = courses[0].strip()
            info["course2"] = courses[1].strip()
        elif len(courses) == 1:
            info["course1"] = courses[0].strip()

        # 备用模式：直接提取括号前的中文+英文
        if not info["course1"]:
            alt_pattern = r'([一-龥]+[A-Z]?)\s*[（(]'
            alt_courses = re.findall(alt_pattern, text)
            # 过滤掉班级名和太短的匹配
            alt_courses = [c for c in alt_courses if len(c) >= 3 and '班' not in c]
            if len(alt_courses) >= 2:
                info["course1"] = alt_courses[0]
                info["course2"] = alt_courses[1]
            elif len(alt_courses) == 1:
                info["course1"] = alt_courses[0]

        # 第三种模式：提取"数学课"、"物理课"等格式（无括号）
        if not info["course1"]:
            subject_list = ["语文", "数学", "英语", "物理", "化学", "生物",
                          "历史", "地理", "政治", "体育", "音乐", "美术"]
            found_subjects = []
            for subj in subject_list:
                if subj in text:
                    found_subjects.append(subj)
            if len(found_subjects) >= 2:
                info["course1"] = found_subjects[0]
                info["course2"] = found_subjects[1]
            elif len(found_subjects) == 1:
                info["course1"] = found_subjects[0]

        # 判断是否是调课
        swap_keywords = ["调课", "换课", "调换", "交换", "对调", "换"]
        if any(keyword in text for keyword in swap_keywords):
            info["action"] = "swap"

            # 提取第一天和第二天
            day_pattern = r'(周[一二三四五六日]|星期[一二三四五六日])'
            days = re.findall(day_pattern, text)
            if len(days) >= 2:
                info["day1"] = days[0]
                info["day2"] = days[1]
            elif len(days) == 1:
                info["day1"] = days[0]

            # 提取节次（支持多种格式）
            # 格式1: "周一第1节" 或 "周三第3节"
            single_pattern = r'周[一二三四五六日]\s*第?\s*(\d+)\s*节'
            singles = re.findall(single_pattern, text)

            # 格式2: "周一上午1-2节" 或 "周三5-6节"
            range_pattern = r'周[一二三四五六日]\s*(上午|下午|晚上)?\s*(\d+)\s*-\s*(\d+)\s*节'
            ranges = re.findall(range_pattern, text)

            # 格式3: "周一上午第一节课" 或 "周三下午第二节课"（中文数字）
            cn_num_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                          '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
            cn_period_pattern = r'周[一二三四五六日]\s*(上午|下午|晚上)?\s*第?([一二三四五六七八九十]+)\s*节课?'
            cn_periods = re.findall(cn_period_pattern, text)

            # 合并结果
            periods = []
            for s in singles:
                periods.append(("", s, s))
            for r in ranges:
                periods.append(r)
            for time_val, cn_num in cn_periods:
                if cn_num in cn_num_map:
                    num = str(cn_num_map[cn_num])
                    periods.append((time_val, num, num))

            if len(periods) >= 2:
                period1 = periods[0]
                period2 = periods[1]
                time1 = period1[0] if period1[0] else ""
                time2 = period2[0] if period2[0] else ""
                info["period1"] = f"{time1}第{period1[1]}-{period1[2]}节" if time1 else f"第{period1[1]}-{period1[2]}节"
                info["period2"] = f"{time2}第{period2[1]}-{period2[2]}节" if time2 else f"第{period2[1]}-{period2[2]}节"
            elif len(periods) == 1:
                period1 = periods[0]
                time1 = period1[0] if period1[0] else ""
                info["period1"] = f"{time1}第{period1[1]}-{period1[2]}节" if time1 else f"第{period1[1]}-{period1[2]}节"

            # 判断是否永久/临时
            if "临时" in text:
                info["permanent"] = False
            elif "永久" in text:
                info["permanent"] = True

        return info

    async def execute(self, text: str, context: dict) -> str:
        """执行课表操作"""
        import logging
        import os
        logger = logging.getLogger(__name__)

        try:
            from agent.knowledge_base_v2 import get_knowledge_base
            from .scheduling.swap_manager import SwapManager, SwapStatus

            info = self.extract_info(text)
            school_config = context.get("school_config")

            if not school_config:
                return "无法获取学校配置，请稍后再试。"

            # 获取用户信息
            user_id = context.get("user_id", "")
            user_nick = context.get("sender_nick", "")
            user_role = context.get("user_role", "teacher")

            logger.info(f"课表技能执行: action={info['action']}, text={text[:50]}")

            # 初始化调课管理器
            swap_dir = os.path.join(school_config.knowledge_dir, "scheduling")
            swap_manager = SwapManager(swap_dir)

            # 先检查是否有待处理的调课流程
            pending_swap = swap_manager.get_pending_for_user(user_id)
            logger.info(f"检查待处理调课请求: user_id={user_id}, pending_swap={pending_swap is not None}")
            if pending_swap:
                logger.info(f"待处理调课请求状态: {pending_swap.status}, swap_id={pending_swap.swap_id}")
                # 检查用户的输入是否是调课相关的（同意/拒绝/取消/教师名/永久/临时/调课/换课）
                # 如果是普通课表查询，跳过调课流程
                swap_related_keywords = ["同意", "拒绝", "取消", "确定", "好的", "确认", "yes", "no", "永久", "临时", "调课", "换课", "调换", "交换", "对调"]
                text_lower = text.strip().lower()

                # 检查是否是调课相关回复
                is_swap_response = False
                if any(keyword in text_lower for keyword in swap_related_keywords):
                    is_swap_response = True
                    logger.info(f"检测到调课相关关键词: {text[:20]}")
                # 检查是否是教师选择（从教师列表中选择）
                elif pending_swap.status == SwapStatus.SELECTING.value:
                    # 加载教师列表检查是否匹配
                    data_file = os.path.join(school_config.knowledge_dir, "scheduling", "scheduling_data.json")
                    if os.path.exists(data_file):
                        import json
                        with open(data_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        # 提取教师名（支持"张老师（数学）"、"张老师"等格式）
                        import re
                        teacher_name_match = re.match(r'([一-龥]+(?:老师|教授|教师))', text.strip())
                        extracted_name = teacher_name_match.group(1) if teacher_name_match else text.strip()

                        for t in data.get("teachers", []):
                            teacher_name = t.get("name", "")
                            if extracted_name == teacher_name or extracted_name in teacher_name or teacher_name in extracted_name:
                                is_swap_response = True
                                logger.info(f"检测到教师名: {extracted_name}")
                                break

                if is_swap_response:
                    # 根据状态分发到不同的处理步骤
                    logger.info(f"进入调课流程: status={pending_swap.status}")
                    return await self._handle_swap_step(
                        pending_swap, text, swap_manager, school_config, context,
                        user_id, user_nick, user_role
                    )
                else:
                    # 不是调课相关，当作普通课表查询，清除待处理状态
                    logger.info(f"用户输入非调课相关，当作普通查询: {text[:30]}")

            # 检查是否是新的调课请求
            if info["action"] == "swap":
                kb = get_knowledge_base(school_config.knowledge_dir, school_config.corp_id)
                return await self._handle_swap(kb, info, user_id, user_nick, user_role, school_config, context, swap_manager)
            else:
                kb = get_knowledge_base(school_config.knowledge_dir, school_config.corp_id)
                return await self._handle_query(kb, info, text, user_id, user_nick, user_role, school_config, context)

        except Exception as e:
            logger.error(f"课表技能执行失败: {e}", exc_info=True)
            return f"查询课表时出现错误：{str(e)}\n\n💡 请确保已上传课表文件，然后再试。"

    async def _handle_swap_step(self, swap_request, text: str, swap_manager,
                                 school_config, context: dict,
                                 user_id: str, user_nick: str, user_role: str) -> str:
        """
        处理调课流程的各个步骤

        根据 swap_request.status 分发到不同的处理逻辑
        """
        import logging
        import os
        logger = logging.getLogger(__name__)

        from .scheduling.swap_manager import SwapStatus
        from agent.knowledge_base_v2 import get_knowledge_base

        status = swap_request.status
        logger.info(f"_handle_swap_step: status={status}, text={text[:30]}")

        # ── 步骤0: 等待选择调课类型（永久/临时）──
        if status == SwapStatus.PENDING_TYPE.value:
            logger.info(f"处理 PENDING_TYPE 状态")
            # 检查是否取消
            if text.strip() in ["取消", "取消调课", "算了"]:
                swap_manager.cancel_request(swap_request.swap_id, user_id)
                return "✅ 调课已取消。"

            # 检查是否选择了调课类型
            text_lower = text.strip()
            permanent = None
            if "永久" in text_lower:
                permanent = True
            elif "临时" in text_lower:
                permanent = False

            logger.info(f"检查调课类型: permanent={permanent}")

            if permanent is None:
                # 用户输入不是"永久"或"临时"，可能是新的调课请求或课表查询
                # 检查是否是新的调课请求
                new_swap_keywords = ["调课", "换课", "调换", "交换", "对调"]
                is_new_swap_request = any(keyword in text for keyword in new_swap_keywords)

                if is_new_swap_request:
                    # 用户发送了新的调课请求，取消当前的调课，创建新的调课请求
                    swap_manager.cancel_request(swap_request.swap_id, user_id)
                    logger.info(f"用户发送新调课请求，取消旧调课，创建新调课")
                    # 重新进入调课流程
                    info = self.extract_info(text)
                    kb = get_knowledge_base(school_config.knowledge_dir, school_config.corp_id)
                    return await self._handle_swap(kb, info, user_id, user_nick, user_role, school_config, context, swap_manager)
                else:
                    # 用户输入不是调课相关，可能是课表查询，自动取消调课并转为普通查询
                    swap_manager.cancel_request(swap_request.swap_id, user_id)
                    logger.info(f"用户输入非调课相关，自动取消调课，转为普通查询")
                    # 继续走普通课表查询流程
                    info = self.extract_info(text)
                    kb = get_knowledge_base(school_config.knowledge_dir, school_config.corp_id)
                    return await self._handle_query(kb, info, text, user_id, user_nick, user_role, school_config, context)

            # 更新调课类型，进入下一步
            swap_manager.select_type(swap_request.swap_id, permanent)

            # 重新获取更新后的请求
            swap_request = swap_manager.get_request(swap_request.swap_id)

            # 查询并返回空闲教师名单
            data_file = os.path.join(school_config.knowledge_dir, "scheduling", "scheduling_data.json")
            teachers_list = ""
            if os.path.exists(data_file):
                import json
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                free_teachers = []
                for t in data.get('teachers', []):
                    subjects = ", ".join(t.get('subjects', []))
                    free_teachers.append(f"  {t['name']}（{subjects}）")
                teachers_list = "\n".join(free_teachers) if free_teachers else "  （暂无空闲教师）"

            perm_text = "永久" if permanent else "临时"
            return f"✅ 已选择{perm_text}调课\n\n" \
                   f"📋 调课信息确认\n\n" \
                   f"  班级：{swap_request.class_name}\n" \
                   f"  {swap_request.day1} 第{swap_request.period1}节：{swap_request.course1_name}（{swap_request.course1_teacher}）\n" \
                   f"  {swap_request.day2} 第{swap_request.period2}节：{swap_request.course2_name}（{swap_request.course2_teacher}）\n" \
                   f"  类型：{perm_text}调课\n\n" \
                   f"👨‍🏫 可选教师名单：\n{teachers_list}\n\n" \
                   f"请回复教师姓名选择调换对象，或回复「取消」"

        # ── 步骤1: 等待发起人选择调换对象 ──
        if status == SwapStatus.SELECTING.value:
            # 检查是否取消
            if text.strip() in ["取消", "取消调课", "算了"]:
                swap_manager.cancel_request(swap_request.swap_id, user_id)
                return "✅ 调课已取消。"

            # 加载教师数据
            data_file = os.path.join(school_config.knowledge_dir, "scheduling", "scheduling_data.json")
            if not os.path.exists(data_file):
                return "❌ 排课数据不存在。"

            import json
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 判断输入是否像教师名
            target_nick = text.strip()
            # 提取教师名（支持"张老师（数学）"、"张老师"等格式）
            import re
            teacher_name_match = re.match(r'([一-龥]+(?:老师|教授|教师))', target_nick)
            extracted_name = teacher_name_match.group(1) if teacher_name_match else target_nick

            teacher_names = [t.get("name", "") for t in data.get("teachers", [])]
            is_teacher_name = any(extracted_name == name or extracted_name in name or name in extracted_name for name in teacher_names)

            # 检查是否是新的调课请求（包含"调课"、"换课"等关键词）
            new_swap_keywords = ["调课", "换课", "调换", "交换", "对调"]
            is_new_swap_request = any(keyword in text for keyword in new_swap_keywords)

            if is_new_swap_request:
                # 用户发送了新的调课请求，取消当前的调课，创建新的调课请求
                swap_manager.cancel_request(swap_request.swap_id, user_id)
                logger.info(f"用户发送新调课请求，取消旧调课，创建新调课")
                # 重新进入调课流程
                info = self.extract_info(text)
                kb = get_knowledge_base(school_config.knowledge_dir, school_config.corp_id)
                return await self._handle_swap(kb, info, user_id, user_nick, user_role, school_config, context, swap_manager)
            elif not is_teacher_name:
                # 不是教师名，也不是新调课请求 → 可能是课表查询，自动取消调课并转为普通查询
                swap_manager.cancel_request(swap_request.swap_id, user_id)
                logger.info(f"用户输入非教师名「{target_nick}」，自动取消调课，转为普通查询")
                # 继续走普通课表查询流程
                info = self.extract_info(text)
                kb = get_knowledge_base(school_config.knowledge_dir, school_config.corp_id)
                return await self._handle_query(kb, info, text, user_id, user_nick, user_role, school_config, context)

            # 查找目标教师（使用提取的教师名）
            target_teacher = None
            for t in data.get("teachers", []):
                teacher_name = t.get("name", "")
                if extracted_name == teacher_name or extracted_name in teacher_name or teacher_name in extracted_name:
                    target_teacher = t
                    break

            if not target_teacher:
                return f"❌ 未找到教师「{target_nick}」，请从列表中选择：\n" + \
                       self._format_free_teachers_list(data, swap_request)

            # 获取目标教师的钉钉用户ID
            target_dingtalk_id = target_teacher.get("dingtalk_user_id", "")
            if not target_dingtalk_id:
                logger.warning(f"教师 {target_teacher['name']} 未绑定钉钉账号")

            # 选择目标
            swap_manager.select_target(
                swap_request.swap_id,
                target_teacher["id"],
                target_teacher["name"]
            )

            # 向对方教师发送确认请求
            perm_manager = None
            try:
                from agent.permission_manager import get_permission_manager
                perm_manager = get_permission_manager(school_config.knowledge_dir, school_config.corp_id)
            except:
                pass

            # 构建调课信息
            perm_text = "永久" if swap_request.permanent else "临时"
            confirm_msg = f"""📞 调课确认请求

{swap_request.requester_nick} 请求与您调课：

📅 班级：{swap_request.class_name}
  {swap_request.day1} 第{swap_request.period1}节：{swap_request.course1_name}（{swap_request.course1_teacher}）
  ↔ 换为
  {swap_request.day2} 第{swap_request.period2}节：{swap_request.course2_name}（{target_teacher['name']}）

⏰ 类型：{perm_text}调课
{f'📝 原因：{swap_request.reason}' if swap_request.reason else ''}

请回复「同意」或「拒绝」"""

            # 发送消息给对方教师
            if target_dingtalk_id:
                try:
                    # 使用绑定的钉钉用户ID发送消息
                    context["_swap_notify_to"] = target_dingtalk_id
                    context["_swap_notify_msg"] = confirm_msg
                    logger.info(f"调课确认请求将发送给: {target_teacher['name']} (钉钉ID: {target_dingtalk_id})")
                except Exception as e:
                    logger.warning(f"发送调课确认失败: {e}")
            else:
                logger.warning(f"教师 {target_teacher['name']} 未绑定钉钉账号，无法发送通知")

            return f"✅ 已向 {target_teacher['name']} 发送调课确认请求，请等待对方回复。\n\n" \
                   f"📋 调课信息详情：\n" \
                   f"  班级：{swap_request.class_name}\n" \
                   f"  {swap_request.day1} 第{swap_request.period1}节：{swap_request.course1_name}（{swap_request.course1_teacher}）\n" \
                   f"  ↔ 换为\n" \
                   f"  {swap_request.day2} 第{swap_request.period2}节：{swap_request.course2_name}（{target_teacher['name']}）\n" \
                   f"  类型：{perm_text}调课\n\n" \
                   f"💡 您也可以回复「取消」取消本次调课。"

        # ── 步骤2: 等待对方教师确认 ──
        elif status == SwapStatus.CONFIRMING.value:
            # 检查是否是目标教师本人或发起人
            if user_id != swap_request.target_teacher_id and user_id != swap_request.requester_id:
                return "⏳ 当前有调课确认请求等待您处理。"

            # 检查是否是新的调课请求
            new_swap_keywords = ["调课", "换课", "调换", "交换", "对调"]
            is_new_swap_request = any(keyword in text for keyword in new_swap_keywords)

            if is_new_swap_request:
                # 用户发送了新的调课请求，取消当前的调课，创建新的调课请求
                swap_manager.cancel_request(swap_request.swap_id, user_id)
                logger.info(f"用户发送新调课请求，取消旧调课，创建新调课")
                # 重新进入调课流程
                info = self.extract_info(text)
                kb = get_knowledge_base(school_config.knowledge_dir, school_config.corp_id)
                return await self._handle_swap(kb, info, user_id, user_nick, user_role, school_config, context, swap_manager)

            text_lower = text.strip().lower()
            if text_lower in ["同意", "同意调课", "确认", "yes", "ok"]:
                swap_manager.confirm_by_target(swap_request.swap_id, user_id, approved=True)

                # 查找上级审批人
                approver_id = ""
                approver_nick = ""
                perm_manager = None
                try:
                    from agent.permission_manager import get_permission_manager
                    perm_manager = get_permission_manager(school_config.knowledge_dir, school_config.corp_id)
                    # 查找 dean 角色的用户
                    perm_data = perm_manager._load_perm_data()
                    for uid, uinfo in perm_data.get("users", {}).items():
                        if uinfo.get("role") in ["dean", "vice_principal", "principal"]:
                            approver_id = uid
                            approver_nick = uinfo.get("name", "")
                            break
                except:
                    pass

                if not approver_id:
                    # 没有找到审批人，直接执行
                    swap_manager.approve_by_superior(swap_request.swap_id, "system", "系统自动审批", True)
                    return self._execute_swap_result(swap_request, swap_manager, school_config, context)

                # 更新审批人信息
                swap_request.approver_id = approver_id
                swap_request.approver_nick = approver_nick
                swap_manager._save()

                # 向上级提交审批
                perm_text = "永久" if swap_request.permanent else "临时"
                approval_msg = f"""📋 调课审批申请

申请人：{swap_request.requester_nick}
对方教师：{swap_request.target_teacher_nick}（已同意）

📅 调课内容：
  {swap_request.class_name} {swap_request.day1}第{swap_request.period1}节 {swap_request.course1_name}
  ↔
  {swap_request.day2}第{swap_request.period2}节 {swap_request.course2_name}

⏰ 类型：{perm_text}调课
{f'📝 原因：{swap_request.reason}' if swap_request.reason else ''}

请回复「同意 {swap_request.swap_id}」或「拒绝 {swap_request.swap_id}」"""

                context["_swap_notify_to"] = approver_id
                context["_swap_notify_msg"] = approval_msg

                return f"✅ {swap_request.target_teacher_nick} 已同意调课。\n\n" \
                       f"📋 已向上级 {approver_nick} 提交审批申请，请等待审批结果。"

            elif text_lower in ["拒绝", "拒绝调课", "不同意", "no"]:
                swap_manager.confirm_by_target(swap_request.swap_id, user_id, approved=False)

                # 通知发起人
                context["_swap_notify_to"] = swap_request.requester_id
                context["_swap_notify_msg"] = f"❌ {swap_request.target_teacher_nick} 拒绝了调课请求。\n\n" \
                                               f"班级：{swap_request.class_name}\n" \
                                               f"{swap_request.day1}第{swap_request.period1}节 ↔ {swap_request.day2}第{swap_request.period2}节"

                return f"❌ 调课已被 {swap_request.target_teacher_nick} 拒绝。"
            else:
                return "请回复「同意」或「拒绝」。"

        # ── 步骤3: 等待上级审批 ──
        elif status == SwapStatus.APPROVING.value:
            if user_id != swap_request.approver_id:
                return "⏳ 当前有调课审批等待处理。"

            text_lower = text.strip()
            approved = None
            if "同意" in text_lower or "批准" in text_lower or "通过" in text_lower:
                approved = True
            elif "拒绝" in text_lower or "驳回" in text_lower:
                approved = False

            if approved is None:
                return f"请回复「同意 {swap_request.swap_id}」或「拒绝 {swap_request.swap_id}」。"

            swap_manager.approve_by_superior(swap_request.swap_id, user_id, user_nick, approved)

            if not approved:
                # 通知发起人和对方教师
                reject_msg = f"❌ 调课审批未通过\n\n" \
                             f"审批人：{user_nick}\n" \
                             f"班级：{swap_request.class_name}\n" \
                             f"{swap_request.day1}第{swap_request.period1}节 ↔ {swap_request.day2}第{swap_request.period2}节"

                context["_swap_notify_to"] = swap_request.requester_id
                context["_swap_notify_msg"] = reject_msg
                return f"❌ 调课审批已拒绝。"

            # 审批通过，执行调课
            return self._execute_swap_result(swap_request, swap_manager, school_config, context)

        return "❓ 调课状态异常，请联系管理员。"

    def _format_free_teachers_list(self, data: dict, swap_request) -> str:
        """格式化空闲教师列表"""
        # 查找当前时间段有课的教师
        busy_teachers = set()
        # 这里简化处理，列出所有教师让用户选择
        teachers = data.get("teachers", [])
        lines = []
        for i, t in enumerate(teachers, 1):
            subjects = ", ".join(t.get("subjects", []))
            lines.append(f"  {i}. {t['name']}（{subjects}）")
        return "\n".join(lines)

    def _execute_swap_result(self, swap_request, swap_manager, school_config, context) -> str:
        """执行调课并返回结果"""
        import os
        import json
        import logging
        logger = logging.getLogger(__name__)

        perm_text = "永久" if swap_request.permanent else "临时"

        if swap_request.permanent:
            # 永久调课：修改课表数据
            schedule_file = os.path.join(school_config.knowledge_dir, "scheduling", "schedule_result.json")
            if os.path.exists(schedule_file):
                try:
                    with open(schedule_file, 'r', encoding='utf-8') as f:
                        schedule_data = json.load(f)

                    # 交换两个条目的时间
                    entry1 = None
                    entry2 = None
                    for e in schedule_data.get("entries", []):
                        if e.get("id") == swap_request.entry1_id:
                            entry1 = e
                        if e.get("id") == swap_request.entry2_id:
                            entry2 = e

                    if entry1 and entry2:
                        slot1 = entry1["time_slot"].copy()
                        slot2 = entry2["time_slot"].copy()
                        entry1["time_slot"] = slot2
                        entry2["time_slot"] = slot1

                        with open(schedule_file, 'w', encoding='utf-8') as f:
                            json.dump(schedule_data, f, ensure_ascii=False, indent=2)

                        logger.info(f"永久调课已执行: {swap_request.swap_id}")
                except Exception as e:
                    logger.error(f"执行永久调课失败: {e}")
        else:
            logger.info(f"临时调课已记录: {swap_request.swap_id}（不修改课表）")

        # 构建结果消息
        result = f"✅ 调课已完成！\n\n"
        result += f"📅 {swap_request.class_name}\n"
        result += f"  {swap_request.day1} 第{swap_request.period1}节：{swap_request.course1_name}（{swap_request.course1_teacher}）\n"
        result += f"  ↔ 调整为 ↔\n"
        result += f"  {swap_request.day2} 第{swap_request.period2}节：{swap_request.course2_name}（{swap_request.target_teacher_nick}）\n\n"
        result += f"⏰ 类型：{perm_text}调课\n"
        result += f"👨‍🏫 发起人：{swap_request.requester_nick}\n"
        result += f"👨‍🏫 对方教师：{swap_request.target_teacher_nick}\n"
        result += f"👨‍🏫 审批人：{swap_request.approver_nick}\n"

        if swap_request.permanent:
            result += f"\n📅 正式课表已更新"
        else:
            result += f"\n📝 临时调课已记录（不改动正式课表）"

        return result

    async def _handle_swap(self, kb, info: dict, user_id: str = "", user_nick: str = "",
                           user_role: str = "teacher", school_config=None, context: dict = None,
                           swap_manager=None) -> str:
        """
        处理调课请求 — 创建调课流程

        新流程：
        1. 解析调课信息
        2. 查询空闲教师
        3. 创建调课请求
        4. 推送空闲教师名单给发起人
        """
        import logging
        import os
        import json
        from datetime import datetime
        logger = logging.getLogger(__name__)

        if context is None:
            context = {}

        # ── 1. 验证调课信息 ──
        if not info["day1"] or not info["day2"]:
            return "请提供需要调换的两天，例如：\n• '周一第1节和周二第1节调课'\n• '张老师周一和周四调课'"

        # 解析节次
        period1 = self._parse_period(info.get("period1", ""))
        period2 = self._parse_period(info.get("period2", ""))

        # ── 2. 加载排课数据 ──
        if not school_config:
            return "无法获取学校配置"

        knowledge_dir = school_config.knowledge_dir
        schedule_file = os.path.join(knowledge_dir, "scheduling", "schedule_result.json")
        data_file = os.path.join(knowledge_dir, "scheduling", "scheduling_data.json")

        if not os.path.exists(schedule_file) or not os.path.exists(data_file):
            return "未找到排课数据，请先执行排课。"

        with open(schedule_file, 'r', encoding='utf-8') as f:
            schedule_data = json.load(f)

        with open(data_file, 'r', encoding='utf-8') as f:
            scheduling_data = json.load(f)

        if not schedule_data.get("entries"):
            return "排课数据为空，请先执行排课。"

        # ── 3. 如果没有指定节次，按科目查找 ──
        if not period1 or not period2:
            period1, period2 = self._find_periods_by_subject(
                schedule_data, scheduling_data, info
            )

        if not period1 or not period2:
            return "未找到对应的课程，请检查：\n• 班级名是否正确\n• 该天是否有该科目的课程\n\n示例：\n• '周一第1节和周二第3节调课'\n• '高一(1)班周一数学和周三物理调换'"

        # ── 4. 查找要调换的课程 ──
        weekday_map = {
            '周一': '周一', '星期一': '周一',
            '周二': '周二', '星期二': '周二',
            '周三': '周三', '星期三': '周三',
            '周四': '周四', '星期四': '周四',
            '周五': '周五', '星期五': '周五',
        }

        target_day1 = weekday_map.get(info['day1'], info['day1'])
        target_day2 = weekday_map.get(info['day2'], info['day2'])

        # 获取班级名和课程名
        class_name = info.get('class_name', '')
        course1_name = info.get('course1', '')
        course2_name = info.get('course2', '')

        courses_dict = {c['id']: c for c in scheduling_data.get('courses', [])}
        classes_dict = {c['id']: c for c in scheduling_data.get('classes', [])}

        # 查找原课程（精确匹配：时间 + 班级 + 课程）
        entry1 = None
        entry2 = None

        for entry in schedule_data['entries']:
            slot = entry.get('time_slot', {})
            entry_weekday = slot.get('weekday', '')
            entry_period = slot.get('period', 0)

            entry_class = classes_dict.get(entry.get('class_id', ''), {})
            entry_course = courses_dict.get(entry.get('course_id', ''), {})

            # 匹配第一个调课目标
            if entry_weekday == target_day1 and entry_period == period1:
                # 检查班级
                if class_name and class_name != entry_class.get('name', ''):
                    continue
                # 检查课程
                if course1_name and course1_name not in entry_course.get('name', ''):
                    continue
                if not entry1:
                    entry1 = entry

            # 匹配第二个调课目标
            if entry_weekday == target_day2 and entry_period == period2:
                # 检查班级
                if class_name and class_name != entry_class.get('name', ''):
                    continue
                # 检查课程
                if course2_name and course2_name not in entry_course.get('name', ''):
                    continue
                if not entry2:
                    entry2 = entry

        if not entry1 and not entry2:
            return f"未找到 {target_day1} 第{period1}节 和 {target_day2} 第{period2}节 的课程。"

        # ── 4. 获取课程和教师信息 ──
        courses_dict = {c['id']: c for c in scheduling_data.get('courses', [])}
        teachers_dict = {t['id']: t for t in scheduling_data.get('teachers', [])}
        classes_dict = {c['id']: c for c in scheduling_data.get('classes', [])}

        course1 = courses_dict.get(entry1.get('course_id', ''), {})
        course2 = courses_dict.get(entry2.get('course_id', ''), {})
        teacher1 = teachers_dict.get(entry1.get('teacher_id', ''), {})
        teacher2 = teachers_dict.get(entry2.get('teacher_id', ''), {})
        class1 = classes_dict.get(entry1.get('class_id', ''), {})

        # ── 5. 检查是否指定了调课类型 ──
        permanent = info.get("permanent")
        if permanent is None:
            # 未指定类型，创建等待选择类型的请求
            if swap_manager:
                swap_request = swap_manager.create_pending_type_request(
                    requester_id=user_id,
                    requester_nick=user_nick,
                    conversation_id=context.get("conversation_id", ""),
                    corp_id=school_config.corp_id,
                    class_name=class1.get('name', class_name),
                    class_id=entry1.get('class_id', ''),
                    day1=target_day1,
                    period1=period1,
                    day2=target_day2,
                    period2=period2,
                    course1_name=course1.get('name', ''),
                    course1_teacher=teacher1.get('name', ''),
                    course2_name=course2.get('name', ''),
                    course2_teacher=teacher2.get('name', ''),
                    entry1_id=entry1.get('id', ''),
                    entry2_id=entry2.get('id', ''),
                )
                return f"📋 调课信息确认\n\n" \
                       f"  班级：{class1.get('name', class_name)}\n" \
                       f"  {target_day1} 第{period1}节：{course1.get('name', '')}（{teacher1.get('name', '')}）\n" \
                       f"  {target_day2} 第{period2}节：{course2.get('name', '')}（{teacher2.get('name', '')}）\n\n" \
                       f"请选择调课类型：\n" \
                       f"  • 回复「永久」— 修改正式课表\n" \
                       f"  • 回复「临时」— 仅记录，不改课表"
            else:
                return "❌ 调课管理器初始化失败，请联系管理员。"

        if swap_manager:
            swap_request = swap_manager.create_request(
                requester_id=user_id,
                requester_nick=user_nick,
                conversation_id=context.get("conversation_id", ""),
                corp_id=school_config.corp_id,
                class_name=class1.get('name', class_name),
                class_id=entry1.get('class_id', ''),
                day1=target_day1,
                period1=period1,
                day2=target_day2,
                period2=period2,
                course1_name=course1.get('name', ''),
                course1_teacher=teacher1.get('name', ''),
                course2_name=course2.get('name', ''),
                course2_teacher=teacher2.get('name', ''),
                entry1_id=entry1.get('id', ''),
                entry2_id=entry2.get('id', ''),
                permanent=permanent,
            )
        else:
            return "❌ 调课管理器初始化失败，请联系管理员。"

        # ── 6. 查询并推送空闲教师名单 ──
        perm_text = "永久" if permanent else "临时"

        # 构建空闲教师列表（简化：列出所有教师）
        free_teachers = []
        for t in scheduling_data.get('teachers', []):
            subjects = ", ".join(t.get('subjects', []))
            free_teachers.append(f"  {t['name']}（{subjects}）")

        teachers_list = "\n".join(free_teachers) if free_teachers else "  （暂无空闲教师）"

        response = f"📋 调课信息确认\n\n"
        response += f"  班级：{class1.get('name', class_name)}\n"
        response += f"  {target_day1} 第{period1}节：{course1.get('name', '')}（{teacher1.get('name', '')}）\n"
        response += f"  {target_day2} 第{period2}节：{course2.get('name', '')}（{teacher2.get('name', '')}）\n"
        response += f"  类型：{perm_text}调课\n\n"
        response += f"👨‍🏫 可选教师名单：\n{teachers_list}\n\n"
        response += f"请回复教师姓名选择调换对象，或回复「取消」"

        return response

    def _parse_period(self, text: str) -> int:
        """解析节次文本，返回数字"""
        import re

        if not text:
            return 0

        # 直接数字
        match = re.search(r'(\d+)', text)
        if match:
            return int(match.group(1))

        # 中文数字
        cn_num_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                      '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
        for cn, num in cn_num_map.items():
            if cn in text:
                return num

        return 0

    def _find_periods_by_subject(self, schedule_data: dict, scheduling_data: dict, info: dict) -> tuple:
        """
        按科目查找实际节次

        当用户说"高一(1)班周一数学课和周三物理课调换"时，
        需要从排课数据中找到数学课和物理课的实际节次。

        返回: (period1, period2)
        """
        # 星期映射
        weekday_map = {
            '周一': '周一', '星期一': '周一',
            '周二': '周二', '星期二': '周二',
            '周三': '周三', '星期三': '周三',
            '周四': '周四', '星期四': '周四',
            '周五': '周五', '星期五': '周五',
        }

        target_day1 = weekday_map.get(info['day1'], info['day1'])
        target_day2 = weekday_map.get(info['day2'], info['day2'])

        # 获取班级名
        class_name = info.get('class_name', '')

        # 获取课程名
        course1_name = info.get('course1', '')
        course2_name = info.get('course2', '')

        # 构建查找索引
        courses_dict = {c['id']: c for c in scheduling_data.get('courses', [])}
        classes_dict = {c['id']: c for c in scheduling_data.get('classes', [])}

        period1 = 0
        period2 = 0

        # 查找第一个课程的节次（优先精确匹配班级）
        best_entry1 = None
        for entry in schedule_data.get('entries', []):
            slot = entry.get('time_slot', {})
            entry_weekday = slot.get('weekday', '')
            entry_period = slot.get('period', 0)

            if entry_weekday != target_day1:
                continue

            # 检查课程
            entry_course = courses_dict.get(entry.get('course_id', ''), {})
            if not (course1_name and course1_name in entry_course.get('name', '')):
                continue

            # 检查班级
            entry_class = classes_dict.get(entry.get('class_id', ''), {})
            entry_class_name = entry_class.get('name', '')

            if class_name:
                if class_name == entry_class_name:
                    # 精确匹配，直接返回
                    period1 = entry_period
                    break
                elif class_name in entry_class_name or entry_class_name in class_name:
                    # 模糊匹配，记录但继续查找
                    if not best_entry1:
                        best_entry1 = entry
                        period1 = entry_period
            else:
                # 没有指定班级，取第一个匹配
                period1 = entry_period
                break

        # 如果没有精确匹配，使用模糊匹配的结果
        if not period1 and best_entry1:
            period1 = best_entry1.get('time_slot', {}).get('period', 0)

        # 查找第二个课程的节次
        best_entry2 = None
        for entry in schedule_data.get('entries', []):
            slot = entry.get('time_slot', {})
            entry_weekday = slot.get('weekday', '')
            entry_period = slot.get('period', 0)

            if entry_weekday != target_day2:
                continue

            # 检查课程
            entry_course = courses_dict.get(entry.get('course_id', ''), {})
            if not (course2_name and course2_name in entry_course.get('name', '')):
                continue

            # 检查班级
            entry_class = classes_dict.get(entry.get('class_id', ''), {})
            entry_class_name = entry_class.get('name', '')

            if class_name:
                if class_name == entry_class_name:
                    period2 = entry_period
                    break
                elif class_name in entry_class_name or entry_class_name in class_name:
                    if not best_entry2:
                        best_entry2 = entry
                        period2 = entry_period
            else:
                period2 = entry_period
                break

        if not period2 and best_entry2:
            period2 = best_entry2.get('time_slot', {}).get('period', 0)

        return period1, period2

    async def _handle_query(self, kb, info: dict, text: str, user_id: str = "", user_nick: str = "", user_role: str = "teacher", school_config=None, context: dict = None) -> str:
        """处理查询请求"""
        import logging
        import os
        import json
        logger = logging.getLogger(__name__)

        if context is None:
            context = {}

        logger.info(f"课表查询开始: text={text[:50]}")

        # 检测是否是图片请求
        is_image_request = any(keyword in text for keyword in ["照片", "图片", "图像", "截图", "发给我", "发送"])
        logger.info(f"课表查询: is_image_request={is_image_request}, text={text[:50]}")

        # 首先检查排课系统生成的课表
        try:
            # 查找排课数据目录
            knowledge_dir = None
            if school_config:
                knowledge_dir = school_config.knowledge_dir
                logger.info(f"知识库目录: {knowledge_dir}")

            if knowledge_dir:
                schedule_file = os.path.join(knowledge_dir, "scheduling", "schedule_result.json")
                data_file = os.path.join(knowledge_dir, "scheduling", "scheduling_data.json")
                logger.info(f"排课文件: schedule_file={schedule_file}, exists={os.path.exists(schedule_file)}")
                logger.info(f"排课数据: data_file={data_file}, exists={os.path.exists(data_file)}")

                if os.path.exists(schedule_file) and os.path.exists(data_file):
                    # 加载排课数据
                    with open(schedule_file, 'r', encoding='utf-8') as f:
                        schedule_data = json.load(f)

                    with open(data_file, 'r', encoding='utf-8') as f:
                        scheduling_data = json.load(f)

                    logger.info(f"排课结果: entries={len(schedule_data.get('entries', []))}")
                    logger.info(f"排课数据: classes={len(scheduling_data.get('classes', []))}")

                    # 检查是否有排课结果
                    if schedule_data.get("entries"):
                        # 提取班级名（支持中文括号和英文括号）
                        import re
                        class_match = re.search(r'([高初][一二三])\s*[（(](\d+)[）)]\s*班', text)
                        class_name = None
                        class_id = None

                        logger.info(f"班级名匹配结果: {class_match}")

                        if class_match:
                            class_name = f"{class_match.group(1)}({class_match.group(2)})班"
                            logger.info(f"匹配到的班级名: {class_name}")
                            # 查找班级ID
                            for cls in scheduling_data.get("classes", []):
                                if cls["name"] == class_name:
                                    class_id = cls["id"]
                                    logger.info(f"找到班级ID: {class_id}")
                                    break

                        # 如果没有指定班级，但有图片请求，使用第一个班级
                        if is_image_request and not class_id and scheduling_data.get("classes"):
                            first_class = scheduling_data["classes"][0]
                            class_name = first_class["name"]
                            class_id = first_class["id"]
                            logger.info(f"图片请求，使用默认班级: {class_name}")

                        # 如果没有指定班级，但是教师查询或科目查询，使用第一个班级
                        if not class_id and ("老师" in text or "教授" in text or "教师" in text or
                                           "课" in text or "科目" in text):
                            if scheduling_data.get("classes"):
                                first_class = scheduling_data["classes"][0]
                                class_name = first_class["name"]
                                class_id = first_class["id"]
                                logger.info(f"教师/科目查询，使用默认班级: {class_name}")

                        if class_id:
                            # 生成课表
                            from agent.skills.scheduling import Schedule, ClassGroup, Course, Teacher, Classroom

                            schedule = Schedule.from_json(json.dumps(schedule_data))
                            classes = {c["id"]: ClassGroup.from_dict(c) for c in scheduling_data.get("classes", [])}
                            courses = {c["id"]: Course.from_dict(c) for c in scheduling_data.get("courses", [])}
                            teachers = {t["id"]: Teacher.from_dict(t) for t in scheduling_data.get("teachers", [])}
                            classrooms = {c["id"]: Classroom.from_dict(c) for c in scheduling_data.get("classrooms", [])}

                            # 提取查询的日期和节次
                            import re
                            query_day = ""
                            query_period = ""

                            # 提取日期
                            day_match = re.search(r'(周[一二三四五六日]|星期[一二三四五六日])', text)
                            if day_match:
                                query_day = day_match.group(1)

                            # 提取节次
                            period_match = re.search(r'第?(\d+)-?(\d*)节', text)
                            if period_match:
                                start = period_match.group(1)
                                end = period_match.group(2) if period_match.group(2) else start
                                query_period = f"第{start}-{end}节"

                            # 生成课表图片
                            try:
                                img_dir = os.path.join(knowledge_dir, "scheduling")
                                os.makedirs(img_dir, exist_ok=True)
                                img_path = os.path.join(img_dir, f"课表_{class_name}.png")
                                img_result = schedule.to_image(class_id, classes, courses, teachers, img_path, classrooms)
                                # 转为绝对路径，确保钉钉机器人运行时能找到文件
                                img_path = os.path.abspath(img_path)
                                logger.info(f"图片生成结果: {img_result}, 路径: {img_path}, 存在: {os.path.exists(img_path)}")
                                if img_result:
                                    context["_file_to_send"] = img_path
                                    context["_file_name"] = f"{class_name}课程表.png"
                                    context["_file_type"] = "image"
                                    logger.info(f"已设置 context 图片: _file_to_send={context.get('_file_to_send')}")
                            except Exception as e:
                                logger.warning(f"生成课表图片失败: {e}", exc_info=True)

                            # 检测是否查询教室
                            query_classroom = None
                            classroom_match = re.search(r'(\d+)\s*教室', text)
                            if classroom_match:
                                query_classroom = classroom_match.group(1) + "教室"
                            # 也匹配"实验室"、"微机室"等
                            if not query_classroom:
                                classroom_keywords = ["实验室", "微机室", "音乐教室", "美术教室", "操场", "通用技术教室"]
                                for kw in classroom_keywords:
                                    if kw in text:
                                        query_classroom = kw
                                        break

                            # 检测是否查询特定科目
                            query_subject = None
                            subject_list = ["语文", "数学", "英语", "物理", "化学", "生物",
                                          "历史", "地理", "政治", "体育", "音乐", "美术",
                                          "信息技术", "班会", "自习", "选修"]
                            for subj in subject_list:
                                if subj in text:
                                    query_subject = subj
                                    break

                            if query_classroom:
                                # 按教室筛选课表
                                classroom_schedule = schedule.filter_by_classroom(
                                    query_classroom, classes, courses, teachers, classrooms
                                )
                                if classroom_schedule:
                                    response = f"📚 课表查询结果\n\n"
                                    response += f"🏫 {query_classroom} 课程安排：\n"
                                    response += classroom_schedule
                                    response += f"\n\n📄 来自: 排课系统自动生成"
                                else:
                                    response = f"📚 {query_classroom} 本周没有课程安排"
                                return response
                            elif query_subject:
                                # 按科目筛选课表
                                filtered_table = schedule.filter_by_subject(
                                    class_id, query_subject, classes, courses, teachers, classrooms
                                )
                                if filtered_table:
                                    response = f"📚 课表查询结果\n\n"
                                    response += f"📅 {class_name} {query_subject}课安排：\n"
                                    response += filtered_table
                                    response += f"\n\n📄 来自: 排课系统自动生成"
                                else:
                                    response = f"📚 {class_name} 本周没有 {query_subject} 课"
                                return response
                            elif query_day:
                                # 有指定日期，精准查询
                                day_schedule = schedule.filter_by_day(class_id, query_day, classes, courses, teachers, classrooms)
                                if day_schedule:
                                    response = f"📚 课表查询结果\n\n"
                                    response += f"📅 {class_name} {query_day} 课表：\n"
                                    response += day_schedule
                                    response += f"\n\n📄 来自: 排课系统自动生成"
                                else:
                                    response = f"📚 {class_name} {query_day} 没有课程安排"
                                return response
                            elif "老师" in text or "教授" in text or "教师" in text:
                                # 检查是否是非课表查询场景
                                non_schedule_keywords = ["个人信息", "简介", "介绍", "背景", "资料", "履历",
                                                         "职称", "学历", "学位", "研究方向", "论文", "著作",
                                                         "联系方式", "电话", "邮箱", "邮箱地址"]
                                is_non_schedule = any(keyword in text for keyword in non_schedule_keywords)

                                if is_non_schedule:
                                    # 非课表查询，跳过教师课表查询，继续走知识库搜索
                                    logger.info(f"检测到非课表查询关键词，跳过教师课表查询")
                                else:
                                    # 教师课表查询
                                    teacher_schedule = schedule.filter_by_teacher(text, classes, courses, teachers, classrooms)
                                    if teacher_schedule:
                                        response = f"📚 课表查询结果\n\n"
                                        response += f"👨‍🏫 教师课表：\n"
                                        response += teacher_schedule
                                        response += f"\n\n📄 来自: 排课系统自动生成"
                                    else:
                                        response = f"📚 未找到该教师的课表信息"
                                    return response
                            else:
                                # 显示完整课表
                                table = schedule.to_table(class_id, classes, courses, teachers, classrooms)
                                response = f"📚 课表查询结果\n\n"
                                response += f"📅 {class_name} 课表：\n"
                                response += table
                                response += f"\n\n📄 来自: 排课系统自动生成"
                                return response
        except Exception as e:
            logger.warning(f"检查排课系统失败: {e}")

        # 如果排课系统没有结果，从知识库搜索课表
        try:
            search_result = await kb.search(text, top_k=10, method="hybrid", user_id=user_id, user_nick=user_nick, user_role=user_role)
            results = search_result.get("results", []) if isinstance(search_result, dict) else search_result
        except Exception as e:
            logger.error(f"知识库搜索失败: {e}", exc_info=True)
            return f"查询知识库时出现错误：{str(e)}\n\n💡 请确保已上传课表文件。"

        logger.info(f"课表搜索完成: 找到 {len(results)} 条结果")

        if not results:
            return "未找到相关课表信息。请确保已上传课表文件或使用排课系统生成课表。"

        # 提取查询的日期和节次
        query_day = ""
        query_period = ""

        import re
        # 提取日期
        day_match = re.search(r'(周[一二三四五六日]|星期[一二三四五六日])', text)
        if day_match:
            query_day = day_match.group(1)

        # 提取节次
        period_match = re.search(r'第?(\d+)-?(\d*)节', text)
        if period_match:
            start = period_match.group(1)
            end = period_match.group(2) if period_match.group(2) else start
            query_period = f"第{start}-{end}节"

        # 判断是否是具体查询（包含教师名、课程名等具体信息）
        has_specific_query = False
        # 检查是否提取到了教师名或课程名
        if info.get("teacher1") or info.get("course1"):
            has_specific_query = True
        # 检查是否包含教师相关模式（X老师、X教授）
        if re.search(r'[一-龥]+(?:老师|教授|教师)', text):
            has_specific_query = True
        # 检查是否包含"什么课"这类具体查询
        if any(w in text for w in ["什么课", "有哪些课", "有什么课"]):
            has_specific_query = True

        # 优先返回课表文件内容
        file_results = [r for r in results if r.chunk.source_type == 'file' and r.chunk.file_name]

        # 获取课表内容（从文件或文本结果）
        schedule_text = ""
        schedule_source = ""

        if file_results:
            schedule_text = file_results[0].chunk.text
            schedule_source = file_results[0].chunk.file_name
        else:
            # 从文本结果中查找包含课表内容的分块
            schedule_chunks = [r for r in results
                               if any(day in r.chunk.text for day in ['周一', '周二', '周三', '周四', '周五'])
                               or '课表' in r.chunk.text or '课程' in r.chunk.text]
            if schedule_chunks:
                schedule_text = schedule_chunks[0].chunk.text
                schedule_source = schedule_chunks[0].chunk.file_name or schedule_chunks[0].chunk.sender_nick or "知识库"

        # 没有找到课表内容，显示概览
        if not schedule_text:
            seen_files = set()
            schedule_files = []
            for r in file_results:
                fname = r.chunk.file_name
                if fname and fname not in seen_files:
                    seen_files.add(fname)
                    schedule_files.append(fname)

            response = f"📚 课表查询结果\n\n"
            if schedule_files:
                response += f"📄 课表文件（{len(schedule_files)} 个）：\n"
                for i, fname in enumerate(schedule_files, 1):
                    response += f"  {i}. {fname}\n"
            response += f"\n💡 未找到具体课表内容，请确保已上传课表文件。"
            return response

        # 有课表内容，根据查询类型展示
        if query_day:
            # 有指定日期，精准查询
            course_info = self._extract_course_from_schedule(schedule_text, query_day, query_period) if query_period else ""
            if course_info:
                response = f"📚 课表查询结果\n\n"
                response += f"📅 {query_day} {query_period}\n"
                response += f"📖 {course_info}\n"
                response += f"\n📄 来自: {schedule_source}"
            else:
                day_schedule = self._extract_day_schedule(schedule_text, query_day)
                response = f"📚 课表查询结果\n\n"
                response += f"📅 {query_day} 课表：\n"
                response += f"{day_schedule}\n"
                response += f"\n📄 来自: {schedule_source}"
        elif has_specific_query:
            # 有具体查询（教师/课程等），展示匹配的课表内容
            response = f"📚 课表查询结果\n\n"

            # 提取教师名和称谓：匹配 "X教授/老师/教师"，排除"班"开头的误匹配
            teacher_matches = re.findall(r'([一-龥]{1,4})(教授|老师|教师)', text)
            teacher_name = ""
            teacher_title = ""
            for name, title in teacher_matches:
                clean_name = name.lstrip("班")
                if clean_name and len(clean_name) >= 1:
                    teacher_name = clean_name
                    teacher_title = title
                    break
            if not teacher_name:
                teacher_name = info.get("teacher1", "")
                teacher_title = "老师"

            display_name = f"{teacher_name}{teacher_title}" if teacher_name else ""

            if teacher_name:
                # 从课表中提取该教师的具体课程
                matched_courses = []
                for line in schedule_text.split('\n'):
                    if teacher_name not in line:
                        continue
                    # 按 "|" 分割，提取包含教师名的具体课程格
                    parts = line.split('|')
                    day = parts[0].strip() if parts else ""
                    for part in parts[1:]:
                        part = part.strip()
                        if teacher_name in part:
                            matched_courses.append(f"{day} | {part}")

                if matched_courses:
                    response += f"👨‍🏫 {display_name} 的课程：\n\n"
                    for course in matched_courses:
                        response += f"  {course}\n"
                else:
                    # 教师名未直接匹配，展示完整课表让用户查看
                    response += f"👨‍🏫 未找到包含「{display_name}」的课程\n\n"
                    response += f"📋 完整课表：\n"
                    response += schedule_text[:2000]
                    if len(schedule_text) > 2000:
                        response += "\n...(内容过长已截断)"
            else:
                # 展示完整课表内容
                response += f"📋 课表内容：\n\n"
                response += schedule_text[:2000]
                if len(schedule_text) > 2000:
                    response += "\n...(内容过长已截断)"

            response += f"\n\n📄 来自: {schedule_source}"
        else:
            # 无具体查询且无日期，显示课表概览
            seen_files = set()
            schedule_files = []
            for r in file_results:
                fname = r.chunk.file_name
                if fname and fname not in seen_files:
                    seen_files.add(fname)
                    schedule_files.append(fname)

            schedule_chunks = [r for r in results if '课表' in r.chunk.text or '课程' in r.chunk.text
                               or any(day in r.chunk.text for day in ['周一', '周二', '周三', '周四', '周五'])]

            response = f"📚 课表查询结果\n\n"
            response += f"🔍 共识别到 {len(schedule_chunks)} 条课表相关信息\n\n"

            if schedule_files:
                response += f"📄 课表文件（{len(schedule_files)} 个）：\n"
                for i, fname in enumerate(schedule_files, 1):
                    response += f"  {i}. {fname}\n"
                response += f"\n💡 请指定日期查询，例如：「周一有什么课」「周三第3-4节」"
            else:
                response += f"📋 知识库中的课表内容：\n\n"
                for i, r in enumerate(results[:5], 1):
                    chunk = r.chunk
                    preview = chunk.text[:150].replace('\n', ' ')
                    if len(chunk.text) > 150:
                        preview += "..."
                    source = f"（来自：{chunk.file_name or chunk.sender_nick or '未知'}）"
                    response += f"{i}. {preview} {source}\n\n"

        return response

    def _extract_course_from_schedule(self, schedule_text: str, day: str, period: str) -> str:
        """从课表中提取指定日期和节次的课程"""
        import re

        # 将中文日期转换为标准格式
        day_map = {
            '周一': '周一', '星期一': '周一',
            '周二': '周二', '星期二': '周二',
            '周三': '周三', '星期三': '周三',
            '周四': '周四', '星期四': '周四',
            '周五': '周五', '星期五': '周五',
            '周六': '周六', '星期六': '周六',
            '周日': '周日', '星期日': '周日',
        }
        target_day = day_map.get(day, day)

        # 解析节次
        period_match = re.search(r'第?(\d+)-?(\d*)', period)
        if not period_match:
            return ""

        start_period = int(period_match.group(1))
        end_period = int(period_match.group(2)) if period_match.group(2) else start_period

        # 按行分割课表
        lines = schedule_text.split('\n')

        # 找到目标日期的行
        target_line = ""
        for line in lines:
            if target_day in line:
                target_line = line
                break

        if not target_line:
            return ""

        # 提取该行中的所有课程
        # 格式: "周一 | 课程1 | 课程2 | 课程3 | 课程4 | 课程5 | 课程6 | 课程7 | 课程8"
        courses = target_line.split('|')

        # 按单节计算索引：第1节 -> 索引1, 第2节 -> 索引2, ...
        period_index = start_period

        if 0 < period_index < len(courses):
            course = courses[period_index].strip()
            if course and course != '无课程':
                return course

        return "无课程"

    def _extract_day_schedule(self, schedule_text: str, day: str) -> str:
        """提取指定日期的完整课表"""
        # 将中文日期转换为标准格式
        day_map = {
            '周一': '周一', '星期一': '周一',
            '周二': '周二', '星期二': '周二',
            '周三': '周三', '星期三': '周三',
            '周四': '周四', '星期四': '周四',
            '周五': '周五', '星期五': '周五',
            '周六': '周六', '星期六': '周六',
            '周日': '周日', '星期日': '周日',
        }
        target_day = day_map.get(day, day)

        # 按行分割课表
        lines = schedule_text.split('\n')

        # 找到目标日期的行
        for line in lines:
            if target_day in line:
                # 格式化输出（按单节显示）
                courses = line.split('|')
                result = f"{target_day}:\n"
                # 按单节显示：第1节到第8节
                period_names = [f'第{i}节' for i in range(1, 9)]

                for i, course in enumerate(courses[1:], 0):
                    if i < len(period_names):
                        course = course.strip()
                        if course and course != '无课程':
                            result += f"  {period_names[i]}: {course}\n"

                return result

        return "未找到该日期的课表"


# 注册技能
skill_registry.register(ScheduleSkill())
