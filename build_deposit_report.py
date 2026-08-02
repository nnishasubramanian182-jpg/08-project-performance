"""
Builds an aggregated deposit report -- channel-wise, amount-range, hourly
breakdowns, and success-rate analysis (total vs completed, by amount range /
channel / hour) -- bucketed per calendar date, from the deposits table and
uploads it as JSON to R2 for the "08-project-performance" dashboard Worker.

Usage: python3 build_deposit_report.py
Requires daily_records.db to be present locally (already downloaded by the
caller) and R2 credentials in env vars or .r2_credentials.
"""
import json
import os
import re
import shutil
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from datetime import time as dtime

import boto3

import ban_utils

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "daily_records.db")

AMOUNT_RANGES = [
    (200, 299),
    (300, 499),
    (500, 999),
    (1000, 1999),
    (2000, 2499),
    (2500, 4999),
    (5000, 9999),
    (10000, 19999),
    (20000, 50000),
]
RANGE_LABELS = [f"{lo}-{hi}" for lo, hi in AMOUNT_RANGES] + ["Other"]


def bucket_for_amount(amount):
    for lo, hi in AMOUNT_RANGES:
        if lo <= amount <= hi:
            return f"{lo}-{hi}"
    return "Other"


def load_creds():
    creds_path = os.path.join(BASE, ".r2_credentials")
    if os.path.exists(creds_path):
        return dict(line.strip().split("=", 1) for line in open(creds_path) if "=" in line)
    return {
        "R2_ACCESS_KEY_ID": os.environ["R2_ACCESS_KEY_ID"],
        "R2_SECRET_ACCESS_KEY": os.environ["R2_SECRET_ACCESS_KEY"],
        "R2_ENDPOINT_URL": os.environ["R2_ENDPOINT_URL"],
        "R2_BUCKET": os.environ["R2_BUCKET"],
    }


def load_json_with_r2_fallback(local_path, r2_key, creds, default):
    """Load a local JSON artifact if present (handed off same-job from
    api_pull_ingest.py), otherwise fall back to the copy it also uploads to
    R2. Needed because ingest.yml -- dispatched by ANY dashboard file
    upload (userlist/deposits/withdrawals/wallet/agents/bulk_reassign), not
    just the hourly api_pull.yml job -- re-runs this script in its OWN
    fresh checkout, with no local copy of reactivation/vip_upgrade
    candidates from the last api_pull.yml run. Without this fallback,
    Reactivation/VIP Upgrade silently zero out on every such upload until
    the next hourly run overwrites them again."""
    if os.path.exists(local_path):
        with open(local_path) as f:
            return json.load(f)
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=creds["R2_ENDPOINT_URL"],
            aws_access_key_id=creds["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=creds["R2_SECRET_ACCESS_KEY"],
            region_name="auto",
        )
        s3.download_file(creds["R2_BUCKET"], r2_key, local_path)
        with open(local_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"Could not load {r2_key} from R2 (falling back to empty): {e}")
        return default


def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace(" ", "T"))
    except ValueError:
        return None


TOP_DEPOSITORS_MIN_TOTAL = 10000.0


def top_depositors(records, withdrawal_records, min_total=TOP_DEPOSITORS_MIN_TOTAL, limit=500):
    """
    Per-user total COMPLETED deposit amount for this scope, filtered to
    users whose day total is >= min_total, sorted descending -- powers
    the Home page's Highest Deposit Users table. Also reports each such
    user's same-day withdrawal total, counting only In-Review/Processing/
    Complete orders (statuses 0/1/2) -- excludes Rejected/Failed.
    """
    totals = defaultdict(float)
    for r in records:
        if r["status"] == "COMPLETE" and r["user_id"] is not None:
            totals[r["user_id"]] += r["amount"]
    qualifying = {uid for uid, amt in totals.items() if amt >= min_total}

    withdraw_totals = defaultdict(float)
    for r in withdrawal_records:
        if r["user_id"] in qualifying and r["status"] in (0, 1, 2):
            withdraw_totals[r["user_id"]] += r["amount"]

    rows = [
        {"user_id": uid, "total_deposit": round(amt, 2), "total_withdraw": round(withdraw_totals.get(uid, 0.0), 2)}
        for uid, amt in totals.items() if uid in qualifying
    ]
    rows.sort(key=lambda x: -x["total_deposit"])
    return rows[:limit]


def aggregate(records):
    """
    records: list of dicts with keys channel, amount, hour, status,
    completion_minutes, user_id. Returns all report sections for this scope.
    """
    completed = [r for r in records if r["status"] == "COMPLETE"]

    # --- completed-only breakdowns (money/volume of successful deposits) ---
    by_channel = {}
    by_range = {label: {"count": 0, "total_amount": 0.0, "users": set()} for label in RANGE_LABELS}
    by_channel_and_range = {}
    hourly = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"count": 0, "total_amount": 0.0})))
    total_count, total_amount = 0, 0.0

    for r in completed:
        channel, amount, hour = r["channel"], r["amount"], r["hour"]
        rlabel = bucket_for_amount(amount)
        total_count += 1
        total_amount += amount

        ch = by_channel.setdefault(channel, {"count": 0, "total_amount": 0.0})
        ch["count"] += 1
        ch["total_amount"] += amount

        by_range[rlabel]["count"] += 1
        by_range[rlabel]["total_amount"] += amount
        if r["user_id"] is not None:
            by_range[rlabel]["users"].add(r["user_id"])

        cr = by_channel_and_range.setdefault((channel, rlabel), {"count": 0, "total_amount": 0.0})
        cr["count"] += 1
        cr["total_amount"] += amount

        if hour is not None:
            hcr = hourly[hour][channel][rlabel]
            hcr["count"] += 1
            hcr["total_amount"] += amount

    # --- success-rate breakdowns (all statuses vs completed) ---
    succ_range = {label: {"total": 0, "completed": 0, "min_sum": 0.0, "min_n": 0} for label in RANGE_LABELS}
    succ_channel = {}
    hourly_succ_channel = defaultdict(lambda: defaultdict(lambda: {"total": 0, "completed": 0}))
    hourly_succ_range = defaultdict(lambda: defaultdict(lambda: {"total": 0, "completed": 0}))

    for r in records:
        channel, amount, hour = r["channel"], r["amount"], r["hour"]
        rlabel = bucket_for_amount(amount)
        is_completed = r["status"] == "COMPLETE"

        sr = succ_range[rlabel]
        sr["total"] += 1
        if is_completed:
            sr["completed"] += 1
            if r["completion_minutes"] is not None:
                sr["min_sum"] += r["completion_minutes"]
                sr["min_n"] += 1

        sc = succ_channel.setdefault(channel, {
            "total": 0, "completed": 0, "completed_users": set(), "completed_amount": 0.0, "min_sum": 0.0, "min_n": 0
        })
        sc["total"] += 1
        if is_completed:
            sc["completed"] += 1
            sc["completed_amount"] += amount
            if r["user_id"] is not None:
                sc["completed_users"].add(r["user_id"])
            if r["completion_minutes"] is not None:
                sc["min_sum"] += r["completion_minutes"]
                sc["min_n"] += 1

        if hour is not None:
            hsc = hourly_succ_channel[hour][channel]
            hsc["total"] += 1
            if is_completed:
                hsc["completed"] += 1
            hsr = hourly_succ_range[hour][rlabel]
            hsr["total"] += 1
            if is_completed:
                hsr["completed"] += 1

    def pct(completed, total):
        return round(completed / total * 100, 1) if total else 0

    return {
        "totals": {"count": total_count, "total_amount": round(total_amount, 2)},
        "by_channel": [
            {
                "channel": ch,
                "count": v["count"],
                "total_amount": round(v["total_amount"], 2),
                "avg_amount": round(v["total_amount"] / v["count"], 2) if v["count"] else 0,
            }
            for ch, v in sorted(by_channel.items(), key=lambda x: -x[1]["total_amount"])
        ],
        "by_amount_range": [
            {
                "range": label,
                "count": by_range[label]["count"],
                "users": len(by_range[label]["users"]),
                "total_amount": round(by_range[label]["total_amount"], 2),
            }
            for label in RANGE_LABELS
        ],
        "by_channel_and_range": [
            {"channel": ch, "range": rl, "count": v["count"], "total_amount": round(v["total_amount"], 2)}
            for (ch, rl), v in sorted(by_channel_and_range.items(), key=lambda x: -x[1]["total_amount"])
        ],
        "hourly": [
            {
                "hour": hour,
                "channel": ch,
                "range": rl,
                "count": v["count"],
                "total_amount": round(v["total_amount"], 2),
            }
            for hour, chans in sorted(hourly.items())
            for ch, ranges in chans.items()
            for rl, v in ranges.items()
        ],
        "success_by_range": [
            {
                "range": label,
                "total": v["total"],
                "completed": v["completed"],
                "success_pct": pct(v["completed"], v["total"]),
                "avg_minutes": round(v["min_sum"] / v["min_n"], 1) if v["min_n"] else None,
            }
            for label, v in succ_range.items()
        ],
        "success_by_channel": [
            {
                "channel": ch,
                "total": v["total"],
                "comp_orders": v["completed"],
                "comp_users": len(v["completed_users"]),
                "comp_amount": round(v["completed_amount"], 2),
                "success_pct": pct(v["completed"], v["total"]),
                "avg_minutes": round(v["min_sum"] / v["min_n"], 1) if v["min_n"] else None,
            }
            for ch, v in sorted(succ_channel.items(), key=lambda x: -x[1]["completed_amount"])
        ],
        "hourly_success_by_channel": [
            {"hour": hour, "channel": ch, "total": v["total"], "completed": v["completed"], "success_pct": pct(v["completed"], v["total"])}
            for hour, chans in sorted(hourly_succ_channel.items())
            for ch, v in chans.items()
        ],
        "hourly_success_by_range": [
            {"hour": hour, "range": rl, "total": v["total"], "completed": v["completed"], "success_pct": pct(v["completed"], v["total"])}
            for hour, ranges in sorted(hourly_succ_range.items())
            for rl, v in ranges.items()
        ],
    }


# Withdrawal status codes: 0 In-Review, 1 Processing, 2 Complete, 3 Rejected, 4 Failed
ACTIVE_WITHDRAW_STATUSES = (0, 1, 2)


def summarize(deposit_records, withdrawal_records, bet_user_ids, return_users=None):
    completed_deposits = [r for r in deposit_records if r["status"] == "COMPLETE"]
    active_withdrawals = [r for r in withdrawal_records if r["status"] in ACTIVE_WITHDRAW_STATUSES]

    total_deposit = round(sum(r["amount"] for r in completed_deposits), 2)
    total_withdraw = round(sum(r["amount"] for r in active_withdrawals), 2)
    deposit_users = {r["user_id"] for r in completed_deposits if r["user_id"] is not None}
    withdraw_users = {r["user_id"] for r in active_withdrawals if r["user_id"] is not None}
    active_users = deposit_users | withdraw_users | bet_user_ids

    return {
        "total_deposit": total_deposit,
        "total_withdraw": total_withdraw,
        "deposit_orders": len(completed_deposits),
        "withdraw_orders": len(active_withdrawals),
        "deposit_users": len(deposit_users),
        "withdraw_users": len(withdraw_users),
        "active_users": len(active_users),
        # Users with a COMPLETE deposit on this date who also had one on the
        # calendar day immediately before it -- None when that previous day
        # falls outside the retained window (see compute_return_users()).
        "return_users": return_users,
        "difference": round(total_deposit - total_withdraw, 2),
        "withdraw_deposit_pct": round(total_withdraw / total_deposit * 100, 1) if total_deposit else None,
        # kept for backward compatibility with the KPI cards
        "total_users": len(deposit_users),
        "total_orders": len(completed_deposits),
        "profit": round(total_deposit - total_withdraw, 2),
    }


def compute_return_users(by_date_records_dict, all_dates):
    """For each date, the count of distinct users with a COMPLETE deposit
    that date who ALSO had a COMPLETE deposit on the calendar day
    immediately before it -- a simple day-over-day return-depositor count,
    for the Home page's "Return Users" tile. Uses the calendar date, not
    just the previous entry in all_dates, so a gap in the retained window
    correctly yields None rather than comparing against the wrong day."""
    depositors_by_date = {
        date_str: {
            r["user_id"] for r in records
            if r["status"] == "COMPLETE" and r["user_id"] is not None
        }
        for date_str, records in by_date_records_dict.items()
    }
    result = {}
    for date_str in all_dates:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        prev_str = (d - timedelta(days=1)).isoformat()
        prev_set = depositors_by_date.get(prev_str)
        if prev_set is None:
            result[date_str] = None
        else:
            result[date_str] = len(depositors_by_date.get(date_str, set()) & prev_set)
    return result


PROCESSING_TIME_BUCKETS = ["<1h", "1-3h", "3-6h", "6-12h", ">12h"]


def processing_time_bucket(hours):
    if hours < 1:
        return "<1h"
    if hours < 3:
        return "1-3h"
    if hours < 6:
        return "3-6h"
    if hours < 12:
        return "6-12h"
    return ">12h"


PROCESSING_BACKLOG_BUCKETS = ["3-6h", "6-12h", "12-24h", ">24h"]


def processing_backlog_bucket(hours):
    if hours < 3:
        return None
    if hours < 6:
        return "3-6h"
    if hours < 12:
        return "6-12h"
    if hours < 24:
        return "12-24h"
    return ">24h"


INREVIEW_BACKLOG_BUCKETS = ["1-3h", "3-6h", ">6h"]


def inreview_backlog_bucket(hours):
    if hours < 1:
        return None
    if hours < 3:
        return "1-3h"
    if hours < 6:
        return "3-6h"
    return ">6h"


def withdrawal_review_by_channel(withdrawal_full_records):
    """Channel x processing-time-bucket matrix for orders currently in Payment
    Processing (status=1), duration measured strictly from create_time to
    review_time (no update_time fallback -- these orders haven't completed yet)."""
    matrix = defaultdict(lambda: defaultdict(int))
    for r in withdrawal_full_records:
        if r["status"] != 1:
            continue
        if not r["create_dt"] or not r["review_dt"]:
            continue
        hours = max((r["review_dt"] - r["create_dt"]).total_seconds() / 3600.0, 0)
        bucket = processing_time_bucket(hours)
        matrix[r["channel"]][bucket] += 1
    return [
        {"channel": ch, "bucket": b, "count": matrix[ch][b]}
        for ch in sorted(matrix.keys())
        for b in PROCESSING_TIME_BUCKETS
    ]


def withdrawal_completion_by_channel(withdrawal_full_records):
    """Channel x processing-time-bucket matrix for Completed (status=2) withdrawals,
    duration measured from review_time to update_time (the payout step, after review)."""
    matrix = defaultdict(lambda: defaultdict(int))
    for r in withdrawal_full_records:
        if r["status"] != 2:
            continue
        if not r["review_dt"] or not r["update_dt"]:
            continue
        hours = max((r["update_dt"] - r["review_dt"]).total_seconds() / 3600.0, 0)
        bucket = processing_time_bucket(hours)
        matrix[r["channel"]][bucket] += 1
    return [
        {"channel": ch, "bucket": b, "count": matrix[ch][b]}
        for ch in sorted(matrix.keys())
        for b in PROCESSING_TIME_BUCKETS
    ]


AMOUNT_RANGE_BUCKETS = ["200-999", "1000-4999", "5000-9999", "10000-20000", "20001-50000"]


def amount_range_bucket(amount):
    if amount < 200:
        return None
    if amount < 1000:
        return "200-999"
    if amount < 5000:
        return "1000-4999"
    if amount < 10000:
        return "5000-9999"
    if amount <= 20000:
        return "10000-20000"
    if amount <= 50000:
        return "20001-50000"
    return None


def withdrawal_amount_range_aging_matrix(withdrawal_full_records, now, status, amount_bucket_fn, amount_buckets, time_bucket_fn, time_buckets):
    """Snapshot (as of `now`) of orders sitting in `status`, cross-tabulated by
    withdrawal amount range x aging bucket (same aging logic as withdrawal_backlog)."""
    matrix = defaultdict(lambda: defaultdict(int))
    amounts = defaultdict(lambda: defaultdict(float))
    for r in withdrawal_full_records:
        if r["status"] != status or not r["create_dt"]:
            continue
        hours = max((now - r["create_dt"]).total_seconds() / 3600.0, 0)
        time_bucket = time_bucket_fn(hours)
        if not time_bucket:
            continue
        amount_bucket = amount_bucket_fn(r["amount"] or 0.0)
        if not amount_bucket:
            continue
        matrix[amount_bucket][time_bucket] += 1
        amounts[amount_bucket][time_bucket] += r["amount"] or 0.0
    return [
        {"amount_range": ar, "bucket": tb, "count": matrix[ar][tb], "amount": round(amounts[ar][tb], 2)}
        for ar in amount_buckets
        for tb in time_buckets
    ]


YESTERDAY_AMOUNT_RANGES = ["<10,000", "10,000-19,999", "20,000-49,999", "50,000+"]
# 0 In-Review, 1 Processing, 2 Complete -- excludes 3 Rejected/4 Failed, per
# the report's explicit scope ("completed, processing, in-review").
WITHDRAWAL_STATUS_LABELS = {0: "in_review", 1: "processing", 2: "complete"}


def yesterday_amount_range_bucket(amount):
    if amount < 10000:
        return "<10,000"
    if amount < 20000:
        return "10,000-19,999"
    if amount < 50000:
        return "20,000-49,999"
    return "50,000+"


def withdrawal_amount_range_day_report(withdrawal_full_records, date_str):
    """Amount-range x status breakdown of withdrawal ORDERS CREATED on
    `date_str`, for the Home page report below the existing Withdrawal
    Processing -- Amount Range chart. Unlike that chart (a live snapshot of
    the CURRENT processing/in-review backlog, aged from create_time to now),
    this is a fixed one-day cohort: every withdrawal order created that day,
    however it stands now, split by In-Review/Processing/Complete and by
    amount range. Called once for "today" and once for "yesterday" so the
    frontend can toggle between them without a extra request."""
    counts = defaultdict(lambda: defaultdict(int))
    amounts = defaultdict(lambda: defaultdict(float))
    for r in withdrawal_full_records:
        if r["status"] not in WITHDRAWAL_STATUS_LABELS:
            continue
        if not r["create_dt"] or r["create_dt"].strftime("%Y-%m-%d") != date_str:
            continue
        bucket = yesterday_amount_range_bucket(r["amount"] or 0.0)
        counts[bucket][r["status"]] += 1
        amounts[bucket][r["status"]] += r["amount"] or 0.0

    rows = []
    grand_orders = defaultdict(int)
    grand_amount = defaultdict(float)
    grand_total_orders = 0
    grand_total_amount = 0.0
    for bucket in YESTERDAY_AMOUNT_RANGES:
        row = {"range": bucket}
        total_orders = 0
        total_amount = 0.0
        for status, label in WITHDRAWAL_STATUS_LABELS.items():
            c = counts[bucket][status]
            a = round(amounts[bucket][status], 2)
            row[label] = {"orders": c, "amount": a}
            total_orders += c
            total_amount += a
            grand_orders[status] += c
            grand_amount[status] += a
        row["total_orders"] = total_orders
        row["total_amount"] = round(total_amount, 2)
        rows.append(row)
        grand_total_orders += total_orders
        grand_total_amount += total_amount

    totals_row = {"range": "Total"}
    for status, label in WITHDRAWAL_STATUS_LABELS.items():
        totals_row[label] = {"orders": grand_orders[status], "amount": round(grand_amount[status], 2)}
    totals_row["total_orders"] = grand_total_orders
    totals_row["total_amount"] = round(grand_total_amount, 2)

    return {
        "date": date_str,
        "ranges": YESTERDAY_AMOUNT_RANGES,
        "rows": rows,
        "totals": totals_row,
    }


def withdrawal_backlog(withdrawal_full_records, now, status, bucket_fn, bucket_labels):
    """Snapshot (as of `now`) of orders currently sitting in `status`, aged from create_time."""
    counts = {label: 0 for label in bucket_labels}
    amounts = {label: 0.0 for label in bucket_labels}
    for r in withdrawal_full_records:
        if r["status"] != status or not r["create_dt"]:
            continue
        hours = max((now - r["create_dt"]).total_seconds() / 3600.0, 0)
        bucket = bucket_fn(hours)
        if bucket:
            counts[bucket] += 1
            amounts[bucket] += r["amount"] or 0.0
    return [{"bucket": label, "count": counts[label], "amount": round(amounts[label], 2)} for label in bucket_labels]


