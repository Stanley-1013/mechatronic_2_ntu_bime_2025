/**
 * Live Tab - Real-time sensor data visualization
 */

import { onMessage, sendMessage } from '../websocket.js';
import { createMultiSeriesChart } from '../components/chart.js';

let chart = null;
let unsubscribe = null;
let isActive = true;
let isRecording = false;
let recordingName = '';
let recordingStartTime = null;

// Data buffers
const WINDOW_SECONDS = 10; // Display last 10 seconds
const SAMPLE_RATE = 30; // 30 Hz
const MAX_POINTS = WINDOW_SECONDS * SAMPLE_RATE;

let dataBuffer = {
    time: [],
    g1: [],
    g2: [],
    dg: []
};

// Statistics
let stats = {
    pps: 0,
    dropped: 0,
    buffer: 0
};

let segments = [];

/**
 * Initialize Live tab
 * @returns {object} Tab controller
 */
export function initLiveTab() {
    console.log('[Live] Initializing Live tab...');

    // Initialize chart
    initChart();

    // Initialize controls
    initControls();

    // Subscribe to WebSocket messages
    unsubscribe = onMessage(handleMessage);

    return {
        isActive,

        activate() {
            isActive = true;
            console.log('[Live] Tab activated');
        },

        deactivate() {
            isActive = false;
            console.log('[Live] Tab deactivated');
        },

        destroy() {
            if (unsubscribe) unsubscribe();
            if (chart) chart.destroy();
        }
    };
}

/**
 * Initialize time-series chart
 */
function initChart() {
    const chartContainer = document.getElementById('live-chart');

    if (!chartContainer) {
        console.error('[Live] Chart container not found');
        return;
    }

    // Create chart with three series: |g1|, |g2|, Δ|g|
    chart = createMultiSeriesChart(
        chartContainer,
        ['|g1|', '|g2|', 'Δ|g|'],
        ['#2563eb', '#10b981', '#f59e0b'] // blue, green, orange
    );

    console.log('[Live] Chart initialized');
}

/**
 * Initialize recording controls
 */
function initControls() {
    const btnStart = document.getElementById('btn-record-start');
    const btnStop = document.getElementById('btn-record-stop');
    const inputName = document.getElementById('record-name');

    if (!btnStart || !btnStop || !inputName) {
        console.error('[Live] Control elements not found');
        return;
    }

    btnStart.addEventListener('click', async () => {
        const name = inputName.value.trim() || `session_${Date.now()}`;
        await startRecording(name);
    });

    btnStop.addEventListener('click', async () => {
        await stopRecording();
    });

    console.log('[Live] Controls initialized');
}

/**
 * Handle incoming WebSocket messages
 * @param {object} data - WebSocket message
 */
function handleMessage(data) {
    if (!isActive) return;

    switch (data.type) {
        case 'sample':
            onSample(data);
            break;
        case 'segment_start':
            onSegmentStart(data);
            break;
        case 'segment_end':
            onSegmentEnd(data);
            break;
        case 'stats':
            onStats(data);
            break;
        case 'recording_started':
            onRecordingStarted(data);
            break;
        case 'recording_stopped':
            onRecordingStopped(data);
            break;
        default:
            // Ignore unknown message types
            break;
    }
}

/**
 * Handle sensor sample data
 * @param {object} data - Sample data
 */
function onSample(data) {
    // Expected format:
    // {
    //   type: 'sample',
    //   timestamp: 1234567890.123,
    //   g1: [x, y, z],
    //   g2: [x, y, z]
    // }

    const { timestamp, g1, g2 } = data;

    if (!timestamp || !g1 || !g2) {
        console.warn('[Live] Invalid sample data:', data);
        return;
    }

    // Calculate magnitudes
    const g1_mag = Math.sqrt(g1[0]**2 + g1[1]**2 + g1[2]**2);
    const g2_mag = Math.sqrt(g2[0]**2 + g2[1]**2 + g2[2]**2);
    const dg_mag = Math.abs(g1_mag - g2_mag);

    // Add to buffer
    dataBuffer.time.push(timestamp);
    dataBuffer.g1.push(g1_mag);
    dataBuffer.g2.push(g2_mag);
    dataBuffer.dg.push(dg_mag);

    // Trim to window size
    if (dataBuffer.time.length > MAX_POINTS) {
        dataBuffer.time = dataBuffer.time.slice(-MAX_POINTS);
        dataBuffer.g1 = dataBuffer.g1.slice(-MAX_POINTS);
        dataBuffer.g2 = dataBuffer.g2.slice(-MAX_POINTS);
        dataBuffer.dg = dataBuffer.dg.slice(-MAX_POINTS);
    }

    // Update chart
    if (chart) {
        chart.setData([
            dataBuffer.time,
            dataBuffer.g1,
            dataBuffer.g2,
            dataBuffer.dg
        ]);
    }

    // Update buffer stat
    stats.buffer = dataBuffer.time.length;
    updateStatsDisplay();
}

/**
 * Handle segment start event
 * @param {object} data - Segment data
 */
function onSegmentStart(data) {
    // Expected format:
    // {
    //   type: 'segment_start',
    //   segment_id: 'seg_123',
    //   timestamp: 1234567890.123
    // }

    console.log('[Live] Segment started:', data);

    const segment = {
        id: data.segment_id,
        startTime: data.timestamp,
        endTime: null,
        label: null
    };

    segments.push(segment);
    updateSegmentsList();
}

