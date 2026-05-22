import logging

from fastapi import APIRouter, HTTPException

logger = logging.getLogger("vsat.session")

from server.database import (
    get_session,
    get_student_config,
    get_reference_config,
    save_student_config,
    reset_student_config,
    update_last_activity,
)
from server.models import (
    FullConfig,
    SessionInfo,
    ComtechStatus,
)
from server.utils import db_row_to_full_config, full_config_to_flat
from server.status_simulator import simulate_panel
from server.routes.websocket import manager

router = APIRouter()


def _compute_status(config: FullConfig, ref: FullConfig | None = None) -> ComtechStatus:
    """Compute Comtech-style status indicators (8 modules)."""
    rf = config.rf
    sid = config.search_id
    profile = config.profile

    # LAN1: always green (simulated Ethernet always up)
    lan1 = "cg"
    # LAN2: always disabled
    lan2 = "cwd"

    # DEM1: depends on rx1_lo
    if rf.rx1_lo > 0 and rf.rx_power:
        if ref and rf.rx1_lo == ref.rf.rx1_lo:
            dem1 = "cg"  # locked
        else:
            dem1 = "cy"  # set but not correct / no lock
    elif rf.rx1_lo > 0:
        dem1 = "cy"  # frequency set but power off
    else:
        dem1 = "cr"  # not configured

    # DEM2: always disabled
    dem2 = "cwd"

    # MOD: depends on tx_lo + tx_power
    if rf.tx_lo > 0 and rf.tx_power:
        if ref and rf.tx_lo == ref.rf.tx_lo:
            mod = "cg"
        else:
            mod = "cy"
    elif rf.tx_lo > 0:
        mod = "cy"
    else:
        mod = "cr"

    # NET: depends on net_id + rf_id
    if sid.net_id > 0 and sid.rf_id > 0:
        if ref and sid.net_id == ref.search_id.net_id and sid.rf_id == ref.search_id.rf_id:
            net = "cg"
        else:
            net = "cy"
    elif sid.net_id > 0 or sid.rf_id > 0:
        net = "cy"
    else:
        net = "cr"

    # SYS: always green
    sys_st = "cg"

    # MON: always off (monitoring disabled)
    mon = "cw"

    # Overall state
    # [?] УТОЧНИТЬ У ПРЕПОДАВАТЕЛЯ: точные условия перехода в UP
    if dem1 == "cg" and mod == "cg" and net == "cg":
        state = "UP"
        state_color = "#7dd228"
        sys_led = "cg"
        system_status = "Online"
    elif dem1 in ("cg", "cy") or mod in ("cg", "cy"):
        state = "DOWN"
        state_color = "#fe5e37"
        sys_led = "cy"
        system_status = "Configuring..."
    else:
        state = "No RX"
        state_color = "#fe5e37"
        sys_led = "cr"
        system_status = "Configuring..."

    profile_text = f"{profile.active_profile}-{profile.profile_mode}"

    return ComtechStatus(
        sys_led=sys_led,
        lan1=lan1,
        lan2=lan2,
        dem1=dem1,
        dem2=dem2,
        mod=mod,
        net=net,
        sys_st=sys_st,
        mon=mon,
        state=state,
        state_color=state_color,
        profile_text=profile_text,
        system_status=system_status,
    )


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    config_row = await get_student_config(session_id)
    if not config_row:
        raise HTTPException(status_code=404, detail="Configuration not found")

    await update_last_activity(session_id)

    return SessionInfo(
        session_id=session["id"],
        student_name=session["student_name"],
        student_group=session["student_group"],
        status=session["status"],
        connection_time=session["connection_time"],
        last_activity=session["last_activity"],
        config=db_row_to_full_config(config_row),
    )


@router.post("/{session_id}/config")
async def save_config(session_id: str, config: FullConfig):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    logger.info("Config saved: session=%s name=%s", session_id, session["student_name"])
    flat = full_config_to_flat(config)
    await save_student_config(session_id, flat)

    # Get reference for status computation
    ref_row = await get_reference_config()
    ref_config = db_row_to_full_config(ref_row)

    # Send real-time status update to student
    status = _compute_status(config, ref_config)
    await manager.send_to_session(session_id, {
        "type": "status_update",
        "data": status.model_dump(),
    })
    # Notify admins that student config changed
    await manager.notify_admins({
        "type": "student_updated",
        "session_id": session_id,
        "student_name": session["student_name"],
    })

    return {"status": "ok"}


@router.get("/{session_id}/status", response_model=ComtechStatus)
async def get_status(session_id: str):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    config_row = await get_student_config(session_id)
    if not config_row:
        raise HTTPException(status_code=404, detail="Configuration not found")

    await update_last_activity(session_id)

    config = db_row_to_full_config(config_row)
    ref_row = await get_reference_config()
    ref_config = db_row_to_full_config(ref_row)
    return _compute_status(config, ref_config)


@router.get("/{session_id}/panels/{panel_name}")
async def get_panel_data(session_id: str, panel_name: str):
    """Get simulated status panel data."""
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    config_row = await get_student_config(session_id)
    if not config_row:
        raise HTTPException(status_code=404, detail="Configuration not found")

    ref_row = await get_reference_config()

    config = db_row_to_full_config(config_row)
    ref_config = db_row_to_full_config(ref_row)

    data = simulate_panel(panel_name, config, ref_config)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Unknown panel: {panel_name}")

    return data


@router.post("/{session_id}/reset")
async def reset_config(session_id: str):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await reset_student_config(session_id)
    logger.info("Config reset: session=%s name=%s", session_id, session["student_name"])

    return {"status": "ok", "message": "Configuration reset to factory defaults"}
