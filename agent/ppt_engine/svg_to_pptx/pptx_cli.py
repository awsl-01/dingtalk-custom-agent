"""
PPT Engine - SVG转PPTX命令行入口

使用方式：
    python -m agent.ppt_engine.svg_to_pptx.pptx_cli <project_path> [--format ppt169]
"""

import argparse
import sys
from pathlib import Path

from .pptx_builder import PPTXBuilder


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='SVG转PPTX')
    parser.add_argument('project_path', help='项目路径')
    parser.add_argument('--format', default='ppt169',
                       choices=['ppt169', 'ppt43', 'xhs', 'story'],
                       help='画布格式')
    parser.add_argument('--output', '-o', help='输出路径')
    parser.add_argument('--svg-dir', help='SVG目录（默认为svg_output）')
    parser.add_argument('--notes-dir', help='备注目录（默认为notes）')

    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        print(f"[ERROR] Project not found: {project_path}")
        sys.exit(1)

    # 确定SVG目录
    svg_dir = args.svg_dir or str(project_path / 'svg_output')
    notes_dir = args.notes_dir or str(project_path / 'notes')

    # 读取项目配置以确定格式
    config_path = project_path / 'project.json'
    if config_path.exists():
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        canvas_format = config.get('canvas_format', args.format)
    else:
        canvas_format = args.format

    try:
        builder = PPTXBuilder(canvas_format)
        output_path = builder.build_from_svg_dir(
            svg_dir,
            notes_dir if Path(notes_dir).exists() else None,
            args.output
        )
        print(f"\n[OK] Conversion completed: {output_path}")

    except Exception as e:
        print(f"\n[ERROR] Conversion failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
