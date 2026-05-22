// =============================================================================
// Comtech CEL-AC 3 Satellite Switch Simulator — Main SPA Logic
// =============================================================================

// ---------------------------------------------------------------------------
// 1. Session Management & Init
// ---------------------------------------------------------------------------
const SESSION_ID = sessionStorage.getItem('session_id');
if (!SESSION_ID) window.location.href = '/';

let currentConfig = null;
let ws = null;
let statusTimer = null;

async function init() {
    try {
        const resp = await fetch('/api/session/' + SESSION_ID);
        if (!resp.ok) {
            sessionStorage.removeItem('session_id');
            window.location.href = '/';
            return;
        }
        const data = await resp.json();
        currentConfig = data.config || data;
        setupWebSocket();
        startStatusPolling();
        showPage('overview');
    } catch (e) {
        console.error('Init failed:', e);
        sessionStorage.removeItem('session_id');
        window.location.href = '/';
    }
}

// ---------------------------------------------------------------------------
// 2. Page Router
// ---------------------------------------------------------------------------
function showPage(pageId, stubTitle) {
    const main = document.getElementById('main');
    if (!main) return;

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
        case 'stub':
            main.innerHTML = renderStub(stubTitle);
            break;
        default:
            main.innerHTML = renderStub(pageId);
    }
}

// ---------------------------------------------------------------------------
// 3. Status Polling
// ---------------------------------------------------------------------------
function startStatusPolling() {
    if (statusTimer) clearInterval(statusTimer);
    pollStatus();
    statusTimer = setInterval(pollStatus, 5000);
}

async function pollStatus() {
    try {
        var resp = await fetch('/api/session/' + SESSION_ID + '/status');
        if (!resp.ok) return;
        var s = await resp.json();
        applyStatus(s);
    } catch (e) {
        console.error('Status poll error:', e);
    }
}

function applyStatus(s) {
    // Update 8 status buttons (API returns: {lan1:"cg", dem1:"cr", ...})
    var panels = {
        lan1: 'btn-lan1', lan2: 'btn-lan2',
        dem1: 'btn-dem1', dem2: 'btn-dem2',
        mod: 'btn-mod', net: 'btn-net',
        sys_st: 'btn-sys', mon: 'btn-mon'
    };
    for (var key in panels) {
        var btn = document.getElementById(panels[key]);
        if (btn && s[key]) {
            // Keep the label text, just change the color class
            var label = btn.textContent;
            btn.className = 'sbtn ' + s[key];
        }
    }

    // SysLed
    var sysLed = document.getElementById('SysLed');
    if (sysLed && s.sys_led) {
        sysLed.className = 'sys-led ' + s.sys_led;
    }

    // Header state
    var stateEl = document.getElementById('hdr-state');
    if (stateEl && s.state !== undefined) {
        stateEl.textContent = s.state;
        stateEl.style.color = s.state_color || '#fe5e37';
    }

    // Header profile
    var profEl = document.getElementById('hdr-profile');
    if (profEl && s.profile_text !== undefined) {
        profEl.textContent = s.profile_text;
    }
}

// ---------------------------------------------------------------------------
// 4. Overview Page Renderer
// ---------------------------------------------------------------------------
function renderOverview() {
    const c = currentConfig || {};
    const site = c.site || {};
    const rf = c.rf || {};
    const profile = c.profile || {};
    const status = c.status || {};

    const cpuLoad = status.cpu_load !== undefined ? status.cpu_load : 22;
    const buffers = status.buffers !== undefined ? status.buffers : 2;
    const temp = status.temperature !== undefined ? status.temperature : 62;
    const uptime = status.uptime || '+00:00:00';
    const runs = profile.runs !== undefined ? profile.runs : 0;
    const profileMode = profile.profile_mode || 'none';
    const profileState = status.profile_state || 'DOWN';

    const ethState = status.lan1_up ? 'Up' : 'Up';
    const ethClass = 'green';
    const ethInfo = 'Link: Eth1:1G/FD Eth2:No link';
    const ethTx = status.eth_tx_rate || '0';
    const ethRx = status.eth_rx_rate || '0';

    const dem1State = status.dem1_up ? 'Up' : 'Down';
    const dem1Class = status.dem1_up ? 'green' : 'red';
    const dem1Info = status.dem1_up ? '' : 'NoSig';

    const modState = status.mod_up ? 'Up' : 'Down';
    const modClass = status.mod_up ? 'green' : 'red';
    const modTxLvl = status.mod_tx_lvl || '- 15.0 dBm/TLC';

    return '<div class="overview-page">' +
        '<table class="ov-header" width="100%"><tr>' +
            '<td>SN: <b>20097360</b></td>' +
            '<td>SW: <b>CEL-20X Software</b></td>' +
            '<td>Ver: <b>3.8.1.40</b></td>' +
        '</tr></table>' +
        '<table class="ov-stats" width="100%"><tr>' +
            '<td>CPU load: <b>' + cpuLoad + ' %</b></td>' +
            '<td>Buffers: <b>' + buffers + ' %</b></td>' +
            '<td>Temp: <b>' + temp + ' C</b></td>' +
            '<td>Profile: <b>' + profileState + ' during ' + uptime +
                '&nbsp;&nbsp;&nbsp;(' + runs + ' runs)</b></td>' +
        '</tr></table>' +
        '<table class="ov-iface" width="100%" border="1" cellpadding="4">' +
        '<tr><th>Interface</th><th>State</th><th>Info</th>' +
            '<th>TX rate (bps)</th><th>RX rate (bps)</th><th>RX errors</th></tr>' +
        '<tr><td><a href="#" onclick="showPage(\'lan1\');return false">Ethernet</a></td>' +
            '<td class="' + ethClass + '"><b>' + ethState + '</b></td>' +
            '<td>' + ethInfo + '</td>' +
            '<td><b>' + ethTx + '</b></td><td><b>' + ethRx + '</b></td><td><b>0</b></td></tr>' +
        '<tr><td><a href="#" onclick="showPage(\'dem2\');return false">Demodulator-2</a></td>' +
            '<td class="gray"><b>Disabled</b></td>' +
            '<td>Lvl: <b>- 8.0 dBm</b></td>' +
            '<td><b>-</b></td><td><b>0</b></td><td><b>0</b></td></tr>' +
        '<tr><td><a href="#" onclick="showPage(\'dem1\');return false">Demodulator-1</a></td>' +
            '<td class="' + dem1Class + '"><b>' + dem1State + '</b></td>' +
            '<td><b>' + dem1Info + '</b></td>' +
            '<td><b>-</b></td><td><b>0</b></td><td><b>0</b></td></tr>' +
        '<tr><td><a href="#" onclick="showPage(\'mod\');return false">Modulator</a></td>' +
            '<td class="' + modClass + '"><b>' + modState + '</b></td>' +
            '<td>Tx Lvl: <b>' + modTxLvl + '</b></td>' +
            '<td><b>0</b></td><td><b>-</b></td><td><b>-</b></td></tr>' +
        '</table>' +
        '<br>' +
        '<table class="ov-station" width="100%" border="1" cellpadding="4">' +
        '<tr><th colspan="10">Station</th></tr>' +
        '<tr><td>Number</td><td><b>0</b></td><td>FP lost</td><td><b>0</b></td>' +
            '<td>DTTS cor</td><td><b>0 us</b></td><td>Frq cor</td><td><b>0 Hz</b></td>' +
            '<td>Lvl cor</td><td><b>0.0 dBm</b></td></tr>' +
        '<tr><td>Cur BW</td><td><b>0 (0 k)</b></td><td>Sum Rq</td><td><b>0 (0 k)</b></td>' +
            '<td>RT rq</td><td><b>0 (0 k)</b></td><td>Codecs</td><td><b>0 / 0</b></td>' +
            '<td>Timeout</td><td><b>0</b></td></tr>' +
        '</table>' +
    '</div>';
}

