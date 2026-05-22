from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Literal


# ── Authentication ────────────────────────────────────────────


class LoginRequest(BaseModel):
    student_name: str = Field(..., min_length=1, max_length=100)
    student_group: str = Field(..., min_length=1, max_length=50)


class LoginResponse(BaseModel):
    session_id: str
    student_name: str
    student_group: str
    is_new_session: bool


# ── Comtech CEL-AC 3 Configuration ───────────────────────────


class SiteConfig(BaseModel):
    site_name: str = Field(default="AC 3", max_length=20)
    latitude_deg: int = Field(default=0, ge=0, le=90)
    latitude_min: int = Field(default=0, ge=0, le=59)
    latitude_dir: Literal["N", "S"] = "N"
    longitude_deg: int = Field(default=0, ge=0, le=180)
    longitude_min: int = Field(default=0, ge=0, le=59)
    longitude_dir: Literal["E", "W"] = "E"


class RFConfig(BaseModel):
    rx1_lo: int = Field(default=0, ge=0)          # kHz, 0 or 2675000-33000000
    rx2_lo: int = Field(default=0, ge=0)          # kHz, 0 or 2675000-33000000
    tx_lo: int = Field(default=0, ge=0)           # kHz, 0 or 2675000-35000000
    rx_power: bool = False                         # LNB power (shared Rx1/Rx2)
    rx_10mhz: bool = False                         # 10MHz reference
    rx1_spinv: bool = False                        # Spectrum inversion Rx1
    rx2_spinv: bool = False                        # Spectrum inversion Rx2
    tx_spinv: bool = False                         # Spectrum inversion TX
    rx1_freq_adj: int = Field(default=0, ge=0, le=4095)   # kHz
    rx2_freq_adj: int = Field(default=0, ge=0, le=4095)   # kHz
    tx_freq_adj: int = Field(default=0, ge=0, le=4095)    # kHz
    tx_power: bool = False                         # TX enable (24V)


class SearchIDConfig(BaseModel):
    search_bw_scpc: int = Field(default=1800, ge=0, le=10000)   # kHz
    search_bw_tdma: int = Field(default=12)                      # enum: 6, 12, 24, 40
    net_id: int = Field(default=0, ge=0, le=255)
    rf_id: int = Field(default=0, ge=0, le=255)
    far_end_cn: int = Field(default=0, ge=0, le=30)             # dB


class ProfileConfig(BaseModel):
    active_profile: int = Field(default=1, ge=1, le=8)
    profile_mode: str = "none"
    profile_autorun: bool = False
    profile_timeout: int = Field(default=10, ge=10, le=250)


class FullConfig(BaseModel):
    site: SiteConfig = Field(default_factory=SiteConfig)
    rf: RFConfig = Field(default_factory=RFConfig)
    search_id: SearchIDConfig = Field(default_factory=SearchIDConfig)
    profile: ProfileConfig = Field(default_factory=ProfileConfig)


# ── Session ───────────────────────────────────────────────────


class SessionInfo(BaseModel):
    session_id: str
    student_name: str
    student_group: str
    status: str
    connection_time: str
    last_activity: str
    config: FullConfig


class ComtechStatus(BaseModel):
    sys_led: Literal["cg", "cy", "cr", "cw"] = "cw"
    lan1: Literal["cg", "cy", "cr", "cw", "cwd"] = "cg"
    lan2: Literal["cg", "cy", "cr", "cw", "cwd"] = "cwd"
    dem1: Literal["cg", "cy", "cr", "cw", "cwd"] = "cr"
    dem2: Literal["cg", "cy", "cr", "cw", "cwd"] = "cwd"
    mod: Literal["cg", "cy", "cr", "cw", "cwd"] = "cr"
    net: Literal["cg", "cy", "cr", "cw", "cwd"] = "cr"
    sys_st: Literal["cg", "cy", "cr", "cw", "cwd"] = "cg"
    mon: Literal["cg", "cy", "cr", "cw", "cwd"] = "cw"
    state: str = "No RX"
    state_color: str = "#fe5e37"
    profile_text: str = "1-none"
    system_status: str = "Configuring..."


# ── Console / Ping ────────────────────────────────────────────


class ConsoleCommand(BaseModel):
    command: str


class ConsoleResponse(BaseModel):
    output: str


class PingRequest(BaseModel):
    target_ip: str
    config: FullConfig


class PingResponse(BaseModel):
    output: str
    loss_percent: int
    validation_summary: Optional[ValidationResult] = None


# ── Validation ────────────────────────────────────────────────


class ParameterResult(BaseModel):
    name: str
    category: Literal["site", "rf", "search_id", "profile"]
    student_value: str
    reference_value: str
    is_correct: bool
    tolerance: Optional[str] = None


class ValidationResult(BaseModel):
    overall_correct: bool
    site_correct: bool
    rf_correct: bool
    search_id_correct: bool
    profile_correct: bool
    correct_count: int
    total_count: int
    percentage: float
    loss_percent: int
    details: list[ParameterResult]


# Rebuild PingResponse now that ValidationResult is defined
PingResponse.model_rebuild()


# ── Admin ─────────────────────────────────────────────────────


class StudentListItem(BaseModel):
    session_id: str
    student_name: str
    student_group: str
    status: str
    connection_time: str
    last_activity: str
    correct_percentage: float


class StudentDetail(BaseModel):
    session: SessionInfo
    validation: ValidationResult
    console_history: list[dict]


class ServerSettingsUpdate(BaseModel):
    partial_mode: Optional[bool] = None
    registration_open: Optional[bool] = None
    admin_password: Optional[str] = None


class ServerSettingsResponse(BaseModel):
    partial_mode: bool
    registration_open: bool
    help_text: str


class HelpTextUpdate(BaseModel):
    help_text: str