# Cumulative deposit ("experience") required to reach each VIP level, per the
# platform's VIP table. Level N's threshold is the deposit total needed to move
# from level N-1 to level N. Kept in sync with api_pull_ingest.py's copy, which
# uses it to (re)compute vip_level in master_userlist.db on every pull.
VIP_THRESHOLDS = {
    0: 0, 1: 100, 2: 600, 3: 5600, 4: 15600, 5: 95600, 6: 295600, 7: 795600,
    8: 1795600, 9: 3795600, 10: 8795600, 11: 16795600, 12: 28795600,
    13: 44795600, 14: 69795600, 15: 119795600,
}
ACTION_CENTER_LIST_CAP = 500
# See profit_users_of_the_day: a ranked leaderboard over the whole user
# base, not a bounded cohort, so it needs a (much larger) cap of its own
# rather than shipping in full like the other Action Center/Analytics lists.
PROFIT_USERS_CAP = 5000

AGENT_UNASSIGNED = "Un-Assigned"


def agent_for(agent_by_user, user_id):
    return agent_by_user.get(user_id) or AGENT_UNASSIGNED


def tally_by_agent(user_ids, agent_by_user):
    """{agent_name: count} for a collection of user_ids -- used for the
    Performance page's per-agent cohort/target denominators, which need the
    TRUE uncapped count, not the ACTION_CENTER_LIST_CAP-limited `rows` list
    used for on-screen display."""
    counts = defaultdict(int)
    for uid in user_ids:
        counts[agent_for(agent_by_user, uid)] += 1
    return dict(counts)


def tally_rows_by_agent(rows):
    """Same as tally_by_agent, but for a list of row dicts that already carry
    an "agent" key (cheaper than re-deriving it from user_id)."""
    counts = defaultdict(int)
    for r in rows:
        counts[r["agent"]] += 1
    return dict(counts)


def action_center_reports(mconn, now, agent_by_user):
    """Action Center reports, computed from the master userlist snapshot (not
    date-scoped -- these are lifetime/as-of-last-upload figures, not tied to the
    selected date). Two "near upgrade" lists (users whose remaining deposit gap
    to the next VIP tier is Rs 1-1000 for VIP2-4, Rs 1-50000 for VIP5-15), two
    "inactive" lists (users who haven't been active within a VIP-tier-specific
    day range), and two "active" lists (the inverse -- active within a
    VIP-tier-specific day range). Each list is capped at the top
    ACTION_CENTER_LIST_CAP rows by relevance (closest to upgrade / most or
    least inactive) so the report and its Excel download stay a reasonable
    size."""
    rows = mconn.execute(
        "SELECT user_id, vip_level, total_recharge, recharge_count, user_balance, last_active_time FROM users"
    ).fetchall()

    near_low, near_high, inactive_high, inactive_low = [], [], [], []
    active_low, active_high = [], []
    for user_id, vip_level, total_recharge, recharge_count, user_balance, last_active_time in rows:
        if vip_level is None:
            continue
        total_recharge = total_recharge or 0.0
        recharge_count = recharge_count or 0
        inactive_days = None
        last_active_dt = parse_dt(last_active_time)
        if last_active_dt:
            inactive_days = (now - last_active_dt).days

        if vip_level < 15 and (vip_level + 1) in VIP_THRESHOLDS:
            gap = VIP_THRESHOLDS[vip_level + 1] - total_recharge
            near_row = {
                "user_id": user_id,
                "agent": agent_for(agent_by_user, user_id),
                "current_vip": vip_level,
                "next_vip": vip_level + 1,
                "total_deposit": round(total_recharge, 2),
                "amount_to_next": round(gap, 2),
                "inactive_days": inactive_days,
            }
            if 2 <= vip_level <= 4 and 1 <= gap <= 1000:
                near_low.append(near_row)
            elif 5 <= vip_level <= 15 and 1 <= gap <= 50000:
                near_high.append(near_row)

        if inactive_days is not None:
            inactive_row = {
                "user_id": user_id,
                "agent": agent_for(agent_by_user, user_id),
                "vip_level": vip_level,
                "total_deposit": round(total_recharge, 2),
                "wallet_balance": round(user_balance or 0.0, 2),
                "inactive_days": inactive_days,
                "last_active_date": last_active_dt.strftime("%Y-%m-%d") if last_active_dt else None,
            }
            if 5 <= vip_level <= 15 and 16 <= inactive_days <= 180:
                inactive_high.append(inactive_row)
            if 2 <= vip_level <= 4 and 16 <= inactive_days <= 180 and recharge_count >= 3:
                inactive_low.append(inactive_row)

            active_row = {
                "user_id": user_id,
                "agent": agent_for(agent_by_user, user_id),
                "vip_level": vip_level,
                "total_deposit": round(total_recharge, 2),
                "wallet_balance": round(user_balance or 0.0, 2),
                "inactive_days": inactive_days,
            }
            if 5 <= vip_level <= 15 and inactive_days <= 15:
                active_high.append(active_row)
            if 2 <= vip_level <= 4 and inactive_days <= 15 and recharge_count >= 3:
                active_low.append(active_row)

    near_low.sort(key=lambda r: r["amount_to_next"])
    near_high.sort(key=lambda r: r["amount_to_next"])
    inactive_high.sort(key=lambda r: -r["inactive_days"])
    inactive_low.sort(key=lambda r: -r["inactive_days"])
    active_high.sort(key=lambda r: -r["inactive_days"])
    active_low.sort(key=lambda r: -r["inactive_days"])

    # Every list below ships in FULL (no cap) -- these are audit/payout-style
    # reports where the on-screen table paginates client-side and the Excel
    # export must contain every matching user, not just a "top N" sample.
    return {
        "near_upgrade_low": {
            "note": "VIP 2 to VIP 4, gap to next level Rs 1-1000",
            "total_matching": len(near_low),
            "rows": near_low,
        },
        "near_upgrade_high": {
            "note": "VIP 5 to VIP 15, gap to next level Rs 1-50000",
            "total_matching": len(near_high),
            "rows": near_high,
        },
        "inactive_high": {
            "note": "VIP 5 to VIP 15, inactive 16-180 days",
            "total_matching": len(inactive_high),
            "rows": inactive_high,
        },
        "inactive_low": {
            "note": "VIP 2 to VIP 4, 3+ deposit count, inactive 16-180 days",
            "total_matching": len(inactive_low),
            "rows": inactive_low,
        },
        "active_low": {
            "note": "VIP 2 to VIP 4, 3+ deposit count, active within last 15 days",
            "total_matching": len(active_low),
            "rows": active_low,
        },
        "active_high": {
            "note": "VIP 5 to VIP 15, active within last 15 days",
            "total_matching": len(active_high),
            "rows": active_high,
        },
    }


def deposit_reactivation_analytics(mconn, reactivation_candidates, action_center, agent_by_user):
    """Users active TODAY (deposit, withdrawal, or wallet/bet activity --
    whichever is most recent) after a qualifying inactive gap since their
    previous activity. Two VIP-tier-scoped cohorts, using the same day ranges
    as the Inactive-Low/Inactive-High action-center lists so a user "moving"
    from one report to the other is exactly consistent:
      Low  (VIP2-4):  previous gap 16-180 days
      High (VIP5-15): previous gap 16-180 days
    total_deposit on each row is specifically today's DEPOSIT amount (0 if
    the user reactivated via a withdrawal or wallet transaction with no
    matching deposit today) -- VIP/total_recharge stay deposit-only even
    though the activity/inactivity signal itself is not.

    reactivation_candidates comes from api_pull_ingest.py's
    sync_master_userlist(), NOT derived here from daily_records.db directly
    -- those tables are purged to a rolling 33-day window, which would
    silently drop every comeback after a longer gap (i.e. most of the
    16-180 day range). sync_master_userlist runs earlier in the same
    job and is the only place that still has each user's PRE-update
    last_active_time (unbounded history), so it computes the true gap there
    and hands the candidate list off via a local JSON file.

    "% reactivated" denominator is reconstructed as reactivated_today +
    still_currently_inactive (from action_center, already computed this run
    -- reactivated users are correctly excluded from it since their
    inactive_days reset to 0 once today's activity lands in master_userlist.db).
    No separate "yesterday's inactive list" snapshot needs to be stored."""
    vip_by_user = dict(mconn.execute("SELECT user_id, vip_level FROM users").fetchall())

    low_rows, high_rows = [], []
    for cand in reactivation_candidates:
        user_id = cand["user_id"]
        gap_days = cand["inactive_days"]
        vip_level = vip_by_user.get(user_id)
        if vip_level is None:
            continue
        row = {
            "user_id": user_id,
            "agent": agent_for(agent_by_user, user_id),
            "vip_level": vip_level,
            "total_deposit": cand["total_deposit"],
            "inactive_days": gap_days,
        }
        if 2 <= vip_level <= 4 and 16 <= gap_days <= 180:
            low_rows.append(row)
        elif 5 <= vip_level <= 15 and 16 <= gap_days <= 180:
            high_rows.append(row)

    low_rows.sort(key=lambda r: -r["inactive_days"])
    high_rows.sort(key=lambda r: -r["inactive_days"])

    still_inactive_low = action_center["inactive_low"]["total_matching"] if action_center else 0
    still_inactive_high = action_center["inactive_high"]["total_matching"] if action_center else 0
    baseline_low = len(low_rows) + still_inactive_low
    baseline_high = len(high_rows) + still_inactive_high

    # Per-agent version of the same baseline (reactivated today + still
    # currently inactive) -- purely informational, shown on the
    # Performance page next to the Reactivation Low/High target so admins
    # can see how many users an agent is actually responsible for, distinct
    # from the flat daily reactivation-count target. NOT part of the
    # numerator/denominator used for scoring (that stays the flat target).
    still_inactive_low_by_agent = tally_rows_by_agent(action_center["inactive_low"]["rows"]) if action_center else {}
    still_inactive_high_by_agent = tally_rows_by_agent(action_center["inactive_high"]["rows"]) if action_center else {}
    reactivated_low_by_agent = tally_rows_by_agent(low_rows)
    reactivated_high_by_agent = tally_rows_by_agent(high_rows)
    cohort_by_agent_low = {
        agent: reactivated_low_by_agent.get(agent, 0) + still_inactive_low_by_agent.get(agent, 0)
        for agent in set(reactivated_low_by_agent) | set(still_inactive_low_by_agent)
    }
    cohort_by_agent_high = {
        agent: reactivated_high_by_agent.get(agent, 0) + still_inactive_high_by_agent.get(agent, 0)
        for agent in set(reactivated_high_by_agent) | set(still_inactive_high_by_agent)
    }

    return {
        "low": {
            "note": "VIP 2 to VIP 4, reactivated today (was inactive 16-180 days)",
            "reactivated_count": len(low_rows),
            "pct_reactivated": round(len(low_rows) / baseline_low * 100, 2) if baseline_low else 0.0,
            # Per-agent count of reactivated users, from the FULL (uncapped)
            # low_rows list -- feeds the Performance page's Reactivation Low
            # criterion (target: 25/day), which needs the true count even
            # when the on-screen `rows` list is capped for display size.
            "agent_breakdown": reactivated_low_by_agent,
            "cohort_by_agent": cohort_by_agent_low,
            "rows": low_rows,
        },
        "high": {
            "note": "VIP 5 to VIP 15, reactivated today (was inactive 16-180 days)",
            "reactivated_count": len(high_rows),
            "pct_reactivated": round(len(high_rows) / baseline_high * 100, 2) if baseline_high else 0.0,
            "agent_breakdown": reactivated_high_by_agent,
            "cohort_by_agent": cohort_by_agent_high,
            "rows": high_rows,
        },
    }


def vip_upgrade_analytics(vip_upgrade_candidates, action_center, agent_by_user):
    """Users who were in the near-upgrade cohort (gap Rs 1-1000 for VIP2-4,
    Rs 1-50000 for VIP5-15) as of the START of today and have since crossed
    into the next VIP tier. vip_upgrade_candidates comes from
    api_pull_ingest.py's sync_master_userlist(), which is the only place
    with a stable day-start snapshot to compare against (the pipeline runs
    hourly, so a naive "before this run vs after this run" diff would lose
    upgrades from earlier the same day once a later run's report overwrites
    it).

    Each row also carries amount_over_minimum = today's deposit minus the
    exact gap that was needed to cross the threshold -- a bare-minimum
    crosser is ~0, a big spender well above it. Useful for telling "the
    near-upgrade push is converting people right at the line" apart from
    "these are just big depositors who would have crossed anyway".

    "% converted" denominator is reconstructed as upgraded_today +
    still_near_upgrade (from action_center's near_upgrade_low/high, already
    computed this run), same pattern as the Reactivation report."""
    low_rows = sorted(vip_upgrade_candidates.get("low", []), key=lambda r: -r["total_deposit"])
    high_rows = sorted(vip_upgrade_candidates.get("high", []), key=lambda r: -r["total_deposit"])
    for r in low_rows + high_rows:
        r["agent"] = agent_for(agent_by_user, r["user_id"])

    still_near_low = action_center["near_upgrade_low"]["total_matching"] if action_center else 0
    still_near_high = action_center["near_upgrade_high"]["total_matching"] if action_center else 0
    baseline_low = len(low_rows) + still_near_low
    baseline_high = len(high_rows) + still_near_high

    return {
        "low": {
            "note": "VIP 2 to VIP 4, upgraded today from the near-upgrade cohort",
            "upgraded_count": len(low_rows),
            "pct_upgraded": round(len(low_rows) / baseline_low * 100, 2) if baseline_low else 0.0,
            "agent_breakdown": tally_rows_by_agent(low_rows),
            "rows": low_rows,
        },
        "high": {
            "note": "VIP 5 to VIP 15, upgraded today from the near-upgrade cohort",
            "upgraded_count": len(high_rows),
            "pct_upgraded": round(len(high_rows) / baseline_high * 100, 2) if baseline_high else 0.0,
            "agent_breakdown": tally_rows_by_agent(high_rows),
            "rows": high_rows,
        },
    }


def build_deposit_day_stats(deposit_rows):
    """user_id -> {date: {"count": n, "amount": total}} for COMPLETE deposits.

    NOTE: deposits are only retained for a rolling 33-day window, so a user's
    true first-ever deposit could already be purged if it happened earlier --
    in that case a later deposit here would be mis-identified as their "first
    deposit" (FD). Fine for the last-4-day FD lookback these reports use, but
    worth knowing if this function is ever reused for a longer window."""
    stats = defaultdict(lambda: defaultdict(lambda: {"count": 0, "amount": 0.0}))
    for pay_channel, order_amount, create_time, update_time, status, user_id, is_first_deposit in deposit_rows:
        if status != "COMPLETE" or user_id is None:
            continue
        dt = parse_dt(create_time)
        if not dt:
            continue
        entry = stats[user_id][dt.date()]
        entry["count"] += 1
        entry["amount"] += order_amount or 0.0
    return stats


def yesterday_first_deposit_users(deposit_rows, all_withdrawal_full, vip_by_user, city_by_user, today, agent_by_user):
    """Users flagged by the source system's own is_first_deposit column
    (column S in the water/export sheet: 0 = not first deposit, 1 = first
    deposit) as making their first-ever deposit yesterday. This is the
    authoritative flag from the platform itself, not an inference from
    deposit history -- unlike a MIN(create_time) heuristic, it isn't affected
    by the deposits table's 33-day retention window."""
    yesterday = today - timedelta(days=1)
    withdraw_by_user = defaultdict(float)
    for r in all_withdrawal_full:
        if r["status"] in ACTIVE_WITHDRAW_STATUSES and r["user_id"] is not None:
            withdraw_by_user[r["user_id"]] += r["amount"] or 0.0

    day_stats = defaultdict(lambda: {"count": 0, "amount": 0.0})
    first_deposit_users = set()
    for pay_channel, order_amount, create_time, update_time, status, user_id, is_first_deposit in deposit_rows:
        if status != "COMPLETE" or user_id is None:
            continue
        dt = parse_dt(create_time)
        if not dt or dt.date() != yesterday:
            continue
        entry = day_stats[user_id]
        entry["count"] += 1
        entry["amount"] += order_amount or 0.0
        if is_first_deposit == 1:
            first_deposit_users.add(user_id)

    rows = []
    for user_id in first_deposit_users:
        entry = day_stats[user_id]
        total_deposit = round(entry["amount"], 2)
        total_withdraw = round(withdraw_by_user.get(user_id, 0.0), 2)
        rows.append({
            "user_id": user_id,
            "agent": agent_for(agent_by_user, user_id),
            "vip_level": vip_by_user.get(user_id),
            "deposit_count": entry["count"],
            "total_deposit": total_deposit,
            "total_withdraw": total_withdraw,
            "profit_loss": round(total_deposit - total_withdraw, 2),
            "region": city_by_user.get(user_id),
        })
    rows.sort(key=lambda r: -r["total_deposit"])
    return rows


def no_return_fd_users(deposit_rows, all_withdrawal_full, agent_by_user, today):
    """Users whose first-ever deposit (source system's is_first_deposit flag)
    landed 2-5 days ago -- e.g. today=12th July -> FD on 10th/9th/8th/7th --
    and who have made NO COMPLETE deposit on any day AFTER that FD date
    since. The 2-day buffer before the window starts (skipping today and
    yesterday) gives every included user at least one full day where a
    return deposit COULD have happened, so this reads as "genuinely
    one-and-done," not just "hasn't come back yet" noise from someone whose
    FD was only yesterday."""
    window_start = today - timedelta(days=5)
    window_end = today - timedelta(days=2)

    fd_date_by_user = {}
    deposit_dates_by_user = defaultdict(set)
    deposit_amount_by_user_date = defaultdict(float)
    for pay_channel, order_amount, create_time, update_time, status, user_id, is_first_deposit in deposit_rows:
        if status != "COMPLETE" or user_id is None:
            continue
        dt = parse_dt(create_time)
        if not dt:
            continue
        d = dt.date()
        deposit_dates_by_user[user_id].add(d)
        deposit_amount_by_user_date[(user_id, d)] += order_amount or 0.0
        if is_first_deposit == 1 and window_start <= d <= window_end:
            fd_date_by_user[user_id] = d

    withdraw_by_user = defaultdict(float)
    for r in all_withdrawal_full:
        if r["status"] in ACTIVE_WITHDRAW_STATUSES and r["user_id"] is not None:
            withdraw_by_user[r["user_id"]] += r["amount"] or 0.0

    rows = []
    for user_id, fd_date in fd_date_by_user.items():
        returned = any(d > fd_date for d in deposit_dates_by_user.get(user_id, ()))
        if returned:
            continue
        rows.append({
            "user_id": user_id,
            "agent": agent_for(agent_by_user, user_id),
            "fd_date": fd_date.isoformat(),
            "total_deposit": round(deposit_amount_by_user_date.get((user_id, fd_date), 0.0), 2),
            "total_withdraw": round(withdraw_by_user.get(user_id, 0.0), 2),
        })
    rows.sort(key=lambda r: r["fd_date"])
    return rows


DEPOSIT_CHALLENGE_RULES = {
    1: ("Rule 1 (+Rs10) - FD+1 Auto Bonus", 10),
    2: ("Rule 2 (+Rs20) - Deposited on FD+1", 20),
    3: ("Rule 3 (+Rs30) - Deposited on FD+2", 30),
    4: ("Rule 4 (+Rs60) - Deposited on FD+1 & FD+2", 60),
}


