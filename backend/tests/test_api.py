"""
Test API Endpoints
測試 API 端點
"""
import pytest


def test_health_check(client):
    """
    測試健康檢查端點
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_root_endpoint(client):
    """
    測試根端點
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs" in data


def test_sessions_list(client):
    """
    測試 Sessions 列表端點
    """
    response = client.get("/api/sessions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_recording_status(client):
    """
    測試錄製狀態端點
    """
    response = client.get("/api/recording/status")
    assert response.status_code == 200
    data = response.json()
    assert "is_recording" in data


def test_playback_status(client):
    """
    測試播放狀態端點
    """
    response = client.get("/api/playback/status")
    assert response.status_code == 200
    data = response.json()
    assert "is_playing" in data


def test_segments_list(client):
    """
    測試 Segments 列表端點
    """
    response = client.get("/api/segments")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_stats_endpoint(client):
    """
    測試統計資訊端點
    """
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "serial" in data or "buffer_size" in data
