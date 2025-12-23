/**
 * Replay Tab - Session playback with controls
 */

import { getSessions, getSession } from '../api.js';
import { onMessage } from '../websocket.js';

let replayChart = null;
let loadedSession = null;
let selectedSessionId = null;
let isPlaying = false;
let isPaused = false;
let unsubscribe = null;

// Data buffers for playback
const WINDOW_SECONDS = 10;
const SAMPLE_RATE = 30;
const MAX_POINTS = WINDOW_SECONDS * SAMPLE_RATE;

let dataBuffer = {
    time: [],
    gx1: [],
    gy1: [],
    gz1: [],
    gx2: [],
    gy2: [],
    gz2: []
};

/**
 * Initialize Replay tab
 * @returns {object} Tab controller
 */
export function initReplayTab() {
    console.log('[Replay] Initializing Replay tab...');

    // Initialize chart
    initChart();

    // Setup controls
    setupControls();

    // Load sessions list
    loadSessionsList();

    // Subscribe to WebSocket messages
    unsubscribe = onMessage(handleMessage);

    return {
        destroy() {
            if (unsubscribe) unsubscribe();
            if (replayChart) {
                replayChart.dispose();
                replayChart = null;
            }
        }
    };
}

/**
 * Initialize ECharts instance
 */
function initChart() {
    const container = document.getElementById('replay-chart');
    if (!container) {
        console.error('[Replay] Chart container not found');
        return;
    }

    replayChart = echarts.init(container, 'dark');

    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross'
            }
        },
        legend: {
            data: ['gx1', 'gy1', 'gz1', 'gx2', 'gy2', 'gz2'],
            textStyle: {
                color: '#f3f4f6'
            }
        },
        xAxis: {
            type: 'time',
            name: 'Time',
            axisLine: {
                lineStyle: { color: '#4b5563' }
            },
            axisLabel: {
                color: '#9ca3af'
            }
        },
        yAxis: {
            type: 'value',
            name: 'Angular Velocity (deg/s)',
            axisLine: {
                lineStyle: { color: '#4b5563' }
            },
            axisLabel: {
                color: '#9ca3af'
            },
            splitLine: {
                lineStyle: { color: '#374151' }
            }
        },
        series: [
            // MPU1: red, green, blue
            {
                name: 'gx1',
                type: 'line',
                data: [],
                symbol: 'none',
                lineStyle: { width: 2, color: '#ef4444' }
            },
            {
                name: 'gy1',
                type: 'line',
                data: [],
                symbol: 'none',
                lineStyle: { width: 2, color: '#22c55e' }
            },
            {
                name: 'gz1',
                type: 'line',
                data: [],
                symbol: 'none',
                lineStyle: { width: 2, color: '#3b82f6' }
            },
            // MPU2: orange, purple, cyan
            {
                name: 'gx2',
                type: 'line',
                data: [],
                symbol: 'none',
                lineStyle: { width: 2, color: '#f97316' }
            },
            {
                name: 'gy2',
                type: 'line',
                data: [],
                symbol: 'none',
                lineStyle: { width: 2, color: '#a855f7' }
            },
            {
                name: 'gz2',
                type: 'line',
                data: [],
                symbol: 'none',
                lineStyle: { width: 2, color: '#06b6d4' }
            }
        ]
    };

    replayChart.setOption(option);

    // Handle resize
    window.addEventListener('resize', () => {
        if (replayChart) replayChart.resize();
    });

    console.log('[Replay] Chart initialized');
}

/**
 * Load sessions list from API
 */
async function loadSessionsList() {
    const select = document.getElementById('session-select');
    if (!select) return;

    try {
        const sessions = await getSessions();
        console.log(`[Replay] Loaded ${sessions.length} sessions`);

        // Clear existing options (except first)
        select.innerHTML = '<option value="">-- 選擇 --</option>';

        // Add sessions
        sessions.forEach(session => {
            const option = document.createElement('option');
            option.value = session.id;
            option.textContent = `${session.name || session.id} (${formatDate(session.created_at)})`;
            select.appendChild(option);
        });

    } catch (error) {
        console.error('[Replay] Failed to load sessions:', error);
    }
}

/**
 * Setup control event listeners
 */
function setupControls() {
    const sessionSelect = document.getElementById('session-select');
    const btnPlay = document.getElementById('btn-play');
    const btnPause = document.getElementById('btn-pause');
    const btnStop = document.getElementById('btn-stop');
    const progressBar = document.getElementById('playback-progress');
    const speedSelect = document.getElementById('playback-speed');

    if (!sessionSelect) {
        console.error('[Replay] Session select not found');
        return;
    }

    // Session change
    sessionSelect.addEventListener('change', async (e) => {
        selectedSessionId = e.target.value;
        if (selectedSessionId) {
            await loadSession(selectedSessionId);
        } else {
            clearSessionInfo();
        }
    });

    // Play button
    if (btnPlay) {
        btnPlay.addEventListener('click', () => {
            if (loadedSession) {
                startPlayback();
            } else {
                alert('請先選擇 Session');
            }
        });
    }

    // Pause button
    if (btnPause) {
        btnPause.addEventListener('click', () => {
            pausePlayback();
        });
    }

    // Stop button
    if (btnStop) {
        btnStop.addEventListener('click', () => {
            stopPlayback();
        });
    }

    // Progress bar (seek)
    if (progressBar) {
        progressBar.addEventListener('input', (e) => {
            // TODO: Implement seek functionality when backend supports it
            console.log('[Replay] Seek to:', e.target.value);
        });
    }

    // Speed change
    if (speedSelect) {
        speedSelect.addEventListener('change', (e) => {
            console.log('[Replay] Speed changed to:', e.target.value);
            // TODO: Update playback speed
        });
    }
}

