/* ═══════════════════════════════════════════════════════════
   VSAT Terminal Simulator — Client Application
   ═══════════════════════════════════════════════════════════ */

const API = '';  // same origin
let SESSION_ID = null;
let ws = null;
let uptimeStart = null;
let uptimeTimer = null;
let commandHistory = [];
let historyIndex = -1;
let isCommandRunning = false;

// ── Initialization ─────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    SESSION_ID = sessionStorage.getItem('session_id');
    if (!SESSION_ID) {
        window.location.href = '/';
        return;
    }

    document.getElementById('headerName').textContent = sessionStorage.getItem('student_name') || '—';
    document.getElementById('headerGroup').textContent = sessionStorage.getItem('student_group') || '—';

    loadSession();
    loadHelpText();
    setupConsoleInput();
    setupToggleListeners();
    connectWebSocket();
});

// ── API Helpers ────────────────────────────────────────────

async function api(path, opts = {}) {
    const resp = await fetch(API + path, {
        headers: { 'Content-Type': 'application/json', ...opts.headers },
        ...opts,
    });
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    return resp.json();
}

// ── Session Loading ────────────────────────────────────────

async function loadSession() {
    try {
        const data = await api(`/api/session/${SESSION_ID}`);
        populateForm(data.config);
        uptimeStart = new Date(data.connection_time);
        startUptime();
        updateStatusDisplay(data.status);
        refreshLEDs();
    } catch (err) {
        console.error('Failed to load session:', err);
        // Session expired — go back to login
        sessionStorage.clear();
        window.location.href = '/';
    }
}

function populateForm(config) {
    const sat = config.satellite;
    const net = config.network;
    const ant = config.antenna;

    // Satellite
    setVal('rx_frequency', sat.rx_frequency || '');
    setVal('tx_frequency', sat.tx_frequency || '');
    setVal('symbol_rate', sat.symbol_rate || '');
    setVal('modulation', sat.modulation);
    setVal('fec_rate', sat.fec_rate);
    setVal('polarization', sat.polarization);
    document.getElementById('carrier_state').checked = sat.carrier_state === 'UNMUTED';
    updateToggleLabel('carrier_state', 'UNMUTED', 'MUTED');
    setVal('roll_off', sat.roll_off);

    // Network
    setVal('ip_address', net.ip_address);
    setVal('subnet_mask', net.subnet_mask);
    setVal('gateway', net.gateway);
    setVal('dns_server', net.dns_server);
    document.getElementById('dhcp_mode').checked = net.dhcp_mode === 'Enabled';
    updateToggleLabel('dhcp_mode', 'Enabled', 'Disabled');
    setVal('vlan_id', net.vlan_id);
    setVal('mtu', net.mtu);

    // Antenna
    setVal('azimuth', ant.azimuth || '');
    setVal('elevation', ant.elevation || '');
    setVal('lnb_skew', ant.lnb_skew || '');
    setVal('lnb_frequency', ant.lnb_frequency || '');
    document.getElementById('buc_power').checked = ant.buc_power === 'Enabled';
    updateToggleLabel('buc_power', 'Enabled', 'Disabled');
    setVal('antenna_size', ant.antenna_size);
}

function setVal(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value;
}

function collectConfig() {
    return {
        satellite: {
            rx_frequency: parseFloat(document.getElementById('rx_frequency').value) || 0,
            tx_frequency: parseFloat(document.getElementById('tx_frequency').value) || 0,
            symbol_rate: parseFloat(document.getElementById('symbol_rate').value) || 0,
            modulation: document.getElementById('modulation').value,
            fec_rate: document.getElementById('fec_rate').value,
            polarization: document.getElementById('polarization').value,
            carrier_state: document.getElementById('carrier_state').checked ? 'UNMUTED' : 'MUTED',
            roll_off: parseFloat(document.getElementById('roll_off').value),
        },
        network: {
            ip_address: document.getElementById('ip_address').value || '0.0.0.0',
            subnet_mask: document.getElementById('subnet_mask').value || '0.0.0.0',
            gateway: document.getElementById('gateway').value || '0.0.0.0',
            dns_server: document.getElementById('dns_server').value || '0.0.0.0',
            dhcp_mode: document.getElementById('dhcp_mode').checked ? 'Enabled' : 'Disabled',
            vlan_id: parseInt(document.getElementById('vlan_id').value) || 1,
            mtu: parseInt(document.getElementById('mtu').value) || 1500,
        },
        antenna: {
            azimuth: parseFloat(document.getElementById('azimuth').value) || 0,
            elevation: parseFloat(document.getElementById('elevation').value) || 0,
            lnb_skew: parseFloat(document.getElementById('lnb_skew').value) || 0,
            lnb_frequency: parseFloat(document.getElementById('lnb_frequency').value) || 9750,
            buc_power: document.getElementById('buc_power').checked ? 'Enabled' : 'Disabled',
            antenna_size: parseFloat(document.getElementById('antenna_size').value) || 1.2,
        }
    };
}

