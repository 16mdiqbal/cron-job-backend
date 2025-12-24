#!/usr/bin/env python3
"""
Initialize the database schema for the FastAPI backend (FastAPI-only).

This runs `Base.metadata.create_all()` plus lightweight SQLite schema guards.

Examples:
  ./scripts/init_fastapi_db.py
  DATABASE_URL=sqlite:////tmp/cron_jobs.db ./scripts/init_fastapi_db.py
  ./scripts/init_fastapi_db.py --database-url sqlite:////tmp/fastapi_test.db --testing
"""

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize DB schema for FastAPI.")
    parser.add_argument("--database-url", help="SQLAlchemy database URL (overrides env)")
    parser.add_argument("--testing", action="store_true", help="Set TESTING=true and disable scheduler")
    args = parser.parse_args()

    os.environ.setdefault("SCHEDULER_ENABLED", "false")
    if args.testing:
        os.environ["TESTING"] = "true"

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url
        os.environ["FASTAPI_DATABASE_URL"] = args.database_url

    from src.database.bootstrap import init_db

    init_db()
    print("✅ Database initialized successfully.")
    print(f"   DATABASE_URL={os.environ.get('DATABASE_URL')}")


if __name__ == "__main__":
    main()

