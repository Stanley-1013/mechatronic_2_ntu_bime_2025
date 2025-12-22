/**
 * Mechtronic Frontend - Main Application
 * Vanilla JavaScript SPA with tab-based navigation
 */

import { initWebSocket, closeWebSocket } from './websocket.js';
import { updateConnectionStatus } from './components/status.js';
import { initLiveTab } from './tabs/live.js';
import { initReplayTab } from './tabs/replay.js';
import { initAnalysisTab } from './tabs/analysis.js';

class MechtronicApp {
    constructor() {
        this.currentTab = 'live';
        this.tabs = {
            live: null,
            replay: null,
            analysis: null
        };
    }

    /**
     * Initialize application
     */
    async init() {
        console.log('[App] Initializing Mechtronic application...');

        // Initialize tab navigation
        this.initTabNavigation();

        // Initialize connection status component
        updateConnectionStatus('disconnected');

        // Initialize tabs
        this.tabs.live = initLiveTab();
        this.tabs.replay = initReplayTab();
        this.tabs.analysis = initAnalysisTab();

        // Connect WebSocket for live tab
        try {
            await initWebSocket();
            console.log('[App] WebSocket connected');
        } catch (error) {
            console.error('[App] Failed to connect WebSocket:', error);
            updateConnectionStatus('error', error.message);
        }

        console.log('[App] Application initialized');
    }

    /**
     * Initialize tab navigation
     */
    initTabNavigation() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');

        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabName = button.dataset.tab;

                // Update active states
                tabButtons.forEach(btn => btn.classList.remove('active'));
                tabContents.forEach(content => content.classList.remove('active'));

                button.classList.add('active');
                document.getElementById(`tab-${tabName}`).classList.add('active');

                // Handle tab change
                this.onTabChange(tabName);
            });
        });
    }

    /**
     * Handle tab change
     * @param {string} tabName - New tab name
     */
    onTabChange(tabName) {
        console.log(`[App] Switching to tab: ${tabName}`);
        this.currentTab = tabName;

        // Tab-specific behavior
        switch (tabName) {
            case 'live':
                // Resume WebSocket if needed
                if (!this.tabs.live?.isActive) {
                    this.tabs.live?.activate();
                }
                break;

            case 'replay':
                // Pause live updates
                this.tabs.live?.deactivate();
                // Resize ECharts after tab becomes visible
                setTimeout(() => this.resizeCharts('replay'), 50);
                break;

            case 'analysis':
                // Pause live updates
                this.tabs.live?.deactivate();
                // Resize ECharts after tab becomes visible
                setTimeout(() => this.resizeCharts('analysis'), 50);
                break;
        }
    }

    /**
     * Resize charts in a specific tab
     * @param {string} tabName - Tab name
     */
    resizeCharts(tabName) {
        // Find all ECharts instances in the tab and resize them
        const tabEl = document.getElementById(`tab-${tabName}`);
        if (!tabEl) return;

        // Get all chart containers that might have ECharts instances
        const chartContainers = tabEl.querySelectorAll('[id$="-chart"]');
        chartContainers.forEach(container => {
            const chartInstance = echarts.getInstanceByDom(container);
            if (chartInstance) {
                console.log(`[App] Resizing chart: ${container.id}`);
                chartInstance.resize();
            }
        });
    }

    /**
     * Cleanup on page unload
     */
    cleanup() {
        console.log('[App] Cleaning up...');
        closeWebSocket();
    }
}

// Initialize app on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new MechtronicApp();
    app.init();

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => app.cleanup());

    // Expose for debugging
    window.mechtronicApp = app;
});
