// =============================================================================
// Comtech CEL-AC 3 — Исправленная версия с отладкой
// =============================================================================

console.log('=== comtech.js loaded ===');

const SESSION_ID = sessionStorage.getItem('session_id');
console.log('SESSION_ID:', SESSION_ID);

if (!SESSION_ID) {
    console.log('No session, redirecting to login');
    window.location.href = '/';
}

let currentConfig = null;
let ws = null;
let statusTimer = null;

// ── Сопоставление режимов профилей с HTML-файлами ──
const PROFILE_PAGES = {
    'none': 'profile_none.html',
    'SCPC modem': 'profile_scpc_modem.html',
    'Star station': 'profile_star_station.html',
    'Mesh station': 'profile_mesh_station.html',
    'Hubless station': 'profile_hubless_station.html',
    'DAMA station': 'profile_dama_station.html',
    'CrossPol test': 'profile_crosspol_test.html',
    'Star hub': 'profile_star_hub.html',
    'MF hub': 'profile_mf_hub.html',
    'Outroute': 'profile_outroute.html',
    'Inroute': 'profile_inroute.html',
    'MF inroute': 'profile_mf_inroute.html',
    'Hubless master': 'profile_hubless_master.html',
    'DAMA hub': 'profile_dama_hub.html',
    'DAMA inroute': 'profile_dama_inroute.html',
    'Channel simulator': 'profile_channel_sim.html',
    'Spectrum Analyzer': 'profile_spectrum_analyzer.html',
    'Commissioning unit': 'profile_commissioning.html'
};

const PROFILE_MODES = Object.keys(PROFILE_PAGES);

// ── 1. Инициализация ──
async function init() {
    console.log('=== init() called ===');
    console.log('SESSION_ID:', SESSION_ID);
    
    try {
        console.log('Fetching session data...');
        const resp = await fetch('/api/session/' + SESSION_ID);
        console.log('Session response status:', resp.status);
        
        if (!resp.ok) {
            console.error('Session load failed:', resp.status);
            sessionStorage.removeItem('session_id');
            window.location.href = '/';
            return;
        }
        
        const data = await resp.json();
        console.log('Session data loaded:', data);
        currentConfig = data.config || data;
        
        console.log('Setting up WebSocket...');
        setupWebSocket();
        
        console.log('Starting status polling...');
        startStatusPolling();
        
        console.log('Showing overview page...');
        showPage('overview');
        
        console.log('=== init() completed ===');
    } catch (e) {
        console.error('Init failed:', e);
        sessionStorage.removeItem('session_id');
        window.location.href = '/';
    }
}

// ── 2. Навигация ──
function showPage(pageId, stubTitle) {
    console.log('=== showPage ===');
    console.log('pageId:', pageId, 'stubTitle:', stubTitle);
    
    const main = document.getElementById('main');
    if (!main) {
        console.error('main element not found!');
        return;
    }
    console.log('main element found');

    // Обновляем активный пункт в дереве
    document.querySelectorAll('.li-selector').forEach(el => el.classList.remove('active'));
    const links = document.querySelectorAll('#myUL a');
    links.forEach(link => {
        const text = link.textContent.trim();
        if (text === pageId || text === stubTitle || link.getAttribute('data-page') === pageId) {
            const parent = link.closest('.li-selector');
            if (parent) parent.classList.add('active');
        }
    });

    // Загружаем контент
    try {
        console.log('Rendering page:', pageId);
        switch (pageId) {
            case 'overview':
                main.innerHTML = renderOverview();
                break;
            case 'site_setup':
                main.innerHTML = renderSiteSetup();
                break;
            case 'profiles':
                main.innerHTML = renderProfiles();
                break;
            case 'dem1': case 'dem2':
            case 'mod':
            case 'lan1': case 'lan2':
            case 'net':
            case 'sys':
            case 'mon':
                loadPanel(pageId);
                break;
            default:
                main.innerHTML = renderStub(stubTitle || pageId);
        }
        console.log('Page rendered successfully');
    } catch (e) {
        console.error('Error rendering page:', e);
        main.innerHTML = '<div style="padding:20px;color:#ef4444;">Ошибка загрузки страницы: ' + e.message + '</div>';
    }
}

