/* ═══════════════════════════════════════════════════════════
   Comtech CEL-AC 3 Simulator — Admin Panel Logic
   ═══════════════════════════════════════════════════════════ */

let ADMIN_PWD = '';
let refreshInterval = null;
let adminWs = null;

// ── API Helper ─────────────────────────────────────────────

async function adminApi(path, opts = {}) {
    const headers = {
        'Content-Type': 'application/json',
        'X-Admin-Password': ADMIN_PWD,
        ...opts.headers,
    };
    const resp = await fetch(path, { ...opts, headers });
    if (resp.status === 401) {
        toast('Сессия истекла — войдите заново', 'error');
        showLogin();
        throw new Error('Unauthorized');
    }
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    // Handle CSV/blob responses
    const ct = resp.headers.get('content-type') || '';
    if (ct.includes('text/csv')) return resp;
    return resp.json();
}

// ── Auth ───────────────────────────────────────────────────

async function adminAuth(e) {
    e.preventDefault();
    const pwd = document.getElementById('adminPassword').value;
    const errEl = document.getElementById('adminError');
    errEl.style.display = 'none';

    try {
        ADMIN_PWD = pwd;
        await adminApi('/api/admin/students');
        // Success — show panel
        document.getElementById('adminLogin').style.display = 'none';
        document.getElementById('adminPanel').style.display = 'flex';
        sessionStorage.setItem('admin_pwd', pwd);
        initAdmin();
    } catch (err) {
        errEl.textContent = 'Неверный пароль';
        errEl.style.display = 'block';
        ADMIN_PWD = '';
    }
    return false;
}

function showLogin() {
    document.getElementById('adminPanel').style.display = 'none';
    document.getElementById('adminLogin').style.display = 'flex';
    sessionStorage.removeItem('admin_pwd');
    ADMIN_PWD = '';
    if (refreshInterval) clearInterval(refreshInterval);
}

// Auto-login if password saved in session
document.addEventListener('DOMContentLoaded', () => {
    const saved = sessionStorage.getItem('admin_pwd');
    if (saved) {
        ADMIN_PWD = saved;
        adminApi('/api/admin/students').then(() => {
            document.getElementById('adminLogin').style.display = 'none';
            document.getElementById('adminPanel').style.display = 'flex';
            initAdmin();
        }).catch(() => {
            sessionStorage.removeItem('admin_pwd');
            ADMIN_PWD = '';
        });
    }
});

function initAdmin() {
    refreshStudents();
    loadReference();
    loadSettings();
    loadHelpText();
    connectAdminWS();
    // Fallback polling every 10 seconds (WS handles instant updates)
    if (refreshInterval) clearInterval(refreshInterval);
    refreshInterval = setInterval(refreshStudents, 10000);
}

// ── Admin WebSocket ────────────────────────────────────────

function connectAdminWS() {
    if (adminWs && adminWs.readyState === WebSocket.OPEN) return;

    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    adminWs = new WebSocket(`${proto}//${location.host}/ws/admin`);

    adminWs.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleAdminWSMessage(msg);
        } catch { /* ignore */ }
    };

    adminWs.onclose = () => {
        setTimeout(connectAdminWS, 5000);
    };

    adminWs.onerror = () => {
        adminWs.close();
    };
}

function handleAdminWSMessage(msg) {
    if (msg.type === 'heartbeat') {
        if (adminWs && adminWs.readyState === WebSocket.OPEN) {
            adminWs.send(JSON.stringify({ type: 'ping' }));
        }
    } else if (msg.type === 'student_connected') {
        toast('Студент подключился', 'success');
        refreshStudents();
    } else if (msg.type === 'student_disconnected') {
        toast('Студент отключился', '');
        refreshStudents();
    } else if (msg.type === 'student_updated') {
        // Silently refresh the list (student saved config or pinged)
        refreshStudents();
    }
}

// ── Sidebar Navigation ─────────────────────────────────────

