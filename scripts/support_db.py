#!/usr/bin/env python3
"""Support database query helper.

Uses Supabase REST API by default (--remote or local Docker).
Falls back to direct PostgreSQL for init and raw SQL.

Usage:
    python scripts/support_db.py health
    python scripts/support_db.py order ORD-1042
    python scripts/support_db.py customer @anna_care
    python scripts/support_db.py tickets
    python scripts/support_db.py metrics
    python scripts/support_db.py delayed
    python scripts/support_db.py faq возврат
    python scripts/support_db.py sql "SELECT status, count(*) FROM orders GROUP BY status"

    # Explicit connection mode:
    python scripts/support_db.py --remote health      # Supabase Cloud/Dockploy (default if .env present)
    python scripts/support_db.py --local health        # Local Docker Supabase
"""

import argparse
import csv
import io
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

# ── Supabase REST API ──────────────────────────────────────────────────────

def get_supabase_client():
    """Create a Supabase client from environment variables."""
    try:
        from supabase import create_client
    except ImportError:
        print("ERROR: supabase package not installed. Run: pip install supabase", file=sys.stderr)
        sys.exit(1)

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        # Try loading .env
        try:
            from dotenv import load_dotenv
            load_dotenv(os.path.join(PROJECT_DIR, ".env"))
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_KEY")
        except ImportError:
            pass

    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set.", file=sys.stderr)
        print("Export them or create .env from .env.example.", file=sys.stderr)
        sys.exit(1)

    return create_client(url, key)


def rest_query(table: str, select: str = "*", filters: dict | None = None,
               order: str | None = None, limit: int | None = None) -> list[dict]:
    """Query a Supabase table via REST API."""
    sb = get_supabase_client()
    query = sb.table(table).select(select)
    if filters:
        for col, val in filters.items():
            query = query.eq(col, val)
    if order:
        col, direction = order.split(":") if ":" in order else (order, "asc")
        query = query.order(col, desc=(direction == "desc"))
    if limit:
        query = query.limit(limit)
    response = query.execute()
    return response.data if response.data else []


def rest_health() -> list[dict]:
    """Get health metrics from all tables."""
    sb = get_supabase_client()
    tables = ["customers", "orders", "support_tickets", "faq_cards"]
    result = {}
    for table in tables:
        try:
            response = sb.table(table).select("id", count="exact").limit(0).execute()
            result[table] = response.count if hasattr(response, 'count') else len(response.data) if response.data else 0
        except Exception:
            result[table] = "error"
    return [result]


def rest_order(order_number: str) -> list[dict]:
    """Get order details with customer and items."""
    sb = get_supabase_client()
    # Get order
    response = sb.table("orders").select(
        "order_number, status, delivery_city, delivery_method, tracking_number, "
        "expected_delivery_date, delivered_at, total_rub, paid_status, payment_method, notes, "
        "customers(telegram, full_name)"
    ).eq("order_number", order_number).execute()
    if not response.data:
        return []
    order = response.data[0]

    # Get order items
    items_response = sb.table("order_items").select(
        "quantity, products(name, sku)"
    ).eq("order_id", order.get("id", 0)).execute()

    # Flatten
    customer = order.pop("customers", {}) or {}
    flat = {**order, **{f"customer_{k}": v for k, v in customer.items()}}

    items = []
    if items_response.data:
        for item in items_response.data:
            product = item.pop("products", {}) or {}
            items.append(f"{product.get('name', '?')} x{item.get('quantity', 0)}")
    flat["items"] = "; ".join(items) if items else ""

    return [flat]


def rest_customer(telegram: str) -> list[dict]:
    """Get customer details with orders and tickets."""
    sb = get_supabase_client()

    # Get customer
    cust_response = sb.table("customers").select("*").eq("telegram", telegram).execute()
    if not cust_response.data:
        return []
    customer = cust_response.data[0]

    # Get orders
    orders_response = sb.table("orders").select("order_number, status").eq("customer_id", customer["id"]).execute()
    orders_str = "; ".join(f"{o['order_number']} ({o['status']})" for o in (orders_response.data or []))

    # Get tickets
    tickets_response = sb.table("support_tickets").select("ticket_number, status, category").eq("customer_id", customer["id"]).execute()
    tickets_str = "; ".join(f"{t['ticket_number']} ({t['status']}, {t['category']})" for t in (tickets_response.data or []))

    flat = {
        "telegram": customer.get("telegram", ""),
        "full_name": customer.get("full_name", ""),
        "city": customer.get("city", ""),
        "preferred_tone": customer.get("preferred_tone", ""),
        "risk_flags": customer.get("risk_flags", ""),
        "orders": orders_str,
        "tickets": tickets_str,
    }
    return [flat]


def rest_tickets() -> list[dict]:
    """Get all support tickets."""
    return rest_query("support_tickets", select="*",
                       order="created_at:desc")


def rest_metrics() -> list[dict]:
    """Get key metrics."""
    sb = get_supabase_client()

    orders_total = sb.table("orders").select("id", count="exact").limit(0).execute().count or 0
    revenue = sb.table("orders").select("total_rub").eq("paid_status", "paid").execute()
    revenue_paid = sum(r.get("total_rub", 0) or 0 for r in (revenue.data or []))
    open_tickets = sb.table("support_tickets").select("id", count="exact").eq("status", "open").limit(0).execute().count or 0
    needs_human = sb.table("support_tickets").select("id", count="exact").eq("needs_human", "true").limit(0).execute().count or 0

    return [{
        "orders_total": orders_total,
        "revenue_paid_rub": int(revenue_paid),
        "open_tickets": open_tickets,
        "needs_human_tickets": needs_human,
    }]


