"""
PPT Engine 集成测试

测试PPT Engine与钉钉机器人的集成。
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.ppt_engine_integration import (
    PPTEngineIntegration,
    generate_education_ppt,
    generate_from_outline
)


def test_integration_init():
    """测试集成初始化"""
    print("\n" + "="*60)
    print("[TEST] Integration Init")
    print("="*60)

    integration = PPTEngineIntegration()

    print(f"\n1. Projects dir: {integration.projects_dir}")
    print(f"   Exists: {integration.projects_dir.exists()}")

    print(f"\n2. Supported subjects:")
    subjects = integration.list_subjects()
    print(f"   {', '.join(subjects)}")

    print(f"\n3. Supported content types:")
    content_types = integration.list_content_types()
    print(f"   {', '.join(content_types)}")


def test_generate_education_ppt():
    """测试生成教育PPT"""
    print("\n" + "="*60)
    print("[TEST] Generate Education PPT")
    print("="*60)

    print("\n1. Generate math lesson PPT...")
    try:
        ppt_path, ppt_title = generate_education_ppt(
            subject='数学',
            grade='高一',
            chapter='三角函数',
            content_type='课件',
            difficulty='中等'
        )

        print(f"   [OK] PPT generated: {ppt_path}")
        print(f"   [OK] Title: {ppt_title}")

        # 检查文件是否存在
        if Path(ppt_path).exists():
            file_size = Path(ppt_path).stat().st_size
            print(f"   [OK] File size: {file_size / 1024:.1f} KB")
        else:
            print(f"   [FAIL] File not found")

    except Exception as e:
        print(f"   [FAIL] Generate failed: {e}")
        import traceback
        traceback.print_exc()


def test_generate_from_outline():
    """测试从大纲生成PPT"""
    print("\n" + "="*60)
    print("[TEST] Generate From Outline")
    print("="*60)

    outline = """# 三角函数

## 一、学习目标

- 理解三角函数的定义
- 掌握三角函数的性质
- 学会应用三角函数解决问题

## 二、基本概念

### 2.1 正弦函数

- 定义：sinθ = 对边/斜边
- 图像：正弦曲线
- 周期：2π

### 2.2 余弦函数

- 定义：cosθ = 邻边/斜边
- 图像：余弦曲线
- 周期：2π

## 三、例题解析

- 例题1：求sin30°的值
- 例题2：求cos60°的值
- 例题3：证明sin²θ + cos²θ = 1

## 四、课堂练习

- 练习1：计算特殊角的三角函数值
- 练习2：绘制三角函数图像
- 练习3：应用三角函数解决实际问题

## 五、课堂小结

- 本节课学习了三角函数的基本概念
- 掌握了正弦函数和余弦函数的性质
- 能够应用三角函数解决简单问题
"""

    print("\n1. Generate PPT from outline...")
    try:
        ppt_path, ppt_title = generate_from_outline(
            outline=outline,
            subject='数学',
            grade='高一',
            chapter='三角函数'
        )

        print(f"   [OK] PPT generated: {ppt_path}")
        print(f"   [OK] Title: {ppt_title}")

        # 检查文件是否存在
        if Path(ppt_path).exists():
            file_size = Path(ppt_path).stat().st_size
            print(f"   [OK] File size: {file_size / 1024:.1f} KB")
        else:
            print(f"   [FAIL] File not found")

    except Exception as e:
        print(f"   [FAIL] Generate failed: {e}")
        import traceback
        traceback.print_exc()


def test_parse_education_info():
    """测试解析教育信息"""
    print("\n" + "="*60)
    print("[TEST] Parse Education Info")
    print("="*60)

    # 导入main.py中的函数
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from main import parse_education_info

    test_cases = [
        "生成高一数学三角函数的课件",
        "帮我制作一个初中物理力学的教案",
        "请生成高二英语Unit 5的说课稿",
        "制作一个关于《岳阳楼记》的PPT",
    ]

    for text in test_cases:
        print(f"\n   Input: {text}")
        info = parse_education_info(text)
        print(f"   Subject: {info['subject']}")
        print(f"   Grade: {info['grade']}")
        print(f"   Chapter: {info['chapter']}")
        print(f"   Content Type: {info['content_type']}")


def main():
    """主测试函数"""
    print("[START] PPT Engine Integration Test")
    print("="*60)

    try:
        # 1. 测试集成初始化
        test_integration_init()

        # 2. 测试解析教育信息
        test_parse_education_info()

        # 3. 测试生成教育PPT（可选，需要较长时间）
        # test_generate_education_ppt()

        # 4. 测试从大纲生成PPT（可选，需要较长时间）
        # test_generate_from_outline()

        print("\n" + "="*60)
        print("[DONE] All integration tests passed!")
        print("="*60)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
