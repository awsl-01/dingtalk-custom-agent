"""
知识库核心模块 V2 - 全面优化版
改进：检索质量、分块策略、管理功能、缓存优化
"""
from __future__ import annotations
import os
import json
import hashlib
import logging
import time
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from collections import Counter

import numpy as np

import config

logger = logging.getLogger(__name__)

# 导入主动智能模块
try:
    from agent.proactive.notifier import ChangeNotifier, get_notifier
    from agent.proactive.reminder import PeriodicReminder, get_reminder
    from agent.proactive.feedback import FeedbackTracker, get_feedback_tracker
    PROACTIVE_ENABLED = True
except ImportError:
    PROACTIVE_ENABLED = False
    logger.warning("主动智能模块导入失败，相关功能将不可用")

# 导入检索增强模块
try:
    from agent.search.explainer import SearchExplainer, SearchExplanation, get_search_explainer
    from agent.search.suggester import SearchSuggestion, get_search_suggester
    from agent.search.optimizer import AdaptiveWeightOptimizer, get_weight_optimizer
    SEARCH_ENHANCEMENT_ENABLED = True
except ImportError:
    SEARCH_ENHANCEMENT_ENABLED = False
    logger.warning("检索增强模块导入失败，相关功能将不可用")

# 导入运维模块
try:
    from agent.maintenance.snapshot import KnowledgeSnapshot, get_snapshot_manager
    from agent.maintenance.batch import BatchImporter, BatchExporter
    MAINTENANCE_ENABLED = True
except ImportError:
    MAINTENANCE_ENABLED = False
    logger.warning("运维模块导入失败，相关功能将不可用")

# 导入多模态模块
try:
    from agent.multimodal.ocr import OCREngine, get_ocr_engine
    from agent.multimodal.parser import DeepFileParser, get_file_parser
    MULTIMODAL_ENABLED = True
except ImportError:
    MULTIMODAL_ENABLED = False
    logger.warning("多模态模块导入失败，相关功能将不可用")

# 导入反馈循环模块
try:
    from agent.proactive.feedback_loop import FeedbackCollector, get_feedback_collector
    FEEDBACK_LOOP_ENABLED = True
except ImportError:
    FEEDBACK_LOOP_ENABLED = False
    logger.warning("反馈循环模块导入失败，相关功能将不可用")

# 导入音视频转写模块
try:
    from agent.multimodal.transcriber import MediaTranscriber, get_media_transcriber
    TRANSCRIBER_ENABLED = True
except ImportError:
    TRANSCRIBER_ENABLED = False
    logger.warning("音视频转写模块导入失败，相关功能将不可用")

# 导入 A/B 测试模块
try:
    from agent.search.ab_testing import ABTestManager, get_ab_manager
    AB_TESTING_ENABLED = True
except ImportError:
    AB_TESTING_ENABLED = False
    logger.warning("A/B 测试模块导入失败，相关功能将不可用")

# 导入 SLA 监控模块
try:
    from agent.maintenance.monitor import SLAMonitor, get_sla_monitor
    SLA_MONITOR_ENABLED = True
except ImportError:
    SLA_MONITOR_ENABLED = False
    logger.warning("SLA 监控模块导入失败，相关功能将不可用")

# ========== 配置参数 ==========
CHUNK_SIZE = 400  # 优化：减小分块大小，提升检索精度
CHUNK_OVERLAP = 80  # 增加重叠，保持上下文连贯
TOP_K = 5
SIMILARITY_THRESHOLD = 0.25  # 优化：降低阈值，提高召回率
EMBEDDING_CACHE_SIZE = 2000  # 增大缓存，提升查询速度
INDEX_PAGE_SIZE = 100  # 索引分页大小

# 存储容量配置
MAX_CHUNKS = 100000  # 最大分块数量（默认10万）
MAX_MEMORY_MB = 512  # 最大内存占用（MB）
MAX_FILE_SIZE_MB = 50  # 单文件最大大小（MB）
AUTO_CLEANUP_DAYS = 365  # 自动清理天数（0表示不清理）

# ========== 去重与版本控制配置 ==========
DEDUP_ENABLED = True  # 是否启用去重
VERSION_CONTROL_ENABLED = True  # 是否启用版本控制
# 版本控制策略：overwrite（覆盖旧版本）/ keep（保留历史）/ smart（智能判断）
VERSION_STRATEGY = "smart"
# 需要版本控制的类别（课表、考试等经常更新的内容）
VERSION_CONTROLLED_CATEGORIES = {"schedule", "exam"}

# ========== 时效管理配置 ==========
EXPIRY_ENABLED = True  # 是否启用时效管理
# 各类别的默认过期时间（天数，0表示永不过期）
EXPIRY_DAYS = {
    "exam": 30,       # 考试安排：30天后过期
    "notice": 90,     # 通知：90天后过期
    "homework": 7,    # 作业：7天后过期
    "schedule": 0,    # 课表：永不过期（通过版本控制更新）
    "contact": 0,     # 通讯录：永不过期
    "teaching": 365,  # 教学资料：365天后过期
    "student": 0,     # 学生信息：永不过期
    "other": 180,     # 其他：180天后过期
}
# 自动过期检查间隔（小时）
EXPIRY_CHECK_INTERVAL_HOURS = 24
# 过期后是否自动删除（False则标记为过期但保留）
EXPIRY_AUTO_DELETE = False

# ========== 使用统计与维护提醒配置 ==========
# 启用使用统计
USAGE_STATS_ENABLED = True
# 低频知识阈值（天数）：超过此天数未被检索的知识块视为低频
LOW_FREQUENCY_DAYS = 30
# 无效知识阈值（天数）：超过此天数未被检索的知识块视为无效
USELESS_DAYS = 90
# 最小访问次数：低于此次数且超过低频阈值的知识块需要审核
MIN_ACCESS_COUNT = 3
# 维护提醒检查间隔（小时）
MAINTENANCE_CHECK_INTERVAL_HOURS = 168  # 7天

# ========== 消息过滤配置 ==========
# 不存档的消息（精确匹配）
SKIP_EXACT = {
    # 简单确认/取消
    '确认', '确定', '好的', '可以', '没问题', '同意', 'ok', 'yes',
    '取消', '不要了', '算了', '放弃',
    # 简单感谢
    '谢谢', '感谢', 'thank', 'thanks', '3q',
    # 表情/无意义
    '哈哈哈', '呵呵呵', '嘻嘻', '哈哈', '呵呵', '嘿嘿', '666',
    '👍', '👌', '😊', '🙏', '😄', '😁', '🤣', '😂',
    # 指令类（简短的触发词，不含实质知识）
    '开始排课', '开始', '导出', '优化', '查看', '发送',
    '课表查询', '查看课表', '排课模板', '查询知识库', '知识库统计',
}

# 包含这些关键词的消息需要进一步判断（仅作为辅助，不是直接保留的条件）
# 这些关键词表示消息可能与教学相关，但仍需检查是否是问题/指令
EDUCATION_KEYWORDS = [
    # PPT/课件相关（用户上传的教学内容）
    'ppt', 'PPT', '幻灯片', '演示文稿', 'slides',
    # 教学资料关键词（真正代表知识内容）
    '课件', '教案', '说课', '教学设计', '教学计划', '教学进度',
    # 学科名称（需要配合陈述句形式才保留）
    '语文', '数学', '英语', '物理', '化学', '生物', '历史', '地理', '政治',
    '音乐', '美术', '体育', '科学', '信息技术',
]

# 必须包含这些关键词才会保留（知识性内容的必要条件）
# 只有同时满足：包含这些关键词 + 长度足够 + 不是问题/指令，才会存入
KNOWLEDGE_KEYWORDS = [
    # 课表结构化数据
    '第1节', '第2节', '第3节', '第4节', '第5节', '第6节', '第7节', '第8节',
    '上午', '下午', '周一', '周二', '周三', '周四', '周五',
    # 通知/公告类（陈述句形式）
    '通知：', '公告：', '通知如下', '特此通知', '请注意',
    # 考试/成绩（陈述句形式，如"考试安排"、"成绩公布"）
    '考试安排', '考试时间', '成绩公布', '成绩查询',
    # 学生信息（陈述句形式）
    '学生名单', '花名册', '通讯录', '班级人数',
    # 教学内容（陈述句形式）
    '教学目标', '教学重点', '教学难点', '课程标准',
    # 文件上传提示（用户主动分享的知识）
    '已上传', '已分享', '文件已保存',
]

# 直接跳过这些模式的消息（问题类、指令类、对话类）
SKIP_PATTERNS = [
    # === 问题类（最重要：问题不是知识，不应存入）===
    r'.*\?$',                    # 以?结尾
    r'.*？$',                    # 以？结尾
    r'.*吗[？?]?$',              # 以"吗"结尾（疑问语气）
    r'.*呢[？?]?$',              # 以"呢"结尾（疑问语气）
    r'^什么.*',                  # "什么课"、"什么时候"
    r'^怎么.*',                  # "怎么查询"、"怎么做"
    r'^为什么.*',
    r'^哪些.*',
    r'^如何.*',
    r'^是否.*',
    r'^能否.*',
    r'^有没有.*',
    r'^可以.*吗',                # "可以XXX吗"
    r'^是.*还是',                # "是A还是B"
    r'.*是什么',                 # "XXX是什么"
    r'.*怎么样',                 # "XXX怎么样"
    r'.*好不好',                 # "XXX好不好"
    r'.*行不行',                 # "XXX行不行"
    r'.*对不对',                 # "XXX对不对"

    # === 指令/请求类（用户让机器人做事，不是提供知识）===
    r'^帮我.*',
    r'^请(帮我|给我|发送|生成|制作|查|找|看一下|查一下|找一下).*',
    r'^开始.*',
    r'^查看.*',
    r'^导出.*',
    r'^下载.*',
    r'^发送.*',
    r'^查询.*',
    r'^搜索.*',
    r'^搜一下.*',
    r'^找一下.*',
    r'^查一下.*',
    r'^看一下.*',
    r'^告诉.*',
    r'^说一下.*',
    r'^介绍一下.*',
    r'^解释一下.*',

    # === 调课/换课指令 ===
    r'.*换课.*',
    r'.*调课.*',
    r'.*调换.*',

    # === 确认/回复类 ===
    r'^确认.*',
    r'^好的.*',
    r'^可以.*',
    r'^没问题.*',
    r'^收到.*',
    r'^了解.*',
    r'^明白.*',
    r'^知道了.*',

    # === 对话/闲聊类 ===
    r'^你好.*',
    r'^在吗.*',
    r'^在不在.*',
    r'^有人吗.*',
    r'^谢谢.*',
    r'^感谢.*',
    r'^辛苦了.*',
    r'^麻烦了.*',
    r'^抱歉.*',
    r'^对不起.*',
    r'^不好意思.*',

    # === 太短的消息（不含实质知识）===
    r'^.{1,15}$',                # 15个字符以内的短消息（大概率不是知识）

    # === 包含疑问词的消息（即使较长，也是问题）===
    r'.*什么时候.*',
    r'.*在哪里.*',
    r'.*在哪.*',
    r'.*多少.*',
    r'.*几个.*',
    r'.*谁是.*',
    r'.*是谁.*',
]


def should_skip_message(text: str) -> bool:
    """
    判断消息是否应该跳过存档（关键词匹配版本，用于快速初筛）

    过滤逻辑优先级：
    1. 空消息 → 跳过
    2. 精确匹配 SKIP_EXACT → 跳过
    3. 匹配指令/问题模式 → 跳过（优先过滤，避免指令类消息被保留）
    4. 包含 KNOWLEDGE_KEYWORDS → 不跳过
    5. 包含 EDUCATION_KEYWORDS + 不是问题/指令 → 不跳过
    6. 太短（≤15字符）→ 跳过
    7. 其他 → 跳过（宁可漏存，不要存垃圾）

    参数:
        text: 消息文本

    返回:
        True 表示应该跳过
    """
    if not text or not text.strip():
        return True

    text = text.strip()

    # 精确匹配跳过列表（最高优先级）
    if text in SKIP_EXACT:
        return True

    # 检查指令词（优先于 KNOWLEDGE_KEYWORDS 检查）
    instruction_words = ['帮我', '请帮', '请给', '查一下', '找一下', '搜一下', '看一下',
                         '请查看', '请检查', '请确认', '请回复', '请告诉我']
    has_instruction = any(word in text for word in instruction_words)

    # 检查疑问词
    question_words = ['什么', '怎么', '为什么', '哪些', '如何', '是否', '能否',
                      '什么时候', '在哪里', '在哪', '多少', '几个', '谁', '吗', '呢',
                      '是谁', '是什么', '怎么样', '好不好', '行不行', '对不对',
                      '难不难', '会不会', '能不能', '有没有', '是不是']
    has_question = any(word in text for word in question_words)

    # 如果是指令或问题，直接跳过（即使包含关键词）
    if has_instruction or has_question:
        return True

    # 包含 KNOWLEDGE_KEYWORDS → 不跳过
    for keyword in KNOWLEDGE_KEYWORDS:
        if keyword in text:
            return False

    # 包含 EDUCATION_KEYWORDS 的消息，需要进一步判断
    has_education_keyword = any(kw.lower() in text.lower() for kw in EDUCATION_KEYWORDS)
    if has_education_keyword:
        # 包含教育关键词且不是问题/指令，可以保留
        return False

    # 匹配跳过模式（对话类）
    import re
    for pattern in SKIP_PATTERNS:
        if re.match(pattern, text):
            return True

    # 太短的消息（15个字符以内，大概率不是知识）
    if len(text) <= 15:
        return True

    # 默认跳过（宁可漏存，不要存垃圾到知识库）
    return True


async def should_skip_message_with_llm(text: str, keyword_result: bool = None) -> bool:
    """
    使用 LLM 判断消息是否应该跳过存档（更准确，但有 API 调用成本）

    参数:
        text: 消息文本
        keyword_result: 关键词匹配的结果（可选，用于验证）

    返回:
        True 表示应该跳过
    """
    if not text or not text.strip():
        return True

    text = text.strip()

    # 如果文本很短，直接返回关键词匹配结果
    if len(text) < 10 and keyword_result is not None:
        return keyword_result

    try:
        from agent.llm_utils import call_llm_json

        # 构建过滤提示
        system_prompt = """你是一个消息过滤助手，负责判断学校消息是否包含值得存入知识库的信息。

判断标准：
1. 是否包含事实性信息（时间、地点、人物、事件、数据）
2. 是否是可复用的知识（不是一次性对话、不是简单的确认/取消）
3. 是否是用户主动分享的信息（不是提问、不是指令、不是闲聊）
4. 是否有明确的知识价值（如课表、考试安排、联系方式、通知等）

需要保留的消息类型：
- 事实性信息（如"下周一期中考试"、"张教授的电话是138xxxx"）
- 通知公告（如"明天放假通知"、"家长会安排"）
- 课表安排（如"计算机2301班周一上午有数学课"）
- 联系方式（如"李老师的办公室在A栋301"）
- 教学资料（如"这是第三章的教案"）

应该跳过的消息类型：
- 简单确认（如"好的"、"确认"、"收到"）
- 简单感谢（如"谢谢"、"辛苦了"）
- 闲聊对话（如"你好"、"在吗"）
- 提问指令（如"帮我查一下"、"张教授的课表是什么"）
- 太短无意义（如"666"、"👍"）

请只返回 JSON 格式：{"should_skip": true/false, "reason": "原因说明", "confidence": 0.0-1.0}"""

        prompt = f"""请判断以下消息是否应该存入知识库：

消息：{text}

请返回 JSON 格式的判断结果。"""

        result = await call_llm_json(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,  # 低温度，更确定
            max_tokens=150,
        )

        if result and "should_skip" in result:
            llm_should_skip = result["should_skip"]
            confidence = result.get("confidence", 0.5)

            # 如果置信度高，使用 LLM 结果
            if confidence >= 0.7:
                logger.debug(f"LLM 过滤: {'跳过' if llm_should_skip else '保留'} (置信度: {confidence})")
                return llm_should_skip
            # 如果置信度低，使用关键词匹配结果
            elif keyword_result is not None:
                logger.debug(f"LLM 置信度低，使用关键词结果: {'跳过' if keyword_result else '保留'}")
                return keyword_result

        # 如果 LLM 调用失败或返回无效结果，返回关键词匹配结果
        return keyword_result if keyword_result is not None else True

    except Exception as e:
        logger.warning(f"LLM 过滤失败，使用关键词匹配: {e}")
        return keyword_result if keyword_result is not None else True


async def smart_should_skip(text: str) -> bool:
    """
    智能过滤：结合关键词匹配和 LLM

    参数:
        text: 消息文本

    返回:
        True 表示应该跳过
    """
    # 第一步：关键词快速初筛
    keyword_result = should_skip_message(text)

    # 检查是否启用 LLM 过滤
    if not config.LLM_FILTERING_ENABLED:
        return keyword_result

    # 第二步：对于边界情况，使用 LLM 判断
    # 边界情况：文本较长、包含教育关键词、或包含疑问词但可能是有价值的信息
    if len(text) > 15 and not keyword_result:
        # 文本较长且关键词匹配认为应该保留，使用 LLM 确认
        return await should_skip_message_with_llm(text, keyword_result)

    # 对于明确的跳过或保留，直接返回结果
    return keyword_result


# ========== 文本清洗 ==========
def clean_text(text: str) -> str:
    """
    轻量级文本清洗，提升检索质量

    参数:
        text: 原始文本

    返回:
        清洗后的文本
    """
    if not text:
        return ""

    import re

    # 1. 移除控制字符（保留换行 \n 和制表符 \t）
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # 2. 移除零宽字符
    text = re.sub(r'[​‌‍﻿­]', '', text)

    # 3. 标准化标点：全角 → 半角
    punctuation_map = {
        '，': ',', '。': '.', '！': '!', '？': '?',
        '：': ':', '；': ';', '"': '"', '"': '"',
        ''': "'", ''': "'", '（': '(', '）': ')',
        '【': '[', '】': ']', '《': '<', '》': '>',
        '、': ',', '…': '...', '—': '-', '～': '~',
    }
    for full, half in punctuation_map.items():
        text = text.replace(full, half)

    # 4. 合并多个空格为一个
    text = re.sub(r' {2,}', ' ', text)

    # 5. 合并多个换行为最多两个
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 6. 移除行尾空白
    text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)

    # 7. 移除首尾空白
    text = text.strip()

    return text


def clean_for_indexing(text: str) -> str:
    """
    为索引优化的深度清洗（用于生成 Embedding 和关键词提取）

    参数:
        text: 原始文本

    返回:
        深度清洗后的文本
    """
    if not text:
        return ""

    import re

    # 先进行基础清洗
    text = clean_text(text)

    # 1. 移除常见无意义内容
    noise_patterns = [
        # 页眉页脚
        r'^第\s*\d+\s*页.*$', r'^\d+\s*/\s*\d+\s*$',
        # 页码
        r'^[-—]\s*\d+\s*[-—]$', r'^\[\s*\d+\s*\]$',
        # 版权声明
        r'版权所有.*$', r'Copyright.*$', r'©.*$',
        # 免责声明
        r'免责声明.*$', r'声明：.*$',
        # 水印文字
        r'^[A-Z0-9]{8,}$',
    ]
    for pattern in noise_patterns:
        text = re.sub(pattern, '', text, flags=re.MULTILINE | re.IGNORECASE)

    # 2. 移除多余空白行（保留最多一个空行）
    text = re.sub(r'\n\s*\n', '\n\n', text)

    # 3. 移除纯标点行
    text = re.sub(r'^[.,;:!?\-—=*_~`\'\"]+$', '', text, flags=re.MULTILINE)

    # 4. 清理首尾
    text = text.strip()

    return text