// ── Save / Reset ───────────────────────────────────────────

async function saveConfig() {
    const status = document.getElementById('saveStatus');
    const applyBtn = document.querySelector('.action-bar .btn-primary');
    try {
        status.textContent = 'Сохранение...';
        status.className = 'status-text';
        if (applyBtn) { applyBtn.disabled = true; applyBtn.textContent = 'Сохранение...'; }
        const config = collectConfig();
        await api(`/api/session/${SESSION_ID}/config`, {
            method: 'POST',
            body: JSON.stringify(config),
        });
        status.textContent = 'Конфигурация сохранена';
        status.className = 'status-text saved';
        refreshLEDs();
        setTimeout(() => {
            status.textContent = 'Готово';
            status.className = 'status-text';
        }, 3000);
    } catch (err) {
        status.textContent = 'Ошибка сохранения: ' + err.message;
        status.className = 'status-text';
    } finally {
        if (applyBtn) { applyBtn.disabled = false; applyBtn.textContent = 'Применить конфигурацию'; }
    }
}

async function resetConfig() {
    if (!confirm('Сбросить все параметры к заводским настройкам?')) return;
    try {
        await api(`/api/session/${SESSION_ID}/reset`, { method: 'POST' });
        await loadSession();
        document.getElementById('saveStatus').textContent = 'Сброшено к заводским настройкам';
        document.getElementById('saveStatus').className = 'status-text saved';
    } catch (err) {
        alert('Ошибка сброса: ' + err.message);
    }
}

// ── LED Updates ────────────────────────────────────────────

async function refreshLEDs() {
    try {
        const data = await api(`/api/session/${SESSION_ID}/status`);
        updateLEDs(data);
    } catch (err) {
        console.error('LED refresh failed:', err);
    }
}

function updateLEDs(data) {
    setLED('led-power', data.power_led);
    setLED('led-rx', data.rx_led);
    setLED('led-tx', data.tx_led);
    setLED('led-network', data.network_led);
    setLED('led-lan', data.lan_led);

    // Status badge
    const badge = document.getElementById('statusBadge');
    badge.textContent = data.system_status;
    badge.className = 'status-badge';
    if (data.system_status === 'Online') badge.classList.add('online');
    else if (data.system_status === 'Offline') badge.classList.add('offline');
    else badge.classList.add('configuring');

    document.getElementById('dashStatus').textContent = data.system_status;

    // Signal meter
    const meter = document.getElementById('signalMeter');
    meter.className = 'signal-meter';
    if (data.system_status === 'Online') meter.classList.add('active');
    else if (data.rx_led === 'yellow' || data.tx_led === 'yellow') meter.classList.add('partial');
}

function setLED(id, color) {
    const el = document.getElementById(id);
    if (el) {
        el.className = 'led ' + color;
    }
}

// ── Tab Navigation ─────────────────────────────────────────

function switchTab(tabName) {
    // Deactivate all tabs
    document.querySelectorAll('.tab-nav button').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

    // Activate selected
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(`tab-${tabName}`).classList.add('active');

    // Focus console input when switching to console tab
    if (tabName === 'console') {
        setTimeout(() => document.getElementById('consoleInput').focus(), 100);
    }
}

// ── Console ────────────────────────────────────────────────