function showSection(name) {
    document.querySelectorAll('.admin-section').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.sidebar-nav button').forEach(btn => btn.classList.remove('active'));

    document.getElementById(`section-${name}`).style.display = '';
    document.querySelector(`[data-section="${name}"]`).classList.add('active');

    // Hide student detail when switching away
    if (name !== 'students') hideDetail();
}

// ── Students ───────────────────────────────────────────────

async function refreshStudents() {
    try {
        const students = await adminApi('/api/admin/students');
        document.getElementById('studentCount').textContent = students.length;
        renderStudentTable(students);
    } catch (err) {
        // silent on refresh errors
    }
}

function renderStudentTable(students) {
    const tbody = document.getElementById('studentsBody');
    if (!students.length) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#4a5a7a;padding:40px">Нет подключённых студентов</td></tr>';
        return;
    }

    tbody.innerHTML = students.map(s => {
        const pct = s.correct_percentage;
        const fillClass = pct >= 80 ? 'high' : pct >= 40 ? 'mid' : 'low';
        const statusClass = s.status;
        const connTime = formatTime(s.connection_time);
        const lastAct = formatTime(s.last_activity);

        return `<tr onclick="showStudentDetail('${s.session_id}')">
            <td>${esc(s.student_name)}</td>
            <td>${esc(s.student_group)}</td>
            <td><span class="status-pill ${statusClass}">${s.status}</span></td>
            <td>
                <div class="progress-bar"><div class="fill ${fillClass}" style="width:${pct}%"></div></div>
                <span style="font-size:12px;color:#8b9cc0">${pct}%</span>
            </td>
            <td style="font-size:12px;color:#6b7a99">${connTime}</td>
            <td style="font-size:12px;color:#6b7a99">${lastAct}</td>
            <td>
                <button class="btn btn-secondary" style="padding:4px 10px;font-size:11px" onclick="event.stopPropagation();resetStudent('${s.session_id}')">Reset</button>
                <button class="btn btn-danger" style="padding:4px 10px;font-size:11px" onclick="event.stopPropagation();kickStudent('${s.session_id}')">Kick</button>
            </td>
        </tr>`;
    }).join('');
}

// ── Student Detail ─────────────────────────────────────────

async function showStudentDetail(sessionId) {
    try {
        const data = await adminApi(`/api/admin/student/${sessionId}`);
        const s = data.session;
        const v = data.validation;

        document.getElementById('detailName').textContent = s.student_name;
        document.getElementById('detailGroup').textContent = `Группа: ${s.student_group}`;
        document.getElementById('detailStatus').innerHTML = `<span class="status-pill ${s.status}">${s.status}</span>`;

        document.getElementById('detailPercent').textContent = `${v.percentage}%`;
        document.getElementById('detailPercent').style.color = v.percentage >= 80 ? '#4ade80' : v.percentage >= 40 ? '#fbbf24' : '#f87171';
        document.getElementById('detailCorrectCount').textContent = `${v.correct_count} / ${v.total_count} параметров верно`;

        document.getElementById('detailSiteOk').innerHTML = boolBadge(v.site_correct);
        document.getElementById('detailRfOk').innerHTML = boolBadge(v.rf_correct);
        document.getElementById('detailSearchOk').innerHTML = boolBadge(v.search_id_correct);
        document.getElementById('detailProfileOk').innerHTML = boolBadge(v.profile_correct);
        document.getElementById('detailLoss').textContent = `${v.loss_percent}%`;
        document.getElementById('detailLoss').style.color = v.loss_percent === 0 ? '#4ade80' : '#f87171';

        // Config comparison table
        renderConfigCompare(v.details);

        // Console history
        renderConsoleHistory(data.console_history);

        document.getElementById('studentList').style.display = 'none';
        document.getElementById('studentDetail').style.display = 'block';
    } catch (err) {
        toast('Ошибка загрузки данных студента: ' + err.message, 'error');
    }
}

