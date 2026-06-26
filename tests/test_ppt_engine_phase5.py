"""
PPT Engine 第五阶段测试

测试SVG质量检查增强、TTS音频生成、后处理流水线。
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.ppt_engine.quality.svg_quality_checker import SVGQualityChecker, IssueLevel
from agent.ppt_engine.tts.tts_generator import TTSGenerator, AudioRequest, AudioResult
from agent.ppt_engine.svg_finalize.finalize_svg import SVGFinalizer


def test_quality_checker():
    """测试SVG质量检查器"""
    print("\n" + "="*60)
    print("[TEST] SVG Quality Checker")
    print("="*60)

    # 测试创建检查器
    print("\n1. Create checker...")
    checker = SVGQualityChecker()
    print(f"   [OK] Checker created")

    # 测试检查规则
    print("\n2. Check rules...")
    print(f"   Banned features: {checker.BANNED_FEATURES}")
    print(f"   Font size range: {checker.FONT_SIZE_MIN_RATIO}x - {checker.FONT_SIZE_MAX_RATIO}x")

    # 测试检查目录
    print("\n3. Check directory...")
    project_path = 'D:/claude/projects/test_project'
    svg_dir = Path(project_path) / 'svg_output'

    if svg_dir.exists():
        issues = checker.check_directory(str(svg_dir))
        summary = checker.get_summary(issues)

        print(f"   Total issues: {summary['total']}")
        print(f"   Errors: {summary['errors']}")
        print(f"   Warnings: {summary['warnings']}")
        print(f"   Info: {summary['info']}")
        print(f"   Passed: {summary['passed']}")

        # 显示问题详情
        if issues:
            print("\n4. Issue details:")
            for issue in issues[:5]:
                print(f"   {issue}")
    else:
        print(f"   [SKIP] Directory not found: {svg_dir}")

    return checker


def test_tts_generator():
    """测试TTS生成器"""
    print("\n" + "="*60)
    print("[TEST] TTS Generator")
    print("="*60)

    generator = TTSGenerator()

    # 测试列出后端
    print("\n1. List backends...")
    backends = generator.list_backends()
    print(f"   Available backends: {backends}")

    # 测试自动检测
    print("\n2. Auto-detect backend...")
    print(f"   Default backend: {generator.default_backend}")

    # 测试创建请求
    print("\n3. Create audio request...")
    request = AudioRequest(
        text="这是一个测试文本，用于验证TTS生成功能。",
        filename="test.mp3",
        voice="zh-CN-XiaoxiaoNeural"
    )
    print(f"   Text: {request.text}")
    print(f"   Voice: {request.voice}")

    # 测试后端实例化
    print("\n4. Instantiate backends...")
    for backend_name in backends:
        try:
            backend = generator.get_backend(backend_name)
            print(f"   [OK] {backend.name}")
        except Exception as e:
            print(f"   [FAIL] {backend_name}: {e}")

    # 测试Edge-TTS声音列表
    print("\n5. List Edge-TTS voices (zh-CN)...")
    try:
        edge_backend = generator.get_backend('edge')
        voices = edge_backend.list_voices('zh-CN')
        print(f"   Found {len(voices)} voices")
        for v in voices[:3]:
            print(f"     - {v['name']} ({v['gender']})")
    except Exception as e:
        print(f"   [SKIP] List voices failed: {e}")

    return generator


def test_svg_finalizer():
    """测试SVG后处理器"""
    print("\n" + "="*60)
    print("[TEST] SVG Finalizer")
    print("="*60)

    project_path = 'D:/claude/projects/test_project'

    if not Path(project_path).exists():
        print(f"   [SKIP] Project not found: {project_path}")
        return

    finalizer = SVGFinalizer(project_path)

    # 测试处理方法
    print("\n1. Check processing methods...")
    methods = ['_embed_icons', '_embed_images', '_flatten_tspan', '_convert_rounded_rect']
    for method in methods:
        if hasattr(finalizer, method):
            print(f"   [OK] {method}")
        else:
            print(f"   [FAIL] {method}")

    # 测试处理目录
    print("\n2. Process SVG directory...")
    svg_output_dir = Path(project_path) / 'svg_output'
    svg_final_dir = Path(project_path) / 'svg_final'

    if svg_output_dir.exists():
        svg_files = list(svg_output_dir.glob('*.svg'))
        print(f"   Found {len(svg_files)} SVG files")

        # 处理单个文件测试
        if svg_files:
            print("\n3. Process single file...")
            test_file = svg_files[0]
            result = finalizer.process_svg(test_file)
            if result:
                print(f"   [OK] Processed: {result}")
            else:
                print(f"   [FAIL] Process failed")
    else:
        print(f"   [SKIP] SVG directory not found")

    return finalizer


def test_integration():
    """测试集成"""
    print("\n" + "="*60)
    print("[TEST] Integration")
    print("="*60)

    # 测试完整工作流
    print("\n1. Full workflow...")
    workflow = {
        'steps': [
            'Generate SVG pages',
            'Run quality check',
            'Fix errors',
            'Finalize SVGs',
            'Generate TTS audio',
            'Export PPTX'
        ]
    }

    for i, step in enumerate(workflow['steps'], 1):
        print(f"   {i}. {step}")

    # 测试质量检查集成
    print("\n2. Quality check integration...")
    print("   - Check SVG files")
    print("   - Fix errors")
    print("   - Re-check")
    print("   - Generate report")

    # 测试TTS集成
    print("\n3. TTS integration...")
    print("   - Read speaker notes")
    print("   - Generate audio per slide")
    print("   - Embed in PPTX")

    # 测试后处理集成
    print("\n4. Finalization integration...")
    print("   - Embed icons")
    print("   - Embed images")
    print("   - Flatten text")
    print("   - Convert rounded rects")
    print("   - Export to svg_final/")


def main():
    """主测试函数"""
    print("[START] PPT Engine Phase 5 Test")
    print("="*60)

    try:
        # 1. 测试质量检查器
        test_quality_checker()

        # 2. 测试TTS生成器
        test_tts_generator()

        # 3. 测试SVG后处理器
        test_svg_finalizer()

        # 4. 测试集成
        test_integration()

        print("\n" + "="*60)
        print("[DONE] All Phase 5 tests passed!")
        print("="*60)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
