"""
Read-only verification: tests the hypothesis that wallet_transactions'
change_after column is lagged by one row -- i.e. that stored change_after on
row i is actually the TRUE balance from row i-1 (before row i's own
change_value was applied), not the result of row i itself. If true, the
correct running balance after row i is:
    stored[i] + change_value[i]   if direction[i] == 0 (credit)
    stored[i] - change_value[i]   if direction[i] == 1 (debit)
and that should equal stored[i+1] for the very next row of the same user.

Usage: python3 verify_ledger_lag.py [--sample 30]
"""
import argparse
import os
import sqlite3
from collections import defaultdict

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
    ap.add_argument("--sample", type=int, default=30)
    args = ap.parse_args()

    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()
    s3.download_file(bucket, "daily_records.db", DAILY_DB)

    conn = sqlite3.connect(DAILY_DB)
    cur = conn.cursor()

    print("=== distinct direction values (sampled) ===")
    for row in cur.execute(
        "SELECT direction, consume_type, COUNT(*) FROM wallet_transactions "
        "GROUP BY direction, consume_type ORDER BY COUNT(*) DESC LIMIT 20"
    ).fetchall():
        print(" ", row)

    users = [r[0] for r in cur.execute(
        "SELECT user_id FROM wallet_transactions WHERE user_id IS NOT NULL "
        "GROUP BY user_id HAVING COUNT(*) >= 5 ORDER BY RANDOM() LIMIT ?",
        (args.sample,),
    ).fetchall()]

    total_pairs = 0
    matches = 0
    mismatches = []
    for uid in users:
        rows = cur.execute(
            "SELECT id, change_value, change_after, direction, create_time FROM wallet_transactions "
            "WHERE user_id = ? ORDER BY create_time, id",
            (uid,),
        ).fetchall()
        for i in range(len(rows) - 1):
            rid, cv, stored, direction, ct = rows[i]
            next_id, next_cv, next_stored, next_direction, next_ct = rows[i + 1]
            if cv is None or stored is None or next_stored is None or direction is None:
                continue
            predicted_next = stored + cv if direction == 0 else stored - cv
            total_pairs += 1
            if abs(predicted_next - next_stored) < 0.01:
                matches += 1
            else:
                mismatches.append((uid, rid, cv, stored, direction, predicted_next, next_id, next_stored))

    print(f"\n=== lag hypothesis check across {len(users)} users, {total_pairs} consecutive pairs ===")
    print(f"matches: {matches} / {total_pairs} ({round(100*matches/total_pairs, 2) if total_pairs else 0}%)")
    print(f"mismatches: {len(mismatches)}")
    for m in mismatches[:15]:
        print(" MISMATCH:", m)

    conn.close()


if __name__ == "__main__":
    main()
