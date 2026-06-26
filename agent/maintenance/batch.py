"""
批量导入导出器

支持 Excel/CSV 格式批量导入历史课表、通讯录，并导出为结构化报告
"""
import os
import json
import csv
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """导入结果"""
    success: bool
    total_rows: int = 0
    imported: int = 0
    skipped: int = 0
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    details: dict = field(default_factory=dict)


class BatchImporter:
    """
    批量导入器

    支持从 Excel/CSV 导入：
    - 课表数据
    - 考试安排
    - 通讯录
    - 通用知识
    """

    def __init__(self, kb):
        """
        初始化批量导入器

        参数:
            kb: 知识库实例
        """
        self.kb = kb

    async def import_from_csv(self, file_path: str,
                              data_type: str = "auto",
                              encoding: str = "utf-8-sig",
                              mapping: dict = None) -> ImportResult:
        """
        从 CSV 导入

        参数:
            file_path: CSV 文件路径
            data_type: 数据类型（auto/schedule/exam/contact/text）
            encoding: 文件编码
            mapping: 字段映射

        返回:
            导入结果
        """
        if not os.path.exists(file_path):
            return ImportResult(success=False, errors=[f"文件不存在: {file_path}"])

        try:
            # 读取 CSV 文件
            with open(file_path, "r", encoding=encoding) as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            if not rows:
                return ImportResult(success=False, errors=["CSV 文件为空"])

            # 自动检测数据类型
            if data_type == "auto":
                data_type = self._detect_data_type(rows[0])

            # 根据数据类型分发
            if data_type == "schedule":
                return await self._import_schedules(rows, mapping)
            elif data_type == "exam":
                return await self._import_exams(rows, mapping)
            elif data_type == "contact":
                return await self._import_contacts(rows, mapping)
            else:
                return await self._import_generic(rows, mapping)

        except Exception as e:
            logger.error(f"导入 CSV 失败: {e}")
            return ImportResult(success=False, errors=[str(e)])

    async def import_from_excel(self, file_path: str,
                                data_type: str = "auto",
                                sheet_name: str = None,
                                mapping: dict = None) -> ImportResult:
        """
        从 Excel 导入

        参数:
            file_path: Excel 文件路径
            data_type: 数据类型
            sheet_name: 工作表名称
            mapping: 字段映射

        返回:
            导入结果
        """
        if not os.path.exists(file_path):
            return ImportResult(success=False, errors=[f"文件不存在: {file_path}"])

        try:
            import pandas as pd

            # 读取 Excel 文件
            df = pd.read_excel(file_path, sheet_name=sheet_name or 0)

            if df.empty:
                return ImportResult(success=False, errors=["Excel 文件为空"])

            # 转换为字典列表
            rows = df.to_dict('records')

            # 自动检测数据类型
            if data_type == "auto":
                data_type = self._detect_data_type(rows[0])

            # 根据数据类型分发
            if data_type == "schedule":
                return await self._import_schedules(rows, mapping)
            elif data_type == "exam":
                return await self._import_exams(rows, mapping)
            elif data_type == "contact":
                return await self._import_contacts(rows, mapping)
            else:
                return await self._import_generic(rows, mapping)

        except ImportError:
            return ImportResult(success=False, errors=["需要安装 pandas 和 openpyxl: pip install pandas openpyxl"])
        except Exception as e:
            logger.error(f"导入 Excel 失败: {e}")
            return ImportResult(success=False, errors=[str(e)])

    def _detect_data_type(self, row: dict) -> str:
        """自动检测数据类型"""
        keys = set(str(k).lower() for k in row.keys())

        # 课表特征
        schedule_keys = {"周一", "周二", "周三", "周四", "周五", "班级", "class", "monday", "tuesday"}
        if keys & schedule_keys:
            return "schedule"

        # 考试特征
        exam_keys = {"考试", "课程", "日期", "时间", "exam", "course", "date"}
        if keys & exam_keys:
            return "exam"

        # 通讯录特征
        contact_keys = {"姓名", "电话", "手机", "邮箱", "name", "phone", "email"}
        if keys & contact_keys:
            return "contact"

        return "text"

    async def _import_schedules(self, rows: list, mapping: dict = None) -> ImportResult:
        """导入课表数据"""
        result = ImportResult(success=True, total_rows=len(rows))

        # 标准化字段映射
        field_map = mapping or {
            "class": ["班级", "class", "班级名称"],
            "monday": ["周一", "monday", "星期一"],
            "tuesday": ["周二", "tuesday", "星期二"],
            "wednesday": ["周三", "wednesday", "星期三"],
            "thursday": ["周四", "thursday", "星期四"],
            "friday": ["周五", "friday", "星期五"],
        }

        schedules = []
        for i, row in enumerate(rows):
            try:
                # 提取班级名称
                class_name = self._get_field_value(row, field_map.get("class", []))
                if not class_name:
                    result.warnings.append(f"第 {i+1} 行：缺少班级名称，跳过")
                    result.skipped += 1
                    continue

                # 构建课表数据
                schedule_data = {"class": class_name, "schedule": {}}

                for day, field_names in field_map.items():
                    if day == "class":
                        continue

                    value = self._get_field_value(row, field_names)
                    if value:
                        # 解析课程（假设格式为"语文,数学,英语,..."或"第1节:语文 第2节:数学"）
                        courses = self._parse_courses(value)
                        if courses:
                            day_name = self._normalize_day(day)
                            schedule_data["schedule"][day_name] = courses

                if schedule_data["schedule"]:
                    schedules.append(schedule_data)
                    result.imported += 1
                else:
                    result.warnings.append(f"第 {i+1} 行：没有有效的课程数据")
                    result.skipped += 1

            except Exception as e:
                result.errors.append(f"第 {i+1} 行: {str(e)}")
                result.skipped += 1

        # 保存到知识库
        if schedules:
            existing = self.kb.get_structured_data("schedules")
            existing.extend(schedules)
            self.kb.save_structured_data("schedules", existing)

            # 添加到知识库索引
            for schedule in schedules:
                text = self._schedule_to_text(schedule)
                await self.kb.add_message(
                    text=text,
                    source_type="file",
                    source_id=f"import_schedule_{schedule['class']}",
                    file_name="批量导入",
                    tags=["schedule", "import"]
                )

        result.details = {"schedules_count": len(schedules)}
        return result

    async def _import_exams(self, rows: list, mapping: dict = None) -> ImportResult:
        """导入考试安排"""
        result = ImportResult(success=True, total_rows=len(rows))

        field_map = mapping or {
            "course": ["课程", "course", "课程名称"],
            "exam_type": ["考试类型", "type", "exam_type"],
            "date": ["日期", "date", "考试日期"],
            "time": ["时间", "time", "考试时间"],
            "classroom": ["教室", "classroom", "考场"],
        }

        exams = []
        for i, row in enumerate(rows):
            try:
                exam_data = {}
                for field, field_names in field_map.items():
                    value = self._get_field_value(row, field_names)
                    if value:
                        exam_data[field] = str(value).strip()

                if "course" in exam_data and "date" in exam_data:
                    exams.append(exam_data)
                    result.imported += 1
                else:
                    result.warnings.append(f"第 {i+1} 行：缺少必要字段（课程/日期）")
                    result.skipped += 1

            except Exception as e:
                result.errors.append(f"第 {i+1} 行: {str(e)}")
                result.skipped += 1

        # 保存到知识库
        if exams:
            existing = self.kb.get_structured_data("exams")
            existing.extend(exams)
            self.kb.save_structured_data("exams", existing)

            # 添加到知识库索引
            for exam in exams:
                text = self._exam_to_text(exam)
                await self.kb.add_message(
                    text=text,
                    source_type="file",
                    source_id=f"import_exam_{exam.get('course', '')}",
                    file_name="批量导入",
                    tags=["exam", "import"]
                )

        result.details = {"exams_count": len(exams)}
        return result

    async def _import_contacts(self, rows: list, mapping: dict = None) -> ImportResult:
        """导入通讯录"""
        result = ImportResult(success=True, total_rows=len(rows))

        field_map = mapping or {
            "name": ["姓名", "name", "名字"],
            "title": ["职务", "title", "职位"],
            "department": ["部门", "department", "科室"],
            "phone": ["电话", "phone", "手机"],
            "email": ["邮箱", "email"],
        }

        contacts = []
        for i, row in enumerate(rows):
            try:
                contact_data = {}
                for field, field_names in field_map.items():
                    value = self._get_field_value(row, field_names)
                    if value:
                        contact_data[field] = str(value).strip()

                if "name" in contact_data:
                    contacts.append(contact_data)
                    result.imported += 1
                else:
                    result.warnings.append(f"第 {i+1} 行：缺少姓名")
                    result.skipped += 1

            except Exception as e:
                result.errors.append(f"第 {i+1} 行: {str(e)}")
                result.skipped += 1

        # 保存到知识库
        if contacts:
            existing = self.kb.get_structured_data("contacts")
            existing.extend(contacts)
            self.kb.save_structured_data("contacts", existing)

            # 添加到知识库索引
            for contact in contacts:
                text = self._contact_to_text(contact)
                await self.kb.add_message(
                    text=text,
                    source_type="file",
                    source_id=f"import_contact_{contact.get('name', '')}",
                    file_name="批量导入",
                    tags=["contact", "import"]
                )

        result.details = {"contacts_count": len(contacts)}
        return result

    async def _import_generic(self, rows: list, mapping: dict = None) -> ImportResult:
        """导入通用文本数据"""
        result = ImportResult(success=True, total_rows=len(rows))

        for i, row in enumerate(rows):
            try:
                # 将每行转换为文本
                text_parts = []
                for key, value in row.items():
                    if value and str(value).strip():
                        text_parts.append(f"{key}: {value}")

                text = "\n".join(text_parts)

                if text.strip():
                    await self.kb.add_message(
                        text=text,
                        source_type="file",
                        source_id=f"import_row_{i}",
                        file_name="批量导入",
                        tags=["import"]
                    )
                    result.imported += 1
                else:
                    result.skipped += 1

            except Exception as e:
                result.errors.append(f"第 {i+1} 行: {str(e)}")
                result.skipped += 1

        return result

    def _get_field_value(self, row: dict, field_names: list) -> str:
        """获取字段值（支持多个字段名）"""
        for name in field_names:
            # 精确匹配
            if name in row and row[name]:
                return str(row[name]).strip()
            # 模糊匹配
            for key in row.keys():
                if name in str(key) and row[key]:
                    return str(row[key]).strip()
        return ""

    def _parse_courses(self, value: str) -> dict:
        """解析课程数据"""
        courses = {}
        parts = str(value).split(",")

        for i, part in enumerate(parts):
            part = part.strip()
            if part:
                period = f"第{i+1}节"
                courses[period] = part

        return courses

    def _normalize_day(self, day: str) -> str:
        """标准化星期名称"""
        day_map = {
            "monday": "周一", "周一": "周一", "星期一": "周一",
            "tuesday": "周二", "周二": "周二", "星期二": "周二",
            "wednesday": "周三", "周三": "周三", "星期三": "周三",
            "thursday": "周四", "周四": "周四", "星期四": "周四",
            "friday": "周五", "周五": "周五", "星期五": "周五",
            "saturday": "周六", "周六": "周六", "星期六": "周六",
            "sunday": "周日", "周日": "周日", "星期日": "周日",
        }
        return day_map.get(day.lower(), day)

    def _schedule_to_text(self, schedule: dict) -> str:
        """将课表转换为文本"""
        lines = [f"【课表】{schedule.get('class', '')}"]

        for day, courses in schedule.get("schedule", {}).items():
            if isinstance(courses, dict):
                courses_str = "、".join([f"{k}:{v}" for k, v in courses.items()])
                lines.append(f"{day}: {courses_str}")
            elif isinstance(courses, list):
                lines.append(f"{day}: {', '.join(courses)}")

        return "\n".join(lines)

    def _exam_to_text(self, exam: dict) -> str:
        """将考试数据转换为文本"""
        parts = []
        if "course" in exam:
            parts.append(f"课程：{exam['course']}")
        if "exam_type" in exam:
            parts.append(f"类型：{exam['exam_type']}")
        if "date" in exam:
            parts.append(f"日期：{exam['date']}")
        if "time" in exam:
            parts.append(f"时间：{exam['time']}")
        if "classroom" in exam:
            parts.append(f"教室：{exam['classroom']}")
        return "，".join(parts)

    def _contact_to_text(self, contact: dict) -> str:
        """将联系人数据转换为文本"""
        parts = []
        if "name" in contact:
            parts.append(f"姓名：{contact['name']}")
        if "title" in contact:
            parts.append(f"职务：{contact['title']}")
        if "department" in contact:
            parts.append(f"部门：{contact['department']}")
        if "phone" in contact:
            parts.append(f"电话：{contact['phone']}")
        if "email" in contact:
            parts.append(f"邮箱：{contact['email']}")
        return "，".join(parts)


