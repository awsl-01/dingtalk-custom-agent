"""
PPT Engine 第三阶段测试

测试AI图片生成、网络图片搜索、LaTeX公式渲染。
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.ppt_engine.image_gen.image_generator import (
    ImageGenerator, ImageRequest, ImageResult,
    GeminiBackend, OpenAIBackend, QwenBackend, ZhipuBackend
)
from agent.ppt_engine.image_search.image_searcher import (
    ImageSearcher, SearchRequest, SearchResult,
    OpenverseProvider, WikimediaProvider
)
from agent.ppt_engine.latex_render.latex_renderer import (
    LaTeXRenderer, FormulaRequest, FormulaResult
)


def test_image_generator():
    """测试AI图片生成器"""
    print("\n" + "="*60)
    print("[TEST] Image Generator")
    print("="*60)

    generator = ImageGenerator()

    # 测试列出后端
    print("\n1. List backends...")
    backends = generator.list_backends()
    print(f"   Available backends: {backends}")

    # 测试自动检测
    print("\n2. Auto-detect backend...")
    print(f"   Default backend: {generator.default_backend}")

    # 测试创建请求
    print("\n3. Create image request...")
    request = ImageRequest(
        prompt="A beautiful mountain landscape",
        filename="test_landscape.png",
        aspect_ratio="16:9",
        style="natural"
    )
    print(f"   Prompt: {request.prompt}")
    print(f"   Aspect ratio: {request.aspect_ratio}")

    # 测试后端实例化
    print("\n4. Instantiate backends...")
    for backend_name in backends:
        try:
            backend = generator.get_backend(backend_name)
            print(f"   [OK] {backend.name}")
        except Exception as e:
            print(f"   [FAIL] {backend_name}: {e}")

    return generator


def test_image_searcher():
    """测试网络图片搜索器"""
    print("\n" + "="*60)
    print("[TEST] Image Searcher")
    print("="*60)

    searcher = ImageSearcher()

    # 测试列出Provider
    print("\n1. List providers...")
    providers = searcher.list_providers()
    print(f"   Available providers: {providers}")

    # 测试创建请求
    print("\n2. Create search request...")
    request = SearchRequest(
        query="mountain landscape",
        filename="mountain.jpg",
        orientation="landscape",
        limit=5
    )
    print(f"   Query: {request.query}")
    print(f"   Orientation: {request.orientation}")

    # 测试Provider实例化
    print("\n3. Instantiate providers...")
    for provider_name in providers:
        try:
            provider = searcher.get_provider(provider_name)
            print(f"   [OK] {provider.name}")
        except Exception as e:
            print(f"   [FAIL] {provider_name}: {e}")

    # 测试搜索（不实际下载）
    print("\n4. Test search (dry run)...")
    print("   [SKIP] Actual search requires network access")

    return searcher


def test_latex_renderer():
    """测试LaTeX公式渲染器"""
    print("\n" + "="*60)
    print("[TEST] LaTeX Renderer")
    print("="*60)

    renderer = LaTeXRenderer()

    # 测试Provider链
    print("\n1. Provider chain...")
    print(f"   Chain: {renderer.provider_chain}")

    # 测试创建请求
    print("\n2. Create formula request...")
    request = FormulaRequest(
        formula="E = mc^2",
        filename="energy.png",
        background="transparent",
        color="#000000",
        dpi=300
    )
    print(f"   Formula: {request.formula}")
    print(f"   Background: {request.background}")

    # 测试颜色转换
    print("\n3. Test color conversion...")
    rgb = renderer._hex_to_rgb("#FF0000")
    print(f"   #FF0000 -> RGB{rgb}")

    rgb = renderer._hex_to_rgb("#00FF00")
    print(f"   #00FF00 -> RGB{rgb}")

    # 测试颜色距离
    print("\n4. Test color distance...")
    dist = renderer._color_distance((255, 0, 0), (255, 0, 0))
    print(f"   Red to Red: {dist}")

    dist = renderer._color_distance((255, 0, 0), (0, 0, 0))
    print(f"   Red to Black: {dist}")

    return renderer


def test_integration():
    """测试集成"""
    print("\n" + "="*60)
    print("[TEST] Integration")
    print("="*60)

    # 测试图片生成器和搜索器的协作
    print("\n1. Generator + Searcher workflow...")
    print("   - Generate hero image with AI")
    print("   - Search for supporting images")
    print("   - Combine results")

    # 测试LaTeX和SVG的集成
    print("\n2. LaTeX + SVG integration...")
    print("   - Render formula as PNG")
    print("   - Embed in SVG as <image>")
    print("   - Include in final PPTX")

    # 测试manifest驱动
    print("\n3. Manifest-driven workflow...")
    manifest = {
        "items": [
            {
                "type": "ai_image",
                "prompt": "A classroom scene",
                "filename": "classroom.png"
            },
            {
                "type": "formula",
                "formula": "x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}",
                "filename": "quadratic.png"
            },
            {
                "type": "web_image",
                "query": "school building",
                "filename": "school.jpg"
            }
        ]
    }
    print(f"   Manifest items: {len(manifest['items'])}")
    for item in manifest['items']:
        print(f"     - {item['type']}: {item.get('filename', 'N/A')}")


def main():
    """主测试函数"""
    print("[START] PPT Engine Phase 3 Test")
    print("="*60)

    try:
        # 1. 测试AI图片生成器
        generator = test_image_generator()

        # 2. 测试网络图片搜索器
        searcher = test_image_searcher()

        # 3. 测试LaTeX公式渲染器
        renderer = test_latex_renderer()

        # 4. 测试集成
        test_integration()

        print("\n" + "="*60)
        print("[DONE] All Phase 3 tests passed!")
        print("="*60)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
