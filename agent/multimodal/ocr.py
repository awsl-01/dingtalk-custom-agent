"""
OCR 引擎

从图片中提取文字，支持多种策略：
1. 本地 OCR（PaddleOCR）
2. API OCR（百度/腾讯）
3. LLM OCR（多模态模型，推荐）
"""
import os
import logging
import base64
from typing import Dict, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """OCR 结果"""
    text: str                    # 识别的文字
    confidence: float = 0.0      # 置信度
    regions: list = field(default_factory=list)  # 文字区域
    strategy: str = ""           # 使用的策略
    error: str = ""              # 错误信息


@dataclass
class TextRegion:
    """文字区域"""
    text: str           # 文字内容
    confidence: float   # 置信度
    bbox: list = field(default_factory=list)  # 边界框 [x1, y1, x2, y2]


class OCREngine:
    """
    OCR 引擎

    支持多种 OCR 策略：
    - local: 本地 PaddleOCR（需要安装 paddleocr）
    - api: 第三方 API（百度/腾讯）
    - llm: 多模态 LLM（推荐，如 GPT-4V、Claude）
    """

    def __init__(self, default_strategy: str = "llm"):
        """
        初始化 OCR 引擎

        参数:
            default_strategy: 默认策略
        """
        self._default_strategy = default_strategy
        self._strategies = {
            "local": self._ocr_local,
            "api": self._ocr_api,
            "llm": self._ocr_llm,
        }

        # 延迟初始化的组件
        self._paddle_ocr = None
        self._llm_client = None

    async def recognize(self, image_path: str,
                       strategy: str = None,
                       language: str = "ch") -> OCRResult:
        """
        识别图片中的文字

        参数:
            image_path: 图片路径
            strategy: 识别策略（None 使用默认策略）
            language: 语言（ch/en/japan/korean）

        返回:
            OCR 结果
        """
        strategy = strategy or self._default_strategy

        if not os.path.exists(image_path):
            return OCRResult(
                text="",
                error=f"图片不存在: {image_path}",
                strategy=strategy
            )

        # 检查文件大小
        file_size = os.path.getsize(image_path)
        if file_size > 20 * 1024 * 1024:  # 20MB
            return OCRResult(
                text="",
                error="图片文件过大（>20MB）",
                strategy=strategy
            )

        # 调用对应的策略
        ocr_func = self._strategies.get(strategy)
        if not ocr_func:
            return OCRResult(
                text="",
                error=f"不支持的 OCR 策略: {strategy}",
                strategy=strategy
            )

        try:
            result = await ocr_func(image_path, language)
            result.strategy = strategy
            return result
        except Exception as e:
            logger.error(f"OCR 识别失败: {e}")
            return OCRResult(
                text="",
                error=str(e),
                strategy=strategy
            )

    async def _ocr_local(self, image_path: str,
                         language: str = "ch") -> OCRResult:
        """
        本地 OCR（PaddleOCR）

        需要安装：pip install paddleocr paddlepaddle
        """
        try:
            # 延迟导入
            if self._paddle_ocr is None:
                try:
                    from paddleocr import PaddleOCR
                    self._paddle_ocr = PaddleOCR(
                        use_angle_cls=True,
                        lang=language,
                        show_log=False
                    )
                except ImportError:
                    return OCRResult(
                        text="",
                        error="需要安装 PaddleOCR: pip install paddleocr paddlepaddle"
                    )

            # 执行 OCR
            result = self._paddle_ocr.ocr(image_path, cls=True)

            if not result or not result[0]:
                return OCRResult(text="", confidence=0.0)

            # 解析结果
            texts = []
            regions = []
            total_confidence = 0.0

            for line in result[0]:
                bbox = line[0]
                text = line[1][0]
                confidence = line[1][1]

                texts.append(text)
                total_confidence += confidence

                regions.append(TextRegion(
                    text=text,
                    confidence=confidence,
                    bbox=[int(bbox[0][0]), int(bbox[0][1]),
                          int(bbox[2][0]), int(bbox[2][1])]
                ))

            avg_confidence = total_confidence / len(regions) if regions else 0.0

            return OCRResult(
                text="\n".join(texts),
                confidence=avg_confidence,
                regions=[r.__dict__ for r in regions]
            )

        except Exception as e:
            logger.error(f"本地 OCR 失败: {e}")
            raise

    async def _ocr_api(self, image_path: str,
                       language: str = "ch") -> OCRResult:
        """
        API OCR（百度/腾讯）

        需要配置 API 密钥
        """
        try:
            import httpx
            import config

            # 读取图片并编码
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()

            # 调用百度 OCR API
            api_key = getattr(config, 'BAIDU_OCR_API_KEY', '')
            secret_key = getattr(config, 'BAIDU_OCR_SECRET_KEY', '')

            if not api_key or not secret_key:
                return OCRResult(
                    text="",
                    error="需要配置百度 OCR API 密钥（BAIDU_OCR_API_KEY, BAIDU_OCR_SECRET_KEY）"
                )

            # 获取 access_token
            token_url = "https://aip.baidubce.com/oauth/2.0/token"
            async with httpx.AsyncClient() as client:
                token_resp = await client.post(token_url, data={
                    "grant_type": "client_credentials",
                    "client_id": api_key,
                    "client_secret": secret_key
                })
                access_token = token_resp.json().get("access_token")

                # 调用 OCR
                ocr_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}"
                resp = await client.post(ocr_url, data={
                    "image": image_data,
                    "language_type": "CHN_ENG" if language == "ch" else "ENG"
                })

                result = resp.json()
                if "words_result" in result:
                    texts = [item["words"] for item in result["words_result"]]
                    return OCRResult(
                        text="\n".join(texts),
                        confidence=0.9
                    )
                else:
                    return OCRResult(
                        text="",
                        error=f"API 返回错误: {result.get('error_msg', '未知错误')}"
                    )

        except ImportError:
            return OCRResult(
                text="",
                error="需要安装 httpx: pip install httpx"
            )
        except Exception as e:
            logger.error(f"API OCR 失败: {e}")
            raise

    async def _ocr_llm(self, image_path: str,
                       language: str = "ch") -> OCRResult:
        """
        LLM OCR（多模态模型）

        使用 GPT-4V 或 Claude 进行图片文字识别
        """
        try:
            import config

            # 读取图片并编码
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()

            # 构建提示词
            prompt = """请识别这张图片中的所有文字内容。

要求：
1. 保留原始格式和布局
2. 按照从上到下、从左到右的顺序
3. 如果有表格，用 Markdown 表格格式输出
4. 如果有标题、正文等层次结构，保留层次
5. 只输出识别的文字，不要添加解释

请开始识别："""

            # 调用 LLM
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=config.OPENAI_API_KEY,
                base_url=config.OPENAI_BASE_URL
            )

            response = await client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096
            )

            text = response.choices[0].message.content

            return OCRResult(
                text=text,
                confidence=0.95  # LLM 通常有较高的准确率
            )

        except ImportError:
            return OCRResult(
                text="",
                error="需要安装 openai: pip install openai"
            )
        except Exception as e:
            logger.error(f"LLM OCR 失败: {e}")
            raise

    async def recognize_batch(self, image_paths: List[str],
                              strategy: str = None,
                              language: str = "ch") -> List[OCRResult]:
        """
        批量识别图片

        参数:
            image_paths: 图片路径列表
            strategy: 识别策略
            language: 语言

        返回:
            OCR 结果列表
        """
        results = []
        for path in image_paths:
            result = await self.recognize(path, strategy, language)
            results.append(result)
        return results

    def get_supported_languages(self) -> List[str]:
        """获取支持的语言"""
        return ["ch", "en", "japan", "korean", "fr", "german", "italian"]

    def get_available_strategies(self) -> List[str]:
        """获取可用的策略"""
        return list(self._strategies.keys())


# 全局 OCR 引擎实例
_ocr_engine: Optional[OCREngine] = None


def get_ocr_engine(default_strategy: str = "llm") -> OCREngine:
    """获取全局 OCR 引擎实例"""
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = OCREngine(default_strategy)
    return _ocr_engine