// ---------------------------------------------------------------------------
// 5. Site Setup Page Renderer
// ---------------------------------------------------------------------------
function renderSiteSetup() {
    const c = currentConfig || {};
    const site = c.site || {};
    const rf = c.rf || {};
    const si = c.search_id || {};
    const profile = c.profile || {};

    const siteName   = site.site_name    || 'AC 3';
    const latDeg     = site.latitude_deg !== undefined ? site.latitude_deg : 32;
    const latMin     = site.latitude_min !== undefined ? site.latitude_min : 0;
    const latDir     = site.latitude_dir || 'N';
    const lonDeg     = site.longitude_deg !== undefined ? site.longitude_deg : 35;
    const lonMin     = site.longitude_min !== undefined ? site.longitude_min : 0;
    const lonDir     = site.longitude_dir || 'E';

    const rx1Lo      = rf.rx1_lo !== undefined ? rf.rx1_lo : 0;
    const rx2Lo      = rf.rx2_lo !== undefined ? rf.rx2_lo : 0;
    const txLo       = rf.tx_lo  !== undefined ? rf.tx_lo  : 0;
    const rxPower    = rf.rx_power  ? ' checked' : '';
    const rx10mhz    = rf.rx_10mhz  ? ' checked' : '';
    const rx1Spinv   = rf.rx1_spinv ? ' checked' : '';
    const rx2Spinv   = rf.rx2_spinv ? ' checked' : '';
    const txPower    = rf.tx_power  ? ' checked' : '';
    // 10MHz reference is shared (one oscillator), no separate tx_10mhz
    const txSpinv    = rf.tx_spinv  ? ' checked' : '';
    const rx1FreqAdj = rf.rx1_freq_adj !== undefined ? rf.rx1_freq_adj : 0;
    const rx2FreqAdj = rf.rx2_freq_adj !== undefined ? rf.rx2_freq_adj : 0;
    const txFreqAdj  = rf.tx_freq_adj  !== undefined ? rf.tx_freq_adj  : 0;

    const searchBwScpc = si.search_bw_scpc !== undefined ? si.search_bw_scpc : 1800;
    const searchBwTdma = si.search_bw_tdma !== undefined ? si.search_bw_tdma : 12;
    const netId        = si.net_id !== undefined ? si.net_id : 0;
    const rfId         = si.rf_id  !== undefined ? si.rf_id  : 0;
    const farEndCn     = si.far_end_cn !== undefined ? si.far_end_cn : 0;

    function tdmaSel(val) {
        var opts = [6, 12, 24, 40];
        return opts.map(function (v) {
            return '<option value="' + v + '"' +
                (v == val ? ' selected' : '') + '>' + v + '</option>';
        }).join('');
    }

    return '<div class="site-setup-page">' +
        '<h3>Site setup</h3>' +
        '<form id="site-setup-form" onsubmit="return false">' +

        // Site name
        '<table class="ss-table">' +
        '<tr><td>Site name</td><td>' +
            '<input id="ss-site-name" type="text" size="20" maxlength="20" value="' + siteName + '">' +
        '</td></tr>' +

        // Location
        '<tr><th colspan="2">Location</th></tr>' +
        '<tr><td>Latitude</td><td>' +
            '<input id="ss-lat-deg" type="text" size="3" maxlength="3" value="' + latDeg + '"> deg ' +
            '<input id="ss-lat-min" type="text" size="2" maxlength="2" value="' + latMin + '"> min ' +
            '<select id="ss-lat-dir">' +
                '<option value="N"' + (latDir === 'N' ? ' selected' : '') + '>N</option>' +
                '<option value="S"' + (latDir === 'S' ? ' selected' : '') + '>S</option>' +
            '</select>' +
        '</td></tr>' +
        '<tr><td>Longitude</td><td>' +
            '<input id="ss-lon-deg" type="text" size="3" maxlength="3" value="' + lonDeg + '"> deg ' +
            '<input id="ss-lon-min" type="text" size="2" maxlength="2" value="' + lonMin + '"> min ' +
            '<select id="ss-lon-dir">' +
                '<option value="E"' + (lonDir === 'E' ? ' selected' : '') + '>E</option>' +
                '<option value="W"' + (lonDir === 'W' ? ' selected' : '') + '>W</option>' +
            '</select>' +
        '</td></tr>' +
        '</table><br>' +

        // RF Interface table
        '<table class="ss-table" border="1" cellpadding="4">' +
        '<tr><td>RF interface</td><th>LO (kHz)</th><th>Power</th><th>10MHz</th>' +
            '<th>SpInv</th><th>Frequency adjust (+/- kHz)<br><small>(0-4095)</small></th></tr>' +

        // Rx1
        '<tr><th>Rx1</th>' +
            '<td><input id="ss-rx1-lo" type="text" size="8" maxlength="8" value="' + rx1Lo + '">' +
                '<br><span style="font-size:10px">2675000-33000000</span></td>' +
            '<td rowspan="2"><input id="ss-rx-power" type="checkbox"' + rxPower + '></td>' +
            '<td><input id="ss-rx-10mhz" type="checkbox"' + rx10mhz + '></td>' +
            '<td><input id="ss-rx1-spinv" type="checkbox"' + rx1Spinv + '></td>' +
            '<td><input id="ss-rx1-freq-adj" type="text" size="5" maxlength="5" value="' + rx1FreqAdj + '"></td>' +
        '</tr>' +

        // Rx2
        '<tr><th>Rx2</th>' +
            '<td><input id="ss-rx2-lo" type="text" size="8" maxlength="8" value="' + rx2Lo + '">' +
                '<br><span style="font-size:10px">2675000-33000000</span></td>' +
            '<td></td>' +
            '<td><input id="ss-rx2-spinv" type="checkbox"' + rx2Spinv + '></td>' +
            '<td><input id="ss-rx2-freq-adj" type="text" size="5" maxlength="5" value="' + rx2FreqAdj + '"></td>' +
        '</tr>' +

        // TX
        '<tr><th>Transmit</th>' +
            '<td><input id="ss-tx-lo" type="text" size="8" maxlength="8" value="' + txLo + '">' +
                '<br><span style="font-size:10px">2675000-35000000</span></td>' +
            '<td><input id="ss-tx-power" type="checkbox"' + txPower + '></td>' +
            '<td></td>' +
            '<td><input id="ss-tx-spinv" type="checkbox"' + txSpinv + '></td>' +
            '<td><input id="ss-tx-freq-adj" type="text" size="5" maxlength="5" value="' + txFreqAdj + '"></td>' +
        '</tr>' +
        '</table><br>' +

        // Search BW / Identification / Global TX level
        '<table class="ss-table" border="1" cellpadding="4">' +
        '<tr><th colspan="2">Carrier search bw (+/- kHz)</th>' +
            '<th colspan="2">Identification (hubs only)</th>' +
            '<th>Global TX level</th></tr>' +
        '<tr>' +
            '<td>SCPC mode (0-10000)</td>' +
            '<td><input id="ss-search-bw-scpc" type="text" size="4" maxlength="4" value="' + searchBwScpc + '"></td>' +
            '<td>Net ID (0-255)</td>' +
            '<td><input id="ss-net-id" type="text" size="3" maxlength="3" value="' + netId + '"></td>' +
            '<td>Far end C/N (1-30) dB</td>' +
        '</tr>' +
        '<tr>' +
            '<td>TDMA mode</td>' +
            '<td><select id="ss-search-bw-tdma">' + tdmaSel(searchBwTdma) + '</select></td>' +
            '<td>RF ID (0-255)</td>' +
            '<td><input id="ss-rf-id" type="text" size="3" maxlength="3" value="' + rfId + '"></td>' +
            '<td><input id="ss-far-end-cn" type="text" size="3" maxlength="3" value="' + farEndCn + '"></td>' +
        '</tr>' +
        '</table><br>' +

        '<button type="button" class="btn-apply" onclick="saveConfig()">Apply</button> ' +
        '<button type="button" class="btn-reset" onclick="resetConfig()">Reset</button>' +
        '</form>' +
    '</div>';
}

