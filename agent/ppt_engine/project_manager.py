"""
PPT Engine - 项目管理模块

功能：
- 创建项目目录结构
- 导入源文件
- 验证项目结构
- 查询项目信息

使用方式：
    python -m agent.ppt_engine.project_manager init <project_name> [--format ppt169]
    python -m agent.ppt_engine.project_manager import-sources <project_path> <source_files...>
    python -m agent.ppt_engine.project_manager validate <project_path>
    python -m agent.ppt_engine.project_manager info <project_path>
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any


# 画布格式定义
CANVAS_FORMATS = {
    'ppt169': {
        'name': 'PPT 16:9',
        'width': 1920,
        'height': 1080,
        'description': '标准宽屏演示文稿'
    },
    'ppt43': {
        'name': 'PPT 4:3',
        'width': 1440,
        'height': 1080,
        'description': '传统演示文稿'
    },
    'xhs': {
        'name': '小红书',
        'width': 1080,
        'height': 1440,
        'description': '小红书竖版图片'
    },
    'story': {
        'name': '故事',
        'width': 1080,
        'height': 1920,
        'description': '竖版故事'
    }
}

# 支持的源文件格式
SUPPORTED_FORMATS = {
    # 文本格式
    '.md', '.markdown', '.txt',
    # 表格格式
    '.csv', '.tsv',
    # PDF格式
    '.pdf',
    # 演示文稿格式
    '.pptx', '.pptm', '.ppsx', '.ppsm', '.potx', '.potm',
    # Excel格式
    '.xlsx', '.xlsm',
    # 文档格式
    '.docx', '.doc', '.odt', '.rtf',
    # 电子书格式
    '.epub',
    # 网页格式
    '.html', '.htm',
    # 学术格式
    '.tex', '.latex', '.rst', '.org',
    # 其他格式
    '.ipynb', '.typ'
}

# 图片资源格式
IMAGE_FORMATS = {
    '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.tif',
    '.emf', '.wmf', '.svg'
}


def get_project_dir(project_name: str, base_dir: str = None) -> Path:
    """获取项目目录路径"""
    if base_dir:
        return Path(base_dir) / project_name
    return Path(__file__).parent.parent.parent / 'projects' / project_name


def init_project(project_name: str, canvas_format: str = 'ppt169',
                 base_dir: str = None) -> Path:
    """
    初始化项目

    参数:
        project_name: 项目名称
        canvas_format: 画布格式（ppt169/ppt43/xhs/story）
        base_dir: 基础目录（默认为 projects/）

    返回:
        项目目录路径
    """
    if canvas_format not in CANVAS_FORMATS:
        raise ValueError(f"不支持的画布格式: {canvas_format}，支持: {list(CANVAS_FORMATS.keys())}")

    project_dir = get_project_dir(project_name, base_dir)

    # 创建项目目录结构
    directories = [
        'sources',
        'images',
        'svg_output',
        'svg_final',
        'notes',
        'exports',
        'templates',
        'backup'
    ]

    for dir_name in directories:
        (project_dir / dir_name).mkdir(parents=True, exist_ok=True)

    # 创建项目配置文件
    config = {
        'name': project_name,
        'canvas_format': canvas_format,
        'canvas': CANVAS_FORMATS[canvas_format],
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'status': 'initialized',
        'source_files': [],
        'page_count': 0
    }

    config_path = project_dir / 'project.json'
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    # 创建空的 design_spec.md
    design_spec = f"""# {project_name}

## 画布格式

- 格式: {CANVAS_FORMATS[canvas_format]['name']}
- 尺寸: {CANVAS_FORMATS[canvas_format]['width']} x {CANVAS_FORMATS[canvas_format]['height']}

## 设计规范

（待填充）

## 内容大纲

（待填充）
"""
    (project_dir / 'design_spec.md').write_text(design_spec, encoding='utf-8')

    # 创建空的 spec_lock.md
    spec_lock = """# 执行锁定

