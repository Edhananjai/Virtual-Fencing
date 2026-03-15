/**
 * app.js — WebSocket client, real-time updates, alerts, and UI logic.
 */

let ws = null;
let alertCount = 0;
let alertAudio = null;
let isMonitoring = false;

// ── Initialize ──
document.addEventListener('DOMContentLoaded', async () => {
    // Fetch config and initialize map
    const resp = await fetch('/api/config');
    const config = await resp.json();

    initMap(config.center_lat, config.center_lon, config.zoom);

    if (config.fence && config.fence.length >= 3) {
        drawFence(config.fence);
        // Enable start monitoring if fence exists
        document.getElementById('btn-start-monitoring').disabled = false;
    }

    // Set initial monitoring state
    if (config.monitoring) {
        setMonitoringUI(true);
    }

    // Load existing alerts
    loadAlerts();

    // Connect WebSocket
    connectWebSocket();

    // Button handlers
    document.getElementById('btn-draw-fence').addEventListener('click', onDrawFence);
    document.getElementById('btn-clear-fence').addEventListener('click', onClearFence);
    document.getElementById('btn-save-fence').addEventListener('click', onSaveFence);
    document.getElementById('btn-start-monitoring').addEventListener('click', onStartMonitoring);
    document.getElementById('btn-stop-monitoring').addEventListener('click', onStopMonitoring);

    // Create alert sound
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        alertAudio = audioCtx;
    } catch (e) {
        // Audio not supported
    }
});


