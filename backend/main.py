"""
FastAPI Application Entry Point
主應用程式入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import CORS_ORIGINS, API_PREFIX, API_VERSION

# 匯入 routers
from api.routes import (
    sessions_router,
    recording_router,
    playback_router,
    segments_router,
    stats_router
)

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


@app.get("/")
async def root():
    """
    根端點
    """
    return {
        "message": "Mechtronic 2 Backend API",
        "docs": f"{API_PREFIX}/docs",
        "version": API_VERSION
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
