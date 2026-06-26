"""
PPT Engine - SVG编辑器服务器

Flask Web服务器，提供：
- SVG实时预览
- 标注和反馈
- 自动刷新
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# 检查Flask是否可用
try:
    from flask import Flask, render_template_string, jsonify, request, send_from_directory
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False


# HTML模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PPT Engine - SVG Preview</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
        }
        .header {
            background: #16213e;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #0f3460;
        }
        .header h1 {
            font-size: 18px;
            color: #e94560;
        }
        .controls {
            display: flex;
            gap: 10px;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }
        .btn-primary {
            background: #e94560;
            color: white;
        }
        .btn-primary:hover {
            background: #c73e54;
        }
        .btn-secondary {
            background: #0f3460;
            color: white;
        }
        .btn-secondary:hover {
            background: #1a4a8a;
        }
        .container {
            display: flex;
            height: calc(100vh - 60px);
        }
        .sidebar {
            width: 250px;
            background: #16213e;
            border-right: 1px solid #0f3460;
            overflow-y: auto;
            padding: 10px;
        }
        .sidebar h3 {
            font-size: 14px;
            color: #e94560;
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 1px solid #0f3460;
        }
        .page-list {
            list-style: none;
        }
        .page-item {
            padding: 10px;
            margin-bottom: 5px;
            background: #1a1a2e;
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.3s;
        }
        .page-item:hover {
            background: #0f3460;
        }
        .page-item.active {
            background: #e94560;
        }
        .page-item .page-num {
            font-weight: bold;
            color: #e94560;
        }
        .page-item .page-title {
            font-size: 12px;
            color: #aaa;
            margin-top: 4px;
        }
        .main {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            overflow: auto;
        }
        .svg-container {
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            max-width: 90%;
            max-height: 90%;
            overflow: auto;
        }
        .svg-container svg {
            display: block;
        }
        .info-bar {
            background: #16213e;
            padding: 10px 20px;
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            color: #aaa;
        }
        .annotation-panel {
            width: 300px;
            background: #16213e;
            border-left: 1px solid #0f3460;
            padding: 10px;
            display: none;
        }
        .annotation-panel.visible {
            display: block;
        }
        .annotation-panel h3 {
            font-size: 14px;
            color: #e94560;
            margin-bottom: 10px;
        }
        .annotation-input {
            width: 100%;
            padding: 8px;
            background: #1a1a2e;
            border: 1px solid #0f3460;
            border-radius: 4px;
            color: white;
            resize: vertical;
            min-height: 100px;
        }
        .annotation-list {
            margin-top: 10px;
        }
        .annotation-item {
            background: #1a1a2e;
            padding: 8px;
            margin-bottom: 5px;
            border-radius: 4px;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>PPT Engine - SVG Preview</h1>
        <div class="controls">
            <button class="btn btn-secondary" onclick="toggleAnnotations()">Annotations</button>
            <button class="btn btn-primary" onclick="refreshSVG()">Refresh</button>
        </div>
    </div>
    <div class="container">
        <div class="sidebar">
            <h3>Pages</h3>
            <ul class="page-list" id="pageList">
                {% for page in pages %}
                <li class="page-item {% if loop.index0 == 0 %}active{% endif %}"
                    onclick="selectPage({{ loop.index0 }})">
                    <span class="page-num">{{ loop.index }}</span>
                    <div class="page-title">{{ page.title }}</div>
                </li>
                {% endfor %}
            </ul>
        </div>
        <div class="main">
            <div class="svg-container" id="svgContainer">
                {{ svg_content|safe }}
            </div>
        </div>
        <div class="annotation-panel" id="annotationPanel">
            <h3>Annotations</h3>
            <textarea class="annotation-input" id="annotationInput"
                      placeholder="Add your annotation here..."></textarea>
            <button class="btn btn-primary" style="margin-top: 10px; width: 100%;"
                    onclick="saveAnnotation()">Save</button>
            <div class="annotation-list" id="annotationList"></div>
        </div>
    </div>
    <div class="info-bar">
        <span>Canvas: {{ canvas_width }} x {{ canvas_height }}</span>
        <span>Page: <span id="currentPage">1</span> / {{ pages|length }}</span>
    </div>
    <script>
        let currentPage = 0;
        let annotations = {};

        function selectPage(index) {
            currentPage = index;
            document.getElementById('currentPage').textContent = index + 1;

            // 更新页面列表高亮
            document.querySelectorAll('.page-item').forEach((item, i) => {
                item.classList.toggle('active', i === index);
            });

            // 加载SVG
            loadSVG(index);
        }

        function loadSVG(index) {
            fetch(`/api/svg/${index}`)
                .then(response => response.json())
                .then(data => {
                    document.getElementById('svgContainer').innerHTML = data.svg;
                });
        }

        function refreshSVG() {
            loadSVG(currentPage);
        }

        function toggleAnnotations() {
            document.getElementById('annotationPanel').classList.toggle('visible');
        }

        function saveAnnotation() {
            const input = document.getElementById('annotationInput');
            const text = input.value.trim();
            if (!text) return;

            if (!annotations[currentPage]) {
                annotations[currentPage] = [];
            }
            annotations[currentPage].push({
                text: text,
                timestamp: new Date().toISOString()
            });

            // 发送到服务器
            fetch('/api/annotations', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    page: currentPage,
                    text: text
                })
            });

            // 更新列表
            updateAnnotationList();
            input.value = '';
        }

        function updateAnnotationList() {
            const list = document.getElementById('annotationList');
            const pageAnnotations = annotations[currentPage] || [];
            list.innerHTML = pageAnnotations.map(a =>
                `<div class="annotation-item">${a.text}</div>`
            ).join('');
        }

        // 自动刷新（每5秒）
        setInterval(refreshSVG, 5000);
    </script>
</body>
</html>
'''


def create_app(project_path: str) -> Flask:
    """
    创建Flask应用

    参数:
        project_path: 项目路径

    返回:
        Flask应用实例
    """
    if not FLASK_AVAILABLE:
        raise ImportError("Flask not installed. Run: pip install flask")

    app = Flask(__name__)
    project_path = Path(project_path)
    svg_dir = project_path / 'svg_output'

    # 存储标注
    annotations_file = project_path / 'annotations.json'
    annotations = {}
    if annotations_file.exists():
        try:
            annotations = json.loads(annotations_file.read_text(encoding='utf-8'))
        except Exception:
            pass

    def get_svg_files():
        """获取SVG文件列表"""
        if not svg_dir.exists():
            return []
        return sorted(svg_dir.glob('*.svg'))

    def get_page_info(svg_file):
        """获取页面信息"""
        return {
            'filename': svg_file.name,
            'title': svg_file.stem.replace('slide_', 'Page '),
            'path': str(svg_file)
        }

    @app.route('/')
    def index():
        """首页"""
        svg_files = get_svg_files()
        pages = [get_page_info(f) for f in svg_files]

        # 读取第一个SVG
        svg_content = ''
        canvas_width = 1920
        canvas_height = 1080

        if svg_files:
            svg_content = svg_files[0].read_text(encoding='utf-8')
            # 提取viewBox
            import re
            match = re.search(r'viewBox="(\d+)\s+(\d+)\s+(\d+)\s+(\d+)"', svg_content)
            if match:
                canvas_width = int(match.group(3))
                canvas_height = int(match.group(4))

        return render_template_string(
            HTML_TEMPLATE,
            pages=pages,
            svg_content=svg_content,
            canvas_width=canvas_width,
            canvas_height=canvas_height
        )

    @app.route('/api/svg/<int:page_index>')
    def get_svg(page_index):
        """获取SVG内容"""
        svg_files = get_svg_files()
        if 0 <= page_index < len(svg_files):
            svg_content = svg_files[page_index].read_text(encoding='utf-8')
            return jsonify({'svg': svg_content})
        return jsonify({'error': 'Page not found'}), 404

    @app.route('/api/annotations', methods=['POST'])
    def save_annotation():
        """保存标注"""
        data = request.json
        page = data.get('page', 0)
        text = data.get('text', '')

        if page not in annotations:
            annotations[page] = []

        annotations[page].append({
            'text': text,
            'timestamp': data.get('timestamp', '')
        })

        # 保存到文件
        annotations_file.write_text(
            json.dumps(annotations, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

        return jsonify({'success': True})

    @app.route('/api/annotations')
    def get_annotations():
        """获取标注"""
        return jsonify(annotations)

    return app


def run_server(project_path: str, port: int = 5050, live: bool = False):
    """
    运行服务器

    参数:
        project_path: 项目路径
        port: 端口号
        live: 是否自动打开浏览器
    """
    if not FLASK_AVAILABLE:
        print("[ERROR] Flask not installed. Run: pip install flask")
        return

    app = create_app(project_path)

    if live:
        import webbrowser
        import threading

        def open_browser():
            webbrowser.open(f'http://localhost:{port}')

        threading.Timer(1.5, open_browser).start()

    print(f"[START] SVG Preview Server")
    print(f"   URL: http://localhost:{port}")
    print(f"   Project: {project_path}")
    print(f"   Press Ctrl+C to stop")

    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 5050
        run_server(project_path, port)
    else:
        print("Usage: python server.py <project_path> [port]")