# ========== 内容分类 ==========
# 分类关键词配置
CATEGORY_KEYWORDS = {
    "schedule": {
        "name": "课表",
        "keywords": ["课表", "课程表", "课程安排", "上课时间", "教室", "节次", "上午", "下午", "第1节", "第2节", "第3节", "第4节", "第5节", "第6节", "第7节", "第8节", "周一", "周二", "周三", "周四", "周五", "调课", "换课"],
        "patterns": [r'周[一二三四五].*第\d+节', r'课程.*安排', r'上课.*时间']
    },
    "exam": {
        "name": "考试",
        "keywords": ["考试", "测验", "期中", "期末", "月考", "模拟考", "成绩", "分数", "及格", "优秀", "不及格", "补考", "重考"],
        "patterns": [r'考试.*时间', r'期[中末]考试', r'成绩.*公布']
    },
    "contact": {
        "name": "通讯录",
        "keywords": ["电话", "手机", "联系方式", "邮箱", "微信", "QQ", "办公室", "地址", "联系人", "负责人", "班主任", "老师电话"],
        "patterns": [r'联系.*方式', r'电话.*\d{11}', r'手机.*\d{11}']
    },
    "homework": {
        "name": "作业",
        "keywords": ["作业", "练习", "习题", "试卷", "练习册", "课后题", "布置作业", "交作业", "批改"],
        "patterns": [r'作业.*布置', r'课后.*练习']
    },
    "notice": {
        "name": "通知",
        "keywords": ["通知", "公告", "告家长书", "放假", "开学", "返校", "家长会", "活动", "比赛", "报名"],
        "patterns": [r'关于.*通知', r'放假.*通知', r'家长会']
    },
    "teaching": {
        "name": "教学",
        "keywords": ["教案", "课件", "PPT", "教学计划", "教学进度", "备课", "说课", "公开课", "教研"],
        "patterns": [r'教学.*计划', r'教案.*设计']
    },
    "student": {
        "name": "学生",
        "keywords": ["学生", "班级", "名单", "学号", "考勤", "请假", "迟到", "早退", "纪律"],
        "patterns": [r'学生.*名单', r'班级.*人数']
    }
}


def classify_text(text: str) -> str:
    """
    自动分类文本内容（关键词匹配版本，用于快速预分类）

    参数:
        text: 文本内容

    返回:
        分类标签：schedule/exam/contact/homework/notice/teaching/student/other
    """
    if not text:
        return "other"

    text_lower = text.lower()
    scores = {}

    for category, config in CATEGORY_KEYWORDS.items():
        score = 0
        # 关键词匹配
        for keyword in config["keywords"]:
            if keyword in text_lower:
                score += 1

        # 正则匹配（权重更高）
        import re
        for pattern in config.get("patterns", []):
            if re.search(pattern, text_lower):
                score += 2

        if score > 0:
            scores[category] = score

    if not scores:
        return "other"

    # 返回得分最高的分类
    return max(scores, key=scores.get)


async def classify_text_with_llm(text: str, keyword_result: str = None) -> str:
    """
    使用 LLM 分类文本内容（更准确，但有 API 调用成本）

    参数:
        text: 文本内容
        keyword_result: 关键词匹配的结果（可选，用于验证）

    返回:
        分类标签：schedule/exam/contact/homework/notice/teaching/student/other
    """
    if not text:
        return "other"

    # 如果文本很短，直接返回关键词匹配结果
    if len(text) < 10 and keyword_result:
        return keyword_result

    try:
        from agent.llm_utils import call_llm_json

        # 构建分类提示
        system_prompt = """你是一个文本分类助手，负责将学校相关消息分类到正确的类别。

可选类别：
- schedule: 课表、课程安排、上课时间、调课、换课
- exam: 考试、测验、成绩、分数
- contact: 通讯录、联系方式、电话、邮箱
- homework: 作业、练习、习题
- notice: 通知、公告、放假、活动
- teaching: 教学、教案、课件、PPT
- student: 学生、班级、名单、考勤
- other: 其他不属于以上类别的内容

请只返回 JSON 格式：{"category": "类别名称", "confidence": 0.0-1.0}"""

        prompt = f"""请分析以下消息的内容，判断它属于哪个类别：

消息：{text}

请返回 JSON 格式的分类结果。"""

        result = await call_llm_json(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,  # 低温度，更确定
            max_tokens=100,
        )

        if result and "category" in result:
            llm_category = result["category"]
            confidence = result.get("confidence", 0.5)

            # 验证分类结果
            valid_categories = ["schedule", "exam", "contact", "homework",
                              "notice", "teaching", "student", "other"]
            if llm_category in valid_categories:
                # 如果置信度高，或者与关键词匹配结果一致，使用 LLM 结果
                if confidence >= 0.7 or llm_category == keyword_result:
                    logger.debug(f"LLM 分类: {llm_category} (置信度: {confidence})")
                    return llm_category
                # 如果置信度低且与关键词结果不一致，使用关键词结果
                elif keyword_result and keyword_result != "other":
                    logger.debug(f"LLM 置信度低，使用关键词结果: {keyword_result}")
                    return keyword_result

        # 如果 LLM 调用失败或返回无效结果，返回关键词匹配结果
        return keyword_result or "other"

    except Exception as e:
        logger.warning(f"LLM 分类失败，使用关键词匹配: {e}")
        return keyword_result or "other"


async def smart_classify(text: str) -> str:
    """
    智能分类：结合关键词匹配和 LLM

    参数:
        text: 文本内容

    返回:
        分类标签
    """
    # 第一步：关键词快速预分类
    keyword_result = classify_text(text)

    # 检查是否启用 LLM 分类
    if not config.LLM_CLASSIFICATION_ENABLED:
        return keyword_result

    # 第二步：对于边界情况，使用 LLM 确认
    # 边界情况：关键词匹配分数低、或匹配到多个类别
    if keyword_result == "other" or len(text) > 50:
        # 文本较长或关键词匹配不明确时，使用 LLM
        return await classify_text_with_llm(text, keyword_result)

    # 对于明确的关键词匹配，直接返回结果
    return keyword_result


def get_category_name(category: str) -> str:
    """获取分类的中文名称"""
    if category in CATEGORY_KEYWORDS:
        return CATEGORY_KEYWORDS[category]["name"]
    return "其他"


def compute_content_hash(text: str) -> str:
    """
    计算内容哈希（用于去重）

    参数:
        text: 文本内容

    返回:
        内容的 MD5 哈希值
    """
    import hashlib
    # 清洗文本后计算哈希，忽略空白字符差异
    cleaned = re.sub(r'\s+', '', text.strip())
    return hashlib.md5(cleaned.encode('utf-8')).hexdigest()


def extract_entity_key(text: str, category: str) -> str:
    """
    提取实体键（用于版本控制）

    对于课表：提取班级名称
    对于考试：提取考试名称
    对于其他：返回空字符串

    参数:
        text: 文本内容
        category: 内容类别

    返回:
        实体键（如班级名称）
    """
    if not text or not category:
        return ""

    text_lower = text.lower()

    if category == "schedule":
        # 提取班级名称，如"计算机2301"、"三年级2班"
        patterns = [
            r'([一-龥]+\d{4})',  # 计算机2301
            r'([一-龥]+\d+班)',   # 三年级2班
            r'([一-龥]+\d+年级\d+班)',  # 三年级2班
            r'([一-龥]+\d+级)',   # 三年级
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

    elif category == "exam":
        # 提取考试名称，如"三年级数学期中考试"
        patterns = [
            r'([一-龥]+\d*[一-龥]*考试)',  # 三年级数学期中考试
            r'([一-龥]+\d*[一-龥]*测验)',  # 单元测验
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

    return ""


def extract_expiry_date(text: str, category: str) -> Optional[float]:
    """
    从文本中提取过期时间

    对于考试：提取考试日期，考试结束后过期
    对于作业：提取交作业日期
    对于通知：提取截止日期

    参数:
        text: 文本内容
        category: 内容类别

    返回:
        过期时间戳（如果提取到），否则返回 None
    """
    if not text or not category:
        return None

    text_lower = text.lower()

    # 日期模式：2026年6月1日、2026-06-01、6月1日、6.1
    date_patterns = [
        r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})[日号]?',  # 2026年6月1日
        r'(\d{1,2})[月\-/](\d{1,2})[日号]?',  # 6月1日
    ]

    dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                if len(match) == 3:
                    year, month, day = int(match[0]), int(match[1]), int(match[2])
                else:
                    year = datetime.now().year
                    month, day = int(match[0]), int(match[1])

                # 如果月份已过，可能是明年
                now = datetime.now()
                if month < now.month and year == now.year:
                    year += 1

                date = datetime(year, month, day)
                dates.append(date)
            except (ValueError, IndexError):
                continue

    if not dates:
        return None

    if category == "exam":
        # 考试：使用最后一个日期（通常是考试结束日期），考试结束后1天过期
        exam_date = max(dates)
        expiry_date = exam_date + timedelta(days=1)
        return expiry_date.timestamp()

    elif category == "homework":
        # 作业：使用最后一个日期（通常是交作业日期）
        homework_date = max(dates)
        return homework_date.timestamp()

    elif category == "notice":
        # 通知：使用最后一个日期（通常是截止日期）
        notice_date = max(dates)
        return notice_date.timestamp()

    return None


def get_default_expiry(category: str, timestamp: float) -> float:
    """
    获取默认过期时间

    参数:
        category: 内容类别
        timestamp: 创建时间戳

    返回:
        过期时间戳
    """
    if not EXPIRY_ENABLED:
        return 0.0

    days = EXPIRY_DAYS.get(category, EXPIRY_DAYS.get("other", 180))
    if days <= 0:
        return 0.0  # 永不过期

    return timestamp + days * 24 * 3600


# ========== 数据结构 ==========
@dataclass
class DocumentChunk:
    """文档分块"""
    chunk_id: str
    text: str
    source_type: str
    source_id: str
    sender_id: str = ""
    sender_nick: str = ""
    corp_id: str = ""
    timestamp: float = 0.0
    conversation_id: str = ""
    message_type: str = ""
    file_name: str = ""
    tags: list = field(default_factory=list)
    # V2 新增字段
    keywords: list = field(default_factory=list)  # 提取的关键词
    summary: str = ""  # 分块摘要
    # V2.1 新效期管理字段
    category: str = ""  # 内容类别：schedule/exam/contact/homework/notice/other
    # V2.2 新增字段（去重与版本控制）
    content_hash: str = ""  # 内容哈希（用于去重）
    version: int = 1  # 版本号
    is_latest: bool = True  # 是否是最新版本
    replaces_id: str = ""  # 替换的旧版本 ID
    # V2.3 新增字段（时效管理）
    expires_at: float = 0.0  # 过期时间戳（0表示永不过期）
    is_expired: bool = False  # 是否已过期
    expiry_reason: str = ""  # 过期原因
    # V2.4 新增字段（知识溯源）
    original_text: str = ""  # 原始消息完整文本
    message_timestamp: float = 0.0  # 原始消息发送时间
    conversation_type: str = ""  # 会话类型：single/group
    conversation_name: str = ""  # 会话名称（群名或单聊对象）
    sender_dept: str = ""  # 发送者部门
    file_size: int = 0  # 文件大小（字节）
    file_type: str = ""  # 文件类型
    chunk_index: int = 0  # 分块在原始消息中的索引
    total_chunks: int = 0  # 原始消息的总分块数
    # V2.5 新增字段（使用统计）
    last_accessed_at: float = 0.0  # 最后访问时间
    access_count: int = 0  # 访问次数
    last_query: str = ""  # 最后一次查询词
    # V2.6 新增字段（权限管理）
    access_level: str = "public"  # 访问级别：public, internal, confidential


@dataclass
class SearchResult:
    """搜索结果"""
    chunk: DocumentChunk
    score: float
    match_type: str  # "semantic", "keyword", "hybrid"
    highlights: list = field(default_factory=list)  # 高亮片段


@dataclass
class KnowledgeStats:
    """知识库统计"""
    total_chunks: int = 0
    total_messages: int = 0
    source_types: dict = field(default_factory=dict)
    top_senders: list = field(default_factory=list)
    date_range: dict = field(default_factory=dict)
    index_size_mb: float = 0.0
    categories: dict = field(default_factory=dict)  # 按类别统计
    # 溯源统计
    conversations: dict = field(default_factory=dict)  # 按会话统计
    conversation_types: dict = field(default_factory=dict)  # 按会话类型统计
    file_types: dict = field(default_factory=dict)  # 按文件类型统计


# ========== Embedding 缓存 ==========
class EmbeddingCache:
    """Embedding 向量缓存"""

    def __init__(self, max_size: int = EMBEDDING_CACHE_SIZE):
        self._cache: Dict[str, np.ndarray] = {}
        self._max_size = max_size
        self._access_order: List[str] = []

    def get(self, text: str) -> Optional[np.ndarray]:
        """获取缓存的 Embedding"""
        key = self._get_key(text)
        if key in self._cache:
            # 更新访问顺序
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
        return None

    def put(self, text: str, embedding: np.ndarray):
        """缓存 Embedding"""
        key = self._get_key(text)

        # 如果缓存已满，删除最久未访问的
        while len(self._cache) >= self._max_size:
            oldest_key = self._access_order.pop(0)
            del self._cache[oldest_key]

        self._cache[key] = embedding
        self._access_order.append(key)

    def _get_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(text.encode()).hexdigest()

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._access_order.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


# 全局 Embedding 缓存
_embedding_cache = EmbeddingCache()


# ========== 文本处理 ==========
def extract_keywords(text: str, top_n: int = 5) -> List[str]:
    """
    从文本中提取关键词（简单 TF-IDF 实现）

    参数:
        text: 输入文本
        top_n: 返回关键词数量

    返回:
        关键词列表
    """
    if not text:
        return []

    # 中文分词（简单实现，按标点和空格分割）
    words = re.findall(r'[一-鿿]+|[a-zA-Z]+', text.lower())

    # 停用词
    stop_words = {'的', '了', '是', '在', '我', '有', '和', '就', '不', '人',
                  '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
                  '你', '会', '着', '没有', '看', '好', '自己', '这', '他', '她',
                  '它', '们', '那', '些', '什么', '怎么', '如何', '为什么', '可以',
                  '把', '被', '让', '给', '对', '从', '但', '可是', '如果', '因为'}

    # 过滤停用词，统计词频
    word_counts = Counter(w for w in words if w not in stop_words and len(w) > 1)

    # 返回 Top-N 关键词
    keywords = [word for word, _ in word_counts.most_common(top_n)]

    # 改进中文分词：将长词拆分为更小的单元
    extended_keywords = list(keywords)
    for keyword in keywords:
        # 如果关键词长度大于 3，尝试拆分
        if len(keyword) > 3:
            # 按常见后缀拆分
            suffixes = ['信息', '资料', '数据', '情况', '详情', '介绍', '简介', '一下']
            for suffix in suffixes:
                if keyword.endswith(suffix) and len(keyword) > len(suffix):
                    prefix = keyword[:-len(suffix)]
                    if len(prefix) >= 2:
                        extended_keywords.append(prefix)
                    break

            # 按常见前缀拆分
            prefixes = ['汇报', '查询', '搜索', '查看', '显示', '展示', '介绍']
            for prefix in prefixes:
                if keyword.startswith(prefix) and len(keyword) > len(prefix):
                    suffix = keyword[len(prefix):]
                    if len(suffix) >= 2:
                        extended_keywords.append(suffix)
                    break

            # 按"的"拆分
            if '的' in keyword:
                parts = keyword.split('的')
                for part in parts:
                    if len(part) >= 2:
                        extended_keywords.append(part)

            # 按"一下"拆分
            if '一下' in keyword:
                parts = keyword.split('一下')
                for part in parts:
                    if len(part) >= 2:
                        extended_keywords.append(part)

            # 按常见称呼拆分（教授、老师、医生等）
            title_match = re.search(r'(张|王|李|刘|陈|杨|黄|赵|周|吴)(教授|老师|医生|主任|院长)', keyword)
            if title_match:
                extended_keywords.append(title_match.group())

    # 去重
    extended_keywords = list(set(extended_keywords))

    return extended_keywords


def generate_summary(text: str, max_length: int = 100) -> str:
    """
    生成文本摘要（简单截取）

    参数:
        text: 输入文本
        max_length: 最大长度

    返回:
        摘要文本
    """
    if not text:
        return ""

    # 取前 max_length 个字符
    summary = text[:max_length].strip()

    # 尝试在句子边界截断
    for sep in ['。', '！', '？', '；', '\n']:
        idx = summary.rfind(sep)
        if idx > max_length // 2:
            summary = summary[:idx + 1]
            break

    if len(text) > max_length:
        summary += "..."

    return summary


