"""
知识库操作日志查看工具

用法:
    python scripts/view_logs.py [选项]

选项:
    --all              查看所有企业的汇总日志（管理员模式）
    --corp_id ID       企业 ID
    --operation TYPE   操作类型过滤 (add/search/delete/export/update_schedule)
    --user ID          用户 ID 过滤
    --days N           查看最近 N 天（默认 7）
    --limit N          显示条数（默认 50）
    --stats            只显示统计信息
    --export FILE      导出到文件 (json/csv)
    --clear N          清理 N 天前的日志
"""
import sys
import os
import json
import argparse
from datetime import datetime, timedelta
from dataclasses import asdict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from agent.knowledge_base_v2 import get_knowledge_base, OperationLog, OperationLogger


def format_time(iso_str: str) -> str:
    """格式化时间显示"""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return iso_str


def print_log_entry(log, index: int):
    """打印单条日志"""
    status_icon = "✓" if log.status == "success" else "✗" if log.status == "failed" else "○"
    print(f"{index:3d}. [{status_icon}] {format_time(log.timestamp)}")
    print(f"     操作: {log.operation}")
    if log.user_nick:
        print(f"     用户: {log.user_nick} ({log.user_id})")
    if log.query:
        print(f"     查询: {log.query[:50]}{'...' if len(log.query) > 50 else ''}")
    if log.file_name:
        print(f"     文件: {log.file_name}")
    if log.result_count > 0:
        print(f"     结果: {log.result_count} 条")
    if log.details:
        print(f"     详情: {log.details}")
    print()


def print_stats(stats: dict, days: int):
    """打印统计信息"""
    print(f"\n{'='*60}")
    print(f"  知识库操作统计 (最近 {days} 天)")
    print(f"{'='*60}\n")

    print(f"  总操作数: {stats['total_operations']}")
    print()

    if stats['by_operation']:
        print("  按操作类型:")
        for op, count in sorted(stats['by_operation'].items(), key=lambda x: -x[1]):
            print(f"    {op:20s} {count:>6d} 次")
        print()

    if stats['by_user']:
        print("  按用户:")
        for user, count in sorted(stats['by_user'].items(), key=lambda x: -x[1])[:10]:
            print(f"    {user:20s} {count:>6d} 次")
        print()

    if stats['by_status']:
        print("  按状态:")
        for status, count in stats['by_status'].items():
            icon = "✓" if status == "success" else "✗" if status == "failed" else "○"
            print(f"    {icon} {status:18s} {count:>6d} 次")
        print()

    if stats['daily']:
        print("  每日操作量:")
        for day, count in sorted(stats['daily'].items()):
            bar = "█" * min(count, 40)
            print(f"    {day}  {bar} {count}")
        print()


def get_all_corp_ids() -> list:
    """获取所有企业 ID"""
    knowledge_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge")
    if not os.path.exists(knowledge_dir):
        return []
    return [d for d in os.listdir(knowledge_dir) if os.path.isdir(os.path.join(knowledge_dir, d))]


def query_all_logs(start_time: str = None, operation: str = None,
                   user_id: str = None, limit: int = 1000) -> list:
    """查询所有企业的日志"""
    all_logs = []
    knowledge_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge")

    for corp_id in get_all_corp_ids():
        school_dir = os.path.join(knowledge_dir, corp_id)
        logs_dir = os.path.join(school_dir, "logs")
        log_file = os.path.join(logs_dir, "operation_logs.jsonl")

        if not os.path.exists(log_file):
            continue

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        # 添加企业标识
                        data["corp_id"] = corp_id
                        entry = OperationLog(**{k: v for k, v in data.items() if k != "corp_id"})
                        entry._corp_id = corp_id  # 临时存储

                        # 时间过滤
                        if start_time and entry.timestamp < start_time:
                            continue
                        # 操作类型过滤
                        if operation and entry.operation != operation:
                            continue
                        # 用户过滤
                        if user_id and entry.user_id != user_id:
                            continue

                        all_logs.append((corp_id, entry))
                    except Exception:
                        continue
        except Exception as e:
            print(f"警告: 读取 {corp_id} 日志失败: {e}")

    # 按时间倒序
    all_logs.sort(key=lambda x: x[1].timestamp, reverse=True)
    return all_logs[:limit]