// ── 3. Загрузка статуса ──
function startStatusPolling() {
    console.log('startStatusPolling called');
    if (statusTimer) clearInterval(statusTimer);
    pollStatus();
    statusTimer = setInterval(pollStatus, 5000);
}

async function pollStatus() {
    try {
        const resp = await fetch('/api/session/' + SESSION_ID + '/status');
        if (!resp.ok) return;
        const s = await resp.json();
        applyStatus(s);
    } catch (e) {
        console.error('Status poll error:', e);
    }
}

function applyStatus(s) {
    // Обновляем кнопки статуса
    const panels = {
        lan1: 'Lan1', lan2: 'Lan2',
        dem1: 'Dem1', dem2: 'Dem2',
        mod: 'Mod', net: 'Net',
        sys: 'Sys', mon: 'Mon'
    };
    for (const key in panels) {
        const el = document.getElementById(panels[key]);
        if (el && s[key] !== undefined) {
            el.className = s[key];
        }
    }

    // SysLed
    const sysLed = document.getElementById('SysLed');
    if (sysLed && s.sys_led) {
        sysLed.className = s.sys_led;
    }

    // Имя
    const nameEl = document.getElementById('Name');
    if (nameEl && s.site_name) {
        nameEl.textContent = s.site_name;
    }

    // Профиль
    const profileEl = document.getElementById('Profile');
    if (profileEl) {
        const mode = currentConfig?.profile?.profile_mode || 'none';
        const num = currentConfig?.profile?.active_profile || 1;
        profileEl.textContent = num + '-' + mode;
        profileEl.href = '#';
        profileEl.onclick = function() { showProfileDetail(mode); return false; };
    }

    // Состояние
    const stateEl = document.getElementById('State');
    if (stateEl && s.state !== undefined) {
        stateEl.textContent = s.state;
        stateEl.style.color = s.state_color || '#fe5e37';
        stateEl.style.fontWeight = s.state_weight || '600';
    }

    // Замок
    const lockEl = document.getElementById('StateLock');
    if (lockEl) {
        lockEl.style.visibility = s.state_lock || 'hidden';
    }

    // Иконки
    const saveEl = document.getElementById('SaveCfg');
    if (saveEl && s.cfg) {
        saveEl.className = s.cfg;
    }
    const clearEl = document.getElementById('ClrFaults');
    if (clearEl && s.flt) {
        clearEl.className = s.flt;
    }
}

