/**
 * Replay Tab - Session playback with controls
 */

import { getSessions, getSession } from '../api.js';

let replayChart = null;
let loadedSession = null;
let selectedSessionId = null;

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

    return {
        destroy() {
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
            data: ['Gyro1', 'Gyro2', 'Delta'],
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
            {
                name: 'Gyro1',
                type: 'line',
                data: [],
                symbol: 'none',
                lineStyle: { width: 2, color: '#2563eb' }
            },
            {
                name: 'Gyro2',
                type: 'line',
                data: [],
                symbol: 'none',
                lineStyle: { width: 2, color: '#10b981' }
            },
            {
                name: 'Delta',
                type: 'line',
                data: [],
                symbol: 'none',
                lineStyle: { width: 1, color: '#f59e0b' }
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
 * Start playback
 */
function startPlayback() {
    console.log('[Replay] Starting playback...');

    const btnPlay = document.getElementById('btn-play');
    const btnPause = document.getElementById('btn-pause');
    const btnStop = document.getElementById('btn-stop');

    if (btnPlay) btnPlay.disabled = true;
    if (btnPause) btnPause.disabled = false;
    if (btnStop) btnStop.disabled = false;

    // TODO: Implement actual playback via WebSocket
    // For now, just show a message
    alert('回放功能需要後端 WebSocket 支援（開發中）');
}

/**
 * Pause playback
 */
function pausePlayback() {
    console.log('[Replay] Pausing playback...');

    const btnPlay = document.getElementById('btn-play');
    const btnPause = document.getElementById('btn-pause');

    if (btnPlay) btnPlay.disabled = false;
    if (btnPause) btnPause.disabled = true;

    // TODO: Implement pause
}

/**
 * Stop playback
 */
function stopPlayback() {
    console.log('[Replay] Stopping playback...');

    const btnPlay = document.getElementById('btn-play');
    const btnPause = document.getElementById('btn-pause');
    const btnStop = document.getElementById('btn-stop');
    const progressBar = document.getElementById('playback-progress');
    const timeDisplay = document.getElementById('playback-time');

    if (btnPlay) btnPlay.disabled = false;
    if (btnPause) btnPause.disabled = true;
    if (btnStop) btnStop.disabled = true;
    if (progressBar) progressBar.value = 0;
    if (timeDisplay) timeDisplay.textContent = '00:00 / 00:00';

    // Clear chart
    if (replayChart) {
        replayChart.setOption({
            series: [
                { data: [] },
                { data: [] },
                { data: [] }
            ]
        });
    }

    // TODO: Implement stop
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