// ---------------------------------------------------------------------------
// 6. Profiles Page Renderer
// ---------------------------------------------------------------------------
function renderProfiles() {
    const c = currentConfig || {};
    const profile = c.profile || {};
    const activeProfile = profile.active_profile !== undefined ? profile.active_profile : 1;
    const profileMode = profile.profile_mode || 'Star station';
    const autorun = profile.profile_autorun ? ' checked' : '';
    const runs = profile.runs !== undefined ? profile.runs : 0;

    var modeOptions = [
        'none', 'SCPC modem', 'Star station', 'Mesh station', 'Hubless station',
        'DAMA station', 'CrossPol test', 'Star hub', 'MF hub', 'Outroute',
        'Inroute', 'MF inroute', 'Hubless master', 'DAMA hub', 'DAMA inroute',
        'Channel simulator', 'Spectrum Analyzer', 'Commissioning unit'
    ];

    function modeSelect(id, selected) {
        return '<select id="' + id + '">' +
            modeOptions.map(function (m) {
                return '<option value="' + m + '"' +
                    (m === selected ? ' selected' : '') + '>' + m + '</option>';
            }).join('') +
        '</select>';
    }

    var rows = '';
    for (var i = 1; i <= 8; i++) {
        var isActive = (i === activeProfile);
        var mode = isActive ? profileMode : 'none';
        var valid = isActive ? '+' : '&nbsp;';
        var ar = '<input type="checkbox" id="prof-autorun-' + i + '"' +
                 (isActive && profile.profile_autorun ? ' checked' : '') + '>';
        var runLink = isActive ? '<a href="#" onclick="return false">*</a>' : '&nbsp;';
        var runCount = isActive ? runs : '&nbsp;';

        rows += '<tr>' +
            '<td>' + i + '</td>' +
            '<td>' + modeSelect('prof-mode-' + i, mode) + '</td>' +
            '<td>' + valid + '</td>' +
            '<td>' + ar + '</td>' +
            '<td>&nbsp;</td>' +
            '<td>' + runLink + '</td>' +
            '<td>' + runCount + '</td>' +
        '</tr>';
    }

    return '<div class="profiles-page">' +
        '<h3>Profiles</h3>' +
        '<form id="profiles-form" onsubmit="return false">' +
        '<table class="prof-table" border="2" cellpadding="4">' +
        '<tr><th>Num</th><th>Mode</th><th>Valid</th><th>Autorun</th>' +
            '<th width="200">Title</th><th>Run</th><th>Runs</th></tr>' +
        rows +
        '</table><br>' +
        '<button type="button" class="btn-apply" onclick="saveConfig()">Apply</button>' +
        '</form>' +
    '</div>';
}

