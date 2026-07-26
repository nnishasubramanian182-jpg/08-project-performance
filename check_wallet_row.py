"""One-off read-only check: print wallet_transactions rows for a user around
a specific timestamp, to verify a claimed historical balance before trusting
it as a rebase anchor.

Usage: python3 check_wallet_row.py --user-id 1761219 --time "2026-07-04 01:32:52"
"""
import argparse
import os
import sqlite3

import boto3

BASE = os.path.dirname(os.path.abspath(__file__))
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
    ap.add_argument("--time", required=True, help="YYYY-MM-DD HH:MM:SS, exact create_time to look for")
    args = ap.parse_args()

    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()
    s3.download_file(bucket, "daily_records.db", DAILY_DB)

    conn = sqlite3.connect(DAILY_DB)
    cur = conn.cursor()
    print(f"=== Exact match for user {args.user_id} at {args.time} ===")
    for row in cur.execute(
        "SELECT id, game_name, change_value, change_after, direction, consume_type, create_time "
        "FROM wallet_transactions WHERE user_id = ? AND create_time = ?",
        (args.user_id, args.time),
    ).fetchall():
        print(" ", row)

    day = args.time[:10]
    print(f"=== All rows for user {args.user_id} on {day} between 01:30:00 and 01:35:00 ===")
    for row in cur.execute(
        "SELECT id, game_name, change_value, change_after, direction, consume_type, create_time "
        "FROM wallet_transactions WHERE user_id = ? AND create_time BETWEEN ? AND ? ORDER BY create_time, id",
        (args.user_id, f"{day} 01:30:00", f"{day} 01:35:00"),
    ).fetchall():
        print(" ", row)

    print(f"=== Last row of {day} for user {args.user_id} (by create_time, id) ===")
    last = cur.execute(
        "SELECT id, game_name, change_value, change_after, direction, consume_type, create_time "
        "FROM wallet_transactions WHERE user_id = ? AND create_time LIKE ? ORDER BY create_time DESC, id DESC LIMIT 1",
        (args.user_id, f"{day}%"),
    ).fetchone()
    print(" ", last)
    conn.close()


if __name__ == "__main__":
    main()
