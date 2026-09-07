# Comtech CEL-AC Interface Integration

## Обзор

Этот документ описывает интеграцию оригинального интерфейса Comtech CEL-AC в симулятор спутникового маршрутизатора.

## Структура файлов

```
source/server/
├── static/
│   ├── css/
│   │   ├── lm.css          # Основные стили Comtech
│   │   └── ls.css          # Стили для iframe контента
│   └── templates/
│       └── comtech/
│           ├── main.html                    # Главный экран с меню
│           └── iframe_content/
│               ├── ss40.html                # Overview страница
│               ├── ss35.html                # System General
│               ├── cc2.html                 # Site Setup
│               └── cc3.html                 # Profiles
└── routes/
    └── simulator.py         # Маршруты для симулятора
```

## Запуск симулятора

1. Установите зависимости:
```bash
cd /workspace/source
pip install -r requirements.txt  # или pip install fastapi uvicorn aiosqlite
```

2. Запустите сервер:
```bash
python -m server.main
```

3. Откройте в браузере:
- **Основной интерфейс**: http://localhost:8000/sim
- **Оригинальный терминал**: http://localhost:8000/terminal
- **Админ панель**: http://localhost:8000/admin

## Доступные страницы

### Главное меню (/sim)
Содержит:
- Верхнюю панель статусов (LAN, DEM, MOD, NET, SYS, MON)
- Левое дерево навигации
- Iframe для отображения контента

### Разделы навигации

#### Overview (ss40)
- Статус системы
- Информация об интерфейсах
- Статистика станции

#### Site Setup (cc2)
- Настройки сайта
- Параметры станции

#### Profiles (cc3)
- Выбор профиля
- Конфигурация профилей

#### IP Routing
- Static (ss4/cc4)
- Dynamic (ss64)

#### IP Protocols
- SNMP, DHCP, DNS, ARP, NAT
- RIPv2, SNTP, RTP, TFTP, GTP
- Multicast, Acceleration

#### QoS
- Policies, Shapers
- Real-time, Service mon.

#### Network
- Overview, Stations
- MF TDMA, ACM
- STLC/NMS/Red, COTM/AMIP
- Beam sw., Security

#### System
- General, Interfaces
- Ethernet, Demodulator, Modulator
- Time-related, User access
- Flash/Boot, Save/load

#### Maintenance
- Support info, Log
- Pointing, Spectrum
- Run script, Tuning
- Traffic gen., Reboot

## API Endpoints

### Статус системы
```
GET /sim/JS0
```
Возвращает JSON с текущим статусом всех индикаторов.

### Данные Overview
```
GET /sim/api/overview_data
```
Возвращает детальную информацию для страницы Overview.

### Команды управления
```
GET /sim/z    # Save Configuration
GET /sim/hz   # Clear Faults
GET /sim/hy   # Profile Status Refresh
```

## Добавление новых страниц

1. Создайте HTML файл в `source/server/static/templates/comtech/iframe_content/`
2. Добавьте маппинг в `source/server/routes/simulator.py`:
```python
page_map = {
    "XX": "ssXX.html",  # Для status страниц
}
```
3. Используйте стили `/static/css/ls.css` для консистентности

## Стилизация

Все страницы используют оригинальные CSS файлы Comtech:
- `lm.css` - основные стили интерфейса
- `ls.css` - стили для контента страниц

Цветовые коды состояний:
- `cg` (green) - Активно/Нормально
- `cw` (white) - Ожидание/Нейтрально
- `cr` (red) - Ошибка/Down
- `cy` (yellow) - Предупреждение
- `cwd` (white disabled) - Отключено

## Автообновление

Главная страница автоматически обновляет статус каждые 5 секунд через JavaScript fetch запрос к `/sim/JS0`.

Страницы в iframe обновляются независимо (каждые 10 секунд для Overview).

## Интеграция с существующим функционалом

Новый интерфейс Comtech доступен параллельно с существующим терминалом:
- Старый интерфейс: `/terminal`
- Новый интерфейс: `/sim`

Оба используют одну базу данных и бэкенд логику.
