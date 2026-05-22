import json
import copy
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = {
    "server": {
        "host": "0.0.0.0",
        "port": 8080,
        "debug": False,
    },
    "admin": {
        "password": "admin",
    },
    "simulation": {
        "partial_mode": True,
        "max_students": 30,
        "ping_packet_count": 4,
        "base_latency_ms": 540,
        "jitter_ms": 5,
    },
    "database": {
        "path": "data/vsat.db",
    },
}

# All Comtech parameter columns (shared between student_configs and reference_config)
CONFIG_COLUMNS = [
    # Site
    "site_name", "latitude_deg", "latitude_min", "latitude_dir",
    "longitude_deg", "longitude_min", "longitude_dir",
    # RF Interface
    "rx1_lo", "rx2_lo", "tx_lo",
    "rx_power", "rx_10mhz",
    "rx1_spinv", "rx2_spinv", "tx_spinv",
    "rx1_freq_adj", "rx2_freq_adj", "tx_freq_adj",
    "tx_power",
    # Search / Identification
    "search_bw_scpc", "search_bw_tdma",
    "net_id", "rf_id", "far_end_cn",
    # Profile
    "active_profile", "profile_mode", "profile_autorun", "profile_timeout",
]

FACTORY_DEFAULTS = {
    # Site
    "site_name": "AC 3",
    "latitude_deg": 0,
    "latitude_min": 0,
    "latitude_dir": "N",
    "longitude_deg": 0,
    "longitude_min": 0,
    "longitude_dir": "E",
    # RF Interface
    "rx1_lo": 0,
    "rx2_lo": 0,
    "tx_lo": 0,
    "rx_power": 0,       # bool stored as int in SQLite
    "rx_10mhz": 0,
    "rx1_spinv": 0,
    "rx2_spinv": 0,
    "tx_spinv": 0,
    "rx1_freq_adj": 0,
    "rx2_freq_adj": 0,
    "tx_freq_adj": 0,
    "tx_power": 0,
    # Search / Identification
    "search_bw_scpc": 1800,
    "search_bw_tdma": 12,
    "net_id": 0,
    "rf_id": 0,
    "far_end_cn": 0,
    # Profile
    "active_profile": 1,
    "profile_mode": "none",
    "profile_autorun": 0,
    "profile_timeout": 10,
}

REFERENCE_DEFAULTS = {
    # Site
    "site_name": "AC 3",
    "latitude_deg": 32,
    "latitude_min": 0,
    "latitude_dir": "N",
    "longitude_deg": 35,
    "longitude_min": 0,
    "longitude_dir": "E",
    # RF Interface
    "rx1_lo": 9750000,
    "rx2_lo": 0,
    "tx_lo": 13050000,
    "rx_power": 1,
    "rx_10mhz": 1,
    "rx1_spinv": 0,
    "rx2_spinv": 0,
    "tx_spinv": 0,
    "rx1_freq_adj": 0,
    "rx2_freq_adj": 0,
    "tx_freq_adj": 0,
    "tx_power": 1,
    # Search / Identification
    "search_bw_scpc": 1800,
    "search_bw_tdma": 12,
    "net_id": 1,
    "rf_id": 1,
    "far_end_cn": 12,
    # Profile
    "active_profile": 1,
    "profile_mode": "Star station",
    "profile_autorun": 1,
    "profile_timeout": 10,
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


_cached_config: dict[str, Any] | None = None


def load_config(config_path: str = "config.json") -> dict[str, Any]:
    global _cached_config
    if _cached_config is not None:
        return _cached_config

    path = Path(config_path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
        _cached_config = _deep_merge(DEFAULT_CONFIG, user_config)
    else:
        _cached_config = copy.deepcopy(DEFAULT_CONFIG)

    return _cached_config


def reset_config_cache() -> None:
    global _cached_config
    _cached_config = None