// ── WebSocket ──
function connectWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws`);

    ws.onopen = () => {
        document.getElementById('connection-status').className = 'status-dot connected';
        document.getElementById('connection-status').title = 'Connected';
        console.log('[WS] Connected');
    };

    ws.onclose = () => {
        document.getElementById('connection-status').className = 'status-dot disconnected';
        document.getElementById('connection-status').title = 'Disconnected';
        console.log('[WS] Disconnected — reconnecting in 3s...');
        setTimeout(connectWebSocket, 3000);
    };

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleMessage(msg);
    };

    // Keep alive
    setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
        }
    }, 30000);
}


function handleMessage(msg) {
    switch (msg.type) {
        case 'init':
            if (msg.fence && msg.fence.length >= 3) {
                drawFence(msg.fence);
                document.getElementById('btn-start-monitoring').disabled = false;
            }
            if (msg.monitoring !== undefined) {
                setMonitoringUI(msg.monitoring);
            }
            if (msg.positions) {
                for (const [name, pos] of Object.entries(msg.positions)) {
                    updateAnimalMarker(pos.node_name, pos.lat, pos.lon, pos.inside_fence);
                    updateNodeInfo(pos);
                }
            }
            break;

        case 'gps_update':
            updateAnimalMarker(msg.node_name, msg.lat, msg.lon, msg.inside_fence);
            updateNodeInfo(msg);
            break;

        case 'alert':
            addAlert(msg);
            showToast(`ALERT: ${msg.node_name} left the fence!`);
            playAlertSound();
            break;

        case 'fence_updated':
            drawFence(msg.fence);
            document.getElementById('btn-start-monitoring').disabled = false;
            break;

        case 'monitoring_started':
            setMonitoringUI(true);
            showToast('Monitoring started — watching for fence breaches.');
            break;

        case 'monitoring_stopped':
            setMonitoringUI(false);
            showToast('Monitoring stopped.');
            break;
    }
}


// ── Node Info ──
function updateNodeInfo(data) {
    const container = document.getElementById('node-info');
    let card = document.getElementById(`node-${data.node_name}`);

    if (!card) {
        card = document.createElement('div');
        card.id = `node-${data.node_name}`;
        card.className = 'node-card';
        container.innerHTML = '';
        container.appendChild(card);
    }

    let statusClass, statusText;
    if (data.inside_fence === null || data.inside_fence === undefined) {
        statusClass = 'idle';
        statusText = 'NOT MONITORING';
    } else if (data.inside_fence) {
        statusClass = 'inside';
        statusText = 'INSIDE FENCE';
    } else {
        statusClass = 'outside';
        statusText = 'OUTSIDE FENCE';
    }

    card.innerHTML = `
        <div class="node-name">${escapeHtml(data.node_name)}</div>
        <div class="coords">${data.lat.toFixed(6)}, ${data.lon.toFixed(6)}</div>
        <div class="fence-status ${statusClass}">${statusText}</div>
    `;
}


// ── Alerts ──
async function loadAlerts() {
    const resp = await fetch('/api/alerts?limit=20');
    const data = await resp.json();

    if (data.alerts && data.alerts.length > 0) {
        alertCount = data.alerts.length;
        document.getElementById('alert-count').textContent = alertCount;

        const container = document.getElementById('alert-list');
        container.innerHTML = '';
        data.alerts.forEach(a => appendAlertItem(container, a));
    }
}


function addAlert(alert) {
    alertCount++;
    document.getElementById('alert-count').textContent = alertCount;

    const container = document.getElementById('alert-list');
    if (container.querySelector('.muted')) {
        container.innerHTML = '';
    }

    const item = document.createElement('div');
    item.className = 'alert-item';
    item.innerHTML = `
        <div class="alert-node">${alert.node_name} — GEOFENCE BREACH</div>
        <div class="alert-coords">${alert.lat.toFixed(6)}, ${alert.lon.toFixed(6)}</div>
        <div class="alert-time">${new Date().toLocaleTimeString()}</div>
    `;
    container.insertBefore(item, container.firstChild);
}


function appendAlertItem(container, alert) {
    if (container.querySelector('.muted')) {
        container.innerHTML = '';
    }
    const item = document.createElement('div');
    item.className = 'alert-item';
    item.innerHTML = `
        <div class="alert-node">${escapeHtml(alert.node_name)} — ${escapeHtml(alert.alert_type)}</div>
        <div class="alert-coords">${alert.lat.toFixed(6)}, ${alert.lon.toFixed(6)}</div>
        <div class="alert-time">${new Date(alert.timestamp).toLocaleString()}</div>
    `;
    container.appendChild(item);
}


// ── Toast Notifications ──
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('hide');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}


// ── Alert Sound ──
function playAlertSound() {
    if (!alertAudio) return;
    try {
        const oscillator = alertAudio.createOscillator();
        const gainNode = alertAudio.createGain();
        oscillator.connect(gainNode);
        gainNode.connect(alertAudio.destination);
        oscillator.frequency.value = 800;
        oscillator.type = 'square';
        gainNode.gain.value = 0.1;
        oscillator.start();
        oscillator.stop(alertAudio.currentTime + 0.3);
    } catch (e) {
        // Ignore audio errors
    }
}


// ── Fence Drawing UI ──
function onDrawFence() {
    startDrawing();
    document.getElementById('btn-draw-fence').style.display = 'none';
    document.getElementById('btn-clear-fence').style.display = '';
    document.getElementById('btn-save-fence').style.display = '';
    showToast('Click on the map to draw fence vertices. Click "Save Fence" when done.');
}


function onClearFence() {
    cancelDrawing();
    document.getElementById('btn-draw-fence').style.display = '';
    document.getElementById('btn-clear-fence').style.display = 'none';
    document.getElementById('btn-save-fence').style.display = 'none';
}


async function onSaveFence() {
    const vertices = finishDrawing();

    document.getElementById('btn-draw-fence').style.display = '';
    document.getElementById('btn-clear-fence').style.display = 'none';
    document.getElementById('btn-save-fence').style.display = 'none';

    if (!vertices) {
        showToast('Need at least 3 points to create a fence.');
        return;
    }

    const resp = await fetch('/api/fence', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vertices }),
    });

    if (resp.ok) {
        showToast('Fence saved successfully!');
        document.getElementById('btn-start-monitoring').disabled = false;
    } else {
        showToast('Failed to save fence.');
    }
}


// ── Monitoring UI ──
function setMonitoringUI(active) {
    isMonitoring = active;
    const startBtn = document.getElementById('btn-start-monitoring');
    const stopBtn = document.getElementById('btn-stop-monitoring');
    const drawBtn = document.getElementById('btn-draw-fence');

    if (active) {
        startBtn.style.display = 'none';
        stopBtn.style.display = '';
        drawBtn.disabled = true;
    } else {
        startBtn.style.display = '';
        stopBtn.style.display = 'none';
        drawBtn.disabled = false;
    }
}


async function onStartMonitoring() {
    const resp = await fetch('/api/monitoring/start', { method: 'POST' });
    const data = await resp.json();

    if (data.status === 'error') {
        showToast(data.message);
        return;
    }

    // Clear alert list in UI
    alertCount = 0;
    document.getElementById('alert-count').textContent = '0';
    document.getElementById('alert-list').innerHTML = '<p class="muted">No alerts yet</p>';

    setMonitoringUI(true);
    showToast('Monitoring started — watching for fence breaches.');
}


async function onStopMonitoring() {
    await fetch('/api/monitoring/stop', { method: 'POST' });
    setMonitoringUI(false);
    showToast('Monitoring stopped.');
}


// ── Utility ──
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
