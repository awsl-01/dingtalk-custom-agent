"""
资产数据存储模块 - 封装资产数据的读写操作

支持功能：
- JSON 格式存储
- 按 corp_id 隔离数据
- 自动创建目录和文件
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

# 资产数据目录
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'knowledge', 'assets')


def ensure_assets_dir():
    """确保资产数据目录存在"""
    os.makedirs(ASSETS_DIR, exist_ok=True)


def get_assets_file(corp_id: str = "default") -> str:
    """获取资产数据文件路径"""
    ensure_assets_dir()
    return os.path.join(ASSETS_DIR, f"{corp_id}_assets.json")


def load_assets(corp_id: str = "default") -> List[Dict]:
    """加载资产数据"""
    filepath = get_assets_file(corp_id)
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"加载资产数据失败: {e}")
            return []
    return []


def save_assets(assets: List[Dict], corp_id: str = "default"):
    """保存资产数据"""
    filepath = get_assets_file(corp_id)
    ensure_assets_dir()
    print(f"保存数据到: {filepath}")
    print(f"数据内容: {assets}")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(assets, f, ensure_ascii=False, indent=2)
    print("保存完成")


def generate_asset_id(corp_id: str = "default") -> str:
    """生成资产编号"""
    today = datetime.now().strftime("%Y%m%d")
    assets = load_assets(corp_id)
    # 统计今天创建的资产数量
    today_count = sum(1 for a in assets if a.get('id', '').startswith(f"AST{today}"))
    return f"AST{today}{today_count + 1:03d}"


def get_asset_by_id(asset_id: str, corp_id: str = "default") -> Optional[Dict]:
    """根据ID获取资产"""
    assets = load_assets(corp_id)
    for asset in assets:
        if asset.get('id') == asset_id:
            return asset
    return None


def get_assets_by_name(name: str, corp_id: str = "default") -> List[Dict]:
    """根据名称查询资产"""
    assets = load_assets(corp_id)
    return [a for a in assets if name in a.get('name', '')]


def get_asset_stats(corp_id: str = "default") -> Dict:
    """获取资产统计数据"""
    assets = load_assets(corp_id)

    if not assets:
        return {
            "total": 0,
            "status_count": {},
            "category_count": {},
            "location_count": {}
        }

    status_count = {}
    category_count = {}
    location_count = {}

    for asset in assets:
        # 状态统计
        status = asset.get('status', '未知')
        status_count[status] = status_count.get(status, 0) + 1

        # 分类统计
        category = asset.get('category', '其他')
        category_count[category] = category_count.get(category, 0) + 1

        # 位置统计
        location = asset.get('location', '未指定')
        location_count[location] = location_count.get(location, 0) + 1

    return {
        "total": len(assets),
        "status_count": status_count,
        "category_count": category_count,
        "location_count": location_count
    }


def create_asset(asset_data: Dict, corp_id: str = "default") -> Dict:
    """创建新资产"""
    assets = load_assets(corp_id)

    # 生成资产编号
    asset_id = generate_asset_id(corp_id)

    # 创建资产记录
    new_asset = {
        "id": asset_id,
        "name": asset_data.get("name", ""),
        "category": asset_data.get("category", "其他"),
        "location": asset_data.get("location", "未指定"),
        "status": "在用",
        "purchase_date": asset_data.get("purchase_date", datetime.now().strftime("%Y-%m-%d")),
        "responsible_user": asset_data.get("responsible_user", "未指定"),
        "description": asset_data.get("description", ""),
        "class_name": asset_data.get("class_name", ""),
        "borrow_records": [],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    assets.append(new_asset)
    save_assets(assets, corp_id)

    return new_asset


def update_asset_status(asset_id: str, new_status: str, corp_id: str = "default") -> bool:
    """更新资产状态"""
    assets = load_assets(corp_id)

    for asset in assets:
        if asset.get('id') == asset_id:
            asset['status'] = new_status
            asset['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_assets(assets, corp_id)
            return True

    return False


def add_borrow_record(asset_id: str, borrower: str, corp_id: str = "default") -> Optional[Dict]:
    """添加借用记录"""
    assets = load_assets(corp_id)

    for asset in assets:
        if asset.get('id') == asset_id:
            # 更新资产状态
            asset['status'] = '借用中'

            # 添加借用记录
            borrow_record = {
                "borrower": borrower,
                "borrow_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "return_date": None
            }
            asset['borrow_records'].append(borrow_record)
            asset['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            save_assets(assets, corp_id)
            return borrow_record

    return None


def return_asset(asset_id: str, corp_id: str = "default") -> bool:
    """归还资产"""
    assets = load_assets(corp_id)

    for asset in assets:
        if asset.get('id') == asset_id:
            if asset.get('status') != '借用中':
                return False

            # 更新最近一条借用记录
            if asset.get('borrow_records'):
                last_record = asset['borrow_records'][-1]
                if last_record.get('return_date') is None:
                    last_record['return_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 更新资产状态
            asset['status'] = '在用'
            asset['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            save_assets(assets, corp_id)
            return True

    return False


def delete_asset(asset_id: str, corp_id: str = "default") -> bool:
    """删除资产"""
    assets = load_assets(corp_id)
    original_count = len(assets)

    assets = [a for a in assets if a.get('id') != asset_id]

    if len(assets) < original_count:
        save_assets(assets, corp_id)
        return True

    return False


def search_assets(keyword: str, corp_id: str = "default") -> List[Dict]:
    """搜索资产（支持名称、分类、位置）"""
    assets = load_assets(corp_id)
    results = []

    for asset in assets:
        if (keyword in asset.get('name', '') or
            keyword in asset.get('category', '') or
            keyword in asset.get('location', '') or
            keyword in asset.get('id', '')):
            results.append(asset)

    return results
