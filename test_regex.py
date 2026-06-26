import re, sys
sys.stdout.reconfigure(encoding='utf-8')

tests = [
    '计算机科学与技术2301班张教授有什么课',
    '张教授有什么课',
    '高等数学A(张教授)',
    '李老师的课',
    '2301班张教授',
    '王教授的课表',
]

for t in tests:
    matches = re.findall(r'([一-龥]{1,4})(?:教授|老师|教师)', t)
    teacher_name = ""
    for name in matches:
        clean_name = name.lstrip("班")
        if clean_name and len(clean_name) >= 1:
            teacher_name = clean_name
            break
    print(f'[{t}] -> matches={matches} -> teacher=[{teacher_name}]')
