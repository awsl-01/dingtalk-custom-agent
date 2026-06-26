# PPT 生成流程对比（更新版）

## 当前实现流程

```
用户请求（钉钉消息）
    ↓
解析请求信息（主题、学科、年级、页数）
    ↓
生成大纲 → 用户确认
    ↓
┌─────────────────────────────────────────────────────────────┐
│  generate_ppt_with_master()                                  │
│  ├── 1. 选择配色（学科专属配色）                              │
│  ├── 2. 搜索教材内容                                         │
│  ├── 3. AI规划页面（plan_pages_with_ai）                     │
│  ├── 4. 创建项目（project_manager.py init）                  │
│  ├── 5. 生成设计规范（design_spec.md + spec_lock.md）        │
│  ├── 6. 搜索教学配图                                         │
│  ├── 7. 逐页生成SVG（保持上下文）                            │
│  │   ├── 读取spec_lock和design_spec                          │
│  │   ├── 调用OpenAI API生成SVG                               │
│  │   └── 传递已生成的SVG给下一页                              │
│  ├── 8. 生成演讲备注                                         │
│  └── 9. 后处理（finalize_svg → svg_to_pptx）                 │
└─────────────────────────────────────────────────────────────┘
    ↓
发送PPTX文件
```

## ppt-master 原始流程

```
用户请求（Claude Code交互）
    ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 1: 源文件处理                                          │
│  ├── PDF/DOCX/URL/Markdown → Markdown                        │
│  └── 图片提取                                                │
├─────────────────────────────────────────────────────────────┤
│  Step 2: 创建项目                                            │
│  └── project_manager.py init                                 │
├─────────────────────────────────────────────────────────────┤
│  Step 3: 模板选择（可选）                                    │
│  └── 用户指定模板路径                                        │
├─────────────────────────────────────────────────────────────┤
│  Step 4: Strategist（八项确认）⛔ BLOCKING                   │
│  ├── 1. 画布格式                                             │
│  ├── 2. 页数范围                                             │
│  ├── 3. 目标受众                                             │
│  ├── 4. 风格目标                                             │
│  ├── 5. 配色方案                                             │
│  ├── 6. 图标方案                                             │
│  ├── 7. 字体方案                                             │
│  └── 8. 图片方案                                             │
│  → 生成 design_spec.md + spec_lock.md                        │
├─────────────────────────────────────────────────────────────┤
│  Step 5: 图片获取（可选）                                    │
│  ├── AI生成（image_gen.py）                                  │
│  ├── 网络搜索（image_search.py）                             │
│  └── 用户上传                                                │
├─────────────────────────────────────────────────────────────┤
│  Step 6: Executor（逐页手写SVG）                             │
│  ├── 读取executor-base.md + shared-standards.md              │
│  ├── 读取executor-{style}.md                                 │
│  ├── 启动实时预览（svg_editor/server.py）                    │
│  ├── 批量读取模板SVG                                         │
│  ├── 逐页生成：                                              │
│  │   ├── 重读spec_lock.md                                    │
│  │   ├── AI手写SVG（保持完整上下文）                         │
│  │   └── 质量检查（svg_quality_checker.py）                  │
│  └── 生成演讲备注（notes/total.md）                          │
├─────────────────────────────────────────────────────────────┤
│  Step 7: 后处理与导出                                        │
│  ├── 7.1 拆分演讲备注（total_md_split.py）                   │
│  ├── 7.2 SVG后处理（finalize_svg.py）                        │
│  └── 7.3 导出PPTX（svg_to_pptx.py）                          │
│      ├── 动画配置（fade转场 + auto入场）                     │
│      └── 演讲备注嵌入                                        │
└─────────────────────────────────────────────────────────────┘
    ↓
导出PPTX文件
```

---

## 关键差异对比

