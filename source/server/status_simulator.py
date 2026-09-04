"""
Status panel simulation for Comtech CEL-AC 3.

Generates simulated data for the 8 status panels (DEM1, DEM2, MOD, LAN1, LAN2, NET, SYS, MON)
based on the student's current configuration and the reference config.

[?] УТОЧНИТЬ У ПРЕПОДАВАТЕЛЯ:
- Какой SR (symbol rate) показывать в DEM1?
- Какой MODCOD для каждого режима профиля?
- Должен ли C/N зависеть от far_end_cn?
- Как InLvl переходит из NoSig в значение?
- При каких условиях state переходит в UP?
"""

import random
import time

from server.models import FullConfig

# Session start time for uptime calculation
_start_time = time.time()


def _uptime_str() -> str:
    elapsed = int(time.time() - _start_time)
    h = elapsed // 3600
    m = (elapsed % 3600) // 60
    s = elapsed % 60
    return f"+{h:02d}:{m:02d}:{s:02d}"


def simulate_dem1(config: FullConfig, ref: FullConfig) -> dict:
    """Demodulator-1 status panel data."""
    lo_set = config.rf.rx1_lo > 0
    lo_correct = config.rf.rx1_lo == ref.rf.rx1_lo
    power_on = config.rf.rx_power

    if lo_correct and power_on:
        state = "UP"
        inlvl = "-8.0 dBm"
        cn = f"{config.search_id.far_end_cn or 12.5:.1f}"
        modcod = "SF QPSK 1/2"  # [?] УТОЧНИТЬ: зависит от режима профиля
        sr_off = "0.00"
        rx_offset = "0 KHz"
    elif lo_set:
        state = "DOWN"
        inlvl = "NoSig"
        cn = "0.0"
        modcod = "--------"
        sr_off = "-----"
        rx_offset = f"{random.randint(-5, 5)} KHz"
    else:
        state = "DOWN"
        inlvl = "NoSig"
        cn = "0.0"
        modcod = "--------"
        sr_off = "-----"
        rx_offset = "0 KHz"

    return {
        "state": state,
        "last_ud": "never",
        "last_du": "never" if state == "DOWN" else _uptime_str(),
        "lnb_power": "ON" if power_on else "OFF",
        "t10m": "ON" if config.rf.rx_10mhz else "OFF",
        "offset": config.rf.rx1_freq_adj,
        "search_bw": config.search_id.search_bw_scpc,
        "lo": config.rf.rx1_lo,
        "freq": ref.rf.rx1_lo if lo_correct else 1350000,
        "sr": 8300,  # [?] УТОЧНИТЬ
        "input": "RX-1",
        "spi": "ON" if config.rf.rx1_spinv else "OFF",
        "inlvl": inlvl,
        "modcod": modcod,
        "sr_off": sr_off,
        "cn": cn,
        "rx_offset": rx_offset,
        "fix_offset": "0 KHz",
        "rate_bps": 0 if state == "DOWN" else 3168,
        "channels": [{"packets": 0, "bytes": 0, "crc_errors": 0} for _ in range(8)],
    }


def simulate_dem2(config: FullConfig, ref: FullConfig) -> dict:
    """Demodulator-2 — always disabled in simulator."""
    return {
        "state": "Disabled",
        "last_ud": "never",
        "last_du": "never",
        "lnb_power": "OFF",
        "t10m": "OFF",
        "offset": 0,
        "search_bw": 0,
        "lo": config.rf.rx2_lo,
        "freq": 0,
        "sr": 0,
        "input": "RX-2",
        "spi": "OFF",
        "inlvl": "NoSig",
        "modcod": "--------",
        "sr_off": "-----",
        "cn": "0.0",
        "rx_offset": "0 KHz",
        "fix_offset": "0 KHz",
        "rate_bps": 0,
        "channels": [{"packets": 0, "bytes": 0, "crc_errors": 0} for _ in range(8)],
    }


