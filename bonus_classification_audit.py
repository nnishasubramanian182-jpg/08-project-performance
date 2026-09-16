"""One-off read-only diagnostic: pin down exactly which wallet_transactions
columns (game_name/source/source_id) produce the fragmented
VIP_DAILY_RECHARGE_CASHBACK matched_category rows in bonuses, since the
raw LIKE filter against wallet_transactions.source_id doesn't reconcile
with the row count already found in bonuses.

Usage: python3 bonus_classification_audit.py
"""
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
    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()
    s3.download_file(bucket, "daily_records.db", DAILY_DB)
    print("downloaded daily_records.db")

    conn = sqlite3.connect(DAILY_DB)
    cur = conn.cursor()

    print("\n=== bonuses rows matching the fragmented family, joined to wallet_transactions ===")
    rows = cur.execute(
        "SELECT b.id, b.matched_category, w.game_name, w.source, w.source_id, w.direction "
        "FROM bonuses b LEFT JOIN wallet_transactions w ON w.id = b.id "
        "WHERE b.matched_category LIKE 'VIP_DAILY_RECHARGE_CASHBACK%' LIMIT 20"
    ).fetchall()
    for r in rows:
        print(f"  {r}")

    print("\n=== Are the corresponding wallet_transactions rows still present? ===")
    missing = cur.execute(
        "SELECT COUNT(*) FROM bonuses b WHERE b.matched_category LIKE 'VIP_DAILY_RECHARGE_CASHBACK%' "
        "AND b.id NOT IN (SELECT id FROM wallet_transactions)"
    ).fetchone()[0]
    present = cur.execute(
        "SELECT COUNT(*) FROM bonuses b WHERE b.matched_category LIKE 'VIP_DAILY_RECHARGE_CASHBACK%' "
        "AND b.id IN (SELECT id FROM wallet_transactions)"
    ).fetchone()[0]
    print(f"orphaned (wallet_transactions row gone): {missing}")
    print(f"still present: {present}")

    print("\n=== bonuses date range for this family ===")
    date_range = cur.execute(
        "SELECT MIN(create_time), MAX(create_time), COUNT(*) FROM bonuses "
        "WHERE matched_category LIKE 'VIP_DAILY_RECHARGE_CASHBACK%'"
    ).fetchone()
    print(f"  {date_range}")

    conn.close()


if __name__ == "__main__":
    main()