// ---------------------------------------------------------------------------
// 7. Status Panel Loaders
// ---------------------------------------------------------------------------
async function loadPanel(panelName) {
    const main = document.getElementById('main');
    main.innerHTML = '<pre>Loading ' + panelName.toUpperCase() + '...</pre>';
    try {
        const resp = await fetch('/api/session/' + SESSION_ID + '/panels/' + panelName);
        if (!resp.ok) {
            main.innerHTML = renderPanelFallback(panelName);
            return;
        }
        const data = await resp.json();
        main.innerHTML = '<div style="width:fit-content"><pre>' +
            formatPanel(panelName, data) + '</pre></div>';
    } catch (e) {
        main.innerHTML = renderPanelFallback(panelName);
    }
}

function renderPanelFallback(panelName) {
    var c = currentConfig || {};
    var rf = c.rf || {};
    var si = c.search_id || {};
    var site = c.site || {};
    return '<div style="width:fit-content"><pre>' +
        formatPanel(panelName, { config: c }) + '</pre></div>';
}

function formatPanel(name, data) {
    var d = data || {};
    var c = d.config || currentConfig || {};
    var rf = c.rf || {};
    var si = c.search_id || {};
    var site = c.site || {};
    var profile = c.profile || {};
    var st = c.status || {};

    switch (name) {
        case 'dem1': return formatDem(d, rf, si, 1);
        case 'dem2': return formatDem(d, rf, si, 2);
        case 'mod':  return formatMod(d, rf);
        case 'lan1': return formatLan(d, 1);
        case 'lan2': return formatLan(d, 2);
        case 'net':  return formatNet(d, site, profile);
        case 'sys':  return formatSys(d, st);
        case 'mon':  return formatMon(d);
        default:     return name.toUpperCase() + ' panel';
    }
}

function formatDem(d, rf, si, num) {
    var state = d.state || 'DOWN';
    var lastUD = d.last_ud || 'never';
    var lastDU = d.last_du || 'never';
    var transitions = d.transitions || 0;
    var cleared = d.cleared || 'never';
    var lnbPwr = d.lnb_pwr || (rf.rx_power ? 'ON' : 'OFF');
    var t10m = d.t10m || (rf.rx_10mhz ? 'ON' : 'OFF');
    var offset = d.offset || 0;
    var searchBw = d.search_bw || si.search_bw_scpc || 1800;
    var lo = d.lo || (num === 1 ? (rf.rx1_lo || 0) : (rf.rx2_lo || 0));
    var frq = d.frq || 1350000;
    var sr = d.sr || 8300;
    var input = 'RX-' + num;
    var spi = d.spi || (num === 1 ? (rf.rx1_spinv ? 'ON' : 'OFF') : (rf.rx2_spinv ? 'ON' : 'OFF'));
    var inlvl = d.inlvl || 'NoSig';
    var modcod = d.modcod || '----------------';
    var sroff = d.sroff || '-----';
    var cn = d.cn || '0.0';
    var rxOffset = d.rx_offset || '-1     KHz';
    var fixOffset = d.fix_offset || '0      KHz';
    var rate = d.rate || 0;

    var lines = [];
    lines.push('Demodulator-' + num + ' interface is ' + state);
    lines.push('Last U->D: ' + pad(lastUD, 20) + 'U->D transitions: ' + transitions);
    lines.push('Last D->U: ' + pad(lastDU, 20) + 'Counters cleared: ' + cleared);
    lines.push('-------------------------------- Outdoor Unit --------------------------------');
    lines.push('| LNB-pwr: ' + pad(lnbPwr, 7) + ' T10M: ' + pad(t10m, 8) +
        ' Offset: ' + pad(String(offset), 5) + 'KHz      SearchBW: ' + searchBw + ' KHz    |');
    lines.push('| LO: ' + pad(String(lo), 14) + 'Frq: ' + pad(String(frq), 10) +
        'SR: ' + pad(String(sr), 9) + 'Input:  ' + pad(input, 10) + 'SpI:  ' + pad(spi, 4) + '|');
    lines.push('----------------------------- Demodulator state ------------------------------');
    lines.push('| InLvl | SpI |      MODCOD      | SRoff  | C/N  | RX-offset  |  FixOffset   |');
    lines.push('| ' + pad(inlvl, 5) + ' | ' + pad(spi, 3) + ' | ' + pad(modcod, 16) +
        ' | ' + pad(sroff, 6) + '| ' + pad(cn, 4) + ' | ' + pad(rxOffset, 10) +
        ' | ' + pad(fixOffset, 12) + ' |');
    lines.push('------------------------------- Data received --------------------------------');
    lines.push('Rate/bps: ' + rate);

    for (var i = 1; i <= 8; i++) {
        var ch = d['ch' + i] || {};
        lines.push('CH' + i + '   Packets: ' + pad(String(ch.packets || 0), 16) +
            'Bytes: ' + pad(String(ch.bytes || 0), 12) +
            'CRC_errors: ' + (ch.crc_errors || 0));
    }

    return lines.join('\n');
}

