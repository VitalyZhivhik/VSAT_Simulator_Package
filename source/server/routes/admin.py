import csv
import io
import logging

from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse

logger = logging.getLogger("vsat.admin")

from server.database import (
    get_all_sessions,
    get_session,
    get_student_config,
    get_reference_config,
    save_reference_config,
    get_setting,
    set_setting,
    get_console_history,
    delete_session,
    reset_student_config,
)
from server.models import (
    FullConfig,
    StudentListItem,
    StudentDetail,
    SessionInfo,
    ServerSettingsUpdate,
    ServerSettingsResponse,
    HelpTextUpdate,
    ValidationResult,
)
from server.utils import db_row_to_full_config, full_config_to_flat
from server.validation import validate_config

router = APIRouter()


async def verify_admin(x_admin_password: str = Header(...)):
    stored = await get_setting("admin_password")
    if x_admin_password != stored:
        logger.warning("Admin auth failed (wrong password)")
        raise HTTPException(status_code=401, detail="Invalid admin password")


async def _get_validation_for_session(
    session_id: str,
) -> tuple[FullConfig, ValidationResult] | None:
    config_row = await get_student_config(session_id)
    if not config_row:
        return None

    student_config = db_row_to_full_config(config_row)
    ref_row = await get_reference_config()
    reference_config = db_row_to_full_config(ref_row)

    partial_mode_str = await get_setting("partial_mode")
    partial_mode = partial_mode_str == "true"

    result = validate_config(student_config, reference_config, partial_mode)
    return student_config, result


# ── Student List ──────────────────────────────────────────────


@router.get(
    "/students",
    response_model=list[StudentListItem],
    dependencies=[Depends(verify_admin)],
)
async def list_students():
    sessions = await get_all_sessions()
    items: list[StudentListItem] = []

    for s in sessions:
        vr = await _get_validation_for_session(s["id"])
        pct = vr[1].percentage if vr else 0.0

        items.append(StudentListItem(
            session_id=s["id"],
            student_name=s["student_name"],
            student_group=s["student_group"],
            status=s["status"],
            connection_time=s["connection_time"],
            last_activity=s["last_activity"],
            correct_percentage=pct,
        ))

    return items


# ── Student Detail ────────────────────────────────────────────


@router.get(
    "/student/{session_id}",
    response_model=StudentDetail,
    dependencies=[Depends(verify_admin)],
)
async def get_student_detail(session_id: str):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    vr = await _get_validation_for_session(session_id)
    if not vr:
        raise HTTPException(status_code=404, detail="Configuration not found")

    student_config, validation = vr
    history = await get_console_history(session_id)

    return StudentDetail(
        session=SessionInfo(
            session_id=session["id"],
            student_name=session["student_name"],
            student_group=session["student_group"],
            status=session["status"],
            connection_time=session["connection_time"],
            last_activity=session["last_activity"],
            config=student_config,
        ),
        validation=validation,
        console_history=history,
    )


# ── Reference Configuration ──────────────────────────────────


@router.get(
    "/reference",
    response_model=FullConfig,
    dependencies=[Depends(verify_admin)],
)
async def get_reference():
    ref_row = await get_reference_config()
    return db_row_to_full_config(ref_row)


@router.post("/reference", dependencies=[Depends(verify_admin)])
async def update_reference(config: FullConfig):
    flat = full_config_to_flat(config)
    await save_reference_config(flat)
    return {"status": "ok", "message": "Reference configuration updated"}


# ── Server Settings ───────────────────────────────────────────


@router.get(
    "/settings",
    response_model=ServerSettingsResponse,
    dependencies=[Depends(verify_admin)],
)
async def get_settings():
    partial_mode = await get_setting("partial_mode")
    reg_open = await get_setting("registration_open")
    help_text = await get_setting("help_text")

    return ServerSettingsResponse(
        partial_mode=partial_mode == "true",
        registration_open=reg_open == "true",
        help_text=help_text or "",
    )


@router.post("/settings", dependencies=[Depends(verify_admin)])
async def update_settings(settings: ServerSettingsUpdate):
    if settings.partial_mode is not None:
        await set_setting("partial_mode", str(settings.partial_mode).lower())
    if settings.registration_open is not None:
        await set_setting("registration_open", str(settings.registration_open).lower())
    if settings.admin_password is not None:
        await set_setting("admin_password", settings.admin_password)
    return {"status": "ok"}


# ── Help Text ─────────────────────────────────────────────────


@router.get("/help-text", dependencies=[Depends(verify_admin)])
async def get_help_text():
    text = await get_setting("help_text")
    return {"help_text": text or ""}


@router.post("/help-text", dependencies=[Depends(verify_admin)])
async def update_help_text(body: HelpTextUpdate):
    await set_setting("help_text", body.help_text)
    return {"status": "ok"}


# ── Student Management ────────────────────────────────────────


@router.post("/student/{session_id}/reset", dependencies=[Depends(verify_admin)])
async def admin_reset_student(session_id: str):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await reset_student_config(session_id)
    return {"status": "ok", "message": "Student configuration reset"}


@router.delete("/student/{session_id}", dependencies=[Depends(verify_admin)])
async def admin_kick_student(session_id: str):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await delete_session(session_id)
    return {"status": "ok", "message": "Student disconnected"}


# ── CSV Export ────────────────────────────────────────────────


@router.get("/export", dependencies=[Depends(verify_admin)])
async def export_results():
    sessions = await get_all_sessions()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Name", "Group", "Correct Parameters", "Total Parameters",
        "Percentage", "Status", "Connection Time", "Last Activity",
    ])

    for s in sessions:
        vr = await _get_validation_for_session(s["id"])
        if vr:
            _, validation = vr
            writer.writerow([
                s["student_name"],
                s["student_group"],
                validation.correct_count,
                validation.total_count,
                validation.percentage,
                s["status"],
                s["connection_time"],
                s["last_activity"],
            ])
        else:
            writer.writerow([
                s["student_name"],
                s["student_group"],
                0, 0, 0.0,
                s["status"],
                s["connection_time"],
                s["last_activity"],
            ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=comtech_results.csv"},
    )
