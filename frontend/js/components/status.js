/**
 * Connection Status Component
 * Displays WebSocket connection status
 */

const statusElement = document.getElementById('connection-status');

const STATUS_CONFIG = {
    connected: {
        icon: '🟢',
        text: 'Connected',
        class: 'connected'
    },
    connecting: {
        icon: '🟡',
        text: 'Connecting',
        class: 'connecting'
    },
    disconnected: {
        icon: '🔴',
        text: 'Disconnected',
        class: 'disconnected'
    },
    error: {
        icon: '❌',
        text: 'Error',
        class: 'disconnected'
    }
};

/**
 * Update connection status display
 * @param {string} status - Status key ('connected', 'connecting', 'disconnected', 'error')
 * @param {string} message - Optional custom message
 */
export function updateConnectionStatus(status, message = null) {
    if (!statusElement) return;

    const config = STATUS_CONFIG[status] || STATUS_CONFIG.disconnected;
    const text = message || config.text;

    statusElement.innerHTML = `
        <span class="status-dot ${config.class}"></span>
        <span>${text}</span>
    `;
}