// ── 4. Overview ──
function renderOverview() {
    console.log('renderOverview called');
    return `
        <table class="ov-header" width="100%">
            <tr>
                <td>SN: <b>20097360</b></td>
                <td>SW: <b>CEL-20X Software</b></td>
                <td>Ver: <b>3.8.1.40</b></td>
            </tr>
        </table>
        <table class="ov-stats" width="100%">
            <tr>
                <td>CPU load: <b>22 %</b></td>
                <td>Buffers: <b>2 %</b></td>
                <td>Temp: <b>62 C</b></td>
                <td>Profile: <b>Down during +00:00:00 (0 runs)</b></td>
            </tr>
        </table>
        <table class="ov-iface" width="100%" border="1" cellpadding="4">
            <tr>
                <th>Interface</th><th>State</th><th>Info</th>
                <th>TX rate (bps)</th><th>RX rate (bps)</th><th>RX errors</th>
            </tr>
            <tr>
                <td><a href="#" onclick="showPage('lan1');return false">Ethernet</a></td>
                <td class="cg"><b>Up</b></td>
                <td>Link: Eth1:1G/FD Eth2:No link</td>
                <td><b>0</b></td><td><b>0</b></td><td><b>0</b></td>
            </tr>
            <tr>
                <td><a href="#" onclick="showPage('dem2');return false">Demodulator-2</a></td>
                <td class="cwd"><b>Disabled</b></td>
                <td>Lvl: <b>- 8.0 dBm</b></td>
                <td><b>-</b></td><td><b>0</b></td><td><b>0</b></td>
            </tr>
            <tr>
                <td><a href="#" onclick="showPage('dem1');return false">Demodulator-1</a></td>
                <td class="cr"><b>Down</b></td>
                <td><b>NoSig</b></td>
                <td><b>-</b></td><td><b>0</b></td><td><b>0</b></td>
            </tr>
            <tr>
                <td><a href="#" onclick="showPage('mod');return false">Modulator</a></td>
                <td class="cr"><b>Down</b></td>
                <td>Tx Lvl: <b>- 15.0 dBm/TLC</b></td>
                <td><b>0</b></td><td><b>-</b></td><td><b>-</b></td>
            </tr>
        </table>
        <br>
        <table class="ov-station" width="100%" border="1" cellpadding="4">
            <tr><th colspan="10">Station</th></tr>
            <tr>
                <td>Number</td><td><b>0</b></td>
                <td>FP lost</td><td><b>0</b></td>
                <td>DTTS cor</td><td><b>0 us</b></td>
                <td>Frq cor</td><td><b>0 Hz</b></td>
                <td>Lvl cor</td><td><b>0.0 dBm</b></td>
            </tr>
            <tr>
                <td>Cur BW</td><td><b>0 (0 k)</b></td>
                <td>Sum Rq</td><td><b>0 (0 k)</b></td>
                <td>RT rq</td><td><b>0 (0 k)</b></td>
                <td>Codecs</td><td><b>0 / 0</b></td>
                <td>Timeout</td><td><b>0</b></td>
            </tr>
        </table>
    `;
}