function setupConsoleInput() {
    const input = document.getElementById('consoleInput');
    input.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const cmd = input.value.trim();
            if (!cmd || isCommandRunning) return;

            commandHistory.push(cmd);
            historyIndex = commandHistory.length;
            input.value = '';

            appendToConsole(cmd, 'cmd');

            isCommandRunning = true;
            input.disabled = true;
            input.placeholder = 'Выполнение...';

            // Auto-save config before ping
            if (cmd.toLowerCase().startsWith('ping')) {
                try {
                    const config = collectConfig();
                    await api(`/api/session/${SESSION_ID}/config`, {
                        method: 'POST',
                        body: JSON.stringify(config),
                    });
                } catch (_) { /* ignore */ }
            }

            try {
                const data = await api(`/api/session/${SESSION_ID}/command`, {
                    method: 'POST',
                    body: JSON.stringify({ command: cmd }),
                });
                if (data.output) {
                    typeOutput(data.output, () => {
                        isCommandRunning = false;
                        input.disabled = false;
                        input.placeholder = 'Введите команду...';
                        input.focus();
                    });
                } else {
                    isCommandRunning = false;
                    input.disabled = false;
                    input.placeholder = 'Введите команду...';
                    input.focus();
                }
                // Refresh LEDs after ping
                if (cmd.toLowerCase().startsWith('ping')) {
                    setTimeout(refreshLEDs, 200);
                }
            } catch (err) {
                appendToConsole(err.message, 'error');
                isCommandRunning = false;
                input.disabled = false;
                input.placeholder = 'Введите команду...';
                input.focus();
            }
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (historyIndex > 0) {
                historyIndex--;
                input.value = commandHistory[historyIndex];
            }
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (historyIndex < commandHistory.length - 1) {
                historyIndex++;
                input.value = commandHistory[historyIndex];
            } else {
                historyIndex = commandHistory.length;
                input.value = '';
            }
        }
    });
}

function appendToConsole(text, type) {
    const output = document.getElementById('consoleOutput');
    const line = document.createElement('div');

    if (type === 'cmd') {
        line.innerHTML = `<span class="cmd-prompt">VSAT-Terminal&gt;</span> <span class="cmd-line">${escapeHtml(text)}</span>`;
    } else if (type === 'error') {
        line.className = 'cmd-error';
        line.textContent = text;
    } else {
        line.className = 'cmd-output';
        line.textContent = text;
    }

    output.appendChild(line);
    output.scrollTop = output.scrollHeight;
}

function typeOutput(text, onComplete) {
    const output = document.getElementById('consoleOutput');
    const container = document.createElement('div');
    container.className = 'cmd-output';
    output.appendChild(container);

    // Split into lines for line-by-line typing with per-line delay
    const lines = text.split('\n');
    let lineIdx = 0;

    function typeLine() {
        if (lineIdx >= lines.length) {
            if (onComplete) onComplete();
            return;
        }

        const line = lines[lineIdx];
        lineIdx++;

        // Type each line character by character
        let charIdx = 0;
        function typeChar() {
            if (charIdx < line.length) {
                // Batch 3 chars per frame for natural speed
                const batch = Math.min(3, line.length - charIdx);
                for (let j = 0; j < batch; j++) {
                    container.textContent += line[charIdx++];
                }
                output.scrollTop = output.scrollHeight;
                setTimeout(typeChar, 8);
            } else {
                // End of line — add newline and start next line with delay
                if (lineIdx < lines.length) {
                    container.textContent += '\n';
                }
                output.scrollTop = output.scrollHeight;
                // Simulate satellite delay between ping reply lines
                const delay = line.startsWith('Reply') || line.startsWith('Request') ? 120 : 30;
                setTimeout(typeLine, delay);
            }
        }
        typeChar();
    }
    typeLine();
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ── Toggle Listeners ───────────────────────────────────────

function setupToggleListeners() {
    document.getElementById('carrier_state').addEventListener('change', function () {
        updateToggleLabel('carrier_state', 'UNMUTED', 'MUTED');
    });
    document.getElementById('dhcp_mode').addEventListener('change', function () {
        updateToggleLabel('dhcp_mode', 'Enabled', 'Disabled');
    });
    document.getElementById('buc_power').addEventListener('change', function () {
        updateToggleLabel('buc_power', 'Enabled', 'Disabled');
    });
}

function updateToggleLabel(id, onText, offText) {
    const checkbox = document.getElementById(id);
    const label = document.getElementById(id + '_label');
    if (label) {
        label.textContent = checkbox.checked ? onText : offText;
    }
}

// ── Help Bar ───────────────────────────────────────────────

function renderMarkdown(md) {
    // Lightweight Markdown → HTML (no external deps)
    let html = escapeHtml(md);
    // Horizontal rules
    html = html.replace(/^---$/gm, '<hr>');
    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Tables: detect header + separator + rows
    html = html.replace(/((?:^\|.+\|$\n?)+)/gm, function(block) {
        const rows = block.trim().split('\n').filter(r => r.trim());
        if (rows.length < 2) return block;
        // Skip separator row (|---|---|)
        const isSep = r => /^\|[\s\-|]+\|$/.test(r);
        let out = '<table>';
        let inHead = true;
        for (const row of rows) {
            if (isSep(row)) { inHead = false; continue; }
            const cells = row.split('|').filter((_, i, a) => i > 0 && i < a.length - 1);
            const tag = inHead ? 'th' : 'td';
            out += '<tr>' + cells.map(c => `<${tag}>${c.trim()}</${tag}>`).join('') + '</tr>';
            if (inHead) inHead = false;
        }
        return out + '</table>';
    });
    // List items (unordered)
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/((?:<li>.+<\/li>\n?)+)/g, '<ul>$1</ul>');
    // Numbered lists
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
    // Wrap remaining lines in paragraphs (skip tags)
    html = html.split('\n').map(line => {
        const trimmed = line.trim();
        if (!trimmed) return '';
        if (/^<[a-z]/.test(trimmed)) return line;
        return `<p>${line}</p>`;
    }).join('\n');
    return html;
}

