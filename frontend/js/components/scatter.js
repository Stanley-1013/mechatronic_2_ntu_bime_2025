/**
 * Scatter Plot Component (ECharts)
 * Displays 2D/3D scatter plots for analysis
 */

/**
 * Create ECharts scatter plot
 * @param {HTMLElement} container - Container element
 * @param {object} options - Chart options
 * @returns {object} ECharts instance controller
 */
export function createScatterPlot(container, options = {}) {
    const chart = echarts.init(container, 'dark');

    const defaultOptions = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'item',
            backgroundColor: 'rgba(31, 41, 55, 0.95)',
            borderColor: '#4b5563',
            textStyle: {
                color: '#f3f4f6'
            }
        },
        grid: {
            left: '10%',
            right: '10%',
            bottom: '10%',
            top: '10%',
            containLabel: true
        },
        xAxis: {
            type: 'value',
            name: 'X',
            nameTextStyle: {
                color: '#9ca3af'
            },
            axisLine: {
                lineStyle: {
                    color: '#4b5563'
                }
            },
            axisLabel: {
                color: '#9ca3af'
            },
            splitLine: {
                lineStyle: {
                    color: '#374151'
                }
            }
        },
        yAxis: {
            type: 'value',
            name: 'Y',
            nameTextStyle: {
                color: '#9ca3af'
            },
            axisLine: {
                lineStyle: {
                    color: '#4b5563'
                }
            },
            axisLabel: {
                color: '#9ca3af'
            },
            splitLine: {
                lineStyle: {
                    color: '#374151'
                }
            }
        },
        series: [{
            type: 'scatter',
            symbolSize: 8,
            data: [],
            itemStyle: {
                color: '#2563eb'
            }
        }],
        ...options
    };

    chart.setOption(defaultOptions);

    // Handle resize
    const resizeObserver = new ResizeObserver(() => {
        chart.resize();
    });
    resizeObserver.observe(container);

    return {
        instance: chart,
        resizeObserver,

        /**
         * Update chart data
         * @param {Array} data - Scatter data [[x1, y1], [x2, y2], ...]
         * @param {object} options - Additional options
         */
        setData(data, options = {}) {
            chart.setOption({
                series: [{
                    data,
                    ...options
                }]
            });
        },

        /**
         * Update chart options
         * @param {object} options - ECharts options
         */
        setOption(options) {
            chart.setOption(options);
        },

        /**
         * Clear chart data
         */
        clear() {
            chart.setOption({
                series: [{
                    data: []
                }]
            });
        },

        /**
         * Destroy chart and cleanup
         */
        destroy() {
            resizeObserver.disconnect();
            chart.dispose();
        }
    };
}

/**
 * Create 3D scatter plot
 * @param {HTMLElement} container - Container element
 * @param {object} options - Chart options
 * @returns {object} ECharts instance controller
 */
export function create3DScatterPlot(container, options = {}) {
    const chart = echarts.init(container, 'dark');

    const defaultOptions = {
        backgroundColor: 'transparent',
        tooltip: {},
        xAxis3D: {
            type: 'value',
            name: 'X'
        },
        yAxis3D: {
            type: 'value',
            name: 'Y'
        },
        zAxis3D: {
            type: 'value',
            name: 'Z'
        },
        grid3D: {
            viewControl: {
                autoRotate: false
            }
        },
        series: [{
            type: 'scatter3D',
            symbolSize: 8,
            data: [],
            itemStyle: {
                color: '#2563eb'
            }
        }],
        ...options
    };

    chart.setOption(defaultOptions);

    // Handle resize
    const resizeObserver = new ResizeObserver(() => {
        chart.resize();
    });
    resizeObserver.observe(container);

    return {
        instance: chart,
        resizeObserver,

        setData(data, options = {}) {
            chart.setOption({
                series: [{
                    data,
                    ...options
                }]
            });
        },

        setOption(options) {
            chart.setOption(options);
        },

        clear() {
            chart.setOption({
                series: [{
                    data: []
                }]
            });
        },

        destroy() {
            resizeObserver.disconnect();
            chart.dispose();
        }
    };
}
