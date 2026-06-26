"""
LLM意图解析模块 - 优化版
使用LLM理解用户自然语言输入，解析出结构化意图和参数
"""
import json
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LLMIntentParser:
    """LLM意图解析器 - 优化版"""

    def __init__(self):
        self.client = None
        self.model = None
        self.max_retries = 3  # 最大重试次数
        self.timeout = 30  # 超时时间（秒）
        self._init_client()

    def _init_client(self):
        """初始化LLM客户端"""
        try:
            import config
            from openai import OpenAI
            self.client = OpenAI(
                api_key=config.OPENAI_API_KEY,
                base_url=config.OPENAI_BASE_URL,
                timeout=self.timeout,  # 设置超时
            )
            self.model = config.OPENAI_MODEL
            logger.info(f"LLM意图解析器初始化成功，模型: {self.model}，超时: {self.timeout}秒")
        except Exception as e:
            logger.error(f"LLM意图解析器初始化失败: {e}")
            self.client = None
            self.model = None

    def _get_date_context(self) -> str:
        """获取日期上下文"""
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        return f"今天:{today.strftime('%Y-%m-%d')},昨天:{yesterday.strftime('%Y-%m-%d')}"

    def _call_llm_with_retry(self, system_prompt: str, user_text: str) -> str:
        """
        调用LLM API，带重试机制

        返回: LLM返回的文本，失败返回空字符串
        """
        import re

        # 前置检查：确保client和model可用
        if not self.client or not self.model:
            logger.warning("[LLM调用] 客户端或模型未初始化，跳过调用")
            return ""

        for attempt in range(1, self.max_retries + 1):
            start_time = time.time()

            try:
                logger.info(f"[LLM调用] 第{attempt}次尝试，模型: {self.model}")

                # 构建消息
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ]

                # 调用API
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=300,
                )

                elapsed = time.time() - start_time

                # 检查响应
                if not response.choices:
                    logger.warning(f"[LLM调用] 第{attempt}次尝试，响应为空，耗时: {elapsed:.2f}秒")
                    continue

                content = response.choices[0].message.content
                logger.info(f"[LLM调用] 第{attempt}次尝试，原始返回: {repr(content[:200] if content else 'None')}，耗时: {elapsed:.2f}秒")

                # 前置校验：检查是否为空或全空白
                if not content or not content.strip():
                    logger.warning(f"[LLM调用] 第{attempt}次尝试，返回内容为空，跳过")
                    continue

                # 清理内容
                content = content.strip()

                # 尝试提取JSON
                json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                if json_match:
                    result = json_match.group(0)
                    logger.info(f"[LLM调用] 第{attempt}次尝试，提取到JSON: {result[:100]}...")
                    return result
                else:
                    logger.warning(f"[LLM调用] 第{attempt}次尝试，未找到JSON格式内容")
                    continue

            except Exception as e:
                elapsed = time.time() - start_time
                error_msg = str(e)
                # 检查是否是超时错误
                is_timeout = "timeout" in error_msg.lower() or "timed out" in error_msg.lower()
                logger.error(f"[LLM调用] 第{attempt}次尝试失败，耗时: {elapsed:.2f}秒，超时: {is_timeout}，错误: {error_msg[:100]}")
                continue

        logger.error(f"[LLM调用] 达到最大重试次数{self.max_retries}，放弃调用")
        return ""

    def parse_schedule_query(self, text: str) -> Dict[str, Any]:
        """解析课表查询意图"""
        date_context = self._get_date_context()

        # 极简system prompt
        system_prompt = f"""你是意图解析器。当前日期:{date_context}。

用户说:"{{text}}"
输出纯JSON:{{"intent":"query_schedule","class":"班级或null","date":"日期或null","period":"节次或null","subject":"科目或null","teacher":"教师或null","type":"full|day|period|subject|teacher"}}

规则:日期转换为YYYY-MM-DD格式,节次转为数字格式,无则null。只输出JSON。"""

        result_text = self._call_llm_with_retry(system_prompt, text)

        if not result_text:
            return self._fallback_parse_schedule(text)

        try:
            result = json.loads(result_text)
            logger.info(f"[课表查询] 解析成功: {result}")
            return result
        except Exception as e:
            logger.error(f"[课表查询] JSON解析失败: {e}")
            return self._fallback_parse_schedule(text)

    def parse_schedule_swap(self, text: str) -> Dict[str, Any]:
        """解析调课意图"""
        date_context = self._get_date_context()

        # 极简system prompt
        system_prompt = f"""你是意图解析器。当前日期:{date_context}。

用户说:"{{text}}"
输出纯JSON:{{"intent":"swap_schedule","class":"班级或null","day1":"日期1","period1":"节次1","day2":"日期2","period2":"节次2","course1":"课程1或null","course2":"课程2或null","permanent":true|false|null}}

规则:日期转换为周X格式,节次转为数字格式,无则null。只输出JSON。"""

        result_text = self._call_llm_with_retry(system_prompt, text)

        if not result_text:
            return self._fallback_parse_swap(text)

        try:
            result = json.loads(result_text)
            logger.info(f"[调课] 解析成功: {result}")
            return result
        except Exception as e:
            logger.error(f"[调课] JSON解析失败: {e}")
            return self._fallback_parse_swap(text)

    def parse_inspection_query(self, text: str) -> Dict[str, Any]:
        """解析巡检记录查询意图"""
        date_context = self._get_date_context()

        # 极简system prompt
        system_prompt = f"""你是意图解析器。当前日期:{date_context}。

用户说:"{{text}}"
输出纯JSON:{{"intent":"query_inspection","point":"点位名或null","date":"日期或null","date_rel":"相对日期或null","photos":true|false,"type":"records|photos|stats"}}

规则:昨天转换为具体日期,今天转换为具体日期,有照片需求设photos:true。只输出JSON。"""

        result_text = self._call_llm_with_retry(system_prompt, text)

        if not result_text:
            return self._fallback_parse_inspection(text)

        try:
            result = json.loads(result_text)
            logger.info(f"[巡检查询] 解析成功: {result}")
            return result
        except Exception as e:
            logger.error(f"[巡检查询] JSON解析失败: {e}")
            return self._fallback_parse_inspection(text)

    # ==================== 回退解析器 ====================

    def _fallback_parse_schedule(self, text: str) -> Dict[str, Any]:
        """回退的规则解析（课表查询）"""
        import re
        result = {
            "intent": "query_schedule",
            "class": None,
            "date": None,
            "period": None,
            "subject": None,
            "teacher": None,
            "type": "full",
            "confidence": 0.5,
        }
        # 提取班级
        class_match = re.search(r'([高初][一二三])\s*[（(](\d+)[）)]\s*班', text)
        if class_match:
            result["class"] = f"{class_match.group(1)}({class_match.group(2)})班"
        # 提取日期
        day_match = re.search(r'(周[一二三四五六日]|星期[一二三四五六日])', text)
        if day_match:
            result["date"] = day_match.group(1)
            result["type"] = "day"
        # 提取节次
        period_match = re.search(r'第?(\d+)节', text)
        if period_match:
            result["period"] = f"第{period_match.group(1)}节"
            result["type"] = "period"
        # 提取科目
        subjects = ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "政治", "体育", "音乐", "美术"]
        for subj in subjects:
            if subj in text:
                result["subject"] = subj
                result["type"] = "subject"
                break
        # 提取教师
        teacher_match = re.search(r'([一-龥]+)(?:老师|教授|教师)', text)
        if teacher_match:
            result["teacher"] = teacher_match.group(1) + "老师"
            result["type"] = "teacher"
        return result

    def _fallback_parse_swap(self, text: str) -> Dict[str, Any]:
        """回退的规则解析（调课）"""
        import re
        result = {
            "intent": "swap_schedule",
            "class": None,
            "day1": None,
            "period1": None,
            "day2": None,
            "period2": None,
            "course1": None,
            "course2": None,
            "permanent": None,
            "confidence": 0.5,
        }
        # 提取班级
        class_match = re.search(r'([高初][一二三])\s*[（(](\d+)[）)]\s*班', text)
        if class_match:
            result["class"] = f"{class_match.group(1)}({class_match.group(2)})班"
        # 提取日期
        days = re.findall(r'(周[一二三四五六日]|星期[一二三四五六日])', text)
        if len(days) >= 2:
            result["day1"] = days[0]
            result["day2"] = days[1]
        # 提取节次
        periods = re.findall(r'第?(\d+)节', text)
        if len(periods) >= 2:
            result["period1"] = f"第{periods[0]}节"
            result["period2"] = f"第{periods[1]}节"
        # 提取课程
        subjects = ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "政治", "体育", "音乐", "美术"]
        found_subjects = [s for s in subjects if s in text]
        if len(found_subjects) >= 2:
            result["course1"] = found_subjects[0]
            result["course2"] = found_subjects[1]
        # 提取调课类型
        if "永久" in text:
            result["permanent"] = True
        elif "临时" in text:
            result["permanent"] = False
        return result

    def _fallback_parse_inspection(self, text: str) -> Dict[str, Any]:
        """回退的规则解析（巡检查询）"""
        import re
        result = {
            "intent": "query_inspection",
            "point": None,
            "date": None,
            "date_rel": None,
            "photos": False,
            "type": "records",
            "confidence": 0.5,
        }
        # 检查是否想看照片
        if "照片" in text or "图片" in text or "拍照" in text:
            result["photos"] = True
            result["type"] = "photos"
        # 检查是否是统计
        if "统计" in text or "汇总" in text:
            result["type"] = "stats"
        # 提取日期
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
        if date_match:
            result["date"] = date_match.group(1)
        elif "昨天" in text:
            result["date_rel"] = "昨天"
        elif "今天" in text:
            result["date_rel"] = "今天"
        elif "本周" in text or "这周" in text:
            result["date_rel"] = "本周"
        # 提取点位名称
        point_keywords = ["操场", "教学楼", "宿舍", "食堂", "消防", "看台", "走廊"]
        for kw in point_keywords:
            if kw in text:
                point_match = re.search(rf'([一-龥]*{kw}[一-龥]*)', text)
                if point_match:
                    result["point"] = point_match.group(1)
                break
        return result


# 全局实例
_parser = None


def get_llm_intent_parser() -> LLMIntentParser:
    """获取LLM意图解析器单例"""
    global _parser
    if _parser is None:
        _parser = LLMIntentParser()
    return _parser
