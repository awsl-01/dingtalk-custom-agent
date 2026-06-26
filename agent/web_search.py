"""
网络搜索模块
为钉钉机器人提供网络搜索能力
"""

import re
import json
import logging
from typing import List, Dict, Optional
from urllib.parse import quote_plus

import httpx
from openai import OpenAI

import config

logger = logging.getLogger(__name__)

# 搜索结果缓存
_search_cache = {}


async def search_web(query: str, num_results: int = 5) -> List[Dict]:
    """
    搜索网络内容

    参数:
        query: 搜索关键词
        num_results: 返回结果数量

    返回:
        搜索结果列表，每个结果包含title、url、snippet
    """
    # 检查缓存
    cache_key = f"{query}_{num_results}"
    if cache_key in _search_cache:
        return _search_cache[cache_key]

    results = []

    # 优先使用必应搜索（HTML结构更规范，更容易提取摘要）
    try:
        results = await _search_bing(query, num_results)
    except Exception as e:
        logger.warning(f"必应搜索失败: {e}")
        try:
            # 备用：使用百度搜索
            results = await _search_baidu(query, num_results)
        except Exception as e2:
            logger.warning(f"百度搜索失败: {e2}")
            results = []

    # 缓存结果
    if results:
        _search_cache[cache_key] = results

    return results


async def _search_baidu(query: str, num_results: int = 5) -> List[Dict]:
    """使用百度搜索，优先获取最新结果"""
    results = []
    # 添加时间限定参数，优先获取最近一年的结果
    url = f"https://www.baidu.com/s?wd={quote_plus(query)}&rn={num_results}&gpc=stf%3D1704038400%2C1746038400%7Cstftype%3D1"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, follow_redirects=True, timeout=10)

        if response.status_code == 200:
            html = response.text

            # 解析搜索结果 - 匹配标题、链接和摘要
            # 百度搜索结果通常在 <div class="result"> 或 <div class="c-container"> 中
            # 标题在 <h3> 中，摘要在 <div class="c-abstract"> 或 <span class="content-right_8Zs40"> 中

            # 方法1: 匹配完整的搜索结果块
            result_pattern = r'<div[^>]*class="[^"]*result[^"]*"[^>]*>.*?<h3[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?</h3>(.*?)(?=<div[^>]*class="[^"]*result|$)'
            blocks = re.findall(result_pattern, html, re.DOTALL)

            for link, title, content in blocks[:num_results]:
                # 清理HTML标签
                title = re.sub(r'<[^>]+>', '', title).strip()
                # 提取摘要 - 尝试多种模式
                snippet = ''
                # 尝试匹配 c-abstract
                abstract_match = re.search(r'<div[^>]*class="[^"]*c-abstract[^"]*"[^>]*>(.*?)</div>', content, re.DOTALL)
                if abstract_match:
                    snippet = re.sub(r'<[^>]+>', '', abstract_match.group(1)).strip()
                # 尝试匹配 content-right
                if not snippet:
                    content_match = re.search(r'<span[^>]*class="[^"]*content-right[^"]*"[^>]*>(.*?)</span>', content, re.DOTALL)
                    if content_match:
                        snippet = re.sub(r'<[^>]+>', '', content_match.group(1)).strip()
                # 尝试匹配任何较长的文本块
                if not snippet:
                    text_blocks = re.findall(r'>([^<]{20,})<', content)
                    if text_blocks:
                        snippet = text_blocks[0].strip()

                if title and link:
                    results.append({
                        'title': title,
                        'url': link,
                        'snippet': snippet[:200] if snippet else ''  # 限制摘要长度
                    })

            # 如果方法1没有结果，尝试方法2
            if not results:
                title_pattern = r'<h3[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
                matches = re.findall(title_pattern, html, re.DOTALL)

                for link, title in matches[:num_results]:
                    title = re.sub(r'<[^>]+>', '', title).strip()
                    if title and link:
                        results.append({
                            'title': title,
                            'url': link,
                            'snippet': ''
                        })

    return results


