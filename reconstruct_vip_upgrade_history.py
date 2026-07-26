"""
Read-only one-off: reconstruct the VIP Upgrade report (Low V2-V4, High
V5-V15) for a historical date range, WITHOUT relying on the
reports/analytics_history/*.json day-start snapshots build_deposit_report.py
normally uses (those are purged to the last ~7 days).

Reconstruction works because VIP level is a pure function of a user's
CUMULATIVE lifetime deposit total (VIP_THRESHOLDS) and total_recharge in
master_userlist.db's users table is that cumulative total, continuously
synced and never purged. daily_records.db's deposits table (rolling 33-day
window) gives exactly enough day-by-day deposit detail to walk that
cumulative total backwards/forwards across the requested window:

  running_before_window = total_recharge_now
                           - sum(deposits within the window)
                           - sum(deposits after the window, up to now)
  then walk the window day by day, adding each day's deposits to `running`
  and checking whether the mapped VIP level crossed a tier boundary.

Usage: python3 reconstruct_vip_upgrade_history.py --start 2026-06-28 --end 2026-07-07
"""
import argparse
import json
import os
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta

import boto3

import ban_utils

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER_DB = os.path.join(BASE, "master_userlist.db")
DAILY_DB = os.path.join(BASE, "daily_records.db")

# Kept identical to build_deposit_report.py's VIP_THRESHOLDS.
VIP_THRESHOLDS = {
    0: 0, 1: 200, 2: 1500, 3: 9600, 4: 19600, 5: 95600, 6: 295600, 7: 795600,
    8: 1795600, 9: 3795600, 10: 8795600, 11: 16795600, 12: 28795600,
    13: 44795600, 14: 69795600, 15: 119795600,
}
SORTED_LEVELS = sorted(VIP_THRESHOLDS)


def vip_level_for(cumulative):
    level = 0
    for lvl in SORTED_LEVELS:
        if cumulative >= VIP_THRESHOLDS[lvl]:
            level = lvl
        else:
            break
    return level


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
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    args = ap.parse_args()

    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()
    s3.download_file(bucket, "master_userlist.db", MASTER_DB)
    s3.download_file(bucket, "daily_records.db", DAILY_DB)

    window_start = datetime.strptime(args.start, "%Y-%m-%d").date()
    window_end = datetime.strptime(args.end, "%Y-%m-%d").date()
    window_dates = []
    d = window_start
    while d <= window_end:
        window_dates.append(d.isoformat())
        d += timedelta(days=1)
    window_date_set = set(window_dates)

    banned_ids = set(ban_utils.get_banned_user_ids(MASTER_DB))

    mconn = sqlite3.connect(MASTER_DB)
    total_recharge_by_user = {
        uid: tr for uid, tr in mconn.execute("SELECT user_id, total_recharge FROM users").fetchall()
        if uid not in banned_ids
    }
    agent_by_user = {}
    try:
        agent_by_user = dict(mconn.execute("SELECT user_id, agent_name FROM agent_assignments").fetchall())
    except sqlite3.OperationalError:
        pass
    mconn.close()

    dconn = sqlite3.connect(DAILY_DB)
    # All deposits from window_start onward (covers "in window" + "after
    # window, up to now" in one query -- daily_records.db's 33-day retention
    # already guarantees nothing before window_start matters, since we only
    # need the running total AS OF window_start, taken from total_recharge
    # minus everything from window_start onward).
    rows = dconn.execute(
        "SELECT user_id, order_amount, create_time FROM deposits "
        "WHERE status = 'COMPLETE' AND user_id IS NOT NULL AND create_time >= ?",
        (window_start.isoformat(),),
    ).fetchall()
    dconn.close()

    dep_by_user_date = defaultdict(lambda: defaultdict(float))
    for user_id, amount, create_time in rows:
        date_str = str(create_time)[:10]
        dep_by_user_date[user_id][date_str] += amount or 0.0

    daily_totals = {
        "low": {d: {"upgraded": [], "near_at_start": 0} for d in window_dates},
        "high": {d: {"upgraded": [], "near_at_start": 0} for d in window_dates},
    }

    for user_id, by_date in dep_by_user_date.items():
        total_now = total_recharge_by_user.get(user_id)
        if total_now is None:
            continue
        sum_from_window_start_onward = sum(by_date.values())
        running = total_now - sum_from_window_start_onward
        for date_str in window_dates:
            day_amount = by_date.get(date_str, 0.0)
            vip_before = vip_level_for(running)
            # near-upgrade check at START of this day -- same gap bands as
            # the live Action Center near_upgrade_low/high lists. Only users
            # who were ALREADY in this band get counted as a "conversion"
            # if they cross today (matches the live report's definition:
            # near-upgrade cohort at day start who have since upgraded, not
            # just any VIP jump).
            near_cohort = None
            gap_before = None
            if vip_before < 15 and (vip_before + 1) in VIP_THRESHOLDS:
                gap_before = VIP_THRESHOLDS[vip_before + 1] - running
                if 2 <= vip_before <= 4 and 1 <= gap_before <= 1000:
                    near_cohort = "low"
                    daily_totals["low"][date_str]["near_at_start"] += 1
                elif 5 <= vip_before <= 14 and 1 <= gap_before <= 50000:
                    near_cohort = "high"
                    daily_totals["high"][date_str]["near_at_start"] += 1
            if day_amount:
                running += day_amount
                vip_after = vip_level_for(running)
                if near_cohort and vip_after > vip_before:
                    row = {
                        "user_id": user_id,
                        "agent": agent_by_user.get(user_id) or "Un-Assigned",
                        "vip_before": vip_before,
                        "vip_after": vip_after,
                        "total_deposit": round(day_amount, 2),
                        "amount_over_minimum": round(day_amount - gap_before, 2),
                    }
                    daily_totals[near_cohort][date_str]["upgraded"].append(row)

    def summarize(cohort):
        out = []
        for date_str in window_dates:
            upgraded = daily_totals[cohort][date_str]["upgraded"]
            near_at_start = daily_totals[cohort][date_str]["near_at_start"]
            # near_at_start already INCLUDES users who upgraded today (they
            # were near-upgrade at the start of the day) -- matches how the
            # live report's baseline = upgraded_today + still_near_upgrade.
            pct = round(len(upgraded) / near_at_start * 100, 2) if near_at_start else 0.0
            out.append({
                "date": date_str,
                "upgraded_count": len(upgraded),
                "near_upgrade_cohort_at_start": near_at_start,
                "pct_upgraded": pct,
                "rows": sorted(upgraded, key=lambda r: -r["total_deposit"]),
            })
        return out

    result = {"low": summarize("low"), "high": summarize("high")}

    print("=== VIP_HISTORY_JSON_START ===")
    print(json.dumps(result))
    print("=== VIP_HISTORY_JSON_END ===")


if __name__ == "__main__":
    main()
