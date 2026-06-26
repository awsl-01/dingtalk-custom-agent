from openai import OpenAI
import config
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个学校的智能助手，为老师们提供服务。当前时间是2026年5月。你的职责包括：
1. 回答学校规章制度、流程相关的问题
2. 协助处理请假、调课等事务
3. 帮助制作课件、教案等教学材料
4. 解答日常工作中遇到的各种问题

重要要求：
- 始终提供2026年及以后的最新信息
- 如果涉及政策、法规、课程标准等，请基于最新版本回答
- 对于时效性较强的信息（如考试时间、假期安排等），请明确说明信息的时间范围
- 如果不确定最新情况，请坦诚告知并建议查询官方渠道

请用友好、专业的语气回答。回答要简洁明了，适合在聊天软件中阅读。"""


def chat(user_message: str) -> str:
    """调用 OpenAI 兼容 API 进行对话"""
    client = OpenAI(
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_BASE_URL,
    )
    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"抱歉，处理消息时出现错误：{e}"


async def chat_with_knowledge(user_message: str, knowledge_context: str = "",
                              need_web_search: bool = False,
                              intent: dict = None) -> str:
    """
    基于知识库上下文的对话（支持意图驱动的回答生成）

    参数:
        user_message: 用户消息
        knowledge_context: 知识库检索结果
        need_web_search: 是否需要网络搜索增强
        intent: 查询意图（来自意图识别模块）

    返回:
        AI回答
    """
    from agent.web_search import search_and_summarize

    # 构建系统提示
    system_prompt = SYSTEM_PROMPT

    # 根据意图类型调整系统提示
    intent_type = intent.get("type", "other") if intent else "other"
    entities = intent.get("entities", {}) if intent else {}

    if knowledge_context:
        system_prompt += """

【知识库检索结果】
以下是学校知识库中与用户问题相关的信息，请优先使用这些信息回答问题：

""" + knowledge_context

        # 根据意图类型添加特定的回答指导
        if intent_type == "person_info":
            person = entities.get("person", "")
            system_prompt += f"""

【意图分析】
用户想了解{person}的个人信息。

回答要求：
1. 优先展示：姓名、职务/职称、联系方式、办公室位置
2. 如果有课程信息，可以简要提及
3. 如果有个人简介，可以适当展示
4. 回答要结构化，使用列表或分段展示"""
        elif intent_type == "schedule":
            system_prompt += """

【意图分析】
用户想了解课程安排。

回答要求：
1. 优先展示课表信息，使用表格格式
2. 包含：时间、课程名称、教室、教师
3. 如果有多个课程，按时间顺序排列
4. 回答要清晰易读"""
        elif intent_type == "exam":
            system_prompt += """

【意图分析】
用户想了解考试信息。

回答要求：
1. 优先展示考试安排
2. 包含：考试时间、地点、科目、注意事项
3. 如果有成绩信息，注意保护隐私
4. 回答要准确，避免歧义"""
        elif intent_type == "contact":
            system_prompt += """

【意图分析】
用户想了解联系方式。

回答要求：
1. 优先展示联系方式
2. 包含：电话、邮箱、微信、办公室位置
3. 注意保护隐私，只展示公开信息
4. 回答要简洁明了"""
        elif intent_type == "notice":
            system_prompt += """

【意图分析】
用户想了解通知公告。

回答要求：
1. 优先展示通知内容
2. 包含：通知标题、发布时间、主要内容、截止时间
3. 如果有附件或链接，提醒用户查看
4. 回答要完整，不要遗漏关键信息"""

        system_prompt += """

重要规则：
1. 优先使用知识库中的信息回答
2. 如果知识库信息足够回答，直接给出答案
3. 如果知识库信息不足，可以补充你自己的知识
4. 回答时可以说明"根据学校知识库记录..."来增加可信度
5. **严格遵循用户问题范围**：用户问什么就答什么，不要添加额外信息
6. 回答要简洁，只包含用户需要的信息
7. 根据信息类型选择合适的格式（表格、列表、段落等）"""

    # 构建用户消息
    final_message = user_message

    if need_web_search and not knowledge_context:
        # 没有知识库结果但需要搜索
        try:
            search_results = search_and_summarize(user_message)
            final_message = f"""用户问题：{user_message}

网络搜索结果（2026年最新）：
{search_results}

请基于以上搜索结果回答用户的问题。"""
        except Exception as e:
            logger.warning(f"网络搜索失败: {e}")

    elif not knowledge_context and not need_web_search:
        # 没有知识库结果，也不需要搜索
        system_prompt += """

注意：学校知识库中暂无与用户问题相关的信息。请根据你的知识回答，并在回答末尾提示：
"💡 提示：如需将此信息存入知识库，请直接发送相关文件或图片给我。" """

    client = OpenAI(
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_BASE_URL,
    )

    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": final_message},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"抱歉，处理消息时出现错误：{e}"
