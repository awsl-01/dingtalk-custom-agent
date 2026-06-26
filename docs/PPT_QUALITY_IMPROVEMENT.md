# PPT 质量改进方案

## 问题分析

### 当前实现 vs ppt-master 对比

| 维度 | 当前实现 | ppt-master | 差距 |
|------|----------|------------|------|
| **SVG文件大小** | 1-7KB | 2-8KB | 接近 |
| **页数** | 7页 | 12页 | 较少 |
| **装饰元素** | 简单矩形 | 渐变、圆形、阴影 | 较差 |
| **配色方案** | 通用配色 | 学科专属配色 | 较差 |
| **模板继承** | 无 | 从模板SVG继承 | 缺失 |
| **spec_lock重读** | 无 | 每页重读 | 缺失 |

### 具体问题

#### 1. 装饰元素不足

**当前实现：**
```svg
<rect width="1280" height="720" fill="#FAFAFA" />
<rect x="0" y="0" width="1280" height="100" fill="#37474F" />
```

**ppt-master：**
```svg
<rect width="1280" height="720" fill="#FBF8F1" />
<rect width="1280" height="720" fill="url(#coverGrad)" />
<circle cx="80" cy="120" r="60" fill="#5B7F5E" fill-opacity="0.06" />
<circle cx="140" cy="200" r="40" fill="#5B7F5E" fill-opacity="0.04" />
```

**差异：** ppt-master有渐变背景、装饰圆形、透明度效果

#### 2. 配色方案不匹配

**当前实现：**
- 使用通用配色：#37474F, #1976D2
- 不根据学科调整

**ppt-master：**
- 使用学科专属配色
- 语文：#5B7F5E, #C4883A（文学、典雅）
- 数学：#1A5276, #E74C3C（严谨、逻辑）

#### 3. 缺少模板继承

**当前实现：**
- 每页独立生成
- 不继承模板设计

**ppt-master：**
- 从模板SVG继承设计元素
- 保持视觉一致性

---

## 改进方案

### 方案1：增强SVG生成逻辑（推荐）

修改 `ppt_master_integration.py` 中的 `generate_svg_with_executor` 函数：

```python
def generate_svg_with_executor(page_spec, theme, ...):
    # 1. 读取模板SVG（如果有）
    template_svg = read_template_svg(page_spec['layout'])

    # 2. 应用学科专属配色
    subject_theme = get_subject_theme(subject)

    # 3. 添加装饰元素
    decorations = generate_decorations(page_spec['layout'], subject_theme)

    # 4. 生成SVG
    svg = generate_svg_with_enhancements(
        page_spec=page_spec,
        theme=subject_theme,
        template=template_svg,
        decorations=decorations
    )

    return svg
```

### 方案2：集成ppt-master的Executor

直接调用ppt-master的Executor脚本：

```python
def generate_svg_with_ppt_master_executor(page_spec, project_path):
    # 调用ppt-master的Executor
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "executor.py"),
        "--page-spec", json.dumps(page_spec),
        "--project-path", str(project_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout
```

### 方案3：添加装饰元素生成器

创建专门的装饰元素生成模块：

```python
class DecorationGenerator:
    """装饰元素生成器"""

    def generate_cover_decorations(self, theme):
        """生成封面装饰"""
        return f"""
        <defs>
            <linearGradient id="coverGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="{theme['primary']}" stop-opacity="0.12" />
                <stop offset="100%" stop-color="{theme['accent']}" stop-opacity="0.08" />
            </linearGradient>
        </defs>
        <rect width="1280" height="720" fill="url(#coverGrad)" />
        <circle cx="80" cy="120" r="60" fill="{theme['primary']}" fill-opacity="0.06" />
        <circle cx="1200" cy="580" r="70" fill="{theme['accent']}" fill-opacity="0.06" />
        """

    def generate_content_decorations(self, theme):
        """生成内容页装饰"""
        return f"""
        <rect x="0" y="0" width="1280" height="4" fill="{theme['accent']}" />
        <rect x="0" y="716" width="1280" height="4" fill="{theme['primary']}" />
        """
```

---

## 实施计划

### 阶段1：增强配色方案（1天）

1. 修改 `pick_theme` 函数，使用学科专属配色
2. 添加10个学科的配色方案
3. 测试配色效果

### 阶段2：添加装饰元素（2天）

1. 创建 `DecorationGenerator` 类
2. 为每种布局生成装饰元素
3. 集成到SVG生成流程

### 阶段3：集成模板继承（3天）

1. 读取模板SVG
2. 解析模板设计元素
3. 应用到新生成的SVG

### 阶段4：质量检查（1天）

1. 集成 `svg_quality_checker.py`
2. 添加错误修复机制
3. 测试质量检查

---

## 快速修复

### 立即改进：更新配色方案

修改 `ppt_master_integration.py` 中的 `pick_theme` 函数：

```python
def pick_theme(subject: str, topic: str) -> dict:
    """根据学科选择配色方案"""
    SUBJECT_THEMES = {
        '语文': {
            'primary': '#5B7F5E',  # 绿色，文学
            'accent': '#C4883A',   # 金色，典雅
            'bg': '#FBF8F1',       # 米色，温暖
        },
        '数学': {
            'primary': '#1A5276',  # 深蓝，严谨
            'accent': '#E74C3C',   # 红色，强调
            'bg': '#F0F5FB',       # 浅蓝，冷静
        },
        '英语': {
            'primary': '#1A6FC4',  # 蓝色，国际
            'accent': '#F39C12',   # 橙色，活力
            'bg': '#EBF3FC',       # 浅蓝，清新
        },
        # ... 其他学科
    }

    if subject in SUBJECT_THEMES:
        return SUBJECT_THEMES[subject]

    # 默认配色
    return {
        'primary': '#37474F',
        'accent': '#1976D2',
        'bg': '#FAFAFA',
    }
```

---

## 预期效果

### 改进前

- 简单的矩形设计
- 通用配色
- 缺少装饰元素

### 改进后

- 渐变背景、装饰圆形
- 学科专属配色
- 丰富的视觉效果
- 与ppt-master质量相当

---

## 优先级

1. **高优先级**：更新配色方案（立即）
2. **高优先级**：添加装饰元素（2天）
3. **中优先级**：集成模板继承（3天）
4. **低优先级**：质量检查（1天）

总工期：约1周
