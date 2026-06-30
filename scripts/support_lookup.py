#!/usr/bin/env python3
"""Search support knowledge base.

Reads FAQ cards from the database (faq_cards table).
Falls back to built-in cards if the database is unavailable.

Usage:
    python scripts/support_lookup.py "как оформить возврат"
    python scripts/support_lookup.py --remote "где мой заказ"
"""

import argparse
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

# Built-in fallback cards (used when DB is unavailable)
# In production, FAQ data lives in the faq_cards table.
FALLBACK_CARDS = [
    {
        "topic": "заказ",
        "keywords": "заказ, оформить, корзина, купить, покупка",
        "answer": "Вы можете оформить заказ на сайте: добавьте товары в корзину, укажите контактные данные, адрес доставки и выберите способ оплаты. После оформления придёт подтверждение заказа.",
        "clarify": "Если не получается оформить заказ, уточните, на каком шаге возникла проблема.",
        "handoff_rule": "Нужен человек, если сайт выдаёт ошибку, не проходит оплата или клиент не получил подтверждение."
    },
    {
        "topic": "статус заказа",
        "keywords": "где, статус, трек, отследить, мой заказ",
        "answer": "Я помогу проверить заказ. Пришлите, пожалуйста, номер заказа или телефон, указанный при оформлении.",
        "clarify": "Номер заказа или телефон.",
        "handoff_rule": "Нужен человек, если номер заказа есть, но статус не найден или срок доставки вышел."
    },
    {
        "topic": "доставка",
        "keywords": "доставка, срок, когда, идёт, придёт",
        "answer": "Обычно доставка по России занимает 2-5 рабочих дней после передачи заказа службе доставки. В праздничные периоды срок может увеличиться.",
        "clarify": "Город доставки, если нужен более точный ориентир.",
        "handoff_rule": "Нужен человек, если клиент сообщает о просрочке."
    },
    {
        "topic": "возврат",
        "keywords": "возврат, вернуть, не подошёл, возврата",
        "answer": "Возврат можно оформить в течение 14 дней после получения заказа, если товар не был вскрыт и сохранил товарный вид. Пришлите номер заказа — подскажем следующий шаг.",
        "clarify": "Номер заказа, дата получения, состояние упаковки.",
        "handoff_rule": "Нужен человек, если упаковка вскрыта, срок прошёл или клиент просит исключение."
    },
    {
        "topic": "жалоба",
        "keywords": "жалоба, претензия, недоволен, отзыв, распотрёб",
        "answer": "Мне жаль, что возникла такая ситуация. Я передам обращение специалисту, чтобы его проверили внимательно. Пришлите, пожалуйста, номер заказа и краткое описание проблемы.",
        "clarify": "Номер заказа, описание проблемы, фото при необходимости.",
        "handoff_rule": "Всегда нужен человек."
    },
    {
        "topic": "оператор",
        "keywords": "оператор, человек, менеджер, связаться, позовите",
        "answer": "Конечно, передам обращение оператору. Напишите, пожалуйста, коротко суть вопроса и номер заказа, если он есть.",
        "clarify": "Суть вопроса и номер заказа.",
        "handoff_rule": "Всегда нужен человек."
    },
    {
        "topic": "аллергия",
        "keywords": "аллергия, отёк, отек, зуд, сыпь",
        "answer": "Если есть риск аллергии или уже появилась реакция, лучше прекратить использование средства и обратиться к врачу. Пришлите номер заказа и описание ситуации — передадим обращение специалисту.",
        "clarify": "Номер заказа, какой товар, какая реакция.",
        "handoff_rule": "Всегда нужен человек."
    },
    {
        "topic": "беременность",
        "keywords": "беремен, кормлен, гв",
        "answer": "Во время беременности и кормления лучше согласовывать уходовые средства с врачом, особенно если есть чувствительность кожи или противопоказания. Мы можем подсказать состав средства, но не даём медицинских гарантий.",
        "clarify": "Название средства и конкретный вопрос по составу.",
        "handoff_rule": "Нужен человек, если клиент ждёт медицинское подтверждение или гарантию безопасности."
    },
    {
        "topic": "скидка",
        "keywords": "скид, промокод, акци, дешевл",
        "answer": "Актуальные акции и промокоды отображаются на сайте. Если у вас есть промокод и он не применяется, пришлите его название и скрин ошибки — проверим.",
        "clarify": "Промокод и ошибка.",
        "handoff_rule": "Нужен человек, если клиент просит индивидуальную скидку или промокод не работает."
    },
]