// ── 5. Site Setup ──
function renderSiteSetup() {
    console.log('renderSiteSetup called');
    const c = currentConfig || {};
    const site = c.site || {};
    const rf = c.rf || {};
    const si = c.search_id || {};

    const siteName   = site.site_name    || 'AC 3';
    const latDeg     = site.latitude_deg || 32;
    const latMin     = site.latitude_min || 0;
    const latDir     = site.latitude_dir || 'N';
    const lonDeg     = site.longitude_deg || 35;
    const lonMin     = site.longitude_min || 0;
    const lonDir     = site.longitude_dir || 'E';

    const rx1Lo      = rf.rx1_lo || 0;
    const rx2Lo      = rf.rx2_lo || 0;
    const txLo       = rf.tx_lo || 0;
    const rxPower    = rf.rx_power ? ' checked' : '';
    const rx10mhz    = rf.rx_10mhz ? ' checked' : '';
    const rx1Spinv   = rf.rx1_spinv ? ' checked' : '';
    const rx2Spinv   = rf.rx2_spinv ? ' checked' : '';
    const txPower    = rf.tx_power ? ' checked' : '';
    const txSpinv    = rf.tx_spinv ? ' checked' : '';
    const rx1FreqAdj = rf.rx1_freq_adj || 0;
    const rx2FreqAdj = rf.rx2_freq_adj || 0;
    const txFreqAdj  = rf.tx_freq_adj || 0;

    const searchBwScpc = si.search_bw_scpc || 1800;
    const searchBwTdma = si.search_bw_tdma || 12;
    const netId        = si.net_id || 0;
    const rfId         = si.rf_id || 0;
    const farEndCn     = si.far_end_cn || 0;

    function tdmaSel(val) {
        const opts = [6, 12, 24, 40];
        return opts.map(v =>
            `<option value="${v}"${v == val ? ' selected' : ''}>${v}</option>`
        ).join('');
    }

    return `
        <center>
            <h3>Site setup</h3>
            <a href="cc53">Setup via script</a>
            <br><br>
            <form method="get" action="cw2" onsubmit="return false">
                <table>
                    <tr><td>Site name</td>
                        <td><input name="td" type="text" size="20" maxlength="20" value="${siteName}"></td>
                    </tr>
                    <tr><th colspan="2">Location</th></tr>
                    <tr><td>Latitude</td>
                        <td>
                            <input name="du" type="text" size="3" maxlen="3" value="${latDeg}"> deg
                            <input name="dv" type="text" size="2" maxlen="2" value="${latMin}"> min
                            <select name="dw">
                                <option value="0"${latDir === 'N' ? ' selected' : ''}>N</option>
                                <option value="1"${latDir === 'S' ? ' selected' : ''}>S</option>
                            </select>
                        </td>
                    </tr>
                    <tr><td>Longitude</td>
                        <td>
                            <input name="dx" type="text" size="3" maxlen="3" value="${lonDeg}"> deg
                            <input name="dy" type="text" size="2" maxlen="2" value="${lonMin}"> min
                            <select name="dz">
                                <option value="0"${lonDir === 'E' ? ' selected' : ''}>E</option>
                                <option value="1"${lonDir === 'W' ? ' selected' : ''}>W</option>
                            </select>
                        </td>
                    </tr>
                </table>
                <br>
                <table>
                    <tr>
                        <td>RF interface</td>
                        <th>LO (kHz)</th><th>Power</th><th>10MHz</th>
                        <th>SpInv</th><th>Frequency adjust (+/-kHz)<br><small>(0-4095)</small></th>
                    </tr>
                    <tr>
                        <th>Rx1</th>
                        <td>
                            <input name="df" type="text" size="8" maxlen="8" value="${rx1Lo}">
                            <br><span style="font-size:10px">2675000-33000000</span>
                        </td>
                        <td rowspan="2"><input name="dn" type="checkbox" value="1"${rxPower}></td>
                        <td><input name="do" type="checkbox" value="1"${rx10mhz}></td>
                        <td><input name="dp" type="checkbox" value="1"${rx1Spinv}></td>
                        <td><input name="dr" type="text" size="5" maxlen="5" value="${rx1FreqAdj}"></td>
                    </tr>
                    <tr>
                        <th>Rx2</th>
                        <td>
                            <input name="de" type="text" size="8" maxlen="8" value="${rx2Lo}">
                            <br><span style="font-size:10px">2675000-33000000</span>
                        </td>
                        <td></td>
                        <td><input name="dm" type="checkbox" value="1"${rx2Spinv}></td>
                        <td><input name="dq" type="text" size="5" maxlen="5" value="${rx2FreqAdj}"></td>
                    </tr>
                    <tr>
                        <th>Transmit</th>
                        <td>
                            <input name="dd" type="text" size="8" maxlen="8" value="${txLo}">
                            <br><span style="font-size:10px">2675000-35000000</span>
                        </td>
                        <td><input name="dg" type="checkbox" value="1"${txPower}></td>
                        <td><input name="dh" type="checkbox" value="1"${rx10mhz}></td>
                        <td><input name="di" type="checkbox" value="1"${txSpinv}></td>
                        <td><input name="dk" type="text" size="5" maxlen="5" value="${txFreqAdj}"></td>
                    </tr>
                </table>
                <br>
                <table>
                    <tr>
                        <th colspan="2">Carrier search bw (+/- kHz)</th>
                        <th colspan="2">Identification (hubs only)</th>
                        <th>Global TX level</th>
                    </tr>
                    <tr>
                        <td>SCPC mode (0-10000)</td>
                        <td><input name="dt" type="text" size="4" maxlen="4" value="${searchBwScpc}"></td>
                        <td>Net ID (0-255)</td>
                        <td><input name="dc" type="text" size="3" maxlen="3" value="${netId}"></td>
                        <td>Far end C/N (1-30) dB</td>
                    </tr>
                    <tr>
                        <td>TDMA mode</td>
                        <td><select name="ds">${tdmaSel(searchBwTdma)}</select></td>
                        <td>RF ID (0-255)</td>
                        <td><input name="db" type="text" size="3" maxlen="3" value="${rfId}"></td>
                        <td><input name="dl" type="text" size="3" maxlen="3" value="${farEndCn}"></td>
                    </tr>
                </table>
                <br>
                <input type="submit" name="tf" value="Apply" onclick="saveConfig();return false">
                <input type="button" value="Reset" onclick="resetConfig()">
            </form>
        </center>
    `;
}

