"""
排课系统技能 - 自动排课、冲突检测、课表优化

用法示例：
- "开始排课"
- "自动排课：高一(1)班、高一(2)班"
- "查看排课结果"
- "优化课表"
- "导出课表"
"""
import re
import json
import os
import logging
from typing import Optional, Dict, List
from .registry import BaseSkill, skill_registry

logger = logging.getLogger(__name__)


class SchedulingSkill(BaseSkill):
    """排课系统技能"""

    @property
    def name(self) -> str:
        return "排课系统"

    @property
    def description(self) -> str:
        return "自动排课、冲突检测、课表优化"

    @property
    def keywords(self) -> list:
        return ["排课", "自动排课", "生成课表", "编排课表", "开始排课"]

    @property
    def priority(self) -> int:
        return 50  # 比课表管理(55)更高优先级

    def can_handle(self, text: str) -> float:
        """判断是否是排课相关请求"""
        text_lower = text.lower()

        # 模板请求（高优先级）
        template_keywords = [
            "排课模板", "排课的模板", "排课模板下载", "下载排课模板",
            "排课excel", "排课表格", "excel模板", "excel模板文件",
            "模板文件", "排课文件", "发送模板", "发送excel",
        ]
        for keyword in template_keywords:
            if keyword in text_lower:
                return 0.98  # 最高置信度

        # 模板 + 动作的组合（不需要"排课"前缀）
        template_action_patterns = [
            (r"模板", r"(发|给我|下载|要|求|提供|发一下|发个|传|发来)"),
            (r"(发|给我|下载|要|求|提供)", r"模板"),
        ]
        for pat_a, pat_b in template_action_patterns:
            if re.search(pat_a, text) and re.search(pat_b, text):
                return 0.95

        # 导出课表（高优先级，优先于课表查询）
        if "导出" in text_lower and "课表" in text_lower:
            return 0.95

        # 高置信度关键词
        high_confidence = ["排课", "自动排课", "编排课表", "优化课表", "开始排课"]
        for keyword in high_confidence:
            if keyword in text_lower:
                return 0.95

        # 中置信度关键词
        medium_confidence = ["生成课表", "开始排课", "排课系统"]
        for keyword in medium_confidence:
            if keyword in text_lower:
                return 0.8

        # 低置信度模式
        if "课表" in text_lower and ("生成" in text_lower or "编排" in text_lower):
            return 0.7

        # 检测排课数据格式：包含"班级"、"教师"、"课程"中的至少两个
        has_class = "班级" in text or "班" in text
        has_teacher = "教师" in text or "老师" in text
        has_course = "课程" in text or "课时" in text

        if (has_class and has_teacher) or (has_class and has_course) or (has_teacher and has_course):
            return 0.85  # 高置信度，可能是排课数据

        return 0

    def extract_info(self, text: str) -> dict:
        """提取排课请求信息"""
        info = {
            "action": "schedule",  # schedule, optimize, export, view
            "classes": [],
            "grade": "",
        }

        # 判断操作类型
        if "优化" in text:
            info["action"] = "optimize"
        elif "导出" in text or "下载" in text:
            info["action"] = "export"
        elif "查看" in text or "显示" in text:
            info["action"] = "view"

        # 提取班级
        class_patterns = [
            r'([一-龥]+\d{4}班)',
            r'([一-龥]+(?:科学与技术)?\d{4}班)',
            r'(\d{4}[一-龥]+班)',
            r'([一-龥]+[一二三四五六七八九十]年级[一-龥]+班)',
            r'高[一二三]\(\d+\)班',
            r'初[一二三]\(\d+\)班',
        ]
        for pattern in class_patterns:
            matches = re.findall(pattern, text)
            info["classes"].extend(matches)

        # 提取年级
        grade_patterns = [
            r'(高[一二三])',
            r'(初[一二三])',
            r'([一二三四五六七八九]年级)',
        ]
        for pattern in grade_patterns:
            grade_match = re.search(pattern, text)
            if grade_match:
                info["grade"] = grade_match.group(1)
                break

        return info

    async def execute(self, text: str, context: dict) -> str:
        """执行排课操作"""
        try:
            info = self.extract_info(text)
            school_config = context.get("school_config")

            if not school_config:
                return "无法获取学校配置，请稍后再试。"

            logger.info(f"排课技能执行: action={info['action']}, text={text[:50]}")

            # 检测是否是模板请求
            if self._is_template_request(text):
                return await self._handle_template_request(context)

            # 检测是否是排课数据输入（包含班级、教师、课程信息）
            if self._is_scheduling_data(text):
                return await self._handle_data_input(text, context)

            # 根据操作类型分发
            if info["action"] == "schedule":
                return await self._handle_schedule(info, context)
            elif info["action"] == "optimize":
                return await self._handle_optimize(info, context)
            elif info["action"] == "export":
                return await self._handle_export(info, context)
            elif info["action"] == "view":
                return await self._handle_view(info, context)
            else:
                return await self._handle_schedule(info, context)

        except Exception as e:
            logger.error(f"排课技能执行失败: {e}", exc_info=True)
            return f"排课时出现错误：{str(e)}"

    def _is_template_request(self, text: str) -> bool:
        """检测是否是模板请求"""
        template_keywords = [
            "排课模板", "排课的模板", "排课模板下载", "下载排课模板",
            "排课excel", "排课表格", "excel模板", "excel模板文件",
            "模板文件", "排课文件", "发送模板", "发送excel",
        ]
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in template_keywords):
            return True
        # "模板" + 动作词的组合
        if "模板" in text and re.search(r'发|给我|下载|要|求|提供|传', text):
            return True
        return False

    def _is_scheduling_data(self, text: str) -> bool:
        """检测是否是排课数据输入"""
        # 检查是否包含班级、教师、课程信息的典型格式
        has_class = bool(re.search(r'班级[：:]', text)) or bool(re.search(r'[高初][一二三]\(\d+\)班', text))
        has_teacher = bool(re.search(r'教师[：:]', text)) or bool(re.search(r'老师', text))
        has_course = bool(re.search(r'课程[：:]', text)) or bool(re.search(r'\d+\s*课时', text))

        # 至少包含两个数据类别
        return (has_class and has_teacher) or (has_class and has_course) or (has_teacher and has_course)

    async def _handle_template_request(self, context: dict) -> str:
        """处理模板请求，生成并返回排课模板"""
        from .scheduling.excel_handler import generate_template

        school_config = context.get("school_config")
        data_dir = os.path.join(school_config.knowledge_dir, "scheduling")
        os.makedirs(data_dir, exist_ok=True)
        template_file = os.path.join(data_dir, "排课模板.xlsx")

        # 生成模板
        success = generate_template(template_file)

        if success:
            # 将文件路径存入 context，由主处理器统一发送文件
            context["_file_to_send"] = template_file
            context["_file_name"] = "排课模板.xlsx"

            # 返回说明文字
            response = "📋 排课模板已发送！\n\n"
            response += "📄 模板包含以下工作表：\n"
            response += "  1. 班级信息 - 填写班级名称、年级、人数等\n"
            response += "  2. 教师信息 - 填写教师姓名、可教科目等\n"
            response += "  3. 课程信息 - 填写课程名称、周课时数等\n"
            response += "  4. 教室信息 - 填写教室名称、容量、设备等\n"
            response += "  5. 约束配置 - 设置排课约束条件\n\n"
            response += "📝 使用方法：\n"
            response += "  1. 下载并填写模板\n"
            response += "  2. 将填写好的文件发送给我\n"
            response += "  3. 发送「开始排课」执行自动排课\n\n"
            response += "💡 也可以直接发送文字格式的数据"

            return response
        else:
            return "❌ 生成模板失败，请确保已安装 openpyxl：pip install openpyxl"

    async def _handle_data_input(self, text: str, context: dict) -> str:
        """处理排课数据输入"""
        from .scheduling import Teacher, Classroom, Course, ClassGroup
        from .scheduling.excel_handler import parse_scheduling_excel

        # 检查是否是Excel文件路径
        file_path = context.get("_file_path")
        if file_path and file_path.endswith(('.xlsx', '.xls')):
            # 解析Excel文件
            excel_data = parse_scheduling_excel(file_path)
            if excel_data:
                # 使用Excel解析的数据
                data = excel_data
                logger.info(f"从Excel文件解析排课数据: {len(data.get('classes', []))} 班级, "
                           f"{len(data.get('teachers', []))} 教师, {len(data.get('courses', []))} 课程")
            else:
                return "❌ 解析Excel文件失败，请检查文件格式是否正确。"
        else:
            # 解析文本数据
            data = self._parse_scheduling_text(text)

        if not data.get("classes") and not data.get("teachers") and not data.get("courses"):
            return "❌ 无法解析排课数据，请检查格式。\n\n💡 示例格式：\n班级：高一(1)班、高一(2)班\n教师：张老师(数学)、李老师(语文)\n课程：数学(5课时/周)、语文(5课时/周)"

        # 保存数据
        school_config = context.get("school_config")
        data_dir = os.path.join(school_config.knowledge_dir, "scheduling")
        os.makedirs(data_dir, exist_ok=True)
        data_file = os.path.join(data_dir, "scheduling_data.json")

        # 加载已有数据（如果有）
        existing_data = {"classes": [], "teachers": [], "courses": [], "classrooms": []}
        if os.path.exists(data_file):
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except:
                pass

        # 合并数据（避免重复）
        # 班级合并：如果已有同ID班级，更新教室分配信息
        existing_class_ids = {e["id"]: i for i, e in enumerate(existing_data["classes"])}
        for c in data["classes"]:
            if c["id"] in existing_class_ids:
                # 更新已有班级的教室分配
                idx = existing_class_ids[c["id"]]
                if c.get("assigned_classrooms"):
                    existing_data["classes"][idx]["assigned_classrooms"] = c["assigned_classrooms"]
            else:
                existing_data["classes"].append(c)

        existing_data["teachers"].extend([t for t in data["teachers"]
                                          if t["id"] not in [e["id"] for e in existing_data["teachers"]]])
        existing_data["courses"].extend([c for c in data["courses"]
                                         if c["id"] not in [e["id"] for e in existing_data["courses"]]])

        # 如果没有教室数据，添加默认教室
        if not existing_data.get("classrooms"):
            existing_data["classrooms"] = [
                {"id": "room_01", "name": "101教室", "capacity": 50, "equipment": ["多媒体"], "building": "教学楼A"},
                {"id": "room_02", "name": "102教室", "capacity": 50, "equipment": ["多媒体"], "building": "教学楼A"},
                {"id": "room_03", "name": "103教室", "capacity": 50, "equipment": ["多媒体"], "building": "教学楼A"},
                {"id": "room_04", "name": "104教室", "capacity": 50, "equipment": ["多媒体"], "building": "教学楼A"},
                {"id": "room_05", "name": "105教室", "capacity": 50, "equipment": ["多媒体"], "building": "教学楼A"},
                {"id": "room_06", "name": "201教室", "capacity": 50, "equipment": ["多媒体"], "building": "教学楼B"},
                {"id": "room_07", "name": "202教室", "capacity": 50, "equipment": ["多媒体"], "building": "教学楼B"},
                {"id": "room_08", "name": "203教室", "capacity": 50, "equipment": ["多媒体"], "building": "教学楼B"},
                {"id": "room_09", "name": "实验室1", "capacity": 45, "equipment": ["实验设备", "多媒体"], "building": "实验楼"},
                {"id": "room_10", "name": "实验室2", "capacity": 45, "equipment": ["实验设备", "多媒体"], "building": "实验楼"},
            ]

        # 调整教师课时限制，确保能满足需求
        # 计算每个教师的需求课时
        teacher_demand = {}
        for cls in existing_data.get("classes", []):
            for course_id in cls.get("courses", []):
                # 找到能教这门课的教师
                for t in existing_data.get("teachers", []):
                    for subject in t.get("subjects", []):
                        if course_id.endswith(subject):
                            if t["id"] not in teacher_demand:
                                teacher_demand[t["id"]] = 0
                            # 找到课程的课时数
                            for c in existing_data.get("courses", []):
                                if c["id"] == course_id:
                                    teacher_demand[t["id"]] += c.get("hours_per_week", 5)
                                    break

        # 计算总需求和总供给
        total_demand = sum(teacher_demand.values())
        total_supply = sum(t.get("max_hours_per_week", 20) for t in existing_data.get("teachers", []))

        # 如果需求超过供给，自动增加教师
        if total_demand > total_supply:
            logger.warning(f"教师资源不足: 需求={total_demand}课时, 供给={total_supply}课时")

            # 为每个科目添加备用教师
            subjects_teachers = {}
            for t in existing_data.get("teachers", []):
                for subject in t.get("subjects", []):
                    if subject not in subjects_teachers:
                        subjects_teachers[subject] = []
                    subjects_teachers[subject].append(t)

            # 为需求超过供给的科目添加教师
            for subject, demand in teacher_demand.items():
                # 找到能教这门课的教师
                for t in existing_data.get("teachers", []):
                    if subject in t.get("subjects", []):
                        # 计算该教师的缺口
                        teacher_demand_val = teacher_demand.get(t["id"], 0)
                        teacher_supply_val = t.get("max_hours_per_week", 20)

                        if teacher_demand_val > teacher_supply_val:
                            # 添加一个新教师
                            new_teacher_id = f"teacher_{len(existing_data['teachers']) + 1:02d}"
                            new_teacher = {
                                "id": new_teacher_id,
                                "name": f"{t['name']}（备）",
                                "subjects": t["subjects"],
                                "max_hours_per_day": 8,
                                "max_hours_per_week": teacher_demand_val + 10,
                            }
                            existing_data["teachers"].append(new_teacher)
                            logger.info(f"添加备用教师: {new_teacher['name']}")

        # 调整教师最大课时数
        for teacher in existing_data.get("teachers", []):
            demand = teacher_demand.get(teacher["id"], 0)
            if demand > teacher.get("max_hours_per_week", 20):
                teacher["max_hours_per_week"] = demand + 10
            teacher["max_hours_per_day"] = 8

        # 为课程添加标签（主/副课权重、单日上限、专属教室类型）
        main_subjects = ["数学", "语文", "英语"]
        for course in existing_data.get("courses", []):
            is_main = course.get("subject", "") in main_subjects or course.get("is_main_subject", False)
            course["is_main_subject"] = is_main
            course["weight"] = (100 if is_main else 50) + course.get("hours_per_week", 5)
            course["max_per_day"] = 3 if is_main else 2
            # 物理化学默认不限制教室类型（实验室不足时可在普通教室上）
            course["room_type"] = ""

        # 添加约束配置（优化版）
        existing_data["constraints"] = {
            "max_consecutive_hours": 4,
            "main_subject_prefer_morning": True,
            "max_daily_hours_per_teacher": 8,
            "course_even_distribution": False,
            "max_same_subject_per_day": 3,
            "penalty_main_subject_afternoon": 10,
            "penalty_consecutive_over_limit": 5,
            "penalty_teacher_daily_over": 8,
            "penalty_same_course_same_day": 6,
            "penalty_same_subject_over_limit": 4,
        }

        # 保存数据
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)

        # 生成回复
        response = "✅ 排课数据已接收！\n\n"
        response += f"📊 数据统计：\n"
        response += f"  • 班级：{len(data['classes'])} 个\n"
        response += f"  • 教师：{len(data['teachers'])} 人\n"
        response += f"  • 课程：{len(data['courses'])} 门\n"
        response += f"  • 教室：{len(existing_data['classrooms'])} 间（已自动添加）\n\n"

        # 显示解析结果
        if data["classes"]:
            response += "📚 班级列表：\n"
            for c in data["classes"]:
                response += f"  • {c['name']}\n"
            response += "\n"

        if data["teachers"]:
            response += "👨‍🏫 教师列表：\n"
            for t in data["teachers"]:
                response += f"  • {t['name']}（{', '.join(t['subjects'])}）\n"
            response += "\n"

        if data["courses"]:
            response += "📖 课程列表：\n"
            for c in data["courses"]:
                main_tag = " [主课]" if c.get("is_main_subject") else ""
                response += f"  • {c['name']}（{c['hours_per_week']}课时/周）{main_tag}\n"
            response += "\n"

        # 自动执行排课
        response += "🔄 正在自动排课...\n\n"

        try:
            from .scheduling import ScheduleAlgorithm, SchedulingTask, ConstraintManager

            # 构建排课任务
            task = self._build_task(existing_data)

            # 执行排课
            algorithm = ScheduleAlgorithm()
            result = algorithm.schedule(task)

            if result.success:
                # 保存排课结果
                result_file = os.path.join(data_dir, "schedule_result.json")
                with open(result_file, 'w', encoding='utf-8') as f:
                    f.write(result.schedule.to_json())

                response += "✅ 排课完成！\n\n"

                # 显示第一个班级的课表作为预览
                if data["classes"]:
                    first_class = data["classes"][0]
                    classes_dict = {c["id"]: ClassGroup.from_dict(c) for c in existing_data["classes"]}
                    courses_dict = {c["id"]: Course.from_dict(c) for c in existing_data["courses"]}
                    teachers_dict = {t["id"]: Teacher.from_dict(t) for t in existing_data["teachers"]}
                    classrooms_dict = {c["id"]: Classroom.from_dict(c) for c in existing_data.get("classrooms", [])}

                    table = result.schedule.to_table(first_class["id"], classes_dict, courses_dict, teachers_dict, classrooms_dict)
                    response += f"📅 {first_class['name']} 课表预览：\n"
                    response += table
                    response += "\n\n"

                    # 生成并发送第一个班级的课表图片
                    try:
                        img_path = os.path.join(data_dir, f"课表_{first_class['name']}.png")
                        img_path = os.path.abspath(img_path)
                        if result.schedule.to_image(first_class["id"], classes_dict, courses_dict, teachers_dict, img_path, classrooms_dict):
                            context["_file_to_send"] = img_path
                            context["_file_name"] = f"{first_class['name']}课程表.png"
                            context["_file_type"] = "image"
                            response += f"📸 已生成 {first_class['name']} 课表图片\n\n"
                    except Exception as e:
                        logger.warning(f"生成课表图片失败: {e}", exc_info=True)

                response += "💡 可用命令：\n"
                response += "  • 「查看课表 高一(1)班」- 查看指定班级课表\n"
                response += "  • 「优化课表」- 优化课表质量\n"
            else:
                response += f"⚠️ 排课部分完成：{result.message}\n"
                response += f"  • 冲突数：{result.conflicts}\n"
        except Exception as e:
            response += f"❌ 排课失败：{str(e)}\n"
            logger.error(f"自动排课失败: {e}", exc_info=True)

        return response

    def _parse_scheduling_text(self, text: str) -> dict:
        """解析排课文本数据"""
        data = {
            "classes": [],
            "teachers": [],
            "courses": [],
        }

        # 解析班级
        # 格式：班级：高一(1)班、高一(2)班
        # 或：高一(1)班、高一(2)班
        class_section = re.search(r'班级[：:]\s*(.+?)(?=教师[：:]|课程[：:]|$)', text, re.DOTALL)
        if class_section:
            class_text = class_section.group(1)
        else:
            class_text = text

        class_patterns = [
            r'([高初][一二三])\s*\((\d+)\)\s*班',
            r'([高初][一二三])\s*(\d+)\s*班',
            r'(\d{4})\s*([一-龥]+)\s*班',
        ]

        classes_found = set()
        for pattern in class_patterns:
            matches = re.findall(pattern, class_text)
            for match in matches:
                if len(match) == 2:
                    if match[0].startswith(('高', '初')):
                        class_name = f"{match[0]}({match[1]})班"
                    else:
                        class_name = f"{match[0]}{match[1]}班"
                    if class_name not in classes_found:
                        classes_found.add(class_name)
                        # 根据班级名称确定年级
                        grade = ""
                        if "高一" in class_name:
                            grade = "高一"
                        elif "高二" in class_name:
                            grade = "高二"
                        elif "高三" in class_name:
                            grade = "高三"
                        elif "初一" in class_name:
                            grade = "初一"
                        elif "初二" in class_name:
                            grade = "初二"
                        elif "初三" in class_name:
                            grade = "初三"

                        data["classes"].append({
                            "id": f"class_{len(data['classes']) + 1:02d}",
                            "name": class_name,
                            "grade": grade,
                            "student_count": 45,
                            "courses": [],
                            "assigned_classrooms": [],
                        })

        # 解析教师
        # 格式：教师：张老师(数学)、李老师(语文)
        teacher_section = re.search(r'教师[：:]\s*(.+?)(?=班级[：:]|课程[：:]|$)', text, re.DOTALL)
        if teacher_section:
            teacher_text = teacher_section.group(1)
        else:
            teacher_text = text

        # 匹配：张老师(数学) 或 张老师（数学）或 张老师 (数学)
        teacher_pattern = r'([一-龥]+)\s*(?:老师|教授|教师)\s*[（(]\s*([一-龥]+)\s*[）)]'
        teachers_found = re.findall(teacher_pattern, teacher_text)

        # 也匹配单独的教师名（没有科目）
        teacher_pattern2 = r'([一-龥]+)\s*(?:老师|教授|教师)'
        all_teachers = re.findall(teacher_pattern2, teacher_text)

        teachers_with_subject = {t[0] for t in teachers_found}

        for name, subject in teachers_found:
            data["teachers"].append({
                "id": f"teacher_{len(data['teachers']) + 1:02d}",
                "name": f"{name}老师",
                "subjects": [subject],
                "max_hours_per_day": 4,
                "max_hours_per_week": 20,
            })

        # 添加没有科目的教师
        for name in all_teachers:
            if name not in teachers_with_subject:
                data["teachers"].append({
                    "id": f"teacher_{len(data['teachers']) + 1:02d}",
                    "name": f"{name}老师",
                    "subjects": [],
                    "max_hours_per_day": 4,
                    "max_hours_per_week": 20,
                })

        # 解析课程
        # 格式：课程：数学(5课时/周)、语文(5课时/周)
        course_section = re.search(r'课程[：:]\s*(.+?)(?=班级[：:]|教师[：:]|$)', text, re.DOTALL)
        if course_section:
            course_text = course_section.group(1)
        else:
            course_text = text

        # 匹配：数学(5课时/周) 或 数学（5课时/周）或 数学 (5 课时 / 周)
        course_pattern = r'([一-龥A-Za-z]+)\s*[（(]\s*(\d+)\s*课时\s*/\s*(?:周|星期)\s*[）)]'
        courses_found = re.findall(course_pattern, course_text)

        # 主课列表
        main_subjects = ["数学", "语文", "英语", "物理", "化学", "生物"]

        for subject, hours in courses_found:
            is_main = subject in main_subjects
            data["courses"].append({
                "id": f"course_{subject}",
                "name": subject,
                "subject": subject,
                "hours_per_week": int(hours),
                "is_main_subject": is_main,
                "needs_consecutive": False,
                "required_equipment": [],
            })

        # 为班级分配课程
        course_ids = [c["id"] for c in data["courses"]]
        for cls in data["classes"]:
            cls["courses"] = course_ids

        return data

    async def _handle_schedule(self, info: dict, context: dict) -> str:
        """处理排课请求"""
        from .scheduling import (
            ScheduleAlgorithm, SchedulingTask,
            ConstraintManager, Teacher, Classroom, Course, ClassGroup,
        )
        from .scheduling.excel_handler import parse_scheduling_excel

        # 获取学校数据目录
        school_config = context.get("school_config")
        data_dir = os.path.join(school_config.knowledge_dir, "scheduling")
        os.makedirs(data_dir, exist_ok=True)

        # 检查是否有新上传的Excel文件
        files_dir = os.path.join(school_config.knowledge_dir, "files")
        excel_files = []
        if os.path.exists(files_dir):
            for root, dirs, files in os.walk(files_dir):
                for file in files:
                    # 检查文件扩展名和是否包含排课关键词
                    if file.endswith(('.xlsx', '.xls')):
                        # 去掉括号和数字后缀进行匹配
                        base_name = file.split('(')[0]  # 去掉(1)(1)等后缀
                        if '排课' in base_name or '课表' in base_name:
                            excel_files.append(os.path.join(root, file))

        # 如果有Excel文件，解析最新的一个
        if excel_files:
            latest_excel = max(excel_files, key=os.path.getmtime)
            logger.info(f"找到排课Excel文件: {latest_excel}")
            excel_data = parse_scheduling_excel(latest_excel)
            if excel_data:
                # 保存解析后的数据
                data_file = os.path.join(data_dir, "scheduling_data.json")
                with open(data_file, 'w', encoding='utf-8') as f:
                    json.dump(excel_data, f, ensure_ascii=False, indent=2)
                logger.info(f"已从Excel文件更新排课数据")
                data = excel_data
            else:
                return "❌ 解析Excel文件失败，请检查文件格式。"
        else:
            # 检查是否有排课数据
            data_file = os.path.join(data_dir, "scheduling_data.json")
            if not os.path.exists(data_file):
                return self._show_data_guide()

            # 加载排课数据
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                return f"加载排课数据失败：{str(e)}"

        # 构建排课任务
        try:
            task = self._build_task(data)
        except Exception as e:
            return f"构建排课任务失败：{str(e)}"

        # 检查是否有足够的数据
        if not task.classes:
            return "❌ 没有班级信息，请先上传排课数据。"
        if not task.teachers:
            return "❌ 没有教师信息，请先上传排课数据。"
        if not task.courses:
            return "❌ 没有课程信息，请先上传排课数据。"

        # 执行排课
        response = "🔄 正在排课，请稍候...\n\n"
        response += f"📊 排课信息：\n"
        response += f"  • 班级：{len(task.classes)} 个\n"
        response += f"  • 教师：{len(task.teachers)} 人\n"
        response += f"  • 课程：{len(task.courses)} 门\n"
        response += f"  • 教室：{len(task.classrooms)} 间\n\n"

        algorithm = ScheduleAlgorithm()
        result = algorithm.schedule(task)

        if result.success:
            # 保存排课结果
            result_file = os.path.join(data_dir, "schedule_result.json")
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(result.schedule.to_json())

            response += "✅ 排课完成！\n\n"

            # 将课表信息存入知识库
            try:
                from agent.knowledge_base_v2 import get_knowledge_base
                kb = get_knowledge_base(school_config.knowledge_dir, school_config.corp_id)

                # 为每个班级生成课表文本
                for class_id, class_group in task.classes.items():
                    class_schedule = result.schedule.get_class_schedule(class_id)
                    if class_schedule:
                        # 生成课表文本
                        schedule_text = f"【{class_group.name} 课程表】\n\n"

                        # 按时间段组织课表
                        weekdays = ['周一', '周二', '周三', '周四', '周五']
                        periods = ['第1节', '第2节', '第3节', '第4节', '第5节', '第6节', '第7节', '第8节']

                        # 创建课表字典
                        schedule_dict = {}
                        for entry in class_schedule:
                            weekday = entry.time_slot.weekday.value
                            period = f'第{entry.time_slot.period}节'
                            course = task.courses.get(entry.course_id)
                            teacher = task.teachers.get(entry.teacher_id)
                            classroom = task.classrooms.get(entry.classroom_id)

                            if course and teacher:
                                if weekday not in schedule_dict:
                                    schedule_dict[weekday] = {}
                                classroom_name = classroom.name if classroom else ""
                                schedule_dict[weekday][period] = f"{course.name}({teacher.name}@{classroom_name})"

                        # 生成表格文本
                        schedule_text += "| 节次 | 周一 | 周二 | 周三 | 周四 | 周五 |\n"
                        schedule_text += "|------|------|------|------|------|------|\n"
                        for period in periods:
                            row = [period]
                            for weekday in weekdays:
                                cell = schedule_dict.get(weekday, {}).get(period, "")
                                row.append(cell)
                            schedule_text += "| " + " | ".join(row) + " |\n"

                        # 存入知识库
                        await kb.add_message(
                            schedule_text,
                            source_type="system",
                            source_id=f"schedule_{class_id}",
                            file_name=f"{class_group.name}课程表",
                        )
                        logger.info(f"已将{class_group.name}课表存入知识库")

            except Exception as e:
                logger.warning(f"将课表存入知识库失败: {e}", exc_info=True)

            # 显示冲突信息
            if result.conflicts > 0:
                detector = algorithm.conflict_detector
                detector.detect_all(
                    result.schedule, task.teachers, task.classrooms,
                    task.courses, task.classes
                )
                response += detector.format_report(task.teachers, task.courses)
                response += "\n\n"
            else:
                response += "✅ 无冲突！\n\n"

            # 生成第一个班级的课表图片
            if task.classes:
                first_class_id = list(task.classes.keys())[0]
                first_class = task.classes[first_class_id]
                try:
                    img_path = os.path.join(data_dir, f"课表_{first_class.name}.png")
                    img_path = os.path.abspath(img_path)
                    if result.schedule.to_image(first_class_id, task.classes, task.courses, task.teachers, img_path, task.classrooms):
                        context["_file_to_send"] = img_path
                        context["_file_name"] = f"{first_class.name}课程表.png"
                        context["_file_type"] = "image"
                        response += f"📸 已生成 {first_class.name} 课表图片\n\n"
                except Exception as e:
                    logger.warning(f"生成课表图片失败: {e}", exc_info=True)

            response += "💡 可用命令：\n"
            response += "  • 「查看课表 高一(1)班」- 查看班级课表\n"
            response += "  • 「优化课表」- 优化课表质量\n"
            response += "  • 「导出课表」- 导出为 Excel 文件\n"
        else:
            response += "⚠️ 排课部分完成\n"
            response += f"  • {result.message}\n"
            response += f"  • 冲突数：{result.conflicts}\n"

        return response

    async def _handle_optimize(self, info: dict, context: dict) -> str:
        """处理优化请求"""
        from .scheduling import ScheduleAlgorithm, SchedulingTask

        school_config = context.get("school_config")
        data_dir = os.path.join(school_config.knowledge_dir, "scheduling")
        result_file = os.path.join(data_dir, "schedule_result.json")

        if not os.path.exists(result_file):
            return "❌ 未找到排课结果，请先执行排课。"

        # 加载数据
        data_file = os.path.join(data_dir, "scheduling_data.json")
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        task = self._build_task(data)

        # 加载现有课表
        from .scheduling import Schedule
        with open(result_file, 'r', encoding='utf-8') as f:
            schedule = Schedule.from_json(f.read())

        # 优化
        algorithm = ScheduleAlgorithm()
        optimized = algorithm.optimize(schedule, task, iterations=200)

        # 保存优化结果
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(optimized.to_json())

        # 检测冲突
        detector = algorithm.conflict_detector
        conflicts = detector.detect_all(
            optimized, task.teachers, task.classrooms,
            task.courses, task.classes
        )

        response = "✅ 课表优化完成！\n\n"
        if conflicts:
            response += detector.format_report(task.teachers, task.courses)
        else:
            response += "✅ 无冲突！\n"

        return response

    async def _handle_view(self, info: dict, context: dict) -> str:
        """处理查看请求"""
        from .scheduling import Schedule, ClassGroup, Course, Teacher

        school_config = context.get("school_config")
        data_dir = os.path.join(school_config.knowledge_dir, "scheduling")
        result_file = os.path.join(data_dir, "schedule_result.json")

        if not os.path.exists(result_file):
            return "❌ 未找到排课结果，请先执行排课。"

        # 加载课表
        with open(result_file, 'r', encoding='utf-8') as f:
            schedule = Schedule.from_json(f.read())

        # 加载基础数据
        data_file = os.path.join(data_dir, "scheduling_data.json")
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        classes = {c["id"]: ClassGroup.from_dict(c) for c in data.get("classes", [])}
        courses = {c["id"]: Course.from_dict(c) for c in data.get("courses", [])}
        teachers = {t["id"]: Teacher.from_dict(t) for t in data.get("teachers", [])}

        # 如果指定了班级，显示该班级的课表
        if info["classes"]:
            class_name = info["classes"][0]
            class_id = None
            for cid, cls in classes.items():
                if cls.name == class_name:
                    class_id = cid
                    break

            if class_id:
                table = schedule.to_table(class_id, classes, courses, teachers)
                return f"📅 {class_name} 课表\n\n{table}"
            else:
                return f"❌ 未找到班级「{class_name}」"

        # 否则显示所有班级列表
        response = "📚 排课结果\n\n"
        response += f"已排课班级（{len(classes)} 个）：\n"
        for cls in classes.values():
            entry_count = len(schedule.get_class_schedule(cls.id))
            response += f"  • {cls.name}（{entry_count} 节课）\n"

        response += "\n💡 请指定班级查看课表，例如：「查看课表 高一(1)班」"
        return response

    async def _handle_export(self, info: dict, context: dict) -> str:
        """处理导出请求 — 生成 Excel 文件并发送"""
        import os
        import json
        from .scheduling import Schedule, ClassGroup, Course, Teacher, Classroom
        from .scheduling.excel_handler import export_schedule_to_excel

        school_config = context.get("school_config")
        if not school_config:
            return "无法获取学校配置"

        data_dir = os.path.join(school_config.knowledge_dir, "scheduling")
        result_file = os.path.join(data_dir, "schedule_result.json")
        data_file = os.path.join(data_dir, "scheduling_data.json")

        if not os.path.exists(result_file):
            return "❌ 未找到排课结果，请先执行排课。"

        if not os.path.exists(data_file):
            return "❌ 未找到排课数据。"

        # 加载排课结果
        with open(result_file, 'r', encoding='utf-8') as f:
            schedule = Schedule.from_json(f.read())

        # 加载基础数据
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        classes = {c["id"]: ClassGroup.from_dict(c) for c in data.get("classes", [])}
        courses = {c["id"]: Course.from_dict(c) for c in data.get("courses", [])}
        teachers = {t["id"]: Teacher.from_dict(t) for t in data.get("teachers", [])}
        classrooms = {c["id"]: Classroom.from_dict(c) for c in data.get("classrooms", [])}

        # 确定要导出的班级
        export_all = True
        target_class_id = None
        if info.get("classes"):
            class_name = info["classes"][0]
            for cid, cls in classes.items():
                if cls.name == class_name:
                    target_class_id = cid
                    export_all = False
                    break

        # 生成 Excel 文件
        os.makedirs(data_dir, exist_ok=True)

        if export_all:
            output_path = os.path.join(data_dir, "全部班级课表.xlsx")
            label = "全部班级"
        else:
            class_name = classes[target_class_id].name
            output_path = os.path.join(data_dir, f"{class_name}课表.xlsx")
            label = class_name

        try:
            success = export_schedule_to_excel(
                schedule, classes, courses, teachers, output_path, classrooms
            )

            if success:
                output_path = os.path.abspath(output_path)
                # 将文件路径存入 context，由主处理器统一发送文件
                context["_file_to_send"] = output_path
                context["_file_name"] = os.path.basename(output_path)
                context["_file_type"] = "file"

                response = f"📊 {label}课表已导出！\n\n"
                response += f"📄 文件: {os.path.basename(output_path)}\n"
                response += f"📅 包含周一至周五全部课程安排\n\n"
                response += "💡 也可以指定班级导出，例如：「导出课表 高一(1)班」"
                return response
            else:
                return "❌ 导出课表失败，请检查数据是否完整。"

        except Exception as e:
            logger.error(f"导出课表失败: {e}", exc_info=True)
            return f"❌ 导出课表时出现错误：{str(e)}"

    def _build_task(self, data: dict):
        """构建排课任务"""
        from .scheduling import (
            SchedulingTask, ConstraintManager,
            Teacher, Classroom, Course, ClassGroup,
        )

        teachers = {t["id"]: Teacher.from_dict(t) for t in data.get("teachers", [])}
        classrooms = {c["id"]: Classroom.from_dict(c) for c in data.get("classrooms", [])}
        courses = {c["id"]: Course.from_dict(c) for c in data.get("courses", [])}
        classes = {c["id"]: ClassGroup.from_dict(c) for c in data.get("classes", [])}

        constraints = ConstraintManager()
        if "constraints" in data:
            constraints.update_config(data["constraints"])

        return SchedulingTask(
            classes=classes,
            teachers=teachers,
            classrooms=classrooms,
            courses=courses,
            constraints=constraints,
        )

    def _show_data_guide(self) -> str:
        """显示数据上传指南"""
        return """📋 排课系统使用指南

要使用自动排课功能，需要先上传排课数据。

请准备以下信息并上传 Excel 文件：

**1. 班级信息**
| 班级名称 | 年级 | 学生人数 | 班主任 | 固定教室 |
|---------|------|---------|--------|---------|
| 高一(1)班 | 高一 | 45 | 张老师 | 101教室,102教室 |

💡 固定教室列：指定该班级平时上课的教室，排课时会优先使用这些教室。
   多个教室用逗号分隔，留空则由系统自动分配。

**2. 教师信息**
| 教师姓名 | 可教科目 | 每天最大课时 |
|---------|---------|-------------|
| 张老师 | 数学 | 4 |

**3. 课程信息**
| 课程名称 | 学科 | 每周课时 | 是否主课 |
|---------|------|---------|---------|
| 高一数学 | 数学 | 5 | 是 |

**4. 教室信息**
| 教室名称 | 容量 | 设备 |
|---------|------|------|
| 101教室 | 50 | 多媒体 |

💡 也可以直接发送文字格式的数据，例如：
"班级：高一(1)班、高一(2)班
教师：张老师(数学)、李老师(语文)
课程：数学(5课时/周)、语文(5课时/周)"
"""


# 注册技能
skill_registry.register(SchedulingSkill())