def rest_delayed() -> list[dict]:
    """Get delayed orders (expected delivery in the past, not delivered)."""
    sb = get_supabase_client()
    from datetime import date
    today = date.today().isoformat()
    response = sb.table("orders").select(
        "order_number, status, delivery_city, tracking_number, expected_delivery_date, notes, "
        "customers(telegram, full_name)"
    ).lt("expected_delivery_date", today).is_("delivered_at", "null").execute()
    if not response.data:
        return []
    result = []
    for row in response.data:
        customer = row.pop("customers", {}) or {}
        flat = {**row, **{f"customer_{k}": v for k, v in customer.items()}}
        result.append(flat)
    return result


def rest_faq(term: str) -> list[dict]:
    """Search FAQ cards by term."""
    sb = get_supabase_client()
    # Use ilike for case-insensitive search
    response = sb.table("faq_cards").select("topic, answer, clarify, handoff_rule").ilike(
        "topic", f"%{term}%"
    ).execute()
    # Also search keywords
    if not response.data:
        response = sb.table("faq_cards").select("topic, answer, clarify, handoff_rule").ilike(
            "keywords", f"%{term}%"
        ).execute()
    return response.data if response.data else []


# ── Local Docker fallback (psql) ───────────────────────────────────────────

COMPOSE = ["docker", "compose", "exec", "-T", "-e", "PGPASSWORD=***", "support-db"]
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
    """Execute SQL via local Docker Supabase (psql)."""
    cmd = COMPOSE + PSQL + ["-c", sql]
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    text = result.stdout.strip()
    if not text:
        return []
    return list(csv.DictReader(io.StringIO(text)))


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


def markdown_table(rows: list[dict]) -> str:
    if not rows:
        return "_Нет данных._"
    headers = list(rows[0].keys())
    lines = [
        "| " + " | ".join(str(h) for h in headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        values = []
        for header in headers:
            value = str(row.get(header, "")).replace("\n", " ").replace("|", "\\|")
            values.append(value)
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Support database query helper.")
    parser.add_argument("--local", action="store_true", help="Use local Docker Supabase (psql)")
    parser.add_argument("--remote", action="store_true", help="Use remote Supabase REST API (default)")
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

    # Default: remote (REST API). Use --local for psql.
    use_local = args.local

    # Load .env if available
    if not use_local:
        try:
            from dotenv import load_dotenv
            load_dotenv(os.path.join(PROJECT_DIR, ".env"))
        except ImportError:
            pass

    if use_local:
        # Local Docker: use psql
        if args.command == "sql":
            query = select_only(args.query)
        elif args.command in QUERIES:
            query = QUERIES[args.command]
        elif args.command == "order":
            safe = args.order_number.replace("'", "''")
            query = f"""SELECT o.order_number, c.telegram, c.full_name, o.status, o.delivery_city,
                o.delivery_method, coalesce(o.tracking_number,'') AS tracking_number,
                o.expected_delivery_date, o.delivered_at, o.total_rub, o.paid_status,
                o.payment_method, o.notes,
                string_agg(p.name || ' x' || oi.quantity, '; ' ORDER BY p.name) AS items
                FROM orders o JOIN customers c ON c.id=o.customer_id
                LEFT JOIN order_items oi ON oi.order_id=o.id
                LEFT JOIN products p ON p.id=oi.product_id
                WHERE o.order_number='{safe}' GROUP BY o.id, c.telegram, c.full_name;"""
        elif args.command == "customer":
            safe = args.telegram.replace("'", "''")
            query = f"""SELECT c.telegram, c.full_name, c.city, c.preferred_tone, c.risk_flags,
                coalesce(string_agg(DISTINCT o.order_number || ' (' || o.status || ')', '; '), '') AS orders,
                coalesce(string_agg(DISTINCT t.ticket_number || ' (' || t.status || ', ' || t.category || ')', '; '), '') AS tickets
                FROM customers c LEFT JOIN orders o ON o.customer_id=c.id
                LEFT JOIN support_tickets t ON t.customer_id=c.id
                WHERE c.telegram='{safe}' GROUP BY c.id;"""
        elif args.command == "faq":
            safe = args.term.replace("'", "''")
            query = f"SELECT topic, answer, clarify, handoff_rule FROM faq_cards WHERE lower(topic || ' ' || keywords || ' ' || answer) LIKE lower('%{safe}%') ORDER BY topic LIMIT 10;"
        else:
            parser.error(f"Unknown command: {args.command}")
        print(markdown_table(run_sql_local(query)))
    else:
        # Remote: use REST API
        if args.command == "health":
            print(markdown_table(rest_health()))
        elif args.command == "metrics":
            print(markdown_table(rest_metrics()))
        elif args.command == "tickets":
            print(markdown_table(rest_tickets()))
        elif args.command == "delayed":
            print(markdown_table(rest_delayed()))
        elif args.command == "order":
            print(markdown_table(rest_order(args.order_number)))
        elif args.command == "customer":
            print(markdown_table(rest_customer(args.telegram)))
        elif args.command == "faq":
            print(markdown_table(rest_faq(args.term)))
        elif args.command == "sql":
            # Raw SQL only available via local Docker
            print("Raw SQL is only available with --local flag (Docker psql).", file=sys.stderr)
            print("Use specific commands (order, customer, tickets, etc.) for REST API.", file=sys.stderr)
            sys.exit(1)
        else:
            parser.error(f"Unknown command: {args.command}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())