def get_all_stats(days: int = 7) -> dict:
    """获取所有企业的汇总统计"""
    start_time = (datetime.now() - timedelta(days=days)).isoformat()
    all_logs = query_all_logs(start_time=start_time, limit=100000)

    stats = {
        "total_operations": len(all_logs),
        "by_corp": {},
        "by_operation": {},
        "by_user": {},
        "by_status": {},
        "daily": {},
    }

    for corp_id, log in all_logs:
        # 按企业统计
        stats["by_corp"][corp_id] = stats["by_corp"].get(corp_id, 0) + 1

        # 按操作类型统计
        stats["by_operation"][log.operation] = stats["by_operation"].get(log.operation, 0) + 1

        # 按用户统计
        if log.user_nick:
            stats["by_user"][log.user_nick] = stats["by_user"].get(log.user_nick, 0) + 1

        # 按状态统计
        stats["by_status"][log.status] = stats["by_status"].get(log.status, 0) + 1

        # 按日期统计
        day = log.timestamp[:10]
        stats["daily"][day] = stats["daily"].get(day, 0) + 1

    return stats


def print_all_stats(stats: dict, days: int):
    """打印所有企业的汇总统计"""
    print(f"\n{'='*60}")
    print(f"  所有企业知识库操作统计 (最近 {days} 天)")
    print(f"{'='*60}\n")

    print(f"  总操作数: {stats['total_operations']}")
    print()

    if stats['by_corp']:
        print("  按企业:")
        for corp, count in sorted(stats['by_corp'].items(), key=lambda x: -x[1]):
            print(f"    {corp:30s} {count:>6d} 次")
        print()

    if stats['by_operation']:
        print("  按操作类型:")
        for op, count in sorted(stats['by_operation'].items(), key=lambda x: -x[1]):
            print(f"    {op:20s} {count:>6d} 次")
        print()

    if stats['by_user']:
        print("  按用户 (Top 10):")
        for user, count in sorted(stats['by_user'].items(), key=lambda x: -x[1])[:10]:
            print(f"    {user:20s} {count:>6d} 次")
        print()

    if stats['by_status']:
        print("  按状态:")
        for status, count in stats['by_status'].items():
            icon = "✓" if status == "success" else "✗" if status == "failed" else "○"
            print(f"    {icon} {status:18s} {count:>6d} 次")
        print()

    if stats['daily']:
        print("  每日操作量:")
        for day, count in sorted(stats['daily'].items()):
            bar = "█" * min(count, 40)
            print(f"    {day}  {bar} {count}")
        print()