def deposit_challenge_bonus(deposit_rows, deposit_day_stats, today, agent_by_user):
    """Bonuses payable TODAY only -- a daily payout worksheet, not a rolling
    history of everything earned in the last few days. Each rule has a fixed
    FD offset that determines which FD cohort is relevant for today's payout:
      Rule 1 (+Rs10, auto):                  FD = today - 1
      Rule 2 (+Rs20, if deposited on FD+1):  FD = today - 2
      Rule 3 (+Rs30, if deposited on FD+2):  FD = today - 3
      Rule 4 (+Rs60, if deposited FD+1&+2):  FD = today - 3
    FD is taken from the source system's own is_first_deposit column (column S
    in the water/export sheet: 1 = first deposit), not inferred from
    MIN(create_time) -- the flag is authoritative and isn't affected by the
    deposits table's 33-day retention window."""
    fd_by_user = {}
    for pay_channel, order_amount, create_time, update_time, status, user_id, is_first_deposit in deposit_rows:
        if status != "COMPLETE" or user_id is None or is_first_deposit != 1:
            continue
        dt = parse_dt(create_time)
        if not dt:
            continue
        fd_by_user[user_id] = dt.date()

    rows = []
    for user_id, fd in fd_by_user.items():
        day_map = deposit_day_stats.get(user_id, {})
        deposited_fd1 = (fd + timedelta(days=1)) in day_map
        deposited_fd2 = (fd + timedelta(days=2)) in day_map

        def add(rule_no):
            label, amount = DEPOSIT_CHALLENGE_RULES[rule_no]
            rows.append({
                "user_id": user_id, "agent": agent_for(agent_by_user, user_id), "rule": label,
                "bonus_amount": amount, "fd_date": fd.isoformat(),
            })

        if fd == today - timedelta(days=1):
            add(1)
        if fd == today - timedelta(days=2) and deposited_fd1:
            add(2)
        if fd == today - timedelta(days=3):
            if deposited_fd2:
                add(3)
            if deposited_fd1 and deposited_fd2:
                add(4)

    # Highest bonus first -- surfaces the more meaningful Rule 2/3/4 winners
    # (users who actually kept depositing) ahead of the many Rule 1 auto-awards.
    rows.sort(key=lambda r: (-r["bonus_amount"], r["user_id"]))
    return rows


def _today_deposit_activity(deposit_rows, today):
    """user_id -> {"count", "amount"} for COMPLETE deposits dated TODAY.
    Shared by both retention reports below."""
    activity = defaultdict(lambda: {"count": 0, "amount": 0.0})
    for pay_channel, order_amount, create_time, update_time, status, user_id, is_first_deposit in deposit_rows:
        if status != "COMPLETE" or user_id is None:
            continue
        dt = parse_dt(create_time)
        if not dt or dt.date() != today:
            continue
        entry = activity[user_id]
        entry["count"] += 1
        entry["amount"] += order_amount or 0.0
    return activity


def _retention_report(cohort, today_activity, city_by_user, note, agent_by_user):
    """Shared shape for both retention reports: cohort_size, converted_count,
    pct_converted, avg_deposit_amount (of converters -- a headcount-only
    conversion rate treats a Rs200 top-up and a Rs20,000 deposit as
    identical; this flags whether the retained users are actually
    meaningful deposits or just token amounts to stay counted), and the
    per-user row list."""
    rows = []
    for user_id in cohort:
        activity = today_activity.get(user_id)
        if not activity:
            continue
        rows.append({
            "user_id": user_id,
            "agent": agent_for(agent_by_user, user_id),
            "total_deposit": round(activity["amount"], 2),
            "deposit_count": activity["count"],
            "region": city_by_user.get(user_id) or "Unknown",
        })
    rows.sort(key=lambda r: -r["total_deposit"])
    cohort_size = len(cohort)
    converted = len(rows)
    avg_deposit = round(sum(r["total_deposit"] for r in rows) / converted, 2) if converted else 0.0
    return {
        "note": note,
        "cohort_size": cohort_size,
        "converted_count": converted,
        "pct_converted": round(converted / cohort_size * 100, 2) if cohort_size else 0.0,
        "avg_deposit_amount": avg_deposit,
        # Per-agent cohort/converted counts (full, uncapped) -- feeds the
        # Performance page's Retention criterion (target: 30%), computed
        # from First-Deposit retention specifically (see first_deposit_retention).
        "cohort_by_agent": tally_by_agent(cohort, agent_by_user),
        "converted_by_agent": tally_rows_by_agent(rows),
        "rows": rows,
    }


def first_deposit_retention(deposit_rows, city_by_user, today, agent_by_user):
    """Of users whose first-ever deposit (the source system's own
    is_first_deposit flag) was YESTERDAY, how many made another COMPLETE
    deposit TODAY -- a basic Day-1 retention signal. Computed directly from
    deposit_rows (not a day-start snapshot, unlike Reactivation/VIP Upgrade)
    since "yesterday" and "today" are both fully derivable from timestamps
    already sitting in every row, so it's naturally correct regardless of
    which hourly run computes it."""
    yesterday = today - timedelta(days=1)
    fd_yesterday = set()
    for pay_channel, order_amount, create_time, update_time, status, user_id, is_first_deposit in deposit_rows:
        if status != "COMPLETE" or user_id is None or is_first_deposit != 1:
            continue
        dt = parse_dt(create_time)
        if dt and dt.date() == yesterday:
            fd_yesterday.add(user_id)
    return _retention_report(
        fd_yesterday, _today_deposit_activity(deposit_rows, today), city_by_user,
        "Yesterday's first-deposit users who deposited again today", agent_by_user,
    )


def no_return_fd_conversion(deposit_rows, city_by_user, agent_by_user, today):
    """Of users whose first-ever deposit landed 2-5 days ago and had NOT
    made another COMPLETE deposit as of yesterday (the "No-Return First
    Deposit Users" cohort -- see no_return_fd_users), how many made a
    COMPLETE deposit TODAY. Cohort membership is evaluated using only
    deposits strictly BEFORE today (not the live no_return_fd_users list,
    which would already exclude anyone who deposited today) -- otherwise
    today's converters would disqualify themselves from their own cohort."""
    window_start = today - timedelta(days=5)
    window_end = today - timedelta(days=2)

    fd_date_by_user = {}
    deposit_dates_before_today = defaultdict(set)
    for pay_channel, order_amount, create_time, update_time, status, user_id, is_first_deposit in deposit_rows:
        if status != "COMPLETE" or user_id is None:
            continue
        dt = parse_dt(create_time)
        if not dt:
            continue
        d = dt.date()
        if d < today:
            deposit_dates_before_today[user_id].add(d)
        if is_first_deposit == 1 and window_start <= d <= window_end:
            fd_date_by_user[user_id] = d

    cohort = {
        user_id for user_id, fd_date in fd_date_by_user.items()
        if not any(d > fd_date for d in deposit_dates_before_today.get(user_id, ()))
    }
    return _retention_report(
        cohort, _today_deposit_activity(deposit_rows, today), city_by_user,
        "No-Return First Deposit Users (FD 2-5 days ago, no deposit since) who deposited again today", agent_by_user,
    )


def premium_active_conversion(mconn, deposit_rows, now, agent_by_user):
    """Of users already on the Active Users list in Action Center (VIP2-4
    active within 15 days with 3+ lifetime deposits = "low", VIP5-15 active
    within 15 days = "high"), how many ALSO made a COMPLETE deposit
    specifically TODAY -- a continued-engagement signal, distinct from
    Reactivation (which tracks INACTIVE users coming back) and from Active
    Users itself (which only shows who's active, not who's converting
    today).

    Recomputes the full active_low/active_high user_id membership directly
    (duplicating action_center_reports' classification, not reusing its
    output) rather than adding a dependency between the two reports --
    keeps this self-contained even though action_center_reports' own rows
    are no longer capped either."""
    rows = mconn.execute("SELECT user_id, vip_level, recharge_count, last_active_time FROM users").fetchall()
    active_low_ids, active_high_ids = set(), set()
    vip_by_user = {}
    for user_id, vip_level, recharge_count, last_active_time in rows:
        if vip_level is None:
            continue
        vip_by_user[user_id] = vip_level
        last_active_dt = parse_dt(last_active_time)
        if not last_active_dt:
            continue
        inactive_days = (now - last_active_dt).days
        if 2 <= vip_level <= 4 and inactive_days <= 15 and (recharge_count or 0) >= 3:
            active_low_ids.add(user_id)
        if 5 <= vip_level <= 15 and inactive_days <= 15:
            active_high_ids.add(user_id)

    today_activity = _today_deposit_activity(deposit_rows, now.date())

    def build(cohort, tier_label):
        rows_out = []
        for user_id in cohort:
            activity = today_activity.get(user_id)
            if not activity:
                continue
            rows_out.append({
                "user_id": user_id,
                "agent": agent_for(agent_by_user, user_id),
                "vip": vip_by_user.get(user_id),
                "deposit_amount": round(activity["amount"], 2),
                "deposit_count": activity["count"],
            })
        rows_out.sort(key=lambda r: -r["deposit_amount"])
        cohort_size = len(cohort)
        converted = len(rows_out)
        avg_deposit = round(sum(r["deposit_amount"] for r in rows_out) / converted, 2) if converted else 0.0
        return {
            "note": f"{tier_label} Active Users who deposited today",
            "cohort_size": cohort_size,
            "converted_count": converted,
            "pct_converted": round(converted / cohort_size * 100, 2) if cohort_size else 0.0,
            "avg_deposit_amount": avg_deposit,
            # Per-agent cohort/converted counts (full, uncapped) -- feeds the
            # Performance page's Low/High Premium Active criteria (targets:
            # 35%/30% of the agent's own active-user cohort).
            "cohort_by_agent": tally_by_agent(cohort, agent_by_user),
            "converted_by_agent": tally_rows_by_agent(rows_out),
            "rows": rows_out,
        }

    return {"low": build(active_low_ids, "Low"), "high": build(active_high_ids, "High")}


STATUS_LABELS = {0: "In-Review", 1: "Processing", 2: "Complete", 3: "Rejected", 4: "Failed"}


def withdrawal_waiting_hours(r):
    end_dt = r["review_dt"] or r["update_dt"]
    if not r["create_dt"] or not end_dt:
        return None
    return round(max((end_dt - r["create_dt"]).total_seconds() / 3600.0, 0), 2)


def withdrawal_orders_export(withdrawal_full_records, vip_by_user, now, agent_by_user):
    """Raw order-level rows for the withdrawal Excel export: order number
    (both order_no and payment_center_order_no -- the latter is the
    "TW..."-prefixed field, the closest match found to a requested
    "TP"-prefixed order number; order_no itself is "DIZC..."-prefixed and
    channel_order_id is inconsistent, neither matches), channel, amount,
    status, date, waiting time, user id and VIP level. For orders still open
    (status 0 In-Review / 1 Processing), also computes hours_in_review /
    hours_processing as (now - create_time) -- how long the order has actually
    been sitting in that state as of report generation. waiting_hours (which
    uses review_time/update_time) is near-zero for these still-open orders
    since they haven't been reviewed/updated yet, so it can't answer "how long
    has this been pending" -- these two fields exist specifically for that."""
    rows = []
    for r in withdrawal_full_records:
        hours_in_review = hours_processing = None
        if r["status"] in (0, 1) and r["create_dt"]:
            pending_hours = round(max((now - r["create_dt"]).total_seconds() / 3600.0, 0), 2)
            if r["status"] == 0:
                hours_in_review = pending_hours
            else:
                hours_processing = pending_hours
        rows.append({
            "order_no": r["order_no"],
            "payment_center_order_no": r.get("payment_center_order_id"),
            "channel": r["channel"],
            "amount": r["amount"],
            "status": STATUS_LABELS.get(r["status"], r["status"]),
            "date": r["create_dt"].strftime("%Y-%m-%d") if r["create_dt"] else None,
            "waiting_hours": withdrawal_waiting_hours(r),
            "hours_in_review": hours_in_review,
            "hours_processing": hours_processing,
            "user_id": r["user_id"],
            "agent": agent_for(agent_by_user, r["user_id"]),
            "vip_level": vip_by_user.get(r["user_id"]),
        })
    return rows


def last4days_completion(by_date_withdrawal_full, dates):
    """For the last 4 dates: count of completed (status=2) withdrawals whose
    PROCESSING duration -- review_time (when the order left In-Review and
    entered Processing) to update_time (when it finished and became
    Complete) -- was within 4h vs more than 4h. Same review_dt/update_dt
    pair as withdrawal_completion_by_channel, not create_time -- create_time
    also includes however long the order sat in In-Review before Processing
    even started, which isn't part of the processing step being measured
    here."""
    last4 = dates[-4:]
    result = []
    for date in last4:
        within, over = 0, 0
        for r in by_date_withdrawal_full.get(date, []):
            if r["status"] != 2:
                continue
            if not r["review_dt"] or not r["update_dt"]:
                continue
            hours = max((r["update_dt"] - r["review_dt"]).total_seconds() / 3600.0, 0)
            if hours <= 4:
                within += 1
            else:
                over += 1
        result.append({"date": date, "within_4h": within, "more_than_4h": over})
    return result


def region_vip_deposit_analytics(by_date_records, by_date_withdrawals, city_by_user, vip_by_user, dates):
    """For each of the last 7 dates: top 10 regions by total COMPLETE deposit
    amount (with order count, unique user count, total withdrawal, and net
    revenue = deposit - withdrawal), and the same breakdown per VIP level.
    Powers the Analytics page's region/VIP charts with a 7-day date switch.

    Net revenue matters here because gross deposit volume alone can be
    misleading -- a region can look like a top performer by deposit total
    while actually being net-negative for the house once withdrawals are
    subtracted. Regions/tiers are still ranked by deposit (that's still the
    natural "where's the volume" question), but every row also carries
    total_withdrawal/net_revenue so that's never hidden."""
    last7 = dates[-7:]
    result = {}
    for date in last7:
        region_totals = defaultdict(float)
        region_counts = defaultdict(int)
        region_users = defaultdict(set)
        region_withdrawals = defaultdict(float)
        vip_totals = defaultdict(float)
        vip_counts = defaultdict(int)
        vip_users = defaultdict(set)
        vip_withdrawals = defaultdict(float)
        for r in by_date_records.get(date, []):
            if r["status"] != "COMPLETE" or r["user_id"] is None:
                continue
            region = city_by_user.get(r["user_id"]) or "Unknown"
            region_totals[region] += r["amount"]
            region_counts[region] += 1
            region_users[region].add(r["user_id"])
            vip = vip_by_user.get(r["user_id"])
            if vip is not None:
                vip_totals[vip] += r["amount"]
                vip_counts[vip] += 1
                vip_users[vip].add(r["user_id"])
        for r in by_date_withdrawals.get(date, []):
            if r["status"] != 2 or r["user_id"] is None:  # 2 = Complete
                continue
            region = city_by_user.get(r["user_id"]) or "Unknown"
            region_withdrawals[region] += r["amount"]
            vip = vip_by_user.get(r["user_id"])
            if vip is not None:
                vip_withdrawals[vip] += r["amount"]
        top_regions = sorted(region_totals.items(), key=lambda x: -x[1])[:10]
        vip_rows = [
            {
                "vip_level": vip,
                "total_deposit": round(vip_totals[vip], 2),
                "count": vip_counts[vip],
                "user_count": len(vip_users[vip]),
                "total_withdrawal": round(vip_withdrawals.get(vip, 0.0), 2),
                "net_revenue": round(vip_totals[vip] - vip_withdrawals.get(vip, 0.0), 2),
            }
            for vip in sorted(vip_totals.keys())
        ]
        result[date] = {
            "top_regions": [
                {
                    "region": region,
                    "total_deposit": round(total, 2),
                    "count": region_counts[region],
                    "user_count": len(region_users[region]),
                    "total_withdrawal": round(region_withdrawals.get(region, 0.0), 2),
                    "net_revenue": round(total - region_withdrawals.get(region, 0.0), 2),
                }
                for region, total in top_regions
            ],
            "vip_breakdown": vip_rows,
        }
    return result


def performance_history(mconn):
    """Permanent daily/weekly/monthly Total Deposit / Total Withdrawal / Net
    Revenue trends. Reads from master_userlist.db's daily_performance table
    (populated once per day by api_pull_ingest.py's sync_master_userlist),
    which is NEVER purged -- unlike daily_records.db's rolling 33-day
    window, this is unlimited history: every day's totals survive forever
    once written, even after that day's row-level detail eventually ages
    out and gets purged. Weekly/monthly are derived here on read via simple
    date-bucketing since daily_performance itself stays small (one row per
    calendar date, not per transaction)."""
    try:
        daily_rows = mconn.execute(
            "SELECT date, total_deposit, deposit_count, unique_depositors, "
            "total_withdrawal, withdrawal_count, unique_withdrawers, net_revenue "
            "FROM daily_performance ORDER BY date"
        ).fetchall()
    except sqlite3.OperationalError:
        return {"daily": [], "weekly": [], "monthly": []}  # pre-dates this feature

    daily = [
        {
            "date": d, "total_deposit": td, "deposit_count": dc, "unique_depositors": ud,
            "total_withdrawal": tw, "withdrawal_count": wc, "unique_withdrawers": uw, "net_revenue": nr,
        }
        for d, td, dc, ud, tw, wc, uw, nr in daily_rows
    ]

    def rollup(rows, key_fn):
        buckets = {}
        for r in rows:
            key = key_fn(r["date"])
            b = buckets.setdefault(key, {
                "period": key, "start_date": r["date"], "end_date": r["date"],
                "total_deposit": 0.0, "total_withdrawal": 0.0, "net_revenue": 0.0,
                "deposit_count": 0, "withdrawal_count": 0,
            })
            b["total_deposit"] += r["total_deposit"]
            b["total_withdrawal"] += r["total_withdrawal"]
            b["net_revenue"] += r["net_revenue"]
            b["deposit_count"] += r["deposit_count"]
            b["withdrawal_count"] += r["withdrawal_count"]
            b["start_date"] = min(b["start_date"], r["date"])
            b["end_date"] = max(b["end_date"], r["date"])
        result = sorted(buckets.values(), key=lambda b: b["start_date"])
        for b in result:
            b["total_deposit"] = round(b["total_deposit"], 2)
            b["total_withdrawal"] = round(b["total_withdrawal"], 2)
            b["net_revenue"] = round(b["net_revenue"], 2)
        return result

    def week_key(date_str):
        y, w, _ = datetime.strptime(date_str, "%Y-%m-%d").isocalendar()
        return f"{y}-W{w:02d}"

    def month_key(date_str):
        return date_str[:7]

    return {
        "daily": daily,
        "weekly": rollup(daily, week_key),
        "monthly": rollup(daily, month_key),
    }


def profit_users_of_the_day(mconn, deposit_rows, withdrawal_rows, now, agent_by_user):
    """Top users by CURRENT wallet balance (user_balance on
    master_userlist.db, continuously updated by wallet activity) -- "who is
    sitting on the most money right now", enriched with today's deposit/
    withdrawal activity and permanent last-deposit/last-withdrawal dates.

    Last deposit/withdraw use deposit_sync_time/withdrawal_sync_time (see
    sync_master_userlist in api_pull_ingest.py) rather than deriving from
    daily_records.db's deposit_rows/withdrawal_rows directly -- those are
    purged to a rolling 33-day window, so a user who hasn't deposited in
    longer than that would wrongly show "no deposit" instead of their true
    last date. deposit_sync_time/withdrawal_sync_time are permanent,
    continuously advanced every run, and immune to that purge."""
    today = now.date()
    today_deposit = defaultdict(float)
    for pay_channel, order_amount, create_time, update_time, status, user_id, is_first_deposit in deposit_rows:
        if status != "COMPLETE" or user_id is None:
            continue
        dt = parse_dt(create_time)
        if dt and dt.date() == today:
            today_deposit[user_id] += order_amount or 0.0

    today_withdraw = defaultdict(float)
    for withdraw_amount, create_time, status, user_id, payment_channel, review_time, update_time, order_no, payment_center_order_id in withdrawal_rows:
        if status not in (0, 1, 2) or user_id is None:  # 0 In-Review, 1 Processing, 2 Complete -- excludes 3 Rejected, 4 Failed
            continue
        dt = parse_dt(create_time)
        if dt and dt.date() == today:
            today_withdraw[user_id] += withdraw_amount or 0.0

    # "New user" here = whose FIRST-EVER deposit (is_first_deposit=1) landed
    # today or either of the previous 2 days, for the "3 Days New User" filter
    # button -- same is_first_deposit concept as new_vs_old_user_analysis.
    new_user_within_3d = set()
    for pay_channel, order_amount, create_time, update_time, status, user_id, is_first_deposit in deposit_rows:
        if status != "COMPLETE" or user_id is None or is_first_deposit != 1:
            continue
        dt = parse_dt(create_time)
        if dt and 0 <= (today - dt.date()).days <= 2:
            new_user_within_3d.add(user_id)

    def days_ago_label(sync_time):
        dt = parse_dt(sync_time)
        if not dt:
            return None
        gap = (today - dt.date()).days
        return "Today" if gap <= 0 else f"{gap}d ago"

    # Unlike the Action Center/Analytics audit lists (bounded cohorts, now
    # shipped in full -- see ACTION_CENTER_LIST_CAP usage elsewhere), this is
    # a ranked "top by balance" leaderboard over the ENTIRE 334K+ user base,
    # not a fixed-size cohort -- uncapping it entirely could mean tens of
    # thousands of near-zero-balance rows nobody asked for. Kept at a much
    # larger but still bounded cap so both the on-screen view and the Excel
    # export cover every user who plausibly matters here.
    rows = mconn.execute(
        "SELECT user_id, vip_level, user_balance, deposit_sync_time, withdrawal_sync_time FROM users "
        "WHERE user_balance IS NOT NULL AND user_balance > 0 "
        "ORDER BY user_balance DESC LIMIT ?",
        (PROFIT_USERS_CAP,),
    ).fetchall()

    result = []
    for user_id, vip_level, user_balance, dep_sync, wd_sync in rows:
        dep_today = round(today_deposit.get(user_id, 0.0), 2)
        wd_today = round(today_withdraw.get(user_id, 0.0), 2)
        result.append({
            "user_id": user_id,
            "agent": agent_for(agent_by_user, user_id),
            "vip": vip_level,
            "dep_today": dep_today,
            "wallet_bal": round(user_balance or 0.0, 2),
            "wd_today": wd_today,
            "net_dep": round(dep_today - wd_today, 2),
            "last_dep": days_ago_label(dep_sync),
            "last_wd": days_ago_label(wd_sync),
            "is_new_user_3d": user_id in new_user_within_3d,
        })
    return result


