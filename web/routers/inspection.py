"""
巡检管理 API

提供巡检计划、点位、打卡、问题、工单、统计等 REST API
"""
import os
import logging
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

import os
import tempfile
import shutil
from agent.inspection.service import get_inspection_service
from agent.inspection.models import (
    AreaType, CheckCategory, IssueCategory, IssueStatus,
    PlanStatus, CheckFrequency,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["巡检管理"])

# 名称映射
AREA_TYPE_NAMES = {
    "teaching": "教学区",
    "dormitory": "宿舍区",
    "canteen": "食堂",
    "playground": "操场",
    "fire": "消防设施",
    "public": "公共区域",
    "other": "其他",
}

CHECK_CATEGORY_NAMES = {
    "safety": "安全",
    "hygiene": "卫生",
    "facility": "设施",
    "discipline": "纪律",
}

PLAN_STATUS_NAMES = {
    "draft": "草稿",
    "active": "进行中",
    "completed": "已完成",
    "cancelled": "已取消",
}

ISSUE_CATEGORY_NAMES = {
    "safety_hazard": "安全隐患",
    "hygiene_issue": "卫生问题",
    "facility_damage": "设施损坏",
    "discipline_violation": "纪律违规",
    "fire_safety": "消防安全",
    "other": "其他",
}

ISSUE_STATUS_NAMES = {
    "pending": "待处理",
    "assigned": "已派单",
    "in_progress": "整改中",
    "pending_review": "待复查",
    "resolved": "已解决",
    "closed": "已关闭",
    "rejected": "已驳回",
}

# 页面路由（不带API前缀）
page_router = APIRouter(tags=["巡检页面"])

# 照片存储目录
PHOTOS_DIR = os.path.join("knowledge", "inspection", "photos")
os.makedirs(PHOTOS_DIR, exist_ok=True)


def _convert_photo_url(photo_url: str) -> str:
    """
    将照片URL转换为可访问的API URL

    支持转换:
    1. 本地绝对路径 -> API URL (/api/inspection/local-photo?file_path=...)
    2. 已经是API URL -> 保持不变
    3. 其他 -> 保持不变
    """
    if not photo_url:
        return ""

    # 如果已经是API URL，直接返回
    if photo_url.startswith("/api/inspection/"):
        return photo_url

    # 如果是本地文件路径
    if os.path.exists(photo_url):
        # 转换为API URL
        abs_path = os.path.abspath(photo_url)
        return f"/api/inspection/local-photo?file_path={abs_path}"

    # 如果是相对路径，尝试转换为绝对路径
    if not os.path.isabs(photo_url):
        abs_path = os.path.abspath(photo_url)
        if os.path.exists(abs_path):
            return f"/api/inspection/local-photo?file_path={abs_path}"

    return photo_url


def _convert_photo_urls(photo_urls: list) -> list:
    """批量转换照片URL"""
    if not photo_urls:
        return []
    return [_convert_photo_url(url) for url in photo_urls]


# ==================== HTML 页面 ====================

@page_router.get("/inspection", response_class=HTMLResponse, summary="巡检详情页面")
async def inspection_page():
    """返回巡检详情 HTML 页面"""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "inspection.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>页面未找到</h1>", status_code=404)


# ==================== API 路由 ====================


# ==================== Pydantic 模型 ====================

class PlanCreateRequest(BaseModel):
    """创建巡检计划请求"""
    plan_name: str = Field(..., description="计划名称")
    area_type: str = Field(..., description="区域类型: teaching/dormitory/canteen/playground/fire/public")
    check_category: str = Field(..., description="检查大类: safety/hygiene/facility/discipline")
    frequency: str = Field("daily", description="巡检频率: daily/weekly/monthly/custom")
    assigned_inspectors: list = Field(default_factory=list, description="巡检员ID列表")
    assigned_areas: list = Field(default_factory=list, description="巡检区域列表")
    check_items: list = Field(default_factory=list, description="检查项列表")
    start_date: str = Field("", description="开始日期")
    end_date: str = Field("", description="结束日期")
    description: str = Field("", description="计划描述")


class PlanUpdateStatusRequest(BaseModel):
    """更新计划状态请求"""
    status: str = Field(..., description="新状态: draft/active/completed/cancelled")