function formatMod(d, rf) {
    var state = d.state || 'DOWN';
    var lastUD = d.last_ud || 'never';
    var lastDU = d.last_du || 'never';
    var transitions = d.transitions || 0;
    var cleared = d.cleared || 'never';
    var freq = d.freq || 0;
    var freqAdj = d.freq_adj || (rf.tx_freq_adj || 0);
    var sr = d.sr || 4096;
    var setLvl = d.set_lvl || '-0.0';
    var maxLvl = d.max_lvl || '-15.0';
    var t10m = d.t10m || (rf.rx_10mhz ? 'ON' : 'OFF');
    var lo = d.lo || (rf.tx_lo || 0);
    var outLvl = d.out_lvl || 'OFF';
    var tx = d.tx || 'OFF';
    var v24 = d.v24 || 'OFF';
    var modcod = d.modcod || 'SF QPSK 1/2';
    var rolloff = d.rolloff || '20%';
    var pilots = d.pilots || 'OFF';
    var rate = d.rate || 0;
    var load = d.load || 0;
    var bw = d.bw || 4096;
    var shprDrops = d.shpr_drops || 0;

    var lines = [];
    lines.push('Modulator interface is ' + state);
    lines.push('Last U->D: ' + pad(lastUD, 20) + 'U->D transitions: ' + transitions);
    lines.push('Last D->U: ' + pad(lastDU, 20) + 'Counters cleared: ' + cleared);
    lines.push('----------------------------- Modulator settings -----------------------------');
    lines.push('Type: Internal');
    lines.push('Freq: ' + pad(String(freq), 8) + 'FreqAdj: ' + pad(String(freqAdj), 7) +
        'SR: ' + pad(String(sr), 7) + 'SetLvl: ' + pad(setLvl, 6) +
        'Max: ' + pad(maxLvl, 8) + '10M: ' + t10m);
    lines.push('LO: ' + pad(String(lo), 10) + 'FixCorr: ' + pad('0', 7) +
        'BR: ' + pad('0', 7) + 'OutLvl: ' + pad(outLvl, 6) +
        'TX: ' + pad(tx, 8) + '24V: ' + v24);
    lines.push('------------------------------------------------------------------------------');
    lines.push('Mode: DVB-S2X  MODCOD: ' + modcod + '  Rolloff: ' + rolloff +
        '  Pilots: ' + pilots);
    lines.push('------------------------------------------------------------------------------');
    lines.push('Rate/bps: ' + pad(String(rate), 16) +
        'Load(%)/BW(bps): ' + load + '  /' + bw +
        '           Shpr.Drops: ' + shprDrops);

    var queues = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'CTRL'];
    var qLens  = [2000, 1600, 1200, 800, 400, 100, 50, 200];
    for (var i = 0; i < queues.length; i++) {
        var q = d[queues[i].toLowerCase()] || {};
        lines.push(pad(queues[i], 5) + 'Packets: ' + pad(String(q.packets || 0), 13) +
            'Bytes: ' + pad(String(q.bytes || 0), 12) +
            'Q_len/' + pad(String(qLens[i]), 5) + ': ' + pad(String(q.q_len || 0), 8) +
            'Drops: ' + (q.drops || 0));
    }

    return lines.join('\n');
}

