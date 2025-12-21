/**
 * Analysis Tab - Shot segments analysis and visualization
 */

let scatterChart = null;
let allSegments = [];
let selectedSegmentId = null;

/**
 * Initialize Analysis tab
 * @returns {object} Tab controller
 */
export function initAnalysisTab() {
    console.log('[Analysis] Initializing Analysis tab...');

    // Initialize scatter chart
    initScatterChart();

    // Setup controls
    setupControls();

    // Load segments
    loadSegments();

    return {
        destroy() {
            if (scatterChart) {
                scatterChart.dispose();
                scatterChart = null;
            }
        }
    };
}

/**
 * Initialize scatter chart
 */
function initScatterChart() {
    const container = document.getElementById('scatter-chart');
    if (!container) {
        console.error('[Analysis] Scatter chart container not found');
        return;
    }

    scatterChart = echarts.init(container, 'dark');

    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'item',
            formatter: (params) => {
                const data = params.data;
                return `Shot: ${data.shot_id}<br/>
                        x: ${data.value[0].toFixed(2)}<br/>
                        y: ${data.value[1].toFixed(2)}<br/>
                        Label: ${data.label}`;
            }
        },
        xAxis: {
            name: 'g1_rms',
            type: 'value',
            nameTextStyle: { color: '#9ca3af' },
            nameLocation: 'center',
            nameGap: 30,
            axisLine: {
                lineStyle: { color: '#4b5563' }
            },
            axisLabel: { color: '#9ca3af' },
            splitLine: {
                lineStyle: { color: '#374151' }
            }
        },
        yAxis: {
            name: 'dg_rms',
            type: 'value',
            nameTextStyle: { color: '#9ca3af' },
            nameLocation: 'center',
            nameGap: 40,
            axisLine: {
                lineStyle: { color: '#4b5563' }
            },
            axisLabel: { color: '#9ca3af' },
            splitLine: {
                lineStyle: { color: '#374151' }
            }
        },
        series: [{
            type: 'scatter',
            symbolSize: 12,
            data: [],
            itemStyle: {
                color: (params) => {
                    return params.data.label === 'good' ? '#10b981' : '#6b7280';
                }
            }
        }]
    };

    scatterChart.setOption(option);

    // Click event
    scatterChart.on('click', (params) => {
        selectSegment(params.data.shot_id);
    });

    // Handle resize
    window.addEventListener('resize', () => {
        if (scatterChart) scatterChart.resize();
    });

    console.log('[Analysis] Scatter chart initialized');
}

/**
 * Setup controls
 */
function setupControls() {
    const filterGood = document.getElementById('filter-good');
    const filterUnknown = document.getElementById('filter-unknown');
    const scatterX = document.getElementById('scatter-x');
    const scatterY = document.getElementById('scatter-y');
    const refreshBtn = document.getElementById('scatter-refresh');

    // Filter checkboxes
    if (filterGood) {
        filterGood.addEventListener('change', () => {
            updateSegmentsList();
        });
    }

    if (filterUnknown) {
        filterUnknown.addEventListener('change', () => {
            updateSegmentsList();
        });
    }

    // Scatter axis selects
    if (scatterX) {
        scatterX.addEventListener('change', () => {
            updateScatterChart();
        });
    }

    if (scatterY) {
        scatterY.addEventListener('change', () => {
            updateScatterChart();
        });
    }

    // Refresh button
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadSegments();
        });
    }
}

/**
 * Load segments from API
 */
async function loadSegments() {
    try {
        console.log('[Analysis] Loading segments...');

        // TODO: Replace with actual API call
        // For now, use mock data
        const response = await fetch('/api/segments');

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        allSegments = await response.json();
        console.log(`[Analysis] Loaded ${allSegments.length} segments`);

        // Update UI
        updateSegmentsList();
        updateScatterChart();

    } catch (error) {
        console.error('[Analysis] Failed to load segments:', error);

        // Use mock data for development
        allSegments = generateMockSegments();
        updateSegmentsList();
        updateScatterChart();
    }
}

/**
 * Update segments list display
 */
function updateSegmentsList() {
    const container = document.getElementById('analysis-segments-list');
    if (!container) return;

    const filterGood = document.getElementById('filter-good');
    const filterUnknown = document.getElementById('filter-unknown');

    const showGood = filterGood ? filterGood.checked : true;
    const showUnknown = filterUnknown ? filterUnknown.checked : true;

    // Filter segments
    const filtered = allSegments.filter(seg => {
        if (seg.label === 'good' && !showGood) return false;
        if (seg.label === 'unknown' && !showUnknown) return false;
        return true;
    });

    if (filtered.length === 0) {
        container.innerHTML = '<div class="empty-message">沒有符合條件的段落</div>';
        return;
    }

    // Render segments
    container.innerHTML = filtered.map(seg => {
        const isSelected = seg.shot_id === selectedSegmentId;
        const features = seg.features || {};

        return `
            <div class="segment-item ${isSelected ? 'selected' : ''} label-${seg.label}"
                 data-shot-id="${seg.shot_id}">
                <div class="segment-item-header">
                    <span class="segment-item-id">${seg.shot_id.substring(0, 8)}</span>
                    <span class="segment-label label-${seg.label}">${seg.label}</span>
                </div>
                <div class="segment-item-features">
                    Dur: ${seg.duration_ms}ms |
                    g1_rms: ${features.g1_rms?.toFixed(1) || 'N/A'} |
                    dg_rms: ${features.dg_rms?.toFixed(1) || 'N/A'}
                </div>
            </div>
        `;
    }).join('');

    // Add click listeners
    container.querySelectorAll('.segment-item').forEach(item => {
        item.addEventListener('click', () => {
            const shotId = item.dataset.shotId;
            selectSegment(shotId);
        });
    });
}

