"""
Bans a user: adds them to the permanent banned_users table in
master_userlist.db. This is a soft ban only -- it does NOT delete or touch
any of their existing records. Their users/agent_assignments/
balance_adjustments rows, and their deposits/withdrawals/wallet_transactions/
bonuses rows, keep existing and keep updating normally as new activity comes
in; the ban only makes build_deposit_report.py exclude them from every
report, listing, export, and the user-search index (see the
"report_daily_db_path"/"report_master_db_path" filtered-copy logic in its
main()) -- so they're fully invisible on the dashboard without losing any
history. Unban with unban_user.py.

Triggered by the "Ban User" widget on the dashboard's Search User page (via
the 08-project-upload worker's /ban-user endpoint) -- same pattern as
reassign_agent.py.

Usage: python3 ban_user.py --user-id 12345
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta

import boto3

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER_DB = os.path.join(BASE, "master_userlist.db")
DAILY_DB = os.path.join(BASE, "daily_records.db")


def r2_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-id", required=True, type=int)
    args = ap.parse_args()

    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()
    try:
        s3.download_file(bucket, "master_userlist.db", MASTER_DB)
        # Not modified here, but build_deposit_report.py (run right after
        # this script, in the same job workspace) needs it present locally
        # to refresh the live report -- same pattern as reassign_agent.py.
        s3.download_file(bucket, "daily_records.db", DAILY_DB)
    except Exception as e:
        print(f"FATAL: could not download DBs from R2: {e}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(MASTER_DB)
    exists = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (args.user_id,)).fetchone()
    conn.execute("CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY, banned_at TEXT)")
    now = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO banned_users (user_id, banned_at) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET banned_at = excluded.banned_at",
        (args.user_id, now),
    )
    conn.commit()
    conn.close()
    if not exists:
        print(f"NOTE: user_id {args.user_id} was not found in users table (banning anyway)")

    s3.upload_file(MASTER_DB, bucket, "master_userlist.db")
    print(f"Banned user {args.user_id} at {now} -- no records deleted, they'll disappear from reports on the next refresh")


if __name__ == "__main__":
    main()
