#!/usr/bin/env python3
import argparse
import os

os.environ.setdefault('SCHEDULER_ENABLED', 'false')

from ..app import app as flask_app
from ..models import db
from ..models.job import Job


def main():
    parser = argparse.ArgumentParser(description="Backfill github_owner for GitHub jobs.")
    parser.add_argument("--owner", required=True, help="GitHub owner/org to set (e.g. Pay-Baymax)")
    parser.add_argument("--dry-run", action="store_true", help="Only report changes, do not write")
    args = parser.parse_args()

    with flask_app.app_context():
        query = Job.query.filter(
            Job.github_repo.isnot(None),
            Job.github_workflow_name.isnot(None),
        )

        jobs = query.all()
        to_update = [j for j in jobs if (j.github_owner or "").strip() != args.owner]

        print(f"Found {len(jobs)} GitHub jobs; will update {len(to_update)} to github_owner='{args.owner}'")
        if args.dry_run:
            return

        for job in to_update:
            job.github_owner = args.owner

        db.session.commit()
        print("Done.")


if __name__ == "__main__":
    main()
