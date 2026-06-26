"""
钉钉机器人 Web 管理后台 - FastAPI 应用入口
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn

from web.config import WEB_HOST, WEB_PORT
from web.routers import dashboard, knowledge, messages, debug, organizations, users, scheduling, auth, inspection, assets

class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # 对 JS/CSS 资源文件禁用缓存
        path = request.url.path
        if path.startswith("/assets/") or path.endswith(".js") or path.endswith(".css"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


app = FastAPI(
    title="钉钉机器人管理后台",
    description="学校智能助手 Web 管理界面",
    version="1.0.0"
)

# 添加缓存控制中间件
app.add_middleware(NoCacheMiddleware)

# CORS 配置（允许前端开发服务器访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["仪表盘"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["知识库"])
app.include_router(messages.router, prefix="/api/messages", tags=["消息日志"])
app.include_router(debug.router, prefix="/api/debug", tags=["对话调试"])
app.include_router(organizations.router, prefix="/api/organizations", tags=["组织管理"])
app.include_router(users.router, prefix="/api/users", tags=["用户管理"])
app.include_router(scheduling.router, prefix="/api/scheduling", tags=["排课系统"])
app.include_router(inspection.router, prefix="/api/inspection", tags=["巡检管理"])
app.include_router(inspection.page_router, tags=["巡检页面"])
app.include_router(assets.router, prefix="/api/assets", tags=["资产管理"])

# 静态文件服务
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    # 挂载 assets 目录到根路径（前端构建的资源文件）
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    # 挂载整个 static 目录
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", tags=["根路径"])
async def index():
    """返回前端页面"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "钉钉机器人管理后台 API", "docs": "/docs"}


@app.get("/{path:path}", include_in_schema=False)
async def catch_all(path: str):
    """处理前端路由（Vue Router History 模式）"""
    # 先检查是否是静态文件
    file_path = os.path.join(static_dir, path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    # 返回 index.html（Vue Router 会处理路由）
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"detail": "Not Found"}


@app.get("/api", tags=["API信息"])
async def api_info():
    """API 信息"""
    return {
        "name": "钉钉机器人管理后台",
        "version": "1.0.0",
        "endpoints": {
            "dashboard": "/api/dashboard",
            "knowledge": "/api/knowledge",
            "messages": "/api/messages",
            "debug": "/api/debug",
            "docs": "/docs"
        }
    }


def start_web_server(host: str = WEB_HOST, port: int = WEB_PORT):
    """启动 Web 服务器"""
    uvicorn.run(
        "web.app:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    start_web_server()