SUSPICIOUS_WITHDRAW_MAX_GAMES = 50
SUSPICIOUS_WITHDRAW_MIN_DEPOSIT = 1000.0


def suspicious_withdraw_users(deposit_rows, withdrawal_rows, game_play_rows, now, agent_by_user, vip_by_user):
    """Fraud/bonus-abuse signal: any users (new or existing) who, within
    the last 3 days (today and the previous 2), made COMPLETE deposits
    totaling at least SUSPICIOUS_WITHDRAW_MIN_DEPOSIT AND requested a
    withdrawal (In-Review/Processing/Complete -- same statuses "WD Today"
    counts elsewhere), while playing fewer than SUSPICIOUS_WITHDRAW_MAX_GAMES
    actual games in that same window -- i.e. deposited a meaningful amount
    and cashed out without genuinely playing. game_play_rows excludes bonus
    payouts (same definition as the "games played" query in
    build_recent_activity_by_user: wallet_transactions rows with a real
    game_name, id NOT IN bonuses)."""
    window_start = now.date() - timedelta(days=2)

    deposit_amount = defaultdict(float)
    for pay_channel, order_amount, create_time, update_time, status, user_id, is_first_deposit in deposit_rows:
        if status != "COMPLETE" or user_id is None:
            continue
        dt = parse_dt(create_time)
        if not dt or dt.date() < window_start:
            continue
        deposit_amount[user_id] += order_amount or 0.0
    deposited_users = {u for u, amt in deposit_amount.items() if amt >= SUSPICIOUS_WITHDRAW_MIN_DEPOSIT}

    withdraw_amount_by_user = defaultdict(float)
    in_review_by_user = defaultdict(bool)
    for withdraw_amount, create_time, status, user_id, payment_channel, review_time, update_time, order_no, payment_center_order_id in withdrawal_rows:
        if status not in (0, 1, 2) or user_id is None:  # 0 In-Review, 1 Processing, 2 Complete
            continue
        dt = parse_dt(create_time)
        if dt and dt.date() >= window_start:
            withdraw_amount_by_user[user_id] += withdraw_amount or 0.0
            if status == 0:
                in_review_by_user[user_id] = True
    withdrew_users = set(withdraw_amount_by_user.keys())

    game_count = defaultdict(int)
    for user_id, create_time in game_play_rows:
        if user_id is None:
            continue
        dt = parse_dt(create_time)
        if dt and dt.date() >= window_start:
            game_count[user_id] += 1

    result = []
    for user_id in deposited_users & withdrew_users:
        count = game_count.get(user_id, 0)
        if count < SUSPICIOUS_WITHDRAW_MAX_GAMES:
            result.append({
                "user_id": user_id,
                "agent": agent_for(agent_by_user, user_id),
                "vip": vip_by_user.get(user_id),
                "deposit_amount": round(deposit_amount[user_id], 2),
                "withdraw_amount": round(withdraw_amount_by_user[user_id], 2),
                "game_count": count,
                "in_review": in_review_by_user.get(user_id, False),
            })
    result.sort(key=lambda r: r["game_count"])
    return result


def new_vs_old_user_analysis(deposit_rows, withdrawal_rows, all_dates, today):
    """Per-day new-vs-old depositor breakdown for Platform Analysis, below
    Bonus Claim Report. "New" = a user whose FIRST-EVER deposit
    (is_first_deposit=1) landed on that day; "old" = any other COMPLETE
    depositor that day (excluded from the new-user set even if they also
    happen to appear there). Also breaks out withdrawal behavior for each
    cohort (status 2 = Complete only) and 3-day return-deposit retention for
    new users, split by whether they withdrew (any status) in that window.

    `all_dates` already spans exactly what daily_records.db retains -- a
    rolling RETENTION_DAYS(=33)-day window (see ingest_update.py) -- so this
    naturally starts wherever data first became available rather than
    always covering a full 33 days, and needs no separate date-range input.
    """
    dep_by_date = defaultdict(list)
    for pay_channel, order_amount, create_time, update_time, status, user_id, is_first_deposit in deposit_rows:
        if status != "COMPLETE" or user_id is None:
            continue
        dt = parse_dt(create_time)
        if not dt:
            continue
        dep_by_date[dt.date().isoformat()].append((user_id, order_amount or 0.0, is_first_deposit == 1))

    wd_by_date = defaultdict(list)
    for withdraw_amount, create_time, status, user_id, *_rest in withdrawal_rows:
        if user_id is None:
            continue
        dt = parse_dt(create_time)
        if not dt:
            continue
        wd_by_date[dt.date().isoformat()].append((user_id, withdraw_amount or 0.0, status))

    daily_rows = []
    for date_str in all_dates:
        rows = dep_by_date.get(date_str, [])
        new_ids = {uid for uid, amt, is_first in rows if is_first}
        old_ids = {uid for uid, amt, is_first in rows if not is_first} - new_ids
        new_dep_total = sum(amt for uid, amt, is_first in rows if uid in new_ids)
        old_dep_total = sum(amt for uid, amt, is_first in rows if uid in old_ids)

        wd_rows = wd_by_date.get(date_str, [])
        wd_complete = [(uid, amt) for uid, amt, status in wd_rows if status == 2]  # 2 = Complete
        old_withdrawers = {uid for uid, amt in wd_complete if uid in old_ids}
        new_withdrawers = {uid for uid, amt in wd_complete if uid in new_ids}
        old_wd_total = sum(amt for uid, amt in wd_complete if uid in old_withdrawers)
        new_wd_total = sum(amt for uid, amt in wd_complete if uid in new_withdrawers)

        daily_rows.append({
            "date": date_str,
            "old_users_count": len(old_ids),
            "old_users_deposit_total": round(old_dep_total, 2),
            "old_users_avg_deposit": round(old_dep_total / len(old_ids), 2) if old_ids else 0,
            "new_users_count": len(new_ids),
            "new_users_deposit_total": round(new_dep_total, 2),
            "new_users_avg_deposit": round(new_dep_total / len(new_ids), 2) if new_ids else 0,
            "old_users_withdraw_count": len(old_withdrawers),
            "old_users_withdraw_total": round(old_wd_total, 2),
            "old_users_avg_withdraw": round(old_wd_total / len(old_withdrawers), 2) if old_withdrawers else 0,
            "new_users_withdraw_count": len(new_withdrawers),
            "new_users_withdraw_total": round(new_wd_total, 2),
            "new_users_avg_withdraw": round(new_wd_total / len(new_withdrawers), 2) if new_withdrawers else 0,
            "total_deposit": round(new_dep_total + old_dep_total, 2),
            "total_depositor_count": len(new_ids) + len(old_ids),
        })

    # 3-day retention needs D, D+1, D+2, D+3 all in the past -- skip dates
    # where that window hasn't fully elapsed yet (would otherwise undercount
    # "returned" purely because the days haven't happened).
    retention_rows = []
    for date_str in all_dates:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        window_dates = [(d + timedelta(days=k)).isoformat() for k in range(4)]
        if window_dates[-1] > today.isoformat():
            continue
        new_ids = {uid for uid, amt, is_first in dep_by_date.get(date_str, []) if is_first}
        if not new_ids:
            continue
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
            "date": date_str,
            "new_users": len(new_ids),
            "withdrew_group_count": len(withdrew_group),
            "withdrew_group_returned": len(withdrew_group & returned_ids),
            "withdrew_group_retention_pct": round(100 * len(withdrew_group & returned_ids) / len(withdrew_group), 2) if withdrew_group else None,
            "never_withdrew_group_count": len(never_withdrew_group),
            "never_withdrew_group_returned": len(never_withdrew_group & returned_ids),
            "never_withdrew_group_retention_pct": round(100 * len(never_withdrew_group & returned_ids) / len(never_withdrew_group), 2) if never_withdrew_group else None,
        })

    return {"daily": daily_rows, "retention": retention_rows}


# Weekly Performance section (Platform Analysis, above Region vs VIP
# Depositor Matrix): Target vs Actual only renders while the CURRENT
# calendar week (Monday start) matches WEEKLY_TARGET_WEEK_START below --
# these target figures are a manual business decision (see "Weekly Data
# Comparison & Target" workbook's Target sheet), not derived from data, and
# must be updated by hand each week a new target is set, same cadence as
# the workbook itself. When the current week moves past this date without
# an update, the section simply stops showing a target (rather than
# comparing against a stale one) until refreshed.
WEEKLY_TARGET_WEEK_START = "2026-07-20"
WEEKLY_TARGET_VALUES = {
    "old_users_count": 1876.0,
    "old_users_avg_deposit": 2237.0,
    "total_deposit": 4090000.0,
    "total_depositor_count": 1975.0,
}
WEEKLY_TARGET_LABELS = {
    "old_users_count": "Old Users Count",
    "old_users_avg_deposit": "Avg Deposit of Old Users",
    "total_deposit": "Avg Total Deposit (Day)",
    "total_depositor_count": "Total Depositor Count (Day)",
}

_WEEKLY_PERF_METRIC_KEYS = [
    "old_users_count", "new_users_count", "old_users_avg_deposit", "new_users_avg_deposit",
    "old_users_withdraw_count", "old_users_avg_withdraw", "new_users_withdraw_count",
    "new_users_avg_withdraw", "total_deposit", "total_depositor_count",
]
_WEEKLY_PERF_METRIC_LABELS = {
    "old_users_count": "Old Users Count",
    "new_users_count": "New Users Count",
    "old_users_avg_deposit": "Avg Deposit — Old Users",
    "new_users_avg_deposit": "Avg Deposit — New Users",
    "old_users_withdraw_count": "Old Users Withdraw Count",
    "old_users_avg_withdraw": "Avg Withdraw — Old Users",
    "new_users_withdraw_count": "New Users Withdraw Count",
    "new_users_avg_withdraw": "Avg Withdraw — New Users",
    "total_deposit": "Total Deposit (Day)",
    "total_depositor_count": "Total Depositor Count (Day)",
}


def weekly_performance_report(new_old_daily, new_old_retention, today):
    """Live week-on-week performance section -- mirrors the recurring
    "Weekly Data Comparison & Target" Excel report's Week-on-Week +
    Target vs Actual sheets, computed fresh from the SAME daily new/old
    rows already powering New vs Old User Analysis above (no extra
    queries). Compares the CURRENT calendar week (Monday-Sunday, however
    many days have elapsed so far) against the most recent FULLY COMPLETE
    prior week (exactly 7 retained days) -- so the comparison is always
    "this week's pace so far" vs "last week's final result," never two
    partial weeks against each other.

    On Monday/Tuesday, "current week" instead means the week that JUST
    ENDED (still shown as a full, final 7-vs-7 report) rather than the
    brand-new week that's only 1-2 days old -- same "grace period before
    cutover" idea as weekly_cashback_week_range() above (which holds the
    display on the just-completed week through Sunday evening), just a
    2-day window instead of a same-day time cutoff, so admins get Monday
    and Tuesday to review last week's finished numbers before the section
    flips to tracking the new week's early pace on Wednesday.

    "However many days have elapsed" always excludes today itself -- today
    is still accumulating deposits with every hourly pipeline run, so a
    partial day would understate the average next to fully-finished prior
    days. The current week's average is only ever built from yesterday
    backwards.

    Returns None if there's no data for the displayed week yet or no
    complete prior week to compare against (e.g. right after the 33-day
    retention window rolls past a boundary)."""
    def week_start(date_str):
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return d - timedelta(days=d.weekday())

    by_week = defaultdict(list)
    for row in new_old_daily:
        by_week[week_start(row["date"])].append(row)

    real_week_start = today - timedelta(days=today.weekday())
    current_week_start = real_week_start - timedelta(days=7) if today.weekday() < 2 else real_week_start
    # Exclude today itself -- it's still accumulating deposits with every
    # hourly pipeline run, so a partial "today" would understate the
    # average next to fully-finished prior days. Only matters during
    # normal (Wed-Sun) tracking; during the Mon/Tue grace period above,
    # current_week_start is already last week and today can't appear in it.
    current_week_rows = sorted(
        (r for r in by_week.get(current_week_start, []) if r["date"] < today.isoformat()),
        key=lambda r: r["date"],
    )
    if not current_week_rows:
        return None

    prior_week_start = next(
        (ws for ws in sorted(by_week.keys(), reverse=True) if ws < current_week_start and len(by_week[ws]) == 7),
        None,
    )
    if prior_week_start is None:
        return None
    prior_week_rows = sorted(by_week[prior_week_start], key=lambda r: r["date"])

    def week_avg(rows):
        return {k: round(sum(r[k] for r in rows) / len(rows), 2) for k in _WEEKLY_PERF_METRIC_KEYS}

    prior_avg = week_avg(prior_week_rows)
    current_avg = week_avg(current_week_rows)

    comparison = []
    for k in _WEEKLY_PERF_METRIC_KEYS:
        change = round(current_avg[k] - prior_avg[k], 2)
        pct_change = round(change / prior_avg[k] * 100, 2) if prior_avg[k] else None
        comparison.append({
            "metric": _WEEKLY_PERF_METRIC_LABELS[k],
            "key": k,
            "prior": prior_avg[k],
            "current": current_avg[k],
            "change": change,
            "pct_change": pct_change,
        })

    ret_by_date = {r["date"]: r for r in new_old_retention}

    def retention_week_avg(rows):
        dates = [r["date"] for r in rows if r["date"] in ret_by_date]
        if not dates:
            return None
        withdrew_vals = [ret_by_date[d]["withdrew_group_retention_pct"] for d in dates if ret_by_date[d]["withdrew_group_retention_pct"] is not None]
        never_vals = [ret_by_date[d]["never_withdrew_group_retention_pct"] for d in dates if ret_by_date[d]["never_withdrew_group_retention_pct"] is not None]
        return {
            "cohorts_included": len(dates),
            "new_users_avg": round(sum(ret_by_date[d]["new_users"] for d in dates) / len(dates), 2),
            "withdrew_retention_pct": round(sum(withdrew_vals) / len(withdrew_vals), 2) if withdrew_vals else None,
            "never_withdrew_retention_pct": round(sum(never_vals) / len(never_vals), 2) if never_vals else None,
        }

    retention_comparison = {
        "prior": retention_week_avg(prior_week_rows),
        "current": retention_week_avg(current_week_rows),
    }

    target = None
    if current_week_start.isoformat() == WEEKLY_TARGET_WEEK_START:
        target = []
        for k, t in WEEKLY_TARGET_VALUES.items():
            actual = current_avg[k]
            pct = round(actual / t * 100, 2) if t else None
            target.append({
                "metric": WEEKLY_TARGET_LABELS[k],
                "key": k,
                "target": t,
                "actual": actual,
                "variance": round(actual - t, 2),
                "pct_of_target": pct,
                "status": "MET" if pct is not None and pct >= 100 else "BEHIND",
            })

    return {
        "prior_week_start": prior_week_start.isoformat(),
        "prior_week_end": (prior_week_start + timedelta(days=6)).isoformat(),
        "prior_week_days": len(prior_week_rows),
        "current_week_start": current_week_start.isoformat(),
        "current_week_end": (current_week_start + timedelta(days=6)).isoformat(),
        "current_week_days": len(current_week_rows),
        "comparison": comparison,
        "retention_comparison": retention_comparison,
        "target": target,
    }


def _aggregate_games_reports(rows, agent_by_user, last_active_label_by_user, vip_by_id, cap=None):
    """Shared aggregation for top_games_new_users' Overall/Day/Week/Month
    views -- `rows` is a (user_id, game_name, change_value) subset already
    filtered to the desired date range. `cap` truncates the sorted output
    (used for Week/Month -- see top_games_new_users for why)."""
    game_totals = defaultdict(float)  # (user_id, game_name) -> total wagered
    highest_bet = {}  # user_id -> (amount, game_name)
    for user_id, game_name, change_value in rows:
        amt = change_value or 0.0
        game_totals[(user_id, game_name)] += amt
        if user_id not in highest_bet or amt > highest_bet[user_id][0]:
            highest_bet[user_id] = (amt, game_name)

    top_games = sorted(
        (
            {
                "user_id": uid,
                "vip_level": vip_by_id.get(uid),
                "agent": agent_for(agent_by_user, uid),
                "game_name": game,
                "total_bet_amount": round(total, 2),
                "last_active": last_active_label_by_user.get(uid),
            }
            for (uid, game), total in game_totals.items()
        ),
        key=lambda r: -r["total_bet_amount"],
    )[:cap]

    highest_single_bet = sorted(
        (
            {
                "user_id": uid,
                "vip_level": vip_by_id.get(uid),
                "agent": agent_for(agent_by_user, uid),
                "highest_bet": round(amt, 2),
                "game_name": game,
                "last_active": last_active_label_by_user.get(uid),
            }
            for uid, (amt, game) in highest_bet.items()
        ),
        key=lambda r: -r["highest_bet"],
    )[:cap]

    return {"top_games": top_games, "highest_single_bet": highest_single_bet}


