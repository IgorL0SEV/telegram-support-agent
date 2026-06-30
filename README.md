# Telegram Support Agent

Агент клиентской поддержки для интернет-магазина на базе OpenClaw.

Принимает обращения клиентов, находит ответ в базе знаний, проверяет данные в PostgreSQL (Supabase), формулирует готовый ответ и передаёт человеку только те обращения, где не хватает данных или есть риск ошибки.

## Возможности

- **Оператор поддержки** — отвечает на обращения клиентов по базе знаний
- **Аналитик** — выполняет read-only запросы к базе (заказы, клиенты, тикеты, метрики)
- **Эскалация** — три уровня достоверности: уверенно / уточнение / нужен человек
- **FAQ-поиск** — локальный поиск по карточкам + LLM-контекст
- **Supabase** — работает как с локальным Docker, так и с Cloud (Dockploy)

## Быстрый старт

### 1. Локальный Supabase (Docker)

```bash
docker compose up -d
python scripts/init_db.py
```

### 2. Удалённый Supabase Cloud

```bash
cp .env.example .env
# Отредактируйте .env — укажите SUPABASE_DB_URL, SUPABASE_URL, SUPABASE_ANON_KEY
python scripts/init_db.py --remote
```

### 3. Проверка

```bash
python scripts/support_db.py health
python scripts/support_db.py metrics
python scripts/support_lookup.py "как оформить возврат"
```

## Структура проекта

```
telegram-support-agent/
├── AGENTS.md                 # Инструкция агента (роли, правила, эскалация)
├── SOUL.md                   # Личность и ценности
├── IDENTITY.md               # Имя, emoji, назначение
├── TOOLS.md                  # Справка по инструментам и скриптам
├── HEARTBEAT.md              # Периодические проверки
├── USER.md                   # Описание пользователя (заполняется)
├── README.md                 # Этот файл
├── docker-compose.yml        # Локальный Supabase (PostgreSQL + Studio)
├── .env.example              # Шаблон переменных окружения
├── db/
│   └── init/
│       ├── 001_schema.sql    # Схема БД (customers, orders, products, tickets, faq)
│       └── 002_seed.sql      # Тестовые данные
├── scripts/
│   ├── init_db.py            # Инициализация БД (локально или удалённо)
│   ├── support_db.py         # CLI для запросов к БД
│   ├── support_lookup.py     # Поиск по FAQ-карточкам
│   ├── apply_db.sh           # Bash-обёртка (Docker)
│   └── reset_db.sh           # Сброс БД (Docker)
├── knowledge_base/
│   └── faq.md                # База ответов (~30 тем)
├── policies/
│   └── support_policy.md    # Политики, red lines, эскалация
├── data/
│   ├── customer_context.csv  # Контекст клиентов
│   ├── orders_sample.csv     # Примеры заказов
│   └── quality_questions.csv  # Вопросы для проверки качества
├── quality/                  # Метрики качества ответов
├── reports/                  # Отчёты аналитика
└── logs/
    └── escalation_log.md     # Журнал эскалаций
```

## Скрипты

### support_db.py — запросы к базе данных

```bash
python scripts/support_db.py health                                    # Статус БД
python scripts/support_db.py order ORD-1042                            # Информация по заказу
python scripts/support_db.py customer @anna_care                       # Контекст клиента
python scripts/support_db.py tickets                                   # Открытые тикеты
python scripts/support_db.py metrics                                   # Ключевые метрики
python scripts/support_db.py delayed                                   # Просроченные заказы
python scripts/support_db.py faq возврат                                # Поиск по FAQ-карточкам
python scripts/support_db.py sql "SELECT status, count(*) FROM orders GROUP BY status"  # Произвольный SELECT
```

Флаг `--remote` для подключения к Supabase Cloud:
```bash
python scripts/support_db.py --remote metrics
```

Команда `sql` принимает только `SELECT` и `WITH` — модифицирующие запросы блокируются.

### support_lookup.py — поиск по базе знаний

```bash
python scripts/support_lookup.py "как оформить возврат"
python scripts/support_lookup.py "где мой заказ"
python scripts/support_lookup.py "аллергия на крем"
```

Возвращает: тема, достоверность, ответ, уточнение, нужна ли эскалация.

### init_db.py — инициализация базы данных

```bash
python scripts/init_db.py                    # Локальный Docker (по умолчанию)
python scripts/init_db.py --remote           # Удалённый Supabase Cloud
python scripts/init_db.py --remote --reset   # Пересоздать таблицы (drop + create)
python scripts/init_db.py --schema-only      # Только схема, без тестовых данных
```

## Схема базы данных

| Таблица | Описание |
|---------|-----------|
| `customers` | Клиенты: Telegram, имя, город, предпочтительный тон, risk flags |
| `orders` | Заказы: статус, город доставки, трекинг, сумма, оплата |
| `products` | Товары: SKU, название, категория, цена, гипоаллергенность |
| `order_items` | Состав заказа |
| `support_tickets` | Тикеты: категория, приоритет, статус, нужен ли человек |
| `faq_cards` | Карточки FAQ: тема, ключевые слова, ответ, правило эскалации |

## Политики и эскалация

Три уровня достоверности:

| Уровень | Условие | Действие |
|---------|---------|----------|
| Уверенно | Прямое совпадение в FAQ | Отвечать без уточнения |
| Уточнение | Частичное совпадение | Задать уточняющий вопрос |
| Нужен человек | Жалобы, мошенничество, крупные суммы | Передать оператору |

Red lines: не менять данные в БД, не обещать скидки, не отвечать за чужие ошибки.

## Supabase Cloud (Dockploy)

Для подключения к удалённому Supabase:

1. Скопируйте `.env.example` → `.env`
2. Укажите `SUPABASE_DB_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`
3. Запустите `python scripts/init_db.py --remote`
4. Используйте флаг `--remote` в `support_db.py`

## Требования

- Python 3.10+
- Docker и Docker Compose (для локальной Supabase)
- `psycopg2-binary` — для `init_db.py` и `support_db.py --remote`
- `python-dotenv` — для загрузки `.env`

## Авторы

Пример OpenClaw-агента, адаптированный и очищенный для портфолио.

## Лицензия

MIT