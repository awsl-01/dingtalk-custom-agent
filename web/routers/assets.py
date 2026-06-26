"""
资产管理 API
提供资产列表、创建、编辑、删除、借用、归还、统计等 REST API
"""
import os
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field

from agent.skills.asset_storage import (
    load_assets, save_assets, create_asset, get_asset_by_id,
    get_assets_by_name, get_asset_stats, search_assets,
    update_asset_status, add_borrow_record, return_asset, delete_asset,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["资产管理"])


# ==================== Pydantic 模型 ====================

class AssetCreateRequest(BaseModel):
    name: str = Field(..., description="资产名称")
    category: str = Field("其他", description="分类")
    location: str = Field("未指定", description="存放位置")
    responsible_user: str = Field("未指定", description="负责人")
    purchase_date: str = Field("", description="采购日期")
    description: str = Field("", description="描述")
    class_name: str = Field("", description="使用班级")


class AssetUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="资产名称")
    category: Optional[str] = Field(None, description="分类")
    location: Optional[str] = Field(None, description="存放位置")
    responsible_user: Optional[str] = Field(None, description="负责人")
    purchase_date: Optional[str] = Field(None, description="采购日期")
    description: Optional[str] = Field(None, description="描述")
    status: Optional[str] = Field(None, description="状态")
    class_name: Optional[str] = Field(None, description="使用班级")


class AssetBorrowRequest(BaseModel):
    borrower: str = Field(..., description="借用人")
    class_name: str = Field("", description="借用班级")


class BatchDeleteRequest(BaseModel):
    ids: List[str] = Field(..., description="要删除的ID列表")


# ==================== API 路由 ====================

@router.get("/list", summary="获取资产列表")
async def list_assets(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    category: Optional[str] = Query(None, description="分类过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    location: Optional[str] = Query(None, description="位置过滤"),
):
    assets = load_assets("default")

    # 搜索过滤
    if keyword:
        assets = search_assets(keyword, "default")

    # 分类过滤
    if category:
        assets = [a for a in assets if a.get("category") == category]

    # 状态过滤
    if status:
        assets = [a for a in assets if a.get("status") == status]

    # 位置过滤
    if location:
        assets = [a for a in assets if a.get("location") == location]

    return {"assets": assets, "total": len(assets)}


@router.get("/stats", summary="获取资产统计")
async def get_stats():
    stats = get_asset_stats("default")
    return stats


@router.get("/detail/{asset_id}", summary="获取资产详情")
async def get_asset_detail(asset_id: str):
    asset = get_asset_by_id(asset_id, "default")
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    return asset


@router.post("/create", summary="创建资产")
async def create_asset_api(req: AssetCreateRequest):
    asset_data = req.dict()
    new_asset = create_asset(asset_data, "default")
    return {"success": True, "asset": new_asset}


@router.put("/update/{asset_id}", summary="更新资产信息")
async def update_asset(asset_id: str, req: AssetUpdateRequest):
    asset = get_asset_by_id(asset_id, "default")
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")

    # 更新字段 - 只更新非None的字段
    assets = load_assets("default")
    for a in assets:
        if a.get("id") == asset_id:
            # 获取请求中实际设置的字段（排除None值）
            update_data = req.model_dump(exclude_unset=True)
            # 只更新有值的字段
            for key, value in update_data.items():
                if value is not None:
                    a[key] = value
            from datetime import datetime
            a["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            break
    save_assets(assets, "default")
    return {"success": True}


@router.delete("/delete/{asset_id}", summary="删除资产")
async def delete_asset_api(asset_id: str):
    ok = delete_asset(asset_id, "default")
    if not ok:
        raise HTTPException(status_code=404, detail="资产不存在")
    return {"success": True}


@router.delete("/batch", summary="批量删除资产")
async def delete_assets_batch(req: BatchDeleteRequest):
    count = 0
    for aid in req.ids:
        if delete_asset(aid, "default"):
            count += 1
    return {"success": True, "deleted": count}


@router.post("/borrow/{asset_id}", summary="借用资产")
async def borrow_asset(asset_id: str, req: AssetBorrowRequest):
    asset = get_asset_by_id(asset_id, "default")
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    if asset.get("status") != "在用":
        raise HTTPException(status_code=400, detail=f"资产当前状态为「{asset.get('status')}」，无法借用")

    # 更新资产的使用班级
    if req.class_name:
        assets = load_assets("default")
        for a in assets:
            if a.get("id") == asset_id:
                a["class_name"] = req.class_name
                break
        save_assets(assets, "default")

    record = add_borrow_record(asset_id, req.borrower, "default")
    if not record:
        raise HTTPException(status_code=500, detail="借用失败")

    # 将班级信息添加到借用记录
    if req.class_name:
        record["class_name"] = req.class_name

    return {"success": True, "record": record}


@router.post("/return/{asset_id}", summary="归还资产")
async def return_asset_api(asset_id: str):
    asset = get_asset_by_id(asset_id, "default")
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    if asset.get("status") != "借用中":
        raise HTTPException(status_code=400, detail=f"资产当前状态为「{asset.get('status')}」，无需归还")

    ok = return_asset(asset_id, "default")
    if not ok:
        raise HTTPException(status_code=500, detail="归还失败")

    return {"success": True}