function formatLan(d, num) {
    var state = d.state || (num === 1 ? 'UP' : 'DOWN');
    var lastUD = d.last_ud || (num === 1 ? '+00:10:13' : 'never');
    var lastDU = d.last_du || (num === 1 ? '+00:14:05' : 'never');
    var transitions = d.transitions || (num === 1 ? 1 : 0);
    var cleared = d.cleared || 'never';
    var mac = d.mac || '46:13:20:09:73:60';
    var eth1State = d.eth1_state || '1G/FD';
    var eth2State = d.eth2_state || 'No link';
    var rxRate = d.rx_rate || 0;
    var txRate = d.tx_rate || 0;

    var lines = [];
    lines.push('Ethernet interface is ' + state);
    lines.push('Last U->D: ' + pad(lastUD, 20) + 'U->D transitions: ' + transitions);
    lines.push('Last D->U: ' + pad(lastDU, 20) + 'Counters cleared: ' + cleared);
    lines.push('MAC: ' + mac);
    lines.push('Eth1:     Set: AUTO    State: ' + eth1State);
    lines.push('Eth2:     Set: AUTO    State: ' + eth2State);
    lines.push('|-----+---- RX ----+---- TX ----+--------+------------|No buffer| 0          |');
    lines.push('|Rate | ' + pad(String(rxRate), 10) + ' | ' + pad(String(txRate), 10) +
        ' |Bcasts  | ' + pad(String(d.bcasts || 0), 10) +
        ' |Collision| ' + pad(String(d.collision || 0), 10) + ' |');
    lines.push('|Bytes| ' + pad(String(d.rx_bytes || 0), 10) + ' | ' + pad(String(d.tx_bytes || 0), 10) +
        ' |CRC errs| ' + pad(String(d.crc_errs || 0), 10) +
        ' |16 colls.| ' + pad(String(d.colls16 || 0), 10) + ' |');
    lines.push('|Pkts.| ' + pad(String(d.rx_pkts || 0), 10) + ' | ' + pad(String(d.tx_pkts || 0), 10) +
        ' |Overruns| ' + pad(String(d.overruns || 0), 10) +
        ' |Underruns| ' + pad(String(d.underruns || 0), 10) + ' |');
    lines.push('');
    lines.push('Extended MAC stats');
    lines.push('RxGood: ' + pad(String(d.rx_good || 0), 11) +
        ' RxBcst: ' + pad(String(d.rx_bcst || 0), 11) +
        ' RxMcst: ' + pad(String(d.rx_mcst || 0), 11) +
        ' RxPaus: ' + (d.rx_paus || 0));
    lines.push(' RxCrc: ' + pad(String(d.rx_crc || 0), 11) +
        ' RxAlgn: ' + pad(String(d.rx_algn || 0), 11) +
        ' RxOvSz: ' + pad(String(d.rx_ovsz || 0), 11) +
        ' RxJabb: ' + (d.rx_jabb || 0));
    lines.push('RxUnSz: ' + pad(String(d.rx_unsz || 0), 11) +
        ' RxFrag: ' + pad(String(d.rx_frag || 0), 11) +
        '      -: ' + pad('0', 11) +
        '      -: 0');

    return lines.join('\n');
}

function formatNet(d, site, profile) {
    var mode = d.mode || profile.profile_mode || 'Star station';
    var netState = d.net_state || 'No RX';
    var latDeg = site.latitude_deg !== undefined ? site.latitude_deg : 32;
    var latMin = site.latitude_min !== undefined ? site.latitude_min : 0;
    var latDir = site.latitude_dir || 'N';
    var lonDeg = site.longitude_deg !== undefined ? site.longitude_deg : 35;
    var lonMin = site.longitude_min !== undefined ? site.longitude_min : 0;
    var lonDir = site.longitude_dir || 'E';

    var lines = [];
    lines.push('--------------------------- Unit state ---------------------------');
    lines.push('Mode: ' + mode + '   State: ' + netState);
    lines.push('------------------------- Identification -------------------------');
    lines.push('Inroute: ' + (d.inroute || 0));
    lines.push('----------------------------- TDMA RF ----------------------------');
    lines.push('TxFrq: ' + (d.tx_frq || 0));
    lines.push('Mesh MC: ' + (d.mesh_mc || '-'));
    lines.push('-------------------------- TDMA protocol -------------------------');
    lines.push('SlLen: ' + pad(String(d.sl_len || 0), 5) +
        'FrLen: ' + pad(String(d.fr_len || 0), 5) +
        'StNum: ' + pad(String(d.st_num || 0), 5) +
        'ActChannels: ' + (d.act_channels || 1) + '  LDPCT:' + (d.ldpct || 'Norm'));
    lines.push('------------------------- TDMA calculated ------------------------');
    lines.push('BitR: ' + pad(String(d.bit_r || 0), 5) +
        'SlDur: ' + pad(String(d.sl_dur || '0.0'), 5) +
        'FrDur: ' + (d.fr_dur || 0));
    lines.push('---------------------------- Station -----------------------------');
    lines.push('Number: ' + pad(String(d.number || 0), 7) +
        'CurBw: ' + pad(String(d.cur_bw || '0 (0 k)'), 10) +
        'FpLost: ' + (d.fp_lost || 0));
    lines.push('--------------------------- Corrections --------------------------');
    lines.push('DttsCor: ' + pad(String(d.dtts_cor || 0), 7) +
        'FrqCor: ' + pad(String(d.frq_cor || 0), 7) +
        'LvlCor: ' + (d.lvl_cor || '0.0'));
    lines.push('------------------------ Fixed Corrections -----------------------');
    lines.push('DttsFixCor: ' + pad(String(d.dtts_fix_cor || 0), 7) +
        'FrqFixCor: ' + (d.frq_fix_cor || 0));
    lines.push('---------------------------- BwRequest ---------------------------');
    lines.push('TxRate(k): ' + pad(String(d.tx_rate_k || 0), 8) +
        'TotRq: ' + pad(String(d.tot_rq || 0), 5) +
        'RtRq: ' + pad(String(d.rt_rq || 0), 5) +
        'Codecs: ' + (d.codecs || '0 / 0'));
    lines.push('----------------------------- Timing -----------------------------');
    lines.push('Mode: Value  NetTTS: ' + pad(String(d.net_tts || 0), 8) +
        'TCL: ' + pad(String(d.tcl || 0), 5) +
        'TCE: ' + pad(String(d.tce || 0), 4) +
        'GENcor: ' + (d.gen_cor || 0));
    lines.push('SatPos: ' + (d.sat_pos || '0') + '  d ' +
        (d.sat_min || '0') + ' \' ' + (d.sat_dir || 'E') +
        '   GpsPkts: ' + (d.gps_pkts || 0));
    lines.push('Set  location: ' + latDeg + 'd ' + latMin + ' \' ' + latDir +
        ' / ' + lonDeg + ' d ' + lonMin + ' \' ' + lonDir + '  Set  DTTS=' + (d.set_dtts || 0));
    lines.push('Used location: ' + latDeg + 'd ' + latMin + ' \' ' + latDir +
        ' / ' + lonDeg + ' d ' + lonMin + ' \' ' + lonDir + '  Used DTTS=' + (d.used_dtts || 0));

    return lines.join('\n');
}

