/**
 * Analysis Tab - Shot segments analysis and visualization with K-means clustering
 */

let scatterChart = null;
let allSegments = [];
let selectedSegmentId = null;
let clusterData = null;
let showClusters = false;

// Cluster colors
const CLUSTER_COLORS = [
    '#ef4444', '#22c55e', '#3b82f6', '#f59e0b', '#a855f7',
    '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1'
];

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
                let tooltip = `Shot: ${data.shot_id}<br/>
                        x: ${data.value[0].toFixed(2)}<br/>
                        y: ${data.value[1].toFixed(2)}<br/>
                        Label: ${data.label}`;
                if (data.cluster_id !== undefined) {
                    tooltip += `<br/>Cluster: ${data.cluster_id}`;
                }
                return tooltip;
            }
        },
        legend: {
            show: false,
            textStyle: { color: '#f3f4f6' }
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
                    if (showClusters && params.data.cluster_id !== undefined) {
                        return CLUSTER_COLORS[params.data.cluster_id % CLUSTER_COLORS.length];
                    }
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
    const clusterBtn = document.getElementById('btn-cluster');
    const clusterCount = document.getElementById('cluster-count');

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
            clusterData = null;
            showClusters = false;
            updateScatterChart();
        });
    }

    if (scatterY) {
        scatterY.addEventListener('change', () => {
            clusterData = null;
            showClusters = false;
            updateScatterChart();
        });
    }

    // Refresh button
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            clusterData = null;
            showClusters = false;
            loadSegments();
        });
    }

    // Cluster button
    if (clusterBtn) {
        clusterBtn.addEventListener('click', () => {
            const n = clusterCount ? parseInt(clusterCount.value) : 3;
            runClustering(n);
        });
    }
}

/**
 * Load segments from API
 */
async function loadSegments() {
    try {
        console.log('[Analysis] Loading segments...');

        const response = await fetch('/api/segments');

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        allSegments = await response.json();
        console.log(`[Analysis] Loaded ${allSegments.length} segments`);

        // Update UI
        updateSegmentsList();
        updateScatterChart();
        updateStats();

    } catch (error) {
        console.error('[Analysis] Failed to load segments:', error);

        // Show empty state
        allSegments = [];
        updateSegmentsList();
        updateScatterChart();
    }
}

/**
 * Run K-means clustering
 * @param {number} nClusters - Number of clusters
 */
async function runClustering(nClusters) {
    const scatterX = document.getElementById('scatter-x');
    const scatterY = document.getElementById('scatter-y');

    const xKey = scatterX ? scatterX.value : 'g1_rms';
    const yKey = scatterY ? scatterY.value : 'dg_rms';

    try {
        console.log(`[Analysis] Running K-means with ${nClusters} clusters...`);

        const response = await fetch('/api/segments/cluster', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                n_clusters: nClusters,
                features: [xKey, yKey]
            })
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        clusterData = await response.json();
        showClusters = true;

        console.log(`[Analysis] Clustering complete: ${clusterData.clusters.length} clusters`);

        // Update chart with cluster colors
        updateScatterChart();

        // Show cluster info
        displayClusterInfo();

    } catch (error) {
        console.error('[Analysis] Clustering failed:', error);
        alert(`分群失敗: ${error.message}`);
    }
}

/**
 * Display cluster information
 */
function displayClusterInfo() {
    if (!clusterData) return;

    const container = document.getElementById('segment-detail');
    if (!container) return;

    const clustersHtml = clusterData.clusters.map((cluster, idx) => {
        const color = CLUSTER_COLORS[idx % CLUSTER_COLORS.length];
        return `
            <tr>
                <td><span style="display:inline-block;width:12px;height:12px;background:${color};border-radius:50%;margin-right:8px;"></span>Cluster ${cluster.cluster_id}</td>
                <td>${cluster.count} shots</td>
            </tr>
            <tr>
                <td style="padding-left:24px;">Good ratio:</td>
                <td>${(cluster.good_ratio * 100).toFixed(1)}%</td>
            </tr>
        `;
    }).join('');

    container.innerHTML = `
        <div class="detail-content">
            <h4>K-means 分群結果</h4>
            <p>共 ${clusterData.n_clusters} 群，${clusterData.total_segments} 筆資料</p>
            <table>
                ${clustersHtml}
            </table>
            <h4 style="margin-top:1rem;">群心座標</h4>
            <table>
                ${clusterData.clusters.map((cluster, idx) => {
                    const centerStr = Object.entries(cluster.center)
                        .map(([k, v]) => `${k}: ${v.toFixed(2)}`)
                        .join(', ');
                    return `<tr><td>Cluster ${cluster.cluster_id}:</td><td>${centerStr}</td></tr>`;
                }).join('')}
            </table>
        </div>
    `;
}