/**
 * Handle segment end event
 * @param {object} data - Segment data
 */
function onSegmentEnd(data) {
    // Expected format:
    // {
    //   type: 'segment_end',
    //   segment_id: 'seg_123',
    //   timestamp: 1234567890.123,
    //   label: 'good' | 'bad' | null
    // }

    console.log('[Live] Segment ended:', data);

    const segment = segments.find(s => s.id === data.segment_id);
    if (segment) {
        segment.endTime = data.timestamp;
        segment.label = data.label || null;
        updateSegmentsList();
    }
}

/**
 * Handle statistics update
 * @param {object} data - Stats data
 */
function onStats(data) {
    // Expected format:
    // {
    //   type: 'stats',
    //   pps: 30,
    //   dropped: 0
    // }

    if (data.pps !== undefined) stats.pps = data.pps;
    if (data.dropped !== undefined) stats.dropped = data.dropped;

    updateStatsDisplay();
}

/**
 * Handle recording started confirmation
 * @param {object} data - Recording data
 */
function onRecordingStarted(data) {
    console.log('[Live] Recording started:', data);
    isRecording = true;
    recordingName = data.session_name;
    recordingStartTime = Date.now();

    updateRecordingUI();
    startRecordingTimer();
}

/**
 * Handle recording stopped confirmation
 * @param {object} data - Recording data
 */
function onRecordingStopped(data) {
    console.log('[Live] Recording stopped:', data);
    isRecording = false;
    recordingStartTime = null;

    updateRecordingUI();
}

/**
 * Start recording
 * @param {string} name - Session name
 */
async function startRecording(name) {
    try {
        const response = await fetch('/api/recording/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ session_name: name })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('[Live] Recording start response:', result);

        // Backend will send 'recording_started' WebSocket message
    } catch (error) {
        console.error('[Live] Failed to start recording:', error);
        alert(`錄製啟動失敗: ${error.message}`);
    }
}

/**
 * Stop recording
 */
async function stopRecording() {
    try {
        const response = await fetch('/api/recording/stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('[Live] Recording stop response:', result);

        // Backend will send 'recording_stopped' WebSocket message
    } catch (error) {
        console.error('[Live] Failed to stop recording:', error);
        alert(`錄製停止失敗: ${error.message}`);
    }
}

/**
 * Update statistics display
 */
function updateStatsDisplay() {
    const ppsEl = document.getElementById('live-pps');
    const droppedEl = document.getElementById('live-dropped');
    const bufferEl = document.getElementById('live-buffer');

    if (ppsEl) ppsEl.textContent = stats.pps;
    if (droppedEl) droppedEl.textContent = stats.dropped;
    if (bufferEl) bufferEl.textContent = stats.buffer;
}

/**
 * Update segments list display
 */
function updateSegmentsList() {
    const listEl = document.getElementById('live-segments-list');
    if (!listEl) return;

    if (segments.length === 0) {
        listEl.innerHTML = '<p class="empty-message">尚未偵測到投籃</p>';
        return;
    }

    // Show most recent segments first
    const html = segments.slice().reverse().map(seg => {
        const duration = seg.endTime
            ? ((seg.endTime - seg.startTime) * 1000).toFixed(0)
            : '進行中';

        const labelClass = seg.label === 'good' ? 'label-good' :
                          seg.label === 'bad' ? 'label-bad' : '';

        const labelText = seg.label === 'good' ? '好球' :
                         seg.label === 'bad' ? '壞球' : '未標記';

        return `
            <div class="segment-item">
                <div class="segment-time">
                    ${new Date(seg.startTime * 1000).toLocaleTimeString()}
                </div>
                <div class="segment-duration">
                    時長: ${duration}ms
                </div>
                <div class="segment-label ${labelClass}">
                    ${labelText}
                </div>
            </div>
        `;
    }).join('');

    listEl.innerHTML = html;
}

/**
 * Update recording UI state
 */
function updateRecordingUI() {
    const btnStart = document.getElementById('btn-record-start');
    const btnStop = document.getElementById('btn-record-stop');
    const statusEl = document.getElementById('record-status');
    const inputName = document.getElementById('record-name');

    if (!btnStart || !btnStop || !statusEl || !inputName) return;

    if (isRecording) {
        btnStart.disabled = true;
        btnStop.disabled = false;
        inputName.disabled = true;
        statusEl.innerHTML = `
            <div class="recording-active">
                <span class="recording-dot"></span>
                錄製中: ${recordingName}
                <span id="recording-timer">00:00</span>
            </div>
        `;
    } else {
        btnStart.disabled = false;
        btnStop.disabled = true;
        inputName.disabled = false;
        statusEl.innerHTML = '';
    }
}

/**
 * Start recording timer
 */
function startRecordingTimer() {
    if (!isRecording) return;

    const timerEl = document.getElementById('recording-timer');
    if (!timerEl) return;

    const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
    const seconds = (elapsed % 60).toString().padStart(2, '0');
    timerEl.textContent = `${minutes}:${seconds}`;

    setTimeout(startRecordingTimer, 1000);
}