// ── 6. Profiles ──
function renderProfiles() {
    console.log('renderProfiles called');
    const c = currentConfig || {};
    const profile = c.profile || {};
    const activeProfile = profile.active_profile || 1;

    // Получаем сохранённые режимы из localStorage (используем тот же ключ)
    var savedModes = JSON.parse(localStorage.getItem('profileConfigs_v2') || '{}');
    
    // Создаём массив режимов для всех 8 профилей
    var modes = {};
    for (var i = 1; i <= 8; i++) {
        if (savedModes[i] && savedModes[i].mode) {
            modes[i] = savedModes[i].mode;
        } else {
            modes[i] = 'none';
        }
    }

    let rows = '';
    for (let i = 1; i <= 8; i++) {
        const isActive = (i === activeProfile);
        var mode = modes[i] || 'none';
        const valid = isActive ? '+' : '&nbsp;';
        const ar = `<input name="d${String.fromCharCode(96 + i)}" type="checkbox" value="1"${isActive && profile.profile_autorun ? ' checked' : ''}>`;
        // Текст всегда видимый
        const link = `<a href="#" onclick="showProfileDetail(${i});return false" style="color:${isActive ? '#000' : '#555'};text-decoration:${isActive ? 'underline' : 'none'};">${mode}</a>`;
        const runCount = isActive ? profile.runs || 0 : '&nbsp;';

        rows += `
            <tr>
                <td>${i}</td>
                <td>${link}</td>
                <td>${valid}</td>
                <td>${ar}</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>${runCount}</td>
            </tr>
        `;
    }

    return `
        <center>
            <h3>Profiles</h3>
            <form method="get" action="cA3" onsubmit="return false;">
                <table border="2">
                    <tr>
                        <th>Num</th><th>Mode</th><th>Valid</th><th>Autorun</th>
                        <th width="200">Title</th><th>Run</th><th>Runs</th>
                    </tr>
                    ${rows}
                </table>
                <br>
                <input type="submit" name="ta" value="Apply" onclick="saveConfig();return false">
            </form>
        </center>
    `;
}

// ── Функция для обновления режима профиля из iframe ──
function profileUpdated(profileNum, mode) {
    console.log('profileUpdated:', profileNum, mode);
    // Обновляем данные в localStorage
    var saved = JSON.parse(localStorage.getItem('profileConfigs_v2') || '{}');
    if (!saved[profileNum]) {
        saved[profileNum] = {};
    }
    saved[profileNum].mode = mode;
    localStorage.setItem('profileConfigs_v2', JSON.stringify(saved));
    // Обновляем отображение таблицы
    showPage('profiles');
}

// ── Функция для обновления режима профиля из iframe ──
function profileUpdated(profileNum, mode) {
    console.log('profileUpdated:', profileNum, mode);
    var savedModes = JSON.parse(localStorage.getItem('profileModes') || '{}');
    savedModes[profileNum] = mode;
    localStorage.setItem('profileModes', JSON.stringify(savedModes));
    // Обновляем отображение таблицы
    showPage('profiles');
}

