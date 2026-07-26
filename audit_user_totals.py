"""
Read-only audit: for a specific user, cross-checks stored users.total_recharge
and users.user_balance in master_userlist.db against what's independently
derivable from daily_records.db's own raw deposits/wallet_transactions rows
(within the retained 33-day window), to catch drift between the two.

Also does a bulk pass: recomputes the TRUE wallet balance (see
verify_ledger_lag.py / the change_after-lags-by-one-row fix) for every user
with wallet activity and flags any whose stored user_balance doesn't match,
which would indicate the fix hasn't been applied to them (e.g. no wallet
activity since the fix landed, or a data issue).

Usage: python3 audit_user_totals.py --user-id 949900
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
    ap.add_argument("--user-id", type=int, default=None)
    ap.add_argument("--bulk-mismatch-scan", action="store_true")
    args = ap.parse_args()

    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()
    s3.download_file(bucket, "master_userlist.db", MASTER_DB)
    s3.download_file(bucket, "daily_records.db", DAILY_DB)

    mconn = sqlite3.connect(MASTER_DB)
    dconn = sqlite3.connect(DAILY_DB)

    if args.user_id is not None:
        uid = args.user_id
        stored = mconn.execute(
            "SELECT total_recharge, total_withdrawal, user_balance, deposit_sync_time, withdrawal_sync_time "
            "FROM users WHERE user_id = ?", (uid,)
        ).fetchone()
        print(f"=== users table (master_userlist.db) for {uid} ===")
        print(" ", stored)

        print(f"=== deposits table (daily_records.db, retained window) for {uid} ===")
        dep_rows = dconn.execute(
            "SELECT COUNT(*), SUM(order_amount), MIN(create_time), MAX(create_time) "
            "FROM deposits WHERE user_id = ? AND status = 'COMPLETE'", (uid,)
        ).fetchone()
        print(f"  COMPLETE deposits in window: count={dep_rows[0]}, sum={dep_rows[1]}, first={dep_rows[2]}, last={dep_rows[3]}")
        dep_all = dconn.execute(
            "SELECT COUNT(*), SUM(order_amount) FROM deposits WHERE user_id = ?", (uid,)
        ).fetchone()
        print(f"  ALL-status deposits in window: count={dep_all[0]}, sum={dep_all[1]}")

        wd_rows = dconn.execute(
            "SELECT COUNT(*), SUM(withdraw_amount) FROM withdrawals WHERE user_id = ? AND status = 2", (uid,)
        ).fetchone()
        print(f"  Complete withdrawals in window: count={wd_rows[0]}, sum={wd_rows[1]}")

        latest = dconn.execute(
            "SELECT change_after, change_value, direction, create_time, id FROM wallet_transactions "
            "WHERE user_id = ? ORDER BY create_time DESC, id DESC LIMIT 1", (uid,)
        ).fetchone()
        if latest and latest[0] is not None and latest[1] is not None and latest[2] is not None:
            true_balance = latest[0] + latest[1] if latest[2] == 0 else latest[0] - latest[1]
            print(f"=== latest wallet_transactions row: change_after={latest[0]}, change_value={latest[1]}, "
                  f"direction={latest[2]}, create_time={latest[3]}, id={latest[4]} ===")
            print(f"=== true current balance (formula-derived): {true_balance} ===")
            if stored:
                print(f"=== stored user_balance: {stored[2]} -- {'MATCH' if abs(stored[2] - true_balance) < 0.01 else 'MISMATCH'} ===")

    if args.bulk_mismatch_scan:
        print("=== BULK SCAN: comparing stored user_balance vs formula-derived true balance ===")
        rows = dconn.execute(
            "SELECT user_id, change_after, change_value, direction, create_time, id FROM wallet_transactions "
            "WHERE user_id IS NOT NULL"
        ).fetchall()
        latest_by_user = {}
        for user_id, change_after, change_value, direction, create_time, row_id in rows:
            key = (str(create_time), row_id)
            if user_id not in latest_by_user or key > latest_by_user[user_id][0]:
                latest_by_user[user_id] = (key, change_after, change_value, direction)

        stored_balances = dict(mconn.execute("SELECT user_id, user_balance FROM users").fetchall())
        mismatches = []
        checked = 0
        for user_id, (_, change_after, change_value, direction) in latest_by_user.items():
            if change_after is None or change_value is None or direction is None:
                continue
            true_balance = change_after + change_value if direction == 0 else change_after - change_value
            stored = stored_balances.get(user_id)
            checked += 1
            if stored is None or abs((stored or 0) - true_balance) > 0.01:
                mismatches.append((user_id, stored, true_balance))
        print(f"Checked {checked} users with wallet activity; {len(mismatches)} mismatches")
        for m in mismatches[:50]:
            print(" MISMATCH:", m)

    mconn.close()
    dconn.close()


if __name__ == "__main__":
    main()
