"""
示例技能 - 展示如何创建新技能

创建新技能只需要：
1. 继承 BaseSkill
2. 实现 can_handle() 和 execute()
3. 在 main.py 或技能加载文件中注册
"""
import re
from .registry import BaseSkill, skill_registry


class ExampleSkill(BaseSkill):
    """示例技能：天气查询"""

    @property
    def name(self) -> str:
        return "天气查询"

    @property
    def description(self) -> str:
        return "查询指定城市的天气信息"

    @property
    def keywords(self) -> list:
        return ["天气", "气温", "温度", "下雨", "下雪"]

    @property
    def priority(self) -> int:
        return 50

    def can_handle(self, text: str) -> float:
        """判断是否能处理天气查询"""
        text_lower = text.lower()

        # 检查关键词
        for keyword in self.keywords:
            if keyword in text_lower:
                # 检查是否有城市名
                city_match = re.search(r'([一-龥]{2,4})(?:的|今天|明天)?天气', text)
                if city_match:
                    return 0.9
                return 0.6

        return 0

    def extract_info(self, text: str) -> dict:
        """提取城市信息"""
        city_match = re.search(r'([一-龥]{2,4})(?:的|今天|明天)?天气', text)
        city = city_match.group(1) if city_match else "未知"

        # 判断查询时间
        time_type = "今天"
        if "明天" in text:
            time_type = "明天"
        elif "后天" in text:
            time_type = "后天"

        return {
            "city": city,
            "time_type": time_type,
        }

    async def execute(self, text: str, context: dict) -> str:
        """执行天气查询"""
        info = self.extract_info(text)
        city = info["city"]
        time_type = info["time_type"]

        # 这里可以调用真实的天气 API
        # 示例返回
        return f"📍 {city}{time_type}天气：\n\n🌤️ 晴朗，气温 22-28°C\n💨 微风\n\n（这是一个示例技能，请接入真实天气 API）"


# 注册技能
skill_registry.register(ExampleSkill())