ALWAYS_HANDOFF_PATTERNS = [
    "жалоба", "претенз", "распотрёб", "суд", "адвокат", "верните деньги",
    "аллерг", "отёк", "отек", "сыпь", "беремен", "брак", "разбит", "сломано",
    "не тот товар", "оператор",
]


def get_db_url(remote: bool = False) -> str:
    """Build database connection URL from environment or defaults."""
    if remote:
        url = os.environ.get("SUPABASE_DB_URL")
        if not url:
            try:
                from dotenv import load_dotenv
                load_dotenv(os.path.join(PROJECT_DIR, ".env"))
                url = os.environ.get("SUPABASE_DB_URL")
            except ImportError:
                pass
        if not url:
            print("ERROR: SUPABASE_DB_URL not set.", file=sys.stderr)
            sys.exit(1)
        return url
    return os.environ.get("LOCAL_DB_URL", "postgresql://supabase_admin:***@localhost:54324/postgres")


def fetch_faq_from_db(remote: bool = False) -> list[dict]:
    """Fetch FAQ cards from the database."""
    url = get_db_url(remote)
    try:
        import psycopg2
    except ImportError:
        return []

    try:
        conn = psycopg2.connect(url)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT topic, keywords, answer, clarify, handoff_rule FROM faq_cards ORDER BY topic")
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Warning: Could not fetch FAQ from DB: {e}", file=sys.stderr)
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def score_card(question: str, card: dict) -> int:
    score = 0
    keywords = [kw.strip() for kw in card.get("keywords", "").split(",")]
    for keyword in keywords:
        if keyword and keyword in question:
            score += 2 if " " in keyword else 1
    return score


def find_card(question: str, cards: list[dict]) -> tuple[dict | None, int]:
    scores = [(score_card(question, card), card) for card in cards]
    scores.sort(key=lambda item: item[0], reverse=True)
    best_score, best_card = scores[0] if scores else (0, None)
    if best_score <= 0:
        return None, 0
    return best_card, best_score


def confidence(score: int, handoff: bool) -> str:
    if handoff:
        return "низкая"
    if score >= 3:
        return "высокая"
    if score >= 1:
        return "средняя"
    return "низкая"


def main() -> int:
    parser = argparse.ArgumentParser(description="Search support knowledge base.")
    parser.add_argument("question", nargs="*", help="Customer question")
    parser.add_argument("--remote", action="store_true", help="Use remote Supabase Cloud")
    args = parser.parse_args()

    # Try DB first, fall back to built-in cards
    cards = fetch_faq_from_db(args.remote)
    source = "база данных"
    if not cards:
        cards = FALLBACK_CARDS
        source = "встроенные карточки (БД недоступна)"

    raw_question = " ".join(args.question)
    if not raw_question.strip():
        print("## Как использовать")
        print('python scripts/support_lookup.py "вопрос клиента"')
        print("\n## Примеры")
        print('python scripts/support_lookup.py "как оформить возврат"')
        print('python scripts/support_lookup.py "товар пришёл разбитый"')
        print('python scripts/support_lookup.py "можно беременным этот крем"')
        return 0

    question = normalize(raw_question)
    card, score = find_card(question, cards)
    pattern_handoff = any(pattern in question for pattern in ALWAYS_HANDOFF_PATTERNS)
    handoff = pattern_handoff

    if not card:
        print("## Найденная тема")
        print("Не найдена")
        print("\n## Уверенность")
        print("низкая")
        print("\n## Ответ клиенту")
        print("Я передам ваш вопрос оператору, чтобы не дать неточный ответ. Напишите, пожалуйста, номер заказа, если вопрос связан с покупкой, и коротко опишите ситуацию.")
        print("\n## Что уточнить")
        print("Суть вопроса и номер заказа при наличии.")
        print("\n## Нужен человек")
        print("да")
        print("\n## Внутренняя заметка")
        print("Точного ответа в базе знаний нет. Нужно проверить обращение вручную.")
        return 0

    handoff_rule = card.get("handoff_rule", card.get("handoff", ""))
    if "всегда нужен человек" in handoff_rule.lower():
        handoff = True

    conf = confidence(score, handoff)
    print(f"## Найденная тема (источник: {source})")
    print(card.get("topic", ""))
    print("\n## Уверенность")
    print(conf)
    print("\n## Ответ клиенту")
    print(card.get("answer", ""))
    print("\n## Что уточнить")
    print(card.get("clarify", ""))
    print("\n## Нужен человек")
    print("да" if handoff else "нет")
    print("\n## Внутренняя заметка")
    print(handoff_rule)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())