class PointCreateRequest(BaseModel):
    """创建巡检点位请求"""
    point_name: str = Field(..., description="点位名称")
    area_type: str = Field(..., description="区域类型")
    location: str = Field(..., description="位置描述")
    latitude: float = Field(0.0, description="纬度")
    longitude: float = Field(0.0, description="经度")
    check_items: list = Field(default_factory=list, description="检查项列表")
    requires_photo: bool = Field(True, description="是否要求拍照")
    requires_location: bool = Field(False, description="是否要求定位")
    qr_code: str = Field("", description="二维码")


class CheckInRequest(BaseModel):
    """打卡签到请求"""
    plan_id: str = Field(..., description="计划ID")
    point_id: str = Field(..., description="点位ID")
    latitude: float = Field(0.0, description="纬度")
    longitude: float = Field(0.0, description="经度")
    photo_urls: list = Field(default_factory=list, description="照片URL列表")
    notes: str = Field("", description="备注")


class CheckOutRequest(BaseModel):
    """签退请求"""
    record_id: str = Field(..., description="记录ID")
    check_results: list = Field(default_factory=list, description="检查结果列表")


class IssueReportRequest(BaseModel):
    """问题上报请求"""
    record_id: str = Field("", description="关联的巡检记录ID")
    category: str = Field(..., description="问题分类")
    title: str = Field(..., description="问题标题")
    description: str = Field("", description="问题描述")
    photo_urls: list = Field(default_factory=list, description="照片URL列表")
    severity: str = Field("medium", description="严重程度: low/medium/high/critical")
    point_name: str = Field("", description="点位名称")


class IssueAssignRequest(BaseModel):
    """派单请求"""
    assigned_to: str = Field(..., description="整改负责人ID")
    assigned_to_name: str = Field("", description="整改负责人姓名")
    deadline_hours: int = Field(24, description="整改期限（小时）")


class RectificationSubmitRequest(BaseModel):
    """提交整改请求"""
    rectification_photos: list = Field(default_factory=list, description="整改照片")
    rectification_notes: str = Field("", description="整改说明")


class ReviewRequest(BaseModel):
    """复查请求"""
    review_result: str = Field(..., description="复查结果: pass/reject")
    review_notes: str = Field("", description="复查说明")


# ==================== 计划 API ====================

@router.get("/plans", summary="获取巡检计划列表")
async def list_plans(
    status: Optional[str] = Query(None, description="状态过滤"),
    area_type: Optional[str] = Query(None, description="区域类型过滤"),
    inspector_id: Optional[str] = Query(None, description="巡检员ID过滤"),
):
    service = get_inspection_service()
    plans = service.list_plans(status=status, area_type=area_type, inspector_id=inspector_id)
    from dataclasses import asdict

    result = []
    for p in plans:
        plan_dict = asdict(p)
        # 添加名称字段
        plan_dict["area_name"] = AREA_TYPE_NAMES.get(p.area_type, p.area_type)
        plan_dict["category_name"] = CHECK_CATEGORY_NAMES.get(p.check_category, p.check_category)
        plan_dict["status_name"] = PLAN_STATUS_NAMES.get(p.status, p.status)
        result.append(plan_dict)

    return {"plans": result, "total": len(result)}


@router.get("/plans/{plan_id}", summary="获取计划详情")
async def get_plan(plan_id: str):
    service = get_inspection_service()
    plan = service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    from dataclasses import asdict
    return asdict(plan)


@router.post("/plans", summary="创建巡检计划")
async def create_plan(req: PlanCreateRequest):
    service = get_inspection_service()
    plan = service.create_plan(
        plan_name=req.plan_name,
        area_type=req.area_type,
        check_category=req.check_category,
        frequency=req.frequency,
        assigned_inspectors=req.assigned_inspectors,
        assigned_areas=req.assigned_areas,
        check_items=req.check_items,
        start_date=req.start_date,
        end_date=req.end_date,
        description=req.description,
    )
    from dataclasses import asdict
    return {"success": True, "plan": asdict(plan)}


@router.put("/plans/{plan_id}/status", summary="更新计划状态")
async def update_plan_status(plan_id: str, req: PlanUpdateStatusRequest):
    service = get_inspection_service()
    ok = service.update_plan_status(plan_id, req.status)
    if not ok:
        raise HTTPException(status_code=404, detail="计划不存在")
    return {"success": True}


@router.delete("/plans/{plan_id}", summary="删除计划")
async def delete_plan(plan_id: str):
    service = get_inspection_service()
    ok = service.delete_plan(plan_id)
    if not ok:
        raise HTTPException(status_code=404, detail="计划不存在")
    return {"success": True}


class BatchDeleteRequest(BaseModel):
    ids: list = Field(..., description="要删除的ID列表")


@router.delete("/plans/batch", summary="批量删除计划")
async def delete_plans_batch(req: BatchDeleteRequest):
    service = get_inspection_service()
    count = service.delete_plans_batch(req.ids)
    return {"success": True, "deleted": count}


# ==================== 点位 API ====================

@router.get("/points", summary="获取巡检点位列表")
async def list_points(
    area_type: Optional[str] = Query(None, description="区域类型过滤"),
):
    service = get_inspection_service()
    points = service.list_points(area_type=area_type)
    from dataclasses import asdict

    result = []
    for p in points:
        point_dict = asdict(p)
        # 添加区域类型名称
        point_dict["area_name"] = AREA_TYPE_NAMES.get(p.area_type, p.area_type)
        result.append(point_dict)

    return {"points": result, "total": len(result)}


@router.post("/points", summary="创建巡检点位")
async def create_point(req: PointCreateRequest):
    service = get_inspection_service()
    point = service.create_point(
        point_name=req.point_name,
        area_type=req.area_type,
        location=req.location,
        check_items=req.check_items,
        latitude=req.latitude,
        longitude=req.longitude,
        requires_photo=req.requires_photo,
        requires_location=req.requires_location,
        qr_code=req.qr_code,
    )
    from dataclasses import asdict
    return {"success": True, "point": asdict(point)}


@router.delete("/points/{point_id}", summary="删除点位")
async def delete_point(point_id: str):
    service = get_inspection_service()
    ok = service.delete_point(point_id)
    if not ok:
        raise HTTPException(status_code=404, detail="点位不存在")
    return {"success": True}


@router.put("/points/{point_id}", summary="更新点位信息")
async def update_point(point_id: str, req: PointCreateRequest):
    service = get_inspection_service()
    ok = service.update_point(point_id, req.dict())
    if not ok:
        raise HTTPException(status_code=404, detail="点位不存在")
    return {"success": True}


@router.delete("/points/batch", summary="批量删除点位")
async def delete_points_batch(req: BatchDeleteRequest):
    service = get_inspection_service()
    count = service.delete_points_batch(req.ids)
    return {"success": True, "deleted": count}


# ==================== 打卡 API ====================

@router.post("/checkin", summary="巡检打卡签到")
async def check_in(req: CheckInRequest):
    service = get_inspection_service()
    record, msg = service.check_in(
        plan_id=req.plan_id,
        point_id=req.point_id,
        inspector_id="web_user",
        latitude=req.latitude,
        longitude=req.longitude,
        photo_urls=req.photo_urls,
        notes=req.notes,
    )
    if not record:
        raise HTTPException(status_code=400, detail=msg)
    from dataclasses import asdict
    return {"success": True, "message": msg, "record": asdict(record)}


@router.post("/checkout", summary="巡检签退")
async def check_out(req: CheckOutRequest):
    service = get_inspection_service()
    ok, msg = service.check_out(
        record_id=req.record_id,
        check_results=req.check_results,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@router.get("/records", summary="获取巡检记录列表")
async def list_records(
    plan_id: Optional[str] = Query(None),
    point_id: Optional[str] = Query(None),
    inspector_id: Optional[str] = Query(None),
    date: Optional[str] = Query(None, description="日期 YYYY-MM-DD"),
):
    service = get_inspection_service()
    records = service.list_records(
        plan_id=plan_id, point_id=point_id,
        inspector_id=inspector_id, date_str=date,
    )
    from dataclasses import asdict
    # 预加载点位映射，用于将 point_id 转为中文名称
    all_points = service.list_points()
    point_name_map = {p.point_id: p.point_name for p in all_points}
    records_data = []
    for r in records:
        record_dict = asdict(r)
        # 补充点位中文名称
        record_dict["point_name"] = point_name_map.get(r.point_id, r.point_id)
        # 格式化时间
        if r.check_in_time:
            record_dict["check_in_time_str"] = datetime.fromtimestamp(r.check_in_time).strftime("%Y-%m-%d %H:%M:%S")
        if r.check_out_time:
            record_dict["check_out_time_str"] = datetime.fromtimestamp(r.check_out_time).strftime("%Y-%m-%d %H:%M:%S")
        # 转换照片URL
        record_dict["photo_urls"] = _convert_photo_urls(r.photo_urls)
        records_data.append(record_dict)
    return {"records": records_data, "total": len(records)}


class RecordUpdateRequest(BaseModel):
    notes: Optional[str] = Field(None, description="备注")
    overall_status: Optional[str] = Field(None, description="总体状态")


@router.put("/records/{record_id}", summary="更新巡检记录")
async def update_record(record_id: str, req: RecordUpdateRequest):
    service = get_inspection_service()
    fields = {k: v for k, v in req.dict().items() if v is not None}
    ok = service.update_record(record_id, fields)
    if not ok:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True}


@router.delete("/records/{record_id}", summary="删除巡检记录")
async def delete_record(record_id: str):
    service = get_inspection_service()
    count = service.delete_records_batch([record_id])
    if count == 0:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True}


@router.delete("/records/batch", summary="批量删除记录")
async def delete_records_batch(req: BatchDeleteRequest):
    service = get_inspection_service()
    count = service.delete_records_batch(req.ids)
    return {"success": True, "deleted": count}


# ==================== 问题 API ====================

@router.post("/issues", summary="上报巡检问题")
async def report_issue(req: IssueReportRequest):
    service = get_inspection_service()
    issue = service.report_issue(
        record_id=req.record_id,
        category=req.category,
        title=req.title,
        description=req.description,
        reported_by="web_user",
        photo_urls=req.photo_urls,
        severity=req.severity,
        point_name=req.point_name,
    )
    from dataclasses import asdict
    return {"success": True, "issue": asdict(issue)}


@router.get("/issues", summary="获取问题列表")
async def list_issues(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    plan_id: Optional[str] = Query(None),
):
    service = get_inspection_service()
    issues = service.list_issues(
        status=status, category=category,
        severity=severity, assigned_to=assigned_to, plan_id=plan_id,
    )
    from dataclasses import asdict
    issues_data = []
    for i in issues:
        issue_dict = asdict(i)
        # 添加分类和状态名称
        issue_dict["category_name"] = ISSUE_CATEGORY_NAMES.get(i.category, i.category)
        issue_dict["status_name"] = ISSUE_STATUS_NAMES.get(i.status, i.status)
        # 格式化时间
        if i.reported_at:
            issue_dict["reported_at_str"] = datetime.fromtimestamp(i.reported_at).strftime("%Y-%m-%d %H:%M:%S")
        if i.assigned_at:
            issue_dict["assigned_at_str"] = datetime.fromtimestamp(i.assigned_at).strftime("%Y-%m-%d %H:%M:%S")
        if i.deadline:
            issue_dict["deadline_str"] = datetime.fromtimestamp(i.deadline).strftime("%Y-%m-%d %H:%M:%S")
        # 转换照片URL
        issue_dict["photo_urls"] = _convert_photo_urls(i.photo_urls)
        issues_data.append(issue_dict)
    return {"issues": issues_data, "total": len(issues)}


@router.get("/issues/{issue_id}", summary="获取问题详情")
async def get_issue(issue_id: str):
    service = get_inspection_service()
    issue = service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="问题不存在")
    from dataclasses import asdict
    return asdict(issue)


class IssueUpdateRequest(BaseModel):
    title: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    category: Optional[str] = Field(None)
    severity: Optional[str] = Field(None)
    status: Optional[str] = Field(None)


@router.put("/issues/{issue_id}", summary="更新问题信息")
async def update_issue(issue_id: str, req: IssueUpdateRequest):
    service = get_inspection_service()
    fields = {k: v for k, v in req.dict().items() if v is not None}
    ok = service.update_issue(issue_id, fields)
    if not ok:
        raise HTTPException(status_code=404, detail="问题不存在")
    return {"success": True}


@router.delete("/issues/{issue_id}", summary="删除问题")
async def delete_issue(issue_id: str):
    service = get_inspection_service()
    count = service.delete_issues_batch([issue_id])
    if count == 0:
        raise HTTPException(status_code=404, detail="问题不存在")
    return {"success": True}


@router.delete("/issues/batch", summary="批量删除问题")
async def delete_issues_batch(req: BatchDeleteRequest):
    service = get_inspection_service()
    count = service.delete_issues_batch(req.ids)
    return {"success": True, "deleted": count}


# ==================== 工单 API ====================

@router.post("/issues/{issue_id}/assign", summary="派单")
async def assign_issue(issue_id: str, req: IssueAssignRequest):
    service = get_inspection_service()
    ok, msg = service.assign_order(
        issue_id=issue_id,
        assigned_to=req.assigned_to,
        assigned_to_name=req.assigned_to_name,
        assigned_by="web_admin",
        deadline_hours=req.deadline_hours,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@router.post("/issues/{issue_id}/rectification", summary="提交整改")
async def submit_rectification(issue_id: str, req: RectificationSubmitRequest):
    service = get_inspection_service()
    ok, msg = service.submit_rectification(
        issue_id=issue_id,
        rectification_photos=req.rectification_photos,
        rectification_notes=req.rectification_notes,
        operator="web_user",
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@router.post("/issues/{issue_id}/review", summary="复查验收")
async def review_issue(issue_id: str, req: ReviewRequest):
    service = get_inspection_service()
    ok, msg = service.review_issue(
        issue_id=issue_id,
        review_result=req.review_result,
        reviewer_id="web_reviewer",
        review_notes=req.review_notes,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@router.get("/orders", summary="获取工单列表")
async def list_orders(
    status: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
):
    service = get_inspection_service()
    orders = service.get_orders(status=status, assigned_to=assigned_to)
    from dataclasses import asdict
    return {"orders": [asdict(o) for o in orders], "total": len(orders)}


@router.delete("/orders/{order_id}", summary="删除工单")
async def delete_order(order_id: str):
    service = get_inspection_service()
    count = service.delete_orders_batch([order_id])
    if count == 0:
        raise HTTPException(status_code=404, detail="工单不存在")
    return {"success": True}


@router.delete("/orders/batch", summary="批量删除工单")
async def delete_orders_batch(req: BatchDeleteRequest):
    service = get_inspection_service()
    count = service.delete_orders_batch(req.ids)
    return {"success": True, "deleted": count}


# ==================== 统计 API ====================

@router.get("/stats", summary="获取巡检统计")
async def get_stats():
    service = get_inspection_service()
    stats = service.get_stats()
    from dataclasses import asdict
    return asdict(stats)


# ==================== 导入 API ====================

@router.post("/import/points", summary="导入巡检点位（Excel文件）")
async def import_points(file: UploadFile = File(...)):
    """上传 Excel 文件导入巡检点位"""
    import tempfile
    import shutil

    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="请上传 Excel 文件（.xlsx/.xls）")

    # 保存到临时文件
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        service = get_inspection_service()
        imported, skipped, msg = service.import_points_from_excel(temp_path)
        return {"success": True, "imported": imported, "skipped": skipped, "message": msg}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/import/issues", summary="导入巡检问题（Excel文件）")
async def import_issues(file: UploadFile = File(...)):
    """上传 Excel 文件导入巡检问题"""
    import tempfile
    import shutil

    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="请上传 Excel 文件（.xlsx/.xls）")

    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        service = get_inspection_service()
        imported, skipped, msg = service.import_issues_from_excel(temp_path)
        return {"success": True, "imported": imported, "skipped": skipped, "message": msg}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ==================== 计划详情 API ====================

@router.get("/plans/{plan_id}/detail", summary="获取计划详情（含关联记录和点位）")
async def get_plan_detail(plan_id: str):
    """获取巡检计划详情，包括关联的点位、巡检记录和问题"""
    service = get_inspection_service()
    plan = service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")

    from dataclasses import asdict

    # 获取关联的点位
    points = []
    for point_id in plan.assigned_areas:
        point = service.get_point(point_id)
        if point:
            points.append(asdict(point))

    # 获取该计划的所有巡检记录
    records = service.list_records(plan_id=plan_id)
    # 点位映射
    point_name_map = {}
    for point_id in plan.assigned_areas:
        point = service.get_point(point_id)
        if point:
            point_name_map[point.point_id] = point.point_name
    records_data = []
    for r in records:
        record_dict = asdict(r)
        # 补充点位中文名称
        record_dict["point_name"] = point_name_map.get(r.point_id, r.point_id)
        # 格式化时间
        if r.check_in_time:
            record_dict["check_in_time_str"] = datetime.fromtimestamp(r.check_in_time).strftime("%Y-%m-%d %H:%M:%S")
        if r.check_out_time:
            record_dict["check_out_time_str"] = datetime.fromtimestamp(r.check_out_time).strftime("%Y-%m-%d %H:%M:%S")
        # 转换照片URL
        record_dict["photo_urls"] = _convert_photo_urls(r.photo_urls)
        records_data.append(record_dict)

    # 获取该计划关联的问题
    issues = service.list_issues(plan_id=plan_id)
    issues_data = []
    for i in issues:
        issue_dict = asdict(i)
        issue_dict["photo_urls"] = _convert_photo_urls(i.photo_urls)
        issues_data.append(issue_dict)

    return {
        "plan": asdict(plan),
        "points": points,
        "records": records_data,
        "issues": issues_data,
        "stats": {
            "total_records": len(records),
            "completed_records": sum(1 for r in records if r.check_out_time),
            "total_issues": len(issues),
            "pending_issues": sum(1 for i in issues if i.status in ("pending", "assigned", "in_progress")),
        }
    }


# ==================== 照片管理 API ====================

@router.post("/upload-photo", summary="上传巡检照片")
async def upload_photo(file: UploadFile = File(...), record_id: str = Query("", description="关联的记录ID")):
    """上传巡检照片，返回照片URL"""
    # 验证文件类型
    allowed_types = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_types:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}，支持: {', '.join(allowed_types)}")

    # 生成唯一文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{timestamp}_{unique_id}{ext}"

    # 按日期分目录存储
    date_dir = datetime.now().strftime("%Y%m%d")
    photo_dir = os.path.join(PHOTOS_DIR, date_dir)
    os.makedirs(photo_dir, exist_ok=True)

    file_path = os.path.join(photo_dir, filename)

    # 保存文件
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        logger.error(f"保存照片失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存照片失败: {str(e)}")

    # 返回照片URL
    photo_url = f"/api/inspection/photos/{date_dir}/{filename}"
    logger.info(f"照片已上传: {photo_url}")

    return {
        "success": True,
        "photo_url": photo_url,
        "filename": filename,
        "size": len(content),
    }


