import logging
import os
import uuid
from datetime import datetime, timezone

import aiosqlite

from server.config import load_config, FACTORY_DEFAULTS, REFERENCE_DEFAULTS, CONFIG_COLUMNS

logger = logging.getLogger("vsat.database")

_db: aiosqlite.Connection | None = None

HELP_TEXT_DEFAULT = """\
# Симулятор спутникового коммутатора Comtech CEL-AC 3 — Руководство

## Общие сведения
Вы настраиваете спутниковый коммутатор Comtech CEL-AC 3 (модель CEL-200X) — \
устройство для организации спутниковой связи в сетях VSAT. \
Ваша задача — правильно установить все параметры на странице Site Setup \
и проверить связь командой ping с 0% потерь пакетов.

## Порядок выполнения
1. Перейдите на страницу **Site Setup** в левом меню
2. Заполните параметры: Location, RF Interface, Search/ID
3. Перейдите на страницу **Profiles** и выберите нужный режим
4. Нажмите **Apply** для сохранения настроек
5. Следите за индикаторами в заголовке (LAN1, DEM1, MOD, NET и т.д.)
6. Откройте **Console** и выполните: ping <ip_address>
7. Добейтесь 0% потерь пакетов для завершения работы

---

## Страница Site Setup
Основная страница настройки коммутатора.

- **Site Name** — имя устройства (до 20 символов)
- **Location** — координаты станции (широта/долгота)
- **RF Interface** — настройки гетеродинов (LO) приёмников и передатчика:
  - **Rx1/Rx2 LO** — частота гетеродина приёмника (kHz)
  - **TX LO** — частота гетеродина передатчика (kHz)
  - **Power** — питание LNB
  - **10MHz** — опорный генератор 10 МГц
  - **SpInv** — инверсия спектра
  - **Freq Adj** — подстройка частоты (0-4095 kHz)
- **Carrier Search BW** — полоса поиска несущей (SCPC / TDMA)
- **Net ID / RF ID** — идентификаторы сети и RF-канала (0-255)
- **Far end C/N** — отношение сигнал/шум на дальнем конце (dB)

---

## Индикаторы в заголовке
| Индикатор | Зелёный | Жёлтый | Красный | Серый |
|-----------|---------|--------|---------|-------|
| LAN1/LAN2 | Соединение активно | - | Ошибка | Выключен |
| DEM1/DEM2 | Демодулятор захватил сигнал | Частично настроен | Нет сигнала | Выключен |
| MOD | Модулятор активен | TX настроен, но выключен | Не настроен | - |
| NET | Сеть в норме | Частичная настройка | Ошибка сети | - |
| SYS | Система ОК | - | Ошибка | - |
| MON | Мониторинг вкл. | - | - | Выключен |

## Советы
- Всегда нажимайте **Apply** перед выполнением ping
- Проверьте индикаторы — DEM1, MOD, NET должны быть зелёными
- При 100% потерях — проверьте Net ID и RF ID
- При частичных потерях — проверьте частоты LO\
"""


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        config = load_config()
        db_path = config["database"]["path"]
        abs_path = os.path.abspath(db_path)
        logger.info("Opening database: %s", abs_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        _db = await aiosqlite.connect(db_path)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
        await _create_tables(_db)
        logger.info("Database initialized successfully")
    return _db


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None


async def _create_tables(db: aiosqlite.Connection) -> None:
    # Check if old schema exists (has rx_frequency column) and drop if so
    try:
        async with db.execute("PRAGMA table_info(student_configs)") as cursor:
            cols = [row[1] async for row in cursor]
            if "rx_frequency" in cols:
                logger.info("Old VSAT schema detected, dropping old tables...")
                await db.executescript("""
                    DROP TABLE IF EXISTS console_history;
                    DROP TABLE IF EXISTS student_configs;
                    DROP TABLE IF EXISTS reference_config;
                    DROP TABLE IF EXISTS sessions;
                """)
    except Exception:
        pass

    await db.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id              TEXT PRIMARY KEY,
            student_name    TEXT NOT NULL,
            student_group   TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'configuring',
            connection_time TEXT NOT NULL,
            last_activity   TEXT NOT NULL,
            ping_count      INTEGER NOT NULL DEFAULT 0,
            successful_pings INTEGER NOT NULL DEFAULT 0,
            UNIQUE(student_name, student_group)
        );

        CREATE TABLE IF NOT EXISTS student_configs (
            session_id      TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
            -- Site
            site_name       TEXT NOT NULL DEFAULT 'AC 3',
            latitude_deg    INTEGER NOT NULL DEFAULT 0,
            latitude_min    INTEGER NOT NULL DEFAULT 0,
            latitude_dir    TEXT NOT NULL DEFAULT 'N',
            longitude_deg   INTEGER NOT NULL DEFAULT 0,
            longitude_min   INTEGER NOT NULL DEFAULT 0,
            longitude_dir   TEXT NOT NULL DEFAULT 'E',
            -- RF Interface
            rx1_lo          INTEGER NOT NULL DEFAULT 0,
            rx2_lo          INTEGER NOT NULL DEFAULT 0,
            tx_lo           INTEGER NOT NULL DEFAULT 0,
            rx_power        INTEGER NOT NULL DEFAULT 0,
            rx_10mhz        INTEGER NOT NULL DEFAULT 0,
            rx1_spinv       INTEGER NOT NULL DEFAULT 0,
            rx2_spinv       INTEGER NOT NULL DEFAULT 0,
            tx_spinv        INTEGER NOT NULL DEFAULT 0,
            rx1_freq_adj    INTEGER NOT NULL DEFAULT 0,
            rx2_freq_adj    INTEGER NOT NULL DEFAULT 0,
            tx_freq_adj     INTEGER NOT NULL DEFAULT 0,
            tx_power        INTEGER NOT NULL DEFAULT 0,
            -- Search / ID
            search_bw_scpc  INTEGER NOT NULL DEFAULT 1800,
            search_bw_tdma  INTEGER NOT NULL DEFAULT 12,
            net_id          INTEGER NOT NULL DEFAULT 0,
            rf_id           INTEGER NOT NULL DEFAULT 0,
            far_end_cn      INTEGER NOT NULL DEFAULT 0,
            -- Profile
            active_profile  INTEGER NOT NULL DEFAULT 1,
            profile_mode    TEXT NOT NULL DEFAULT 'none',
            profile_autorun INTEGER NOT NULL DEFAULT 0,
            profile_timeout INTEGER NOT NULL DEFAULT 10
        );

        CREATE TABLE IF NOT EXISTS reference_config (
            id              INTEGER PRIMARY KEY CHECK (id = 1),
            -- Site
            site_name       TEXT NOT NULL DEFAULT 'AC 3',
            latitude_deg    INTEGER NOT NULL DEFAULT 32,
            latitude_min    INTEGER NOT NULL DEFAULT 0,
            latitude_dir    TEXT NOT NULL DEFAULT 'N',
            longitude_deg   INTEGER NOT NULL DEFAULT 35,
            longitude_min   INTEGER NOT NULL DEFAULT 0,
            longitude_dir   TEXT NOT NULL DEFAULT 'E',
            -- RF Interface
            rx1_lo          INTEGER NOT NULL DEFAULT 9750000,
            rx2_lo          INTEGER NOT NULL DEFAULT 0,
            tx_lo           INTEGER NOT NULL DEFAULT 13050000,
            rx_power        INTEGER NOT NULL DEFAULT 1,
            rx_10mhz        INTEGER NOT NULL DEFAULT 1,
            rx1_spinv       INTEGER NOT NULL DEFAULT 0,
            rx2_spinv       INTEGER NOT NULL DEFAULT 0,
            tx_spinv        INTEGER NOT NULL DEFAULT 0,
            rx1_freq_adj    INTEGER NOT NULL DEFAULT 0,
            rx2_freq_adj    INTEGER NOT NULL DEFAULT 0,
            tx_freq_adj     INTEGER NOT NULL DEFAULT 0,
            tx_power        INTEGER NOT NULL DEFAULT 1,
            -- Search / ID
            search_bw_scpc  INTEGER NOT NULL DEFAULT 1800,
            search_bw_tdma  INTEGER NOT NULL DEFAULT 12,
            net_id          INTEGER NOT NULL DEFAULT 1,
            rf_id           INTEGER NOT NULL DEFAULT 1,
            far_end_cn      INTEGER NOT NULL DEFAULT 12,
            -- Profile
            active_profile  INTEGER NOT NULL DEFAULT 1,
            profile_mode    TEXT NOT NULL DEFAULT 'Star station',
            profile_autorun INTEGER NOT NULL DEFAULT 1,
            profile_timeout INTEGER NOT NULL DEFAULT 10
        );

        CREATE TABLE IF NOT EXISTS server_settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS console_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            timestamp   TEXT NOT NULL,
            command     TEXT NOT NULL,
            output      TEXT NOT NULL
        );
    """)

    # Seed reference config if not exists
    async with db.execute("SELECT COUNT(*) FROM reference_config") as cursor:
        row = await cursor.fetchone()
        if row[0] == 0:
            cols = ", ".join(["id"] + CONFIG_COLUMNS)
            placeholders = ", ".join(["?"] * (len(CONFIG_COLUMNS) + 1))
            values = [1] + [REFERENCE_DEFAULTS[c] for c in CONFIG_COLUMNS]
            await db.execute(f"INSERT INTO reference_config ({cols}) VALUES ({placeholders})", values)

    # Seed default settings if not exists
    config = load_config()
    default_settings = {
        "admin_password": config["admin"]["password"],
        "partial_mode": str(config["simulation"]["partial_mode"]).lower(),
        "registration_open": "true",
        "help_text": HELP_TEXT_DEFAULT,
    }
    for key, value in default_settings.items():
        await db.execute(
            "INSERT OR IGNORE INTO server_settings (key, value) VALUES (?, ?)",
            (key, value),
        )

    # Always update admin password from config file on startup
    await db.execute(
        "UPDATE server_settings SET value = ? WHERE key = 'admin_password'",
        (config["admin"]["password"],),
    )

    await db.commit()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Session CRUD ──────────────────────────────────────────────


async def create_session(name: str, group: str) -> tuple[str, bool]:
    """Create a new session or return existing one. Returns (session_id, is_new)."""
    db = await get_db()

    # Check for existing session
    async with db.execute(
        "SELECT id FROM sessions WHERE student_name = ? AND student_group = ?",
        (name, group),
    ) as cursor:
        row = await cursor.fetchone()
        if row:
            logger.info("Reconnect: name=%s group=%s session=%s", name, group, row["id"])
            now = _now_iso()
            await db.execute(
                "UPDATE sessions SET status = 'configuring', last_activity = ? WHERE id = ?",
                (now, row["id"]),
            )
            await db.commit()
            return row["id"], False

    # Create new session
    session_id = uuid.uuid4().hex
    logger.info("New session: name=%s group=%s session=%s", name, group, session_id)
    now = _now_iso()
    await db.execute(
        "INSERT INTO sessions (id, student_name, student_group, status, connection_time, last_activity) "
        "VALUES (?, ?, ?, 'configuring', ?, ?)",
        (session_id, name, group, now, now),
    )

    # Create default config row
    cols = ", ".join(["session_id"] + CONFIG_COLUMNS)
    placeholders = ", ".join(["?"] * (len(CONFIG_COLUMNS) + 1))
    values = [session_id] + [FACTORY_DEFAULTS[c] for c in CONFIG_COLUMNS]
    await db.execute(f"INSERT INTO student_configs ({cols}) VALUES ({placeholders})", values)

    await db.commit()
    return session_id, True


async def get_session(session_id: str) -> dict | None:
    db = await get_db()
    async with db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_all_sessions() -> list[dict]:
    db = await get_db()
    async with db.execute("SELECT * FROM sessions ORDER BY connection_time DESC") as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def update_session_status(session_id: str, status: str) -> None:
    db = await get_db()
    await db.execute(
        "UPDATE sessions SET status = ?, last_activity = ? WHERE id = ?",
        (status, _now_iso(), session_id),
    )
    await db.commit()


async def update_last_activity(session_id: str) -> None:
    db = await get_db()
    await db.execute(
        "UPDATE sessions SET last_activity = ? WHERE id = ?",
        (_now_iso(), session_id),
    )
    await db.commit()


async def update_ping_stats(session_id: str, success: bool) -> None:
    db = await get_db()
    if success:
        await db.execute(
            "UPDATE sessions SET ping_count = ping_count + 1, successful_pings = successful_pings + 1 WHERE id = ?",
            (session_id,),
        )
    else:
        await db.execute(
            "UPDATE sessions SET ping_count = ping_count + 1 WHERE id = ?",
            (session_id,),
        )
    await db.commit()


async def delete_session(session_id: str) -> None:
    db = await get_db()
    await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    await db.commit()


# ── Student Config CRUD ───────────────────────────────────────


async def get_student_config(session_id: str) -> dict | None:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM student_configs WHERE session_id = ?", (session_id,)
    ) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def save_student_config(session_id: str, config_data: dict) -> None:
    db = await get_db()
    set_clauses = ", ".join(f"{col} = ?" for col in CONFIG_COLUMNS)
    values = [config_data[col] for col in CONFIG_COLUMNS] + [session_id]
    await db.execute(
        f"UPDATE student_configs SET {set_clauses} WHERE session_id = ?",
        values,
    )
    await update_last_activity(session_id)
    await db.commit()


async def reset_student_config(session_id: str) -> None:
    db = await get_db()
    set_clauses = ", ".join(f"{col} = ?" for col in CONFIG_COLUMNS)
    values = [FACTORY_DEFAULTS[col] for col in CONFIG_COLUMNS] + [session_id]
    await db.execute(
        f"UPDATE student_configs SET {set_clauses} WHERE session_id = ?",
        values,
    )
    await db.execute(
        "UPDATE sessions SET status = 'configuring', last_activity = ? WHERE id = ?",
        (_now_iso(), session_id),
    )
    await db.commit()


# ── Reference Config CRUD ─────────────────────────────────────


async def get_reference_config() -> dict:
    db = await get_db()
    async with db.execute("SELECT * FROM reference_config WHERE id = 1") as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else {}


async def save_reference_config(config_data: dict) -> None:
    db = await get_db()
    set_clauses = ", ".join(f"{col} = ?" for col in CONFIG_COLUMNS)
    values = [config_data[col] for col in CONFIG_COLUMNS] + [1]
    await db.execute(
        f"UPDATE reference_config SET {set_clauses} WHERE id = ?",
        values,
    )
    await db.commit()


# ── Server Settings CRUD ──────────────────────────────────────


async def get_setting(key: str) -> str | None:
    db = await get_db()
    async with db.execute(
        "SELECT value FROM server_settings WHERE key = ?", (key,)
    ) as cursor:
        row = await cursor.fetchone()
        return row["value"] if row else None


async def set_setting(key: str, value: str) -> None:
    db = await get_db()
    await db.execute(
        "INSERT OR REPLACE INTO server_settings (key, value) VALUES (?, ?)",
        (key, value),
    )
    await db.commit()


# ── Console History CRUD ──────────────────────────────────────


async def add_console_entry(session_id: str, command: str, output: str) -> None:
    db = await get_db()
    await db.execute(
        "INSERT INTO console_history (session_id, timestamp, command, output) VALUES (?, ?, ?, ?)",
        (session_id, _now_iso(), command, output),
    )
    await db.commit()


async def get_console_history(session_id: str) -> list[dict]:
    db = await get_db()
    async with db.execute(
        "SELECT timestamp, command, output FROM console_history WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    ) as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
