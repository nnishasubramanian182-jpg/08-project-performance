"""
Removes a user from the permanent banned_users table (see ban_utils.py /
ban_user.py) so build_deposit_report.py stops excluding them from every
report/export/search-index. Banning never deleted anything -- their real
records kept updating normally the whole time it was banned -- so as soon
as this runs and the report is refreshed, their full history (including
whatever happened while banned) is visible again immediately.

Usage: python3 unban_user.py --user-id 1162645
"""
import argparse
import os
import sqlite3
import sys

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
    conn.execute("CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY, banned_at TEXT)")
    row = conn.execute("SELECT banned_at FROM banned_users WHERE user_id = ?", (args.user_id,)).fetchone()
    if row is None:
        print(f"user_id {args.user_id} was not in banned_users -- nothing to remove")
    else:
        conn.execute("DELETE FROM banned_users WHERE user_id = ?", (args.user_id,))
        conn.commit()
        print(f"Removed user_id {args.user_id} from banned_users (was banned at {row[0]})")
    conn.close()

    s3.upload_file(MASTER_DB, bucket, "master_userlist.db")
    print("Uploaded master_userlist.db")


if __name__ == "__main__":
    main()
