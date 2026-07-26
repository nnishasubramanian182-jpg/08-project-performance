"""
One-time catch-up for users.recharge_count: this column was bootstrapped
from the original userlist export (build_master_userlist.py) with each
user's TRUE lifetime deposit count at that moment, but was never
incremented afterward -- unlike total_recharge, which sync_master_userlist()
already updates on every deposit. api_pull_ingest.py now increments
recharge_count the same way going forward, but every deposit that landed
between the original bootstrap and this fix already advanced
deposit_sync_time (since total_recharge was tracking them) without ever
being counted here.

This script closes exactly that gap, once: for each user with a
deposit_sync_time set, it counts COMPLETE deposits currently in
daily_records.db with create_time <= deposit_sync_time (i.e. ones already
reflected in total_recharge but never counted here) and adds that count on
top of the existing recharge_count. Anything newer than deposit_sync_time
is untouched -- the next hourly sync picks those up itself, counting them
exactly once.

Must only be run ONCE: running it twice would double-add the same catch-up
count, since deposit_sync_time doesn't move as a side effect of this script.

Usage: python3 backfill_recharge_count.py [--apply]  (omit --apply for a dry-run report)
"""
import argparse
import os
import sqlite3

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
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()
    s3.download_file(bucket, "master_userlist.db", MASTER_DB)
    s3.download_file(bucket, "daily_records.db", DAILY_DB)

    mconn = sqlite3.connect(MASTER_DB)
    dconn = sqlite3.connect(DAILY_DB)

    users = mconn.execute(
        "SELECT user_id, deposit_sync_time, recharge_count FROM users WHERE deposit_sync_time IS NOT NULL"
    ).fetchall()
    print(f"Users with a deposit_sync_time set: {len(users)}")

    updates = []
    for user_id, sync_time, recharge_count in users:
        n = dconn.execute(
            "SELECT COUNT(*) FROM deposits WHERE user_id = ? AND status = 'COMPLETE' AND create_time <= ?",
            (user_id, sync_time),
        ).fetchone()[0]
        if n:
            updates.append((user_id, recharge_count or 0, n, (recharge_count or 0) + n))

    print(f"Users needing a catch-up count: {len(updates)}")
    for u in updates[:20]:
        print(" ", u)

    if not args.apply:
        print("Dry run only (pass --apply to write). Exiting.")
        mconn.close()
        dconn.close()
        return

    cur = mconn.cursor()
    for user_id, old_count, add_n, new_count in updates:
        cur.execute("UPDATE users SET recharge_count = ? WHERE user_id = ?", (new_count, user_id))
    mconn.commit()
    print(f"Applied catch-up to {len(updates)} users")
    mconn.close()
    dconn.close()

    s3.upload_file(MASTER_DB, bucket, "master_userlist.db")
    print("Uploaded master_userlist.db")


if __name__ == "__main__":
    main()