function formatSys(d, st) {
    var uptime = d.uptime || st.uptime || '+00:00:00';
    var cpuLoad = d.cpu_load !== undefined ? d.cpu_load : (st.cpu_load || 22);
    var temp = d.temperature !== undefined ? d.temperature : (st.temperature || 62);
    var bufFree = d.buffers_free || 16092;

    var lines = [];
    lines.push('CEL-20X Software(H/W CEL-200X)  Ver: 3.8.1.40 (21.02.2023)   SN: 20097360');
    lines.push('Uptime: ' + pad(uptime, 17) +
        'CurrentTime: ' + pad(uptime, 17) + 'TimeZone: 0');
    lines.push('RateAvgTime: 5     BuffersFree: ' + pad(String(bufFree), 8) +
        'NoBuffer: 0         ScDesc: 8163');
    lines.push('CPUload: ' + cpuLoad + ' %  IdleTimeout: 10      Temperature: ' + temp + 'c');
    lines.push('LastTelnetIP: 0.0.0.0   AutoRestartDelay: 3');
    lines.push('');
    lines.push('Keys information upon start-up:');
    lines.push('');
    lines.push('Key 0  In key:  65535 65535 65535    Out key:  26390 52661 50955');
    lines.push('Options:');
    lines.push('');
    lines.push('Key 1  In key:  65535 65535 65535    Out key:  26390 52661 50955');
    lines.push('Lock ID1: NOT SET');
    lines.push('');
    lines.push('Key 2  In key:  65535 65535 65535    Out key:  26390 52661 50955');
    lines.push('Lock ID2: INVALID');
    lines.push('');
    lines.push('Key 3  In key:  65535 65535 65535    Out key:  26390 52661 50955');
    lines.push('NMS ID: NOT SET');
    lines.push('');
    lines.push('Key 4  In key:  65535 65535 65535    Out key:  26390 52661 50955');
    lines.push('Options:');
    lines.push('');
    lines.push('Missed options:');
    lines.push('');
    lines.push('');
    lines.push('Errors report:');
    lines.push('No SW errors');
    lines.push('No config errors');

    return lines.join('\n');
}

function formatMon(d) {
    var state = d.state || 'OFF';
    var faults = d.faults || '';
    var pingInt = d.ping_interval || 5;
    var lostAllowed = d.lost_allowed || 0;

    var lines = [];
    lines.push('-------------------------- Service monitoring general --------------------------');
    lines.push('State: ' + state + '  Faults: ' + faults);
    lines.push('');
    lines.push('----------------------------- Reachability checks ------------------------------');
    lines.push('Ping interval: ' + pingInt + ' s Lost allowed : ' + lostAllowed);
    lines.push('Local  : OFF Host: 0.0.0.0 VLAN: 0    Max delay check: OFF Delay: 600 ms');
    lines.push('Network: OFF Host: 0.0.0.0 VLAN: 0    Max delay check: OFF Delay: 600 ms');
    lines.push('');
    lines.push('------------------------------ LAN traffic checks ------------------------------');
    lines.push('LAN Rx(Local)  : OFF Threshold: 0 kbps');
    lines.push('LAN Tx(Network): OFF Threshold: 0 kbps');
    lines.push('');
    lines.push('-------------------------- Backup routing switchover ---------------------------');
    lines.push('State    : OFF');
    lines.push('Backup IP: 0.0.0.0');
    lines.push('');
    lines.push('--------------------------------- Auto reboot ----------------------------------');
    lines.push('State: OFF');
    lines.push('Delay: 3 min');

    return lines.join('\n');
}

function pad(str, len) {
    str = String(str);
    while (str.length < len) str += ' ';
    return str;
}

// ---------------------------------------------------------------------------
// 8. Config Save / Reset
// ---------------------------------------------------------------------------
async function saveConfig() {
    var config = {
        site: {
            site_name:     val('ss-site-name') || 'AC 3',
            latitude_deg:  intVal('ss-lat-deg', 0),
            latitude_min:  intVal('ss-lat-min', 0),
            latitude_dir:  selVal('ss-lat-dir', 'N'),
            longitude_deg: intVal('ss-lon-deg', 0),
            longitude_min: intVal('ss-lon-min', 0),
            longitude_dir: selVal('ss-lon-dir', 'E')
        },
        rf: {
            rx1_lo:       intVal('ss-rx1-lo', 0),
            rx2_lo:       intVal('ss-rx2-lo', 0),
            tx_lo:        intVal('ss-tx-lo', 0),
            rx_power:     chkVal('ss-rx-power'),
            rx_10mhz:     chkVal('ss-rx-10mhz'),
            rx1_spinv:    chkVal('ss-rx1-spinv'),
            rx2_spinv:    chkVal('ss-rx2-spinv'),
            tx_power:     chkVal('ss-tx-power'),
            tx_spinv:     chkVal('ss-tx-spinv'),
            rx1_freq_adj: intVal('ss-rx1-freq-adj', 0),
            rx2_freq_adj: intVal('ss-rx2-freq-adj', 0),
            tx_freq_adj:  intVal('ss-tx-freq-adj', 0)
        },
        search_id: {
            search_bw_scpc: intVal('ss-search-bw-scpc', 1800),
            search_bw_tdma: intVal('ss-search-bw-tdma', 12),
            net_id:         intVal('ss-net-id', 0),
            rf_id:          intVal('ss-rf-id', 0),
            far_end_cn:     intVal('ss-far-end-cn', 0)
        },
        profile: collectProfileData()
    };

    try {
        var resp = await fetch('/api/session/' + SESSION_ID + '/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        if (!resp.ok) {
            alert('Save failed: ' + resp.statusText);
            return;
        }
        await resp.json();
        // Reload config from server to get the saved state
        var infoResp = await fetch('/api/session/' + SESSION_ID);
        if (infoResp.ok) {
            var info = await infoResp.json();
            currentConfig = info.config;
        } else {
            currentConfig = config; // fallback to what we sent
        }
        showNotification('Configuration applied');
    } catch (e) {
        console.error('Save config error:', e);
        alert('Save failed: ' + e.message);
    }
}

