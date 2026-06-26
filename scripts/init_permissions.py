"""
权限初始化脚本
用于初始化用户和权限数据
"""
import os
import sys
import json

# 强制使用 UTF-8 编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.permission_manager import (
    PermissionManager, UserInfo, DEFAULT_ROLES_CONFIG
)


def init_permissions(corp_id: str, org_name: str):
    """
    初始化权限配置

    参数:
        corp_id: 企业/组织ID
        org_name: 组织名称
    """
    knowledge_dir = os.path.join("knowledge", corp_id)

    # 确保目录存在
    os.makedirs(os.path.join(knowledge_dir, "structured"), exist_ok=True)

    # 初始化 meta.json
    meta_file = os.path.join(knowledge_dir, "meta.json")
    if os.path.exists(meta_file):
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
    else:
        meta = {
            "corp_id": corp_id,
            "name": org_name,
            "system_prompt": "",
            "knowledge_dir": knowledge_dir,
            "features": {
                "ppt_generation": True,
                "web_search": True,
                "knowledge_qa": True,
                "schedule_qa": True
            },
            "metadata": {}
        }

    # 添加角色配置
    meta["roles"] = DEFAULT_ROLES_CONFIG
    meta["content_levels"] = {
        "public": "公开内容",
        "internal": "内部内容",
        "confidential": "机密内容"
    }

    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"✅ 初始化组织配置: {org_name} ({corp_id})")

    # 初始化用户文件
    users_file = os.path.join(knowledge_dir, "structured", "users.json")
    if not os.path.exists(users_file):
        with open(users_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        print(f"✅ 初始化用户文件: {users_file}")

    # 初始化审批文件
    approvals_file = os.path.join(knowledge_dir, "structured", "approvals.json")
    if not os.path.exists(approvals_file):
        with open(approvals_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        print(f"✅ 初始化审批文件: {approvals_file}")

    print(f"\n✅ 权限配置初始化完成！")
    print(f"\n角色配置:")
    for role_id, role_config in DEFAULT_ROLES_CONFIG.items():
        print(f"  - {role_id}: {role_config['name']}")
        permissions = role_config.get("search_permissions", [])
        print(f"    权限: {', '.join(permissions)}")


def add_user(corp_id: str, user_id: str, name: str,
             role: str = "teacher", department: str = "",
             manager_id: str = ""):
    """
    添加用户

    参数:
        corp_id: 企业/组织ID
        user_id: 用户ID
        name: 用户名称
        role: 角色
        department: 部门
        manager_id: 上级用户ID
    """
    knowledge_dir = os.path.join("knowledge", corp_id)

    if not os.path.exists(knowledge_dir):
        print(f"❌ 组织 {corp_id} 不存在，请先运行 init_permissions 初始化")
        return

    perm_manager = PermissionManager(knowledge_dir, corp_id)

    # 检查用户是否已存在
    if perm_manager.get_user(user_id):
        print(f"⚠️ 用户 {user_id} 已存在")
        return

    # 添加用户
    user = UserInfo(
        user_id=user_id,
        name=name,
        role=role,
        department=department,
        manager_id=manager_id
    )

    if perm_manager.add_user(user):
        print(f"✅ 添加用户: {name} ({user_id})")
        print(f"   角色: {role}")
        if department:
            print(f"   部门: {department}")
        if manager_id:
            manager_name = perm_manager.get_user_name(manager_id)
            print(f"   上级: {manager_name} ({manager_id})")
    else:
        print(f"❌ 添加用户失败")


def list_users(corp_id: str):
    """列出所有用户"""
    knowledge_dir = os.path.join("knowledge", corp_id)

    if not os.path.exists(knowledge_dir):
        print(f"❌ 组织 {corp_id} 不存在")
        return

    perm_manager = PermissionManager(knowledge_dir, corp_id)
    users = perm_manager.list_users()

    if not users:
        print(f"📋 组织 {corp_id} 暂无用户")
        return

    print(f"👥 组织 {corp_id} 用户列表 (共 {len(users)} 人):\n")
    for user in users:
        role_name = perm_manager.get_role_name(user.role)
        print(f"• {user.name} ({user.user_id})")
        print(f"  角色: {role_name}")
        if user.department:
            print(f"  部门: {user.department}")
        if user.manager_id:
            manager_name = perm_manager.get_user_name(user.manager_id)
            print(f"  上级: {manager_name}")
        print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="权限管理初始化工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # init 命令
    init_parser = subparsers.add_parser("init", help="初始化组织权限配置")
    init_parser.add_argument("corp_id", help="企业/组织ID")
    init_parser.add_argument("org_name", help="组织名称")

    # add-user 命令
    add_user_parser = subparsers.add_parser("add-user", help="添加用户")
    add_user_parser.add_argument("corp_id", help="企业/组织ID")
    add_user_parser.add_argument("user_id", help="用户ID")
    add_user_parser.add_argument("name", help="用户名称")
    add_user_parser.add_argument("--role", default="teacher",
                                  help="角色 (admin/principal/director/teacher/student)")
    add_user_parser.add_argument("--department", default="", help="部门")
    add_user_parser.add_argument("--manager", default="", help="上级用户ID")

    # list-users 命令
    list_parser = subparsers.add_parser("list-users", help="列出所有用户")
    list_parser.add_argument("corp_id", help="企业/组织ID")

    args = parser.parse_args()

    if args.command == "init":
        init_permissions(args.corp_id, args.org_name)
    elif args.command == "add-user":
        add_user(
            args.corp_id,
            args.user_id,
            args.name,
            args.role,
            args.department,
            args.manager
        )
    elif args.command == "list-users":
        list_users(args.corp_id)
    else:
        parser.print_help()
