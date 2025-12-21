"""
API Routes Package
"""

# 匯出所有 router
from .sessions import router as sessions_router
from .recording import router as recording_router
from .playback import router as playback_router
from .segments import router as segments_router
from .stats import router as stats_router
from .serial import router as serial_router

__all__ = [
    "sessions_router",
    "recording_router",
    "playback_router",
    "segments_router",
    "stats_router",
    "serial_router",
]
