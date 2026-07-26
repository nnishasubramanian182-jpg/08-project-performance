"""
Records a permanent manual balance correction for a user in the new
balance_adjustments table (master_userlist.db), rather than as a
wallet_transactions row -- see api_pull_ingest.py's sync_master_userlist()
docstring (point 1b) for why a synthetic ledger row can't survive: every
wallet_transactions row's change_after is an ABSOLUTE balance reported by the
source platform itself, not a delta we control, so the very next real
transaction ingested for that user (computed upstream, oblivious to any
correction we inject) simply overwrites it on the next sync -- regardless of
whether the synthetic row is placed today, at the end of yesterday, or
anywhere else in the chronological order.

balance_adjustments instead holds a running total per user that
sync_master_userlist() adds ON TOP of the ledger-derived balance on every
future sync -- so it survives indefinitely, no matter how much new wallet
activity comes in for that user.

This script also removes any earlier synthetic wallet_transactions row
(consume_type='manual_deduct') for the same user, migrating it to the new
mechanism, and immediately recomputes user_balance from the latest real
ledger entry + the new cumulative adjustment (not just the delta), so the
dashboard reflects it right away instead of waiting for the next wallet sync.

Usage: python3 add_balance_adjustment.py --user-id 1761219 --amount -20000 \
    --reason "Manual deduct: recurring 20000 wallet ledger gap"
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
    ap.add_argument("--amount", required=True, type=float, help="Signed amount; negative to deduct")
    ap.add_argument("--reason", default="Manual adjustment")
    args = ap.parse_args()

    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()
    try:
        s3.download_file(bucket, "master_userlist.db", MASTER_DB)
        s3.download_file(bucket, "daily_records.db", DAILY_DB)
    except Exception as e:
        print(f"FATAL: could not download DBs from R2: {e}", file=sys.stderr)
        sys.exit(1)

    dconn = sqlite3.connect(DAILY_DB)
    dcur = dconn.cursor()
    removed = dcur.execute(
        "DELETE FROM wallet_transactions WHERE user_id = ? AND consume_type = 'manual_deduct'",
        (args.user_id,),
    ).rowcount
    dconn.commit()
    if removed:
        print(f"Removed {removed} earlier synthetic manual_deduct ledger row(s) for user {args.user_id} (migrating to balance_adjustments)")

    latest = dcur.execute(
        "SELECT change_after, change_value, direction, create_time, id FROM wallet_transactions "
        "WHERE user_id = ? ORDER BY create_time DESC, id DESC LIMIT 1",
        (args.user_id,),
    ).fetchone()
    dconn.close()
    # change_after lags by one row -- true balance is this row's own
    # change_after plus/minus its own change_value (see verify_ledger_lag.py).
    latest_ledger_balance = None
    if latest and latest[0] is not None and latest[1] is not None and latest[2] is not None:
        latest_ledger_balance = latest[0] + latest[1] if latest[2] == 0 else latest[0] - latest[1]
        print(f"Latest real ledger row for user {args.user_id}: change_after={latest[0]}, change_value={latest[1]}, direction={latest[2]}, create_time={latest[3]} -> true balance={latest_ledger_balance}")

    mconn = sqlite3.connect(MASTER_DB)
    mcur = mconn.cursor()
    mcur.execute(
        "CREATE TABLE IF NOT EXISTS balance_adjustments ("
        "user_id INTEGER PRIMARY KEY, total_adjustment REAL NOT NULL, "
        "last_reason TEXT, updated_at TEXT)"
    )
    prior_adj_row = mcur.execute(
        "SELECT total_adjustment FROM balance_adjustments WHERE user_id = ?", (args.user_id,)
    ).fetchone()
    prior_adjustment = prior_adj_row[0] if prior_adj_row else 0.0
    new_adjustment = round(prior_adjustment + args.amount, 2)
    now = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    mcur.execute(
        "INSERT INTO balance_adjustments (user_id, total_adjustment, last_reason, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET total_adjustment = excluded.total_adjustment, "
        "last_reason = excluded.last_reason, updated_at = excluded.updated_at",
        (args.user_id, new_adjustment, args.reason, now),
    )
    print(f"balance_adjustments for user {args.user_id}: {prior_adjustment} -> {new_adjustment} (this change: {args.amount})")

    urow = mcur.execute("SELECT user_balance FROM users WHERE user_id = ?", (args.user_id,)).fetchone()
    if urow is None:
        print(f"FATAL: user_id {args.user_id} not found in master_userlist.db users table", file=sys.stderr)
        sys.exit(1)
    print(f"Before: user_balance={urow[0]}")
    if latest_ledger_balance is not None:
        new_balance = round(latest_ledger_balance + new_adjustment, 2)
        mcur.execute("UPDATE users SET user_balance = ? WHERE user_id = ?", (new_balance, args.user_id))
        print(f"After:  user_balance={new_balance} (ledger {latest_ledger_balance} + adjustment {new_adjustment})")
    else:
        print("No wallet_transactions found for this user -- user_balance left as-is; adjustment will apply once they have wallet activity.")
    mconn.commit()
    mconn.close()

    s3.upload_file(DAILY_DB, bucket, "daily_records.db")
    s3.upload_file(MASTER_DB, bucket, "master_userlist.db")
    print("Uploaded both DBs")


if __name__ == "__main__":
    main()
