"""
巡检功能测试

测试巡检计划、点位、打卡、问题上报、工单流转等核心功能
"""
import sys
import os

# 强制 UTF-8 编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import shutil
import tempfile
from datetime import datetime

from agent.inspection.service import InspectionService
from agent.inspection.models import (
    AreaType, CheckCategory, IssueCategory, IssueStatus,
    PlanStatus, CheckFrequency,
)


def test_inspection():
    """完整巡检流程测试"""
    # 使用临时目录
    test_dir = tempfile.mkdtemp(prefix="inspection_test_")

    try:
        service = InspectionService(test_dir)

        print("=" * 60)
        print("  巡检功能测试")
        print("=" * 60)

        # 1. 创建巡检点位
        print("\n1️⃣ 创建巡检点位...")
        point1 = service.create_point(
            point_name="教学楼A-1楼走廊",
            area_type=AreaType.TEACHING,
            location="教学楼A栋1层走廊",
            check_items=[
                {"item_id": "light", "item_name": "照明设施", "category": "facility"},
                {"item_id": "clean", "item_name": "卫生状况", "category": "hygiene"},
                {"item_id": "fire_ext", "item_name": "灭火器", "category": "fire"},
            ],
        )
        print(f"   ✅ 创建点位: {point1.point_name} ({point1.point_id})")

        point2 = service.create_point(
            point_name="学生宿舍B栋",
            area_type=AreaType.DORMITORY,
            location="宿舍B栋入口",
            check_items=[
                {"item_id": "door", "item_name": "门禁系统", "category": "safety"},
                {"item_id": "hygiene", "item_name": "走廊卫生", "category": "hygiene"},
            ],
        )
        print(f"   ✅ 创建点位: {point2.point_name} ({point2.point_id})")

        point3 = service.create_point(
            point_name="食堂操作间",
            area_type=AreaType.CANTEEN,
            location="食堂2楼操作间",
            check_items=[
                {"item_id": "food_safety", "item_name": "食品安全", "category": "safety"},
                {"item_id": "clean", "item_name": "卫生清洁", "category": "hygiene"},
            ],
        )
        print(f"   ✅ 创建点位: {point3.point_name} ({point3.point_id})")

        # 2. 创建巡检计划
        print("\n2️⃣ 创建巡检计划...")
        plan = service.create_plan(
            plan_name="每日教学区安全巡检",
            area_type=AreaType.TEACHING,
            check_category=CheckCategory.SAFETY,
            frequency=CheckFrequency.DAILY,
            assigned_inspectors=["inspector_001", "inspector_002"],
            assigned_areas=["教学楼A", "教学楼B"],
            start_date="2026-06-15",
            end_date="2026-12-31",
            description="每日教学区安全、卫生、设施巡检",
        )
        print(f"   ✅ 创建计划: {plan.plan_name} ({plan.plan_id})")

        # 激活计划
        service.update_plan_status(plan.plan_id, PlanStatus.ACTIVE)
        print(f"   ✅ 计划已激活")

        # 3. 巡检打卡
        print("\n3️⃣ 巡检打卡...")
        record1, msg1 = service.check_in(
            plan_id=plan.plan_id,
            point_id=point1.point_id,
            inspector_id="inspector_001",
            inspector_name="张老师",
            latitude=30.5728,
            longitude=104.0668,
            notes="正常巡检",
        )
        print(f"   {msg1}")

        record2, msg2 = service.check_in(
            plan_id=plan.plan_id,
            point_id=point2.point_id,
            inspector_id="inspector_001",
            inspector_name="张老师",
        )
        print(f"   {msg2}")

        # 4. 签退
        print("\n4️⃣ 巡检签退...")
        ok, msg = service.check_out(
            record_id=record1.record_id,
            check_results=[
                {"item_id": "light", "item_name": "照明设施", "status": "pass"},
                {"item_id": "clean", "item_name": "卫生状况", "status": "pass"},
                {"item_id": "fire_ext", "item_name": "灭火器", "status": "fail", "description": "灭火器过期"},
            ],
        )
        print(f"   {msg}")

        # 5. 上报问题
        print("\n5️⃣ 上报问题...")
        issue = service.report_issue(
            record_id=record1.record_id,
            category=IssueCategory.FIRE_SAFETY,
            title="教学楼A-1楼灭火器过期",
            description="1楼走廊东侧灭火器已于2026年5月过期，需要更换",
            reported_by="inspector_001",
            reported_by_name="张老师",
            severity="high",
            point_name="教学楼A-1楼走廊",
        )
        print(f"   ✅ 上报问题: {issue.title} ({issue.issue_id})")
        print(f"   分类: {issue.category}, 严重程度: {issue.severity}")

        # 6. 派单
        print("\n6️⃣ 派单整改...")
        ok, msg = service.assign_order(
            issue_id=issue.issue_id,
            assigned_to="facilities_001",
            assigned_to_name="后勤李师傅",
            assigned_by="admin",
            deadline_hours=48,
        )
        print(f"   {msg}")

        # 7. 开始整改
        print("\n7️⃣ 开始整改...")
        ok, msg = service.start_rectification(issue.issue_id, operator="facilities_001")
        print(f"   {msg}")

        # 8. 提交整改
        print("\n8️⃣ 提交整改结果...")
        ok, msg = service.submit_rectification(
            issue_id=issue.issue_id,
            rectification_notes="已更换新的灭火器，有效期至2028年",
            operator="facilities_001",
        )
        print(f"   {msg}")

        # 9. 复查验收
        print("\n9️⃣ 复查验收...")
        ok, msg = service.review_issue(
            issue_id=issue.issue_id,
            review_result="pass",
            reviewer_id="admin",
            review_notes="确认灭火器已更换，验收通过",
        )
        print(f"   {msg}")

        # 10. 查看统计
        print("\n🔟 查看统计...")
        stats = service.get_stats()
        print(f"   计划总数: {stats.total_plans}")
        print(f"   进行中计划: {stats.active_plans}")
        print(f"   巡检点位: {stats.total_points}")
        print(f"   问题总数: {stats.total_issues}")
        print(f"   已解决问题: {stats.resolved_issues}")

        # 11. 查看问题列表
        print("\n1️⃣1️⃣ 问题列表...")
        issues = service.list_issues()
        for iss in issues:
            print(f"   - [{iss.status}] {iss.title} (严重程度: {iss.severity})")

        # 12. 查看工单列表
        print("\n1️⃣2️⃣ 工单列表...")
        orders = service.get_orders()
        for o in orders:
            print(f"   - [{o.status}] 工单 {o.order_id} -> {o.assigned_to_name}")

        print("\n" + "=" * 60)
        print("  ✅ 巡检功能测试完成！")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 清理测试目录
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    success = test_inspection()
    sys.exit(0 if success else 1)
