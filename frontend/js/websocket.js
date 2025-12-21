/**
 * WebSocket Manager for Mechtronic
 * Handles real-time data streaming from backend
 */

import { updateConnectionStatus } from './components/status.js';

// WebSocket configuration
const WS_URL = window.location.hostname === 'localhost'
    ? 'ws://localhost:8000/ws'
    : `ws://${window.location.host}/ws`;

const RECONNECT_DELAY = 3000; // 3 seconds
const MAX_RECONNECT_ATTEMPTS = 5;

let ws = null;
let reconnectAttempts = 0;
let reconnectTimer = null;
let messageHandlers = [];

/**
 * Initialize WebSocket connection
 * @returns {Promise<WebSocket>} Connected WebSocket
 */
export function initWebSocket() {
    return new Promise((resolve, reject) => {
        if (ws?.readyState === WebSocket.OPEN) {
            resolve(ws);
            return;
        }

        console.log(`[WebSocket] Connecting to ${WS_URL}...`);
        updateConnectionStatus('connecting');

        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            console.log('[WebSocket] Connected');
            reconnectAttempts = 0;
            updateConnectionStatus('connected');
            resolve(ws);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleMessage(data);
            } catch (error) {
                console.error('[WebSocket] Failed to parse message:', error);
            }
        };

        ws.onerror = (error) => {
            console.error('[WebSocket] Error:', error);
            updateConnectionStatus('error', 'Connection error');
            reject(error);
        };

        ws.onclose = (event) => {
            console.log('[WebSocket] Closed:', event.code, event.reason);
            updateConnectionStatus('disconnected');
            ws = null;

            // Attempt reconnection
            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                scheduleReconnect();
            } else {
                console.error('[WebSocket] Max reconnection attempts reached');
                updateConnectionStatus('error', 'Failed to reconnect');
            }
        };
    });
}

/**
 * Close WebSocket connection
 */
export function closeWebSocket() {
    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }

    if (ws) {
        console.log('[WebSocket] Closing connection...');
        ws.close();
        ws = null;
    }
}

/**
 * Schedule reconnection attempt
 */
function scheduleReconnect() {
    if (reconnectTimer) return;

    reconnectAttempts++;
    const delay = RECONNECT_DELAY * reconnectAttempts;

    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);
    updateConnectionStatus('connecting', `Reconnecting (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);

    reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        initWebSocket().catch(error => {
            console.error('[WebSocket] Reconnection failed:', error);
        });
    }, delay);
}

/**
 * Send message through WebSocket
 * @param {object} data - Data to send
 */
export function sendMessage(data) {
    if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    } else {
        console.error('[WebSocket] Cannot send message: not connected');
    }
}

/**
 * Register message handler
 * @param {function} handler - Handler function (receives parsed data)
 * @returns {function} Unregister function
 */
export function onMessage(handler) {
    messageHandlers.push(handler);

    // Return unregister function
    return () => {
        const index = messageHandlers.indexOf(handler);
        if (index > -1) {
            messageHandlers.splice(index, 1);
        }
    };
}

/**
 * Handle incoming WebSocket message
 * @param {object} data - Parsed message data
 */
function handleMessage(data) {
    // Dispatch to all registered handlers
    messageHandlers.forEach(handler => {
        try {
            handler(data);
        } catch (error) {
            console.error('[WebSocket] Handler error:', error);
        }
    });
}

/**
 * Get current WebSocket state
 * @returns {string} State name
 */
export function getState() {
    if (!ws) return 'CLOSED';

    switch (ws.readyState) {
        case WebSocket.CONNECTING: return 'CONNECTING';
        case WebSocket.OPEN: return 'OPEN';
        case WebSocket.CLOSING: return 'CLOSING';
        case WebSocket.CLOSED: return 'CLOSED';
        default: return 'UNKNOWN';
    }
}
