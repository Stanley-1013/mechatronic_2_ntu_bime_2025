/**
 * Live Tab - Real-time sensor data visualization
 */

import { onMessage } from '../websocket.js';
import { createMultiSeriesChart } from '../components/chart.js';

let chart = null;
let unsubscribe = null;
let isActive = true;
let isRecording = false;
let recordingName = '';
let recordingStartTime = null;
let recordingTimerInterval = null;
let recordingSampleCount = 0;

// Data buffers
const WINDOW_SECONDS = 10; // Display last 10 seconds
const SAMPLE_RATE = 30; // 30 Hz
const MAX_POINTS = WINDOW_SECONDS * SAMPLE_RATE;

let dataBuffer = {
    time: [],
    // MPU1 三軸角速度 (deg/s)
    gx1: [],
    gy1: [],
    gz1: [],
    // MPU2 三軸角速度 (deg/s)
    gx2: [],
    gy2: [],
    gz2: []
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
            stopRecordingTimer();
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

    // Create chart with 6 series: MPU1 (gx1, gy1, gz1) + MPU2 (gx2, gy2, gz2)
    chart = createMultiSeriesChart(
        chartContainer,
        ['gx1', 'gy1', 'gz1', 'gx2', 'gy2', 'gz2'],
        [
            '#ef4444', '#22c55e', '#3b82f6',  // MPU1: red, green, blue
            '#f97316', '#a855f7', '#06b6d4'   // MPU2: orange, purple, cyan
        ]
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
        case 'segment':
            // Backend sends: { type: 'segment', event: 'start'/'end', data: {...} }
            if (data.event === 'start') {
                onSegmentStart(data);
            } else if (data.event === 'end') {
                onSegmentEnd(data);
            }
            break;
        case 'stats':
        case 'stat':
            onStats(data);
            break;
        case 'label':
            // Label event from backend - show feedback
            onLabelEvent(data);
            break;
        case 'recording_status':
            // Recording status update from backend
            onRecordingStatus(data);
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
    // Backend format:
    // {
    //   type: 'sample',
    //   data: {
    //     seq, t_remote_ms, btn,
    //     g1_mag, g2_mag, a1_mag, a2_mag,
    //     gx1_dps, gy1_dps, gz1_dps, gx2_dps, gy2_dps, gz2_dps
    //   }
    // }

    const sample = data.data;
    if (!sample) {
        console.warn('[Live] Invalid sample data:', data);
        return;
    }

    const timestamp = sample.t_remote_ms / 1000.0; // Convert ms to seconds

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
    if (chart) {
        chart.setData([
            dataBuffer.time,
            dataBuffer.gx1,
            dataBuffer.gy1,
            dataBuffer.gz1,
            dataBuffer.gx2,
            dataBuffer.gy2,
            dataBuffer.gz2
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
    // Backend format:
    // {
    //   type: 'segment',
    //   event: 'start',
    //   data: { shot_id, t_start_ms, ... }
    // }

    console.log('[Live] Segment started:', data);

    const segData = data.data || {};
    const segment = {
        id: segData.shot_id,
        startTime: segData.t_start_ms / 1000.0,  // Convert ms to seconds
        endTime: null,
        label: null
    };

    segments.push(segment);

    // Limit segments array size to prevent memory leak
    if (segments.length > 100) {
        segments.shift();
    }

    updateSegmentsList();
}

/**
 * Handle segment end event
 * @param {object} data - Segment data
 */
function onSegmentEnd(data) {
    // Backend format:
    // {
    //   type: 'segment',
    //   event: 'end',
    //   data: { shot_id, t_start_ms, t_end_ms, duration_ms, features, label }
    // }

    console.log('[Live] Segment ended:', data);

    const segData = data.data || {};
    const segment = segments.find(s => s.id === segData.shot_id);
    if (segment) {
        segment.endTime = segData.t_end_ms / 1000.0;  // Convert ms to seconds
        segment.duration_ms = segData.duration_ms;
        segment.label = segData.label || null;
        segment.features = segData.features || {};
        updateSegmentsList();
    } else {
        // Segment not found (maybe started before page load), create new entry
        segments.push({
            id: segData.shot_id,
            startTime: segData.t_start_ms / 1000.0,
            endTime: segData.t_end_ms / 1000.0,
            duration_ms: segData.duration_ms,
            label: segData.label || null,
            features: segData.features || {}
        });
        updateSegmentsList();
    }
}

/**
 * Handle label event (button press marking a shot as "good")
 * @param {object} data - Label data
 */
function onLabelEvent(data) {
    // Backend format:
    // {
    //   type: 'label',
    //   data: { shot_id, label, t_label_ms }
    // }

    console.log('[Live] Label event:', data);

    const labelData = data.data || {};
    const shotId = labelData.shot_id;
    const label = labelData.label;

    if (shotId) {
        // Update segment in local list
        const segment = segments.find(s => s.id === shotId);
        if (segment) {
            segment.label = label;
            updateSegmentsList();
        }

        // Show feedback toast
        showLabelFeedback(shotId, label);
    } else {
        // Button was pressed but no matching segment found
        showLabelFeedback(null, 'no_match');
    }
}

/**
 * Show visual feedback for label event
 * @param {string|null} shotId - Shot ID that was labeled
 * @param {string} label - Label type ('good', 'no_match')
 */
function showLabelFeedback(shotId, label) {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'label-feedback';

    if (shotId && label === 'good') {
        toast.classList.add('success');
        toast.textContent = `Good shot marked! (${shotId.substring(0, 8)}...)`;
    } else if (label === 'no_match') {
        toast.classList.add('warning');
        toast.textContent = 'Button pressed - no recent shot to mark';
    } else {
        toast.classList.add('success');
        toast.textContent = `Shot marked as ${label}`;
    }

    document.body.appendChild(toast);

    // Remove after animation
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

/**
 * Handle recording status update from WebSocket
 * @param {object} data - Recording status data
 */
function onRecordingStatus(data) {
    // Backend format:
    // {
    //   type: 'recording_status',
    //   data: { is_recording, session_name, sample_count }
    // }

    const statusData = data.data || {};

    if (statusData.is_recording) {
        recordingSampleCount = statusData.sample_count || 0;

        // Update UI if we're currently recording
        if (isRecording) {
            updateRecordingUI();
        }
    }
}

/**
 * Handle statistics update
 * @param {object} data - Stats data
 */
function onStats(data) {
    // Backend format:
    // {
    //   type: 'stat',
    //   data: {
    //     pps: 30,
    //     dropped: 0,
    //     ...
    //   }
    // }

    const statData = data.data || data;
    if (statData.pps !== undefined) stats.pps = statData.pps;
    if (statData.dropped !== undefined) stats.dropped = statData.dropped;

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
    recordingSampleCount = 0;

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
    recordingSampleCount = 0;

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
            body: JSON.stringify({ name: name })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('[Live] Recording start response:', result);

        // Update UI directly from API response (don't wait for WebSocket)
        isRecording = true;
        recordingName = result.session_id || name;
        recordingStartTime = Date.now();
        recordingSampleCount = 0;
        updateRecordingUI();
        startRecordingTimer();
    } catch (error) {
        console.error('[Live] Failed to start recording:', error);
        alert(`Recording failed to start: ${error.message}`);
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
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('[Live] Recording stop response:', result);

        // Update UI directly from API response (don't wait for WebSocket)
        isRecording = false;
        recordingStartTime = null;
        recordingSampleCount = 0;
        updateRecordingUI();
    } catch (error) {
        console.error('[Live] Failed to stop recording:', error);
        alert(`Recording failed to stop: ${error.message}`);
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
        listEl.innerHTML = '<p class="empty-message">No shots detected yet</p>';
        return;
    }

    // Show most recent segments first
    const html = segments.slice().reverse().map(seg => {
        const duration = seg.endTime
            ? ((seg.endTime - seg.startTime) * 1000).toFixed(0)
            : 'In progress';

        const labelClass = seg.label === 'good' ? 'label-good' :
                          seg.label === 'bad' ? 'label-bad' : '';

        const labelText = seg.label === 'good' ? 'GOOD' :
                         seg.label === 'bad' ? 'BAD' : 'Unmarked';

        return `
            <div class="segment-item ${labelClass}">
                <div class="segment-time">
                    ${new Date(seg.startTime * 1000).toLocaleTimeString()}
                </div>
                <div class="segment-duration">
                    Duration: ${duration}ms
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

        // Format sample count with thousands separator
        const formattedCount = recordingSampleCount.toLocaleString();

        statusEl.innerHTML = `
            <div class="recording-active">
                <span class="recording-dot"></span>
                Recording: ${recordingName}
                <span class="recording-samples">${formattedCount} samples</span>
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
    // Clear any existing timer to prevent duplicates
    stopRecordingTimer();

    const statusEl = document.getElementById('record-status');

    recordingTimerInterval = setInterval(() => {
        if (!isRecording) {
            stopRecordingTimer();
            return;
        }

        const timerEl = document.getElementById('recording-timer');
        if (!timerEl) return;

        const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
        const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
        const seconds = (elapsed % 60).toString().padStart(2, '0');
        timerEl.textContent = `${minutes}:${seconds}`;

        // Also update sample count display
        const samplesEl = statusEl?.querySelector('.recording-samples');
        if (samplesEl) {
            samplesEl.textContent = `${recordingSampleCount.toLocaleString()} samples`;
        }
    }, 1000);
}

/**
 * Stop recording timer
 */
function stopRecordingTimer() {
    if (recordingTimerInterval) {
        clearInterval(recordingTimerInterval);
        recordingTimerInterval = null;
    }
}
