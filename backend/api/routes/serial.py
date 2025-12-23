"""
Serial Connection API Routes
Serial 連線 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import serial.tools.list_ports

from services.core import CoreService

router = APIRouter(prefix="/api/serial", tags=["serial"])


@router.get("/ports")
async def list_ports():
    """
    列出可用的 Serial ports
    """
    ports = []
    for port in serial.tools.list_ports.comports():
        ports.append({
            "device": port.device,
            "description": port.description,
            "hwid": port.hwid
        })
    return {"ports": ports}


@router.post("/connect")
async def connect_serial(
    port: str = Query(..., description="Serial port (e.g., COM8 or /dev/ttyACM0)"),
    baudrate: int = Query(115200, description="Baud rate")
):
    """
    連接 Serial port
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"[API] Connect request: port={port}, baudrate={baudrate}")
        core = CoreService.get_instance()
        await core.start_serial(port, baudrate)
        logger.info(f"[API] Connect successful: port={port}")
        return {"status": "connected", "port": port, "baudrate": baudrate}
    except Exception as e:
        logger.error(f"[API] Connect failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect")
async def disconnect_serial():
    """
    斷開 Serial 連線
    """
    try:
        core = CoreService.get_instance()
        core.stop_serial()
        return {"status": "disconnected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_serial_status():
    """
    取得 Serial 連線狀態
    """
    core = CoreService.get_instance()
    stats = core.get_stats()
    return {
        "connected": stats.get("is_running", False),
        "port": core.serial_ingest.port if core.serial_ingest else None
    }
