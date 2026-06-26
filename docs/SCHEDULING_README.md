# 排课系统使用说明

## 功能概述

排课系统是一个基于钉钉机器人的智能排课工具，支持：

- **自动排课**：根据班级、教师、课程、教室等信息自动生成课表
- **冲突检测**：检测教师时间冲突、班级时间冲突、教室时间冲突等
- **课表优化**：通过局部搜索算法优化课表质量
- **手动调课**：支持手动调整课程时间
- **Excel 导入导出**：支持通过 Excel 文件导入排课数据

## 快速开始

### 方式一：通过钉钉机器人使用

1. **生成 Excel 模板**
   ```
   用户：生成排课模板
   机器人：[发送 Excel 模板文件]
   ```

2. **填写模板并上传**
   ```
   用户：[上传填写好的 Excel 文件]
   机器人：已接收排课数据
   ```

3. **开始排课**
   ```
   用户：开始排课
   机器人：正在排课...
           排课完成！
           [显示课表]
   ```

### 方式二：通过 Python 代码使用

```python
from agent.skills.scheduling import (
    Teacher, Classroom, Course, ClassGroup,
    ScheduleAlgorithm, SchedulingTask, ConstraintManager,
)

# 1. 创建数据
teachers = {
    't1': Teacher(id='t1', name='张老师', subjects=['数学']),
    't2': Teacher(id='t2', name='李老师', subjects=['语文']),
}

classrooms = {
    'r1': Classroom(id='r1', name='101教室', capacity=50),
}

courses = {
    'math': Course(id='math', name='数学', subject='数学', hours_per_week=5, is_main_subject=True),
    'chinese': Course(id='chinese', name='语文', subject='语文', hours_per_week=5, is_main_subject=True),
}

classes = {
    'c1': ClassGroup(id='c1', name='高一(1)班', courses=['math', 'chinese']),
}

# 2. 创建排课任务
task = SchedulingTask(
    classes=classes,
    teachers=teachers,
    classrooms=classrooms,
    courses=courses,
    constraints=ConstraintManager(),
)

# 3. 执行排课
algorithm = ScheduleAlgorithm()
result = algorithm.schedule(task)

# 4. 查看结果
if result.success:
    table = result.schedule.to_table('c1', classes, courses, teachers)
    print(table)
```

## 数据格式说明

### 班级信息

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| id | string | 班级唯一标识 | class_01 |
| name | string | 班级名称 | 高一(1)班 |
| grade | string | 年级 | 高一 |
| student_count | int | 学生人数 | 45 |
| courses | list | 课程ID列表 | ["math", "chinese"] |
| homeroom_teacher | string | 班主任ID | teacher_01 |

### 教师信息

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| id | string | 教师唯一标识 | teacher_01 |
| name | string | 教师姓名 | 张老师 |
| subjects | list | 可教科目 | ["数学"] |
| max_hours_per_day | int | 每天最大课时 | 4 |
| max_hours_per_week | int | 每周最大课时 | 20 |

### 课程信息

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| id | string | 课程唯一标识 | math |
| name | string | 课程名称 | 高一数学 |
| subject | string | 学科 | 数学 |
| hours_per_week | int | 每周课时数 | 5 |
| is_main_subject | bool | 是否主课 | true |
| needs_consecutive | bool | 是否需要连排 | false |
| required_equipment | list | 所需设备 | ["实验室"] |

### 教室信息

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| id | string | 教室唯一标识 | room_01 |
| name | string | 教室名称 | 101教室 |
| capacity | int | 容量 | 50 |
| equipment | list | 设备列表 | ["多媒体"] |
| building | string | 教学楼 | 教学楼A |

## 约束条件

### 硬约束（必须满足）

- **教师时间冲突**：同一教师同一时间不能上两门课
- **班级时间冲突**：同一班级同一时间不能上两门课
- **教室时间冲突**：同一教室同一时间不能安排两门课
- **教师可用性**：教师在指定时间段必须可用

### 软约束（尽量满足）

- **主课优先上午**：语数外等主课优先安排在上午
- **连排课时限制**：教师连续授课不超过 3 节
- **教师每日课时**：教师每天课时不超过限制
- **课程分布均匀**：同一课程在一周内均匀分布

### 约束配置

```python
constraints = ConstraintManager()
constraints.update_config({
    "max_consecutive_hours": 3,  # 最大连排课时
    "main_subject_prefer_morning": True,  # 主课优先上午
    "max_daily_hours_per_teacher": 4,  # 教师每天最大课时
    "course_even_distribution": True,  # 课程均匀分布
})
```

## 钉钉指令

| 指令 | 说明 | 示例 |
|------|------|------|
| 开始排课 | 启动自动排课 | "开始排课" |
| 排课 | 同上 | "排课" |
| 自动排课 | 同上 | "自动排课：高一(1)班" |
| 查看课表 | 查看班级课表 | "查看课表 高一(1)班" |
| 优化课表 | 优化现有课表 | "优化课表" |
| 导出课表 | 导出为 Excel | "导出课表" |
| 生成排课模板 | 生成 Excel 模板 | "生成排课模板" |

## 文件结构

```
agent/skills/
├── scheduling_skill.py      # 技能注册文件
└── scheduling/              # 排课算法目录
    ├── __init__.py          # 包初始化
    ├── models.py            # 数据模型
    ├── constraints.py       # 约束条件管理
    ├── detector.py          # 冲突检测
    ├── algorithm.py         # 排课算法
    └── excel_handler.py     # Excel 数据处理
```

## 算法说明

### 贪心算法

1. 按优先级排序课程（主课优先，课时多的优先）
2. 为每门课程寻找最佳时间段：
   - 检查教师可用性
   - 检查班级和教室冲突
   - 计算软约束惩罚分数
   - 选择惩罚最小的方案
3. 安排课程到最佳时间段

### 回溯优化

当贪心算法无法完成排课时：
1. 收集未安排的课程
2. 尝试与已安排的课程交换时间
3. 如果找到可行方案，执行交换

### 局部搜索优化

1. 随机选择两个时间段交换
2. 检查交换后的冲突数
3. 如果冲突减少，保留交换
4. 重复迭代，直到达到目标

## 常见问题

### Q: 排课失败怎么办？

A: 检查以下几点：
- 教师数量是否足够
- 教室容量是否满足班级人数
- 课程所需设备是否齐全

### Q: 如何提高排课成功率？

A:
- 增加教师数量
- 减少每班课程数量
- 放宽约束条件（如增加每天最大课时）

### Q: 如何手动调课？

A: 使用现有的课表管理技能：
```
用户：高一(1)班周一上午和周二上午调课
机器人：调课成功
```

### Q: 支持多少个班级？

A: 理论上无限制，但建议：
- 10 个班级以内：秒级完成
- 10-50 个班级：分钟级完成
- 50 个以上：可能需要优化算法

## 技术支持

如有问题，请查看：
- 代码目录：`agent/skills/scheduling/`
- 示例代码：`examples/scheduling_example.py`
- 测试脚本：`tests/test_scheduling.py`