def split_text_v2(text: str, chunk_size: int = CHUNK_SIZE,
                  overlap: int = CHUNK_OVERLAP) -> List[Tuple[str, List[str]]]:
    """
    改进的文本分块策略

    参数:
        text: 原始文本
        chunk_size: 每个分块的最大字符数
        overlap: 分块之间的重叠字符数

    返回:
        [(分块文本, 关键词列表), ...]
    """
    if not text or not text.strip():
        return []

    # 先按段落分割
    paragraphs = text.split("\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # 如果当前分块加上新段落不超过限制，合并
        if len(current_chunk) + len(para) + 1 <= chunk_size:
            current_chunk = f"{current_chunk}\n{para}" if current_chunk else para
        else:
            # 保存当前分块
            if current_chunk:
                keywords = extract_keywords(current_chunk)
                chunks.append((current_chunk, keywords))

            # 如果段落本身超过限制，按固定长度分割
            if len(para) > chunk_size:
                sub_chunks = _split_long_text(para, chunk_size, overlap)
                for sub_chunk in sub_chunks[:-1]:
                    keywords = extract_keywords(sub_chunk)
                    chunks.append((sub_chunk, keywords))
                current_chunk = sub_chunks[-1] if sub_chunks else ""
            else:
                current_chunk = para

    if current_chunk:
        keywords = extract_keywords(current_chunk)
        chunks.append((current_chunk, keywords))

    return chunks


def _split_long_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """将长文本按固定长度分割"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
    return chunks


# ========== Embedding 生成 ==========
_local_embedding_model = None


def _get_local_embedding_model():
    """获取本地 Embedding 模型（懒加载）"""
    global _local_embedding_model
    if _local_embedding_model is None:
        try:
            hf_endpoint = getattr(config, 'HF_ENDPOINT', '')
            if hf_endpoint:
                os.environ['HF_ENDPOINT'] = hf_endpoint

            from sentence_transformers import SentenceTransformer
            model_name = getattr(config, 'LOCAL_EMBEDDING_MODEL',
                                 'BAAI/bge-small-zh-v1.5')
            logger.info(f"加载本地 Embedding 模型: {model_name}")
            _local_embedding_model = SentenceTransformer(model_name)
            logger.info("本地 Embedding 模型加载完成")
        except Exception as e:
            logger.error(f"加载本地 Embedding 模型失败: {e}")
            _local_embedding_model = None
    return _local_embedding_model


async def get_embeddings(texts: List[str], use_cache: bool = True) -> Optional[np.ndarray]:
    """
    生成文本的 Embedding 向量（带缓存）

    参数:
        texts: 文本列表
        use_cache: 是否使用缓存

    返回:
        numpy 数组，shape 为 (len(texts), embedding_dim)
    """
    if not texts:
        return None

    # 检查缓存
    cached_embeddings = []
    uncached_texts = []
    uncached_indices = []

    if use_cache:
        for i, text in enumerate(texts):
            cached = _embedding_cache.get(text)
            if cached is not None:
                cached_embeddings.append((i, cached))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
    else:
        uncached_texts = texts
        uncached_indices = list(range(len(texts)))

    # 生成未缓存的 Embedding
    new_embeddings = None
    if uncached_texts:
        # 优先使用本地模型
        model = _get_local_embedding_model()
        if model is not None:
            try:
                new_embeddings = model.encode(uncached_texts, normalize_embeddings=True)
                new_embeddings = np.array(new_embeddings, dtype=np.float32)
            except Exception as e:
                logger.warning(f"本地 Embedding 生成失败，尝试远程 API: {e}")

        # 备用：远程 API
        if new_embeddings is None:
            from openai import OpenAI
            api_key = getattr(config, 'EMBEDDING_API_KEY', '') or config.OPENAI_API_KEY
            base_url = getattr(config, 'EMBEDDING_BASE_URL', '') or config.OPENAI_BASE_URL
            model_name = getattr(config, 'EMBEDDING_MODEL', 'text-embedding-3-small')

            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                response = client.embeddings.create(
                    model=model_name,
                    input=uncached_texts,
                )
                new_embeddings = np.array([item.embedding for item in response.data],
                                         dtype=np.float32)
            except Exception as e:
                logger.error(f"远程 Embedding 也失败: {e}")
                return None

        # 缓存新生成的 Embedding
        if use_cache and new_embeddings is not None:
            for text, embedding in zip(uncached_texts, new_embeddings):
                _embedding_cache.put(text, embedding)

    # 合并缓存和新生成的 Embedding
    if not cached_embeddings:
        return new_embeddings

    if new_embeddings is None and cached_embeddings:
        # 所有都命中缓存
        result = np.zeros((len(texts), cached_embeddings[0][1].shape[0]), dtype=np.float32)
        for idx, emb in cached_embeddings:
            result[idx] = emb
        return result

    # 混合情况
    result = np.zeros((len(texts), new_embeddings.shape[1]), dtype=np.float32)
    for idx, emb in cached_embeddings:
        result[idx] = emb
    for i, idx in enumerate(uncached_indices):
        result[idx] = new_embeddings[i]

    return result


def cosine_similarity(query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
    """计算余弦相似度"""
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    doc_norms = doc_vecs / (np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-10)
    return np.dot(doc_norms, query_norm)


# ========== Rerank 模块 ==========
class Reranker:
    """
    重排序器：对检索结果进行精排

    支持多种策略：
    - local: 使用本地 Cross-encoder 模型（需要 sentence-transformers）
    - llm: 使用 LLM 进行重排序（通过 OpenAI API）
    - api: 使用第三方 Rerank API（如 Cohere、Jina）
    - rule: 基于规则的重排序（默认，无需额外依赖）
    """

    def __init__(self):
        self._model = None
        self._strategy = config.RERANK_STRATEGY if config.RERANK_ENABLED else "rule"

        if self._strategy == "local":
            self._init_local_model()

    def _init_local_model(self):
        """初始化本地 Cross-encoder 模型"""
        try:
            from sentence_transformers import CrossEncoder
            model_name = config.LOCAL_RERANK_MODEL
            logger.info(f"加载本地 Rerank 模型: {model_name}")

            # 设置 HuggingFace 镜像
            if config.HF_ENDPOINT:
                os.environ["HF_ENDPOINT"] = config.HF_ENDPOINT

            self._model = CrossEncoder(model_name, max_length=512)
            logger.info("本地 Rerank 模型加载完成")
        except ImportError:
            logger.warning("sentence-transformers 未安装，回退到规则重排序")
            self._strategy = "rule"
        except Exception as e:
            logger.error(f"加载本地 Rerank 模型失败: {e}")
            self._strategy = "rule"

    async def rerank(
        self,
        query: str,
        results: List['SearchResult'],
        top_k: int = 3
    ) -> List['SearchResult']:
        """
        对检索结果进行重排序

        参数:
            query: 查询文本
            results: 初始检索结果
            top_k: 返回结果数量

        返回:
            重排序后的结果
        """
        if not results:
            return []

        if len(results) <= top_k:
            # 结果数量已经满足，直接返回
            return results

        try:
            if self._strategy == "local":
                return await self._rerank_local(query, results, top_k)
            elif self._strategy == "llm":
                return await self._rerank_llm(query, results, top_k)
            elif self._strategy == "api":
                return await self._rerank_api(query, results, top_k)
            else:
                return self._rerank_rule(query, results, top_k)
        except Exception as e:
            logger.error(f"Rerank 失败，回退到规则重排序: {e}")
            return self._rerank_rule(query, results, top_k)

    async def _rerank_local(
        self,
        query: str,
        results: List['SearchResult'],
        top_k: int
    ) -> List['SearchResult']:
        """使用本地 Cross-encoder 模型重排序"""
        if self._model is None:
            return self._rerank_rule(query, results, top_k)

        # 构建 query-document 对
        pairs = [(query, result.chunk.text[:512]) for result in results]

        # 计算相关性分数
        scores = self._model.predict(pairs)

        # 更新分数并排序
        for i, result in enumerate(results):
            # 结合原始分数和 rerank 分数（权重可调）
            result.score = float(scores[i]) * 0.7 + result.score * 0.3

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    async def _rerank_llm(
        self,
        query: str,
        results: List['SearchResult'],
        top_k: int
    ) -> List['SearchResult']:
        """使用 LLM 进行重排序"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=config.OPENAI_API_KEY,
                base_url=config.OPENAI_BASE_URL or None
            )

            # 构建 prompt
            docs_text = []
            for i, result in enumerate(results):
                text = result.chunk.text[:200].replace("\n", " ")
                docs_text.append(f"[{i+1}] {text}")

            prompt = f"""请根据查询的相关性对以下文档进行排序。

查询：{query}

文档列表：
{chr(10).join(docs_text)}

请返回一个 JSON 数组，包含文档编号（从1开始），按相关性从高到低排序。
只返回最相关的 {top_k} 个文档编号。
示例格式：[3, 1, 5]

注意：
- 只返回 JSON 数组，不要有其他文字
- 编号对应文档前的数字
- 只返回最相关的 {top_k} 个"""

            response = await client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个文档排序助手，只返回 JSON 数组。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=100
            )

            # 解析响应
            content = response.choices[0].message.content.strip()
            # 提取 JSON 数组
            import re
            match = re.search(r'\[[\d,\s]+\]', content)
            if match:
                indices = json.loads(match.group())
                # 按 LLM 返回的顺序重排
                reranked = []
                for idx in indices:
                    if 1 <= idx <= len(results):
                        result = results[idx - 1]
                        result.score = result.score * 1.2  # 提升被 LLM 选中的结果
                        reranked.append(result)

                # 添加未被选中的结果
                selected_indices = set(indices)
                for i, result in enumerate(results):
                    if (i + 1) not in selected_indices:
                        reranked.append(result)

                return reranked[:top_k]

        except Exception as e:
            logger.error(f"LLM Rerank 失败: {e}")

        # 回退到规则重排序
        return self._rerank_rule(query, results, top_k)

    async def _rerank_api(
        self,
        query: str,
        results: List['SearchResult'],
        top_k: int
    ) -> List['SearchResult']:
        """使用第三方 Rerank API 重排序"""
        try:
            import httpx

            if not config.RERANK_API_KEY:
                logger.warning("RERANK_API_KEY 未配置，回退到规则重排序")
                return self._rerank_rule(query, results, top_k)

            # 构建请求
            documents = [result.chunk.text[:512] for result in results]

            # 支持 Cohere Rerank API 格式
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config.RERANK_BASE_URL or "https://api.cohere.ai/v1/rerank",
                    headers={
                        "Authorization": f"Bearer {config.RERANK_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": config.RERANK_MODEL or "rerank-multilingual-v3.0",
                        "query": query,
                        "documents": documents,
                        "top_n": top_k,
                        "return_documents": False
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    # 解析结果
                    reranked = []
                    for item in data.get("results", []):
                        idx = item["index"]
                        result = results[idx]
                        result.score = item["relevance_score"]
                        reranked.append(result)

                    return reranked[:top_k]

        except Exception as e:
            logger.error(f"API Rerank 失败: {e}")

        # 回退到规则重排序
        return self._rerank_rule(query, results, top_k)

    def _rerank_rule(
        self,
        query: str,
        results: List['SearchResult'],
        top_k: int
    ) -> List['SearchResult']:
        """基于规则的重排序（默认策略）"""
        query_keywords = set(extract_keywords(query, top_n=10))

        for result in results:
            chunk_text = result.chunk.text.lower()

            # 计算额外分数
            bonus = 0.0

            # 关键词出现在前半部分加分
            for keyword in query_keywords:
                pos = chunk_text.find(keyword)
                if 0 <= pos < len(chunk_text) // 2:
                    bonus += 0.1

            # 关键词密度加分
            keyword_count = sum(1 for kw in query_keywords if kw in chunk_text)
            bonus += keyword_count * 0.05

            # 有摘要加分
            if result.chunk.summary:
                bonus += 0.05

            # 有高亮加分
            if result.highlights:
                bonus += 0.05

            # 文本长度适中加分（不要太短也不要太短）
            text_len = len(result.chunk.text)
            if 100 <= text_len <= 500:
                bonus += 0.03

            result.score += bonus

        # 重新排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]


# 全局 Reranker 实例
_reranker: Optional[Reranker] = None


def get_reranker() -> Reranker:
    """获取全局 Reranker 实例"""
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker


# ========== 知识库主体 ==========
class KnowledgeBase:
    """单个学校的知识库（V2 优化版）"""

    def __init__(self, school_dir: str, corp_id: str):
        self._school_dir = school_dir
        self._corp_id = corp_id
        self._index_dir = os.path.join(school_dir, "index")
        self._messages_dir = os.path.join(school_dir, "messages")
        self._files_dir = os.path.join(school_dir, "files")
        self._structured_dir = os.path.join(school_dir, "structured")
        self._logs_dir = os.path.join(school_dir, "logs")
        self._proactive_dir = os.path.join(school_dir, "proactive")

        os.makedirs(self._index_dir, exist_ok=True)
        os.makedirs(self._messages_dir, exist_ok=True)
        os.makedirs(self._files_dir, exist_ok=True)
        os.makedirs(self._structured_dir, exist_ok=True)
        os.makedirs(self._logs_dir, exist_ok=True)
        os.makedirs(self._proactive_dir, exist_ok=True)

        # 初始化操作日志
        self._op_logger = OperationLogger(self._logs_dir)

        # 初始化主动智能模块
        self._notifier = None
        self._reminder = None
        self._feedback_tracker = None
        self._search_explainer = None
        self._search_suggester = None
        self._init_proactive_modules()

        # 加载索引
        self._chunks: List[DocumentChunk] = []
        self._embeddings: Optional[np.ndarray] = None
        self._keyword_index: Dict[str, Set[int]] = {}  # 关键词倒排索引
        self._load_index()

    def _init_proactive_modules(self):
        """初始化主动智能模块"""
        if not PROACTIVE_ENABLED:
            return

        try:
            # 初始化通知器
            self._notifier = get_notifier(self._proactive_dir)

            # 初始化提醒器
            self._reminder = get_reminder(self, self._notifier)

            # 初始化反馈追踪器
            self._feedback_tracker = get_feedback_tracker(self._proactive_dir)

            logger.info("主动智能模块初始化完成")
        except Exception as e:
            logger.error(f"初始化主动智能模块失败: {e}")

        if not SEARCH_ENHANCEMENT_ENABLED:
            return

        try:
            # 初始化搜索解释器
            self._search_explainer = get_search_explainer()

            # 初始化搜索建议器
            self._search_suggester = get_search_suggester(self)

            # 初始化权重优化器
            self._weight_optimizer = get_weight_optimizer(self._proactive_dir)

            logger.info("检索增强模块初始化完成")
        except Exception as e:
            logger.error(f"初始化检索增强模块失败: {e}")

        if not MAINTENANCE_ENABLED:
            return

        try:
            # 初始化快照管理器
            self._snapshot_manager = get_snapshot_manager(self)

            # 初始化批量导入导出器
            self._batch_importer = BatchImporter(self)
            self._batch_exporter = BatchExporter(self)

            logger.info("运维模块初始化完成")
        except Exception as e:
            logger.error(f"初始化运维模块失败: {e}")

        if not MULTIMODAL_ENABLED:
            return

        try:
            # 初始化 OCR 引擎
            self._ocr_engine = get_ocr_engine()

            # 初始化文件解析器
            self._file_parser = get_file_parser()

            logger.info("多模态模块初始化完成")
        except Exception as e:
            logger.error(f"初始化多模态模块失败: {e}")

        if not FEEDBACK_LOOP_ENABLED:
            return

        try:
            # 初始化反馈收集器
            self._feedback_collector = get_feedback_collector(self._proactive_dir)

            logger.info("反馈循环模块初始化完成")
        except Exception as e:
            logger.error(f"初始化反馈循环模块失败: {e}")

        if not TRANSCRIBER_ENABLED:
            return

        try:
            # 初始化媒体转写器
            self._media_transcriber = get_media_transcriber()

            logger.info("音视频转写模块初始化完成")
        except Exception as e:
            logger.error(f"初始化音视频转写模块失败: {e}")

        if not AB_TESTING_ENABLED:
            return

        try:
            # 初始化 A/B 测试管理器
            self._ab_manager = get_ab_manager(self._proactive_dir)

            logger.info("A/B 测试模块初始化完成")
        except Exception as e:
            logger.error(f"初始化 A/B 测试模块失败: {e}")

        if not SLA_MONITOR_ENABLED:
            return

        try:
            # 初始化 SLA 监控器
            self._sla_monitor = get_sla_monitor(self._proactive_dir)

            logger.info("SLA 监控模块初始化完成")
        except Exception as e:
            logger.error(f"初始化 SLA 监控模块失败: {e}")

    def _load_index(self):
        """从磁盘加载索引"""
        chunks_file = os.path.join(self._index_dir, "chunks.json")
        embeddings_file = os.path.join(self._index_dir, "embeddings.npy")

        if os.path.exists(chunks_file):
            try:
                with open(chunks_file, "r", encoding="utf-8") as f:
                    chunks_data = json.load(f)
                self._chunks = [DocumentChunk(**c) for c in chunks_data]
                logger.info(f"加载知识库索引: {len(self._chunks)} 个分块")

                # 构建关键词倒排索引
                self._build_keyword_index()
            except Exception as e:
                logger.warning(f"加载分块索引失败: {e}")
                self._chunks = []

        if os.path.exists(embeddings_file):
            try:
                self._embeddings = np.load(embeddings_file)
                logger.info(f"加载向量索引: {self._embeddings.shape}")
            except Exception as e:
                logger.warning(f"加载向量索引失败: {e}")
                self._embeddings = None

    def _build_keyword_index(self):
        """构建关键词倒排索引"""
        self._keyword_index.clear()
        for i, chunk in enumerate(self._chunks):
            # 从关键词字段构建索引
            for keyword in chunk.keywords:
                if keyword not in self._keyword_index:
                    self._keyword_index[keyword] = set()
                self._keyword_index[keyword].add(i)

            # 从文本中提取关键词补充
            text_keywords = extract_keywords(chunk.text, top_n=10)
            for keyword in text_keywords:
                if keyword not in self._keyword_index:
                    self._keyword_index[keyword] = set()
                self._keyword_index[keyword].add(i)

    def _save_index(self):
        """保存索引到磁盘（支持分页）"""
        # 清理旧的分页文件
        for f in os.listdir(self._index_dir):
            if f.startswith("chunks_page_") and f.endswith(".json"):
                os.remove(os.path.join(self._index_dir, f))

        # 保存完整索引（用于兼容）
        chunks_file = os.path.join(self._index_dir, "chunks.json")
        embeddings_file = os.path.join(self._index_dir, "embeddings.npy")

        try:
            with open(chunks_file, "w", encoding="utf-8") as f:
                json.dump([asdict(c) for c in self._chunks], f,
                          ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存分块索引失败: {e}")

        # 分页保存
        if len(self._chunks) > INDEX_PAGE_SIZE:
            self._save_index_pages()

        if self._embeddings is not None:
            try:
                np.save(embeddings_file, self._embeddings)
            except Exception as e:
                logger.error(f"保存向量索引失败: {e}")

    def _save_index_pages(self):
        """分页保存索引"""
        total_pages = (len(self._chunks) + INDEX_PAGE_SIZE - 1) // INDEX_PAGE_SIZE

        for page in range(total_pages):
            start = page * INDEX_PAGE_SIZE
            end = min(start + INDEX_PAGE_SIZE, len(self._chunks))
            page_chunks = self._chunks[start:end]

            page_file = os.path.join(self._index_dir, f"chunks_page_{page:04d}.json")
            try:
                with open(page_file, "w", encoding="utf-8") as f:
                    json.dump([asdict(c) for c in page_chunks], f,
                              ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"保存索引分页 {page} 失败: {e}")

        # 保存元信息
        meta = {
            "total_chunks": len(self._chunks),
            "total_pages": total_pages,
            "page_size": INDEX_PAGE_SIZE,
            "updated_at": datetime.now().isoformat(),
        }
        meta_file = os.path.join(self._index_dir, "index_meta.json")
        try:
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存索引元信息失败: {e}")

    async def add_message(
        self,
        text: str,
        source_type: str,
        source_id: str,
        sender_id: str = "",
        sender_nick: str = "",
        conversation_id: str = "",
        message_type: str = "",
        file_name: str = "",
        file_path: str = "",
        tags: list = None,
        # 溯源增强参数
        conversation_type: str = "",  # 会话类型：single/group
        conversation_name: str = "",  # 会话名称（群名或单聊对象）
        sender_dept: str = "",  # 发送者部门
        file_size: int = 0,  # 文件大小（字节）
        file_type: str = "",  # 文件类型
        message_timestamp: float = 0.0,  # 原始消息发送时间
        # 权限管理参数
        access_level: str = "public",  # 访问级别：public/internal/confidential
    ) -> List[DocumentChunk]:
        """
        将消息内容存入知识库

        参数:
            text: 提取的文本内容
            source_type: 来源类型 (text/image/file)
            source_id: 消息ID或文件ID
            sender_id: 发送者ID
            sender_nick: 发送者昵称
            conversation_id: 会话ID
            message_type: 消息类型
            file_name: 文件名
            file_path: 原始文件路径
            tags: 标签列表
            conversation_type: 会话类型（single/group）
            conversation_name: 会话名称（群名或单聊对象）
            sender_dept: 发送者部门
            file_size: 文件大小（字节）
            file_type: 文件类型
            message_timestamp: 原始消息发送时间戳

        返回:
            生成的分块列表
        """
        if not text or not text.strip():
            logger.warning("空文本，跳过存档")
            return []

        # 消息过滤：跳过无意义消息和问题类消息（使用智能过滤：关键词匹配 + LLM）
        if source_type == "text":
            if await smart_should_skip(text):
                logger.debug(f"跳过无意义消息: {text[:50]}")
                return []

        # 文本清洗
        cleaned_text = clean_text(text)

        # 深度清洗用于索引（不影响归档）
        indexing_text = clean_for_indexing(text)

        timestamp = time.time()

        # 计算内容哈希（用于去重）
        content_hash = compute_content_hash(indexing_text)

        # 自动分类（使用智能分类：关键词匹配 + LLM）
        category = await smart_classify(text)

        # 去重检查
        if DEDUP_ENABLED:
            duplicate = self._find_duplicate(content_hash, category, text)
            if duplicate:
                logger.debug(f"跳过重复内容: {text[:50]}")
                # 记录操作日志
                self._op_logger.log(OperationLog(
                    timestamp=datetime.now().isoformat(),
                    operation="add",
                    user_id=sender_id,
                    user_nick=sender_nick,
                    source_type=source_type,
                    source_id=source_id,
                    file_name=file_name,
                    result_count=0,
                    status="skipped",
                    details=f"重复内容，哈希={content_hash[:8]}"
                ))
                return []

        # 版本控制：处理同一实体的更新
        replaces_id = ""
        if VERSION_CONTROL_ENABLED and category in VERSION_CONTROLLED_CATEGORIES:
            entity_key = extract_entity_key(text, category)
            if entity_key:
                # 查找同一实体的旧版本
                old_chunks = self._find_chunks_by_entity(entity_key, category)
                if old_chunks:
                    if VERSION_STRATEGY == "overwrite":
                        # 覆盖模式：删除旧版本
                        self._remove_chunks(old_chunks)
                        replaces_id = old_chunks[0].chunk_id.split("_")[0]
                        logger.info(f"覆盖旧版本: {entity_key} ({len(old_chunks)} 个分块)")
                    elif VERSION_STRATEGY == "smart":
                        # 智能模式：内容相似则覆盖，否则保留
                        old_text = " ".join([c.text for c in old_chunks[:3]])
                        similarity = self._compute_text_similarity(indexing_text, old_text)
                        if similarity > 0.8:  # 相似度阈值
                            self._remove_chunks(old_chunks)
                            replaces_id = old_chunks[0].chunk_id.split("_")[0]
                            logger.info(f"智能覆盖: {entity_key} (相似度={similarity:.2f})")
                        else:
                            logger.info(f"保留历史版本: {entity_key} (相似度={similarity:.2f})")
                    # keep 模式：不删除旧版本

        # 保存原始消息归档（保留原始文本，便于查看）
        self._archive_message(
            text=text,
            source_type=source_type,
            source_id=source_id,
            sender_id=sender_id,
            sender_nick=sender_nick,
            conversation_id=conversation_id,
            message_type=message_type,
            file_name=file_name,
            file_path=file_path,
            timestamp=timestamp,
            tags=tags or [],
        )

        # 使用清洗后的文本进行分块和索引
        text_chunks = split_text_v2(indexing_text)

        # 计算版本号
        version = 1
        if replaces_id:
            # 查找旧版本的最大版本号
            old_versions = [c.version for c in self._chunks
                           if c.chunk_id.startswith(replaces_id)]
            if old_versions:
                version = max(old_versions) + 1

        # 计算过期时间
        expires_at = 0.0
        if EXPIRY_ENABLED:
            # 首先尝试从文本中提取过期时间
            extracted_expiry = extract_expiry_date(text, category)
            if extracted_expiry:
                expires_at = extracted_expiry
                logger.debug(f"从文本提取到过期时间: {datetime.fromtimestamp(expires_at).isoformat()}")
            else:
                # 使用默认过期时间
                expires_at = get_default_expiry(category, timestamp)
                if expires_at > 0:
                    logger.debug(f"使用默认过期时间: {EXPIRY_DAYS.get(category, EXPIRY_DAYS.get('other', 180))} 天")

        # 创建 DocumentChunk 对象
        new_chunks = []
        total_chunks_count = len(text_chunks)
        for i, (chunk_text, keywords) in enumerate(text_chunks):
            chunk_id = f"{source_id}_{i}"
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                text=chunk_text,
                source_type=source_type,
                source_id=source_id,
                sender_id=sender_id,
                sender_nick=sender_nick,
                corp_id=self._corp_id,
                timestamp=timestamp,
                conversation_id=conversation_id,
                message_type=message_type,
                file_name=file_name,
                tags=tags or [],
                keywords=keywords,
                summary=generate_summary(chunk_text),
                category=category,
                content_hash=content_hash,
                version=version,
                is_latest=True,
                replaces_id=replaces_id,
                expires_at=expires_at,
                is_expired=False,
                expiry_reason="",
                # 溯源字段
                original_text=text,
                message_timestamp=message_timestamp if message_timestamp > 0 else timestamp,
                conversation_type=conversation_type,
                conversation_name=conversation_name,
                sender_dept=sender_dept,
                file_size=file_size,
                file_type=file_type if file_type else self._detect_file_type(file_name),
                chunk_index=i,
                total_chunks=total_chunks_count,
                # 权限管理字段
                access_level=access_level,
            )
            new_chunks.append(chunk)

        # 生成 Embedding 并更新索引
        if new_chunks:
            new_texts = [c.text for c in new_chunks]
            new_embeddings = await get_embeddings(new_texts)

            if new_embeddings is not None:
                self._chunks.extend(new_chunks)
                if self._embeddings is None:
                    self._embeddings = new_embeddings
                else:
                    self._embeddings = np.vstack([self._embeddings, new_embeddings])
            else:
                self._chunks.extend(new_chunks)

            # 更新关键词索引
            for i, chunk in enumerate(new_chunks):
                chunk_idx = len(self._chunks) - len(new_chunks) + i
                for keyword in chunk.keywords:
                    if keyword not in self._keyword_index:
                        self._keyword_index[keyword] = set()
                    self._keyword_index[keyword].add(chunk_idx)

            self._save_index()
            logger.info(f"知识库新增 {len(new_chunks)} 个分块，总计 {len(self._chunks)} 个")

        # 记录操作日志
        details = f"生成 {len(new_chunks)} 个分块"
        if replaces_id:
            details += f", 替换旧版本, 版本={version}"
        if content_hash:
            details += f", 哈希={content_hash[:8]}"

        self._op_logger.log(OperationLog(
            timestamp=datetime.now().isoformat(),
            operation="add",
            user_id=sender_id,
            user_nick=sender_nick,
            source_type=source_type,
            source_id=source_id,
            file_name=file_name,
            result_count=len(new_chunks),
            status="success" if new_chunks else "skipped",
            details=details if new_chunks else "消息被过滤"
        ))

        return new_chunks

    def _detect_file_type(self, file_name: str) -> str:
        """
        检测文件类型

        参数:
            file_name: 文件名

        返回:
            文件类型
        """
        if not file_name:
            return ""

        ext = os.path.splitext(file_name)[1].lower()
        type_map = {
            ".pdf": "pdf",
            ".doc": "word", ".docx": "word",
            ".xls": "excel", ".xlsx": "excel",
            ".ppt": "powerpoint", ".pptx": "powerpoint",
            ".txt": "text",
            ".md": "markdown",
            ".jpg": "image", ".jpeg": "image", ".png": "image",
            ".gif": "image", ".bmp": "image", ".webp": "image",
            ".mp3": "audio", ".wav": "audio",
            ".mp4": "video", ".avi": "video",
            ".zip": "archive", ".rar": "archive",
        }
        return type_map.get(ext, "other")

    # ========== 去重与版本控制辅助方法 ==========

    def _find_duplicate(self, content_hash: str, category: str, text: str) -> Optional[DocumentChunk]:
        """
        查找重复内容

        参数:
            content_hash: 内容哈希
            category: 内容类别
            text: 原始文本

        返回:
            重复的分块（如果找到）
        """
        # 基于哈希查找
        for chunk in self._chunks:
            if chunk.content_hash == content_hash:
                return chunk

        # 对于非版本控制类别，也检查文本相似性
        if category not in VERSION_CONTROLLED_CATEGORIES:
            for chunk in self._chunks:
                if chunk.category == category:
                    similarity = self._compute_text_similarity(text, chunk.text)
                    if similarity > 0.95:  # 高度相似认为是重复
                        return chunk

        return None

    def _find_chunks_by_entity(self, entity_key: str, category: str) -> List[DocumentChunk]:
        """
        查找同一实体的所有分块

        参数:
            entity_key: 实体键（如班级名称）
            category: 内容类别

        返回:
            该实体的所有分块
        """
        if not entity_key:
            return []

        matching_chunks = []
        for chunk in self._chunks:
            if chunk.category == category:
                chunk_entity = extract_entity_key(chunk.text, category)
                if chunk_entity == entity_key:
                    matching_chunks.append(chunk)

        return matching_chunks

    def _remove_chunks(self, chunks_to_remove: List[DocumentChunk]):
        """
        从索引中移除指定分块

        参数:
            chunks_to_remove: 要移除的分块列表
        """
        if not chunks_to_remove:
            return

        # 获取要移除的 chunk_id 集合
        remove_ids = {c.chunk_id for c in chunks_to_remove}

        # 从 chunks 列表中移除
        self._chunks = [c for c in self._chunks if c.chunk_id not in remove_ids]

        # 重建向量索引和关键词索引
        self._rebuild_embeddings()
        self._build_keyword_index()
        self._save_index()

        logger.info(f"移除了 {len(chunks_to_remove)} 个旧分块")

    def _compute_text_similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的相似度

        参数:
            text1: 文本1
            text2: 文本2

        返回:
            相似度（0-1）
        """
        if not text1 or not text2:
            return 0.0

        # 简单的基于词汇重叠的相似度
        words1 = set(re.findall(r'[\w一-鿿]+', text1.lower()))
        words2 = set(re.findall(r'[\w一-鿿]+', text2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def get_version_history(self, entity_key: str, category: str) -> List[dict]:
        """
        获取实体的版本历史

        参数:
            entity_key: 实体键（如班级名称）
            category: 内容类别

        返回:
            版本历史列表
        """
        chunks = self._find_chunks_by_entity(entity_key, category)
        if not chunks:
            return []

        # 按版本号排序
        chunks.sort(key=lambda x: x.version, reverse=True)

        history = []
        for chunk in chunks:
            history.append({
                "version": chunk.version,
                "timestamp": datetime.fromtimestamp(chunk.timestamp).isoformat(),
                "is_latest": chunk.is_latest,
                "text_preview": chunk.text[:100] + "..." if len(chunk.text) > 100 else chunk.text,
                "source_id": chunk.source_id,
                "sender_nick": chunk.sender_nick,
            })

        return history

    async def search(self, query: str, top_k: int = TOP_K,
                     method: str = "hybrid",
                     use_rerank: bool = True,
                     category: str = None,
                     start_time_filter: float = None,
                     end_time_filter: float = None,
                     source_type: str = None,
                     include_explanation: bool = False,
                     include_intent: bool = True,
                     user_id: str = "", user_nick: str = "",
                     user_role: str = "teacher") -> dict:
        """
        智能检索：结合意图理解、语义检索和关键词检索，支持 Rerank 精排和过滤

        参数:
            query: 查询文本
            top_k: 返回结果数量
            method: 检索方法 ("semantic", "keyword", "hybrid")
            use_rerank: 是否使用 Rerank 精排（默认 True）
            category: 内容类别过滤 (schedule/exam/contact/homework/notice/teaching/student)
            start_time_filter: 开始时间过滤（时间戳）
            end_time_filter: 结束时间过滤（时间戳）
            source_type: 来源类型过滤 (text/image/file)
            include_explanation: 是否包含搜索解释
            include_intent: 是否包含意图理解（默认 True）
            user_id: 用户 ID（用于日志）
            user_nick: 用户昵称（用于日志）
            user_role: 用户角色（用于权限过滤）

        返回:
            {
                "results": SearchResult 列表,
                "intent": QueryIntent 对象（如果 include_intent=True）,
                "explanations": SearchExplanation 列表（如果 include_explanation=True）,
                "suggestions": 检索建议列表,
                "stats": 检索统计信息,
                "permission_info": 权限信息（如果有受限内容）
            }
        """
        start_time = time.time()

        # 第零阶段：意图理解
        intent = None
        if include_intent and config.LLM_INTENT_ENABLED:
            try:
                from agent.search.intent import recognize_intent
                intent = await recognize_intent(query)
                logger.debug(f"查询意图: type={intent.type}, confidence={intent.confidence}, entities={intent.entities}")

                # 如果意图识别置信度高，使用意图建议的类别
                if intent.confidence >= 0.7 and intent.suggested_categories and not category:
                    # 使用意图建议的类别进行过滤
                    category = intent.suggested_categories[0] if len(intent.suggested_categories) == 1 else None
            except Exception as e:
                logger.debug(f"意图识别失败，使用默认检索: {e}")

        if not self._chunks:
            # 记录操作日志
            self._op_logger.log(OperationLog(
                timestamp=datetime.now().isoformat(),
                operation="search",
                user_id=user_id,
                user_nick=user_nick,
                query=query,
                result_count=0,
                status="skipped",
                details="知识库为空"
            ))
            return {"results": [], "intent": intent, "explanations": [], "suggestions": [], "stats": {}}

        # 第一阶段：召回（多取一些用于过滤和 rerank）
        # 根据意图调整召回数量
        base_recall = top_k * 3 if use_rerank and config.RERANK_ENABLED else top_k
        if intent and intent.confidence >= 0.7:
            # 意图明确时，多召回一些结果
            recall_k = base_recall * 2
        else:
            recall_k = base_recall * 5 if (category or start_time_filter or source_type) else base_recall

        if method == "semantic":
            results = await self._semantic_search(query, recall_k)
        elif method == "keyword":
            results = self._keyword_search(query, recall_k)
        else:  # hybrid
            results = await self._hybrid_search(query, recall_k)

        # 第二阶段：过滤
        if category or start_time_filter or end_time_filter or source_type:
            results = self._filter_results(
                results,
                category=category,
                start_time=start_time_filter,
                end_time=end_time_filter,
                source_type=source_type
            )

        # 第三阶段：Rerank 精排
        rerank_used = False
        if use_rerank and config.RERANK_ENABLED and len(results) > top_k:
            try:
                reranker = get_reranker()
                results = await reranker.rerank(query, results, top_k)
                rerank_used = True
            except Exception as e:
                logger.error(f"Rerank 失败，使用原始排序: {e}")

        # 确保不超过 top_k
        results = results[:top_k]

        # 第四阶段：权限过滤
        permission_info = {}
        if user_id and user_role:
            try:
                from agent.permission_manager import get_permission_manager
                # 获取知识库目录
                kb_dir = self._index_dir if hasattr(self, '_index_dir') else ""
                if kb_dir:
                    # 从路径中提取 corp_id（知识库目录的父目录）
                    corp_id = os.path.basename(os.path.dirname(kb_dir))
                    perm_manager = get_permission_manager(os.path.dirname(kb_dir), corp_id)

                    # 获取用户允许的访问级别
                    allowed_levels = perm_manager.get_allowed_access_levels(user_id)

                    # 检查是否是管理员（admin/principal 有最高权限，不需要过滤）
                    is_admin = user_role in ["admin", "principal"]

                    # 如果不是管理员，进行权限过滤
                    if not is_admin:
                        original_count = len(results)
                        filtered_results = []
                        restricted_count = 0

                        for result in results:
                            # 获取知识块的访问级别，默认为 public
                            access_level = getattr(result.chunk, 'access_level', 'public')
                            if access_level in allowed_levels:
                                filtered_results.append(result)
                            else:
                                restricted_count += 1

                        results = filtered_results

                        # 如果有受限内容，记录权限信息
                        if restricted_count > 0:
                            permission_info = {
                                "has_restricted": True,
                                "restricted_count": restricted_count,
                                "user_role": user_role,
                                "allowed_levels": allowed_levels
                            }
                            logger.info(f"权限过滤: 用户 {user_id} ({user_role}), "
                                       f"过滤掉 {restricted_count} 条受限内容")
                    else:
                        logger.info(f"管理员用户 {user_id} ({user_role}), 跳过权限过滤")
            except Exception as e:
                logger.error(f"权限过滤失败: {e}")

        # 更新访问统计
        if USAGE_STATS_ENABLED and results:
            self._update_access_stats(results, query)

        # 生成搜索解释
        explanations = []
        if include_explanation and SEARCH_ENHANCEMENT_ENABLED and self._search_explainer:
            explanations = self._search_explainer.explain_batch(query, results, category)

        # 获取检索建议
        suggestions = []
        if SEARCH_ENHANCEMENT_ENABLED and self._search_suggester:
            # 记录查询历史
            self._search_suggester.record_query(query, user_id, clicked=False)
            # 获取建议（如果查询词较短）
            if len(query) < 10:
                suggestions = self._search_suggester.suggest(query, top_k=3)

        # 记录操作日志
        elapsed = time.time() - start_time
        details = f"方法={method}, 耗时={elapsed:.2f}s"
        if rerank_used:
            details += f", rerank={config.RERANK_STRATEGY}"
        if category:
            details += f", 类别={get_category_name(category)}"
        if start_time_filter or end_time_filter:
            details += ", 时间过滤"

        # 记录操作日志
        elapsed = time.time() - start_time
        details = f"方法={method}, 耗时={elapsed:.2f}s"
        if rerank_used:
            details += f", rerank={config.RERANK_STRATEGY}"
        if category:
            details += f", 类别={get_category_name(category)}"
        if start_time_filter or end_time_filter:
            details += ", 时间过滤"

        self._op_logger.log(OperationLog(
            timestamp=datetime.now().isoformat(),
            operation="search",
            user_id=user_id,
            user_nick=user_nick,
            query=query,
            result_count=len(results),
            status="success",
            details=details
        ))

        # 构建返回结果
        response = {
            "results": results,
            "intent": {
                "type": intent.type if intent else "other",
                "entities": intent.entities if intent else {},
                "info_type": intent.info_type if intent else "",
                "confidence": intent.confidence if intent else 0.0,
                "suggested_keywords": intent.suggested_keywords if intent else [],
                "suggested_categories": intent.suggested_categories if intent else [],
            } if intent else None,
            "explanations": [e.to_dict() for e in explanations] if explanations else [],
            "suggestions": [s.__dict__ for s in suggestions] if suggestions else [],
            "stats": {
                "total_results": len(results),
                "method": method,
                "rerank_used": rerank_used,
                "elapsed_ms": round(elapsed * 1000, 2),
                "category_filter": category,
                "intent_type": intent.type if intent else None,
                "intent_confidence": intent.confidence if intent else None,
            },
            "permission_info": permission_info  # 权限信息
        }

        return response

    def _filter_results(
        self,
        results: List[SearchResult],
        category: str = None,
        start_time: float = None,
        end_time: float = None,
        source_type: str = None,
        include_expired: bool = False
    ) -> List[SearchResult]:
        """
        过滤检索结果

        参数:
            results: 原始检索结果
            category: 内容类别过滤
            start_time: 开始时间过滤（时间戳）
            end_time: 结束时间过滤（时间戳）
            source_type: 来源类型过滤
            include_expired: 是否包含过期内容（默认 False）

        返回:
            过滤后的结果
        """
        if not results:
            return []

        now = time.time()
        filtered = []
        for result in results:
            chunk = result.chunk

            # 过期内容过滤
            if not include_expired and EXPIRY_ENABLED:
                # 检查是否已标记过期
                if chunk.is_expired:
                    continue
                # 检查是否已过期
                if chunk.expires_at > 0 and chunk.expires_at < now:
                    continue

            # 类别过滤
            if category and chunk.category != category:
                continue

            # 时间过滤
            if start_time and chunk.timestamp < start_time:
                continue
            if end_time and chunk.timestamp > end_time:
                continue

            # 来源类型过滤
            if source_type and chunk.source_type != source_type:
                continue

            filtered.append(result)

        return filtered

    # ========== 时效管理方法 ==========

    def check_expired_chunks(self) -> List[DocumentChunk]:
        """
        检查并标记过期的分块

        返回:
            新标记为过期的分块列表
        """
        if not EXPIRY_ENABLED:
            return []

        now = time.time()
        newly_expired = []

        for chunk in self._chunks:
            if not chunk.is_expired and chunk.expires_at > 0 and chunk.expires_at < now:
                chunk.is_expired = True
                chunk.expiry_reason = f"已过期（过期时间：{datetime.fromtimestamp(chunk.expires_at).isoformat()}）"
                newly_expired.append(chunk)

        if newly_expired:
            self._save_index()
            logger.info(f"标记了 {len(newly_expired)} 个过期分块")

            # 记录操作日志
            self._op_logger.log(OperationLog(
                timestamp=datetime.now().isoformat(),
                operation="expiry_check",
                result_count=len(newly_expired),
                status="success",
                details=f"标记 {len(newly_expired)} 个过期分块"
            ))

        return newly_expired

    def delete_expired_chunks(self, older_than_days: int = 0) -> int:
        """
        删除过期的分块

        参数:
            older_than_days: 只删除超过指定天数的过期分块（0表示删除所有过期分块）

        返回:
            删除的分块数量
        """
        if not EXPIRY_ENABLED:
            return 0

        now = time.time()
        cutoff = now - older_than_days * 24 * 3600 if older_than_days > 0 else now

        expired_chunks = []
        for chunk in self._chunks:
            if chunk.is_expired:
                # 检查是否超过指定天数
                if older_than_days > 0:
                    # 使用过期时间或最后更新时间
                    ref_time = chunk.expires_at if chunk.expires_at > 0 else chunk.timestamp
                    if ref_time > cutoff:
                        continue
                expired_chunks.append(chunk)

        if not expired_chunks:
            return 0

        # 删除过期分块
        expired_ids = {c.chunk_id for c in expired_chunks}
        self._chunks = [c for c in self._chunks if c.chunk_id not in expired_ids]

        # 重建索引
        self._rebuild_embeddings()
        self._build_keyword_index()
        self._save_index()

        logger.info(f"删除了 {len(expired_chunks)} 个过期分块")

        # 记录操作日志
        self._op_logger.log(OperationLog(
            timestamp=datetime.now().isoformat(),
            operation="delete_expired",
            result_count=len(expired_chunks),
            status="success",
            details=f"删除 {len(expired_chunks)} 个过期分块"
        ))

        return len(expired_chunks)

    def get_expiry_stats(self) -> dict:
        """
        获取过期统计信息

        返回:
            过期统计信息
        """
        if not EXPIRY_ENABLED:
            return {"enabled": False}

        now = time.time()
        stats = {
            "enabled": True,
            "total_chunks": len(self._chunks),
            "expired": 0,
            "expiring_soon": 0,  # 7天内过期
            "by_category": {},
        }

        for chunk in self._chunks:
            cat = chunk.category or "other"

            if cat not in stats["by_category"]:
                stats["by_category"][cat] = {
                    "total": 0,
                    "expired": 0,
                    "expiring_soon": 0,
                    "default_expiry_days": EXPIRY_DAYS.get(cat, EXPIRY_DAYS.get("other", 180)),
                }

            stats["by_category"][cat]["total"] += 1

            if chunk.is_expired:
                stats["expired"] += 1
                stats["by_category"][cat]["expired"] += 1
            elif chunk.expires_at > 0:
                if chunk.expires_at < now:
                    stats["expired"] += 1
                    stats["by_category"][cat]["expired"] += 1
                elif chunk.expires_at < now + 7 * 24 * 3600:
                    stats["expiring_soon"] += 1
                    stats["by_category"][cat]["expiring_soon"] += 1

        return stats

    def set_expiry(self, chunk_id: str, expires_at: float, reason: str = "") -> bool:
        """
        手动设置分块的过期时间

        参数:
            chunk_id: 分块 ID
            expires_at: 过期时间戳
            reason: 过期原因

        返回:
            是否设置成功
        """
        for chunk in self._chunks:
            if chunk.chunk_id == chunk_id:
                chunk.expires_at = expires_at
                chunk.expiry_reason = reason
                self._save_index()
                logger.info(f"设置分块 {chunk_id} 过期时间: {datetime.fromtimestamp(expires_at).isoformat()}")
                return True

        return False

    def extend_expiry(self, chunk_id: str, days: int) -> bool:
        """
        延长分块的过期时间

        参数:
            chunk_id: 分块 ID
            days: 延长的天数

        返回:
            是否延长成功
        """
        for chunk in self._chunks:
            if chunk.chunk_id == chunk_id:
                if chunk.expires_at > 0:
                    chunk.expires_at += days * 24 * 3600
                else:
                    chunk.expires_at = time.time() + days * 24 * 3600
                chunk.is_expired = False
                chunk.expiry_reason = ""
                self._save_index()
                logger.info(f"延长分块 {chunk_id} 过期时间 {days} 天")
                return True

        return False

    # ========== 使用统计方法 ==========

    def _update_access_stats(self, results: List[SearchResult], query: str):
        """
        更新访问统计

        参数:
            results: 检索结果列表
            query: 查询词
        """
        now = time.time()
        updated = False

        for result in results:
            chunk = result.chunk
            # 查找原始分块并更新统计
            for c in self._chunks:
                if c.chunk_id == chunk.chunk_id:
                    c.last_accessed_at = now
                    c.access_count += 1
                    c.last_query = query[:100]  # 限制长度
                    updated = True
                    break

        if updated:
            # 异步保存，避免影响检索性能
            # 这里简化为同步保存，实际可以改为异步
            try:
                self._save_index()
            except Exception as e:
                logger.error(f"保存访问统计失败: {e}")

    def get_usage_stats(self) -> dict:
        """
        获取使用统计

        返回:
            使用统计信息
        """
        if not USAGE_STATS_ENABLED:
            return {"enabled": False}

        now = time.time()
        stats = {
            "enabled": True,
            "total_chunks": len(self._chunks),
            "never_accessed": 0,
            "low_frequency": 0,  # 超过 LOW_FREQUENCY_DAYS 天未访问
            "useless": 0,  # 超过 USELESS_DAYS 天未访问
            "by_access_count": {
                "0": 0,
                "1-5": 0,
                "6-20": 0,
                "21-100": 0,
                "100+": 0,
            },
            "top_accessed": [],  # 访问次数最多的分块
            "recently_accessed": [],  # 最近访问的分块
        }

        for chunk in self._chunks:
            # 统计从未访问的分块
            if chunk.access_count == 0:
                stats["never_accessed"] += 1

            # 统计低频分块
            if chunk.last_accessed_at > 0:
                days_since_access = (now - chunk.last_accessed_at) / (24 * 3600)
                if days_since_access > LOW_FREQUENCY_DAYS:
                    stats["low_frequency"] += 1
                if days_since_access > USELESS_DAYS:
                    stats["useless"] += 1
            else:
                # 从未访问，检查创建时间
                days_since_created = (now - chunk.timestamp) / (24 * 3600) if chunk.timestamp > 0 else 999
                if days_since_created > LOW_FREQUENCY_DAYS:
                    stats["low_frequency"] += 1
                if days_since_created > USELESS_DAYS:
                    stats["useless"] += 1

            # 按访问次数分组
            count = chunk.access_count
            if count == 0:
                stats["by_access_count"]["0"] += 1
            elif count <= 5:
                stats["by_access_count"]["1-5"] += 1
            elif count <= 20:
                stats["by_access_count"]["6-20"] += 1
            elif count <= 100:
                stats["by_access_count"]["21-100"] += 1
            else:
                stats["by_access_count"]["100+"] += 1

        # 访问次数最多的 Top 10
        sorted_by_count = sorted(self._chunks, key=lambda x: x.access_count, reverse=True)[:10]
        stats["top_accessed"] = [
            {
                "chunk_id": c.chunk_id,
                "text_preview": c.text[:100],
                "access_count": c.access_count,
                "last_accessed": datetime.fromtimestamp(c.last_accessed_at).isoformat() if c.last_accessed_at > 0 else None,
            }
            for c in sorted_by_count if c.access_count > 0
        ]

        # 最近访问的 Top 10
        sorted_by_time = sorted(self._chunks, key=lambda x: x.last_accessed_at, reverse=True)[:10]
        stats["recently_accessed"] = [
            {
                "chunk_id": c.chunk_id,
                "text_preview": c.text[:100],
                "access_count": c.access_count,
                "last_accessed": datetime.fromtimestamp(c.last_accessed_at).isoformat() if c.last_accessed_at > 0 else None,
            }
            for c in sorted_by_time if c.last_accessed_at > 0
        ]

        return stats

    def check_maintenance_needed(self) -> dict:
        """
        检查是否需要维护

        返回:
            维护建议
        """
        if not USAGE_STATS_ENABLED:
            return {"enabled": False}

        now = time.time()
        suggestions = {
            "enabled": True,
            "needs_review": [],  # 需要人工审核的知识块
            "low_frequency": [],  # 低频知识块
            "useless": [],  # 无效知识块
            "never_accessed_old": [],  # 从未访问且创建时间较久的知识块
            "summary": "",
        }

        for chunk in self._chunks:
            # 跳过已过期的分块
            if chunk.is_expired:
                continue

            days_since_created = (now - chunk.timestamp) / (24 * 3600) if chunk.timestamp > 0 else 0
            days_since_access = (now - chunk.last_accessed_at) / (24 * 3600) if chunk.last_accessed_at > 0 else None

            # 从未访问且创建时间超过 LOW_FREQUENCY_DAYS
            if chunk.access_count == 0 and days_since_created > LOW_FREQUENCY_DAYS:
                suggestions["never_accessed_old"].append({
                    "chunk_id": chunk.chunk_id,
                    "text_preview": chunk.text[:100],
                    "category": get_category_name(chunk.category) if chunk.category else "其他",
                    "created_days_ago": int(days_since_created),
                    "sender_nick": chunk.sender_nick,
                })

            # 低频知识：超过 LOW_FREQUENCY_DAYS 天未访问
            if days_since_access is not None and days_since_access > LOW_FREQUENCY_DAYS:
                if chunk.access_count < MIN_ACCESS_COUNT:
                    suggestions["needs_review"].append({
                        "chunk_id": chunk.chunk_id,
                        "text_preview": chunk.text[:100],
                        "category": get_category_name(chunk.category) if chunk.category else "其他",
                        "access_count": chunk.access_count,
                        "days_since_access": int(days_since_access),
                        "last_query": chunk.last_query,
                    })
                else:
                    suggestions["low_frequency"].append({
                        "chunk_id": chunk.chunk_id,
                        "text_preview": chunk.text[:100],
                        "access_count": chunk.access_count,
                        "days_since_access": int(days_since_access),
                    })

            # 无效知识：超过 USELESS_DAYS 天未访问
            if days_since_access is not None and days_since_access > USELESS_DAYS:
                suggestions["useless"].append({
                    "chunk_id": chunk.chunk_id,
                    "text_preview": chunk.text[:100],
                    "category": get_category_name(chunk.category) if chunk.category else "其他",
                    "access_count": chunk.access_count,
                    "days_since_access": int(days_since_access),
                })

        # 生成摘要
        total_issues = (
            len(suggestions["needs_review"]) +
            len(suggestions["useless"]) +
            len(suggestions["never_accessed_old"])
        )

        if total_issues == 0:
            suggestions["summary"] = "✅ 知识库状态良好，暂无需要维护的内容"
        else:
            lines = [
                f"⚠️ 发现 {total_issues} 个需要关注的知识块：",
                "",
            ]

            if suggestions["needs_review"]:
                lines.append(f"📋 需要人工审核：{len(suggestions['needs_review'])} 个")
                lines.append(f"   （访问次数少于 {MIN_ACCESS_COUNT} 次，且超过 {LOW_FREQUENCY_DAYS} 天未访问）")

            if suggestions["useless"]:
                lines.append(f"🗑️ 建议清理：{len(suggestions['useless'])} 个")
                lines.append(f"   （超过 {USELESS_DAYS} 天未访问）")

            if suggestions["never_accessed_old"]:
                lines.append(f"❓ 从未访问：{len(suggestions['never_accessed_old'])} 个")
                lines.append(f"   （创建超过 {LOW_FREQUENCY_DAYS} 天，从未被检索到）")

            suggestions["summary"] = "\n".join(lines)

        # 记录操作日志
        self._op_logger.log(OperationLog(
            timestamp=datetime.now().isoformat(),
            operation="maintenance_check",
            result_count=total_issues,
            status="success",
            details=f"需要审核={len(suggestions['needs_review'])}, 低频={len(suggestions['low_frequency'])}, 无效={len(suggestions['useless'])}"
        ))

        return suggestions

    def get_maintenance_report(self) -> str:
        """
        生成维护报告

        返回:
            格式化的维护报告
        """
        suggestions = self.check_maintenance_needed()

        if not suggestions.get("enabled"):
            return "使用统计功能未启用"

        lines = [
            "=" * 60,
            "  知识库维护报告",
            "=" * 60,
            "",
            suggestions["summary"],
            "",
        ]

        if suggestions["needs_review"]:
            lines.append("-" * 60)
            lines.append(f"📋 需要人工审核的知识块（{len(suggestions['needs_review'])} 个）")
            lines.append("-" * 60)
            for i, item in enumerate(suggestions["needs_review"][:20], 1):  # 最多显示20个
                lines.append(f"{i}. [{item['category']}] {item['text_preview']}")
                lines.append(f"   访问次数: {item['access_count']}, 最后访问: {item['days_since_access']} 天前")
                if item['last_query']:
                    lines.append(f"   最后查询: {item['last_query']}")
                lines.append("")

        if suggestions["useless"]:
            lines.append("-" * 60)
            lines.append(f"🗑️ 建议清理的知识块（{len(suggestions['useless'])} 个）")
            lines.append("-" * 60)
            for i, item in enumerate(suggestions["useless"][:20], 1):
                lines.append(f"{i}. [{item['category']}] {item['text_preview']}")
                lines.append(f"   访问次数: {item['access_count']}, 最后访问: {item['days_since_access']} 天前")
                lines.append("")

        if suggestions["never_accessed_old"]:
            lines.append("-" * 60)
            lines.append(f"❓ 从未访问的知识块（{len(suggestions['never_accessed_old'])} 个）")
            lines.append("-" * 60)
            for i, item in enumerate(suggestions["never_accessed_old"][:20], 1):
                lines.append(f"{i}. [{item['category']}] {item['text_preview']}")
                lines.append(f"   创建于 {item['created_days_ago']} 天前, 来源: {item['sender_nick']}")
                lines.append("")

        lines.append("=" * 60)
        lines.append("  维护建议")
        lines.append("=" * 60)
        lines.append("")
        lines.append("1. 对「需要审核」的知识块，建议人工检查内容是否准确、是否有用")
        lines.append("2. 对「建议清理」的知识块，如果确认无用可以删除")
        lines.append("3. 对「从未访问」的知识块，考虑是否需要优化关键词或删除")
        lines.append("4. 定期运行维护检查，保持知识库质量")
        lines.append("")

        return "\n".join(lines)

    def cleanup_low_frequency(self, days: int = None, min_access_count: int = None,
                              dry_run: bool = True) -> dict:
        """
        清理低频知识块

        参数:
            days: 超过多少天未访问（默认使用配置值）
            min_access_count: 最小访问次数（默认使用配置值）
            dry_run: 是否为试运行（不实际删除）

        返回:
            清理结果
        """
        days = days or LOW_FREQUENCY_DAYS
        min_access_count = min_access_count or MIN_ACCESS_COUNT

        now = time.time()
        to_cleanup = []

        for chunk in self._chunks:
            if chunk.is_expired:
                continue

            days_since_access = (now - chunk.last_accessed_at) / (24 * 3600) if chunk.last_accessed_at > 0 else None
            days_since_created = (now - chunk.timestamp) / (24 * 3600) if chunk.timestamp > 0 else 0

            # 从未访问
            if chunk.access_count == 0 and days_since_created > days:
                to_cleanup.append(chunk)
            # 访问次数少且超过指定天数未访问
            elif chunk.access_count < min_access_count and days_since_access and days_since_access > days:
                to_cleanup.append(chunk)

        result = {
            "total_candidates": len(to_cleanup),
            "dry_run": dry_run,
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "text_preview": c.text[:100],
                    "category": c.category,
                    "access_count": c.access_count,
                }
                for c in to_cleanup[:100]  # 最多返回100个
            ],
        }

        if not dry_run and to_cleanup:
            # 实际删除
            cleanup_ids = {c.chunk_id for c in to_cleanup}
            self._chunks = [c for c in self._chunks if c.chunk_id not in cleanup_ids]
            self._rebuild_embeddings()
            self._build_keyword_index()
            self._save_index()
            result["deleted"] = len(to_cleanup)

            # 记录操作日志
            self._op_logger.log(OperationLog(
                timestamp=datetime.now().isoformat(),
                operation="cleanup_low_frequency",
                result_count=len(to_cleanup),
                status="success",
                details=f"清理了 {len(to_cleanup)} 个低频知识块"
            ))

        return result

    async def _semantic_search(self, query: str, top_k: int) -> List[SearchResult]:
        """语义检索"""
        # 清洗查询文本
        cleaned_query = clean_for_indexing(query)
        query_embedding = await get_embeddings([cleaned_query])
        if query_embedding is None or self._embeddings is None:
            return []

        similarities = cosine_similarity(query_embedding[0], self._embeddings)

        # 取 Top-K
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score >= SIMILARITY_THRESHOLD:
                results.append(SearchResult(
                    chunk=self._chunks[idx],
                    score=score,
                    match_type="semantic",
                ))

        return results

    def _keyword_search(self, query: str, top_k: int) -> List[SearchResult]:
        """关键词检索（使用倒排索引）"""
        # 清洗查询文本
        cleaned_query = clean_text(query)
        query_lower = cleaned_query.lower()
        query_keywords = extract_keywords(cleaned_query, top_n=10)

        # 改进中文分词：将长词拆分为更小的单元
        # 例如 "张教授的个人信息" -> ["张教授", "个人", "信息"]
        extended_keywords = list(query_keywords)
        for keyword in query_keywords:
            # 如果关键词长度大于 2，尝试拆分
            if len(keyword) > 2:
                # 按常见后缀拆分
                suffixes = ['信息', '资料', '数据', '情况', '详情', '介绍', '简介']
                for suffix in suffixes:
                    if keyword.endswith(suffix) and len(keyword) > len(suffix):
                        prefix = keyword[:-len(suffix)]
                        if len(prefix) >= 2:
                            extended_keywords.append(prefix)
                        break

                # 按常见前缀拆分
                prefixes = ['张', '王', '李', '刘', '陈', '杨', '黄', '赵', '周', '吴']
                for prefix in prefixes:
                    if keyword.startswith(prefix) and len(keyword) > len(prefix):
                        suffix = keyword[len(prefix):]
                        if len(suffix) >= 2:
                            extended_keywords.append(suffix)
                        break

                # 按"的"拆分
                if '的' in keyword:
                    parts = keyword.split('的')
                    for part in parts:
                        if len(part) >= 2:
                            extended_keywords.append(part)

        # 去重
        extended_keywords = list(set(extended_keywords))

        # 使用倒排索引快速定位候选文档
        candidate_indices: Set[int] = set()
        for keyword in extended_keywords:
            if keyword in self._keyword_index:
                candidate_indices.update(self._keyword_index[keyword])

        # 如果没有命中倒排索引，回退到全量扫描
        if not candidate_indices:
            candidate_indices = set(range(len(self._chunks)))

        # 改进：如果查询包含"老师"、"教授"等通用教师词，
        # 添加包含这些词的文档到候选集合
        teacher_keywords = ['老师', '教授', '教师', '导师']
        query_teacher_keywords = [kw for kw in teacher_keywords if kw in query_lower]

        if query_teacher_keywords:
            # 添加包含教师关键词的文档到候选集合
            for i, chunk in enumerate(self._chunks):
                chunk_lower = chunk.text.lower()
                if any(kw in chunk_lower for kw in teacher_keywords):
                    candidate_indices.add(i)

        # 计算匹配分数
        results = []
        for idx in candidate_indices:
            chunk = self._chunks[idx]
            chunk_lower = chunk.text.lower()
            score = 0.0
            highlights = []

            # 完全包含查询
            if query_lower in chunk_lower:
                score += 1.0
                highlights.append(query)
            else:
                # 关键词匹配
                matched_keywords = 0
                for keyword in extended_keywords:
                    if keyword in chunk_lower:
                        matched_keywords += 1
                        highlights.append(keyword)
                if extended_keywords:
                    score += matched_keywords / len(extended_keywords) * 0.8

            # 如果是 PDF 文件，给额外的加分
            if chunk.file_name and chunk.file_name.endswith('.pdf'):
                score += 0.1

            # 课表相关查询优化：如果查询包含"课"、"课程"、"课表"等关键词
            # 且内容包含课表信息（如"周"、"节"、"教室"等），给额外加分
            schedule_query_keywords = ['课', '课程', '课表', '上课', '教室', '节']
            schedule_content_keywords = ['周', '节', '教室', '教学楼', '工科楼', '线下授课', '专业课']
            if any(kw in query_lower for kw in schedule_query_keywords):
                if any(kw in chunk_lower for kw in schedule_content_keywords):
                    score += 0.3  # 课表内容加分

            # 教师相关查询优化：如果查询包含教师姓名或通用教师词
            # 且内容包含该教师的信息，给额外加分
            teacher_match = re.search(r'(张|王|李|刘|陈|杨|黄|赵|周|吴)(教授|老师|医生|主任|院长)', query_lower)
            has_teacher_keyword = any(kw in query_lower for kw in ['老师', '教授', '教师', '导师'])

            if teacher_match or has_teacher_keyword:
                # 检查内容是否包含教师相关信息
                teacher_content_keywords = ['教授', '老师', '教师', '导师', '年龄', '学历', '办公室', '研究方向', '从教', '博士', '硕士', '学院']
                if any(kw in chunk_lower for kw in teacher_content_keywords):
                    # 检查是否是课表内容（包含"周"、"节"等）
                    if any(kw in chunk_lower for kw in ['周', '节', '教室', '教学楼']):
                        score += 0.4  # 教师课表内容加分
                    # 检查是否是个人信息内容（包含"年龄"、"学历"、"办公室"等）
                    elif any(kw in chunk_lower for kw in ['年龄', '学历', '办公室', '研究方向', '从教', '博士', '硕士']):
                        score += 0.5  # 教师个人信息内容加分（提高权重）
                    # 其他包含教师姓名的内容
                    else:
                        score += 0.2  # 教师相关内容加分

            # 个人信息相关查询优化：如果查询包含"个人信息"、"简介"、"资料"等关键词
            # 且内容包含个人信息相关内容，给额外加分
            personal_query_keywords = ['个人信息', '简介', '资料', '介绍', '详情']
            personal_content_keywords = ['年龄', '学历', '办公室', '研究方向', '从教', '博士', '硕士', '学院']
            if any(kw in query_lower for kw in personal_query_keywords):
                if any(kw in chunk_lower for kw in personal_content_keywords):
                    score += 0.3  # 个人信息内容加分

            if score > 0.1:
                results.append(SearchResult(
                    chunk=chunk,
                    score=score,
                    match_type="keyword",
                    highlights=highlights,
                ))

        # 按分数降序排列
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    async def _hybrid_search(self, query: str, top_k: int) -> List[SearchResult]:
        """混合检索：结合语义和关键词"""
        # 并行执行两种检索
        semantic_results = await self._semantic_search(query, top_k * 2)
        keyword_results = self._keyword_search(query, top_k * 2)

        # 合并结果
        seen_chunks: Dict[str, SearchResult] = {}

        # 语义检索结果（权重 0.6）
        for result in semantic_results:
            chunk_id = result.chunk.chunk_id
            seen_chunks[chunk_id] = SearchResult(
                chunk=result.chunk,
                score=result.score * 0.6,
                match_type="semantic",
            )

        # 关键词检索结果（权重 0.6，提高权重以保留加分效果）
        for result in keyword_results:
            chunk_id = result.chunk.chunk_id
            if chunk_id in seen_chunks:
                # 已存在，累加分数
                existing = seen_chunks[chunk_id]
                existing.score += result.score * 0.6
                existing.match_type = "hybrid"
                existing.highlights = list(set(
                    existing.highlights + result.highlights
                ))
            else:
                seen_chunks[chunk_id] = SearchResult(
                    chunk=result.chunk,
                    score=result.score * 0.6,
                    match_type="keyword",
                    highlights=result.highlights,
                )

        # 排序并返回 Top-K
        results = sorted(seen_chunks.values(), key=lambda x: x.score, reverse=True)

        # 如果语义搜索没有结果，但关键词搜索有结果，确保返回关键词搜索的结果
        if not semantic_results and keyword_results:
            # 返回关键词搜索的结果，但使用更高的权重
            return [SearchResult(
                chunk=result.chunk,
                score=result.score * 0.8,  # 提高权重
                match_type="keyword",
                highlights=result.highlights,
            ) for result in keyword_results[:top_k]]

        return results[:top_k]

    def delete_by_source(self, source_id: str,
                         user_id: str = "", user_nick: str = "") -> int:
        """
        删除指定来源的所有分块

        参数:
            source_id: 来源ID
            user_id: 用户 ID（用于日志）
            user_nick: 用户昵称（用于日志）

        返回:
            删除的分块数量
        """
        original_count = len(self._chunks)
        self._chunks = [c for c in self._chunks if c.source_id != source_id]

        # 重建索引
        if len(self._chunks) < original_count:
            self._rebuild_embeddings()
            self._build_keyword_index()
            self._save_index()

        deleted = original_count - len(self._chunks)
        if deleted > 0:
            logger.info(f"删除来源 {source_id} 的 {deleted} 个分块")

        # 记录操作日志
        self._op_logger.log(OperationLog(
            timestamp=datetime.now().isoformat(),
            operation="delete",
            user_id=user_id,
            user_nick=user_nick,
            source_id=source_id,
            result_count=deleted,
            status="success" if deleted > 0 else "not_found",
            details=f"删除 {deleted} 个分块" if deleted > 0 else "未找到匹配的分块"
        ))

        return deleted

    def _rebuild_embeddings(self):
        """重建向量索引"""
        if not self._chunks:
            self._embeddings = None
            return

        # 同步调用，因为这是在删除时调用
        try:
            model = _get_local_embedding_model()
            if model is not None:
                texts = [c.text for c in self._chunks]
                self._embeddings = model.encode(texts, normalize_embeddings=True)
                self._embeddings = np.array(self._embeddings, dtype=np.float32)
        except Exception as e:
            logger.error(f"重建向量索引失败: {e}")
            self._embeddings = None

    def get_stats(self) -> KnowledgeStats:
        """获取知识库统计信息"""
        stats = KnowledgeStats()
        stats.total_chunks = len(self._chunks)

        # 统计来源类型、发送者、分类、溯源信息
        source_types: Dict[str, int] = {}
        senders: Dict[str, int] = {}
        categories: Dict[str, int] = {}
        conversations: Dict[str, int] = {}
        conversation_types: Dict[str, int] = {}
        file_types: Dict[str, int] = {}
        timestamps = []

        for chunk in self._chunks:
            source_types[chunk.source_type] = source_types.get(chunk.source_type, 0) + 1
            if chunk.sender_nick:
                senders[chunk.sender_nick] = senders.get(chunk.sender_nick, 0) + 1
            if chunk.timestamp:
                timestamps.append(chunk.timestamp)
            # 统计分类
            cat = chunk.category if chunk.category else "other"
            categories[cat] = categories.get(cat, 0) + 1
            # 溯源统计
            if chunk.conversation_name:
                conversations[chunk.conversation_name] = conversations.get(chunk.conversation_name, 0) + 1
            elif chunk.conversation_id:
                conversations[chunk.conversation_id] = conversations.get(chunk.conversation_id, 0) + 1
            conv_type = chunk.conversation_type or "unknown"
            conversation_types[conv_type] = conversation_types.get(conv_type, 0) + 1
            if chunk.file_type:
                file_types[chunk.file_type] = file_types.get(chunk.file_type, 0) + 1

        stats.source_types = source_types
        stats.top_senders = sorted(senders.items(), key=lambda x: x[1], reverse=True)[:10]
        stats.categories = {get_category_name(k): v for k, v in sorted(categories.items(), key=lambda x: -x[1])}
        stats.conversations = dict(sorted(conversations.items(), key=lambda x: -x[1])[:10])
        stats.conversation_types = conversation_types
        stats.file_types = file_types

        if timestamps:
            stats.date_range = {
                "earliest": datetime.fromtimestamp(min(timestamps)).isoformat(),
                "latest": datetime.fromtimestamp(max(timestamps)).isoformat(),
            }

        # 计算索引大小
        chunks_file = os.path.join(self._index_dir, "chunks.json")
        embeddings_file = os.path.join(self._index_dir, "embeddings.npy")
        total_size = 0
        if os.path.exists(chunks_file):
            total_size += os.path.getsize(chunks_file)
        if os.path.exists(embeddings_file):
            total_size += os.path.getsize(embeddings_file)
        stats.index_size_mb = total_size / (1024 * 1024)

        # 统计消息数
        if os.path.exists(self._messages_dir):
            message_files = 0
            for day_dir in os.listdir(self._messages_dir):
                day_path = os.path.join(self._messages_dir, day_dir)
                if os.path.isdir(day_path):
                    message_files += len([f for f in os.listdir(day_path) if f.endswith('.json')])
            stats.total_messages = message_files

        return stats

    def export_chunks(self, output_file: str, format: str = "json",
                      user_id: str = "", user_nick: str = ""):
        """
        导出知识库分块

        参数:
            output_file: 输出文件路径
            format: 导出格式 ("json", "csv")
            user_id: 用户 ID（用于日志）
            user_nick: 用户昵称（用于日志）
        """
        if format == "json":
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump([asdict(c) for c in self._chunks], f,
                          ensure_ascii=False, indent=2)
        elif format == "csv":
            import csv
            with open(output_file, "w", encoding="utf-8", newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["chunk_id", "text", "source_type", "sender_nick",
                                 "timestamp", "keywords"])
                for chunk in self._chunks:
                    writer.writerow([
                        chunk.chunk_id,
                        chunk.text[:200],  # 截断长文本
                        chunk.source_type,
                        chunk.sender_nick,
                        datetime.fromtimestamp(chunk.timestamp).isoformat() if chunk.timestamp else "",
                        ",".join(chunk.keywords),
                    ])

        logger.info(f"导出知识库到 {output_file}，共 {len(self._chunks)} 个分块")

        # 记录操作日志
        self._op_logger.log(OperationLog(
            timestamp=datetime.now().isoformat(),
            operation="export",
            user_id=user_id,
            user_nick=user_nick,
            result_count=len(self._chunks),
            status="success",
            details=f"导出到 {output_file}, 格式={format}"
        ))

    # ========== 分类管理 ==========

    def get_categories(self) -> dict:
        """
        获取所有可用的分类及其数量

        返回:
            分类字典，key 为分类名称，value 为数量
        """
        categories: Dict[str, int] = {}
        for chunk in self._chunks:
            cat = chunk.category if chunk.category else "other"
            categories[cat] = categories.get(cat, 0) + 1

        # 转换为中文名称
        return {get_category_name(k): v for k, v in sorted(categories.items(), key=lambda x: -x[1])}

    def get_available_category_ids(self) -> list:
        """
        获取所有可用的分类 ID 列表

        返回:
            分类 ID 列表
        """
        categories = set()
        for chunk in self._chunks:
            if chunk.category:
                categories.add(chunk.category)
        return sorted(list(categories))

    # ========== 知识溯源方法 ==========

    def trace_chunk(self, chunk_id: str) -> dict:
        """
        追溯单个分块的来源

        参数:
            chunk_id: 分块 ID

        返回:
            溯源信息
        """
        for chunk in self._chunks:
            if chunk.chunk_id == chunk_id:
                return self._format_trace_info(chunk)

        return {"error": f"未找到分块: {chunk_id}"}

    def trace_by_source(self, source_id: str) -> List[dict]:
        """
        追溯同一来源的所有分块

        参数:
            source_id: 来源 ID（消息 ID 或文件 ID）

        返回:
            溯源信息列表
        """
        results = []
        for chunk in self._chunks:
            if chunk.source_id == source_id:
                results.append(self._format_trace_info(chunk))

        return results

    def trace_by_sender(self, sender_id: str = None, sender_nick: str = None,
                        limit: int = 100) -> List[dict]:
        """
        追溯同一发送者的所有知识

        参数:
            sender_id: 发送者 ID
            sender_nick: 发送者昵称
            limit: 返回数量限制

        返回:
            溯源信息列表
        """
        results = []
        for chunk in self._chunks:
            if sender_id and chunk.sender_id == sender_id:
                results.append(self._format_trace_info(chunk))
            elif sender_nick and chunk.sender_nick == sender_nick:
                results.append(self._format_trace_info(chunk))

            if len(results) >= limit:
                break

        return results

    def trace_by_conversation(self, conversation_id: str,
                              limit: int = 100) -> List[dict]:
        """
        追溯同一会话的所有知识

        参数:
            conversation_id: 会话 ID
            limit: 返回数量限制

        返回:
            溯源信息列表
        """
        results = []
        for chunk in self._chunks:
            if chunk.conversation_id == conversation_id:
                results.append(self._format_trace_info(chunk))

            if len(results) >= limit:
                break

        return results

    def _format_trace_info(self, chunk: DocumentChunk) -> dict:
        """
        格式化溯源信息

        参数:
            chunk: 文档分块

        返回:
            格式化的溯源信息
        """
        return {
            "chunk_id": chunk.chunk_id,
            "text_preview": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
            "category": get_category_name(chunk.category) if chunk.category else "其他",
            "source": {
                "type": chunk.source_type,
                "id": chunk.source_id,
                "file_name": chunk.file_name,
                "file_type": chunk.file_type,
                "file_size": chunk.file_size,
            },
            "sender": {
                "id": chunk.sender_id,
                "nick": chunk.sender_nick,
                "dept": chunk.sender_dept,
            },
            "conversation": {
                "id": chunk.conversation_id,
                "type": chunk.conversation_type,
                "name": chunk.conversation_name,
            },
            "timing": {
                "created": datetime.fromtimestamp(chunk.timestamp).isoformat() if chunk.timestamp else None,
                "message_time": datetime.fromtimestamp(chunk.message_timestamp).isoformat() if chunk.message_timestamp else None,
                "expires_at": datetime.fromtimestamp(chunk.expires_at).isoformat() if chunk.expires_at > 0 else None,
                "is_expired": chunk.is_expired,
            },
            "version": {
                "current": chunk.version,
                "is_latest": chunk.is_latest,
                "replaces_id": chunk.replaces_id,
            },
            "chunking": {
                "index": chunk.chunk_index,
                "total": chunk.total_chunks,
            },
        }

    def get_trace_stats(self) -> dict:
        """
        获取溯源统计信息

        返回:
            溯源统计
        """
        stats = {
            "total_chunks": len(self._chunks),
            "by_source_type": {},
            "by_sender": {},
            "by_conversation_type": {},
            "by_conversation": {},
            "top_senders": [],
            "top_conversations": [],
        }

        sender_counts: Dict[str, int] = {}
        conversation_counts: Dict[str, int] = {}
        conversation_type_counts: Dict[str, int] = {}

        for chunk in self._chunks:
            # 按来源类型统计
            source_type = chunk.source_type or "unknown"
            stats["by_source_type"][source_type] = stats["by_source_type"].get(source_type, 0) + 1

            # 按发送者统计
            if chunk.sender_nick:
                sender_counts[chunk.sender_nick] = sender_counts.get(chunk.sender_nick, 0) + 1

            # 按会话类型统计
            conv_type = chunk.conversation_type or "unknown"
            conversation_type_counts[conv_type] = conversation_type_counts.get(conv_type, 0) + 1

            # 按会话统计
            if chunk.conversation_name:
                conversation_counts[chunk.conversation_name] = conversation_counts.get(chunk.conversation_name, 0) + 1
            elif chunk.conversation_id:
                conversation_counts[chunk.conversation_id] = conversation_counts.get(chunk.conversation_id, 0) + 1

        stats["by_sender"] = sender_counts
        stats["by_conversation_type"] = conversation_type_counts
        stats["by_conversation"] = conversation_counts
        stats["top_senders"] = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        stats["top_conversations"] = sorted(conversation_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return stats

    def export_with_trace(self, output_file: str, format: str = "json",
                          include_trace: bool = True) -> int:
        """
        导出知识库（包含溯源信息）

        参数:
            output_file: 输出文件路径
            format: 导出格式 ("json", "csv")
            include_trace: 是否包含溯源信息

        返回:
            导出的分块数量
        """
        if format == "json":
            data = []
            for chunk in self._chunks:
                chunk_data = asdict(chunk)
                if include_trace:
                    chunk_data["trace"] = self._format_trace_info(chunk)
                data.append(chunk_data)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        elif format == "csv":
            import csv
            with open(output_file, "w", encoding="utf-8-sig", newline='') as f:
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
                for chunk in self._chunks:
                    writer.writerow([
                        chunk.chunk_id,
                        chunk.text[:500],  # 截断长文本
                        get_category_name(chunk.category) if chunk.category else "其他",
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

        logger.info(f"导出知识库到 {output_file}，共 {len(self._chunks)} 个分块")

        # 记录操作日志
        self._op_logger.log(OperationLog(
            timestamp=datetime.now().isoformat(),
            operation="export",
            result_count=len(self._chunks),
            status="success",
            details=f"导出到 {output_file}, 格式={format}, 包含溯源={include_trace}"
        ))

        return len(self._chunks)

    # ========== 主动智能方法 ==========

    def get_notifier(self):
        """获取通知器实例"""
        return self._notifier

    def get_reminder(self):
        """获取提醒器实例"""
        return self._reminder

    def get_feedback_tracker(self):
        """获取反馈追踪器实例"""
        return self._feedback_tracker

    def get_search_suggester(self):
        """获取搜索建议器实例"""
        return self._search_suggester

    async def subscribe_notifications(self, user_id: str, categories: list,
                                       channels: list = None, user_nick: str = "",
                                       conversation_id: str = ""):
        """
        订阅变更通知

        参数:
            user_id: 用户ID
            categories: 关注的类别（schedule/exam/homework/...）
            channels: 通知渠道（dingtalk/wechat/email）
            user_nick: 用户昵称
            conversation_id: 会话ID
        """
        if self._notifier:
            self._notifier.subscribe(
                user_id=user_id,
                categories=categories,
                channels=channels or ["dingtalk"],
                user_nick=user_nick,
                conversation_id=conversation_id,
            )

    async def unsubscribe_notifications(self, user_id: str):
        """取消订阅变更通知"""
        if self._notifier:
            self._notifier.unsubscribe(user_id)

    async def check_and_send_reminders(self):
        """检查并发送提醒"""
        if self._reminder:
            reminders = await self._reminder.check_reminders()
            if reminders:
                await self._reminder.send_reminders(reminders)
                return len(reminders)
        return 0

    def record_feedback(self, chunk_id: str, user_id: str,
                       query: str, feedback_type: str,
                       dwell_time: float = 0.0):
        """
        记录用户反馈

        参数:
            chunk_id: 知识块ID
            user_id: 用户ID
            query: 查询词
            feedback_type: 反馈类型（positive/negative/quick_leave）
            dwell_time: 停留时间（秒）
        """
        if self._feedback_tracker:
            self._feedback_tracker.record_feedback(
                chunk_id=chunk_id,
                user_id=user_id,
                query=query,
                feedback_type=feedback_type,
                dwell_time=dwell_time,
            )

    def get_quality_report(self) -> dict:
        """获取知识质量报告"""
        if self._feedback_tracker:
            return self._feedback_tracker.get_quality_report()
        return {"enabled": False}

    def get_low_quality_chunks(self, threshold: float = 0.3,
                                min_feedbacks: int = 3) -> list:
        """获取低质量知识块"""
        if self._feedback_tracker:
            return self._feedback_tracker.get_low_quality_chunks(threshold, min_feedbacks)
        return []

    def get_search_suggestions(self, partial_query: str,
                                top_k: int = 5) -> list:
        """获取检索建议"""
        if self._search_suggester:
            suggestions = self._search_suggester.suggest(partial_query, top_k)
            return [s.__dict__ for s in suggestions]
        return []

    def correct_query(self, query: str) -> dict:
        """纠错建议"""
        if self._search_suggester:
            return self._search_suggester.correct(query)
        return {"original": query, "corrected": query, "corrections": [], "has_correction": False}

    # ========== 权重优化方法 ==========

    def get_weight_optimizer(self):
        """获取权重优化器实例"""
        return self._weight_optimizer

    def get_current_weights(self) -> dict:
        """获取当前检索权重"""
        if hasattr(self, '_weight_optimizer') and self._weight_optimizer:
            return self._weight_optimizer.get_current_weights()
        return {"semantic": 0.6, "keyword": 0.4}

    def set_search_weights(self, semantic: float, keyword: float):
        """手动设置检索权重"""
        if hasattr(self, '_weight_optimizer') and self._weight_optimizer:
            self._weight_optimizer.set_weights(semantic, keyword)

    def get_weight_optimization_report(self) -> dict:
        """获取权重优化报告"""
        if hasattr(self, '_weight_optimizer') and self._weight_optimizer:
            return self._weight_optimizer.get_optimization_report()
        return {"enabled": False}

    # ========== 快照管理方法 ==========

    def get_snapshot_manager(self):
        """获取快照管理器实例"""
        return self._snapshot_manager

    def create_snapshot(self, description: str = "",
                       tags: list = None) -> str:
        """
        创建知识库快照

        参数:
            description: 快照描述
            tags: 标签列表

        返回:
            快照ID
        """
        if hasattr(self, '_snapshot_manager') and self._snapshot_manager:
            return self._snapshot_manager.create_snapshot(description, tags)
        raise RuntimeError("快照管理器未初始化")

    def list_snapshots(self) -> list:
        """列出所有快照"""
        if hasattr(self, '_snapshot_manager') and self._snapshot_manager:
            return self._snapshot_manager.list_snapshots()
        return []

    def restore_snapshot(self, snapshot_id: str,
                        dry_run: bool = True) -> dict:
        """
        恢复快照

        参数:
            snapshot_id: 快照ID
            dry_run: 是否为试运行

        返回:
            恢复结果
        """
        if hasattr(self, '_snapshot_manager') and self._snapshot_manager:
            return self._snapshot_manager.restore_snapshot(snapshot_id, dry_run)
        return {"success": False, "error": "快照管理器未初始化"}

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """删除快照"""
        if hasattr(self, '_snapshot_manager') and self._snapshot_manager:
            return self._snapshot_manager.delete_snapshot(snapshot_id)
        return False

    def compare_snapshots(self, snapshot_id1: str,
                         snapshot_id2: str = None) -> dict:
        """比较快照差异"""
        if hasattr(self, '_snapshot_manager') and self._snapshot_manager:
            return self._snapshot_manager.compare_snapshots(snapshot_id1, snapshot_id2)
        return {"error": "快照管理器未初始化"}

    def cleanup_old_snapshots(self, keep_count: int = 10,
                              keep_days: int = 30) -> int:
        """清理旧快照"""
        if hasattr(self, '_snapshot_manager') and self._snapshot_manager:
            return self._snapshot_manager.cleanup_old_snapshots(keep_count, keep_days)
        return 0

    # ========== 批量导入导出方法 ==========

    def get_batch_importer(self):
        """获取批量导入器实例"""
        return self._batch_importer

    def get_batch_exporter(self):
        """获取批量导出器实例"""
        return self._batch_exporter

    async def import_from_csv(self, file_path: str,
                              data_type: str = "auto",
                              encoding: str = "utf-8-sig",
                              mapping: dict = None) -> dict:
        """
        从 CSV 导入数据

        参数:
            file_path: CSV 文件路径
            data_type: 数据类型（auto/schedule/exam/contact/text）
            encoding: 文件编码
            mapping: 字段映射

        返回:
            导入结果
        """
        if hasattr(self, '_batch_importer') and self._batch_importer:
            result = await self._batch_importer.import_from_csv(
                file_path, data_type, encoding, mapping
            )
            return result.__dict__
        return {"success": False, "error": "批量导入器未初始化"}

    async def import_from_excel(self, file_path: str,
                                data_type: str = "auto",
                                sheet_name: str = None,
                                mapping: dict = None) -> dict:
        """
        从 Excel 导入数据

        参数:
            file_path: Excel 文件路径
            data_type: 数据类型
            sheet_name: 工作表名称
            mapping: 字段映射

        返回:
            导入结果
        """
        if hasattr(self, '_batch_importer') and self._batch_importer:
            result = await self._batch_importer.import_from_excel(
                file_path, data_type, sheet_name, mapping
            )
            return result.__dict__
        return {"success": False, "error": "批量导入器未初始化"}

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
        if hasattr(self, '_batch_exporter') and self._batch_exporter:
            return self._batch_exporter.export_to_csv(output_path, data_type, include_trace)
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
        if hasattr(self, '_batch_exporter') and self._batch_exporter:
            return self._batch_exporter.export_to_excel(output_path, data_type, include_trace)
        return 0

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
        if hasattr(self, '_batch_exporter') and self._batch_exporter:
            return self._batch_exporter.export_report(output_path, report_type)
        return ""

    # ========== 多模态处理方法 ==========

    def get_ocr_engine(self):
        """获取 OCR 引擎实例"""
        return self._ocr_engine

    def get_file_parser(self):
        """获取文件解析器实例"""
        return self._file_parser

    async def recognize_image_text(self, image_path: str,
                                    strategy: str = None) -> dict:
        """
        识别图片中的文字

        参数:
            image_path: 图片路径
            strategy: OCR 策略（local/api/llm）

        返回:
            {
                "text": "识别的文字",
                "confidence": 0.95,
                "regions": [...],
                "strategy": "llm"
            }
        """
        if hasattr(self, '_ocr_engine') and self._ocr_engine:
            result = await self._ocr_engine.recognize(image_path, strategy)
            return {
                "text": result.text,
                "confidence": result.confidence,
                "regions": result.regions,
                "strategy": result.strategy,
                "error": result.error,
            }
        return {"error": "OCR 引擎未初始化"}

    async def parse_file_deep(self, file_path: str,
                               extract_tables: bool = True) -> dict:
        """
        深度解析文件

        参数:
            file_path: 文件路径
            extract_tables: 是否提取表格

        返回:
            {
                "text": "全文文本",
                "tables": [...],
                "images": [...],
                "headers": [...],
                "footers": [...],
                "metadata": {...},
                "structure": {...}
            }
        """
        if hasattr(self, '_file_parser') and self._file_parser:
            result = await self._file_parser.parse(file_path, extract_tables)
            return {
                "text": result.text,
                "tables": result.tables,
                "images": result.images,
                "headers": result.headers,
                "footers": result.footers,
                "metadata": result.metadata,
                "structure": result.structure,
                "error": result.error,
            }
        return {"error": "文件解析器未初始化"}

    async def add_image_to_knowledge(self, image_path: str,
                                      source_id: str = None,
                                      sender_id: str = "",
                                      sender_nick: str = "",
                                      conversation_id: str = "",
                                      tags: list = None) -> dict:
        """
        将图片添加到知识库（自动 OCR）

        参数:
            image_path: 图片路径
            source_id: 来源ID
            sender_id: 发送者ID
            sender_nick: 发送者昵称
            conversation_id: 会话ID
            tags: 标签

        返回:
            添加结果
        """
        if not hasattr(self, '_ocr_engine') or not self._ocr_engine:
            return {"error": "OCR 引擎未初始化"}

        # 执行 OCR
        ocr_result = await self._ocr_engine.recognize(image_path)

        if ocr_result.error:
            return {"error": ocr_result.error}

        if not ocr_result.text.strip():
            return {"error": "未识别到文字"}

        # 添加到知识库
        source_id = source_id or f"img_{int(time.time())}"
        chunks = await self.add_message(
            text=ocr_result.text,
            source_type="image",
            source_id=source_id,
            sender_id=sender_id,
            sender_nick=sender_nick,
            conversation_id=conversation_id,
            file_name=os.path.basename(image_path),
            tags=tags or ["image", "ocr"],
        )

        return {
            "success": True,
            "text": ocr_result.text,
            "confidence": ocr_result.confidence,
            "chunks_count": len(chunks),
        }

    async def add_file_to_knowledge(self, file_path: str,
                                     source_id: str = None,
                                     sender_id: str = "",
                                     sender_nick: str = "",
                                     conversation_id: str = "",
                                     tags: list = None) -> dict:
        """
        将文件添加到知识库（深度解析）

        参数:
            file_path: 文件路径
            source_id: 来源ID
            sender_id: 发送者ID
            sender_nick: 发送者昵称
            conversation_id: 会话ID
            tags: 标签

        返回:
            添加结果
        """
        if not hasattr(self, '_file_parser') or not self._file_parser:
            return {"error": "文件解析器未初始化"}

        # 深度解析文件
        parse_result = await self._file_parser.parse(file_path)

        if parse_result.error:
            return {"error": parse_result.error}

        if not parse_result.text.strip():
            return {"error": "文件内容为空"}

        # 添加到知识库
        source_id = source_id or f"file_{int(time.time())}"
        chunks = await self.add_message(
            text=parse_result.text,
            source_type="file",
            source_id=source_id,
            sender_id=sender_id,
            sender_nick=sender_nick,
            conversation_id=conversation_id,
            file_name=os.path.basename(file_path),
            tags=tags or ["file"],
        )

        # 保存结构化数据（如果有表格）
        if parse_result.tables:
            existing_tables = self.get_structured_data("tables")
            existing_tables.extend(parse_result.tables)
            self.save_structured_data("tables", existing_tables)

        return {
            "success": True,
            "text_length": len(parse_result.text),
            "tables_count": len(parse_result.tables),
            "chunks_count": len(chunks),
            "metadata": parse_result.metadata,
        }

    # ========== 反馈循环方法 ==========

    def get_feedback_collector(self):
        """获取反馈收集器实例"""
        return self._feedback_collector

    def record_search_feedback(self, query: str, user_id: str,
                              results_count: int, clicked_index: int = -1,
                              clicked_chunk_id: str = ""):
        """
        记录检索反馈

        参数:
            query: 查询词
            user_id: 用户ID
            results_count: 结果数量
            clicked_index: 点击的结果索引
            clicked_chunk_id: 点击的知识块ID
        """
        if hasattr(self, '_feedback_collector') and self._feedback_collector:
            self._feedback_collector.record_search(
                query=query,
                user_id=user_id,
                results_count=results_count,
                clicked_index=clicked_index,
                clicked_chunk_id=clicked_chunk_id,
            )

    def record_user_click(self, query: str, user_id: str,
                         clicked_index: int, clicked_chunk_id: str,
                         dwell_time: float):
        """
        记录用户点击

        参数:
            query: 查询词
            user_id: 用户ID
            clicked_index: 点击的结果索引
            clicked_chunk_id: 点击的知识块ID
            dwell_time: 停留时间
        """
        if hasattr(self, '_feedback_collector') and self._feedback_collector:
            self._feedback_collector.record_click(
                query=query,
                user_id=user_id,
                clicked_index=clicked_index,
                clicked_chunk_id=clicked_chunk_id,
                dwell_time=dwell_time,
            )

    def record_query_refinement(self, original_query: str,
                                new_query: str, user_id: str):
        """
        记录查询优化

        参数:
            original_query: 原始查询
            new_query: 新查询
            user_id: 用户ID
        """
        if hasattr(self, '_feedback_collector') and self._feedback_collector:
            self._feedback_collector.record_refinement(
                original_query=original_query,
                new_query=new_query,
                user_id=user_id,
            )

    def get_search_feedback_stats(self, days: int = 30) -> dict:
        """获取检索反馈统计"""
        if hasattr(self, '_feedback_collector') and self._feedback_collector:
            return self._feedback_collector.get_feedback_stats(days)
        return {"enabled": False}

    def get_search_failure_stats(self, days: int = 30) -> dict:
        """获取检索失败统计"""
        if hasattr(self, '_feedback_collector') and self._feedback_collector:
            return self._feedback_collector.get_failure_stats(days)
        return {"enabled": False}

    def analyze_knowledge_gaps(self, days: int = 30) -> list:
        """分析知识缺口"""
        if hasattr(self, '_feedback_collector') and self._feedback_collector:
            gaps = self._feedback_collector.analyze_knowledge_gaps(days)
            return [
                {
                    "topic": gap.topic,
                    "frequency": gap.frequency,
                    "related_queries": gap.related_queries,
                    "suggestion": gap.suggestion,
                }
                for gap in gaps
            ]
        return []

    def get_improvement_suggestions(self) -> list:
        """获取改进建议"""
        if hasattr(self, '_feedback_collector') and self._feedback_collector:
            return self._feedback_collector.get_improvement_suggestions()
        return []

    def get_feedback_report(self, days: int = 30) -> dict:
        """获取反馈报告"""
        if hasattr(self, '_feedback_collector') and self._feedback_collector:
            return self._feedback_collector.get_report(days)
        return {"enabled": False}

    # ========== 音视频转写方法 ==========

    def get_media_transcriber(self):
        """获取媒体转写器实例"""
        return self._media_transcriber

    async def transcribe_media(self, file_path: str,
                                language: str = None,
                                extract_frames: bool = False) -> dict:
        """
        转写媒体文件

        参数:
            file_path: 媒体文件路径
            language: 语言
            extract_frames: 是否提取视频关键帧

        返回:
            {
                "text": "转写文字",
                "segments": [...],
                "duration": 120.5,
                "language": "zh"
            }
        """
        if hasattr(self, '_media_transcriber') and self._media_transcriber:
            result = await self._media_transcriber.transcribe(
                file_path, language, extract_frames
            )
            return {
                "text": result.text,
                "segments": result.segments,
                "duration": result.duration,
                "language": result.language,
                "error": result.error,
            }
        return {"error": "媒体转写器未初始化"}

    async def add_media_to_knowledge(self, file_path: str,
                                      source_id: str = None,
                                      sender_id: str = "",
                                      sender_nick: str = "",
                                      conversation_id: str = "",
                                      tags: list = None) -> dict:
        """
        将媒体文件添加到知识库（自动转写）

        参数:
            file_path: 媒体文件路径
            source_id: 来源ID
            sender_id: 发送者ID
            sender_nick: 发送者昵称
            conversation_id: 会话ID
            tags: 标签

        返回:
            添加结果
        """
        if not hasattr(self, '_media_transcriber') or not self._media_transcriber:
            return {"error": "媒体转写器未初始化"}

        # 转写媒体
        result = await self._media_transcriber.transcribe(file_path)

        if result.error:
            return {"error": result.error}

        if not result.text.strip():
            return {"error": "未识别到文字"}

        # 添加到知识库
        source_id = source_id or f"media_{int(time.time())}"
        chunks = await self.add_message(
            text=result.text,
            source_type="media",
            source_id=source_id,
            sender_id=sender_id,
            sender_nick=sender_nick,
            conversation_id=conversation_id,
            file_name=os.path.basename(file_path),
            tags=tags or ["media", "transcription"],
        )

        return {
            "success": True,
            "text": result.text,
            "duration": result.duration,
            "language": result.language,
            "chunks_count": len(chunks),
        }

    # ========== A/B 测试方法 ==========

    def get_ab_manager(self):
        """获取 A/B 测试管理器实例"""
        return self._ab_manager

    def create_ab_test(self, name: str,
                      variants: List[Dict[str, Any]],
                      traffic_split: List[float] = None,
                      description: str = "") -> str:
        """
        创建 A/B 测试

        参数:
            name: 实验名称
            variants: 变体配置列表
            traffic_split: 流量分配
            description: 实验描述

        返回:
            实验ID
        """
        if hasattr(self, '_ab_manager') and self._ab_manager:
            return self._ab_manager.create_experiment(
                name, variants, traffic_split, description
            )
        raise RuntimeError("A/B 测试管理器未初始化")

    def get_ab_variant(self, experiment_id: str,
                      user_id: str) -> Optional[Dict]:
        """
        获取用户对应的变体

        参数:
            experiment_id: 实验ID
            user_id: 用户ID

        返回:
            变体配置
        """
        if hasattr(self, '_ab_manager') and self._ab_manager:
            return self._ab_manager.get_variant(experiment_id, user_id)
        return None

    def record_ab_metric(self, experiment_id: str,
                        user_id: str, variant_name: str,
                        metric_type: str, value: float = 0.0):
        """
        记录 A/B 测试指标

        参数:
            experiment_id: 实验ID
            user_id: 用户ID
            variant_name: 变体名称
            metric_type: 指标类型（exposure/click/feedback）
            value: 指标值
        """
        if hasattr(self, '_ab_manager') and self._ab_manager:
            if metric_type == "exposure":
                self._ab_manager.record_exposure(experiment_id, user_id, variant_name)
            elif metric_type == "click":
                self._ab_manager.record_click(experiment_id, user_id, variant_name, value)
            elif metric_type == "feedback":
                self._ab_manager.record_feedback(experiment_id, user_id, variant_name, value)

    def analyze_ab_test(self, experiment_id: str) -> dict:
        """
        分析 A/B 测试结果

        参数:
            experiment_id: 实验ID

        返回:
            分析结果
        """
        if hasattr(self, '_ab_manager') and self._ab_manager:
            return self._ab_manager.analyze_results(experiment_id)
        return {"error": "A/B 测试管理器未初始化"}

    def list_ab_tests(self, status: str = None) -> list:
        """列出 A/B 测试"""
        if hasattr(self, '_ab_manager') and self._ab_manager:
            return self._ab_manager.list_experiments(status)
        return []

    # ========== SLA 监控方法 ==========

    def get_sla_monitor(self):
        """获取 SLA 监控器实例"""
        return self._sla_monitor

    def check_health(self) -> dict:
        """
        健康检查

        返回:
            健康状态
        """
        if hasattr(self, '_sla_monitor') and self._sla_monitor:
            health = self._sla_monitor.check_health()
            return {
                "status": health.status,
                "search_p50": health.search_p50,
                "search_p95": health.search_p95,
                "search_p99": health.search_p99,
                "error_rate": health.error_rate,
                "uptime_hours": health.uptime_hours,
                "issues": health.issues,
                "checked_at": health.checked_at,
            }
        return {"status": "unknown", "error": "SLA 监控器未初始化"}

    def record_search_latency(self, latency: float,
                             query: str = "",
                             results_count: int = 0):
        """
        记录检索延迟

        参数:
            latency: 延迟（秒）
            query: 查询词
            results_count: 结果数量
        """
        if hasattr(self, '_sla_monitor') and self._sla_monitor:
            self._sla_monitor.record_search_latency(latency, query, results_count)

    def record_error(self, error_type: str, message: str,
                    details: dict = None):
        """
        记录错误

        参数:
            error_type: 错误类型
            message: 错误消息
            details: 额外详情
        """
        if hasattr(self, '_sla_monitor') and self._sla_monitor:
            self._sla_monitor.record_error(error_type, message, details)

    def get_sla_report(self, hours: int = 24) -> dict:
        """
        获取 SLA 报告

        参数:
            hours: 报告小时数

        返回:
            SLA 报告
        """
        if hasattr(self, '_sla_monitor') and self._sla_monitor:
            return self._sla_monitor.get_sla_report(hours)
        return {"error": "SLA 监控器未初始化"}

    def get_latency_stats(self, hours: int = 24) -> dict:
        """获取延迟统计"""
        if hasattr(self, '_sla_monitor') and self._sla_monitor:
            return self._sla_monitor.get_latency_stats(hours)
        return {"count": 0}

    def get_alerts(self, limit: int = 50, severity: str = None) -> list:
        """获取告警历史"""
        if hasattr(self, '_sla_monitor') and self._sla_monitor:
            return self._sla_monitor.get_alerts(limit, severity)
        return []

    # ========== 操作日志管理 ==========

    def query_operation_logs(
        self,
        start_time: str = None,
        end_time: str = None,
        operation: str = None,
        user_id: str = None,
        limit: int = 100
    ) -> List[OperationLog]:
        """
        查询操作日志

        参数:
            start_time: 开始时间 (ISO 格式)
            end_time: 结束时间 (ISO 格式)
            operation: 操作类型过滤 (add/search/delete/export/update_schedule)
            user_id: 用户 ID 过滤
            limit: 返回数量限制

        返回:
            日志列表
        """
        return self._op_logger.query(
            start_time=start_time,
            end_time=end_time,
            operation=operation,
            user_id=user_id,
            limit=limit
        )

    def get_operation_stats(self, days: int = 7) -> dict:
        """
        获取操作统计

        参数:
            days: 统计天数

        返回:
            统计信息
        """
        return self._op_logger.get_stats(days)

    def export_operation_logs(self, output_file: str, format: str = "json",
                              limit: int = 10000):
        """
        导出操作日志

        参数:
            output_file: 输出文件路径
            format: 输出格式 (json/csv)
            limit: 导出数量限制
        """
        self._op_logger.export_logs(output_file, format, limit)

    def clear_old_operation_logs(self, days: int = 90) -> int:
        """
        清理过期操作日志

        参数:
            days: 保留天数

        返回:
            清理的日志数量
        """
        return self._op_logger.clear_old_logs(days)

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    @property
    def keyword_index_size(self) -> int:
        return len(self._keyword_index)

    def _archive_message(self, text: str, source_type: str, source_id: str,
                         sender_id: str, sender_nick: str, conversation_id: str,
                         message_type: str, file_name: str, file_path: str,
                         timestamp: float, tags: list,
                         format: str = "markdown"):
        """
        保存原始消息归档

        参数:
            format: 存储格式 "json" 或 "markdown"
        """
        today = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
        day_dir = os.path.join(self._messages_dir, today)
        os.makedirs(day_dir, exist_ok=True)

        archive_time = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")

        if format == "markdown":
            # Markdown 格式存储
            md_content = self._format_as_markdown(
                text=text,
                source_type=source_type,
                sender_nick=sender_nick,
                timestamp=archive_time,
                file_name=file_name,
                tags=tags,
            )
            archive_path = os.path.join(day_dir, f"{source_id}.md")
            try:
                with open(archive_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
            except Exception as e:
                logger.error(f"保存消息归档失败: {e}")
        else:
            # JSON 格式存储
            archive = {
                "source_id": source_id,
                "source_type": source_type,
                "text": text,
                "sender_id": sender_id,
                "sender_nick": sender_nick,
                "corp_id": self._corp_id,
                "conversation_id": conversation_id,
                "message_type": message_type,
                "file_name": file_name,
                "file_path": file_path,
                "timestamp": timestamp,
                "archived_at": datetime.now().isoformat(),
                "tags": tags,
            }
            archive_path = os.path.join(day_dir, f"{source_id}.json")
            try:
                with open(archive_path, "w", encoding="utf-8") as f:
                    json.dump(archive, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"保存消息归档失败: {e}")

    def _format_as_markdown(self, text: str, source_type: str,
                            sender_nick: str, timestamp: str,
                            file_name: str, tags: list) -> str:
        """格式化为 Markdown"""
        lines = []

        # 来源类型图标
        type_icons = {"text": "💬", "image": "🖼️", "file": "📎"}
        icon = type_icons.get(source_type, "📝")

        # 标题行
        lines.append(f"## {icon} {sender_nick} ({timestamp})")
        lines.append("")

        # 文件信息
        if file_name:
            lines.append(f"**文件**: {file_name}")
            lines.append("")

        # 正文
        lines.append(text)
        lines.append("")

        # 标签
        if tags:
            lines.append(f"**标签**: {', '.join(tags)}")
            lines.append("")

        # 分隔线
        lines.append("---")
        lines.append("")

        return "\n".join(lines)

    def get_structured_data(self, data_type: str) -> list:
        """获取结构化数据"""
        file_path = os.path.join(self._structured_dir, f"{data_type}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"读取结构化数据失败: {e}")
        return []

    def save_structured_data(self, data_type: str, data: list):
        """保存结构化数据"""
        file_path = os.path.join(self._structured_dir, f"{data_type}.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存结构化数据失败: {e}")

    def update_schedule(self, class_name: str, day1: str, period1: str,
                        day2: str, period2: str, permanent: bool = True) -> dict:
        """
        更新课表（调课功能）

        参数:
            class_name: 班级名称（如"计算机2301"）
            day1: 第一天（如"周一"）
            period1: 第一节次（如"上午第1节"）
            day2: 第二天（如"周二"）
            period2: 第二节次（如"上午第1节"）
            permanent: 是否永久调课

        返回:
            更新结果
        """
        schedules = self.get_structured_data("schedules")
        if not schedules:
            # 尝试从分块中提取课表
            schedules = self._extract_schedules_from_chunks()

        result = {
            "success": False,
            "message": "",
            "updated": 0,
            "details": []
        }

        # 查找匹配的课表
        updated_schedules = []
        for schedule in schedules:
            if class_name and class_name not in schedule.get("class", ""):
                updated_schedules.append(schedule)
                continue

            # 找到匹配的课表，执行调课
            original_schedule = schedule.copy()
            schedule = self._swap_schedule(schedule, day1, period1, day2, period2)

            if schedule != original_schedule:
                result["updated"] += 1
                result["details"].append({
                    "class": schedule.get("class", ""),
                    "change": f"{day1}{period1} ↔ {day2}{period2}",
                    "permanent": permanent
                })

            updated_schedules.append(schedule)

        if result["updated"] > 0:
            # 保存更新后的课表
            self.save_structured_data("schedules", updated_schedules)

            # 同时更新相关的分块
            self._update_schedule_chunks(class_name, day1, period1, day2, period2)

            result["success"] = True
            result["message"] = f"成功更新 {result['updated']} 个课表"
        else:
            result["message"] = f"未找到匹配的课表（班级：{class_name}）"

        # 记录操作日志
        self._op_logger.log(OperationLog(
            timestamp=datetime.now().isoformat(),
            operation="update_schedule",
            user_id="",
            user_nick="",
            result_count=result["updated"],
            status="success" if result["success"] else "failed",
            details=f"班级={class_name}, {day1}{period1} ↔ {day2}{period2}, {result['message']}"
        ))

        return result

    # ========== 冲突检测方法 ==========

    def detect_conflicts(self) -> dict:
        """
        检测所有冲突

        返回:
            冲突检测结果
        """
        from agent.structured_data import ConflictDetector

        result = {
            "has_conflicts": False,
            "total": 0,
            "errors": 0,
            "warnings": 0,
            "conflicts": [],
            "report": "",
        }

        all_conflicts = []

        # 检测课表冲突
        schedules = self.get_structured_data("schedules")
        if schedules:
            schedule_conflicts = ConflictDetector.detect_schedule_conflicts(schedules)
            all_conflicts.extend(schedule_conflicts)

        # 检测考试冲突
        exams = self.get_structured_data("exams")
        if exams:
            exam_conflicts = ConflictDetector.detect_exam_conflicts(exams)
            all_conflicts.extend(exam_conflicts)

        # 检测课表与考试的重叠
        if schedules and exams:
            overlap_conflicts = ConflictDetector.check_schedule_exam_overlap(schedules, exams)
            all_conflicts.extend(overlap_conflicts)

        # 统计结果
        result["total"] = len(all_conflicts)
        result["errors"] = sum(1 for c in all_conflicts if c.severity == "error")
        result["warnings"] = sum(1 for c in all_conflicts if c.severity == "warning")
        result["has_conflicts"] = len(all_conflicts) > 0
        result["conflicts"] = [
            {
                "type": c.conflict_type,
                "severity": c.severity,
                "message": c.message,
                "details": c.details,
                "detected_at": c.detected_at,
            }
            for c in all_conflicts
        ]
        result["report"] = ConflictDetector.format_conflicts_report(all_conflicts)

        # 记录操作日志
        self._op_logger.log(OperationLog(
            timestamp=datetime.now().isoformat(),
            operation="conflict_check",
            result_count=len(all_conflicts),
            status="success",
            details=f"发现 {len(all_conflicts)} 个冲突"
        ))

        return result

    def detect_schedule_conflicts_for_class(self, class_name: str) -> dict:
        """
        检测指定班级的课表冲突

        参数:
            class_name: 班级名称

        返回:
            冲突检测结果
        """
        from agent.structured_data import ConflictDetector

        schedules = self.get_structured_data("schedules")
        class_schedules = [s for s in schedules if class_name in s.get("class", "")]

        if not class_schedules:
            return {
                "has_conflicts": False,
                "total": 0,
                "message": f"未找到 {class_name} 的课表数据",
            }

        conflicts = ConflictDetector.detect_schedule_conflicts(class_schedules)

        return {
            "has_conflicts": len(conflicts) > 0,
            "total": len(conflicts),
            "errors": sum(1 for c in conflicts if c.severity == "error"),
            "warnings": sum(1 for c in conflicts if c.severity == "warning"),
            "conflicts": [
                {
                    "type": c.conflict_type,
                    "severity": c.severity,
                    "message": c.message,
                    "details": c.details,
                }
                for c in conflicts
            ],
            "report": ConflictDetector.format_conflicts_report(conflicts),
        }

    def detect_exam_conflicts_for_course(self, course_name: str) -> dict:
        """
        检测指定课程的考试冲突

        参数:
            course_name: 课程名称

        返回:
            冲突检测结果
        """
        from agent.structured_data import ConflictDetector

        exams = self.get_structured_data("exams")
        course_exams = [e for e in exams if course_name in e.get("course", "")]

        if not course_exams:
            return {
                "has_conflicts": False,
                "total": 0,
                "message": f"未找到 {course_name} 的考试数据",
            }

        # 只检测该课程的考试是否与其他考试冲突
        all_conflicts = ConflictDetector.detect_exam_conflicts(exams)
        # 过滤出与该课程相关的冲突
        course_conflicts = [
            c for c in all_conflicts
            if course_name in c.message
        ]

        return {
            "has_conflicts": len(course_conflicts) > 0,
            "total": len(course_conflicts),
            "conflicts": [
                {
                    "type": c.conflict_type,
                    "severity": c.severity,
                    "message": c.message,
                    "details": c.details,
                }
                for c in course_conflicts
            ],
            "report": ConflictDetector.format_conflicts_report(course_conflicts),
        }

    def add_schedule(self, schedule_data: dict, check_conflicts: bool = True) -> dict:
        """
        添加课表（带冲突检测）

        参数:
            schedule_data: 课表数据
                {
                    "class": "计算机2301",
                    "schedule": {
                        "周一": {"第1节": "语文", "第2节": "数学", ...},
                        ...
                    }
                }
            check_conflicts: 是否检测冲突

        返回:
            添加结果
        """
        result = {
            "success": False,
            "message": "",
            "conflicts": [],
            "conflict_report": "",
        }

        # 获取现有课表
        schedules = self.get_structured_data("schedules")

        # 检测冲突
        if check_conflicts:
            # 临时添加新课表进行冲突检测
            test_schedules = schedules + [schedule_data]
            from agent.structured_data import ConflictDetector
            conflicts = ConflictDetector.detect_schedule_conflicts(test_schedules)

            if conflicts:
                result["conflicts"] = [
                    {
                        "type": c.conflict_type,
                        "severity": c.severity,
                        "message": c.message,
                        "details": c.details,
                    }
                    for c in conflicts
                ]
                result["conflict_report"] = ConflictDetector.format_conflicts_report(conflicts)

                # 如果有错误级别的冲突，阻止添加
                errors = [c for c in conflicts if c.severity == "error"]
                if errors:
                    result["message"] = f"发现 {len(errors)} 个冲突，课表未添加"
                    return result

        # 添加课表
        # 检查是否已存在同名班级，如果存在则更新
        class_name = schedule_data.get("class", "")
        updated = False
        for i, s in enumerate(schedules):
            if s.get("class") == class_name:
                schedules[i] = schedule_data
                updated = True
                break

        if not updated:
            schedules.append(schedule_data)

        self.save_structured_data("schedules", schedules)

        result["success"] = True
        result["message"] = f"课表{'更新' if updated else '添加'}成功"

        # 记录操作日志
        self._op_logger.log(OperationLog(
            timestamp=datetime.now().isoformat(),
            operation="add_schedule",
            result_count=1,
            status="success",
            details=f"班级={class_name}, {'更新' if updated else '新增'}, 冲突={len(result['conflicts'])} 个"
        ))

        return result

    def add_exam(self, exam_data: dict, check_conflicts: bool = True) -> dict:
        """
        添加考试安排（带冲突检测）

        参数:
            exam_data: 考试数据
                {
                    "course": "高等数学",
                    "exam_type": "期末考试",
                    "date": "2026-06-15",
                    "time": "09:00-11:00",
                    "classroom": "教二楼301"
                }
            check_conflicts: 是否检测冲突

        返回:
            添加结果
        """
        result = {
            "success": False,
            "message": "",
            "conflicts": [],
            "conflict_report": "",
        }

        # 获取现有考试安排
        exams = self.get_structured_data("exams")

        # 检测冲突
        if check_conflicts:
            test_exams = exams + [exam_data]
            from agent.structured_data import ConflictDetector
            conflicts = ConflictDetector.detect_exam_conflicts(test_exams)

            if conflicts:
                result["conflicts"] = [
                    {
                        "type": c.conflict_type,
                        "severity": c.severity,
                        "message": c.message,
                        "details": c.details,
                    }
                    for c in conflicts
                ]
                result["conflict_report"] = ConflictDetector.format_conflicts_report(conflicts)

                # 如果有错误级别的冲突，阻止添加
                errors = [c for c in conflicts if c.severity == "error"]
                if errors:
                    result["message"] = f"发现 {len(errors)} 个冲突，考试安排未添加"
                    return result

        # 添加考试安排
        exams.append(exam_data)
        self.save_structured_data("exams", exams)

        result["success"] = True
        result["message"] = "考试安排添加成功"

        # 记录操作日志
        self._op_logger.log(OperationLog(
            timestamp=datetime.now().isoformat(),
            operation="add_exam",
            result_count=1,
            status="success",
            details=f"课程={exam_data.get('course', '')}, 日期={exam_data.get('date', '')}, 冲突={len(result['conflicts'])} 个"
        ))

        return result

    def _swap_schedule(self, schedule: dict, day1: str, period1: str,
                       day2: str, period2: str) -> dict:
        """交换课表中的两节课"""
        # 解析课表结构
        schedule_data = schedule.get("schedule", {})
        if not schedule_data:
            return schedule

        # 获取两节课的内容
        course1 = self._get_course(schedule_data, day1, period1)
        course2 = self._get_course(schedule_data, day2, period2)

        if course1 is None or course2 is None:
            return schedule

        # 交换课程
        self._set_course(schedule_data, day1, period1, course2)
        self._set_course(schedule_data, day2, period2, course1)

        schedule["schedule"] = schedule_data
        schedule["last_updated"] = datetime.now().isoformat()
        schedule["update_type"] = "permanent_swap" if True else "temporary_swap"

        return schedule

    def _get_course(self, schedule_data: dict, day: str, period: str) -> Optional[str]:
        """获取指定时间的课程"""
        # 尝试不同的数据结构
        if day in schedule_data:
            day_data = schedule_data[day]
            if isinstance(day_data, dict):
                return day_data.get(period)
            elif isinstance(day_data, list):
                # 根据节次索引
                period_index = self._period_to_index(period)
                if 0 <= period_index < len(day_data):
                    return day_data[period_index]
        return None

    def _set_course(self, schedule_data: dict, day: str, period: str, course: str):
        """设置指定时间的课程"""
        if day not in schedule_data:
            schedule_data[day] = {}

        day_data = schedule_data[day]
        if isinstance(day_data, dict):
            day_data[period] = course
        elif isinstance(day_data, list):
            period_index = self._period_to_index(period)
            while len(day_data) <= period_index:
                day_data.append("")
            day_data[period_index] = course

    def _period_to_index(self, period: str) -> int:
        """将节次转换为索引"""
        period_map = {
            "上午第1节": 0, "上午第2节": 1, "上午第3节": 2, "上午第4节": 3,
            "下午第1节": 4, "下午第2节": 5, "下午第3节": 6, "下午第4节": 7,
            "晚上第1节": 8, "晚上第2节": 9,
            "第1节": 0, "第2节": 1, "第3节": 2, "第4节": 3,
            "第5节": 4, "第6节": 5, "第7节": 6, "第8节": 7,
            "第9节": 8, "第10节": 9,
        }
        return period_map.get(period, 0)

    def _extract_schedules_from_chunks(self) -> list:
        """从分块中提取课表信息"""
        schedules = []
        for chunk in self._chunks:
            if "课表" in chunk.text or "课程" in chunk.text:
                # 简单提取，实际应该用更复杂的解析
                schedule = {
                    "class": chunk.file_name or "未知班级",
                    "content": chunk.text,
                    "source_id": chunk.source_id,
                    "extracted_at": datetime.now().isoformat()
                }
                schedules.append(schedule)
        return schedules

    def _update_schedule_chunks(self, class_name: str, day1: str, period1: str,
                                day2: str, period2: str):
        """更新包含课表的分块"""
        for chunk in self._chunks:
            if class_name and class_name not in chunk.text:
                continue

            # 检查是否包含需要修改的内容
            if day1 in chunk.text and period1 in chunk.text:
                # 这里可以添加更精确的文本替换逻辑
                # 目前简单标记为需要更新
                chunk.tags.append(f"schedule_update_{datetime.now().strftime('%Y%m%d')}")

        # 保存更新后的索引
        self._save_index()

    def get_storage_stats(self) -> dict:
        """获取存储统计信息"""
        stats = {
            "total_chunks": len(self._chunks),
            "max_chunks": MAX_CHUNKS,
            "usage_percent": len(self._chunks) / MAX_CHUNKS * 100 if MAX_CHUNKS > 0 else 0,
            "index_size_mb": 0,
            "messages_size_mb": 0,
            "files_size_mb": 0,
            "total_size_mb": 0,
        }

        # 计算索引大小
        chunks_file = os.path.join(self._index_dir, "chunks.json")
        embeddings_file = os.path.join(self._index_dir, "embeddings.npy")
        if os.path.exists(chunks_file):
            stats["index_size_mb"] += os.path.getsize(chunks_file) / (1024 * 1024)
        if os.path.exists(embeddings_file):
            stats["index_size_mb"] += os.path.getsize(embeddings_file) / (1024 * 1024)

        # 计算消息目录大小
        if os.path.exists(self._messages_dir):
            for root, dirs, files in os.walk(self._messages_dir):
                for file in files:
                    stats["messages_size_mb"] += os.path.getsize(os.path.join(root, file))

        # 计算文件目录大小
        if os.path.exists(self._files_dir):
            for root, dirs, files in os.walk(self._files_dir):
                for file in files:
                    stats["files_size_mb"] += os.path.getsize(os.path.join(root, file))

        stats["messages_size_mb"] /= (1024 * 1024)
        stats["files_size_mb"] /= (1024 * 1024)
        stats["total_size_mb"] = stats["index_size_mb"] + stats["messages_size_mb"] + stats["files_size_mb"]

        return stats


# ========== 全局实例 ==========
_kb_cache: Dict[str, KnowledgeBase] = {}


def get_knowledge_base(school_dir: str, corp_id: str) -> KnowledgeBase:
    """获取或创建知识库实例（带缓存）"""
    if corp_id not in _kb_cache:
        _kb_cache[corp_id] = KnowledgeBase(school_dir, corp_id)
    return _kb_cache[corp_id]


def clear_embedding_cache():
    """清空全局 Embedding 缓存"""
    _embedding_cache.clear()
    logger.info("Embedding 缓存已清空")


def get_embedding_cache_stats() -> dict:
    """获取 Embedding 缓存统计"""
    return {
        "size": _embedding_cache.size,
        "max_size": EMBEDDING_CACHE_SIZE,
    }


# ========== 操作日志 ==========
@dataclass
class OperationLog:
    """操作日志记录"""
    timestamp: str          # 操作时间 (ISO 格式)
    operation: str          # 操作类型: add/search/delete/export/update_schedule/stats
    user_id: str = ""       # 操作用户 ID
    user_nick: str = ""     # 操作用户昵称
    query: str = ""         # 查询内容（搜索时）
    source_type: str = ""   # 来源类型（添加时）
    source_id: str = ""     # 来源 ID
    file_name: str = ""     # 文件名
    result_count: int = 0   # 结果数量
    details: str = ""       # 其他详情
    status: str = "success" # 操作状态: success/failed/skipped


class OperationLogger:
    """
    操作日志管理器

    记录知识库的所有操作，支持查询和导出
    """

    def __init__(self, log_dir: str):
        self._log_dir = log_dir
        self._log_file = os.path.join(log_dir, "operation_logs.jsonl")
        os.makedirs(log_dir, exist_ok=True)

    def log(self, entry: OperationLog):
        """记录一条操作日志"""
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"保存操作日志失败: {e}")

    def query(
        self,
        start_time: str = None,
        end_time: str = None,
        operation: str = None,
        user_id: str = None,
        limit: int = 100
    ) -> List[OperationLog]:
        """
        查询操作日志

        参数:
            start_time: 开始时间 (ISO 格式)
            end_time: 结束时间 (ISO 格式)
            operation: 操作类型过滤
            user_id: 用户 ID 过滤
            limit: 返回数量限制

        返回:
            日志列表
        """
        if not os.path.exists(self._log_file):
            return []

        results = []
        try:
            with open(self._log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entry = OperationLog(**data)

                        # 时间过滤
                        if start_time and entry.timestamp < start_time:
                            continue
                        if end_time and entry.timestamp > end_time:
                            continue

                        # 操作类型过滤
                        if operation and entry.operation != operation:
                            continue

                        # 用户过滤
                        if user_id and entry.user_id != user_id:
                            continue

                        results.append(entry)
                    except Exception:
                        continue
        except Exception as e:
            logger.error(f"读取操作日志失败: {e}")

        # 按时间倒序，返回最近的
        results.sort(key=lambda x: x.timestamp, reverse=True)
        return results[:limit]

    def get_stats(self, days: int = 7) -> dict:
        """
        获取操作统计

        参数:
            days: 统计天数

        返回:
            统计信息
        """
        from datetime import timedelta
        start_time = (datetime.now() - timedelta(days=days)).isoformat()
        logs = self.query(start_time=start_time, limit=100000)

        stats = {
            "total_operations": len(logs),
            "by_operation": {},
            "by_user": {},
            "by_status": {},
            "daily": {},
        }

        for log in logs:
            # 按操作类型统计
            stats["by_operation"][log.operation] = stats["by_operation"].get(log.operation, 0) + 1

            # 按用户统计
            if log.user_nick:
                stats["by_user"][log.user_nick] = stats["by_user"].get(log.user_nick, 0) + 1

            # 按状态统计
            stats["by_status"][log.status] = stats["by_status"].get(log.status, 0) + 1

            # 按日期统计
            day = log.timestamp[:10]
            stats["daily"][day] = stats["daily"].get(day, 0) + 1

        return stats

    def clear_old_logs(self, days: int = 90):
        """清理指定天数之前的日志"""
        if not os.path.exists(self._log_file):
            return 0

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        kept = []
        removed = 0

        try:
            with open(self._log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("timestamp", "") >= cutoff:
                            kept.append(line)
                        else:
                            removed += 1
                    except Exception:
                        kept.append(line)

            with open(self._log_file, "w", encoding="utf-8") as f:
                f.write("\n".join(kept) + "\n" if kept else "")

            logger.info(f"清理了 {removed} 条过期日志")
        except Exception as e:
            logger.error(f"清理日志失败: {e}")

        return removed

    def export_logs(self, output_file: str, format: str = "json", limit: int = 10000):
        """
        导出操作日志

        参数:
            output_file: 输出文件路径
            format: 输出格式 (json/csv)
            limit: 导出数量限制
        """
        logs = self.query(limit=limit)

        if format == "csv":
            import csv
            with open(output_file, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["时间", "操作", "用户", "查询内容", "来源类型", "文件名", "结果数", "状态", "详情"])
                for log in logs:
                    writer.writerow([
                        log.timestamp, log.operation, log.user_nick,
                        log.query, log.source_type, log.file_name,
                        log.result_count, log.status, log.details
                    ])
        else:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump([asdict(log) for log in logs], f, ensure_ascii=False, indent=2)

        logger.info(f"导出 {len(logs)} 条操作日志到 {output_file}")