def simulate_mod(config: FullConfig, ref: FullConfig) -> dict:
    """Modulator status panel data."""
    tx_set = config.rf.tx_lo > 0
    tx_correct = config.rf.tx_lo == ref.rf.tx_lo
    tx_on = config.rf.tx_power

    if tx_correct and tx_on:
        state = "UP"
        out_lvl = "-15.0 dBm/TLC"
        rate = 5995
    elif tx_set:
        state = "DOWN"
        out_lvl = "OFF"
        rate = 0
    else:
        state = "DOWN"
        out_lvl = "OFF"
        rate = 0

    return {
        "state": state,
        "last_ud": "never",
        "last_du": "never" if state == "DOWN" else _uptime_str(),
        "type": "Internal",
        "freq": config.rf.tx_lo,
        "freq_adj": config.rf.tx_freq_adj,
        "sr": 4096,  # [?] УТОЧНИТЬ
        "set_lvl": "-0.0",
        "max_lvl": "-15.0",
        "t10m": "ON" if config.rf.rx_10mhz else "OFF",
        "lo": config.rf.tx_lo,
        "fix_corr": 0,
        "br": 0,
        "out_lvl": out_lvl,
        "tx": "ON" if tx_on else "OFF",
        "v24": "ON" if tx_on else "OFF",
        "mode": "DVB-S2X",
        "modcod": "SF QPSK 1/2",  # [?] УТОЧНИТЬ
        "rolloff": "20%",
        "pilots": "OFF",
        "rate_bps": rate,
        "load_pct": 0,
        "bw_bps": 4096,
        "shaper_drops": 0,
        "queues": [{"packets": 0, "bytes": 0, "q_len": 0, "drops": 0} for _ in range(8)],
    }


def simulate_lan1(config: FullConfig, ref: FullConfig) -> dict:
    """LAN1 (Ethernet) — always UP."""
    return {
        "state": "UP",
        "last_ud": _uptime_str(),
        "last_du": _uptime_str(),
        "mac": "46:13:20:09:73:60",
        "eth1_set": "AUTO",
        "eth1_state": "1G/FD",
        "eth2_set": "AUTO",
        "eth2_state": "No link",
        "rx_rate": random.randint(3000, 5000),
        "tx_rate": random.randint(5000, 8000),
        "rx_bytes": random.randint(800000, 1200000),
        "tx_bytes": random.randint(1000000, 1600000),
        "rx_pkts": random.randint(5000, 8000),
        "tx_pkts": random.randint(3000, 5000),
        "broadcasts": random.randint(200, 500),
        "crc_errors": 0,
        "collisions": 0,
    }


def simulate_lan2(config: FullConfig, ref: FullConfig) -> dict:
    """LAN2 — No link."""
    return {
        "state": "DOWN",
        "last_ud": "never",
        "last_du": "never",
        "mac": "46:13:20:09:73:61",
        "eth1_set": "AUTO",
        "eth1_state": "No link",
        "eth2_set": "AUTO",
        "eth2_state": "No link",
        "rx_rate": 0,
        "tx_rate": 0,
        "rx_bytes": 0,
        "tx_bytes": 0,
        "rx_pkts": 0,
        "tx_pkts": 0,
        "broadcasts": 0,
        "crc_errors": 0,
        "collisions": 0,
    }


