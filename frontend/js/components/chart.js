/**
 * Time-Series Chart Component (uPlot)
 * Displays sensor data over time
 */

/**
 * Create uPlot time-series chart
 * @param {HTMLElement} container - Container element
 * @param {object} options - Chart options
 * @returns {object} uPlot instance
 */
export function createTimeSeriesChart(container, options = {}) {
    // Ensure minimum dimensions - fallback if container not yet rendered
    const width = container.clientWidth || 800;
    const height = Math.max(container.clientHeight - 20, 280);

    const defaultOptions = {
        width: width,
        height: height,
        series: [
            {
                label: 'Time'
            },
            {
                label: 'Value',
                stroke: '#2563eb',
                width: 2
            }
        ],
        axes: [
            {
                stroke: '#9ca3af',
                grid: {
                    show: true,
                    stroke: '#374151',
                    width: 1
                }
            },
            {
                stroke: '#9ca3af',
                grid: {
                    show: true,
                    stroke: '#374151',
                    width: 1
                }
            }
        ],
        ...options
    };

    // Initial empty data
    const data = [
        [], // timestamps
        []  // values
    ];

    const chart = new uPlot(defaultOptions, data, container);

    // Handle resize
    const resizeObserver = new ResizeObserver(() => {
        const newWidth = container.clientWidth || 800;
        const newHeight = Math.max(container.clientHeight - 20, 280);
        chart.setSize({
            width: newWidth,
            height: newHeight
        });
    });
    resizeObserver.observe(container);

    return {
        instance: chart,
        resizeObserver,

        /**
         * Update chart data
         * @param {Array<Array>} newData - New data [[timestamps], [values1], [values2], ...]
         */
        setData(newData) {
            chart.setData(newData);
        },

        /**
         * Append new data point
         * @param {number} timestamp - Unix timestamp
         * @param {Array<number>} values - Values for each series
         */
        append(timestamp, values) {
            const data = chart.data;
            data[0].push(timestamp);

            values.forEach((value, index) => {
                if (!data[index + 1]) {
                    data[index + 1] = [];
                }
                data[index + 1].push(value);
            });

            chart.setData(data);
        },

        /**
         * Clear chart data
         */
        clear() {
            const seriesCount = chart.data.length;
            // Create independent empty arrays (not shared references)
            const emptyData = Array(seriesCount).fill(null).map(() => []);
            chart.setData(emptyData);
        },

        /**
         * Destroy chart and cleanup
         */
        destroy() {
            resizeObserver.disconnect();
            chart.destroy();
        }
    };
}

/**
 * Create multi-series time-series chart
 * @param {HTMLElement} container - Container element
 * @param {Array<string>} seriesNames - Series names
 * @param {Array<string>} colors - Series colors
 * @returns {object} Chart controller
 */
export function createMultiSeriesChart(container, seriesNames, colors) {
    const series = [
        { label: 'Time' },
        ...seriesNames.map((name, i) => ({
            label: name,
            stroke: colors[i] || '#2563eb',
            width: 2
        }))
    ];

    return createTimeSeriesChart(container, { series });
}