## 颜色方案

（待填充）

## 字体方案

（待填充）

## 页面列表

（待填充）
"""
    (project_dir / 'spec_lock.md').write_text(spec_lock, encoding='utf-8')

    print(f"[OK] Project created: {project_dir}")
    print(f"   Canvas: {CANVAS_FORMATS[canvas_format]['name']}")
    print(f"   Size: {CANVAS_FORMATS[canvas_format]['width']} x {CANVAS_FORMATS[canvas_format]['height']}")

    return project_dir


def import_sources(project_path: str, source_files: List[str],
                   move: bool = False) -> List[Path]:
    """
    导入源文件到项目

    参数:
        project_path: 项目路径
        source_files: 源文件列表
        move: 是否移动（True）而非复制（False）

    返回:
        导入的文件路径列表
    """
    project_dir = Path(project_path)
    sources_dir = project_dir / 'sources'

    if not project_dir.exists():
        raise FileNotFoundError(f"项目不存在: {project_path}")

    imported_files = []

    for source_file in source_files:
        source_path = Path(source_file)

        if not source_path.exists():
            print(f"⚠️ 文件不存在: {source_file}")
            continue

        # 检查文件格式
        ext = source_path.suffix.lower()
        if ext not in SUPPORTED_FORMATS and ext not in IMAGE_FORMATS:
            print(f"[WARN] Unsupported format: {source_file}")
            continue

        # 复制或移动文件
        dest_path = sources_dir / source_path.name

        if move:
            shutil.move(str(source_path), str(dest_path))
            print(f"[MOVE] {source_path.name}")
        else:
            shutil.copy2(str(source_path), str(dest_path))
            print(f"[COPY] {source_path.name}")

        imported_files.append(dest_path)

    # 更新项目配置
    config_path = project_dir / 'project.json'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        config['source_files'].extend([f.name for f in imported_files])
        config['updated_at'] = datetime.now().isoformat()
        config['status'] = 'sources_imported'

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Import completed: {len(imported_files)} files")

    return imported_files


def validate_project(project_path: str) -> Dict[str, Any]:
    """
    验证项目结构

    参数:
        project_path: 项目路径

    返回:
        验证结果字典
    """
    project_dir = Path(project_path)

    if not project_dir.exists():
        return {'valid': False, 'error': f'项目不存在: {project_path}'}

    issues = []

    # 检查必需目录
    required_dirs = ['sources', 'images', 'svg_output', 'svg_final', 'notes', 'exports']
    for dir_name in required_dirs:
        if not (project_dir / dir_name).exists():
            issues.append(f'缺少目录: {dir_name}')

    # 检查配置文件
    config_path = project_dir / 'project.json'
    if not config_path.exists():
        issues.append('缺少配置文件: project.json')
    else:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 检查画布格式
            if config.get('canvas_format') not in CANVAS_FORMATS:
                issues.append(f"无效的画布格式: {config.get('canvas_format')}")
        except json.JSONDecodeError:
            issues.append('配置文件格式错误: project.json')

    # 检查设计规范文件
    if not (project_dir / 'design_spec.md').exists():
        issues.append('缺少设计规范: design_spec.md')

    if not (project_dir / 'spec_lock.md').exists():
        issues.append('缺少执行锁定: spec_lock.md')

    # 统计文件数量
    source_count = len(list((project_dir / 'sources').glob('*'))) if (project_dir / 'sources').exists() else 0
    svg_count = len(list((project_dir / 'svg_output').glob('*.svg'))) if (project_dir / 'svg_output').exists() else 0
    export_count = len(list((project_dir / 'exports').glob('*.pptx'))) if (project_dir / 'exports').exists() else 0

    result = {
        'valid': len(issues) == 0,
        'issues': issues,
        'stats': {
            'source_files': source_count,
            'svg_pages': svg_count,
            'exported_pptx': export_count
        }
    }

    return result


def get_project_info(project_path: str) -> Dict[str, Any]:
    """
    获取项目信息

    参数:
        project_path: 项目路径

    返回:
        项目信息字典
    """
    project_dir = Path(project_path)

    if not project_dir.exists():
        raise FileNotFoundError(f"项目不存在: {project_path}")

    # 读取配置
    config_path = project_dir / 'project.json'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {'name': project_dir.name}

    # 统计文件
    sources_dir = project_dir / 'sources'
    svg_dir = project_dir / 'svg_output'
    exports_dir = project_dir / 'exports'

    source_files = list(sources_dir.glob('*')) if sources_dir.exists() else []
    svg_files = list(svg_dir.glob('*.svg')) if svg_dir.exists() else []
    export_files = list(exports_dir.glob('*.pptx')) if exports_dir.exists() else []

    # 获取画布信息
    canvas_format = config.get('canvas_format', 'ppt169')
    canvas = CANVAS_FORMATS.get(canvas_format, CANVAS_FORMATS['ppt169'])

    info = {
        'name': config.get('name', project_dir.name),
        'path': str(project_dir),
        'canvas_format': canvas_format,
        'canvas': canvas,
        'created_at': config.get('created_at'),
        'updated_at': config.get('updated_at'),
        'status': config.get('status', 'unknown'),
        'files': {
            'sources': len(source_files),
            'svgs': len(svg_files),
            'exports': len(export_files)
        },
        'source_names': [f.name for f in source_files[:10]],  # 最多显示10个
        'export_names': [f.name for f in export_files]
    }

    return info


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='PPT Engine 项目管理')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # init 命令
    init_parser = subparsers.add_parser('init', help='初始化项目')
    init_parser.add_argument('project_name', help='项目名称')
    init_parser.add_argument('--format', default='ppt169',
                           choices=list(CANVAS_FORMATS.keys()),
                           help='画布格式')
    init_parser.add_argument('--dir', help='基础目录')

    # import-sources 命令
    import_parser = subparsers.add_parser('import-sources', help='导入源文件')
    import_parser.add_argument('project_path', help='项目路径')
    import_parser.add_argument('source_files', nargs='+', help='源文件列表')
    import_parser.add_argument('--move', action='store_true', help='移动而非复制')

    # validate 命令
    validate_parser = subparsers.add_parser('validate', help='验证项目')
    validate_parser.add_argument('project_path', help='项目路径')

    # info 命令
    info_parser = subparsers.add_parser('info', help='项目信息')
    info_parser.add_argument('project_path', help='项目路径')

    args = parser.parse_args()

    if args.command == 'init':
        init_project(args.project_name, args.format, args.dir)

    elif args.command == 'import-sources':
        import_sources(args.project_path, args.source_files, args.move)

    elif args.command == 'validate':
        result = validate_project(args.project_path)
        if result['valid']:
            print("[OK] Project validation passed")
        else:
            print("[FAIL] Project validation failed:")
            for issue in result['issues']:
                print(f"   - {issue}")
        print(f"\n[STATS]")
        print(f"   Source files: {result['stats']['source_files']}")
        print(f"   SVG pages: {result['stats']['svg_pages']}")
        print(f"   Exported PPTX: {result['stats']['exported_pptx']}")

    elif args.command == 'info':
        info = get_project_info(args.project_path)
        print(f"[PROJECT] {info['name']}")
        print(f"   Path: {info['path']}")
        print(f"   Canvas: {info['canvas']['name']} ({info['canvas']['width']}x{info['canvas']['height']})")
        print(f"   Status: {info['status']}")
        print(f"\n[FILES]")
        print(f"   Sources: {info['files']['sources']}")
        print(f"   SVGs: {info['files']['svgs']}")
        print(f"   Exports: {info['files']['exports']}")
        if info['source_names']:
            print(f"\n[SOURCE FILES]")
            for name in info['source_names']:
                print(f"   - {name}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