/**
 * Update statistics display
 */
async function updateStats() {
    try {
        const response = await fetch('/api/segments/stats');
        if (!response.ok) return;

        const stats = await response.json();

        // Update stats display if elements exist
        const totalEl = document.getElementById('stat-total');
        const goodEl = document.getElementById('stat-good');
        const unknownEl = document.getElementById('stat-unknown');

        if (totalEl) totalEl.textContent = stats.total;
        if (goodEl) goodEl.textContent = stats.good;
        if (unknownEl) unknownEl.textContent = stats.unknown;

    } catch (error) {
        console.error('[Analysis] Failed to load stats:', error);
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

    // Get cluster assignment map
    const clusterMap = {};
    if (clusterData && clusterData.assignments) {
        clusterData.assignments.forEach(a => {
            clusterMap[a.shot_id] = a.cluster_id;
        });
    }

    // Render segments
    container.innerHTML = filtered.map(seg => {
        const isSelected = seg.shot_id === selectedSegmentId;
        const features = seg.features || {};
        const clusterId = clusterMap[seg.shot_id];
        const clusterColor = clusterId !== undefined ? CLUSTER_COLORS[clusterId % CLUSTER_COLORS.length] : null;

        return `
            <div class="segment-item ${isSelected ? 'selected' : ''} label-${seg.label}"
                 data-shot-id="${seg.shot_id}"
                 style="${clusterColor && showClusters ? `border-left-color: ${clusterColor}` : ''}">
                <div class="segment-item-header">
                    <span class="segment-item-id">${seg.shot_id.substring(0, 8)}</span>
                    <span class="segment-label label-${seg.label}">${seg.label}</span>
                    ${clusterId !== undefined && showClusters ? `<span style="font-size:0.75rem;color:${clusterColor};">C${clusterId}</span>` : ''}
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

    // Get cluster assignment map
    const clusterMap = {};
    if (clusterData && clusterData.assignments) {
        clusterData.assignments.forEach(a => {
            clusterMap[a.shot_id] = a.cluster_id;
        });
    }

    // Transform data
    const scatterData = allSegments
        .map(seg => {
            const xVal = getFeatureValue(seg, xKey);
            const yVal = getFeatureValue(seg, yKey);

            if (xVal === null || yVal === null) return null;

            return {
                value: [xVal, yVal],
                shot_id: seg.shot_id,
                label: seg.label,
                cluster_id: clusterMap[seg.shot_id]
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
            data: scatterData,
            itemStyle: {
                color: (params) => {
                    if (showClusters && params.data.cluster_id !== undefined) {
                        return CLUSTER_COLORS[params.data.cluster_id % CLUSTER_COLORS.length];
                    }
                    return params.data.label === 'good' ? '#10b981' : '#6b7280';
                }
            }
        }]
    });

    console.log(`[Analysis] Scatter chart updated (${scatterData.length} points, clusters: ${showClusters})`);
}

/**
 * Get feature value from segment
 * @param {object} seg - Segment
 * @param {string} key - Feature key
 * @returns {number|null} Feature value
 */
function getFeatureValue(seg, key) {
    const features = seg.features || {};

    if (key === 'dur' || key === 'duration_ms') {
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
        'dur': 'Duration (ms)',
        'duration_ms': 'Duration (ms)'
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

    // Get cluster info if available
    let clusterInfo = '';
    if (clusterData && clusterData.assignments) {
        const assignment = clusterData.assignments.find(a => a.shot_id === segment.shot_id);
        if (assignment) {
            const cluster = clusterData.clusters[assignment.cluster_id];
            const color = CLUSTER_COLORS[assignment.cluster_id % CLUSTER_COLORS.length];
            clusterInfo = `
                <tr>
                    <td>分群:</td>
                    <td><span style="color:${color};">Cluster ${assignment.cluster_id}</span> (Good率: ${(cluster.good_ratio * 100).toFixed(1)}%)</td>
                </tr>
            `;
        }
    }

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
                ${clusterInfo}
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
