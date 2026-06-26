"""
LLM 工具模块

提供统一的 LLM 调用接口，支持：
- 统一的调用接口
- 重试机制
- 超时控制
- 错误处理
- JSON 响应解析
"""
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from functools import lru_cache

import config

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM 客户端"""

    def __init__(self):
        self._client = None
        self._async_client = None

    def _get_client(self):
        """获取同步客户端"""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=config.OPENAI_API_KEY,
                base_url=config.OPENAI_BASE_URL or None,
            )
        return self._client

    def _get_async_client(self):
        """获取异步客户端"""
        if self._async_client is None:
            from openai import AsyncOpenAI
            self._async_client = AsyncOpenAI(
                api_key=config.OPENAI_API_KEY,
                base_url=config.OPENAI_BASE_URL or None,
            )
        return self._async_client

    async def call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        retries: int = 2,
        timeout: float = None,
    ) -> str:
        """
        调用 LLM 获取文本响应

        参数:
            prompt: 用户提示
            system_prompt: 系统提示
            temperature: 温度参数（0-1，越低越确定）
            max_tokens: 最大 token 数
            retries: 重试次数
            timeout: 超时时间（秒），默认使用 config.LLM_TIMEOUT

        返回:
            LLM 响应文本
        """
        if timeout is None:
            timeout = getattr(config, 'LLM_TIMEOUT', 10)

        client = self._get_async_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(retries):
            try:
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=config.OPENAI_MODEL,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    ),
                    timeout=timeout
                )
                return response.choices[0].message.content.strip()
            except asyncio.TimeoutError:
                logger.warning(f"LLM 调用超时 (尝试 {attempt + 1}/{retries})")
                if attempt == retries - 1:
                    raise
            except Exception as e:
                logger.error(f"LLM 调用失败 (尝试 {attempt + 1}/{retries}): {e}")
                if attempt == retries - 1:
                    raise
                # 等待后重试
                await asyncio.sleep(1 * (attempt + 1))

        return ""

    async def call_llm_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        retries: int = 2,
        timeout: float = None,
    ) -> Dict[str, Any]:
        """
        调用 LLM 获取 JSON 响应

        参数:
            prompt: 用户提示
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大 token 数
            retries: 重试次数
            timeout: 超时时间（秒），默认使用 config.LLM_TIMEOUT

        返回:
            解析后的 JSON 字典
        """
        if timeout is None:
            timeout = getattr(config, 'LLM_TIMEOUT', 10)

        # 添加 JSON 格式要求
        json_prompt = f"""{prompt}

请严格按照以下 JSON 格式返回结果，不要包含任何其他文字：
{{"key": "value"}}"""

        json_system = (system_prompt or "") + "\n你是一个 JSON 格式输出助手，只返回有效的 JSON。"

        response = await self.call_llm(
            prompt=json_prompt,
            system_prompt=json_system,
            temperature=temperature,
            max_tokens=max_tokens,
            retries=retries,
            timeout=timeout,
        )

        # 尝试解析 JSON
        try:
            # 移除可能的 markdown 代码块标记
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[1]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}, 原始响应: {response}")
            # 尝试提取 JSON 部分
            import re
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            return {}


# 全局 LLM 客户端实例
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取全局 LLM 客户端实例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


# ========== 便捷函数 ==========

async def call_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 1000,
) -> str:
    """
    便捷函数：调用 LLM 获取文本响应

    参数:
        prompt: 用户提示
        system_prompt: 系统提示
        temperature: 温度参数
        max_tokens: 最大 token 数

    返回:
        LLM 响应文本
    """
    client = get_llm_client()
    return await client.call_llm(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )


async def call_llm_json(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 1000,
) -> Dict[str, Any]:
    """
    便捷函数：调用 LLM 获取 JSON 响应

    参数:
        prompt: 用户提示
        system_prompt: 系统提示
        temperature: 温度参数
        max_tokens: 最大 token 数

    返回:
        解析后的 JSON 字典
    """
    client = get_llm_client()
    return await client.call_llm_json(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )
