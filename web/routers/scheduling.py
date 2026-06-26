"""
排课系统 API
展示排课结果、调课申请、审批流程
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from pydantic import BaseModel
import json
import os
import time

from web.config import KNOWLEDGE_DIR

router = APIRouter()


class SwapRequest(BaseModel):
    """调课申请"""
    class_id: str
    class_name: str
    day1: str
    period1: int
    day2: str
    period2: int
    reason: str = ""
    permanent: bool = False


class SwapApproval(BaseModel):
    """调课审批"""
    action: str  # approve, reject
    reason: str = ""


# 星期映射
WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 课时映射
PERIODS = {
    1: "第1节",
    2: "第2节",
    3: "第3节",
    4: "第4节",
    5: "第5节",
    6: "第6节",
    7: "第7节",
    8: "第8节",
}


@router.get("/schedule")
async def get_schedule(
    corp_id: str = Query(..., description="企业ID"),
    class_id: Optional[str] = Query(None, description="班级ID，不传则返回所有班级")
):
    """获取排课结果"""
    schedule_file = os.path.join(KNOWLEDGE_DIR, corp_id, "scheduling", "schedule_result.json")

    if not os.path.exists(schedule_file):
        return {"entries": [], "classes": {}, "teachers": {}, "classrooms": {}}

    try:
        with open(schedule_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        entries = data.get("entries", [])

        # 按班级筛选
        if class_id:
            entries = [e for e in entries if e.get("class_id") == class_id]

        # 加载基础数据
        scheduling_data = _load_scheduling_data(corp_id)

        # 转换为前端友好的格式
        schedule = _format_schedule(entries, scheduling_data)

        return schedule
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取排课结果失败: {str(e)}")


@router.get("/classes")
async def get_classes(corp_id: str = Query(..., description="企业ID")):
    """获取班级列表"""
    scheduling_data = _load_scheduling_data(corp_id)
    classes = scheduling_data.get("classes", [])

    return {
        "classes": [{"id": c.get("id"), "name": c.get("name"), "grade": c.get("grade")} for c in classes],
        "total": len(classes)
    }


@router.get("/teachers")
async def get_teachers(corp_id: str = Query(..., description="企业ID")):
    """获取教师列表"""
    scheduling_data = _load_scheduling_data(corp_id)
    teachers = scheduling_data.get("teachers", [])

    return {
        "teachers": [{"id": t.get("id"), "name": t.get("name"), "subjects": t.get("subjects", [])} for t in teachers],
        "total": len(teachers)
    }


@router.get("/swap-requests")
async def get_swap_requests(
    corp_id: str = Query(..., description="企业ID"),
    status: Optional[str] = Query(None, description="状态筛选: pending/approved/rejected/cancelled")
):
    """获取调课申请列表"""
    requests = _load_swap_requests(corp_id)

    # 状态筛选
    if status:
        requests = {k: v for k, v in requests.items() if v.get("status") == status}

    # 按创建时间倒序排序
    sorted_requests = sorted(requests.values(), key=lambda x: x.get("created_at", 0), reverse=True)

    return {
        "requests": sorted_requests,
        "total": len(sorted_requests)
    }


@router.post("/swap-requests")
async def create_swap_request(
    corp_id: str = Query(..., description="企业ID"),
    user_id: str = Query(..., description="用户ID"),
    user_name: str = Query(..., description="用户名"),
    request: SwapRequest = None
):
    """创建调课申请"""
    # 加载排课结果
    schedule_file = os.path.join(KNOWLEDGE_DIR, corp_id, "scheduling", "schedule_result.json")
    if not os.path.exists(schedule_file):
        raise HTTPException(status_code=404, detail="排课结果不存在")

    with open(schedule_file, 'r', encoding='utf-8') as f:
        schedule_data = json.load(f)

    entries = schedule_data.get("entries", [])

    # 查找要调课的两个课程
    entry1 = None
    entry2 = None

    for entry in entries:
        if (entry.get("class_id") == request.class_id and
            entry.get("time_slot", {}).get("weekday") == request.day1 and
            entry.get("time_slot", {}).get("period") == request.period1):
            entry1 = entry
        if (entry.get("class_id") == request.class_id and
            entry.get("time_slot", {}).get("weekday") == request.day2 and
            entry.get("time_slot", {}).get("period") == request.period2):
            entry2 = entry

    if not entry1 or not entry2:
        raise HTTPException(status_code=404, detail="未找到指定的课程")

    # 加载基础数据获取教师名称
    scheduling_data = _load_scheduling_data(corp_id)
    teachers = {t.get("id"): t.get("name") for t in scheduling_data.get("teachers", [])}
    courses = {c.get("id"): c.get("name") for c in scheduling_data.get("courses", [])}

    # 创建调课申请
    swap_id = f"swap_{int(time.time() * 1000)}"
    swap_request = {
        "swap_id": swap_id,
        "requester_id": user_id,
        "requester_nick": user_name,
        "corp_id": corp_id,
        "class_id": request.class_id,
        "class_name": request.class_name,
        "day1": request.day1,
        "period1": request.period1,
        "day2": request.day2,
        "period2": request.period2,
        "course1_name": courses.get(entry1.get("course_id"), entry1.get("course_id")),
        "course1_teacher": teachers.get(entry1.get("teacher_id"), entry1.get("teacher_id")),
        "course2_name": courses.get(entry2.get("course_id"), entry2.get("course_id")),
        "course2_teacher": teachers.get(entry2.get("teacher_id"), entry2.get("teacher_id")),
        "entry1_id": entry1.get("id"),
        "entry2_id": entry2.get("id"),
        "reason": request.reason,
        "permanent": request.permanent,
        "status": "pending",
        "created_at": time.time(),
        "updated_at": time.time(),
    }

    # 保存调课申请
    _save_swap_request(corp_id, swap_id, swap_request)

    return {"message": "调课申请已提交", "swap_id": swap_id, "request": swap_request}


@router.put("/swap-requests/{swap_id}/approve")
async def approve_swap_request(
    swap_id: str,
    corp_id: str = Query(..., description="企业ID"),
    approver_id: str = Query(..., description="审批人ID"),
    approver_name: str = Query(..., description="审批人名称"),
    approval: SwapApproval = None
):
    """审批调课申请"""
    requests = _load_swap_requests(corp_id)

    if swap_id not in requests:
        raise HTTPException(status_code=404, detail="调课申请不存在")

    request = requests[swap_id]

    if request.get("status") != "pending":
        raise HTTPException(status_code=400, detail="该申请已被处理")

    # 更新状态
    if approval.action == "approve":
        request["status"] = "approved"
        # 执行调课
        _execute_swap(corp_id, request)
    else:
        request["status"] = "rejected"
        request["reject_reason"] = approval.reason

    request["approver_id"] = approver_id
    request["approver_nick"] = approver_name
    request["updated_at"] = time.time()

    # 保存更新
    _save_swap_request(corp_id, swap_id, request)

    action_text = "批准" if approval.action == "approve" else "拒绝"
    return {"message": f"已{action_text}调课申请", "request": request}


@router.delete("/swap-requests/{swap_id}")
async def cancel_swap_request(
    swap_id: str,
    corp_id: str = Query(..., description="企业ID"),
    user_id: str = Query(..., description="用户ID")
):
    """取消调课申请（仅申请人可取消）"""
    requests = _load_swap_requests(corp_id)

    if swap_id not in requests:
        raise HTTPException(status_code=404, detail="调课申请不存在")

    request = requests[swap_id]

    if request.get("requester_id") != user_id:
        raise HTTPException(status_code=403, detail="只有申请人可以取消")

    if request.get("status") != "pending":
        raise HTTPException(status_code=400, detail="只能取消待审批的申请")

    request["status"] = "cancelled"
    request["updated_at"] = time.time()

    _save_swap_request(corp_id, swap_id, request)

    return {"message": "已取消调课申请", "request": request}


@router.get("/swap-log")
async def get_swap_log(
    corp_id: str = Query(..., description="企业ID"),
    limit: int = Query(50, ge=1, le=200, description="返回数量")
):
    """获取调课历史记录"""
    log_file = os.path.join(KNOWLEDGE_DIR, corp_id, "scheduling", "swap_log.json")

    if not os.path.exists(log_file):
        return {"logs": [], "total": 0}

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = json.load(f)

        # 按时间倒序排序
        sorted_logs = sorted(logs.values(), key=lambda x: x.get("timestamp", 0), reverse=True)

        return {
            "logs": sorted_logs[:limit],
            "total": len(logs)
        }
    except:
        return {"logs": [], "total": 0}


def _load_scheduling_data(corp_id: str) -> dict:
    """加载排课基础数据"""
    data_file = os.path.join(KNOWLEDGE_DIR, corp_id, "scheduling", "scheduling_data.json")

    if not os.path.exists(data_file):
        return {"classes": [], "teachers": [], "courses": [], "classrooms": []}

    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"classes": [], "teachers": [], "courses": [], "classrooms": []}


def _load_swap_requests(corp_id: str) -> dict:
    """加载调课申请"""
    requests_file = os.path.join(KNOWLEDGE_DIR, corp_id, "scheduling", "swap_requests.json")

    if not os.path.exists(requests_file):
        return {}

    try:
        with open(requests_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def _save_swap_request(corp_id: str, swap_id: str, request: dict):
    """保存调课申请"""
    requests = _load_swap_requests(corp_id)
    requests[swap_id] = request

    requests_file = os.path.join(KNOWLEDGE_DIR, corp_id, "scheduling", "swap_requests.json")
    os.makedirs(os.path.dirname(requests_file), exist_ok=True)

    with open(requests_file, 'w', encoding='utf-8') as f:
        json.dump(requests, f, ensure_ascii=False, indent=2)


def _format_schedule(entries: list, scheduling_data: dict) -> dict:
    """格式化排课结果为前端友好格式"""
    # 构建映射
    classes = {c.get("id"): c.get("name") for c in scheduling_data.get("classes", [])}
    teachers = {t.get("id"): t.get("name") for t in scheduling_data.get("teachers", [])}
    courses = {c.get("id"): c.get("name") for c in scheduling_data.get("courses", [])}
    classrooms = {r.get("id"): r.get("name") for r in scheduling_data.get("classrooms", [])}

    # 按班级和星期组织数据
    schedule = {}
    for entry in entries:
        class_id = entry.get("class_id")
        time_slot = entry.get("time_slot", {})
        weekday = time_slot.get("weekday")
        period = time_slot.get("period")

        if class_id not in schedule:
            schedule[class_id] = {
                "class_id": class_id,
                "class_name": classes.get(class_id, class_id),
                "lessons": {}
            }

        key = f"{weekday}_{period}"
        schedule[class_id]["lessons"][key] = {
            "entry_id": entry.get("id"),
            "course_id": entry.get("course_id"),
            "course_name": courses.get(entry.get("course_id"), entry.get("course_id")),
            "teacher_id": entry.get("teacher_id"),
            "teacher_name": teachers.get(entry.get("teacher_id"), entry.get("teacher_id")),
            "classroom_id": entry.get("classroom_id"),
            "classroom_name": classrooms.get(entry.get("classroom_id"), entry.get("classroom_id")),
            "weekday": weekday,
            "period": period,
        }

    return {
        "schedule": list(schedule.values()),
        "classes": classes,
        "teachers": teachers,
        "courses": courses,
        "classrooms": classrooms,
        "weekdays": WEEKDAYS,
        "periods": PERIODS,
    }


def _execute_swap(corp_id: str, request: dict):
    """执行调课操作"""
    schedule_file = os.path.join(KNOWLEDGE_DIR, corp_id, "scheduling", "schedule_result.json")

    if not os.path.exists(schedule_file):
        return

    try:
        with open(schedule_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        entries = data.get("entries", [])
        entry1_id = request.get("entry1_id")
        entry2_id = request.get("entry2_id")

        # 找到两个 entry 并交换时间
        for entry in entries:
            if entry.get("id") == entry1_id:
                entry["time_slot"] = {
                    "weekday": request.get("day2"),
                    "period": request.get("period2"),
                    "period_type": "上午" if request.get("period2", 0) <= 4 else "下午"
                }
            elif entry.get("id") == entry2_id:
                entry["time_slot"] = {
                    "weekday": request.get("day1"),
                    "period": request.get("period1"),
                    "period_type": "上午" if request.get("period1", 0) <= 4 else "下午"
                }

        data["entries"] = entries

        # 保存更新后的排课结果
        with open(schedule_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 记录调课日志
        _log_swap(corp_id, request)

    except Exception as e:
        print(f"执行调课失败: {e}")


def _log_swap(corp_id: str, request: dict):
    """记录调课日志"""
    log_file = os.path.join(KNOWLEDGE_DIR, corp_id, "scheduling", "swap_log.json")

    logs = {}
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except:
            pass

    log_id = f"log_{int(time.time() * 1000)}"
    logs[log_id] = {
        "log_id": log_id,
        "swap_id": request.get("swap_id"),
        "class_name": request.get("class_name"),
        "course1": f"{request.get('course1_name')}({request.get('course1_teacher')})",
        "course2": f"{request.get('course2_name')}({request.get('course2_teacher')})",
        "from1": f"{request.get('day1')}第{request.get('period1')}节",
        "to1": f"{request.get('day2')}第{request.get('period2')}节",
        "from2": f"{request.get('day2')}第{request.get('period2')}节",
        "to2": f"{request.get('day1')}第{request.get('period1')}节",
        "requester": request.get("requester_nick"),
        "approver": request.get("approver_nick"),
        "timestamp": time.time(),
    }

    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)
