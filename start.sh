#!/bin/bash
# Mechtronic 2 Backend 啟動腳本

set -e

# 切換到 backend 目錄
cd "$(dirname "$0")/backend"

# 檢查 Python 版本
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_MAJOR=3
REQUIRED_MINOR=9

MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$MAJOR" -lt "$REQUIRED_MAJOR" ] || ([ "$MAJOR" -eq "$REQUIRED_MAJOR" ] && [ "$MINOR" -lt "$REQUIRED_MINOR" ]); then
    echo "錯誤: 需要 Python ${REQUIRED_MAJOR}.${REQUIRED_MINOR} 或更高版本（目前: $PYTHON_VERSION）"
    exit 1
fi

echo "Python 版本: $PYTHON_VERSION ✓"

# 檢查依賴是否已安裝
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "錯誤: 依賴未安裝。請先執行："
    echo "  cd backend && pip install -r requirements.txt"
    exit 1
fi

# 啟動 FastAPI 伺服器
echo "啟動 Mechtronic 2 Backend..."
echo "API 文檔: http://localhost:8000/api/docs"
echo "健康檢查: http://localhost:8000/health"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000
