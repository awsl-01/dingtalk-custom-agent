"""
验证资产管理模板功能修复
"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("  验证资产管理模板功能修复")
print("=" * 60)

# 读取 main.py 文件
with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 检查是否包含修复代码
check_strings = [
    'asset_template_keywords',
    'is_asset_template',
    '检测到资产管理模板请求，跳过资源搜索'
]

print("\n检查 main.py 中的修复代码:")
all_found = True
for check_str in check_strings:
    if check_str in content:
        print(f"  [OK] 找到: {check_str}")
    else:
        print(f"  [FAIL] 未找到: {check_str}")
        all_found = False

if all_found:
    print("\n[OK] 修复代码已正确保存到 main.py")
    print("\n请重启服务以使修改生效:")
    print("  python main.py")
else:
    print("\n[FAIL] 修复代码不完整，请检查 main.py")
