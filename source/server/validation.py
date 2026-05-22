import random

from server.models import (
    FullConfig,
    ValidationResult,
    ParameterResult,
)

# Parameter definitions: (category, name, tolerance, comparison_type)
# comparison_type: "exact" (string), "numeric_exact" (number), "bool" (boolean)
#
# Логика основана на реальном Comtech ELEVATE CEL-200:
# - LO частоты (rx1_lo, tx_lo) критичны — без правильного LO демодулятор не захватит сигнал
# - rx_power (LNB питание) и tx_power (BUC 24V) — без питания нет сигнала
# - net_id / rf_id — без правильной идентификации станция не войдёт в сеть
# - profile_mode — определяет режим работы (Star station, SCPC и т.д.)
# - Координаты — нужны для TDMA timing (расчёт задержки до спутника)
# - site_name, search_bw, profile_timeout — НЕ влияют на связь, но проверяются
#   для полноты лабораторной работы
#
PARAM_DEFS: list[tuple[str, str, float | None, str]] = [
    # Site — координаты влияют на TDMA timing (расчёт DTTS задержки до спутника)
    ("site", "latitude_deg", None, "numeric_exact"),
    ("site", "latitude_min", None, "numeric_exact"),
    ("site", "latitude_dir", None, "exact"),
    ("site", "longitude_deg", None, "numeric_exact"),
    ("site", "longitude_min", None, "numeric_exact"),
    ("site", "longitude_dir", None, "exact"),
    # RF Interface — критичные параметры для физического канала
    ("rf", "rx1_lo", None, "numeric_exact"),       # LO приёмника — без него нет захвата
    ("rf", "tx_lo", None, "numeric_exact"),         # LO передатчика — без него нет TX
    ("rf", "rx_power", None, "bool"),               # LNB питание — без него LNB мёртв
    ("rf", "rx_10mhz", None, "bool"),               # опорный генератор 10 МГц
    ("rf", "rx1_spinv", None, "bool"),              # инверсия спектра Rx1
    ("rf", "tx_spinv", None, "bool"),               # инверсия спектра TX
    ("rf", "tx_power", None, "bool"),               # BUC 24V питание — без него нет передачи
    # Search / ID — идентификация в сети
    ("search_id", "net_id", None, "numeric_exact"), # ID сети — без него не войдёшь в сеть
    ("search_id", "rf_id", None, "numeric_exact"),  # ID RF канала
    ("search_id", "far_end_cn", None, "numeric_exact"),  # C/N на дальнем конце
    # Profile — режим работы
    ("profile", "profile_mode", None, "exact"),     # Star station / SCPC / Hub etc.
]


def _get_param_value(config: FullConfig, category: str, name: str):
    if category == "site":
        return getattr(config.site, name)
    elif category == "rf":
        return getattr(config.rf, name)
    elif category == "search_id":
        return getattr(config.search_id, name)
    elif category == "profile":
        return getattr(config.profile, name)
    return None


def _compare(student_val, ref_val, comp_type: str, tolerance: float | None) -> bool:
    if comp_type == "exact":
        return str(student_val) == str(ref_val)
    elif comp_type == "numeric_exact":
        try:
            return float(student_val) == float(ref_val)
        except (ValueError, TypeError):
            return str(student_val) == str(ref_val)
    elif comp_type == "bool":
        return bool(student_val) == bool(ref_val)
    elif comp_type == "numeric_tolerance":
        return abs(float(student_val) - float(ref_val)) <= tolerance
    return False


def _compute_loss(
    site_ok: bool, rf_ok: bool, search_ok: bool, profile_ok: bool,
    partial_mode: bool
) -> int:
    """
    Логика основана на реальной работе спутникового коммутатора:

    Strict mode: все верно -> 0%, иначе -> 100%.

    Partial mode (реалистичная деградация):
      1. RF LO неверен (rx1_lo/tx_lo) -> 100% — демодулятор не захватит сигнал,
         модулятор передаёт на неверной частоте. Также: LNB/BUC питание выключено.
      2. Search/ID неверен (net_id/rf_id) -> 100% — станция не идентифицируется
         в сети, хаб отвергает TDMA burst запросы.
      3. Profile неверен (не тот режим) -> 75% — протоколы не совпадают,
         частичная работа возможна в broadcast.
      4. Site координаты неверны -> 50% — TDMA timing неверный (DTTS задержка
         рассчитана неправильно), burst-ы приходят не в свой слот.
      5. Всё верно -> 0%.

    [?] УТОЧНИТЬ У ПРЕПОДАВАТЕЛЯ: подтвердить приоритеты.
    """
    if not partial_mode:
        return 0 if (site_ok and rf_ok and search_ok and profile_ok) else 100

    # RF — самый критичный: без правильного LO и питания сигнала нет
    if not rf_ok:
        return 100
    # Network ID — без идентификации хаб не принимает станцию
    if not search_ok:
        return 100
    # Profile mode — неправильный протокол, частичная связь
    if not profile_ok:
        return 75
    # Координаты — TDMA timing off, burst-ы не попадают в слоты
    if not site_ok:
        return random.choice([25, 50])
    return 0


def validate_config(
    student: FullConfig,
    reference: FullConfig,
    partial_mode: bool,
) -> ValidationResult:
    details: list[ParameterResult] = []
    site_ok = True
    rf_ok = True
    search_ok = True
    profile_ok = True
    correct_count = 0
    total_count = len(PARAM_DEFS)

    for category, name, tolerance, comp_type in PARAM_DEFS:
        student_val = _get_param_value(student, category, name)
        ref_val = _get_param_value(reference, category, name)

        is_correct = _compare(student_val, ref_val, comp_type, tolerance)

        if is_correct:
            correct_count += 1
        else:
            if category == "site":
                site_ok = False
            elif category == "rf":
                rf_ok = False
            elif category == "search_id":
                search_ok = False
            elif category == "profile":
                profile_ok = False

        details.append(ParameterResult(
            name=name,
            category=category,
            student_value=str(student_val),
            reference_value=str(ref_val),
            is_correct=is_correct,
            tolerance=f"+-{tolerance}" if tolerance else None,
        ))

    loss_percent = _compute_loss(site_ok, rf_ok, search_ok, profile_ok, partial_mode)

    percentage = round(correct_count / total_count * 100, 1) if total_count > 0 else 0.0

    return ValidationResult(
        overall_correct=(loss_percent == 0),
        site_correct=site_ok,
        rf_correct=rf_ok,
        search_id_correct=search_ok,
        profile_correct=profile_ok,
        correct_count=correct_count,
        total_count=total_count,
        percentage=percentage,
        loss_percent=loss_percent,
        details=details,
    )
