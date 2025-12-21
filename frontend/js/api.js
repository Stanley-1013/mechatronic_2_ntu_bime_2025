/**
 * API Client for Mechtronic Backend
 * Handles HTTP requests to FastAPI backend
 */

// Configuration
const API_BASE_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api'
    : '/api';

/**
 * Generic fetch wrapper with error handling
 * @param {string} endpoint - API endpoint (e.g., '/sessions')
 * @param {object} options - Fetch options
 * @returns {Promise<any>} Response data
 */
async function apiFetch(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    };

    try {
        const response = await fetch(url, config);

        // Handle non-OK responses
        if (!response.ok) {
            const error = await response.json().catch(() => ({
                detail: `HTTP ${response.status}: ${response.statusText}`
            }));
            throw new Error(error.detail || error.message || 'API request failed');
        }

        return await response.json();
    } catch (error) {
        console.error(`[API] Request failed: ${endpoint}`, error);
        throw error;
    }
}

/**
 * Get all sessions
 * @returns {Promise<Array>} List of sessions
 */
export async function getSessions() {
    return apiFetch('/sessions');
}

/**
 * Get session by ID
 * @param {string} sessionId - Session ID
 * @returns {Promise<object>} Session data
 */
export async function getSession(sessionId) {
    return apiFetch(`/sessions/${sessionId}`);
}

/**
 * Start a new session
 * @param {object} config - Session configuration
 * @returns {Promise<object>} Created session
 */
export async function startSession(config = {}) {
    return apiFetch('/sessions', {
        method: 'POST',
        body: JSON.stringify(config)
    });
}

/**
 * Stop a session
 * @param {string} sessionId - Session ID
 * @returns {Promise<object>} Updated session
 */
export async function stopSession(sessionId) {
    return apiFetch(`/sessions/${sessionId}/stop`, {
        method: 'POST'
    });
}

/**
 * Query time-series data
 * @param {object} params - Query parameters
 * @param {string} params.start_time - ISO 8601 start time
 * @param {string} params.end_time - ISO 8601 end time
 * @param {string} params.session_id - Session ID (optional)
 * @param {number} params.limit - Max records (optional)
 * @returns {Promise<Array>} Time-series data
 */
export async function queryTimeSeries(params) {
    const query = new URLSearchParams(params).toString();
    return apiFetch(`/timeseries?${query}`);
}

/**
 * Query shots (shot_id records)
 * @param {object} params - Query parameters
 * @param {string} params.start_time - ISO 8601 start time
 * @param {string} params.end_time - ISO 8601 end time
 * @param {string} params.session_id - Session ID (optional)
 * @returns {Promise<Array>} Shots data
 */
export async function queryShots(params) {
    const query = new URLSearchParams(params).toString();
    return apiFetch(`/shots?${query}`);
}

/**
 * Get analysis statistics
 * @param {object} params - Query parameters
 * @param {string} params.metric - Metric name (e.g., 'release_angle')
 * @param {string} params.start_time - ISO 8601 start time
 * @param {string} params.end_time - ISO 8601 end time
 * @returns {Promise<object>} Analysis results
 */
export async function getAnalysis(params) {
    const query = new URLSearchParams(params).toString();
    return apiFetch(`/analysis?${query}`);
}

/**
 * Health check
 * @returns {Promise<object>} Health status
 */
export async function healthCheck() {
    return apiFetch('/health');
}