def top_games_new_users(daily_conn, master_conn, deposit_rows, agent_by_user, all_dates, today):
    """Two Platform Analysis reports below New vs Old User Analysis, both
    scoped to "new" users -- anyone whose FIRST-EVER deposit
    (is_first_deposit=1) landed within the current 33-day retention window,
    same population new_vs_old_user_analysis's daily new_ids union to. Both
    built from bet-only wallet_transactions rows (direction=1, same Bet/Win
    convention as recent_activity() above; win payouts are excluded since
    these are spend reports):
      - "Top Games": per (user, game), total amount wagered.
      - "Highest Single Bet": for each user, their single largest bet
        transaction and which game it was on.
    Each ships 4 views -- "overall" (rolling 15 days, not the full 33-day
    retention window -- the un-windowed version routinely ran to thousands
    of pages), "by_date" (one calendar day), "by_week" (rolling 7 days
    ending that date), "by_month" (rolling 30 days ending that date,
    clipped to all_dates like bonus_claims_by_week/month) -- so the
    frontend can offer the same Overall/Day/Week/Month switch as Bonus
    Claim Report.
    UNCAPPED -- every qualifying row ships, not just a top-N slice, so both
    the on-screen table and its Excel export are complete."""
    empty = {"top_games": [], "highest_single_bet": []}
    new_user_ids = {
        user_id
        for pay_channel, order_amount, create_time, update_time, status, user_id, is_first_deposit in deposit_rows
        if status == "COMPLETE" and user_id is not None and is_first_deposit == 1
    }
    if not new_user_ids:
        return {"overall": empty, "by_date": {}, "by_week": {}, "by_month": {}, "dates": all_dates}

    placeholders = ",".join("?" * len(new_user_ids))
    rows = daily_conn.execute(
        "SELECT user_id, game_name, change_value, create_time FROM wallet_transactions "
        "WHERE direction = 1 AND game_name IS NOT NULL AND game_name != '' "
        f"AND user_id IN ({placeholders})",
        list(new_user_ids),
    ).fetchall()

    last_active_label_by_user = {}
    vip_by_id = {}
    if master_conn is not None:
        placeholders2 = ",".join("?" * len(new_user_ids))
        for user_id, vip_level, last_active_time in master_conn.execute(
            f"SELECT user_id, vip_level, last_active_time FROM users WHERE user_id IN ({placeholders2})", list(new_user_ids)
        ).fetchall():
            vip_by_id[user_id] = vip_level
            dt = parse_dt(last_active_time)
            if not dt:
                continue
            gap = (today - dt.date()).days
            last_active_label_by_user[user_id] = "Today" if gap <= 0 else f"{gap}d ago"

    rows_by_date = defaultdict(list)
    for user_id, game_name, change_value, create_time in rows:
        dt = parse_dt(create_time)
        if not dt:
            continue
        rows_by_date[dt.date().isoformat()].append((user_id, game_name, change_value))

    all_dates_set = set(all_dates)

    def rolling_window(end_date_str, days):
        end_d = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        return {(end_d - timedelta(days=i)).isoformat() for i in range(days)} & all_dates_set

    # "Overall" is the last 15 days of activity, not the full 33-day
    # retention window -- the un-windowed version routinely ran to
    # thousands of pages, unwieldy to browse. The 33-day "new user" (FD)
    # cohort definition itself is unchanged; only the bet-activity window
    # aggregated into this view got narrower. Uncapped within that 15-day
    # window (Day view is also uncapped -- both are genuinely bounded).
    # Week/Month are capped at ACTION_CENTER_LIST_CAP: precomputed for
    # EVERY retained date so the date-switch works instantly, but adjacent
    # dates' 7/30-day windows heavily overlap, so uncapped week/month
    # duplicated ~95% of their rows across dates -- measured at 53MB
    # combined (of a 110MB report) before this cap, the single largest
    # contributor to Platform Analysis failing to load in a browser tab.
    # Same fix as bonus_claims_by_week/month's claim_details.
    last15_dates = rolling_window(today.isoformat(), 15)
    last15_rows = [r for d in last15_dates for r in rows_by_date.get(d, [])]
    overall = _aggregate_games_reports(last15_rows, agent_by_user, last_active_label_by_user, vip_by_id)
    by_date, by_week, by_month = {}, {}, {}
    for date_str in all_dates:
        by_date[date_str] = _aggregate_games_reports(rows_by_date.get(date_str, []), agent_by_user, last_active_label_by_user, vip_by_id)
        week_rows = [r for d in rolling_window(date_str, 7) for r in rows_by_date.get(d, [])]
        by_week[date_str] = _aggregate_games_reports(week_rows, agent_by_user, last_active_label_by_user, vip_by_id, cap=ACTION_CENTER_LIST_CAP)
        month_rows = [r for d in rolling_window(date_str, 30) for r in rows_by_date.get(d, [])]
        by_month[date_str] = _aggregate_games_reports(month_rows, agent_by_user, last_active_label_by_user, vip_by_id, cap=ACTION_CENTER_LIST_CAP)

    return {"overall": overall, "by_date": by_date, "by_week": by_week, "by_month": by_month, "dates": all_dates}


# High/Low Roller Active (Platform Analysis, below Games Activity -- New
# Users): thresholds are all LIFETIME figures from master_userlist.db's
# running total_recharge/recharge_count columns, NOT scoped to the 33-day
# retention window -- "500 lifetime deposits" wouldn't be reachable within
# just 33 days for almost anyone. Avg Bet Size and Top Game Played both use
# the SAME fixed last-15-day wallet_transactions window regardless of
# report (only the Last Active recency cutoff differs between the two).
HIGH_ROLLER_MIN_AVG_DEPOSIT = 5000.0
HIGH_ROLLER_MIN_DEPOSIT_COUNT = 500
HIGH_ROLLER_MIN_TOTAL_DEPOSIT = 500000.0
HIGH_ROLLER_MIN_AVG_BET = 500.0
HIGH_ROLLER_MIN_VIP = 7
HIGH_ROLLER_MAX_INACTIVE_DAYS = 15

LOW_ROLLER_MAX_AVG_DEPOSIT = 5000.0
LOW_ROLLER_MAX_DEPOSIT_COUNT = 500
LOW_ROLLER_MAX_TOTAL_DEPOSIT = 500000.0
LOW_ROLLER_MAX_AVG_BET = 500.0
LOW_ROLLER_MIN_VIP = 2
LOW_ROLLER_MAX_VIP = 6
LOW_ROLLER_MAX_INACTIVE_DAYS = 10

ROLLER_BET_WINDOW_DAYS = 15


def _classify_roller(vip, total_recharge, avg_bet, avg_deposit, recharge_count):
    """Priority waterfall deciding High vs Low Roller for a user whose
    profile would otherwise match criteria on both sides -- checked in
    this exact order (first decisive criterion wins, skipping any with no
    data to evaluate): VIP Level, Total Deposit, Avg Bet Size (last 15
    days), Avg Deposit Amount, Deposit Count. Returns None if none of the
    5 have enough data to decide (excluded from both reports)."""
    if vip is not None:
        if vip >= HIGH_ROLLER_MIN_VIP:
            return "high"
        if LOW_ROLLER_MIN_VIP <= vip <= LOW_ROLLER_MAX_VIP:
            return "low"
    if total_recharge is not None:
        return "high" if total_recharge >= HIGH_ROLLER_MIN_TOTAL_DEPOSIT else "low"
    if avg_bet is not None:
        return "high" if avg_bet > HIGH_ROLLER_MIN_AVG_BET else "low"
    if avg_deposit is not None:
        return "high" if avg_deposit >= HIGH_ROLLER_MIN_AVG_DEPOSIT else "low"
    if recharge_count is not None:
        return "high" if recharge_count >= HIGH_ROLLER_MIN_DEPOSIT_COUNT else "low"
    return None


def high_low_roller_reports(mconn, daily_conn, agent_by_user, today):
    """Two MUTUALLY EXCLUSIVE rosters of currently-active depositors --
    every qualifying user appears in exactly one of High Roller Active or
    Low Roller Active, never both. Classification uses a priority
    waterfall (see _classify_roller: VIP Level, Total Deposit, Avg Bet
    Size, Avg Deposit Amount, Deposit Count -- first decisive criterion
    wins) rather than "match any of 5 criteria" independently per report,
    which previously let the same whale (huge total deposit, huge deposit
    COUNT, low AVERAGE deposit) satisfy a criterion on both sides at once.
    "Active" gates each side separately AFTER classification -- within 15
    days for anyone classified High, within 10 days for anyone classified
    Low -- so a user who'd classify High but hasn't been active in 15 days
    is dropped entirely, not reassigned to Low.
    "Top Game Played" = the game of that user's single highest bet within
    the last 15 days -- blank for users classified via a non-bet
    criterion who placed no bets in that window."""
    users = mconn.execute(
        "SELECT user_id, vip_level, total_recharge, recharge_count, user_balance, last_active_time FROM users"
    ).fetchall()

    # Widest possible window (15 days) so anyone who COULD end up in
    # either roster is included -- narrowed to each side's own cutoff
    # (15d high / 10d low) after classification, below.
    scan_ids = set()
    base_by_user = {}
    inactive_days_by_user = {}
    vip_by_id, total_recharge_by_id, avg_deposit_by_id, recharge_count_by_id = {}, {}, {}, {}
    for user_id, vip, total_recharge, recharge_count, balance, last_active_time in users:
        dt = parse_dt(last_active_time)
        if not dt:
            continue
        inactive_days = (today - dt.date()).days
        if inactive_days > HIGH_ROLLER_MAX_INACTIVE_DAYS:
            continue
        scan_ids.add(user_id)
        inactive_days_by_user[user_id] = inactive_days
        base_by_user[user_id] = {
            "total_deposit": round(total_recharge or 0.0, 2),
            "wallet_balance": round(balance or 0.0, 2),
        }
        vip_by_id[user_id] = vip
        total_recharge_by_id[user_id] = total_recharge
        avg_deposit_by_id[user_id] = (total_recharge or 0.0) / recharge_count if recharge_count else None
        recharge_count_by_id[user_id] = recharge_count

    if not scan_ids:
        return {"high_roller": [], "low_roller": []}

    # Filtered by date range ONLY (not "AND user_id IN (...)") -- wallet_transactions
    # only has single-column indexes (user_id, create_time, game_name separately,
    # no composite), so combining a large IN-list with the date filter forces
    # SQLite to scan every historical row for each candidate user one at a time
    # (measured: 500 users -> 17s, 15,000 would be ~9 minutes). A single
    # date-range scan using idx_wt_time, with candidate membership checked in
    # Python, is dramatically faster (measured: ~20s for the whole ~15K-user
    # candidate pool against 17M+ matching rows).
    window_start = (today - timedelta(days=ROLLER_BET_WINDOW_DAYS)).isoformat()
    bet_sum, bet_count = defaultdict(float), defaultdict(int)
    top_bet = {}  # user_id -> (amount, game_name)
    for user_id, game_name, change_value in daily_conn.execute(
        "SELECT user_id, game_name, change_value FROM wallet_transactions "
        "WHERE direction = 1 AND game_name IS NOT NULL AND game_name != '' AND create_time >= ?",
        (window_start,),
    ):
        if user_id not in scan_ids:
            continue
        amt = change_value or 0.0
        bet_sum[user_id] += amt
        bet_count[user_id] += 1
        if user_id not in top_bet or amt > top_bet[user_id][0]:
            top_bet[user_id] = (amt, game_name)

    high_roller, low_roller = [], []
    for uid in scan_ids:
        avg_bet = (bet_sum[uid] / bet_count[uid]) if bet_count.get(uid) else None
        cls = _classify_roller(vip_by_id[uid], total_recharge_by_id[uid], avg_bet, avg_deposit_by_id[uid], recharge_count_by_id[uid])
        if cls is None:
            continue
        max_days = HIGH_ROLLER_MAX_INACTIVE_DAYS if cls == "high" else LOW_ROLLER_MAX_INACTIVE_DAYS
        if inactive_days_by_user[uid] > max_days:
            continue
        base = base_by_user[uid]
        row = {
            "user_id": uid,
            "vip_level": vip_by_id[uid],
            "agent": agent_for(agent_by_user, uid),
            "total_deposit": base["total_deposit"],
            "wallet_balance": base["wallet_balance"],
            "top_game_played": top_bet[uid][1] if uid in top_bet else None,
        }
        (high_roller if cls == "high" else low_roller).append(row)

    high_roller.sort(key=lambda r: -r["total_deposit"])
    low_roller.sort(key=lambda r: -r["total_deposit"])
    return {"high_roller": high_roller, "low_roller": low_roller}


# Raw "city" values on user records are a messy mix of actual state/region
# names and individual city names (some with inconsistent casing) --
# REGION_MAPPING (from State_and_City_Mapping.xlsx) normalizes every known
# raw value to its correct State/Region so the Region vs VIP Depositor
# Matrix collapses cities into their parent region instead of listing them
# as separate rows. Keys are lowercased for case-insensitive lookup.
REGION_MAPPING = {
    'tamil nadu': 'Tamil Nadu',
    'karnataka': 'Karnataka',
    'andhra pradesh': 'Andhra Pradesh',
    'uttar pradesh': 'Uttar Pradesh',
    'kerala': 'Kerala',
    'maharashtra': 'Maharashtra',
    'gujarat belt': 'Gujarat Belt',
    'madhya pradesh': 'Madhya Pradesh',
    'bihar belt': 'Bihar Belt',
    'odisha': 'Odisha',
    'delhi ncr': 'Delhi NCR',
    'west bengal': 'West Bengal',
    'rajasthan': 'Rajasthan',
    'punjab': 'Punjab',
    'haryana': 'Haryana',
    'chennai': 'Tamil Nadu',
    'bengaluru': 'Karnataka',
    'mumbai': 'Maharashtra',
    'assam': 'Assam',
    'delhi': 'Delhi NCR',
    'indore': 'Madhya Pradesh',
    'ahmedabad': 'Gujarat',
    'pune': 'Maharashtra',
    'mysuru': 'Karnataka',
    'jammu kashmir': 'Jammu Kashmir',
    'himachal pradesh': 'Himachal Pradesh',
    'lucknow': 'Uttar Pradesh',
    'rājkot': 'Gujarat',
    'northeast': 'Northeast',
    'jaipur': 'Rajasthan',
    'hyderabad': 'Andhra Pradesh',
    'vadodara': 'Gujarat',
    'durgapur': 'West Bengal',
    'morādābād': 'Uttar Pradesh',
    'shimla': 'Himachal Pradesh',
    'mūlki': 'Karnataka',
    'thiruvananthapuram': 'Kerala',
    'raipur': 'Chhattisgarh',
    'coimbatore': 'Tamil Nadu',
    'madgaon': 'Goa',
    'ludhiana': 'Punjab',
    'rasapūdipalem': 'Andhra Pradesh',
    'ghāziābād': 'Uttar Pradesh',
    'durg': 'Chhattisgarh',
    'tadepalligudem': 'Andhra Pradesh',
    'nashik': 'Maharashtra',
    'vijayawada': 'Andhra Pradesh',
    'pimpri': 'Maharashtra',
    'kanpur': 'Uttar Pradesh',
    'virār': 'Maharashtra',
    'imphal': 'Manipur',
    'gurugram': 'Haryana',
    'dharmapuri': 'Tamil Nadu',
    'faridabad': 'Haryana',
    'nellore': 'Andhra Pradesh',
    'amsterdam': 'Netherlands',
    'gorakhpur': 'Uttar Pradesh',
    'varanasi': 'Uttar Pradesh',
    'latur': 'Maharashtra',
    'kota': 'Rajasthan',
    'kalyān': 'Maharashtra',
    'tiruppur': 'Tamil Nadu',
    'payyanur': 'Kerala',
    'madurai': 'Tamil Nadu',
    'alīgarh': 'Uttar Pradesh',
    'bhubaneswar': 'Odisha',
    'panipat': 'Haryana',
    'salem': 'Tamil Nadu',
    'tiruchirappalli': 'Tamil Nadu',
    'rohtak': 'Haryana',
    'jaunpur': 'Uttar Pradesh',
    'jamshedpur': 'Jharkhand',
    'saugor': 'Madhya Pradesh',
    'tirupati': 'Andhra Pradesh',
    'agra': 'Uttar Pradesh',
    'meerut': 'Uttar Pradesh',
    'aurangabad': 'Maharashtra',
    'patna': 'Bihar',
    'ambarnath': 'Maharashtra',
    'srinagar': 'Jammu & Kashmir',
    'mangaluru': 'Karnataka',
    'siliguri': 'West Bengal',
    'kumarapalayam': 'Tamil Nadu',
    'tamilnadu': 'Tamil Nadu',
    'nanded': 'Maharashtra',
    'kanayannur': 'Kerala',
    'sahāranpur': 'Uttar Pradesh',
    'kolkata': 'West Bengal',
    'muzaffarnagar': 'Uttar Pradesh',
    'dewas': 'Madhya Pradesh',
    'jammu': 'Jammu & Kashmir',
    'solan': 'Himachal Pradesh',
    'dubai': 'UAE',
    'hisar': 'Haryana',
    'new york city': 'USA',
    'bahraigh': 'Uttar Pradesh',
    'kozhikode': 'Kerala',
    'surat': 'Gujarat',
    'kallakurichi': 'Tamil Nadu',
    'pathānkot': 'Punjab',
    'davangere': 'Karnataka',
    'bāola': 'Gujarat',
    'shāhpur': 'Unknown',
    'dehradun': 'Uttarakhand',
    'pollachi': 'Tamil Nadu',
}


def map_region(raw_city):
    """Normalize a raw city/region string via REGION_MAPPING; unmapped or
    blank values fall back to "Unknown" rather than showing raw, possibly
    duplicated city names as their own region rows."""
    if not raw_city:
        return "Unknown"
    return REGION_MAPPING.get(str(raw_city).strip().lower(), "Unknown")


def region_vip_depositor_matrix(deposit_rows, city_by_user, vip_by_user, all_dates):
    """Platform Analysis section below Game & Revenue Economics: rows =
    Region, columns = VIP level, cell = how many DISTINCT users in that
    Region+VIP combination made at least one COMPLETE deposit. Ships raw
    per-day user-id lists (not pre-summed counts) so the frontend can do
    genuine unique-depositor de-duplication across ANY combination of
    selected dates it builds client-side -- a single day, an arbitrary
    multi-select, a calendar week (Monday-Sunday), or a calendar month --
    without a user who deposited on multiple selected days being
    double-counted. Region is compressed via map_region() (REGION_MAPPING)
    so individual cities collapse into their parent state/region instead of
    showing as separate rows -- unmapped/blank values group as "Unknown".
    Users with no VIP level on record are excluded (a VIP-level breakdown
    can't place them)."""
    depositors_by_date = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    for pay_channel, order_amount, create_time, update_time, status, user_id, is_first_deposit in deposit_rows:
        if status != "COMPLETE" or user_id is None:
            continue
        vip = vip_by_user.get(user_id)
        if vip is None:
            continue
        dt = parse_dt(create_time)
        if not dt:
            continue
        region = map_region(city_by_user.get(user_id))
        depositors_by_date[dt.date().isoformat()][region][vip].add(user_id)

    matrix_by_date = {
        date_str: {region: {vip: sorted(ids) for vip, ids in vip_map.items()} for region, vip_map in region_map.items()}
        for date_str, region_map in depositors_by_date.items()
    }
    return {"dates": all_dates, "matrix_by_date": matrix_by_date}


def channel_performance_report(daily_conn, today):
    """Channel acquisition quality, last 4 days combined. Of users whose
    FIRST deposit (is_first_deposit=1) landed in the last 4 calendar days,
    grouped by acquisition channel (deposits' own 'channel' column,
    spreadsheet column P -- the marketing/agent referral channel, not
    pay_channel/payment method): FD Users, FD Amount, Avg FD, and how many
    came back to deposit again on Day 2 (FD+1) and Day 3 (FD+2).

    Quality is a simple heuristic: a high average first-deposit amount
    marks a valuable acquisition regardless of short-term return rate
    ("High value"); otherwise it's graded on Day-2 return rate (Good >=25%,
    Average 15-24%, Weak <15%)."""
    window_start = today - timedelta(days=3)
    rows = daily_conn.execute(
        "SELECT channel, user_id, order_amount, create_time, is_first_deposit FROM deposits "
        "WHERE status = 'COMPLETE' AND create_time >= ?",
        (window_start.isoformat(),),
    ).fetchall()

    fd_by_user = {}
    deposit_dates_by_user = defaultdict(set)
    for channel, user_id, order_amount, create_time, is_first_deposit in rows:
        if user_id is None:
            continue
        dt = parse_dt(create_time)
        if not dt:
            continue
        deposit_dates_by_user[user_id].add(dt.date())
        if is_first_deposit == 1 and dt.date() >= window_start:
            fd_by_user[user_id] = (channel or "Unknown", dt.date(), order_amount or 0.0)

    by_channel = defaultdict(lambda: {"fd_users": 0, "fd_amount": 0.0, "d2_users": 0, "d3_users": 0})
    for user_id, (channel, fd_date, fd_amount) in fd_by_user.items():
        b = by_channel[channel]
        b["fd_users"] += 1
        b["fd_amount"] += fd_amount
        day_map = deposit_dates_by_user.get(user_id, set())
        if (fd_date + timedelta(days=1)) in day_map:
            b["d2_users"] += 1
        if (fd_date + timedelta(days=2)) in day_map:
            b["d3_users"] += 1

    def quality(avg_fd, d2_pct):
        if avg_fd >= 800:
            return "High value"
        if d2_pct >= 25:
            return "Good"
        if d2_pct >= 15:
            return "Average"
        return "Weak"

    result = []
    for channel, b in by_channel.items():
        avg_fd = round(b["fd_amount"] / b["fd_users"], 2) if b["fd_users"] else 0.0
        d2_pct = round(b["d2_users"] / b["fd_users"] * 100, 1) if b["fd_users"] else 0.0
        d3_pct = round(b["d3_users"] / b["fd_users"] * 100, 1) if b["fd_users"] else 0.0
        result.append({
            "channel": channel,
            "fd_users": b["fd_users"],
            "fd_amount": round(b["fd_amount"], 2),
            "avg_fd": avg_fd,
            "d2_users": b["d2_users"],
            "d2_pct": d2_pct,
            "d3_users": b["d3_users"],
            "d3_pct": d3_pct,
            "quality": quality(avg_fd, d2_pct),
        })
    result.sort(key=lambda r: -r["fd_users"])
    return result


USER_SEARCH_SHARDS = 40


