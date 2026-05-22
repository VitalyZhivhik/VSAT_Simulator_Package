import logging

from fastapi import APIRouter, HTTPException

from server.database import create_session, get_session, get_setting
from server.models import LoginRequest, LoginResponse

logger = logging.getLogger("vsat.auth")

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    logger.info("Login attempt: name=%s group=%s", req.student_name, req.student_group)
    session_id, is_new = await create_session(req.student_name, req.student_group)

    # Block only NEW registrations when registration is closed
    if is_new:
        reg_open = await get_setting("registration_open")
        if reg_open == "false":
            logger.warning("Registration closed — blocked new student: %s", req.student_name)
            from server.database import delete_session
            await delete_session(session_id)
            raise HTTPException(status_code=403, detail="Registration is closed")

    session = await get_session(session_id)
    if not session:
        logger.error("Failed to create/retrieve session for %s", req.student_name)
        raise HTTPException(status_code=500, detail="Failed to create session")

    logger.info("Login OK: name=%s session=%s is_new=%s", req.student_name, session_id, is_new)
    return LoginResponse(
        session_id=session_id,
        student_name=session["student_name"],
        student_group=session["student_group"],
        is_new_session=is_new,
    )
