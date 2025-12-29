#!/usr/bin/env python3
import argparse
import os

os.environ.setdefault('SCHEDULER_ENABLED', 'false')

from sqlalchemy import select

from ..database.session import get_db_session
from ..models.job import Job


def main():
    parser = argparse.ArgumentParser(description="Backfill github_owner for GitHub jobs.")
    parser.add_argument("--owner", required=True, help="GitHub owner/org to set (e.g. Pay-Baymax)")
    parser.add_argument("--dry-run", action="store_true", help="Only report changes, do not write")
    args = parser.parse_args()

    with get_db_session() as session:
        jobs = (
            session.execute(
                select(Job).where(
                    Job.github_repo.is_not(None),
                    Job.github_workflow_name.is_not(None),
                )
            )
            .scalars()
            .all()
        )
        to_update = [j for j in jobs if (j.github_owner or "").strip() != args.owner]

        print(f"Found {len(jobs)} GitHub jobs; will update {len(to_update)} to github_owner='{args.owner}'")
        if args.dry_run:
            return

        for job in to_update:
            job.github_owner = args.owner

        session.commit()
        print("Done.")


if __name__ == "__main__":
    main()
