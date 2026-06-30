#!/usr/bin/env python3
"""Support database query helper.

Supports both local Docker Supabase and remote Supabase Cloud.

Usage:
    python scripts/support_db.py health
    python scripts/support_db.py --remote health
    python scripts/support_db.py order ORD-1042
    python scripts/support_db.py --remote order ORD-1042
"""

import argparse
import csv
import io
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)


def get_connection_mode(args) -> str:
    """Return 'remote' or 'local' based on args."""
    return "remote" if args.remote else "local"


def get_db_url(remote: bool = False) -> str:
    """Build database connection URL from environment or defaults."""
    if remote:
        url = os.environ.get("SUPABASE_DB_URL")
        if not url:
            # Try loading .env
            try:
                from dotenv import load_dotenv
                load_dotenv(os.path.join(PROJECT_DIR, ".env"))
                url = os.environ.get("SUPABASE_DB_URL")
            except ImportError:
                pass
        if not url:
            print("ERROR: SUPABASE_DB_URL not set. Export it or create .env.", file=sys.stderr)
            sys.exit(1)
        return url
    return os.environ.get("LOCAL_DB_URL", "postgresql://supabase_admin:postgres@localhost:54324/postgres")


COMPOSE = ["docker", "compose", "exec", "-T", "-e", "PGPASSWORD=postgres", "support-db"]
PSQL = ["psql", "-U", "supabase_admin", "-d", "postgres", "--csv", "-v", "ON_ERROR_STOP=1"]

QUERIES = {
    "health": """
        SELECT
          (SELECT count(*) FROM customers) AS customers,
          (SELECT count(*) FROM orders) AS orders,
          (SELECT count(*) FROM support_tickets) AS tickets,
          (SELECT count(*) FROM faq_cards) AS faq_cards;
    """,
    "metrics": """
        SELECT 'orders_total' AS metric, count(*)::text AS value FROM orders
        UNION ALL
        SELECT 'revenue_paid_rub', coalesce(sum(total_rub),0)::text FROM orders WHERE paid_status='paid'
        UNION ALL
        SELECT 'open_tickets', count(*)::text FROM support_tickets WHERE status='open'
        UNION ALL
        SELECT 'needs_human_tickets', count(*)::text FROM support_tickets WHERE needs_human=true
        UNION ALL
        SELECT 'delayed_orders', count(*)::text FROM orders WHERE expected_delivery_date < current_date AND delivered_at IS NULL;
    """,
    "tickets": """
        SELECT
          t.ticket_number,
          c.telegram,
          o.order_number,
          t.category,
          t.priority,
          t.status,
          t.needs_human,
          t.customer_message,
          t.internal_note
        FROM support_tickets t
        LEFT JOIN customers c ON c.id=t.customer_id
        LEFT JOIN orders o ON o.id=t.order_id
        ORDER BY t.created_at DESC;
    """,
    "delayed": """
        SELECT
          o.order_number,
          c.telegram,
          c.full_name,
          o.status,
          o.delivery_city,
          o.tracking_number,
          o.expected_delivery_date,
          o.notes
        FROM orders o
        JOIN customers c ON c.id=o.customer_id
        WHERE o.expected_delivery_date < current_date AND o.delivered_at IS NULL
        ORDER BY o.expected_delivery_date;
    """,
}


def run_sql_local(sql: str) -> list[dict[str, str]]:
    """Execute SQL via local Docker Supabase."""
    cmd = COMPOSE + PSQL + ["-c", sql]
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    text = result.stdout.strip()
    if not text:
        return []
    return list(csv.DictReader(io.StringIO(text)))


def run_sql_remote(sql: str, db_url: str) -> list[dict[str, str]]:
    """Execute SQL via remote Supabase Cloud using psycopg2."""
    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cur.description:
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            return []
    finally:
        conn.close()


def run_sql(sql: str, remote: bool = False, db_url: str = "") -> list[dict[str, str]]:
    """Execute SQL using the appropriate method."""
    if remote:
        return run_sql_remote(sql, db_url)
    return run_sql_local(sql)


