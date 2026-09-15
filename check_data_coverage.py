"""One-off read-only diagnostic: per-day row counts for withdrawals,
wallet_transactions, and bonuses over the last N days, to verify the
pipeline actually has complete data (not just that recent runs succeeded).

Usage: python3 check_data_coverage.py --days 10
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
    ap.add_argument("--days", type=int, default=10)
    args = ap.parse_args()

    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()
    s3.download_file(bucket, "daily_records.db", DAILY_DB)

    conn = sqlite3.connect(DAILY_DB)
    cur = conn.cursor()

    print(f"=== withdrawals: per-day counts, last {args.days} days ===")
    for row in cur.execute(
        "SELECT substr(create_time,1,10) as d, COUNT(*), SUM(withdraw_amount) "
        "FROM withdrawals GROUP BY d ORDER BY d DESC LIMIT ?", (args.days,)
    ).fetchall():
        print(" ", row)

    print(f"=== wallet_transactions: per-day counts, last {args.days} days ===")
    for row in cur.execute(
        "SELECT substr(create_time,1,10) as d, COUNT(*) "
        "FROM wallet_transactions GROUP BY d ORDER BY d DESC LIMIT ?", (args.days,)
    ).fetchall():
        print(" ", row)

    print(f"=== bonuses: per-day counts, last {args.days} days ===")
    for row in cur.execute(
        "SELECT substr(create_time,1,10) as d, COUNT(*), SUM(change_value) "
        "FROM bonuses GROUP BY d ORDER BY d DESC LIMIT ?", (args.days,)
    ).fetchall():
        print(" ", row)

    print(f"=== deposits: per-day counts, last {args.days} days (for cross-check) ===")
    for row in cur.execute(
        "SELECT substr(create_time,1,10) as d, COUNT(*) "
        "FROM deposits GROUP BY d ORDER BY d DESC LIMIT ?", (args.days,)
    ).fetchall():
        print(" ", row)

    print("=== retention window (oldest/newest create_time per table) ===")
    for table in ["deposits", "withdrawals", "wallet_transactions", "bonuses"]:
        row = cur.execute(f"SELECT MIN(create_time), MAX(create_time), COUNT(*) FROM {table}").fetchone()
        print(f"  {table}: {row}")

    conn.close()


if __name__ == "__main__":
    main()