function hideDetail() {
    document.getElementById('studentDetail').style.display = 'none';
    document.getElementById('studentList').style.display = 'block';
}

function renderConfigCompare(details) {
    const tbody = document.getElementById('configCompareBody');
    let currentCat = '';
    const catNames = { site: 'Site', rf: 'RF Interface', search_id: 'Search / ID', profile: 'Profile' };

    tbody.innerHTML = details.map(d => {
        let catRow = '';
        if (d.category !== currentCat) {
            currentCat = d.category;
            catRow = `<tr class="category-row"><td colspan="4">${catNames[d.category] || d.category}</td></tr>`;
        }
        const statusIcon = d.is_correct ? '&#10003;' : '&#10007;';
        const statusColor = d.is_correct ? '#4ade80' : '#f87171';
        const valClass = d.is_correct ? 'correct' : 'incorrect';
        const tolStr = d.tolerance ? ` <span style="color:#4a5a7a;font-size:11px">(${d.tolerance})</span>` : '';

        return `${catRow}<tr>
            <td class="param-name">${formatParamName(d.name)}${tolStr}</td>
            <td class="${valClass}">${esc(d.student_value)}</td>
            <td class="ref-val">${esc(d.reference_value)}</td>
            <td style="color:${statusColor};text-align:center;font-size:16px">${statusIcon}</td>
        </tr>`;
    }).join('');
}

function renderConsoleHistory(history) {
    const el = document.getElementById('detailConsole');
    if (!history.length) {
        el.textContent = 'Команды пока не выполнялись.';
        return;
    }
    el.innerHTML = history.map(h =>
        `<div><span class="hist-time">[${formatTime(h.timestamp)}]</span> <span class="hist-cmd">CEL-AC3&gt; ${esc(h.command)}</span></div><div>${esc(h.output)}</div><br>`
    ).join('');
}

// ── Student Actions ────────────────────────────────────────

async function resetStudent(sessionId) {
    if (!confirm('Сбросить конфигурацию студента к значениям по умолчанию?')) return;
    try {
        await adminApi(`/api/admin/student/${sessionId}/reset`, { method: 'POST' });
        toast('Конфигурация студента сброшена', 'success');
        refreshStudents();
    } catch (err) {
        toast('Ошибка сброса: ' + err.message, 'error');
    }
}

async function kickStudent(sessionId) {
    if (!confirm('Отключить студента? Данные его сессии будут удалены.')) return;
    try {
        await adminApi(`/api/admin/student/${sessionId}`, { method: 'DELETE' });
        toast('Студент отключён', 'success');
        hideDetail();
        refreshStudents();
    } catch (err) {
        toast('Ошибка отключения: ' + err.message, 'error');
    }
}

// ── Reference Config ───────────────────────────────────────

async function loadReference() {
    try {
        const data = await adminApi('/api/admin/reference');
        populateReference(data);
    } catch (err) {
        console.error('Failed to load reference:', err);
    }
}