def build_recent_activity_by_user(daily_conn, today):
    """The daily_records.db-dependent half of the user search index: recent
    deposits (7 days, with order_no -- not in the shared deposit_rows tuple
    used everywhere else, so this is a dedicated query), recent withdrawals
    (7 days), and recent games played (2 days, excluding bonus payouts via
    `id NOT IN (SELECT id FROM bonuses)` -- bonuses.id directly reuses the
    source wallet_transactions.id, see ingest_wallet() in ingest_update.py,
    so this is an exact join, not a name-matching heuristic repeated a third
    time). Called while `conn` is still open, same as channel_performance_report,
    since daily_records.db's connection is closed early in main()."""
    dep_start = (today - timedelta(days=6)).isoformat()
    deposits_by_user = defaultdict(list)
    deposit_count_7d = defaultdict(int)
    for user_id, order_amount, create_time, status, order_no, pay_center_order_no, pay_channel in daily_conn.execute(
        "SELECT user_id, order_amount, create_time, status, order_no, pay_center_order_no, pay_channel FROM deposits WHERE create_time >= ?",
        (dep_start,),
    ).fetchall():
        if user_id is None:
            continue
        # pay_center_order_no is the "TP..."-prefixed order number the
        # platform's own admin panel shows; order_no ("DI..."-prefixed) is
        # only a fallback for older rows that predate this column being
        # populated, same pattern withdrawals already use for their own
        # payment_center_order_no.
        deposits_by_user[user_id].append({
            "date": create_time, "amount": order_amount, "status": status,
            "order_no": pay_center_order_no or order_no, "channel": pay_channel,
        })
        if status == "COMPLETE":
            deposit_count_7d[user_id] += 1

    withdrawals_by_user = defaultdict(list)
    for user_id, withdraw_amount, create_time, status, order_no, payment_channel in daily_conn.execute(
        "SELECT user_id, withdraw_amount, create_time, status, order_no, payment_channel FROM withdrawals WHERE create_time >= ?",
        (dep_start,),
    ).fetchall():
        if user_id is None:
            continue
        withdrawals_by_user[user_id].append({
            "date": create_time, "amount": withdraw_amount, "status": STATUS_LABELS.get(status, status),
            "order_no": order_no, "channel": payment_channel,
        })

    games_start = (today - timedelta(days=1)).isoformat()
    games_by_user = defaultdict(list)
    for user_id, game_name, change_value, create_time, direction in daily_conn.execute(
        "SELECT user_id, game_name, change_value, create_time, direction FROM wallet_transactions "
        "WHERE game_name IS NOT NULL AND game_name != '' AND create_time >= ? "
        "AND id NOT IN (SELECT id FROM bonuses)",
        (games_start,),
    ).fetchall():
        if user_id is None:
            continue
        # direction=1 = bet (debit), direction=0 = win payout (credit) --
        # change_value itself is always a positive magnitude in this data,
        # confirmed via an earlier diagnostic; direction carries the actual
        # sign, not change_value.
        games_by_user[user_id].append({
            "game_name": game_name, "amount": change_value,
            "type": "Win" if direction == 0 else "Bet", "date": create_time,
        })

    bonus_start = (today - timedelta(days=6)).isoformat()
    bonuses_by_user = defaultdict(list)
    try:
        bonus_rows = daily_conn.execute(
            "SELECT user_id, matched_category, change_value, create_time FROM bonuses "
            "WHERE create_time >= ?",
            (bonus_start,),
        ).fetchall()
    except sqlite3.OperationalError:
        bonus_rows = []
    for user_id, matched_category, change_value, create_time in bonus_rows:
        if user_id is None:
            continue
        bonuses_by_user[user_id].append({
            "category": matched_category, "amount": change_value, "date": create_time,
        })

    for d in deposits_by_user.values():
        d.sort(key=lambda r: r["date"], reverse=True)
    for d in withdrawals_by_user.values():
        d.sort(key=lambda r: r["date"], reverse=True)
    for d in games_by_user.values():
        d.sort(key=lambda r: r["date"], reverse=True)
        del d[15:]  # keep only the most recent 15 per user
    for d in bonuses_by_user.values():
        d.sort(key=lambda r: r["date"], reverse=True)

    return deposits_by_user, withdrawals_by_user, games_by_user, bonuses_by_user, deposit_count_7d