| 维度 | 当前实现 | ppt-master | 差距分析 |
|------|----------|------------|----------|
| **用户交互** | 钉钉消息 → 大纲确认 | Claude Code → 八项确认 | 当前简化，ppt-master更详细 |
| **源文件处理** | ❌ 无 | ✅ PDF/DOCX/URL等 | 当前缺失 |
| **模板选择** | ❌ 无 | ✅ brand/layout/deck | 当前缺失 |
| **设计规范** | 自动生成 | 用户确认后生成 | 当前自动化，ppt-master需确认 |
| **图片处理** | 搜索教学配图 | AI生成+网络搜索+用户上传 | 当前仅搜索 |
| **SVG生成** | AI调用API生成 | AI手写（保持完整上下文） | 核心差异 |
| **实时预览** | ❌ 无 | ✅ Flask Web编辑器 | 当前缺失 |
| **质量检查** | ❌ 无 | ✅ svg_quality_checker | 当前缺失 |
| **页数控制** | AI自动/用户指定 | 用户确认页数范围 | 当前更灵活 |
| **动画效果** | 自动添加 | 可配置 | 当前自动，ppt-master可自定义 |

---

## SVG生成方式对比

### 当前实现

```python
def generate_svg_with_executor(page_spec, ...):
    # 1. 构建system prompt（包含配色、字体、规范）
    system_prompt = build_executor_prompt(...)

    # 2. 调用OpenAI API
    response = client.chat.completions.create(
        model="...",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请生成SVG..."}
        ]
    )

    # 3. 清理和验证SVG
    svg = clean_svg_output(response.choices[0].message.content)
    return svg
```

**特点**：
- 每次API调用是独立的
- 通过system prompt传递上下文
- 已生成的SVG作为参考传递给下一页

### ppt-master

```
Executor角色：
1. 读取 executor-base.md（通用规范）
2. 读取 executor-{style}.md（风格规范）
3. 读取 shared-standards.md（技术约束）
4. 批量读取模板SVG
5. 逐页生成：
   - 重读 spec_lock.md
   - AI手写SVG（在同一个对话上下文中）
   - 质量检查
```

**特点**：
- AI在整个过程中保持完整上下文
- 每页重读spec_lock，防止上下文漂移
- 严格遵循规范（禁止脚本生成）

---

## 核心问题分析

### 问题1：SVG生成质量差距

**原因**：
- 当前实现通过API调用，每次调用是独立的
- ppt-master的AI在整个过程中保持完整上下文
- 当前实现的system prompt不如ppt-master的规范详细

**解决方案**：
- 增强system prompt，包含更详细的规范
- 传递已生成的SVG作为参考（已实现）
- 使用更强的模型

### 问题2：缺少质量检查

**原因**：
- 当前实现没有集成svg_quality_checker

**解决方案**：
- 在SVG生成后添加质量检查
- 修复检查发现的问题

### 问题3：缺少实时预览

**原因**：
- 当前实现没有集成svg_editor

**解决方案**：
- 集成svg_editor服务器
- 在生成过程中启动实时预览

---

## 改进优先级

| 优先级 | 改进项 | 预期效果 | 工期 |
|--------|--------|----------|------|
| P0 | 增强system prompt | 提升SVG质量 | 1天 |
| P0 | 集成质量检查 | 发现并修复问题 | 1天 |
| P1 | 集成实时预览 | 用户体验提升 | 2天 |
| P1 | 添加源文件处理 | 支持更多输入格式 | 3天 |
| P2 | 添加模板选择 | 更灵活的设计 | 2天 |
| P2 | 增强图片处理 | AI生成+网络搜索 | 2天 |

---

## 总结

当前实现与ppt-master的核心差距在于：

1. **SVG生成方式**：当前通过API调用，ppt-master是AI手写
2. **上下文保持**：当前通过system prompt传递，ppt-master保持完整对话上下文
3. **规范遵循**：当前规范不如ppt-master详细
4. **质量保证**：当前缺少质量检查

**建议**：
1. 优先增强system prompt，包含更详细的规范
2. 集成质量检查，发现并修复问题
3. 逐步集成ppt-master的其他功能