// ── Функция для обновления режима профиля из iframe ──
function profileUpdated(profileNum, mode) {
    console.log('profileUpdated:', profileNum, mode);
    var savedModes = JSON.parse(localStorage.getItem('profileModes') || '{}');
    savedModes[profileNum] = mode;
    localStorage.setItem('profileModes', JSON.stringify(savedModes));
    // Обновляем отображение таблицы
    showPage('profiles');
}

// ── Показать детали профиля (открыть страницу настройки) ──
function showProfileDetail(profileNum) {
    console.log('showProfileDetail called, profileNum:', profileNum);
    
    // Сохраняем выбранный профиль
    if (currentConfig && currentConfig.profile) {
        currentConfig.profile.active_profile = profileNum;
    }
    
    const main = document.getElementById('main');
    if (!main) {
        console.error('main element not found!');
        return;
    }

    // Полностью заменяем содержимое main на iframe со страницей настройки профиля
    const url = '/profiles/profile_config.html?da=' + profileNum;
    console.log('Loading profile config page:', url);
    
    main.innerHTML = `
        <div style="padding:10px 0 5px 0;">
            <button onclick="showPage('profiles')" style="padding:6px 16px;background:#f0f0f0;border:1px solid #ccc;border-radius:3px;cursor:pointer;font-size:14px;">
                ← Назад к профилям
            </button>
        </div>
        <iframe src="${url}" 
                style="width:100%;height:calc(100vh - 190px);border:1px solid #ccc;border-radius:4px;background:#fff;"
                frameborder="0">
        </iframe>
    `;
}

// ── 8. Закрыть детали профиля ──
function closeProfileDetail() {
    const container = document.getElementById('profile-detail-container');
    if (container) {
        container.style.display = 'none';
    }
}