def simulate_net(config: FullConfig, ref: FullConfig) -> dict:
    """Network status panel."""
    mode = config.profile.profile_mode
    if mode == "none":
        mode_display = "---"
    else:
        mode_display = mode

    # Determine state based on overall config
    dem1_ok = config.rf.rx1_lo == ref.rf.rx1_lo and config.rf.rx_power
    mod_ok = config.rf.tx_lo == ref.rf.tx_lo and config.rf.tx_power
    net_ok = config.search_id.net_id == ref.search_id.net_id and config.search_id.rf_id == ref.search_id.rf_id

    if dem1_ok and mod_ok and net_ok:
        state = "RX OK"  # [?] УТОЧНИТЬ: точные условия
    elif dem1_ok:
        state = "No TX"
    else:
        state = "No RX"

    return {
        "mode": mode_display,
        "state": state,
        "inroute": 0,
        "tx_freq": config.rf.tx_lo,
        "mesh_mc": "-",
        "sl_len": 0,
        "fr_len": 0,
        "st_num": 0,
        "act_channels": 1,
        "ldpct": "Norm",
        "bit_rate": 0,
        "sl_dur": "0.0",
        "fr_dur": 0,
        "station_num": 0,
        "cur_bw": "0 (0 k)",
        "fp_lost": 0,
        "dtts_cor": 0,
        "frq_cor": 0,
        "lvl_cor": "0.0",
        "dtts_fix_cor": 0,
        "frq_fix_cor": 0,
        "tx_rate_k": 0,
        "tot_rq": 0,
        "rt_rq": 0,
        "codecs": "0 / 0",
        "timing_mode": "Value",
        "net_tts": 0,
        "sat_pos": f"{config.site.longitude_deg} d {config.site.longitude_min} ' {config.site.longitude_dir}",
        "set_location": f"{config.site.latitude_deg}d {config.site.latitude_min}' {config.site.latitude_dir} / {config.site.longitude_deg}d {config.site.longitude_min}' {config.site.longitude_dir}",
    }


def simulate_sys(config: FullConfig, ref: FullConfig) -> dict:
    """System status panel."""
    return {
        "sw_version": "CEL-20X Software(H/W CEL-200X) Ver: 3.8.1.40 (21.02.2023)",
        "sn": "20097360",
        "uptime": _uptime_str(),
        "current_time": _uptime_str(),
        "timezone": 0,
        "rate_avg_time": 5,
        "buffers_free": random.randint(15000, 16500),
        "no_buffer": 0,
        "sc_desc": random.randint(8000, 8500),
        "cpu_load": random.randint(18, 28),
        "idle_timeout": 10,
        "temperature": random.randint(58, 66),
        "last_telnet_ip": "0.0.0.0",
        "auto_restart_delay": 3,
        "sw_errors": "No SW errors",
        "config_errors": "No config errors",
        "cfg": "saveconf_active",   # или "saveconf"
        "flt": "clearfaults",       # или "clearfaults_active"
        "site_name": config.site.site_name,
        "profile_num": config.profile.active_profile,
        "state_weight": "600",
        "state_lock": "hidden",     # или "visible"
        "profile_mode": config.profile.profile_mode,
        "profile_active": config.profile.active_profile,
        "profile_autorun": config.profile.profile_autorun,
        "profile_timeout": config.profile.profile_timeout,
    }


def simulate_mon(config: FullConfig, ref: FullConfig) -> dict:
    """Monitoring panel — always OFF in simulator."""
    return {
        "state": "OFF",
        "faults": "",
        "ping_interval": 5,
        "lost_allowed": 0,
        "local_state": "OFF",
        "local_host": "0.0.0.0",
        "local_vlan": 0,
        "local_delay_check": "OFF",
        "local_delay": 600,
        "network_state": "OFF",
        "network_host": "0.0.0.0",
        "network_vlan": 0,
        "network_delay_check": "OFF",
        "network_delay": 600,
        "lan_rx_state": "OFF",
        "lan_rx_threshold": 0,
        "lan_tx_state": "OFF",
        "lan_tx_threshold": 0,
        "backup_state": "OFF",
        "backup_ip": "0.0.0.0",
        "auto_reboot_state": "OFF",
        "auto_reboot_delay": 3,
    }


# Panel name -> simulator function mapping
PANEL_SIMULATORS = {
    "dem1": simulate_dem1,
    "dem2": simulate_dem2,
    "mod": simulate_mod,
    "lan1": simulate_lan1,
    "lan2": simulate_lan2,
    "net": simulate_net,
    "sys": simulate_sys,
    "mon": simulate_mon,
}


def simulate_panel(panel_name: str, config: FullConfig, ref: FullConfig) -> dict | None:
    """Simulate a status panel. Returns None if panel_name is invalid."""
    simulator = PANEL_SIMULATORS.get(panel_name)
    if simulator:
        return simulator(config, ref)
    return None