async function loadHelpText() {
    try {
        const data = await api('/api/help-text');
        const text = data.help_text || 'Инструкции не загружены.';
        document.getElementById('helpContent').innerHTML = renderMarkdown(text);
    } catch {
        document.getElementById('helpContent').textContent = 'Здесь появятся инструкции по работе с лабораторией.';
    }
}

function toggleHelp() {
    const bar = document.getElementById('helpBar');
    const btn = document.getElementById('helpToggle');
    bar.classList.toggle('expanded');
    btn.classList.toggle('active');
}

// ── Uptime Timer ───────────────────────────────────────────

function startUptime() {
    if (uptimeTimer) clearInterval(uptimeTimer);
    uptimeTimer = setInterval(updateUptime, 1000);
    updateUptime();
}

function updateUptime() {
    if (!uptimeStart) return;
    const elapsed = Math.floor((Date.now() - new Date(uptimeStart).getTime()) / 1000);
    const h = String(Math.floor(elapsed / 3600)).padStart(2, '0');
    const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0');
    const s = String(elapsed % 60).padStart(2, '0');
    const str = `${h}:${m}:${s}`;
    document.getElementById('headerUptime').textContent = str;
    document.getElementById('dashUptime').textContent = str;
}

// ── WebSocket ──────────────────────────────────────────────

function connectWebSocket() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${proto}//${location.host}/ws/${SESSION_ID}`;

    ws = new WebSocket(url);

    ws.onopen = () => {
        const ind = document.getElementById('wsIndicator');
        if (ind) { ind.classList.add('connected'); ind.title = 'Подключён к серверу'; }
    };

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleWSMessage(msg);
        } catch { /* ignore */ }
    };

    ws.onclose = () => {
        const ind = document.getElementById('wsIndicator');
        if (ind) { ind.classList.remove('connected'); ind.title = 'Отключён — переподключение...'; }
        setTimeout(connectWebSocket, 5000);
    };

    ws.onerror = () => {
        ws.close();
    };
}

function handleWSMessage(msg) {
    if (msg.type === 'heartbeat') {
        // Respond with ping to keep alive
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
        }
    } else if (msg.type === 'status_update') {
        updateLEDs(msg.data);
    } else if (msg.type === 'ping_result') {
        refreshLEDs();
    }
}

// ── Status Display ─────────────────────────────────────────

function updateStatusDisplay(status) {
    const dashStatus = document.getElementById('dashStatus');
    if (dashStatus) {
        const map = {
            'configuring': 'Настройка',
            'testing': 'Тестирование',
            'completed': 'Завершено',
            'disconnected': 'Отключён',
        };
        dashStatus.textContent = map[status] || status;
    }
}