/**
 * Update scatter chart
 */
function updateScatterChart() {
    if (!scatterChart) return;

    const scatterX = document.getElementById('scatter-x');
    const scatterY = document.getElementById('scatter-y');

    const xKey = scatterX ? scatterX.value : 'g1_rms';
    const yKey = scatterY ? scatterY.value : 'dg_rms';

    // Get axis labels
    const xLabel = getFeatureLabel(xKey);
    const yLabel = getFeatureLabel(yKey);

    // Transform data
    const scatterData = allSegments
        .map(seg => {
            const features = seg.features || {};
            const xVal = getFeatureValue(seg, xKey);
            const yVal = getFeatureValue(seg, yKey);

            if (xVal === null || yVal === null) return null;

            return {
                value: [xVal, yVal],
                shot_id: seg.shot_id,
                label: seg.label
            };
        })
        .filter(d => d !== null);

    // Update chart
    scatterChart.setOption({
        xAxis: {
            name: xLabel
        },
        yAxis: {
            name: yLabel
        },
        series: [{
            data: scatterData
        }]
    });

    console.log(`[Analysis] Scatter chart updated (${scatterData.length} points)`);
}

/**
 * Get feature value from segment
 * @param {object} seg - Segment
 * @param {string} key - Feature key
 * @returns {number|null} Feature value
 */
function getFeatureValue(seg, key) {
    const features = seg.features || {};

    if (key === 'dur') {
        return seg.duration_ms;
    }

    return features[key] !== undefined ? features[key] : null;
}

/**
 * Get feature display label
 * @param {string} key - Feature key
 * @returns {string} Display label
 */
function getFeatureLabel(key) {
    const labels = {
        'g1_rms': 'Gyro1 RMS (deg/s)',
        'g1_peak': 'Gyro1 Peak (deg/s)',
        'g2_rms': 'Gyro2 RMS (deg/s)',
        'g2_peak': 'Gyro2 Peak (deg/s)',
        'dg_rms': 'Delta RMS (deg/s)',
        'dur': 'Duration (ms)'
    };

    return labels[key] || key;
}

/**
 * Select a segment
 * @param {string} shotId - Shot ID
 */
function selectSegment(shotId) {
    selectedSegmentId = shotId;

    // Update list display
    updateSegmentsList();

    // Show segment detail
    const segment = allSegments.find(seg => seg.shot_id === shotId);
    if (segment) {
        displaySegmentDetail(segment);
    }
}

/**
 * Display segment detail
 * @param {object} segment - Segment data
 */
function displaySegmentDetail(segment) {
    const container = document.getElementById('segment-detail');
    if (!container) return;

    const features = segment.features || {};

    container.innerHTML = `
        <div class="detail-content">
            <h4>基本資訊</h4>
            <table>
                <tr>
                    <td>Shot ID:</td>
                    <td>${segment.shot_id}</td>
                </tr>
                <tr>
                    <td>標籤:</td>
                    <td><span class="segment-label label-${segment.label}">${segment.label}</span></td>
                </tr>
                <tr>
                    <td>時長:</td>
                    <td>${segment.duration_ms} ms</td>
                </tr>
                <tr>
                    <td>樣本數:</td>
                    <td>${segment.sample_count || 'N/A'}</td>
                </tr>
            </table>

            <h4>特徵</h4>
            <table>
                <tr>
                    <td>g1_rms:</td>
                    <td>${features.g1_rms?.toFixed(2) || 'N/A'}</td>
                </tr>
                <tr>
                    <td>g1_peak:</td>
                    <td>${features.g1_peak?.toFixed(2) || 'N/A'}</td>
                </tr>
                <tr>
                    <td>g2_rms:</td>
                    <td>${features.g2_rms?.toFixed(2) || 'N/A'}</td>
                </tr>
                <tr>
                    <td>g2_peak:</td>
                    <td>${features.g2_peak?.toFixed(2) || 'N/A'}</td>
                </tr>
                <tr>
                    <td>dg_rms:</td>
                    <td>${features.dg_rms?.toFixed(2) || 'N/A'}</td>
                </tr>
            </table>
        </div>
    `;
}

/**
 * Generate mock segments for development
 * @returns {Array} Mock segments
 */
function generateMockSegments() {
    const segments = [];

    for (let i = 0; i < 20; i++) {
        const label = Math.random() > 0.3 ? 'good' : 'unknown';
        const g1_rms = Math.random() * 100 + 50;
        const g2_rms = Math.random() * 80 + 40;
        const dg_rms = Math.abs(g1_rms - g2_rms) * (0.8 + Math.random() * 0.4);

        segments.push({
            shot_id: `shot_${i.toString().padStart(3, '0')}_${Date.now()}`,
            t_start_ms: Date.now() - (20 - i) * 5000,
            t_end_ms: Date.now() - (20 - i) * 5000 + 800,
            duration_ms: 600 + Math.floor(Math.random() * 400),
            label: label,
            sample_count: 60 + Math.floor(Math.random() * 40),
            features: {
                g1_rms: g1_rms,
                g1_peak: g1_rms * (1.5 + Math.random() * 0.5),
                g2_rms: g2_rms,
                g2_peak: g2_rms * (1.5 + Math.random() * 0.5),
                dg_rms: dg_rms
            }
        });
    }

    return segments;
}