def markdown_table(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "_Нет данных._"
    headers = list(rows[0].keys())
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        values = []
        for header in headers:
            value = str(row.get(header, "")).replace("\n", " ").replace("|", "\\|")
            values.append(value)
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def select_only(sql: str) -> str:
    stripped = sql.strip().rstrip(";")
    lowered = stripped.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise SystemExit("Разрешены только SELECT/WITH-запросы.")
    blocked = [" insert ", " update ", " delete ", " drop ", " alter ", " truncate ", " create "]
    padded = f" {lowered} "
    if any(token in padded for token in blocked):
        raise SystemExit("Запрос похож на изменение данных. Используй только чтение.")
    return stripped + ";"


def order_query(order_number: str) -> str:
    safe = order_number.replace("'", "''")
    return f"""
        SELECT
          o.order_number,
          c.telegram,
          c.full_name,
          o.status,
          o.delivery_city,
          o.delivery_method,
          coalesce(o.tracking_number, '') AS tracking_number,
          o.expected_delivery_date,
          o.delivered_at,
          o.total_rub,
          o.paid_status,
          o.payment_method,
          o.notes,
          string_agg(p.name || ' x' || oi.quantity, '; ' ORDER BY p.name) AS items
        FROM orders o
        JOIN customers c ON c.id=o.customer_id
        LEFT JOIN order_items oi ON oi.order_id=o.id
        LEFT JOIN products p ON p.id=oi.product_id
        WHERE o.order_number='{safe}'
        GROUP BY o.id, c.telegram, c.full_name;
    """


def customer_query(telegram: str) -> str:
    safe = telegram.replace("'", "''")
    return f"""
        SELECT
          c.telegram,
          c.full_name,
          c.city,
          c.preferred_tone,
          c.risk_flags,
          coalesce(string_agg(DISTINCT o.order_number || ' (' || o.status || ')', '; '), '') AS orders,
          coalesce(string_agg(DISTINCT t.ticket_number || ' (' || t.status || ', ' || t.category || ')', '; '), '') AS tickets
        FROM customers c
        LEFT JOIN orders o ON o.customer_id=c.id
        LEFT JOIN support_tickets t ON t.customer_id=c.id
        WHERE c.telegram='{safe}'
        GROUP BY c.id;
    """


def faq_query(term: str) -> str:
    safe = term.replace("'", "''")
    return f"""
        SELECT topic, answer, clarify, handoff_rule
        FROM faq_cards
        WHERE lower(topic || ' ' || keywords || ' ' || answer) LIKE lower('%{safe}%')
        ORDER BY topic
        LIMIT 10;
    """


def main() -> int:
    parser = argparse.ArgumentParser(description="Support database query helper.")
    parser.add_argument("--remote", action="store_true", help="Use remote Supabase Cloud instead of local Docker")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health")
    sub.add_parser("metrics")
    sub.add_parser("tickets")
    sub.add_parser("delayed")

    order = sub.add_parser("order")
    order.add_argument("order_number")

    customer = sub.add_parser("customer")
    customer.add_argument("telegram")

    faq = sub.add_parser("faq")
    faq.add_argument("term")

    sql = sub.add_parser("sql")
    sql.add_argument("query")

    args = parser.parse_args()
    remote = args.remote
    db_url = get_db_url(remote) if remote else ""

    # Load .env for remote connections
    if remote:
        try:
            from dotenv import load_dotenv
            load_dotenv(os.path.join(PROJECT_DIR, ".env"))
        except ImportError:
            pass
        db_url = get_db_url(True)

    if args.command in QUERIES:
        query = QUERIES[args.command]
    elif args.command == "order":
        query = order_query(args.order_number)
    elif args.command == "customer":
        query = customer_query(args.telegram)
    elif args.command == "faq":
        query = faq_query(args.term)
    elif args.command == "sql":
        query = select_only(args.query)
    else:
        parser.error("unknown command")

    print(markdown_table(run_sql(query, remote, db_url)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())