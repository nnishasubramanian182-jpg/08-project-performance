"""
One-off (dispatchable) job: re-derives users.user_balance for EVERY user
from their wallet ledger's own running balance, using the EXISTING R2 data
already fetched by the last pipeline run -- no business API re-fetch, no
new deposits/withdrawals/wallet download.

Also prints a full diagnostic for one user_id first, to reconcile a
reported-wrong balance against the raw wallet_transactions rows before
trusting the bulk fix.

Usage: python3 resync_user_balances.py --diagnose-user 1761219
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
    ap.add_argument("--diagnose-user", type=int, default=None)
    ap.add_argument("--apply", action="store_true", help="Actually write the resynced balances (omit for dry-run diagnostic only)")
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

    print("=== DIAGNOSTIC: wallet_transactions rows per calendar day (retained window) ===")
    per_day = dcur.execute(
        "SELECT substr(create_time, 1, 10) AS d, COUNT(*), COUNT(DISTINCT user_id), "
        "MIN(create_time), MAX(create_time) FROM wallet_transactions "
        "WHERE create_time IS NOT NULL GROUP BY d ORDER BY d"
    ).fetchall()
    for d, n, users, mn, mx in per_day:
        print(f"  {d}: {n:>8} rows, {users:>6} users, first={mn}, last={mx}")

    if args.diagnose_user is not None:
        uid = args.diagnose_user
        print(f"=== DIAGNOSTIC: user {uid} -- ALL retained wallet_transactions rows, ordered by id ===")
        rows = dcur.execute(
            "SELECT id, game_name, source_id, source, change_value, change_after, direction, create_time "
            "FROM wallet_transactions WHERE user_id = ? ORDER BY id",
            (uid,),
        ).fetchall()
        print(f"total rows: {len(rows)}")
        for r in rows[-15:]:
            print(" ", r)
        print(f"=== last row by id: {rows[-1] if rows else None} ===")
        by_time = sorted(rows, key=lambda r: (str(r[7]), r[0]))
        last = by_time[-1] if by_time else None
        print(f"=== last row by (create_time, id): {last} ===")
        if last is not None and last[4] is not None and last[6] is not None:
            # change_after lags by one row -- true balance is this row's own
            # change_after plus/minus its own change_value (see
            # verify_ledger_lag.py). Columns: id, game_name, source_id,
            # source, change_value, change_after, direction, create_time.
            true_balance = last[5] + last[4] if last[6] == 0 else last[5] - last[4]
            print(f"=== true current balance (change_after {'+ ' if last[6] == 0 else '- '}change_value): {true_balance} ===")

        mconn_diag = sqlite3.connect(MASTER_DB)
        current = mconn_diag.execute("SELECT user_balance FROM users WHERE user_id = ?", (uid,)).fetchone()
        print(f"=== current stored user_balance: {current} ===")
        mconn_diag.close()

    if not args.apply:
        print("Dry run only (pass --apply to write the resync). Exiting.")
        dconn.close()
        return

    # Bulk resync: for every user, the "latest" wallet transaction is
    # determined by (create_time, id) -- id as a tie-breaker for rows that
    # share the same create_time (down to the second), since id reflects
    # true event order from the source system and create_time alone can't
    # disambiguate same-second transactions.
    print("=== Resyncing user_balance for all users with wallet activity ===")
    # change_after lags by one row (see verify_ledger_lag.py -- row i's
    # change_after is the true balance BEFORE row i's own transaction, not
    # after), so the true current balance is the latest row's own
    # change_after plus (credit, direction 0) or minus (debit, direction 1)
    # that same row's own change_value.
    all_rows = dcur.execute(
        "SELECT user_id, change_after, change_value, direction, create_time, id FROM wallet_transactions WHERE user_id IS NOT NULL"
    ).fetchall()
    latest_by_user = {}
    for user_id, change_after, change_value, direction, create_time, row_id in all_rows:
        key = (str(create_time), row_id)
        if user_id not in latest_by_user or key > latest_by_user[user_id][0]:
            latest_by_user[user_id] = (key, change_after, change_value, direction)
    dconn.close()

    mconn = sqlite3.connect(MASTER_DB)
    mcur = mconn.cursor()
    updated = 0
    for user_id, (_, change_after, change_value, direction) in latest_by_user.items():
        if change_after is None or change_value is None or direction is None:
            continue
        true_balance = change_after + change_value if direction == 0 else change_after - change_value
        mcur.execute("UPDATE users SET user_balance = ? WHERE user_id = ?", (true_balance, user_id))
        if mcur.rowcount:
            updated += 1
    mconn.commit()
    mconn.close()
    print(f"Resynced user_balance for {updated} users (of {len(latest_by_user)} with wallet activity in the retained window)")

    s3.upload_file(MASTER_DB, bucket, "master_userlist.db")
    print("Uploaded corrected master_userlist.db")


if __name__ == "__main__":
    main()
