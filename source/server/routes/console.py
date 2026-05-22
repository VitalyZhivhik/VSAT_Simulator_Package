import logging

from fastapi import APIRouter, HTTPException

logger = logging.getLogger("vsat.console")

from server.database import (
    get_session,
    get_student_config,
    get_reference_config,
    get_setting,
    add_console_entry,
    update_session_status,
    update_ping_stats,
)
from server.models import (
    ConsoleCommand,
    ConsoleResponse,
    PingResponse,
)
from server.utils import db_row_to_full_config
from server.validation import validate_config
from server.ping_simulator import generate_ping_output
from server.routes.websocket import manager

router = APIRouter()

HELP_TEXT = """\
Available commands:
  ping <ip_address>  - Test connectivity to satellite/hub
  help               - Show this help message\
"""


def _parse_command(raw: str) -> tuple[str, list[str]]:
    parts = raw.strip().split()
    if not parts:
        return ("", [])
    return (parts[0].lower(), parts[1:])


@router.post("/{session_id}/command", response_model=ConsoleResponse)
async def execute_command(session_id: str, cmd: ConsoleCommand):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    command_name, args = _parse_command(cmd.command)
    logger.debug("Command from session=%s: %s", session_id, cmd.command)

    if command_name == "help":
        output = HELP_TEXT
    elif command_name == "ping":
        if not args:
            output = "Usage: ping <ip_address>"
        else:
            target_ip = args[0]
            logger.info("PING session=%s name=%s target=%s",
                        session_id, session["student_name"], target_ip)

            config_row = await get_student_config(session_id)
            if not config_row:
                raise HTTPException(status_code=404, detail="Configuration not found")

            student_config = db_row_to_full_config(config_row)

            ref_row = await get_reference_config()
            reference_config = db_row_to_full_config(ref_row)

            partial_mode_str = await get_setting("partial_mode")
            partial_mode = partial_mode_str == "true"

            result = validate_config(student_config, reference_config, partial_mode)

            logger.info("PING result: session=%s correct=%d/%d (%.1f%%) loss=%d%%",
                        session_id, result.correct_count, result.total_count,
                        result.percentage, result.loss_percent)

            output = generate_ping_output(target_ip, result.loss_percent)

            # Update session status
            if result.loss_percent == 0:
                await update_session_status(session_id, "completed")
            else:
                await update_session_status(session_id, "testing")

            # Update ping stats
            await update_ping_stats(session_id, result.loss_percent == 0)

            # Send validation result over WebSocket
            await manager.send_to_session(session_id, {
                "type": "ping_result",
                "data": {
                    "output": output,
                    "loss_percent": result.loss_percent,
                    "overall_correct": result.overall_correct,
                    "percentage": result.percentage,
                },
            })
            # Notify admins about student activity
            await manager.notify_admins({
                "type": "student_updated",
                "session_id": session_id,
                "student_name": session["student_name"],
            })
    elif command_name == "":
        output = ""
    else:
        output = f"Unknown command: '{command_name}'. Type 'help' for available commands."

    # Log to console history
    if command_name:
        await add_console_entry(session_id, cmd.command, output)

    return ConsoleResponse(output=output)


@router.post("/{session_id}/ping", response_model=PingResponse)
async def execute_ping(session_id: str, target_ip: str = ""):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not target_ip:
        raise HTTPException(status_code=400, detail="target_ip is required")

    config_row = await get_student_config(session_id)
    if not config_row:
        raise HTTPException(status_code=404, detail="Configuration not found")

    student_config = db_row_to_full_config(config_row)

    ref_row = await get_reference_config()
    reference_config = db_row_to_full_config(ref_row)

    partial_mode_str = await get_setting("partial_mode")
    partial_mode = partial_mode_str == "true"

    result = validate_config(student_config, reference_config, partial_mode)
    output = generate_ping_output(target_ip, result.loss_percent)

    if result.loss_percent == 0:
        await update_session_status(session_id, "completed")
    else:
        await update_session_status(session_id, "testing")

    await update_ping_stats(session_id, result.loss_percent == 0)
    await add_console_entry(session_id, f"ping {target_ip}", output)

    await manager.send_to_session(session_id, {
        "type": "ping_result",
        "data": {
            "output": output,
            "loss_percent": result.loss_percent,
            "overall_correct": result.overall_correct,
            "percentage": result.percentage,
        },
    })
    await manager.notify_admins({
        "type": "student_updated",
        "session_id": session_id,
        "student_name": session["student_name"],
    })

    return PingResponse(
        output=output,
        loss_percent=result.loss_percent,
        validation_summary=result,
    )
