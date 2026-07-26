"""
Read-only one-off analysis: new vs old depositors, per day, for a date
window -- "new" = a user whose FIRST-EVER deposit (deposits.is_first_deposit
= 1) landed on that day; "old" = anyone else who deposited that day (a
repeat depositor, first deposit was on an earlier day). Also breaks out
withdrawal behavior for each cohort, and 3-day return-deposit retention for
new users, split by whether they withdrew during that 3-day window or not.

Usage: python3 weekly_new_old_analysis.py --start 2026-06-30 --end 2026-07-06
"""
import argparse
import json
import os
import sqlite3
from datetime import datetime, timedelta

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
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD")
    args = ap.parse_args()

    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()
    s3.download_file(bucket, "daily_records.db", DAILY_DB)
    conn = sqlite3.connect(DAILY_DB)

    start = datetime.strptime(args.start, "%Y-%m-%d").date()
    end = datetime.strptime(args.end, "%Y-%m-%d").date()
    # Fetch a bit past `end` too, purely so 3-day retention can be checked
    # for new users on the last couple of days in the window.
    lookahead_end = end + timedelta(days=3)

    all_deposits = conn.execute(
        "SELECT user_id, order_amount, create_time, is_first_deposit FROM deposits "
        "WHERE status = 'COMPLETE' AND user_id IS NOT NULL AND create_time >= ? AND create_time < ?",
        (start.isoformat(), (lookahead_end + timedelta(days=1)).isoformat()),
    ).fetchall()

    all_withdrawals = conn.execute(
        "SELECT user_id, withdraw_amount, create_time, status FROM withdrawals "
        "WHERE user_id IS NOT NULL AND create_time >= ? AND create_time < ?",
        (start.isoformat(), (lookahead_end + timedelta(days=1)).isoformat()),
    ).fetchall()
    conn.close()

    # Index deposits/withdrawals by date string for fast per-day lookup.
    dep_by_date = {}
    for user_id, amount, create_time, is_first in all_deposits:
        d = str(create_time)[:10]
        dep_by_date.setdefault(d, []).append((user_id, amount or 0.0, bool(is_first)))

    wd_by_date = {}
    for user_id, amount, create_time, status in all_withdrawals:
        d = str(create_time)[:10]
        wd_by_date.setdefault(d, []).append((user_id, amount or 0.0, status))

    # first_deposit_date[user_id] = the date string of their is_first_deposit=1 row
    first_deposit_date = {}
    for d, rows in dep_by_date.items():
        for user_id, amount, is_first in rows:
            if is_first:
                first_deposit_date[user_id] = d

    daily_rows = []
    d = start
    while d <= end:
        dstr = d.isoformat()
        rows = dep_by_date.get(dstr, [])
        new_user_ids = {uid for uid, amt, is_first in rows if is_first}
        old_user_ids = {uid for uid, amt, is_first in rows if not is_first} - new_user_ids
        new_deposit_total = sum(amt for uid, amt, is_first in rows if uid in new_user_ids)
        old_deposit_total = sum(amt for uid, amt, is_first in rows if uid in old_user_ids)

        wd_rows = wd_by_date.get(dstr, [])
        wd_complete = [(uid, amt) for uid, amt, status in wd_rows if status == 2]
        old_withdrawers = {uid for uid, amt in wd_complete if uid in old_user_ids}
        new_withdrawers = {uid for uid, amt in wd_complete if uid in new_user_ids}
        old_wd_total = sum(amt for uid, amt in wd_complete if uid in old_withdrawers)
        new_wd_total = sum(amt for uid, amt in wd_complete if uid in new_withdrawers)

        daily_rows.append({
            "date": dstr,
            "old_users_count": len(old_user_ids),
            "old_users_deposit_total": round(old_deposit_total, 2),
            "new_users_count": len(new_user_ids),
            "new_users_deposit_total": round(new_deposit_total, 2),
            "old_users_withdraw_count": len(old_withdrawers),
            "old_users_withdraw_total": round(old_wd_total, 2),
            "new_users_withdraw_count": len(new_withdrawers),
            "new_users_withdraw_total": round(new_wd_total, 2),
            "total_deposit": round(new_deposit_total + old_deposit_total, 2),
            "total_depositor_count": len(new_user_ids) + len(old_user_ids),
        })
        d += timedelta(days=1)

    # 3-day retention for new users of each day in [start, end]: did they
    # deposit again (any deposit, first or repeat -- but by definition any
    # SECOND deposit is a repeat/is_first_deposit=0 row) within the 3 days
    # after their first deposit? Split by whether they withdrew (any status)
    # at all within that same day-D..day-D+3 window.
    retention_rows = []
    d = start
    while d <= end:
        dstr = d.isoformat()
        new_ids = {uid for uid, amt, is_first in dep_by_date.get(dstr, []) if is_first}
        if not new_ids:
            d += timedelta(days=1)
            continue
        window_dates = [(d + timedelta(days=k)).isoformat() for k in range(0, 4)]
        withdrew_ids = set()
        for wdstr in window_dates:
            for uid, amt, status in wd_by_date.get(wdstr, []):
                if uid in new_ids:
                    withdrew_ids.add(uid)
        returned_ids = set()
        for rdstr in window_dates[1:]:
            for uid, amt, is_first in dep_by_date.get(rdstr, []):
                if uid in new_ids and not is_first:
                    returned_ids.add(uid)
        withdrew_group = new_ids & withdrew_ids
        never_withdrew_group = new_ids - withdrew_ids
        retention_rows.append({
            "date": dstr,
            "new_users": len(new_ids),
            "withdrew_group_count": len(withdrew_group),
            "withdrew_group_returned": len(withdrew_group & returned_ids),
            "withdrew_group_retention_pct": round(100 * len(withdrew_group & returned_ids) / len(withdrew_group), 2) if withdrew_group else None,
            "never_withdrew_group_count": len(never_withdrew_group),
            "never_withdrew_group_returned": len(never_withdrew_group & returned_ids),
            "never_withdrew_group_retention_pct": round(100 * len(never_withdrew_group & returned_ids) / len(never_withdrew_group), 2) if never_withdrew_group else None,
        })
        d += timedelta(days=1)

    print("=== DAILY_ROWS_JSON_START ===")
    print(json.dumps(daily_rows))
    print("=== DAILY_ROWS_JSON_END ===")
    print("=== RETENTION_ROWS_JSON_START ===")
    print(json.dumps(retention_rows))
    print("=== RETENTION_ROWS_JSON_END ===")


if __name__ == "__main__":
    main()
