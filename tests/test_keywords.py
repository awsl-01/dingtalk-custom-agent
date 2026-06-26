"""
测试关键词识别
"""
import sys
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.stdout.reconfigure(encoding='utf-8')

# 关键词定义
PPT_KEYWORDS = ["ppt", "PPT", "幻灯片", "演示文稿", "slides"]
TEMPLATE_PPT_KEYWORDS = ["模板", "风格统一", "设计基因", "套用模板"]
EDUCATION_KEYWORDS = ["教案", "课件", "说课", "反思", "教学设计", "教学大纲", "学情", "难度"]
GRADE_KEYWORDS = ["小学", "初中", "高中", "大学", "年级", "学前", "幼儿园",
                  "初一", "初二", "初三", "高一", "高二", "高三",
                  "一年级", "二年级", "三年级", "四年级", "五年级", "六年级"]
SUBJECT_KEYWORDS = ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "政治",
                    "音乐", "美术", "体育", "科学", "信息技术", "心理", "班会", "德育"]


def is_ppt_request(text: str) -> bool:
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in PPT_KEYWORDS)


def is_template_ppt_request(text: str) -> bool:
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in TEMPLATE_PPT_KEYWORDS)


def is_education_request(text: str) -> bool:
    text_lower = text.lower()
    if any(keyword in text_lower for keyword in EDUCATION_KEYWORDS):
        return True
    if any(keyword in text_lower for keyword in GRADE_KEYWORDS):
        return True
    if any(keyword in text_lower for keyword in SUBJECT_KEYWORDS):
        return True
    return False


# 测试用例
test_cases = [
    "生成一个从百草园到三味书屋适合初中的ppt模板风格必须统一",
    "生成一个关于人工智能的PPT",
    "制作一个课件",
    "帮我做一个高中物理教案",
    "生成一个市场分析PPT模板",
    "创建一个风格统一的演示文稿",
]

print("=== 关键词识别测试 ===\n")

for text in test_cases:
    print(f"输入: {text}")
    print(f"  是否PPT请求: {is_ppt_request(text)}")
    print(f"  是否模板PPT请求: {is_template_ppt_request(text)}")
    print(f"  是否教育PPT请求: {is_education_request(text)}")

    # 判断最终类型
    if is_template_ppt_request(text) and is_ppt_request(text):
        print(f"  -> 最终识别: 模板PPT生成")
    elif is_education_request(text):
        print(f"  -> 最终识别: 教育PPT生成")
    elif is_ppt_request(text):
        print(f"  -> 最终识别: 普通PPT生成")
    else:
        print(f"  -> 最终识别: 非PPT请求")
    print()