async def _search_bing(query: str, num_results: int = 5) -> List[Dict]:
    """使用必应搜索，优先获取最新结果"""
    results = []
    url = f"https://www.bing.com/search?q={quote_plus(query)}&count={num_results}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, follow_redirects=True, timeout=10)

        if response.status_code == 200:
            html = response.text

            # 必应搜索结果解析
            # 结果通常在 <li class="b_algo"> 中
            # 标题在 <h2><a> 中，摘要在 <p> 或 <div class="b_caption"><p> 中

            # 匹配搜索结果块
            result_pattern = r'<li[^>]*class="[^"]*b_algo[^"]*"[^>]*>(.*?)</li>'
            blocks = re.findall(result_pattern, html, re.DOTALL)

            for block in blocks[:num_results]:
                # 提取标题和链接
                title_match = re.search(r'<h2[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', block, re.DOTALL)
                if not title_match:
                    continue

                link = title_match.group(1)
                title = re.sub(r'<[^>]+>', '', title_match.group(2)).strip()

                # 提取摘要
                snippet = ''
                # 尝试匹配 <p> 标签中的内容
                snippet_match = re.search(r'<p[^>]*>(.*?)</p>', block, re.DOTALL)
                if snippet_match:
                    snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()
                # 如果没有，尝试匹配 <div class="b_caption"> 中的内容
                if not snippet:
                    caption_match = re.search(r'<div[^>]*class="[^"]*b_caption[^"]*"[^>]*>(.*?)</div>', block, re.DOTALL)
                    if caption_match:
                        snippet = re.sub(r'<[^>]+>', '', caption_match.group(1)).strip()

                if title and link:
                    results.append({
                        'title': title,
                        'url': link,
                        'snippet': snippet[:200] if snippet else ''
                    })

    return results


def search_and_summarize(query: str) -> str:
    """
    搜索并总结结果（同步版本，用于简单查询）

    参数:
        query: 搜索查询

    返回:
        搜索结果的文本总结
    """
    try:
        # 先执行网络搜索获取最新信息
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, search_web(query, 5))
                    search_results = future.result(timeout=15)
            else:
                search_results = loop.run_until_complete(search_web(query, 5))
        except RuntimeError:
            search_results = asyncio.run(search_web(query, 5))

        # 格式化搜索结果
        if search_results:
            search_context = "以下是网络搜索结果，请基于这些信息回答问题：\n\n"
            for i, result in enumerate(search_results[:3], 1):
                title = result.get('title', '无标题')
                snippet = result.get('snippet', '')
                url = result.get('url', '')
                search_context += f"{i}. {title}\n"
                if snippet:
                    search_context += f"   摘要：{snippet}\n"
                if url:
                    search_context += f"   来源：{url}\n"
                search_context += "\n"

            # 强制要求AI基于搜索结果回答
            search_context += """重要指令：
- 你必须基于以上搜索结果回答问题
- 不要使用你自己的知识（可能已过时）
- 如果搜索结果中没有相关信息，请明确说明"根据搜索结果未找到相关信息"
- 回答时请注明信息来源"""
        else:
            search_context = "未找到相关搜索结果。"

        # 使用AI进行搜索和总结
        client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
        )

        system_prompt = """你是一个智能搜索助手。你的任务是基于提供的搜索结果回答问题。

重要规则：
1. 必须基于搜索结果回答，不要使用自己的知识
2. 优先使用最新的搜索结果
3. 如果搜索结果不足以回答问题，请明确说明
4. 回答要简洁明了，适合在聊天软件中阅读
5. 在回答末尾注明信息来源"""

        user_message = f"用户问题：{query}\n\n{search_context}"

        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"搜索总结失败: {e}")
        return f"抱歉，搜索时出现错误：{str(e)}"


def format_search_results(results: List[Dict]) -> str:
    """
    格式化搜索结果

    参数:
        results: 搜索结果列表

    返回:
        格式化后的文本
    """
    if not results:
        return "未找到相关搜索结果。"

    output = "搜索结果：\n\n"

    for i, result in enumerate(results, 1):
        title = result.get('title', '无标题')
        url = result.get('url', '')
        snippet = result.get('snippet', '')

        output += f"{i}. {title}\n"
        if url:
            output += f"   链接：{url}\n"
        if snippet:
            output += f"   摘要：{snippet}\n"
        output += "\n"

    return output


async def search_for_education(topic: str, subject: str = "", grade: str = "") -> Dict:
    """
    为教育内容搜索相关素材

    参数:
        topic: 教学主题
        subject: 学科
        grade: 年级

    返回:
        包含教学素材的字典
    """
    # 构建搜索查询，添加2026年时间限定
    queries = []

    if subject and grade:
        queries.append(f"{subject} {grade} {topic} 教学设计 教案 2026 最新")
        queries.append(f"{topic} 教学课件 PPT 模板 2026")

    queries.append(f"{topic} 知识点 总结 2026")
    queries.append(f"{topic} 教学资源 素材 最新")

    all_results = {}

    for query in queries[:2]:  # 限制搜索次数
        try:
            results = await search_web(query, num_results=3)
            all_results[query] = results
        except Exception as e:
            logger.warning(f"搜索失败 [{query}]: {e}")
            all_results[query] = []

    return {
        'topic': topic,
        'subject': subject,
        'grade': grade,
        'search_results': all_results,
        'summary': _generate_search_summary(topic, all_results)
    }