def build_and_upload_user_search_index(mconn, recent_activity, creds, agent_by_user):
    """Sharded user-search index, rebuilt from scratch every run (cheap:
    everything needed is already local to this pipeline run, no extra
    network calls). Cloudflare Workers can't practically query a 224MB+
    SQLite file per search request -- 40 small JSON shard files in R2 let
    the dashboard's Search User page do one cheap R2 GET (shard =
    user_id % 40) instead. Every user in master_userlist.db gets an entry
    (even ones with zero activity, so a lookup for any valid ID gives a
    sensible "no recent activity" result rather than a 404); recent
    deposits/withdrawals/games are only present for users who have any."""
    deposits_by_user, withdrawals_by_user, games_by_user, bonuses_by_user, deposit_count_7d = recent_activity
    shards = [dict() for _ in range(USER_SEARCH_SHARDS)]
    # Phone is deliberately not selected/exposed here -- not displayed
    # anywhere on the dashboard. recharge_count is the platform's own
    # lifetime deposit count (bootstrapped from the original userlist
    # export, incrementally updated in sync_master_userlist() exactly like
    # total_recharge -- see api_pull_ingest.py).
    rows = mconn.execute(
        "SELECT user_id, city, channel, total_recharge, total_withdrawal, vip_level, "
        "user_balance, last_active_time, create_time, recharge_count FROM users"
    ).fetchall()
    for user_id, city, channel, total_recharge, total_withdrawal, vip_level, user_balance, last_active_time, create_time, recharge_count in rows:
        profile = {
            "user_id": user_id,
            "agent": agent_for(agent_by_user, user_id),
            "region": city,
            "acquisition_channel": channel,
            "vip_level": vip_level,
            "total_deposit": round(total_recharge or 0.0, 2),
            "total_deposit_count": recharge_count or 0,
            "total_withdraw": round(total_withdrawal or 0.0, 2),
            "wallet_balance": round(user_balance or 0.0, 2),
            "net_lifetime": round((total_recharge or 0.0) - (total_withdrawal or 0.0), 2),
            "last_active_time": last_active_time,
            "registered": create_time,
            "recent_deposits": deposits_by_user.get(user_id, []),
            "recent_deposit_count_7d": deposit_count_7d.get(user_id, 0),
            "recent_withdrawals": withdrawals_by_user.get(user_id, []),
            "recent_games": games_by_user.get(user_id, []),
            "recent_bonuses": bonuses_by_user.get(user_id, []),
        }
        shards[user_id % USER_SEARCH_SHARDS][str(user_id)] = profile

    s3 = boto3.client(
        "s3",
        endpoint_url=creds["R2_ENDPOINT_URL"],
        aws_access_key_id=creds["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=creds["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    for i, shard in enumerate(shards):
        key = f"user_search/shard_{i:02d}.json"
        s3.put_object(Bucket=creds["R2_BUCKET"], Key=key, Body=json.dumps(shard), ContentType="application/json")
    print(f"Uploaded {USER_SEARCH_SHARDS} user search shards covering {len(rows)} users")


def bonus_claim_report(bonus_rows_all, deposit_rows, deposit_challenge_bonus_rows, target_dates, agent_by_user):
    """All bonuses claimed on target_dates -- both wallet-sourced bonuses
    (Welcome Back, Loyalty, VIP tiers, Daily Active, etc., from
    daily_records.db's `bonuses` table) and the 3-Day Deposit Challenge
    Bonus (Rules 1-4). For each: claimed users, total bonus value, how many
    of those claimers ALSO made a COMPLETE deposit at any point that same
    day (a same-day "did the bonus convert into a deposit" signal) plus the
    actual amount they deposited (not just the headcount -- two converters
    aren't equally valuable if one deposited Rs200 and the other
    Rs20,000), and the resulting %.

    Called once per retained date (see main()'s bonus_claims_by_date loop)
    so the dashboard's date filter can browse any day in the retention
    window, not just today -- bonus_rows_all is fetched ONCE by the caller
    and reused across every call, rather than re-querying daily_records.db
    per date. The permanent bonus_performance rollup (see
    compute_and_save_bonus_performance in api_pull_ingest.py) still tracks
    lifetime history for each category regardless of what this specific
    view surfaces.

    Learning about new bonuses: `bonuses` is populated by classify_bonus()
    (in ingest_update.py) under four confirmed rules -- a real bonus name
    in game_name with blank source (category = game_name); game_name
    literally "Elle Import Excel Add", using source_id for the real bonus
    identity (e.g. "Daily Active Low VIP"); blank game_name with "bonus"
    in source_id, rolled up into combined "Daily Active Bonus"/"Daily
    Active Bonus Low" categories (stripping the random per-instance
    suffix); or blank game_name with source_id starting "WEEKLY_SIGN",
    rolled up into "Weekly Check-IN Bonus". Any bonus matching one of these
    rules is picked up
    automatically the first day it appears -- no maintained name list, no
    code change needed.

    target_dates is an iterable of 'YYYY-MM-DD' strings -- a single day for
    the Day view, or a rolling 7/30-day window for the Week/Month views
    (see bonus_claims_by_week/bonus_claims_by_month in main()). Using a set
    keeps "claimed users" a true distinct count across the whole window
    rather than a sum-of-daily-counts that double-counts repeat claimers.

    "Deposited After" (wallet bonuses only -- these have a real claim
    create_time; Deposit Challenge Bonus rows only carry an fd_date, no
    claim timestamp, so they keep the same-day check below) means a
    COMPLETE deposit strictly AFTER that specific claim's own timestamp,
    not merely a deposit on the same calendar date -- a user who deposited
    at 9am and claimed a bonus at 6pm the same day did NOT convert off
    that bonus, even though both events fall on the same target date. The
    per-category aggregate measures this once per user, against their
    EARLIEST claim of that category in the window, so a user who re-claims
    the same category more than once in a Week/Month view doesn't get the
    same later deposit counted as "converted" multiple times over."""
    target_dates = set(target_dates)

    # Same-day totals -- still used for Deposit Challenge Bonus below,
    # which has no per-claim timestamp to compare against.
    today_deposit_amount = defaultdict(float)
    # Individual timestamped COMPLETE deposits on target_dates, per user --
    # lets wallet bonus claims check for deposits strictly AFTER their own
    # claim time instead of just "any deposit that calendar day."
    deposits_by_user = defaultdict(list)
    for pay_channel, order_amount, create_time, update_time, status, user_id, is_first_deposit in deposit_rows:
        if status != "COMPLETE" or user_id is None or not create_time:
            continue
        if str(create_time)[:10] in target_dates:
            today_deposit_amount[user_id] += order_amount or 0.0
            dt = parse_dt(create_time)
            if dt:
                deposits_by_user[user_id].append((dt, order_amount or 0.0))
    today_depositors = set(today_deposit_amount.keys())

    def deposit_total_after(user_id, claim_dt):
        if claim_dt is None:
            return 0.0
        return sum(amt for dt, amt in deposits_by_user.get(user_id, []) if dt > claim_dt)

    filtered_claims = []
    for matched_category, user_id, change_value, create_time in bonus_rows_all:
        if not matched_category or not create_time or str(create_time)[:10] not in target_dates:
            continue
        filtered_claims.append((matched_category, user_id, change_value or 0.0, create_time, parse_dt(create_time)))

    by_category = defaultdict(lambda: {"users": set(), "value": 0.0})
    earliest_claim = {}  # (category, user_id) -> earliest claim_dt in this window
    wallet_claim_details = []
    for matched_category, user_id, change_value, create_time, claim_dt in filtered_claims:
        b = by_category[matched_category]
        b["users"].add(user_id)
        b["value"] += change_value
        key = (matched_category, user_id)
        if claim_dt is not None and (key not in earliest_claim or claim_dt < earliest_claim[key]):
            earliest_claim[key] = claim_dt

        after_amount = deposit_total_after(user_id, claim_dt)
        converted = after_amount > 0
        wallet_claim_details.append({
            "user_id": user_id,
            "agent": agent_for(agent_by_user, user_id),
            "bonus_category": matched_category,
            "bonus_amount": round(change_value, 2),
            "claimed_time": str(create_time),
            "deposited_after": "Yes" if converted else "No",
            "deposit_amount": round(after_amount, 2) if converted else 0.0,
        })
    wallet_claim_details.sort(key=lambda r: r["claimed_time"])

    def build_rows(groups, use_claim_time=False):
        rows = []
        for category, b in groups.items():
            claimed_users = len(b["users"])
            if use_claim_time:
                converted_users = [u for u in b["users"] if deposit_total_after(u, earliest_claim.get((category, u))) > 0]
                deposit_amount = sum(deposit_total_after(u, earliest_claim.get((category, u))) for u in converted_users)
            else:
                converted_users = b["users"] & today_depositors
                deposit_amount = sum(today_deposit_amount[u] for u in converted_users)
            converted = len(converted_users)
            rows.append({
                "bonus_category": category,
                "claimed_users": claimed_users,
                "total_value": round(b["value"], 2),
                "deposited_after": converted,
                "deposit_amount": round(deposit_amount, 2),
                "pct_deposited": round(converted / claimed_users * 100, 2) if claimed_users else 0.0,
                # Spend efficiency: this bonus's own total cost (ALL
                # claimers, not just converters -- the full budget was spent
                # regardless of who came back) against the deposit money
                # ITS OWN converters brought back. None (not 0) when nobody
                # converted -- 0% would misleadingly read as "very
                # efficient" when it actually means no measurable return at
                # all. This is same-day-or-after correlation, not proven
                # causation -- a converter may have deposited anyway.
                "bonus_cost_ratio_pct": round(b["value"] / deposit_amount * 100, 2) if deposit_amount else None,
            })
        rows.sort(key=lambda r: -r["total_value"])
        return rows

    dcb_groups = defaultdict(lambda: {"users": set(), "value": 0.0})
    for r in deposit_challenge_bonus_rows:
        d = dcb_groups[r["rule"]]
        d["users"].add(r["user_id"])
        d["value"] += r["bonus_amount"]

    dcb_claim_details = [
        {
            "user_id": r["user_id"],
            "agent": r["agent"],
            "rule": r["rule"],
            "bonus_amount": round(r["bonus_amount"], 2),
            "fd_date": r["fd_date"],
        }
        for r in sorted(deposit_challenge_bonus_rows, key=lambda r: r["fd_date"])
    ]

    wallet_rows = build_rows(by_category, use_claim_time=True)
    dcb_rows = build_rows(dcb_groups)
    return {
        "wallet_bonuses": wallet_rows,
        "deposit_challenge_bonuses": dcb_rows,
        "wallet_claim_details": wallet_claim_details,
        "deposit_challenge_bonus_claim_details": dcb_claim_details,
    }


# Weekly Cashback Shield (Action Center): loss amount Rs 5,000-2,500,000, rate
# scales linearly with what % of the week's deposit was "lost" (verified_loss
# / total_deposit) -- a single line from the 50% anchor to the 100% anchor,
# e.g. for VIP 5-15 a 65% loss earns 1.51 + (65-50)/50*3.49 = 2.56%. 100%+ is
# capped flat at the top anchor. The anchor rates depend on VIP tier: VIP 2-4
# get a lower 2%-4% range, VIP 5-15 get the wider 1.51%-5% range.
WEEKLY_CASHBACK_ANCHORS_LOW_VIP = [
    (50.0, 0.02),
    (100.0, 0.04),
]
WEEKLY_CASHBACK_ANCHORS_HIGH_VIP = [
    (50.0, 0.0151),
    (100.0, 0.05),
]
WEEKLY_CASHBACK_LOW_VIP_MAX = 4
WEEKLY_CASHBACK_MIN_LOSS = 5000.0
WEEKLY_CASHBACK_MAX_LOSS = 2500000.0
WEEKLY_CASHBACK_MIN_VIP = 2

# A separate, smaller-loss tier: Rs 500 up to (not including) the Rs 5,000
# floor above gets a flat 1.5% cashback -- but only if that loss is ALSO at
# least 80% of that week's deposit (a stricter bar than the 50% floor used
# by the 3 tiers above).
WEEKLY_CASHBACK_SMALL_LOSS_MIN = 500.0
WEEKLY_CASHBACK_SMALL_LOSS_MIN_PCT = 80.0
WEEKLY_CASHBACK_SMALL_LOSS_PCT = 0.015


def weekly_cashback_tier_pct(loss_pct, vip):
    """Piecewise-linear cashback rate between the anchor points for this
    VIP's tier (VIP 2-4 use the lower 2%-4% range, VIP 5+ use the wider
    1.51%-5% range). Below the lowest anchor (50%) isn't eligible for this
    path (returns None); at/above the highest anchor (100%) is capped flat
    at the top rate."""
    anchors = WEEKLY_CASHBACK_ANCHORS_LOW_VIP if vip <= WEEKLY_CASHBACK_LOW_VIP_MAX else WEEKLY_CASHBACK_ANCHORS_HIGH_VIP
    if loss_pct < anchors[0][0]:
        return None
    if loss_pct >= anchors[-1][0]:
        return anchors[-1][1]
    for (lo_pct, lo_cb), (hi_pct, hi_cb) in zip(anchors, anchors[1:]):
        if lo_pct <= loss_pct < hi_pct:
            frac = (loss_pct - lo_pct) / (hi_pct - lo_pct)
            return lo_cb + frac * (hi_cb - lo_cb)
    return None


def weekly_cashback_week_range(now):
    """Sunday-to-Saturday week window, matching the promo's own "credited
    every Sunday morning" cadence. Normally the Sun-Sat week containing
    `now`, EXCEPT on the cutover day itself (Sunday) before 22:00 IST --
    there, the dashboard keeps showing the just-completed week so admins
    have all Sunday morning/afternoon to review it before the display
    switches to tracking the new (barely-started) week."""
    today = now.date()
    days_since_sunday = (today.weekday() + 1) % 7  # Python: Monday=0 .. Sunday=6
    this_week_start = today - timedelta(days=days_since_sunday)
    if today == this_week_start and now.time() < dtime(22, 0):
        week_start = this_week_start - timedelta(days=7)
    else:
        week_start = this_week_start
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def weekly_cashback_shield(mconn, deposit_rows, withdrawal_rows, agent_by_user, now):
    """Weekly loss-protection cashback: for each user who deposited during
    the displayed Sun-Sat week (see weekly_cashback_week_range), verified
    loss = total_deposit - total_withdraw - CURRENT wallet balance -- money
    that came in this week and isn't sitting in their wallet or already
    paid back out, i.e. spent on betting activity. Only VIP level 2 and
    above are eligible (WEEKLY_CASHBACK_MIN_VIP). Two eligibility paths:
      - loss Rs 500-4,999.99: flat 1.5% cashback, but only if that's ALSO at
        least 80% of what they deposited that week.
      - loss Rs 5,000-2,500,000: needs to ALSO be at least 50% of what they
        deposited that week -- cashback rate scales linearly with loss %,
        VIP 2-4 capped at 4% and VIP 5-15 capped at 5% (see
        WEEKLY_CASHBACK_ANCHORS_LOW_VIP / _HIGH_VIP).
    Only lists users who actually qualify this week, same convention as
    the other bonus/retention sections on this dashboard -- not a full
    audit of every depositor."""
    week_start, week_end = weekly_cashback_week_range(now)

    deposit_by_user = defaultdict(float)
    for pay_channel, order_amount, create_time, update_time, status, user_id, is_first_deposit in deposit_rows:
        if status != "COMPLETE" or user_id is None or not create_time:
            continue
        dt = parse_dt(create_time)
        if dt and week_start <= dt.date() <= week_end:
            deposit_by_user[user_id] += order_amount or 0.0

    withdraw_by_user = defaultdict(float)
    for withdraw_amount, create_time, status, user_id, *_rest in withdrawal_rows:
        if status != 2 or user_id is None or not create_time:
            continue
        dt = parse_dt(create_time)
        if dt and week_start <= dt.date() <= week_end:
            withdraw_by_user[user_id] += withdraw_amount or 0.0

    user_ids = list(deposit_by_user.keys())
    vip_by_user, balance_by_user = {}, {}
    if user_ids:
        placeholders = ",".join("?" * len(user_ids))
        for uid, vip, bal in mconn.execute(
            f"SELECT user_id, vip_level, user_balance FROM users WHERE user_id IN ({placeholders})", user_ids
        ).fetchall():
            vip_by_user[uid] = vip
            balance_by_user[uid] = bal or 0.0

    rows = []
    for user_id, total_deposit in deposit_by_user.items():
        vip = vip_by_user.get(user_id)
        if vip is None or vip < WEEKLY_CASHBACK_MIN_VIP:
            continue
        total_withdraw = withdraw_by_user.get(user_id, 0.0)
        balance = balance_by_user.get(user_id, 0.0)
        verified_loss = total_deposit - total_withdraw - balance
        if WEEKLY_CASHBACK_SMALL_LOSS_MIN <= verified_loss < WEEKLY_CASHBACK_MIN_LOSS:
            loss_pct = (verified_loss / total_deposit * 100) if total_deposit else 0.0
            if loss_pct < WEEKLY_CASHBACK_SMALL_LOSS_MIN_PCT:
                continue
            cashback_pct = WEEKLY_CASHBACK_SMALL_LOSS_PCT
        elif WEEKLY_CASHBACK_MIN_LOSS <= verified_loss <= WEEKLY_CASHBACK_MAX_LOSS:
            loss_pct = (verified_loss / total_deposit * 100) if total_deposit else 0.0
            cashback_pct = weekly_cashback_tier_pct(loss_pct, vip)
            if cashback_pct is None:
                continue
        else:
            continue
        rows.append({
            "user_id": user_id,
            "agent": agent_for(agent_by_user, user_id),
            "vip": vip_by_user.get(user_id),
            "total_deposit": round(total_deposit, 2),
            "total_withdraw": round(total_withdraw, 2),
            "user_balance": round(balance, 2),
            "verified_loss": round(verified_loss, 2),
            "loss_pct": round(loss_pct, 2),
            "eligible_pct": round(cashback_pct * 100, 2),
            "bonus_amount": round(verified_loss * cashback_pct, 2),
        })
    rows.sort(key=lambda r: -r["bonus_amount"])

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "eligible_count": len(rows),
        "total_bonus": round(sum(r["bonus_amount"] for r in rows), 2),
        # Unlike the other Action Center sections (which cap at
        # ACTION_CENTER_LIST_CAP since they're exploratory "top N" views),
        # this is a definitive payout list -- every eligible user needs to
        # be visible and exportable, not just the top 500 by bonus amount.
        "rows": rows,
    }


# Powers the "Performance" leaderboard: for each agent, per criterion, how
# much they achieved vs a daily target. Two shapes:
#   "count" -- a flat per-day headcount target (e.g. 7 reactivations/day).
#     Stored per day as (actual_count, target_count) so a date range just
#     sums both sides: pct = SUM(actual) / SUM(target) * 100.
#   "rate"  -- a percentage-of-cohort target (e.g. 30% retention). Stored
#     per day as (converted_count, cohort_size) -- NEVER the target itself
#     -- so a date range sums the raw counts and recomputes the TRUE
#     weighted rate (SUM(converted) / SUM(cohort) * 100), rather than
#     naively averaging daily percentages, which would be wrong whenever
#     cohort size varies day to day. That weighted rate is then compared
#     against the flat target here to get "% of target achieved".
AGENT_PERF_TARGETS = {
    "Reactivation Low": {"type": "count", "target": 25},
    "Reactivation High": {"type": "count", "target": 5},
    "Retention": {"type": "rate", "target": 30},
    "Low VIP Upgrade": {"type": "count", "target": 10},
    "High VIP Upgrade": {"type": "count", "target": 5},
    "Low Premium Active": {"type": "rate", "target": 35},
    "High Premium Active": {"type": "rate", "target": 35},
    "FD 2-5 Days Conversion": {"type": "rate", "target": 30},
}

AGENT_PERF_RETENTION_DAYS = 35

# Departments the Performance page's Monthly Leaderboard and Daily/Range
# Performance sections are scored within -- each department groups the
# categories it owns; every agent is scored in every department, but
# obviously only earns nonzero numbers on the categories that actually
# apply to them (e.g. someone with no Reactivation-eligible users just
# shows "No users assigned" there, same as always). "agents": None means
# "the full agent_list," filled in at report-build time in main() since
# the roster itself isn't known until then.
AGENT_PERF_DEPARTMENTS = {
    "FTD Team": {
        "agents": None,
        # Two separate targets: Retention (FD was yesterday) and FD 2-5
        # Days Conversion (FD was 2-5 days ago, no deposit since) -- kept
        # as distinct criteria rather than merged, so each cohort's own
        # conversion rate is visible on its own.
        "categories": ["Retention", "FD 2-5 Days Conversion"],
    },
    "Reactivation Team": {
        "agents": None,
        "categories": ["Reactivation Low", "Reactivation High"],
    },
    "VIP Team": {
        "agents": None,
        "categories": ["Low Premium Active", "High Premium Active"],
    },
    "General": {
        "agents": None,
        "categories": ["Low VIP Upgrade", "High VIP Upgrade"],
    },
}


def compute_agent_performance_rows(
    agent_list, reactivation, vip_upgrade, retention, no_return_conversion, premium_active, date_str
):
    """One (date, agent, category, numerator, denominator) row per agent per
    the Performance-page criteria, for TODAY specifically -- upserted into
    master_userlist.db's agent_performance table by main(). See
    AGENT_PERF_TARGETS for what numerator/denominator mean per category.

    `retention` here is specifically first_deposit_retention's result (by
    user request: the Performance page's "Retention" criterion is
    First-Deposit retention only, not combined with Bonus-Claimer retention,
    which has no Low/High split to begin with) -- FTD Team's first target,
    cohort = FD was yesterday.

    `no_return_conversion` is no_return_fd_conversion's result -- FTD
    Team's second target ("FD 2-5 Days Conversion"), cohort = FD was 2-5
    days ago with no deposit since. Kept as its own separate criterion
    rather than merged with Retention, even though the two cohorts are
    disjoint by construction (FD yesterday vs. FD 2-5 days ago)."""
    rows = []

    count_sources = {
        "Reactivation Low": reactivation["low"]["agent_breakdown"] if reactivation else {},
        "Reactivation High": reactivation["high"]["agent_breakdown"] if reactivation else {},
        "Low VIP Upgrade": vip_upgrade["low"]["agent_breakdown"] if vip_upgrade else {},
        "High VIP Upgrade": vip_upgrade["high"]["agent_breakdown"] if vip_upgrade else {},
    }
    for category, breakdown in count_sources.items():
        target = AGENT_PERF_TARGETS[category]["target"]
        for agent in agent_list:
            rows.append((date_str, agent, category, breakdown.get(agent, 0), target))

    ret_cohort = retention.get("cohort_by_agent", {}) if retention else {}
    ret_converted = retention.get("converted_by_agent", {}) if retention else {}
    for agent in agent_list:
        rows.append((date_str, agent, "Retention", ret_converted.get(agent, 0), ret_cohort.get(agent, 0)))

    nr_cohort = no_return_conversion.get("cohort_by_agent", {}) if no_return_conversion else {}
    nr_converted = no_return_conversion.get("converted_by_agent", {}) if no_return_conversion else {}
    for agent in agent_list:
        cohort = nr_cohort.get(agent, 0)
        converted = nr_converted.get(agent, 0)
        rows.append((date_str, agent, "FD 2-5 Days Conversion", converted, cohort))

    for tier_label, category in [("low", "Low Premium Active"), ("high", "High Premium Active")]:
        tier = premium_active.get(tier_label, {}) if premium_active else {}
        cohort_by_agent = tier.get("cohort_by_agent", {})
        converted_by_agent = tier.get("converted_by_agent", {})
        for agent in agent_list:
            rows.append((date_str, agent, category, converted_by_agent.get(agent, 0), cohort_by_agent.get(agent, 0)))

    return rows


def slugify(name):
    """Turns an agent name into a clean R2 object key / URL segment,
    e.g. "Sathya (WFH)" -> "sathya-wfh". The dashboard's per-agent URLs use
    the real name (URL-encoded, reversible with decodeURIComponent) rather
    than this slug -- this is only for the R2 filename, so parens/spaces in
    agent names don't end up in object keys."""
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "agent"


def build_agent_home_report(
    agent_name, all_records, by_date_records, all_withdrawals, by_date_withdrawals,
    all_withdrawal_full, by_date_withdrawal_full, all_bet_users, by_date_bet_users,
    all_dates, city_by_user, vip_by_user, agent_by_user, now,
):
    """Small supplementary per-agent JSON, uploaded alongside (not instead
    of) the main deposit_report.json -- reports/agent/<slugify(name)>.json.

    Only the Home page's aggregate charts (amount-range/channel/hourly/
    success-rate breakdowns) and the Analytics page's Region/VIP chart
    genuinely need this: they're derived from raw per-transaction records
    that are never shipped to the browser (only pre-aggregated summaries
    are), so there's no way to scope them to one agent client-side. Every
    OTHER per-user section (Action Center, Retention, VIP Upgrade,
    Reactivation, Premium Active, Weekly Cashback Shield, withdrawal
    orders) already carries an "agent" field per row in the main report and
    is scoped entirely client-side instead -- no duplication needed there.

    Reuses the exact same aggregate()/summarize()/withdrawal_*() functions
    the main report uses, just called again on this agent's own subset of
    records -- same math, smaller input, not a separate pipeline."""
    def flt(records):
        return [r for r in records if r["agent"] == agent_name]

    agent_all_records = flt(all_records)
    agent_all_withdrawals = flt(all_withdrawals)
    agent_all_withdrawal_full = flt(all_withdrawal_full)
    # all_bet_users/by_date_bet_users are plain sets of user_ids (from wallet
    # activity, no per-row "agent" field of their own) -- scope via
    # agent_by_user directly instead of the flt() row-filter above.
    agent_bet_users_all = {uid for uid in all_bet_users if agent_for(agent_by_user, uid) == agent_name}

    by_date_records_agent = {d: flt(rows) for d, rows in by_date_records.items()}
    by_date_withdrawals_agent = {d: flt(rows) for d, rows in by_date_withdrawals.items()}
    by_date_withdrawal_full_agent = {d: flt(rows) for d, rows in by_date_withdrawal_full.items()}

    return_users_by_date_agent = compute_return_users(by_date_records_agent, all_dates)
    by_date_out = {
        date: {
            **aggregate(by_date_records_agent.get(date, [])),
            "summary": summarize(
                by_date_records_agent.get(date, []), by_date_withdrawals_agent.get(date, []),
                by_date_bet_users.get(date, set()) & agent_bet_users_all,
                return_users_by_date_agent.get(date),
            ),
            "withdrawal_review_by_channel": withdrawal_review_by_channel(by_date_withdrawal_full_agent.get(date, [])),
            "withdrawal_completion_by_channel": withdrawal_completion_by_channel(by_date_withdrawal_full_agent.get(date, [])),
        }
        for date in all_dates
    }

    withdrawal_analysis_out = {
        "processing_time_buckets": PROCESSING_TIME_BUCKETS,
        "processing_backlog_buckets": PROCESSING_BACKLOG_BUCKETS,
        "inreview_backlog_buckets": INREVIEW_BACKLOG_BUCKETS,
        "processing_backlog": withdrawal_backlog(agent_all_withdrawal_full, now, 1, processing_backlog_bucket, PROCESSING_BACKLOG_BUCKETS),
        "inreview_backlog": withdrawal_backlog(agent_all_withdrawal_full, now, 0, inreview_backlog_bucket, INREVIEW_BACKLOG_BUCKETS),
        "amount_range_buckets": AMOUNT_RANGE_BUCKETS,
        "processing_amount_range_matrix": withdrawal_amount_range_aging_matrix(
            agent_all_withdrawal_full, now, 1, amount_range_bucket, AMOUNT_RANGE_BUCKETS, processing_backlog_bucket, PROCESSING_BACKLOG_BUCKETS
        ),
        "backlog_as_of": now.isoformat(),
        "last4days_completion": last4days_completion(by_date_withdrawal_full_agent, all_dates),
    }

    return {
        "agent_name": agent_name,
        "all_time": {
            **aggregate(agent_all_records),
            "summary": summarize(agent_all_records, agent_all_withdrawals, agent_bet_users_all),
            "withdrawal_review_by_channel": withdrawal_review_by_channel(agent_all_withdrawal_full),
            "withdrawal_completion_by_channel": withdrawal_completion_by_channel(agent_all_withdrawal_full),
        },
        "by_date": by_date_out,
        "withdrawal_analysis": withdrawal_analysis_out,
        "region_vip_analytics": region_vip_deposit_analytics(
            by_date_records_agent, by_date_withdrawals_agent, city_by_user, vip_by_user, all_dates
        ),
    }


def main():
    # Source timestamps (create_time, last_active_time, etc.) are IST, but this
    # script runs on a UTC-clocked GitHub Actions runner -- datetime.now() would
    # be ~5.5h behind IST, making very recent activity look like it's in the
    # future (negative inactive_days/hours). Compute "now" in IST to match.
    now = datetime.utcnow() + timedelta(hours=5, minutes=30)

    # Banned users (dashboard's Ban User feature) must be invisible in every
    # report/search-index/export, but their real records are never deleted
    # -- so report generation reads from a THROWAWAY COPY of each DB with
    # banned users' rows removed, while the ORIGINAL files (re-downloaded by
    # the caller, untouched here) keep full history intact. Only the
    # original master_userlist.db path ever gets re-uploaded to R2 (for the
    # agent_performance write further down), so nothing deleted here is
    # ever persisted.
    master_db_path = os.path.join(BASE, "master_userlist.db")
    banned_ids = ban_utils.get_banned_user_ids(master_db_path) if os.path.exists(master_db_path) else []

    report_daily_db_path = os.path.join(BASE, "daily_records_report.db")
    shutil.copyfile(DB_PATH, report_daily_db_path)
    if banned_ids:
        placeholders = ",".join("?" * len(banned_ids))
        rdconn = sqlite3.connect(report_daily_db_path)
        for table in ["deposits", "withdrawals", "wallet_transactions", "bonuses"]:
            try:
                rdconn.execute(f"DELETE FROM {table} WHERE user_id IN ({placeholders})", banned_ids)
            except sqlite3.OperationalError:
                pass
        rdconn.commit()
        rdconn.close()

    report_master_db_path = None
    if os.path.exists(master_db_path):
        report_master_db_path = os.path.join(BASE, "master_userlist_report.db")
        shutil.copyfile(master_db_path, report_master_db_path)
        if banned_ids:
            placeholders = ",".join("?" * len(banned_ids))
            rmconn = sqlite3.connect(report_master_db_path)
            for table in ["users", "agent_assignments", "balance_adjustments"]:
                try:
                    rmconn.execute(f"DELETE FROM {table} WHERE user_id IN ({placeholders})", banned_ids)
                except sqlite3.OperationalError:
                    pass
            rmconn.commit()
            rmconn.close()

    conn = sqlite3.connect(report_daily_db_path)
    cur = conn.cursor()

    deposit_rows = cur.execute(
        "SELECT pay_channel, order_amount, create_time, update_time, status, user_id, is_first_deposit FROM deposits"
    ).fetchall()
    withdrawal_rows = cur.execute(
        "SELECT withdraw_amount, create_time, status, user_id, payment_channel, review_time, update_time, order_no, "
        "payment_center_order_id FROM withdrawals"
    ).fetchall()
    wallet_rows = cur.execute(
        "SELECT user_id, create_time FROM wallet_transactions WHERE user_id IS NOT NULL"
    ).fetchall()
    # Actual game plays only -- excludes bonus payouts, same definition as
    # build_recent_activity_by_user's "games played" query -- used by
    # suspicious_withdraw_users() below.
    game_play_rows = cur.execute(
        "SELECT user_id, create_time FROM wallet_transactions "
        "WHERE game_name IS NOT NULL AND game_name != '' AND user_id IS NOT NULL "
        "AND id NOT IN (SELECT id FROM bonuses)"
    ).fetchall()
    channel_performance = channel_performance_report(conn, now.date())
    recent_activity = build_recent_activity_by_user(conn, now.date())
    conn.close()

    by_date_bet_users = defaultdict(set)
    all_bet_users = set()
    for user_id, create_time in wallet_rows:
        all_bet_users.add(user_id)
        create_dt = parse_dt(create_time)
        if create_dt:
            by_date_bet_users[create_dt.strftime("%Y-%m-%d")].add(user_id)

    total_registered_users = None
    vip_by_user = {}
    city_by_user = {}
    agent_by_user = {}
    action_center = None
    weekly_cashback = None
    reactivation = None
    vip_upgrade = None
    performance = None
    profit_users = None
    if report_master_db_path:
        mconn = sqlite3.connect(report_master_db_path)
        total_registered_users = mconn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        vip_by_user = dict(mconn.execute("SELECT user_id, vip_level FROM users").fetchall())
        city_by_user = dict(mconn.execute("SELECT user_id, city FROM users").fetchall())
        try:
            agent_by_user = dict(mconn.execute("SELECT user_id, agent_name FROM agent_assignments").fetchall())
        except sqlite3.OperationalError:
            agent_by_user = {}  # table doesn't exist yet -- pre-dates this feature
        action_center = action_center_reports(mconn, now, agent_by_user)
        weekly_cashback = weekly_cashback_shield(mconn, deposit_rows, withdrawal_rows, agent_by_user, now)
        fallback_creds = load_creds()
        reactivation_candidates_path = os.path.join(BASE, "reactivation_candidates.json")
        reactivation_candidates = load_json_with_r2_fallback(
            reactivation_candidates_path, "reports/reactivation_candidates.json", fallback_creds, []
        )
        reactivation = deposit_reactivation_analytics(mconn, reactivation_candidates, action_center, agent_by_user)
        vip_upgrade_path = os.path.join(BASE, "vip_upgrade_candidates.json")
        vip_upgrade_candidates = load_json_with_r2_fallback(
            vip_upgrade_path, "reports/vip_upgrade_candidates.json", fallback_creds, {"low": [], "high": []}
        )
        vip_upgrade = vip_upgrade_analytics(vip_upgrade_candidates, action_center, agent_by_user)

        # Conversion funnels (3-day/7-day: of users near-upgrade/inactive N
        # days ago, how many have since converted) -- computed once/day by
        # api_pull_ingest.py's sync_master_userlist and persisted directly in
        # master_userlist.db, so this is just a cheap read, not a recompute.
        try:
            funnel_row = mconn.execute("SELECT data FROM funnel_stats").fetchone()
        except sqlite3.OperationalError:
            funnel_row = None  # table doesn't exist yet -- pre-dates this feature
        if funnel_row:
            funnel_data = json.loads(funnel_row[0])
            reactivation["funnel"] = funnel_data.get("reactivation")
            vip_upgrade["funnel"] = funnel_data.get("vip_upgrade")

        performance = performance_history(mconn)
        profit_users = profit_users_of_the_day(mconn, deposit_rows, withdrawal_rows, now, agent_by_user)
        build_and_upload_user_search_index(mconn, recent_activity, load_creds(), agent_by_user)

        mconn.close()

    suspicious_withdraw = suspicious_withdraw_users(deposit_rows, withdrawal_rows, game_play_rows, now, agent_by_user, vip_by_user)

    by_date_records = defaultdict(list)
    all_records = []
    by_date_withdrawals = defaultdict(list)
    all_withdrawals = []
    latest_record_time = None

    for pay_channel, order_amount, create_time, update_time, status, user_id, is_first_deposit in deposit_rows:
        channel = pay_channel or "Unknown"
        amount = order_amount or 0.0
        date_str, hour = None, None
        create_dt = parse_dt(create_time)
        if create_dt:
            date_str, hour = create_dt.strftime("%Y-%m-%d"), create_dt.hour
            if latest_record_time is None or create_dt > latest_record_time:
                latest_record_time = create_dt

        completion_minutes = None
        if status == "COMPLETE":
            update_dt = parse_dt(update_time)
            if create_dt and update_dt:
                completion_minutes = max((update_dt - create_dt).total_seconds() / 60.0, 0)

        record = {
            "channel": channel,
            "amount": amount,
            "hour": hour,
            "status": status,
            "completion_minutes": completion_minutes,
            "user_id": user_id,
            "agent": agent_for(agent_by_user, user_id),
        }
        all_records.append(record)
        if date_str:
            by_date_records[date_str].append(record)

    by_date_withdrawal_full = defaultdict(list)
    all_withdrawal_full = []

    for withdraw_amount, create_time, status, user_id, payment_channel, review_time, update_time, order_no, payment_center_order_id in withdrawal_rows:
        amount = withdraw_amount or 0.0
        create_dt = parse_dt(create_time)
        date_str = create_dt.strftime("%Y-%m-%d") if create_dt else None
        if create_dt and (latest_record_time is None or create_dt > latest_record_time):
            latest_record_time = create_dt
        record = {"amount": amount, "status": status, "user_id": user_id, "agent": agent_for(agent_by_user, user_id)}
        all_withdrawals.append(record)
        if date_str:
            by_date_withdrawals[date_str].append(record)

        full_record = {
            "channel": payment_channel or "Unknown",
            "status": status,
            "create_dt": create_dt,
            "review_dt": parse_dt(review_time),
            "update_dt": parse_dt(update_time),
            "order_no": order_no,
            "payment_center_order_id": payment_center_order_id,
            "user_id": user_id,
            "amount": amount,
            "agent": agent_for(agent_by_user, user_id),
        }
        all_withdrawal_full.append(full_record)
        if date_str:
            by_date_withdrawal_full[date_str].append(full_record)

    all_dates = sorted(set(by_date_records.keys()) | set(by_date_withdrawals.keys()))
    return_users_by_date = compute_return_users(by_date_records, all_dates)
    by_date = {
        date: {
            **aggregate(by_date_records.get(date, [])),
            "summary": summarize(
                by_date_records.get(date, []), by_date_withdrawals.get(date, []), by_date_bet_users.get(date, set()),
                return_users_by_date.get(date),
            ),
            "withdrawal_review_by_channel": withdrawal_review_by_channel(by_date_withdrawal_full.get(date, [])),
            "withdrawal_completion_by_channel": withdrawal_completion_by_channel(by_date_withdrawal_full.get(date, [])),
            "withdrawal_orders": withdrawal_orders_export(by_date_withdrawal_full.get(date, []), vip_by_user, now, agent_by_user),
            "top_depositors": top_depositors(by_date_records.get(date, []), by_date_withdrawals.get(date, [])),
        }
        for date in all_dates
    }

    withdrawal_analysis = {
        "processing_time_buckets": PROCESSING_TIME_BUCKETS,
        "processing_backlog_buckets": PROCESSING_BACKLOG_BUCKETS,
        "inreview_backlog_buckets": INREVIEW_BACKLOG_BUCKETS,
        "processing_backlog": withdrawal_backlog(all_withdrawal_full, now, 1, processing_backlog_bucket, PROCESSING_BACKLOG_BUCKETS),
        "inreview_backlog": withdrawal_backlog(all_withdrawal_full, now, 0, inreview_backlog_bucket, INREVIEW_BACKLOG_BUCKETS),
        "amount_range_buckets": AMOUNT_RANGE_BUCKETS,
        "processing_amount_range_matrix": withdrawal_amount_range_aging_matrix(
            all_withdrawal_full, now, 1, amount_range_bucket, AMOUNT_RANGE_BUCKETS, processing_backlog_bucket, PROCESSING_BACKLOG_BUCKETS
        ),
        "backlog_as_of": now.isoformat(),
        "last4days_completion": last4days_completion(by_date_withdrawal_full, all_dates),
    }

    today_str = now.date().isoformat()
    yesterday_str = (now.date() - timedelta(days=1)).isoformat()
    withdrawal_amount_range_by_day = {
        "today": withdrawal_amount_range_day_report(by_date_withdrawal_full.get(today_str, []), today_str),
        "yesterday": withdrawal_amount_range_day_report(by_date_withdrawal_full.get(yesterday_str, []), yesterday_str),
    }

    deposit_challenge_bonus_rows = deposit_challenge_bonus(deposit_rows, build_deposit_day_stats(deposit_rows), now.date(), agent_by_user)
    action_center_extra = {
        "yesterday_first_deposit_users": yesterday_first_deposit_users(deposit_rows, all_withdrawal_full, vip_by_user, city_by_user, now.date(), agent_by_user),
        "no_return_fd_users": no_return_fd_users(deposit_rows, all_withdrawal_full, agent_by_user, now.date()),
    }

    retention = {
        "first_deposit": first_deposit_retention(deposit_rows, city_by_user, now.date(), agent_by_user),
        "no_return_fd_conversion": no_return_fd_conversion(deposit_rows, city_by_user, agent_by_user, now.date()),
    }

    premium_active = None
    if report_master_db_path:
        mconn3 = sqlite3.connect(report_master_db_path)
        premium_active = premium_active_conversion(mconn3, deposit_rows, now, agent_by_user)
        mconn3.close()

    # Bonus Claim Report date filter: bonus_rows_all is fetched ONCE and
    # reused across every retained date (cheap -- `bonuses` is a small
    # table, a subset of wallet_transactions), and deposit_challenge_bonus()
    # is recomputed per date since it's a same-day payout calculation, not
    # a stored table. Both feed bonus_claim_report() once per date in
    # all_dates, same "compute per date, ship the whole rolling window"
    # pattern already used for agent_performance/premium_active.
    bonus_daily_conn = sqlite3.connect(report_daily_db_path)
    try:
        bonus_rows_all = bonus_daily_conn.execute(
            "SELECT matched_category, user_id, change_value, create_time FROM bonuses"
        ).fetchall()
    except sqlite3.OperationalError:
        bonus_rows_all = []  # bonuses table doesn't exist yet
    bonus_daily_conn.close()

    deposit_day_stats = build_deposit_day_stats(deposit_rows)
    dcb_rows_by_date = {}
    bonus_claims_by_date = {}
    for date_str in all_dates:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        dcb_rows_for_date = deposit_challenge_bonus_rows if d == now.date() else deposit_challenge_bonus(deposit_rows, deposit_day_stats, d, agent_by_user)
        dcb_rows_by_date[date_str] = dcb_rows_for_date
        bonus_claims_by_date[date_str] = bonus_claim_report(bonus_rows_all, deposit_rows, dcb_rows_for_date, {date_str}, agent_by_user)
    bonus_claims = bonus_claims_by_date.get(now.date().isoformat(), {
        "wallet_bonuses": [], "deposit_challenge_bonuses": [],
        "wallet_claim_details": [], "deposit_challenge_bonus_claim_details": [],
    })

    # Week/Month views: rolling window ENDING at each retained date, clipped
    # to whatever's actually in all_dates (the 33-day retention window), so
    # e.g. "Month" on an early date just covers however much history exists.
    all_dates_set = set(all_dates)

    def rolling_window(end_date_str, days):
        end_d = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        return {(end_d - timedelta(days=i)).isoformat() for i in range(days)} & all_dates_set

    # Week/Month bonus claims are precomputed for EVERY retained date (so the
    # date-switch buttons can show any date instantly) -- but each date's
    # 7/30-day window heavily overlaps the next date's, so the per-instance
    # claim_details lists were duplicating ~97% of their rows across
    # adjacent dates. Confirmed via measurement: wallet_claim_details alone
    # was 171MB of a 401MB report (month view) plus another ~107MB in the
    # week view, making the dashboard's main JSON too large to reliably
    # parse in a browser tab. The on-screen table only ever reads the
    # category-level summary rows (wallet_bonuses/deposit_challenge_bonuses)
    # regardless of range -- per-instance detail is only used by the Day
    # view's Excel export -- so Week/Month strip the detail lists here and
    # keep only the summary, cutting the report back to a safe size. Day
    # view (bonus_claims_by_date, below) is untouched and keeps full detail.
    bonus_claims_by_week = {}
    bonus_claims_by_month = {}
    for date_str in all_dates:
        week_dates = rolling_window(date_str, 7)
        month_dates = rolling_window(date_str, 30)
        week_dcb_rows = [r for d in week_dates for r in dcb_rows_by_date.get(d, [])]
        month_dcb_rows = [r for d in month_dates for r in dcb_rows_by_date.get(d, [])]
        week_report = bonus_claim_report(bonus_rows_all, deposit_rows, week_dcb_rows, week_dates, agent_by_user)
        month_report = bonus_claim_report(bonus_rows_all, deposit_rows, month_dcb_rows, month_dates, agent_by_user)
        week_report["wallet_claim_details"] = []
        week_report["deposit_challenge_bonus_claim_details"] = []
        month_report["wallet_claim_details"] = []
        month_report["deposit_challenge_bonus_claim_details"] = []
        bonus_claims_by_week[date_str] = week_report
        bonus_claims_by_month[date_str] = month_report

    new_old_user_analysis = new_vs_old_user_analysis(deposit_rows, withdrawal_rows, all_dates, now.date())
    weekly_performance = weekly_performance_report(new_old_user_analysis["daily"], new_old_user_analysis["retention"], now.date())

    games_daily_conn = sqlite3.connect(report_daily_db_path)
    games_master_conn = sqlite3.connect(report_master_db_path) if report_master_db_path else None
    new_users_games = top_games_new_users(games_daily_conn, games_master_conn, deposit_rows, agent_by_user, all_dates, now.date())
    games_daily_conn.close()
    if games_master_conn is not None:
        games_master_conn.close()

    region_vip_matrix = region_vip_depositor_matrix(deposit_rows, city_by_user, vip_by_user, all_dates)

    roller_reports = {"high_roller": [], "low_roller": []}
    if report_master_db_path:
        roller_daily_conn = sqlite3.connect(report_daily_db_path)
        roller_master_conn = sqlite3.connect(report_master_db_path)
        roller_reports = high_low_roller_reports(roller_master_conn, roller_daily_conn, agent_by_user, now.date())
        roller_daily_conn.close()
        roller_master_conn.close()

    # Persist today's per-agent performance, then read back the full rolling
    # window for the Performance page -- small enough (agents x 7 categories
    # x up to 35 days) to ship in full and let the frontend do date-range
    # filtering/aggregation client-side, same pattern as premium_active etc.
    agent_list = sorted(set(agent_by_user.values()))
    agent_performance_rows = []
    if os.path.exists(master_db_path) and agent_list:
        mconn4 = sqlite3.connect(master_db_path)
        mconn4.execute(
            "CREATE TABLE IF NOT EXISTS agent_performance ("
            "date TEXT, agent_name TEXT, category TEXT, numerator REAL, denominator REAL, "
            "PRIMARY KEY (date, agent_name, category))"
        )
        upsert_rows = compute_agent_performance_rows(
            agent_list, reactivation, vip_upgrade, retention["first_deposit"], retention["no_return_fd_conversion"],
            premium_active, now.date().isoformat()
        )
        mconn4.executemany(
            "INSERT OR REPLACE INTO agent_performance (date, agent_name, category, numerator, denominator) "
            "VALUES (?, ?, ?, ?, ?)",
            upsert_rows,
        )
        # Rolling 35-day retention -- ISO date strings compare lexicographically,
        # so a plain string cutoff works without parsing.
        cutoff = (now.date() - timedelta(days=AGENT_PERF_RETENTION_DAYS)).isoformat()
        mconn4.execute("DELETE FROM agent_performance WHERE date < ?", (cutoff,))
        mconn4.commit()
        agent_performance_rows = mconn4.execute(
            "SELECT date, agent_name, category, numerator, denominator FROM agent_performance ORDER BY date"
        ).fetchall()
        mconn4.close()
        # CRITICAL: this function never uploads master_userlist.db anywhere
        # else (every other write to it happens in api_pull_ingest.py /
        # ingest_update.py, which upload it themselves right after) -- so
        # without this upload, every agent_performance write above only ever
        # lands on this job's throwaway local copy. R2 itself never gains the
        # table, meaning the NEXT run downloads a copy with no history at
        # all, re-derives only TODAY's row from scratch, and "Yesterday"
        # forever falls back to today. Confirmed via check_agent_performance.py:
        # the live master_userlist.db had no agent_performance table at all,
        # despite the JSON report showing a populated array every run.
        upload_creds = load_creds()
        upload_s3 = boto3.client(
            "s3",
            endpoint_url=upload_creds["R2_ENDPOINT_URL"],
            aws_access_key_id=upload_creds["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=upload_creds["R2_SECRET_ACCESS_KEY"],
            region_name="auto",
        )
        upload_s3.upload_file(master_db_path, upload_creds["R2_BUCKET"], "master_userlist.db")
        print("Uploaded master_userlist.db (agent_performance rows persisted)")
    agent_performance = [
        {"date": d, "agent": a, "category": c, "numerator": n, "denominator": den}
        for d, a, c, n, den in agent_performance_rows
    ]

    region_vip_analytics_data = region_vip_deposit_analytics(by_date_records, by_date_withdrawals, city_by_user, vip_by_user, all_dates)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        # The exact IST calendar date used as "today" for Reactivation, VIP
        # Upgrade, and Retention -- those three sections are always scoped to
        # this date (never affected by the Region/VIP chart's date-switch,
        # which only re-renders that chart), refreshed on the next pipeline
        # run after midnight IST. Exposed so the frontend can label it
        # explicitly rather than leaving it implicit.
        "report_today": now.date().isoformat(),
        "latest_record_time": latest_record_time.isoformat() if latest_record_time else None,
        "total_registered_users": total_registered_users,
        "status_filter": "COMPLETE (success-rate sections include all statuses)",
        "amount_ranges": RANGE_LABELS[:-1],
        "dates": all_dates,
        "by_date": by_date,
        "all_time": {
            **aggregate(all_records),
            "summary": summarize(all_records, all_withdrawals, all_bet_users),
            "withdrawal_review_by_channel": withdrawal_review_by_channel(all_withdrawal_full),
            "withdrawal_completion_by_channel": withdrawal_completion_by_channel(all_withdrawal_full),
        },
        "withdrawal_analysis": withdrawal_analysis,
        "withdrawal_amount_range_by_day": withdrawal_amount_range_by_day,
        # All-dates raw order rows (unlike by_date[...].withdrawal_orders,
        # which is scoped to a single selected date) -- needed for the
        # Processing/In-Review aging charts and the Last-4-Days completed
        # chart, which all span the whole retained window, not one day.
        "withdrawal_orders_full": withdrawal_orders_export(all_withdrawal_full, vip_by_user, now, agent_by_user),
        "action_center": action_center,
        "action_center_extra": action_center_extra,
        "weekly_cashback_shield": weekly_cashback,
        "region_vip_analytics": region_vip_analytics_data,
        "reactivation": reactivation,
        "vip_upgrade": vip_upgrade,
        "retention": retention,
        "premium_active": premium_active,
        "performance_history": performance,
        "profit_users": profit_users,
        "channel_performance": channel_performance,
        "suspicious_withdraw_users": suspicious_withdraw,
        "bonus_claims": bonus_claims,
        "new_old_user_analysis": new_old_user_analysis,
        # Distinct real agent names (never includes AGENT_UNASSIGNED) -- powers
        # the Reassign Agent dropdown on the Search User page and the
        # Performance leaderboard.
        "agent_list": agent_list,
        # Rolling 35-day per-agent-per-category numerator/denominator rows --
        # the Performance page does all date-range filtering/aggregation and
        # "% of target achieved" math client-side from this.
        "agent_performance": agent_performance,
        "agent_performance_targets": AGENT_PERF_TARGETS,
        # Department -> {agents, categories} for the Performance page's
        # per-department scorecards -- "agents": None in the source dict
        # is resolved to the live agent_list here.
        "agent_performance_departments": {
            dept: {
                "agents": info["agents"] if info["agents"] is not None else agent_list,
                "categories": info["categories"],
            }
            for dept, info in AGENT_PERF_DEPARTMENTS.items()
        },
    }

    out_path = os.path.join(BASE, "deposit_report.json")
    with open(out_path, "w") as f:
        json.dump(report, f)
    completed_n = sum(1 for r in all_records if r["status"] == "COMPLETE")
    print(f"Wrote {out_path} ({completed_n}/{len(all_records)} completed deposits across {len(by_date)} dates)")

    creds = load_creds()
    s3 = boto3.client(
        "s3",
        endpoint_url=creds["R2_ENDPOINT_URL"],
        aws_access_key_id=creds["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=creds["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    s3.upload_file(out_path, creds["R2_BUCKET"], "reports/deposit_report.json")
    print(f"Uploaded reports/deposit_report.json -> r2://{creds['R2_BUCKET']}/reports/deposit_report.json")

    # Platform Analysis-only data, split into its own file -- these fields
    # are never read by Home/Action Center/Performance/Analytics/Search
    # User (confirmed: every reference to them in report_worker/src/index.js
    # sits inside the IS_PLATFORM_ANALYSIS block), so bundling them into the
    # main deposit_report.json forced every OTHER page to download and parse
    # ~80MB+ of data it never uses. The Platform Analysis page fetches this
    # as a second request alongside /data.json (see report_worker).
    platform_analysis_extra = {
        "bonus_claims_by_date": bonus_claims_by_date,
        "bonus_claims_by_week": bonus_claims_by_week,
        "bonus_claims_by_month": bonus_claims_by_month,
        "weekly_performance": weekly_performance,
        "new_users_games": new_users_games,
        "region_vip_depositor_matrix": region_vip_matrix,
        "roller_reports": roller_reports,
    }
    pa_out_path = os.path.join(BASE, "platform_analysis.json")
    with open(pa_out_path, "w") as f:
        json.dump(platform_analysis_extra, f)
    s3.upload_file(pa_out_path, creds["R2_BUCKET"], "reports/platform_analysis.json")
    print(f"Uploaded reports/platform_analysis.json -> r2://{creds['R2_BUCKET']}/reports/platform_analysis.json ({os.path.getsize(pa_out_path)/1e6:.1f} MB)")

    # Per-agent dashboards: small supplementary JSON per real agent (never
    # "Un-Assigned"), for the Home page's aggregate charts and the Analytics
    # Region/VIP chart -- see build_agent_home_report for why only those
    # need a separate file. Everything else on an agent's dashboard filters
    # the SAME main deposit_report.json client-side using its existing
    # per-row "agent" field.
    for agent_name in agent_list:
        agent_report = build_agent_home_report(
            agent_name, all_records, by_date_records, all_withdrawals, by_date_withdrawals,
            all_withdrawal_full, by_date_withdrawal_full, all_bet_users, by_date_bet_users,
            all_dates, city_by_user, vip_by_user, agent_by_user, now,
        )
        agent_out_path = os.path.join(BASE, "agent_report.json")
        with open(agent_out_path, "w") as f:
            json.dump(agent_report, f)
        agent_key = f"reports/agent/{slugify(agent_name)}.json"
        s3.upload_file(agent_out_path, creds["R2_BUCKET"], agent_key)
    print(f"Uploaded {len(agent_list)} per-agent home reports to reports/agent/*.json")

    # Tiny standalone file with just the agent name list -- lets the Worker's
    # admin-only /admin/agent-links endpoint read who's a valid agent without
    # pulling the full (100MB+) deposit_report.json into memory, which
    # exceeds a Worker's memory limit.
    agent_list_out_path = os.path.join(BASE, "agent_list.json")
    with open(agent_list_out_path, "w") as f:
        json.dump({"agent_list": agent_list}, f)
    s3.upload_file(agent_list_out_path, creds["R2_BUCKET"], "reports/agent_list.json")

    # Per-date snapshot of Analytics' Reactivation/VIP Upgrade/Retention/
    # Premium Active sections -- these are single "as of today" computations,
    # overwritten every run, so browsing to a past date on the Analytics page
    # needs its own copy of that day's numbers. Kept as a SEPARATE small R2
    # object per day (not embedded in the ~7MB main deposit_report.json)
    # so switching dates is a small on-demand fetch, matching the same
    # last-7-dates window region_vip_analytics already uses for consistency.
    today_str = now.date().isoformat()
    snapshot = {
        "date": today_str,
        "reactivation": reactivation,
        "vip_upgrade": vip_upgrade,
        "retention": retention,
        "premium_active": premium_active,
    }
    snapshot_key = f"reports/analytics_history/{today_str}.json"
    s3.put_object(Bucket=creds["R2_BUCKET"], Key=snapshot_key, Body=json.dumps(snapshot), ContentType="application/json")
    print(f"Uploaded {snapshot_key}")

    keep_dates = set(all_dates[-7:])
    listing = s3.list_objects_v2(Bucket=creds["R2_BUCKET"], Prefix="reports/analytics_history/")
    purged = 0
    for obj in listing.get("Contents", []):
        key = obj["Key"]
        obj_date = key.rsplit("/", 1)[-1].replace(".json", "")
        if obj_date not in keep_dates:
            s3.delete_object(Bucket=creds["R2_BUCKET"], Key=key)
            purged += 1
    print(f"Purged {purged} analytics_history snapshots outside the last {len(keep_dates)} dates")


if __name__ == "__main__":
    main()