def main():
    parser = argparse.ArgumentParser(description="知识库操作日志查看工具")
    parser.add_argument("--all", action="store_true", help="查看所有企业的汇总日志（管理员模式）")
    parser.add_argument("--corp_id", help="企业 ID")
    parser.add_argument("--operation", help="操作类型过滤")
    parser.add_argument("--user", help="用户 ID 过滤")
    parser.add_argument("--days", type=int, default=7, help="查看最近 N 天")
    parser.add_argument("--limit", type=int, default=50, help="显示条数")
    parser.add_argument("--stats", action="store_true", help="只显示统计信息")
    parser.add_argument("--export", help="导出到文件")
    parser.add_argument("--clear", type=int, help="清理 N 天前的日志")
    parser.add_argument("--list", action="store_true", help="列出所有可用的企业 ID")

    args = parser.parse_args()

    # 列出所有企业 ID
    if args.list:
        corp_ids = get_all_corp_ids()
        if corp_ids:
            print("\n可用的企业 ID:")
            for cid in corp_ids:
                print(f"  - {cid}")
        else:
            print("\n暂无数据")
        return

    # 管理员模式：查看所有企业汇总
    if args.all:
        # 显示统计信息
        if args.stats:
            stats = get_all_stats(days=args.days)
            print_all_stats(stats, args.days)
            return

        # 导出所有企业日志
        if args.export:
            start_time = (datetime.now() - timedelta(days=args.days)).isoformat()
            all_logs = query_all_logs(start_time=start_time, limit=100000)
            format_type = "csv" if args.export.endswith(".csv") else "json"

            if format_type == "csv":
                import csv
                with open(args.export, "w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["企业ID", "时间", "操作", "用户", "查询内容", "来源类型", "文件名", "结果数", "状态", "详情"])
                    for corp_id, log in all_logs:
                        writer.writerow([
                            corp_id, log.timestamp, log.operation, log.user_nick,
                            log.query, log.source_type, log.file_name,
                            log.result_count, log.status, log.details
                        ])
            else:
                with open(args.export, "w", encoding="utf-8") as f:
                    json.dump([
                        {"corp_id": cid, **asdict(log)} for cid, log in all_logs
                    ], f, ensure_ascii=False, indent=2)

            print(f"已导出 {len(all_logs)} 条日志到: {args.export}")
            return

        # 清理所有企业的旧日志
        if args.clear is not None:
            total_cleared = 0
            for corp_id in get_all_corp_ids():
                school_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "knowledge", corp_id
                )
                kb = get_knowledge_base(school_dir, corp_id)
                cleared = kb.clear_old_operation_logs(args.clear)
                if cleared > 0:
                    print(f"  {corp_id}: 清理 {cleared} 条")
                total_cleared += cleared
            print(f"\n共清理 {total_cleared} 条 {args.clear} 天前的日志")
            return

        # 显示所有企业日志
        start_time = (datetime.now() - timedelta(days=args.days)).isoformat()
        all_logs = query_all_logs(
            start_time=start_time,
            operation=args.operation,
            user_id=args.user,
            limit=args.limit
        )

        if not all_logs:
            print(f"\n最近 {args.days} 天没有操作记录")
            return

        print(f"\n{'='*60}")
        print(f"  所有企业操作日志 (最近 {args.days} 天，共 {len(all_logs)} 条)")
        print(f"{'='*60}\n")

        for i, (corp_id, log) in enumerate(all_logs, 1):
            status_icon = "✓" if log.status == "success" else "✗" if log.status == "failed" else "○"
            print(f"{i:3d}. [{status_icon}] {format_time(log.timestamp)}  [{corp_id}]")
            print(f"     操作: {log.operation}")
            if log.user_nick:
                print(f"     用户: {log.user_nick} ({log.user_id})")
            if log.query:
                print(f"     查询: {log.query[:50]}{'...' if len(log.query) > 50 else ''}")
            if log.file_name:
                print(f"     文件: {log.file_name}")
            if log.result_count > 0:
                print(f"     结果: {log.result_count} 条")
            if log.details:
                print(f"     详情: {log.details}")
            print()

        print(f"提示: 使用 --all --stats 查看汇总统计")
        return

    # 单企业模式
    if not args.corp_id:
        print("错误: 请指定 --corp_id 或使用 --all 查看所有企业")
        print("使用 --list 查看可用的企业 ID")
        return

    # 获取知识库实例
    school_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "knowledge", args.corp_id
    )

    if not os.path.exists(school_dir):
        print(f"错误: 企业 {args.corp_id} 的知识库不存在")
        return

    kb = get_knowledge_base(school_dir, args.corp_id)

    # 清理旧日志
    if args.clear is not None:
        cleared = kb.clear_old_operation_logs(args.clear)
        print(f"已清理 {cleared} 条 {args.clear} 天前的日志")
        return

    # 导出日志
    if args.export:
        format_type = "csv" if args.export.endswith(".csv") else "json"
        kb.export_operation_logs(args.export, format=format_type, limit=100000)
        print(f"日志已导出到: {args.export}")
        return

    # 显示统计信息
    if args.stats:
        stats = kb.get_operation_stats(days=args.days)
        print_stats(stats, args.days)
        return

    # 查询日志
    start_time = (datetime.now() - timedelta(days=args.days)).isoformat()
    logs = kb.query_operation_logs(
        start_time=start_time,
        operation=args.operation,
        user_id=args.user,
        limit=args.limit
    )

    if not logs:
        print(f"\n最近 {args.days} 天没有操作记录")
        return

    print(f"\n{'='*60}")
    print(f"  知识库操作日志 (最近 {args.days} 天，共 {len(logs)} 条)")
    print(f"{'='*60}\n")

    for i, log in enumerate(logs, 1):
        print_log_entry(log, i)

    print(f"提示: 使用 --stats 查看统计信息")


if __name__ == "__main__":
    main()