def _generate_search_summary(topic: str, results: Dict) -> str:
    """生成搜索结果摘要"""
    summary = f"关于「{topic}」的搜索结果：\n\n"

    for query, items in results.items():
        summary += f"搜索：{query}\n"
        if items:
            for item in items[:2]:
                summary += f"- {item.get('title', '无标题')}\n"
        else:
            summary += "- 未找到相关结果\n"
        summary += "\n"

    return summary


# 快速搜索功能（用于简单查询）
def quick_search(query: str) -> str:
    """
    快速搜索并返回结果

    参数:
        query: 搜索查询

    返回:
        搜索结果文本
    """
    # 这里可以集成实际的搜索API
    # 目前使用AI模拟搜索结果
    return search_and_summarize(query)


# 教育资源搜索
def search_teaching_resources(topic: str, resource_type: str = "课件") -> str:
    """
    搜索教学资源

    参数:
        topic: 教学主题
        resource_type: 资源类型（课件/教案/习题/视频）

    返回:
        资源搜索结果
    """
    query = f"{topic} {resource_type} 教学资源 2026 最新"
    return quick_search(query)


# 试题搜索
def search_exam_questions(topic: str, difficulty: str = "中等") -> str:
    """
    搜索试题

    参数:
        topic: 知识点
        difficulty: 难度（基础/中等/提高）

    返回:
        试题搜索结果
    """
    query = f"{topic} {difficulty} 练习题 试题 2026 最新"
    return quick_search(query)


# 素材搜索
def search_materials(topic: str, material_type: str = "图片") -> str:
    """
    搜索教学素材

    参数:
        topic: 主题
        material_type: 素材类型（图片/视频/动画/实验）

    返回:
        素材搜索结果
    """
    query = f"{topic} {material_type} 教学素材 2026 最新"
    return quick_search(query)


async def search_textbook_content(topic: str, subject: str = "", grade: str = "") -> str:
    """
    搜索教材相关内容，为PPT生成提供真实教学素材

    参数:
        topic: 教学主题
        subject: 学科
        grade: 年级

    返回:
        结构化的教材内容文本（知识点、公式、例题、重难点）
    """
    import asyncio

    # 构建3组搜索查询
    queries = [
        f"{topic} {subject} {grade} 知识点 教材 2026",
        f"{topic} 教学设计 课标要求 重难点",
        f"{topic} 典型例题 考点 公式",
    ]

    # 并发搜索
    all_results = []
    tasks = [search_web(q, 3) for q in queries]
    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    for results in results_list:
        if isinstance(results, list):
            all_results.extend(results)

    if not all_results:
        return ""

    # 搜索结果文本
    search_text = ""
    for i, r in enumerate(all_results[:9], 1):
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        if title:
            search_text += f"{i}. {title}\n"
        if snippet:
            search_text += f"   {snippet}\n"

    # 用 AI 提炼关键教学内容
    try:
        client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
        )

        system_prompt = f"""你是一个{subject or '学科'}教学专家。请从搜索结果中提取与「{topic}」相关的教学内容。

提取要求：
1. 核心知识点（定义、概念、原理）
2. 重要公式/定理/法则（如有）
3. 教学重点和难点
4. 典型例题或考点（2-3个）
5. 常见错误和易错点

输出格式：
【核心知识点】
- ...

【公式/定理】
- ...

【教学重难点】
- ...

【典型例题】
- ...

【易错点】
- ...

只提取与主题直接相关的内容，不要泛泛而谈。如果搜索结果中没有某类信息，跳过该分类。"""

        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            max_tokens=2000,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"搜索结果：\n{search_text}"},
            ],
        )
        return response.choices[0].message.content

    except Exception as e:
        logger.warning(f"AI提炼教材内容失败: {e}")
        return search_text


if __name__ == "__main__":
    # 测试搜索功能
    import asyncio

    async def test_search():
        results = await search_web("Python 教程", 3)
        print("搜索结果：")
        for r in results:
            print(f"- {r['title']}: {r['url']}")

    asyncio.run(test_search())