class BatchExporter:
    """
    批量导出器

    支持导出为：
    - CSV 格式
    - Excel 格式
    - JSON 格式
    """

    def __init__(self, kb):
        """
        初始化批量导出器

        参数:
            kb: 知识库实例
        """
        self.kb = kb

    def export_to_csv(self, output_path: str,
                      data_type: str = "chunks",
                      include_trace: bool = True) -> int:
        """
        导出为 CSV

        参数:
            output_path: 输出路径
            data_type: 数据类型（chunks/schedules/exams/contacts）
            include_trace: 是否包含溯源信息

        返回:
            导出的记录数
        """
        try:
            if data_type == "schedules":
                return self._export_schedules_csv(output_path)
            elif data_type == "exams":
                return self._export_exams_csv(output_path)
            elif data_type == "contacts":
                return self._export_contacts_csv(output_path)
            else:
                return self._export_chunks_csv(output_path, include_trace)
        except Exception as e:
            logger.error(f"导出 CSV 失败: {e}")
            return 0

    def export_to_excel(self, output_path: str,
                        data_type: str = "chunks",
                        include_trace: bool = True) -> int:
        """
        导出为 Excel

        参数:
            output_path: 输出路径
            data_type: 数据类型
            include_trace: 是否包含溯源信息

        返回:
            导出的记录数
        """
        try:
            import pandas as pd

            # 获取数据
            if data_type == "schedules":
                data = self.kb.get_structured_data("schedules")
            elif data_type == "exams":
                data = self.kb.get_structured_data("exams")
            elif data_type == "contacts":
                data = self.kb.get_structured_data("contacts")
            else:
                data = [asdict(c) for c in self.kb._chunks]

            # 转换为 DataFrame
            df = pd.DataFrame(data)

            # 写入 Excel
            df.to_excel(output_path, index=False, engine='openpyxl')

            logger.info(f"导出 Excel 成功: {output_path}, 记录数: {len(data)}")
            return len(data)

        except ImportError:
            logger.error("需要安装 pandas 和 openpyxl: pip install pandas openpyxl")
            return 0
        except Exception as e:
            logger.error(f"导出 Excel 失败: {e}")
            return 0

    def _export_chunks_csv(self, output_path: str, include_trace: bool) -> int:
        """导出知识分块为 CSV"""
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)

            # 写入表头
            headers = [
                "chunk_id", "text", "category", "source_type", "source_id",
                "file_name", "sender_id", "sender_nick", "sender_dept",
                "conversation_id", "conversation_type", "conversation_name",
                "created_at", "message_time", "expires_at", "is_expired",
                "version", "is_latest", "keywords", "summary"
            ]
            writer.writerow(headers)

            # 写入数据
            for chunk in self.kb._chunks:
                writer.writerow([
                    chunk.chunk_id,
                    chunk.text[:500],
                    chunk.category,
                    chunk.source_type,
                    chunk.source_id,
                    chunk.file_name,
                    chunk.sender_id,
                    chunk.sender_nick,
                    chunk.sender_dept,
                    chunk.conversation_id,
                    chunk.conversation_type,
                    chunk.conversation_name,
                    datetime.fromtimestamp(chunk.timestamp).isoformat() if chunk.timestamp else "",
                    datetime.fromtimestamp(chunk.message_timestamp).isoformat() if chunk.message_timestamp else "",
                    datetime.fromtimestamp(chunk.expires_at).isoformat() if chunk.expires_at > 0 else "",
                    "是" if chunk.is_expired else "否",
                    chunk.version,
                    "是" if chunk.is_latest else "否",
                    ",".join(chunk.keywords),
                    chunk.summary,
                ])

        logger.info(f"导出 CSV 成功: {output_path}, 记录数: {len(self.kb._chunks)}")
        return len(self.kb._chunks)

    def _export_schedules_csv(self, output_path: str) -> int:
        """导出课表为 CSV"""
        schedules = self.kb.get_structured_data("schedules")

        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["班级", "周一", "周二", "周三", "周四", "周五"])

            for schedule in schedules:
                class_name = schedule.get("class", "")
                schedule_data = schedule.get("schedule", {})

                row = [class_name]
                for day in ["周一", "周二", "周三", "周四", "周五"]:
                    day_courses = schedule_data.get(day, {})
                    if isinstance(day_courses, dict):
                        courses = ",".join(day_courses.values())
                    else:
                        courses = str(day_courses)
                    row.append(courses)

                writer.writerow(row)

        logger.info(f"导出课表 CSV 成功: {output_path}, 记录数: {len(schedules)}")
        return len(schedules)

    def _export_exams_csv(self, output_path: str) -> int:
        """导出考试安排为 CSV"""
        exams = self.kb.get_structured_data("exams")

        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["课程", "考试类型", "日期", "时间", "教室"])

            for exam in exams:
                writer.writerow([
                    exam.get("course", ""),
                    exam.get("exam_type", ""),
                    exam.get("date", ""),
                    exam.get("time", ""),
                    exam.get("classroom", ""),
                ])

        logger.info(f"导出考试 CSV 成功: {output_path}, 记录数: {len(exams)}")
        return len(exams)

    def _export_contacts_csv(self, output_path: str) -> int:
        """导出通讯录为 CSV"""
        contacts = self.kb.get_structured_data("contacts")

        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["姓名", "职务", "部门", "电话", "邮箱"])

            for contact in contacts:
                writer.writerow([
                    contact.get("name", ""),
                    contact.get("title", ""),
                    contact.get("department", ""),
                    contact.get("phone", ""),
                    contact.get("email", ""),
                ])

        logger.info(f"导出通讯录 CSV 成功: {output_path}, 记录数: {len(contacts)}")
        return len(contacts)

    def export_report(self, output_path: str,
                      report_type: str = "full") -> str:
        """
        导出报告

        参数:
            output_path: 输出路径
            report_type: 报告类型（full/summary/maintenance）

        返回:
            报告路径
        """
        try:
            report_lines = [
                "=" * 60,
                "  知识库导出报告",
                "=" * 60,
                "",
                f"导出时间: {datetime.now().isoformat()}",
                f"总分块数: {len(self.kb._chunks)}",
                "",
            ]

            # 添加统计信息
            stats = self.kb.get_stats()
            report_lines.append("统计信息:")
            report_lines.append(f"  - 总消息数: {stats.total_messages}")
            report_lines.append(f"  - 索引大小: {stats.index_size_mb:.2f} MB")
            report_lines.append("")

            # 添加分类统计
            report_lines.append("分类统计:")
            for cat, count in stats.categories.items():
                report_lines.append(f"  - {cat}: {count}")
            report_lines.append("")

            # 添加发送者统计
            report_lines.append("Top 发送者:")
            for sender, count in stats.top_senders:
                report_lines.append(f"  - {sender}: {count}")
            report_lines.append("")

            # 写入文件
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines))

            logger.info(f"导出报告成功: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"导出报告失败: {e}")
            return ""
