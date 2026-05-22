"""Shared utilities for config conversion between DB rows and Pydantic models."""

from server.models import (
    FullConfig,
    SiteConfig,
    RFConfig,
    SearchIDConfig,
    ProfileConfig,
)


def db_row_to_full_config(row: dict) -> FullConfig:
    """Convert a flat DB row dict to a FullConfig model."""
    return FullConfig(
        site=SiteConfig(
            site_name=row["site_name"],
            latitude_deg=row["latitude_deg"],
            latitude_min=row["latitude_min"],
            latitude_dir=row["latitude_dir"],
            longitude_deg=row["longitude_deg"],
            longitude_min=row["longitude_min"],
            longitude_dir=row["longitude_dir"],
        ),
        rf=RFConfig(
            rx1_lo=row["rx1_lo"],
            rx2_lo=row["rx2_lo"],
            tx_lo=row["tx_lo"],
            rx_power=bool(row["rx_power"]),
            rx_10mhz=bool(row["rx_10mhz"]),
            rx1_spinv=bool(row["rx1_spinv"]),
            rx2_spinv=bool(row["rx2_spinv"]),
            tx_spinv=bool(row["tx_spinv"]),
            rx1_freq_adj=row["rx1_freq_adj"],
            rx2_freq_adj=row["rx2_freq_adj"],
            tx_freq_adj=row["tx_freq_adj"],
            tx_power=bool(row["tx_power"]),
        ),
        search_id=SearchIDConfig(
            search_bw_scpc=row["search_bw_scpc"],
            search_bw_tdma=row["search_bw_tdma"],
            net_id=row["net_id"],
            rf_id=row["rf_id"],
            far_end_cn=row["far_end_cn"],
        ),
        profile=ProfileConfig(
            active_profile=row["active_profile"],
            profile_mode=row["profile_mode"],
            profile_autorun=bool(row["profile_autorun"]),
            profile_timeout=row["profile_timeout"],
        ),
    )


def full_config_to_flat(config: FullConfig) -> dict:
    """Convert a FullConfig model to a flat dict matching DB columns."""
    return {
        # Site
        "site_name": config.site.site_name,
        "latitude_deg": config.site.latitude_deg,
        "latitude_min": config.site.latitude_min,
        "latitude_dir": config.site.latitude_dir,
        "longitude_deg": config.site.longitude_deg,
        "longitude_min": config.site.longitude_min,
        "longitude_dir": config.site.longitude_dir,
        # RF
        "rx1_lo": config.rf.rx1_lo,
        "rx2_lo": config.rf.rx2_lo,
        "tx_lo": config.rf.tx_lo,
        "rx_power": int(config.rf.rx_power),
        "rx_10mhz": int(config.rf.rx_10mhz),
        "rx1_spinv": int(config.rf.rx1_spinv),
        "rx2_spinv": int(config.rf.rx2_spinv),
        "tx_spinv": int(config.rf.tx_spinv),
        "rx1_freq_adj": config.rf.rx1_freq_adj,
        "rx2_freq_adj": config.rf.rx2_freq_adj,
        "tx_freq_adj": config.rf.tx_freq_adj,
        "tx_power": int(config.rf.tx_power),
        # Search/ID
        "search_bw_scpc": config.search_id.search_bw_scpc,
        "search_bw_tdma": config.search_id.search_bw_tdma,
        "net_id": config.search_id.net_id,
        "rf_id": config.search_id.rf_id,
        "far_end_cn": config.search_id.far_end_cn,
        # Profile
        "active_profile": config.profile.active_profile,
        "profile_mode": config.profile.profile_mode,
        "profile_autorun": int(config.profile.profile_autorun),
        "profile_timeout": config.profile.profile_timeout,
    }