@router.get("/photos/{date_dir}/{filename}", summary="获取巡检照片")
async def get_photo(date_dir: str, filename: str):
    """获取巡检照片文件"""
    file_path = os.path.join(PHOTOS_DIR, date_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="照片不存在")

    # 获取 MIME 类型
    ext = os.path.splitext(filename)[1].lower()
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    media_type = mime_types.get(ext, "image/jpeg")

    return FileResponse(file_path, media_type=media_type)


@router.get("/records/{record_id}/photos", summary="获取巡检记录的照片列表")
async def get_record_photos(record_id: str):
    """获取指定巡检记录的所有照片"""
    service = get_inspection_service()
    record = service._records.get(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    return {
        "record_id": record_id,
        "photos": _convert_photo_urls(record.photo_urls or []),
    }


@router.post("/records/{record_id}/photos", summary="添加照片到巡检记录")
async def add_photo_to_record(record_id: str, photo_url: str = Query(..., description="照片URL")):
    """为巡检记录添加照片"""
    service = get_inspection_service()
    record = service._records.get(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    if record.photo_urls is None:
        record.photo_urls = []

    if photo_url not in record.photo_urls:
        record.photo_urls.append(photo_url)
        service._save_records()

    return {"success": True, "photos": record.photo_urls}


@router.get("/local-photo", summary="获取本地照片文件")
async def get_local_photo(file_path: str = Query(..., description="本地文件路径")):
    """
    获取本地存储的照片文件

    用于访问通过钉钉机器人上传的照片（存储在本地文件系统）
    """
    # 安全检查：只允许访问特定目录下的文件
    allowed_dirs = [
        os.path.abspath("knowledge"),
        os.path.abspath(PHOTOS_DIR),
    ]

    abs_path = os.path.abspath(file_path)

    # 检查文件是否在允许的目录下
    if not any(abs_path.startswith(d) for d in allowed_dirs):
        raise HTTPException(status_code=403, detail="无权访问该文件")

    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    # 获取 MIME 类型
    ext = os.path.splitext(abs_path)[1].lower()
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    media_type = mime_types.get(ext, "application/octet-stream")

    return FileResponse(abs_path, media_type=media_type)
