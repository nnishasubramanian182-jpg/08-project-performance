"""
One-off backfill: recovers agent_performance rows for a past date from its
saved reports/analytics_history/<date>.json snapshot, which already has
the exact reactivation/vip_upgrade/retention/premium_active shape
compute_agent_performance_rows() needs -- this survived independently of
the agent_performance table-persistence bug fixed in build_deposit_report.py
(that snapshot is written via s3.put_object, not the SQLite table that
never got re-uploaded).

Only works for dates still covered by analytics_history's own rolling
7-day retention -- it can't recover a date whose snapshot has already been
pruned.

Usage: python3 backfill_agent_performance.py --date 2026-07-04
"""
import argparse
import json
import os
import sqlite3
import sys

import boto3

import build_deposit_report as bdr

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
    ap.add_argument("--date", required=True, help="YYYY-MM-DD to backfill")
    args = ap.parse_args()

    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()
    try:
        s3.download_file(bucket, "master_userlist.db", MASTER_DB)
        # Not touched by this script, but build_deposit_report.py (run right
        # after, in the same job workspace) needs it present locally to
        # refresh the live report -- same pattern reassign_agent.py uses.
        s3.download_file(bucket, "daily_records.db", DAILY_DB)
    except Exception as e:
        print(f"FATAL: could not download DBs from R2: {e}", file=sys.stderr)
        sys.exit(1)

    snapshot_key = f"reports/analytics_history/{args.date}.json"
    try:
        obj = s3.get_object(Bucket=bucket, Key=snapshot_key)
        snapshot = json.loads(obj["Body"].read())
    except Exception as e:
        print(f"FATAL: no analytics_history snapshot for {args.date} ({snapshot_key}): {e}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(MASTER_DB)
    cur = conn.cursor()
    try:
        agent_by_user = dict(cur.execute("SELECT user_id, agent_name FROM agent_assignments").fetchall())
    except sqlite3.OperationalError:
        agent_by_user = {}
    agent_list = sorted(set(agent_by_user.values()))
    if not agent_list:
        print("FATAL: no agents in agent_assignments -- nothing to backfill", file=sys.stderr)
        sys.exit(1)

    cur.execute(
        "CREATE TABLE IF NOT EXISTS agent_performance ("
        "date TEXT, agent_name TEXT, category TEXT, numerator REAL, denominator REAL, "
        "PRIMARY KEY (date, agent_name, category))"
    )
    rows = bdr.compute_agent_performance_rows(
        agent_list, snapshot["reactivation"], snapshot["vip_upgrade"],
        snapshot["retention"]["first_deposit"], snapshot["premium_active"], args.date,
    )
    cur.executemany(
        "INSERT OR REPLACE INTO agent_performance (date, agent_name, category, numerator, denominator) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    print(f"Backfilled {len(rows)} agent_performance rows for {args.date} ({len(agent_list)} agents)")
    conn.close()

    s3.upload_file(MASTER_DB, bucket, "master_userlist.db")
    print("Uploaded master_userlist.db")


if __name__ == "__main__":
    main()
