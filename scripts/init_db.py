#!/usr/bin/env python3
"""Initialize the support database schema and seed data.

Supports both local Docker Supabase and remote Supabase Cloud.

Usage:
    python scripts/init_db.py                    # Local Docker (default)
    python scripts/init_db.py --remote           # Remote Supabase Cloud
    python scripts/init_db.py --remote --reset   # Drop and recreate (remote)
"""

import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)


def get_db_url(remote: bool = False) -> str:
    """Build database connection URL from environment or defaults."""
    if remote:
        url = os.environ.get("SUPABASE_DB_URL")
        if not url:
            print("ERROR: SUPABASE_DB_URL not set. Export it or use --local.", file=sys.stderr)
            sys.exit(1)
        return url
    return os.environ.get("LOCAL_DB_URL", "postgresql://supabase_admin:postgres@localhost:54324/postgres")


def run_sql(url: str, sql_path: str) -> None:
    """Execute a SQL file against the database."""
    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary", file=sys.stderr)
        sys.exit(1)

    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()

    conn = psycopg2.connect(url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        print(f"OK: {os.path.basename(sql_path)}")
    except Exception as e:
        print(f"ERROR in {os.path.basename(sql_path)}: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize support database")
    parser.add_argument("--remote", action="store_true", help="Use remote Supabase Cloud (requires SUPABASE_DB_URL)")
    parser.add_argument("--local", action="store_true", help="Use local Docker Supabase (default)")
    parser.add_argument("--schema-only", action="store_true", help="Run schema only, skip seed data")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate tables before init (remote only)")
    args = parser.parse_args()

    remote = args.remote
    url = get_db_url(remote)
    schema_path = os.path.join(PROJECT_DIR, "db", "init", "001_schema.sql")
    seed_path = os.path.join(PROJECT_DIR, "db", "init", "002_seed.sql")

    print(f"Connecting to: {'Remote Supabase Cloud' if remote else 'Local Docker Supabase'}")

    if args.reset and remote:
        print("WARNING: --reset will drop all tables. Continuing in 3 seconds...")
        import time
        time.sleep(3)
        drop_sql = """
            DROP TABLE IF EXISTS order_items, support_tickets, orders, products, customers, faq_cards CASCADE;
        """
        try:
            import psycopg2
            conn = psycopg2.connect(url)
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(drop_sql)
            conn.close()
            print("OK: Tables dropped")
        except Exception as e:
            print(f"ERROR dropping tables: {e}", file=sys.stderr)
            sys.exit(1)

    run_sql(url, schema_path)
    if not args.schema_only:
        run_sql(url, seed_path)

    print("Database initialized successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())