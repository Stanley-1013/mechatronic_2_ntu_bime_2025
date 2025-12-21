"""
FastAPI Application Entry Point
主應用程式入口
"""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from config import CORS_ORIGINS, API_PREFIX, API_VERSION

# 前端檔案路徑
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# 匯入 routers
from api.routes import (
    sessions_router,
    recording_router,
    playback_router,
    segments_router,
    stats_router,
    serial_router
)
from api.websocket import websocket_endpoint

# 建立 FastAPI 應用
app = FastAPI(
    title="Mechtronic 2 Backend",
    description="IMU 資料收集與處理 API",
    version=API_VERSION,
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    openapi_url=f"{API_PREFIX}/openapi.json",
)

# CORS 設定（允許本地開發）
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(sessions_router)
app.include_router(recording_router)
app.include_router(playback_router)
app.include_router(segments_router)
app.include_router(stats_router)
app.include_router(serial_router)

# 註冊 WebSocket 端點
app.websocket("/ws")(websocket_endpoint)


# 基本健康檢查端點
@app.get("/health")
async def health_check():
    """
    健康檢查端點
    """
    return {
        "status": "ok",
        "service": "mechtronic-2-backend",
        "version": API_VERSION
    }


# 掛載靜態檔案 (CSS, JS)
if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
    app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")


@app.get("/")
async def root():
    """
    根端點 - 返回前端 HTML
    """
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {
        "message": "Mechtronic 2 Backend API",
        "docs": f"{API_PREFIX}/docs",
        "version": API_VERSION
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