/**
 * Load session data
 * @param {string} sessionId - Session ID
 */
async function loadSession(sessionId) {
    try {
        console.log(`[Replay] Loading session ${sessionId}...`);

        const session = await getSession(sessionId);
        loadedSession = session;

        // Display session info
        displaySessionInfo(session);

        // Enable controls
        enableControls(true);

        // Note: Actual data loading would happen on playback start
        // For now, we just show session metadata

    } catch (error) {
        console.error('[Replay] Failed to load session:', error);
        alert(`載入 Session 失敗: ${error.message}`);
        clearSessionInfo();
    }
}

/**
 * Display session information
 * @param {object} session - Session data
 */
function displaySessionInfo(session) {
    const container = document.getElementById('session-info');
    if (!container) return;

    const durationSec = Math.floor(session.duration_ms / 1000);
    const minutes = Math.floor(durationSec / 60);
    const seconds = durationSec % 60;

    container.classList.remove('empty');
    container.innerHTML = `
        <p><strong>名稱:</strong> ${session.name || session.id}</p>
        <p><strong>建立時間:</strong> ${formatDateTime(session.created_at)}</p>
        <p><strong>時長:</strong> ${minutes}:${seconds.toString().padStart(2, '0')}</p>
        <p><strong>樣本數:</strong> ${session.sample_count.toLocaleString()}</p>
    `;
}

/**
 * Clear session info display
 */
function clearSessionInfo() {
    const container = document.getElementById('session-info');
    if (!container) return;

    container.classList.add('empty');
    container.innerHTML = '<p>請選擇 Session</p>';
    loadedSession = null;
    enableControls(false);
}

/**
 * Enable/disable playback controls
 * @param {boolean} enabled - Enable state
 */
function enableControls(enabled) {
    const btnPlay = document.getElementById('btn-play');
    const progressBar = document.getElementById('playback-progress');
    const speedSelect = document.getElementById('playback-speed');

    if (btnPlay) btnPlay.disabled = !enabled;
    if (progressBar) progressBar.disabled = !enabled;
    if (speedSelect) speedSelect.disabled = !enabled;
}

/**
 * Handle incoming WebSocket messages
 * @param {object} data - WebSocket message
 */
function handleMessage(data) {
    switch (data.type) {
        case 'playback_sample':
            onPlaybackSample(data.data);
            break;
        case 'playback_status':
            onPlaybackStatus(data.data);
            break;
        default:
            // Ignore other message types
            break;
    }
}

/**
 * Handle playback sample data
 * @param {object} sample - Sample data
 */
function onPlaybackSample(sample) {
    if (!sample) return;

    const timestamp = sample.t_remote_ms / 1000.0;

    // Add to buffer - 6 axis data
    dataBuffer.time.push(timestamp);
    dataBuffer.gx1.push(sample.gx1_dps || 0);
    dataBuffer.gy1.push(sample.gy1_dps || 0);
    dataBuffer.gz1.push(sample.gz1_dps || 0);
    dataBuffer.gx2.push(sample.gx2_dps || 0);
    dataBuffer.gy2.push(sample.gy2_dps || 0);
    dataBuffer.gz2.push(sample.gz2_dps || 0);

    // Trim to window size
    if (dataBuffer.time.length > MAX_POINTS) {
        dataBuffer.time = dataBuffer.time.slice(-MAX_POINTS);
        dataBuffer.gx1 = dataBuffer.gx1.slice(-MAX_POINTS);
        dataBuffer.gy1 = dataBuffer.gy1.slice(-MAX_POINTS);
        dataBuffer.gz1 = dataBuffer.gz1.slice(-MAX_POINTS);
        dataBuffer.gx2 = dataBuffer.gx2.slice(-MAX_POINTS);
        dataBuffer.gy2 = dataBuffer.gy2.slice(-MAX_POINTS);
        dataBuffer.gz2 = dataBuffer.gz2.slice(-MAX_POINTS);
    }

    // Update chart
    updateChart();
}

/**
 * Handle playback status update
 * @param {object} status - Status data
 */