function populateReference(config) {
    const s = config.site;
    const r = config.rf;
    const si = config.search_id;
    const p = config.profile;

    setV('ref_site_name', s.site_name);
    setV('ref_latitude_deg', s.latitude_deg);
    setV('ref_latitude_min', s.latitude_min);
    setV('ref_latitude_dir', s.latitude_dir);
    setV('ref_longitude_deg', s.longitude_deg);
    setV('ref_longitude_min', s.longitude_min);
    setV('ref_longitude_dir', s.longitude_dir);

    setV('ref_rx1_lo', r.rx1_lo);
    setV('ref_rx2_lo', r.rx2_lo);
    setV('ref_tx_lo', r.tx_lo);
    setV('ref_rx_power', r.rx_power ? '1' : '0');
    setV('ref_rx_10mhz', r.rx_10mhz ? '1' : '0');
    setV('ref_rx1_spinv', r.rx1_spinv ? '1' : '0');
    setV('ref_rx2_spinv', r.rx2_spinv ? '1' : '0');
    setV('ref_tx_spinv', r.tx_spinv ? '1' : '0');
    setV('ref_rx1_freq_adj', r.rx1_freq_adj);
    setV('ref_rx2_freq_adj', r.rx2_freq_adj);
    setV('ref_tx_freq_adj', r.tx_freq_adj);
    setV('ref_tx_power', r.tx_power ? '1' : '0');

    setV('ref_search_bw_scpc', si.search_bw_scpc);
    setV('ref_search_bw_tdma', si.search_bw_tdma);
    setV('ref_net_id', si.net_id);
    setV('ref_rf_id', si.rf_id);
    setV('ref_far_end_cn', si.far_end_cn);

    setV('ref_active_profile', p.active_profile);
    setV('ref_profile_mode', p.profile_mode);
    setV('ref_profile_autorun', p.profile_autorun ? '1' : '0');
    setV('ref_profile_timeout', p.profile_timeout);
}

function collectReference() {
    return {
        site: {
            site_name: gV('ref_site_name') || 'AC 3',
            latitude_deg: parseInt(gV('ref_latitude_deg')) || 0,
            latitude_min: parseInt(gV('ref_latitude_min')) || 0,
            latitude_dir: gV('ref_latitude_dir') || 'N',
            longitude_deg: parseInt(gV('ref_longitude_deg')) || 0,
            longitude_min: parseInt(gV('ref_longitude_min')) || 0,
            longitude_dir: gV('ref_longitude_dir') || 'E',
        },
        rf: {
            rx1_lo: parseInt(gV('ref_rx1_lo')) || 0,
            rx2_lo: parseInt(gV('ref_rx2_lo')) || 0,
            tx_lo: parseInt(gV('ref_tx_lo')) || 0,
            rx_power: gV('ref_rx_power') === '1',
            rx_10mhz: gV('ref_rx_10mhz') === '1',
            rx1_spinv: gV('ref_rx1_spinv') === '1',
            rx2_spinv: gV('ref_rx2_spinv') === '1',
            tx_spinv: gV('ref_tx_spinv') === '1',
            rx1_freq_adj: parseInt(gV('ref_rx1_freq_adj')) || 0,
            rx2_freq_adj: parseInt(gV('ref_rx2_freq_adj')) || 0,
            tx_freq_adj: parseInt(gV('ref_tx_freq_adj')) || 0,
            tx_power: gV('ref_tx_power') === '1',
        },
        search_id: {
            search_bw_scpc: parseInt(gV('ref_search_bw_scpc')) || 1800,
            search_bw_tdma: parseInt(gV('ref_search_bw_tdma')) || 12,
            net_id: parseInt(gV('ref_net_id')) || 0,
            rf_id: parseInt(gV('ref_rf_id')) || 0,
            far_end_cn: parseInt(gV('ref_far_end_cn')) || 0,
        },
        profile: {
            active_profile: parseInt(gV('ref_active_profile')) || 1,
            profile_mode: gV('ref_profile_mode') || 'none',
            profile_autorun: gV('ref_profile_autorun') === '1',
            profile_timeout: parseInt(gV('ref_profile_timeout')) || 10,
        }
    };
}

async function saveReference() {
    try {
        const config = collectReference();
        await adminApi('/api/admin/reference', {
            method: 'POST',
            body: JSON.stringify(config),
        });
        toast('Эталонная конфигурация сохранена', 'success');
    } catch (err) {
        toast('Ошибка сохранения: ' + err.message, 'error');
    }
}

function exportReference() {
    const config = collectReference();
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'comtech_reference_config.json';
    a.click();
    URL.revokeObjectURL(url);
    toast('Эталон экспортирован', 'success');
}

function importReference() {
    document.getElementById('jsonFileInput').click();
}

function handleImportFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function (ev) {
        try {
            const config = JSON.parse(ev.target.result);
            populateReference(config);
            toast('Конфигурация импортирована — нажмите «Сохранить эталон»', 'success');
        } catch {
            toast('Некорректный JSON-файл', 'error');
        }
    };
    reader.readAsText(file);
    e.target.value = '';
}

// ── Settings ───────────────────────────────────────────────

async function loadSettings() {
    try {
        const data = await adminApi('/api/admin/settings');
        document.getElementById('set_partial_mode').checked = data.partial_mode;
        document.getElementById('set_partial_mode_label').textContent = data.partial_mode ? 'Включён' : 'Выключен';
        document.getElementById('set_registration').checked = data.registration_open;
        document.getElementById('set_registration_label').textContent = data.registration_open ? 'Открыта' : 'Закрыта';

        // Toggle label listeners
        document.getElementById('set_partial_mode').onchange = function () {
            document.getElementById('set_partial_mode_label').textContent = this.checked ? 'Включён' : 'Выключен';
        };
        document.getElementById('set_registration').onchange = function () {
            document.getElementById('set_registration_label').textContent = this.checked ? 'Открыта' : 'Закрыта';
        };
    } catch (err) {
        console.error('Failed to load settings:', err);
    }
}

async function saveSettings() {
    try {
        const body = {
            partial_mode: document.getElementById('set_partial_mode').checked,
            registration_open: document.getElementById('set_registration').checked,
        };
        const pwd = document.getElementById('set_password').value.trim();
        if (pwd) {
            body.admin_password = pwd;
            ADMIN_PWD = pwd;
            sessionStorage.setItem('admin_pwd', pwd);
        }
        await adminApi('/api/admin/settings', {
            method: 'POST',
            body: JSON.stringify(body),
        });
        document.getElementById('set_password').value = '';
        toast('Настройки сохранены', 'success');
    } catch (err) {
        toast('Ошибка сохранения: ' + err.message, 'error');
    }
}

// ── Help Text ──────────────────────────────────────────────

async function loadHelpText() {
    try {
        const data = await adminApi('/api/admin/help-text');
        document.getElementById('helpTextArea').value = data.help_text || '';
    } catch (err) {
        console.error('Failed to load help text:', err);
    }
}

async function saveHelpText() {
    try {
        await adminApi('/api/admin/help-text', {
            method: 'POST',
            body: JSON.stringify({ help_text: document.getElementById('helpTextArea').value }),
        });
        toast('Инструкции сохранены', 'success');
    } catch (err) {
        toast('Ошибка сохранения: ' + err.message, 'error');
    }
}

// ── CSV Export ──────────────────────────────────────────────

async function exportCSV() {
    try {
        const resp = await adminApi('/api/admin/export');
        const text = await resp.text();
        const blob = new Blob([text], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'comtech_results.csv';
        a.click();
        URL.revokeObjectURL(url);
        toast('Результаты экспортированы', 'success');
    } catch (err) {
        toast('Ошибка экспорта: ' + err.message, 'error');
    }
}

// ── Utilities ──────────────────────────────────────────────

function setV(id, val) { const el = document.getElementById(id); if (el) el.value = val; }
function gV(id) { const el = document.getElementById(id); return el ? el.value : ''; }

function esc(str) {
    const d = document.createElement('div');
    d.textContent = String(str);
    return d.innerHTML;
}

function formatTime(iso) {
    if (!iso) return '—';
    try {
        const d = new Date(iso);
        return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
        return iso;
    }
}

function formatParamName(name) {
    return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function boolBadge(ok) {
    if (ok) return '<span style="color:#4ade80">&#10003; OK</span>';
    return '<span style="color:#f87171">&#10007; Failed</span>';
}

function toast(message, type = '') {
    const el = document.getElementById('toast');
    el.textContent = message;
    el.className = 'toast show ' + type;
    setTimeout(() => { el.className = 'toast'; }, 3000);
}