// ── 9. Показать селектор профиля ──
function showProfileSelector(profileNum, currentMode) {
    console.log('showProfileSelector called, profileNum:', profileNum, 'currentMode:', currentMode);
    const overlay = document.createElement('div');
    overlay.id = 'profile-selector-overlay';
    overlay.innerHTML = `
        <div class="modal">
            <h3>Выберите профиль #${profileNum}</h3>
            <div style="margin:15px 0;max-height:300px;overflow-y:auto;">
                ${PROFILE_MODES.map(mode => `
                    <div class="option ${mode === currentMode ? 'selected' : ''}"
                         onclick="selectProfile(${profileNum}, '${mode}')">
                        ${mode}
                    </div>
                `).join('')}
            </div>
            <div style="display:flex;justify-content:flex-end;border-top:1px solid #ddd;padding-top:15px;">
                <button class="close-btn" onclick="closeProfileSelector()">Отмена</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
}

// ── 10. Закрыть селектор профиля ──
function closeProfileSelector() {
    const overlay = document.getElementById('profile-selector-overlay');
    if (overlay) overlay.remove();
}

// ── 11. Выбрать профиль ──
function selectProfile(profileNum, mode) {
    console.log('selectProfile called, profileNum:', profileNum, 'mode:', mode);
    closeProfileSelector();
    
    if (!currentConfig) currentConfig = {};
    if (!currentConfig.profile) currentConfig.profile = {};
    
    currentConfig.profile.active_profile = profileNum;
    currentConfig.profile.profile_mode = mode;
    currentConfig.profile.profile_autorun = false;
    currentConfig.profile.profile_timeout = 10;

    showPage('profiles');
    setTimeout(function() {
        showProfileDetail(mode);
    }, 100);
    
    showNotification('Выбран профиль: ' + mode);
}

// ── 12. Сохранение конфигурации ──
async function saveConfig() {
    console.log('saveConfig called');
    const config = {
        site: {
            site_name:     document.querySelector('[name="td"]')?.value || 'AC 3',
            latitude_deg:  parseInt(document.querySelector('[name="du"]')?.value) || 0,
            latitude_min:  parseInt(document.querySelector('[name="dv"]')?.value) || 0,
            latitude_dir:  document.querySelector('[name="dw"]')?.value === '0' ? 'N' : 'S',
            longitude_deg: parseInt(document.querySelector('[name="dx"]')?.value) || 0,
            longitude_min: parseInt(document.querySelector('[name="dy"]')?.value) || 0,
            longitude_dir: document.querySelector('[name="dz"]')?.value === '0' ? 'E' : 'W'
        },
        rf: {
            rx1_lo:       parseInt(document.querySelector('[name="df"]')?.value) || 0,
            rx2_lo:       parseInt(document.querySelector('[name="de"]')?.value) || 0,
            tx_lo:        parseInt(document.querySelector('[name="dd"]')?.value) || 0,
            rx_power:     !!document.querySelector('[name="dn"]')?.checked,
            rx_10mhz:     !!document.querySelector('[name="do"]')?.checked,
            rx1_spinv:    !!document.querySelector('[name="dp"]')?.checked,
            rx2_spinv:    !!document.querySelector('[name="dm"]')?.checked,
            tx_spinv:     !!document.querySelector('[name="di"]')?.checked,
            tx_power:     !!document.querySelector('[name="dg"]')?.checked,
            rx1_freq_adj: parseInt(document.querySelector('[name="dr"]')?.value) || 0,
            rx2_freq_adj: parseInt(document.querySelector('[name="dq"]')?.value) || 0,
            tx_freq_adj:  parseInt(document.querySelector('[name="dk"]')?.value) || 0
        },
        search_id: {
            search_bw_scpc: parseInt(document.querySelector('[name="dt"]')?.value) || 1800,
            search_bw_tdma: parseInt(document.querySelector('[name="ds"]')?.value) || 12,
            net_id:         parseInt(document.querySelector('[name="dc"]')?.value) || 0,
            rf_id:          parseInt(document.querySelector('[name="db"]')?.value) || 0,
            far_end_cn:     parseInt(document.querySelector('[name="dl"]')?.value) || 0
        },
        profile: {
            active_profile: currentConfig?.profile?.active_profile || 1,
            profile_mode: currentConfig?.profile?.profile_mode || 'none',
            profile_autorun: currentConfig?.profile?.profile_autorun || false,
            profile_timeout: currentConfig?.profile?.profile_timeout || 10
        }
    };

    try {
        const resp = await fetch('/api/session/' + SESSION_ID + '/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        if (!resp.ok) {
            alert('Save failed: ' + resp.statusText);
            return;
        }
        await resp.json();
        const infoResp = await fetch('/api/session/' + SESSION_ID);
        if (infoResp.ok) {
            const info = await infoResp.json();
            currentConfig = info.config;
        } else {
            currentConfig = config;
        }
        showNotification('Configuration applied');
    } catch (e) {
        console.error('Save config error:', e);
        alert('Save failed: ' + e.message);
    }
}

// ── 13. Сброс конфигурации ──
async function resetConfig() {
    console.log('resetConfig called');
    if (!confirm('Reset all parameters to factory defaults?')) return;
    try {
        const resp = await fetch('/api/session/' + SESSION_ID + '/reset', {
            method: 'POST'
        });
        if (!resp.ok) {
            alert('Reset failed: ' + resp.statusText);
            return;
        }
        const infoResp = await fetch('/api/session/' + SESSION_ID);
        if (infoResp.ok) {
            const info = await infoResp.json();
            currentConfig = info.config;
        }
        showNotification('Configuration reset to factory defaults');
        showPage('site_setup');
    } catch (e) {
        console.error('Reset error:', e);
        alert('Reset failed: ' + e.message);
    }
}

// ── 14. Панели статуса ──
async function loadPanel(panelName) {
    console.log('loadPanel called:', panelName);
    const main = document.getElementById('main');
    main.innerHTML = '<pre>Loading ' + panelName.toUpperCase() + '...</pre>';
    try {
        const resp = await fetch('/api/session/' + SESSION_ID + '/panels/' + panelName);
        if (!resp.ok) {
            main.innerHTML = '<pre>Panel not available</pre>';
            return;
        }
        const data = await resp.json();
        main.innerHTML = `<div style="width:fit-content"><pre>${JSON.stringify(data, null, 2)}</pre></div>`;
    } catch (e) {
        main.innerHTML = '<pre>Error loading panel</pre>';
    }
}

// ── 15. Консоль ──
function toggleConsole() {
    const panel = document.getElementById('console-panel');
    if (!panel) return;
    panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
    if (panel.style.display === 'flex') {
        const input = document.getElementById('console-input');
        if (input) input.focus();
    }
}

async function sendCommand() {
    const input = document.getElementById('console-input');
    if (!input) return;
    const cmd = input.value.trim();
    if (!cmd) return;
    input.value = '';

    appendConsole('CEL-AC3> ' + cmd);

    try {
        const resp = await fetch('/api/session/' + SESSION_ID + '/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: cmd })
        });
        if (!resp.ok) {
            appendConsole('Error: server returned ' + resp.status);
            return;
        }
        const data = await resp.json();
        appendConsole(data.output || '');
    } catch (e) {
        appendConsole('Error: ' + e.message);
    }
}

function appendConsole(text) {
    const output = document.getElementById('console-output');
    if (!output) return;
    output.textContent += text + '\n';
    output.scrollTop = output.scrollHeight;
}

// ── 16. WebSocket ──
function setupWebSocket() {
    console.log('setupWebSocket called');
    if (ws) {
        ws.close();
        ws = null;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = protocol + '//' + window.location.host + '/ws/' + SESSION_ID;

    try {
        ws = new WebSocket(url);
    } catch (e) {
        console.warn('WebSocket not available:', e);
        return;
    }

    ws.onopen = function () {
        console.log('WebSocket connected');
    };

    ws.onmessage = function (event) {
        try {
            const msg = JSON.parse(event.data);
            handleWsMessage(msg);
        } catch (e) {
            console.warn('WS parse error:', e);
        }
    };

    ws.onclose = function () {
        console.log('WebSocket closed, reconnecting in 5s...');
        setTimeout(setupWebSocket, 5000);
    };

    ws.onerror = function (e) {
        console.warn('WebSocket error:', e);
    };
}

function handleWsMessage(msg) {
    switch (msg.type) {
        case 'status_update':
            if (msg.data) {
                applyStatus(msg.data);
            }
            break;
        case 'ping_result':
            if (msg.data) {
                const pct = msg.data.loss_percent;
                const txt = pct === 0 ? 'Ping: 0% loss — все параметры верны!' : 'Ping: ' + pct + '% loss';
                showNotification(txt);
            }
            break;
    }
}

// ── 17. Stub ──
function renderStub(title) {
    return `<div class="stub-page"><div class="stub-message"><h2>${title || 'Section'}</h2><p>Этот раздел не реализован в симуляторе</p></div></div>`;
}

// ── 18. Утилиты ──
function showNotification(text) {
    const note = document.createElement('div');
    note.className = 'notification';
    note.textContent = text;
    document.body.appendChild(note);
    setTimeout(function () {
        note.classList.add('fade-out');
        setTimeout(function () { note.remove(); }, 500);
    }, 3000);
}

// ── 19. Инициализация ──
console.log('comtech.js: setting up DOMContentLoaded listener');
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded fired');
    
    // Настройка аккордеона для дерева
    document.querySelectorAll('.caret').forEach(function (caret) {
        caret.addEventListener('click', function () {
            const nested = this.parentElement.querySelector('.nested');
            if (nested) nested.classList.toggle('active');
            this.classList.toggle('caret-down');
        });
    });
    
    console.log('Calling init()...');
    init();
});

console.log('comtech.js: script execution complete');