function collectProfileData() {
    // If not on profiles page, keep current values
    if (!document.getElementById('prof-mode-1') && currentConfig && currentConfig.profile) {
        return currentConfig.profile;
    }
    var result = {
        active_profile: 1,
        profile_mode: 'none',
        profile_autorun: false,
        profile_timeout: 10
    };
    for (var i = 1; i <= 8; i++) {
        var modeEl = document.getElementById('prof-mode-' + i);
        var arEl   = document.getElementById('prof-autorun-' + i);
        if (modeEl && modeEl.value !== 'none') {
            result.active_profile = i;
            result.profile_mode = modeEl.value;
            result.profile_autorun = arEl ? arEl.checked : false;
            break;
        }
    }
    return result;
}

async function resetConfig() {
    if (!confirm('Reset all parameters to factory defaults?')) return;
    try {
        var resp = await fetch('/api/session/' + SESSION_ID + '/reset', {
            method: 'POST'
        });
        if (!resp.ok) {
            alert('Reset failed: ' + resp.statusText);
            return;
        }
        // Reload config from server
        var infoResp = await fetch('/api/session/' + SESSION_ID);
        if (infoResp.ok) {
            var info = await infoResp.json();
            currentConfig = info.config;
        }
        showNotification('Configuration reset to factory defaults');
        showPage('site_setup');
    } catch (e) {
        console.error('Reset error:', e);
        alert('Reset failed: ' + e.message);
    }
}

// Form helpers
function val(id, fallback) {
    var el = document.getElementById(id);
    return el ? el.value : (fallback || '');
}
function intVal(id, fallback) {
    var el = document.getElementById(id);
    if (!el) return fallback || 0;
    var v = parseInt(el.value, 10);
    return isNaN(v) ? (fallback || 0) : v;
}
function selVal(id, fallback) {
    var el = document.getElementById(id);
    return el ? el.value : (fallback || '');
}
function chkVal(id) {
    var el = document.getElementById(id);
    return el ? el.checked : false;
}

// ---------------------------------------------------------------------------
// 9. Console
// ---------------------------------------------------------------------------
function toggleConsole() {
    var panel = document.getElementById('console-panel');
    if (!panel) return;
    panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
    if (panel.style.display === 'flex') {
        var input = document.getElementById('console-input');
        if (input) input.focus();
    }
}

async function sendCommand() {
    var input = document.getElementById('console-input');
    if (!input) return;
    var cmd = input.value.trim();
    if (!cmd) return;
    input.value = '';

    appendConsole('CEL-AC3> ' + cmd);

    try {
        var resp = await fetch('/api/session/' + SESSION_ID + '/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: cmd })
        });
        if (!resp.ok) {
            appendConsole('Error: server returned ' + resp.status);
            return;
        }
        var data = await resp.json();
        appendConsole(data.output || '');
    } catch (e) {
        appendConsole('Error: ' + e.message);
    }
}

function appendConsole(text) {
    var output = document.getElementById('console-output');
    if (!output) return;
    output.textContent += text + '\n';
    output.scrollTop = output.scrollHeight;
}


// ---------------------------------------------------------------------------
// 10. WebSocket
// ---------------------------------------------------------------------------
function setupWebSocket() {
    if (ws) {
        ws.close();
        ws = null;
    }

    var protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    var url = protocol + '//' + window.location.host + '/ws/' + SESSION_ID;

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
            var msg = JSON.parse(event.data);
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
                var pct = msg.data.loss_percent;
                var txt = pct === 0 ? 'Ping: 0% loss — все параметры верны!' : 'Ping: ' + pct + '% loss';
                showNotification(txt);
            }
            break;
    }
}

function showNotification(text) {
    var note = document.createElement('div');
    note.className = 'notification';
    note.textContent = text;
    document.body.appendChild(note);
    setTimeout(function () {
        note.classList.add('fade-out');
        setTimeout(function () { note.remove(); }, 500);
    }, 3000);
}

// ---------------------------------------------------------------------------
// 11. Navigation Tree Toggle
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.caret').forEach(function (caret) {
        caret.addEventListener('click', function () {
            var nested = this.parentElement.querySelector('.nested');
            if (nested) nested.classList.toggle('active');
            this.classList.toggle('caret-down');
        });
    });
    init();
});

// ---------------------------------------------------------------------------
// 12. Stub Page Renderer
// ---------------------------------------------------------------------------
function renderStub(title) {
    return '<div class="stub-page"><div class="stub-message">' +
        '<h2>' + (title || 'Section') + '</h2>' +
        '<p>Этот раздел не реализован в симуляторе</p>' +
    '</div></div>';
}

// ---------------------------------------------------------------------------
// 13. Utility: clearFaults
// ---------------------------------------------------------------------------
function clearFaults() {
    showNotification('Faults cleared');
}