function onPlaybackStatus(status) {
    isPlaying = status.is_playing;
    isPaused = status.is_paused;

    // Update progress bar
    const progressBar = document.getElementById('playback-progress');
    const timeDisplay = document.getElementById('playback-time');

    if (progressBar && status.total_duration_ms > 0) {
        progressBar.max = status.total_duration_ms;
        progressBar.value = status.current_time_ms;
    }

    if (timeDisplay) {
        const current = formatTime(status.current_time_ms);
        const total = formatTime(status.total_duration_ms);
        timeDisplay.textContent = `${current} / ${total}`;
    }

    // Update button states
    updateButtonStates();

    // If playback stopped, clear chart
    if (!status.is_playing && !status.is_paused) {
        // Playback ended
        console.log('[Replay] Playback ended');
    }
}

/**
 * Update button states based on playback status
 */
function updateButtonStates() {
    const btnPlay = document.getElementById('btn-play');
    const btnPause = document.getElementById('btn-pause');
    const btnStop = document.getElementById('btn-stop');

    if (isPlaying) {
        if (btnPlay) btnPlay.disabled = true;
        if (btnPause) btnPause.disabled = false;
        if (btnStop) btnStop.disabled = false;
    } else if (isPaused) {
        if (btnPlay) btnPlay.disabled = false;
        if (btnPause) btnPause.disabled = true;
        if (btnStop) btnStop.disabled = false;
    } else {
        if (btnPlay) btnPlay.disabled = !loadedSession;
        if (btnPause) btnPause.disabled = true;
        if (btnStop) btnStop.disabled = true;
    }
}

/**
 * Update chart with current buffer data
 */
function updateChart() {
    if (!replayChart) return;

    // Convert to ECharts format: [[timestamp, value], ...]
    const gx1Data = dataBuffer.time.map((t, i) => [t * 1000, dataBuffer.gx1[i]]);
    const gy1Data = dataBuffer.time.map((t, i) => [t * 1000, dataBuffer.gy1[i]]);
    const gz1Data = dataBuffer.time.map((t, i) => [t * 1000, dataBuffer.gz1[i]]);
    const gx2Data = dataBuffer.time.map((t, i) => [t * 1000, dataBuffer.gx2[i]]);
    const gy2Data = dataBuffer.time.map((t, i) => [t * 1000, dataBuffer.gy2[i]]);
    const gz2Data = dataBuffer.time.map((t, i) => [t * 1000, dataBuffer.gz2[i]]);

    replayChart.setOption({
        series: [
            { data: gx1Data },
            { data: gy1Data },
            { data: gz1Data },
            { data: gx2Data },
            { data: gy2Data },
            { data: gz2Data }
        ]
    });
}

/**
 * Format milliseconds to mm:ss
 * @param {number} ms - Milliseconds
 * @returns {string} Formatted time
 */
function formatTime(ms) {
    const totalSec = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSec / 60);
    const seconds = totalSec % 60;
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

/**
 * Start playback
 */
async function startPlayback() {
    console.log('[Replay] Starting playback...');

    if (!selectedSessionId) {
        alert('請先選擇 Session');
        return;
    }

    // Clear data buffer
    dataBuffer = { time: [], gx1: [], gy1: [], gz1: [], gx2: [], gy2: [], gz2: [] };

    // Get speed
    const speedSelect = document.getElementById('playback-speed');
    const speed = speedSelect ? parseFloat(speedSelect.value) : 1.0;

    try {
        const response = await fetch(`/api/playback/play/${selectedSessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ speed })
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        console.log('[Replay] Playback started');
        isPlaying = true;
        updateButtonStates();

    } catch (error) {
        console.error('[Replay] Failed to start playback:', error);
        alert(`無法開始回放: ${error.message}`);
    }
}

/**
 * Pause playback
 */
async function pausePlayback() {
    console.log('[Replay] Pausing playback...');

    try {
        const response = await fetch('/api/playback/pause', { method: 'POST' });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        isPaused = true;
        isPlaying = false;
        updateButtonStates();

    } catch (error) {
        console.error('[Replay] Failed to pause:', error);
    }
}

/**
 * Stop playback
 */
async function stopPlayback() {
    console.log('[Replay] Stopping playback...');

    try {
        const response = await fetch('/api/playback/stop', { method: 'POST' });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        isPlaying = false;
        isPaused = false;

        // Reset UI
        const progressBar = document.getElementById('playback-progress');
        const timeDisplay = document.getElementById('playback-time');

        if (progressBar) progressBar.value = 0;
        if (timeDisplay) timeDisplay.textContent = '00:00 / 00:00';

        updateButtonStates();

        // Clear chart and buffer
        dataBuffer = { time: [], gx1: [], gy1: [], gz1: [], gx2: [], gy2: [], gz2: [] };
        if (replayChart) {
            replayChart.setOption({
                series: [
                    { data: [] },
                    { data: [] },
                    { data: [] },
                    { data: [] },
                    { data: [] },
                    { data: [] }
                ]
            });
        }

    } catch (error) {
        console.error('[Replay] Failed to stop:', error);
    }
}

/**
 * Format date string
 * @param {string} dateStr - ISO date string
 * @returns {string} Formatted date
 */
function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-TW');
}

/**
 * Format datetime string
 * @param {string} dateStr - ISO date string
 * @returns {string} Formatted datetime
 */
function formatDateTime(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleString('zh-TW');
}
