"""
Pulls deposit, withdrawal, and wallet-detail exports directly from the business
API (anmanagers.online) and ingests them, instead of waiting for a manual file
upload. Runs on a schedule via GitHub Actions (see .github/workflows/api_pull.yml).

Deposits and withdrawals: always fetch a rolling 5-day window (today - 4 days
through today, IST) since an order created days ago can still complete, fail,
or get rejected later. ingest_update.ingest_deposits/ingest_withdrawals now use
INSERT OR REPLACE, so re-fetching the same order id with an updated status
overwrites the stale row instead of being ignored.

Wallet details: single-day export. Uses `today` (IST) on every run, except the
first run after the IST calendar date has rolled over, which uses `yesterday`
once (to finalize the previous day's data) before switching to `today` for the
rest of that day. Which date was last covered is persisted in R2 at
reports/wallet_fetch_state.json so this survives across independent runs.

The API bearer token is not a GitHub secret -- it's stored in R2 at
config/business_api_token.txt and can be updated any time via the "Business
API Token" form on the upload page, without touching GitHub settings.

master_userlist.db (VIP level, total deposit, new user_ids) is also kept
current on every pull via sync_master_userlist() -- see its docstring.
"""
import datetime
import json
import os
import sqlite3
import subprocess
import sys
import time
from collections import defaultdict

import openpyxl
import requests

import ci_ingest
import ingest_update as iu

API_BASE = "https://api.anmanagers.online/prod-api/business"
PACKAGE_ID = "13"
IST_OFFSET = datetime.timedelta(hours=5, minutes=30)
TOKEN_KEY = "config/business_api_token.txt"
TOKEN_STATUS_KEY = "config/token_status.json"
WALLET_STATE_KEY = "reports/wallet_fetch_state.json"

# Cumulative deposit ("experience") required to reach each VIP level, per the
# platform's own VIP table. VIP level is purely a function of total deposit --
# never withdrawal history. Kept in sync with build_deposit_report.py's copy.
VIP_THRESHOLDS = {
    0: 0, 1: 100, 2: 600, 3: 5600, 4: 15600, 5: 95600, 6: 295600, 7: 795600,
    8: 1795600, 9: 3795600, 10: 8795600, 11: 16795600, 12: 28795600,
    13: 44795600, 14: 69795600, 15: 119795600,
}


def vip_level_for_total(total_recharge):
    total_recharge = total_recharge or 0.0
    level = 0
    for lvl, threshold in VIP_THRESHOLDS.items():
        if total_recharge >= threshold:
            level = max(level, lvl)
    return level


# Windows for the "conversion funnel" -- of users who were near-upgrade/
# inactive N days ago, how many have since converted (by today)? Kept short
# on purpose: this pipeline started collecting daily_snapshot history on
# 2026-07-02, so a 7-day window has no real data until 7 days of history
# have actually accumulated -- see compute_conversion_funnels' "insufficient
# history" handling below.
FUNNEL_WINDOWS = [3, 7]
FUNNEL_HISTORY_DAYS = max(FUNNEL_WINDOWS) + 3  # a little slack past the longest window


def compute_conversion_funnels(cur, today):
    """For each of FUNNEL_WINDOWS, and each of the 4 cohorts (VIP-upgrade
    Low/High, Reactivation Low/High), look up who qualified for that cohort
    in the daily_snapshot row from exactly N days ago, then check -- using
    each user's CURRENT vip_level/last_active_time already sitting in the
    users table -- how many have since converted. Runs once per calendar
    day (called only when the day-start snapshot is (re)created), not every
    hourly run: a single run over one day's ~334k-row snapshot per window is
    already comparable in cost to the existing per-run recompute pass, and
    cohort membership is day-granular anyway so there's nothing to gain from
    recomputing it hourly.

    Returns {window: {"low": {...}, "high": {...}}} for both "vip_upgrade"
    and "reactivation", or None for a window where the required historical
    snapshot doesn't exist yet (not enough days of history collected so
    far)."""
    result = {"vip_upgrade": {}, "reactivation": {}}
    # Fetched once, reused across every window -- "current state" doesn't
    # depend on which historical window we're comparing against.
    current = {uid: (vl, lat) for uid, vl, lat in cur.execute(
        "SELECT user_id, vip_level, last_active_time FROM users"
    ).fetchall()}
    for window in FUNNEL_WINDOWS:
        cohort_date = (today - datetime.timedelta(days=window)).isoformat()
        rows = cur.execute(
            "SELECT user_id, vip_level, total_recharge, last_active_time "
            "FROM daily_snapshot WHERE snapshot_date = ?", (cohort_date,)
        ).fetchall()
        if not rows:
            result["vip_upgrade"][window] = None
            result["reactivation"][window] = None
            continue

        vip_cohort_low = vip_conv_low = vip_cohort_high = vip_conv_high = 0
        react_cohort_low = react_conv_low = react_cohort_high = react_conv_high = 0
        for user_id, vip_level, total_recharge, last_active_time in rows:
            cur_state = current.get(user_id)
            if cur_state is None or vip_level is None:
                continue
            cur_vip, cur_last_active = cur_state
            total_recharge = total_recharge or 0.0

            if vip_level < 15 and (vip_level + 1) in VIP_THRESHOLDS:
                gap = VIP_THRESHOLDS[vip_level + 1] - total_recharge
                if 2 <= vip_level <= 4 and 1 <= gap <= 1000:
                    vip_cohort_low += 1
                    if cur_vip is not None and cur_vip > vip_level:
                        vip_conv_low += 1
                elif 5 <= vip_level <= 15 and 1 <= gap <= 50000:
                    vip_cohort_high += 1
                    if cur_vip is not None and cur_vip > vip_level:
                        vip_conv_high += 1

            if last_active_time:
                try:
                    la_date = datetime.datetime.fromisoformat(str(last_active_time).replace(" ", "T")).date()
                except ValueError:
                    la_date = None
                if la_date is not None:
                    inactive_days = (datetime.date.fromisoformat(cohort_date) - la_date).days
                    reactivated = False
                    if cur_last_active:
                        try:
                            cur_la_date = datetime.datetime.fromisoformat(str(cur_last_active).replace(" ", "T")).date()
                            reactivated = cur_la_date > la_date
                        except ValueError:
                            pass
                    if 2 <= vip_level <= 4 and 10 <= inactive_days <= 180:
                        react_cohort_low += 1
                        if reactivated:
                            react_conv_low += 1
                    elif 5 <= vip_level <= 15 and 15 <= inactive_days <= 240:
                        react_cohort_high += 1
                        if reactivated:
                            react_conv_high += 1

        def pct(n, d):
            return round(n / d * 100, 2) if d else 0.0

        result["vip_upgrade"][window] = {
            "low": {"cohort_size": vip_cohort_low, "converted": vip_conv_low, "pct": pct(vip_conv_low, vip_cohort_low)},
            "high": {"cohort_size": vip_cohort_high, "converted": vip_conv_high, "pct": pct(vip_conv_high, vip_cohort_high)},
        }
        result["reactivation"][window] = {
            "low": {"cohort_size": react_cohort_low, "converted": react_conv_low, "pct": pct(react_conv_low, react_cohort_low)},
            "high": {"cohort_size": react_cohort_high, "converted": react_conv_high, "pct": pct(react_conv_high, react_cohort_high)},
        }
    return result


def put_token_status(s3, bucket, ok, message=None):
    s3.put_object(
        Bucket=bucket, Key=TOKEN_STATUS_KEY,
        Body=json.dumps({
            "ok": ok,
            "message": message,
            "checked_at": datetime.datetime.utcnow().isoformat() + "Z",
        }).encode("utf-8"),
        ContentType="application/json",
    )


def ist_today():
    return (datetime.datetime.utcnow() + IST_OFFSET).date()


def fetch_token(s3, bucket):
    try:
        obj = s3.get_object(Bucket=bucket, Key=TOKEN_KEY)
        token = obj["Body"].read().decode("utf-8").strip()
    except Exception as e:
        put_token_status(s3, bucket, ok=False, message="update new bearer token to run the pipeline")
        print(f"FATAL: could not load business API token from r2://{bucket}/{TOKEN_KEY}: {e}", file=sys.stderr)
        print("Set it via the 'Business API Token' form on the upload page first.", file=sys.stderr)
        sys.exit(1)
    if not token:
        put_token_status(s3, bucket, ok=False, message="update new bearer token to run the pipeline")
        print(f"FATAL: business API token at r2://{bucket}/{TOKEN_KEY} is empty", file=sys.stderr)
        sys.exit(1)
    return token


def fetch_export(token, path, payload, attempts=3):
    last_err = None
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.post(
                f"{API_BASE}/{path}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data=payload,
                timeout=180,
            )
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "")
            if "spreadsheet" not in ctype and "ms-excel" not in ctype:
                raise RuntimeError(f"Unexpected response from {path} (content-type={ctype}): {resp.text[:300]}")
            return resp.content
        except Exception as e:
            last_err = e
            print(f"  fetch attempt {attempt}/{attempts} for {path} failed: {e}")
            if attempt < attempts:
                time.sleep(10 * attempt)
    raise last_err


def save_xlsx(content, name):
    path = os.path.join(ci_ingest.BASE, name)
    with open(path, "wb") as f:
        f.write(content)
    return path


def get_wallet_state(s3, bucket):
    try:
        obj = s3.get_object(Bucket=bucket, Key=WALLET_STATE_KEY)
        return json.loads(obj["Body"].read())
    except Exception:
        return {}


def put_wallet_state(s3, bucket, state):
    s3.put_object(Bucket=bucket, Key=WALLET_STATE_KEY, Body=json.dumps(state).encode("utf-8"),
                   ContentType="application/json")


def extract_deposit_user_info(deposit_path):
    """user_id -> {phone, channel, register_time, city, create_time} from a
    water/export xlsx (column order: ... userPhone[14], channel[15], ...,
    userRegisterTime[17], ..., RegisterCity[23], ..., createTime[32], ...)."""
    wb = openpyxl.load_workbook(deposit_path, read_only=True)
    ws = wb.active
    info = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        user_id = row[3]
        if user_id is None:
            continue
        info[int(user_id)] = {
            "phone": row[14],
            "channel": row[15],
            "register_time": row[17],
            "city": row[23],
            "create_time": row[32],
        }
    wb.close()
    return info


def compute_and_save_daily_performance(cur, deposit_rows, withdrawal_rows, today):
    """Permanent daily rollup (total_deposit, total_withdrawal, net_revenue,
    unique depositors/withdrawers, order counts) -- unlike daily_records.db's
    deposits/withdrawals tables, this table is NEVER purged, so no day's
    performance is ever lost once its row-level detail ages past the 33-day
    window.

    Called once per day (on the day-rollover trigger), it re-derives and
    UPSERTs every date currently present in deposit_rows/withdrawal_rows
    (both passed in as the FULL currently-retained history, up to 33 days --
    not date-filtered) except today (still accumulating, not finalized).
    Re-deriving every retained date each time, rather than only inserting
    brand-new ones, lets a historical day's totals keep correcting themselves
    for as long as its source rows are still around -- e.g. a withdrawal
    created 3 days ago that only reaches Complete status today needs that
    day's total_withdrawal to still be updatable, not already locked in.
    Once a date finally falls out of daily_records.db's retention, whatever
    was last computed here becomes its permanent, final record."""
    cur.execute(
        "CREATE TABLE IF NOT EXISTS daily_performance ("
        "date TEXT PRIMARY KEY, total_deposit REAL, deposit_count INTEGER, unique_depositors INTEGER, "
        "total_withdrawal REAL, withdrawal_count INTEGER, unique_withdrawers INTEGER, net_revenue REAL)"
    )
    dep_by_date = defaultdict(lambda: {"amount": 0.0, "count": 0, "users": set()})
    for pay_channel, order_amount, create_time, update_time_col, status, user_id, is_first_deposit in deposit_rows:
        if status != "COMPLETE" or not create_time:
            continue
        d = str(create_time)[:10]
        entry = dep_by_date[d]
        entry["amount"] += order_amount or 0.0
        entry["count"] += 1
        if user_id is not None:
            entry["users"].add(user_id)

    wd_by_date = defaultdict(lambda: {"amount": 0.0, "count": 0, "users": set()})
    for withdraw_amount, create_time, status, user_id in withdrawal_rows:
        if status != 2 or not create_time:  # 2 = Complete
            continue
        d = str(create_time)[:10]
        entry = wd_by_date[d]
        entry["amount"] += withdraw_amount or 0.0
        entry["count"] += 1
        if user_id is not None:
            entry["users"].add(user_id)

    all_dates = (set(dep_by_date.keys()) | set(wd_by_date.keys())) - {today.isoformat()}
    empty = {"amount": 0.0, "count": 0, "users": set()}
    for d in sorted(all_dates):
        dep = dep_by_date.get(d, empty)
        wd = wd_by_date.get(d, empty)
        total_deposit = round(dep["amount"], 2)
        total_withdrawal = round(wd["amount"], 2)
        cur.execute(
            "INSERT OR REPLACE INTO daily_performance (date, total_deposit, deposit_count, unique_depositors, "
            "total_withdrawal, withdrawal_count, unique_withdrawers, net_revenue) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (d, total_deposit, dep["count"], len(dep["users"]), total_withdrawal, wd["count"], len(wd["users"]),
             round(total_deposit - total_withdrawal, 2)),
        )
    return len(all_dates)


def compute_and_save_bonus_performance(cur, bonus_rows, today):
    """Permanent per-day, per-bonus-category rollup -- daily_records.db's
    `bonuses` table (populated by ingest_update.py's classify_bonus(), which
    tags a wallet_transactions row as a bonus credit under three confirmed
    rules: a real bonus name in game_name with blank source; game_name
    literally "Elle Import Excel Add", using source_id for the real bonus
    identity; or blank game_name with "bonus" in source_id, rolled up into
    combined "Daily Active Bonus"/"Daily Active Bonus Low" categories) is
    ALSO purged
    to the rolling 33-day window, same as everything else in
    daily_records.db. Without this table, "which bonus performed well last
    month" would already be unanswerable by the time you asked.

    Mirrors compute_and_save_daily_performance exactly: re-derives every
    date currently present in bonus_rows (except today, still accumulating)
    on every run, so a date keeps self-correcting for as long as its source
    rows are still retained, and simply keeps its last-computed value
    forever once they finally purge.

    bonus_rows are (matched_category, user_id, change_value, create_time)
    from daily_records.db's bonuses table -- a small table (a subset of
    wallet_transactions), safe to fetch in full."""
    cur.execute(
        "CREATE TABLE IF NOT EXISTS bonus_performance ("
        "bonus_category TEXT, date TEXT, claim_count INTEGER, total_value REAL, unique_users INTEGER, "
        "PRIMARY KEY (bonus_category, date))"
    )
    # One-time cleanup (safe to re-run every time -- a no-op once these are
    # gone): "Chicken Road Bonus" and "Bonus Hunter" are real games, not
    # bonuses -- they were misclassified by an earlier version of
    # classify_bonus()'s generic "contains 'bonus'" fallback before it
    # excluded them, and this permanent rollup would otherwise keep their
    # bad entries forever even after the classifier was fixed.
    cur.execute(
        "DELETE FROM bonus_performance WHERE bonus_category IN ('Chicken Road Bonus', 'Bonus Hunter')"
    )
    by_cat_date = defaultdict(lambda: {"count": 0, "value": 0.0, "users": set()})
    for matched_category, user_id, change_value, create_time in bonus_rows:
        if not matched_category or not create_time:
            continue
        d = str(create_time)[:10]
        entry = by_cat_date[(matched_category, d)]
        entry["count"] += 1
        entry["value"] += change_value or 0.0
        if user_id is not None:
            entry["users"].add(user_id)

    today_str = today.isoformat()
    n = 0
    for (category, d), entry in by_cat_date.items():
        if d == today_str:
            continue
        cur.execute(
            "INSERT OR REPLACE INTO bonus_performance (bonus_category, date, claim_count, total_value, unique_users) "
            "VALUES (?, ?, ?, ?, ?)",
            (category, d, entry["count"], round(entry["value"], 2), len(entry["users"])),
        )
        n += 1
    return n


def sync_master_userlist(master_db_path, deposit_rows, withdrawal_rows, wallet_activity, wallet_balance_by_user, bonus_rows, deposit_info, today):
    """VIP level and total_recharge are purely a function of cumulative
    deposits (the platform's own VIP table -- level N requires
    total_recharge >= VIP_THRESHOLDS[N]), never withdrawal or wallet
    activity. But last_active_time -- "has this user touched the platform at
    all" -- is bumped by ANY of deposit, withdrawal, or wallet (bet)
    activity, whichever is most recent. Keeps master_userlist.db current on
    every pull:

      1. Recomputes vip_level for every existing user from their stored
         total_recharge, correcting any previously-wrong value -- but only
         WRITES when it actually changed.
      1b. Sets user_balance to wallet_balance_by_user[user_id] -- the wallet
         ledger's own change_after value on the user's most recent wallet
         transaction, i.e. their true current balance -- for every user
         touched by wallet activity this run. Self-correcting: nothing
         else in this pipeline ever updates user_balance after the
         original bootstrap import, so it was silently going stale for
         every user the longer this ran without a fresh full userlist
         re-upload. Now it heals itself the next time each user has any
         wallet activity, no re-upload needed. Any row in
         balance_adjustments (see add_balance_adjustment.py) is added on
         top of that ledger-derived value every time -- a manual
         correction can't be recorded as a wallet_transactions row and
         expect it to stick, since change_after is an absolute balance set
         by the source platform on every real row, not a delta we control,
         so the next real transaction would just overwrite it regardless
         of where in time it's placed.
      2. Adds newly-seen COMPLETE deposits to each user's total_recharge, and
         newly-seen Complete (status 2) withdrawals to their total_withdrawal
         -- both lifetime, permanent totals on master_userlist.db, never
         subject to daily_records.db's 33-day purge. Dedicated
         deposit_sync_time/withdrawal_sync_time columns (not the real
         update_time/review_time fields, to avoid conflicting with genuine
         userlist re-uploads) track how far each has already been counted,
         so re-fetching the same rolling window on every run never
         double-counts.
      3. Bumps last_active_time for any user touched by a deposit,
         withdrawal, or wallet transaction more recent than their current
         value -- again, only writes when it actually moves forward.
      4. Inserts a minimal row for any user_id seen in ANY of the three
         sources but not already in the table (phone/city/channel only
         available when the insert is deposit-sourced).

    withdrawal_rows are the FULL rows (not just an activity timestamp) since
    total_withdrawal needs the actual amounts -- withdrawals is a modest
    table (thousands/day, not the tens-of-millions wallet_transactions can
    reach), so fetching it fully is cheap. wallet_activity stays a
    precomputed {user_id: latest create_time str} from a GROUP BY MAX query
    in main(), since wallet_transactions really is too large to fetch
    row-by-row here.

    Also (re)derives the permanent daily_performance rollup (see
    compute_and_save_daily_performance) once per day, from the FULL
    currently-retained deposit_rows/withdrawal_rows (up to 33 days) -- this
    is what makes total_deposit/total_withdrawal/net_revenue trends survive
    past daily_records.db's 33-day purge, instead of being capped at it.

    Skipping no-op writes (instead of touching every row every run
    unconditionally) is what keeps this run's SQLite write volume, and
    therefore its runtime/GitHub Actions billed minutes, proportional to
    what actually changed rather than to the full user table every time.

    Also detects "reactivation candidates" and "VIP upgrade candidates":
    users active/upgraded TODAY compared against a stable snapshot of their
    state as of the START of today. This can't just compare "before this
    run" vs "after this run" -- the pipeline runs hourly, and each run's
    report is freshly regenerated (not cumulative), so a naive per-run diff
    would silently lose an event from an earlier run the same day (e.g. a
    user who reactivates at 10am would show in the 10am report, but by 2pm
    their last_active_time already says "today" so they'd wrongly disappear
    from the 2pm report). Instead, a (vip_level, total_recharge,
    last_active_time) snapshot is taken once, on the first run of each
    calendar day, into the daily_snapshot table, BEFORE any of today's
    updates are applied -- every run for the rest of the day compares
    current state against that same stable snapshot. daily_snapshot also
    keeps FUNNEL_HISTORY_DAYS of rolling history (not just today) so
    build_deposit_report.py can compute N-day conversion funnels ("of users
    who were near-upgrade/inactive N days ago, how many have since
    converted") -- daily_records.db's own deposits/withdrawals/wallet
    tables are purged to a rolling 33-day window and don't carry enough
    signal for that on their own.

    Returns (changed, reactivation_candidates, vip_upgrade_candidates) --
    changed is True iff at least one row was actually inserted or updated
    this run. vip_upgrade_candidates is {"low": [...], "high": [...]}."""
    conn = sqlite3.connect(master_db_path)
    cur = conn.cursor()
    for ddl in (
        "ALTER TABLE users ADD COLUMN deposit_sync_time TEXT",
        "ALTER TABLE users ADD COLUMN total_withdrawal REAL DEFAULT 0",
        "ALTER TABLE users ADD COLUMN withdrawal_sync_time TEXT",
        "ALTER TABLE users ADD COLUMN recharge_count INTEGER DEFAULT 0",
    ):
        try:
            cur.execute(ddl)
        except sqlite3.OperationalError:
            pass  # column already exists from a previous run

    cur.execute(
        "CREATE TABLE IF NOT EXISTS daily_snapshot ("
        "user_id INTEGER, snapshot_date TEXT, vip_level INTEGER, total_recharge REAL, "
        "last_active_time TEXT, PRIMARY KEY (user_id, snapshot_date))"
    )
    cur.execute("CREATE TABLE IF NOT EXISTS daily_snapshot_meta (last_snapshot_date TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS funnel_stats (stat_date TEXT, data TEXT)")
    # Manual balance corrections (see manual_wallet_deduct.py) can't be
    # recorded as a wallet_transactions row and expect it to survive -- every
    # row's change_after is an ABSOLUTE balance reported by the source
    # platform itself, not a delta we control, so the very next real
    # transaction's change_after (computed upstream, oblivious to our
    # correction) simply overwrites it regardless of where in time the
    # synthetic row is placed. This table holds a permanent running total per
    # user that's added on TOP of the ledger-derived balance below instead --
    # survives every future sync, no matter how much new wallet activity
    # comes in.
    cur.execute(
        "CREATE TABLE IF NOT EXISTS balance_adjustments ("
        "user_id INTEGER PRIMARY KEY, total_adjustment REAL NOT NULL, "
        "last_reason TEXT, updated_at TEXT)"
    )
    adjustments = dict(cur.execute("SELECT user_id, total_adjustment FROM balance_adjustments").fetchall())
    today_str = today.isoformat()
    meta_row = cur.execute("SELECT last_snapshot_date FROM daily_snapshot_meta").fetchone()
    snapshot_created = not meta_row or meta_row[0] != today_str
    if snapshot_created:
        # New day (or first run ever) -- snapshot BEFORE any of today's
        # updates are applied below, so it reflects yesterday's end-of-day
        # state and stays stable across every run for the rest of today.
        # Must force a reupload below even if nothing else changes this run
        # (see `changed` at the bottom) -- otherwise this snapshot never
        # reaches R2, and the next run would re-snapshot from ITS
        # already-partway-through-the-day state instead of true day-start.
        cur.execute(
            "INSERT OR REPLACE INTO daily_snapshot (user_id, snapshot_date, vip_level, total_recharge, last_active_time) "
            "SELECT user_id, ?, vip_level, total_recharge, last_active_time FROM users",
            (today_str,),
        )
        prune_before = (today - datetime.timedelta(days=FUNNEL_HISTORY_DAYS)).isoformat()
        cur.execute("DELETE FROM daily_snapshot WHERE snapshot_date < ?", (prune_before,))
        cur.execute("DELETE FROM daily_snapshot_meta")
        cur.execute("INSERT INTO daily_snapshot_meta (last_snapshot_date) VALUES (?)", (today_str,))
        conn.commit()
        funnel_stats = compute_conversion_funnels(cur, today)
        cur.execute("DELETE FROM funnel_stats")
        cur.execute("INSERT INTO funnel_stats (stat_date, data) VALUES (?, ?)", (today_str, json.dumps(funnel_stats)))
        conn.commit()

    # Runs every hourly pull, not just on day-rollover: it's cheap (a single
    # pass over the already-in-memory deposit_rows/withdrawal_rows, not a
    # fresh DB read), and running it every hour means a historical day's
    # totals (e.g. a withdrawal that only reaches Complete status hours
    # after being created) get corrected promptly instead of waiting for
    # tomorrow's first run.
    n_days = compute_and_save_daily_performance(cur, deposit_rows, withdrawal_rows, today)
    n_bonus = compute_and_save_bonus_performance(cur, bonus_rows, today)
    conn.commit()
    print(f"Daily performance rollup refreshed for {n_days} dates; bonus performance for {n_bonus} category-dates (both permanent, survive the 33-day purge)")

    existing_rows = cur.execute(
        "SELECT user_id, total_recharge, vip_level, deposit_sync_time, last_active_time, total_withdrawal, withdrawal_sync_time, recharge_count FROM users"
    ).fetchall()
    existing = {
        uid: {"total_recharge": tr, "vip_level": vl, "sync_time": st, "last_active_time": lat,
              "total_withdrawal": tw, "withdrawal_sync_time": wst, "recharge_count": rc}
        for uid, tr, vl, st, lat, tw, wst, rc in existing_rows
    }

    fixed = 0
    for uid, info in existing.items():
        correct_vip = vip_level_for_total(info["total_recharge"])
        if correct_vip != info["vip_level"]:
            cur.execute("UPDATE users SET vip_level = ? WHERE user_id = ?", (correct_vip, uid))
            info["vip_level"] = correct_vip
            fixed += 1
    conn.commit()

    today_amount = defaultdict(float)
    today_active = set()
    deltas = defaultdict(lambda: {"amount": 0.0, "count": 0, "max_create_time": None})
    for pay_channel, order_amount, create_time, update_time_col, status, user_id, is_first_deposit in deposit_rows:
        if status != "COMPLETE" or user_id is None or not create_time:
            continue
        if str(create_time).startswith(today_str):
            today_amount[user_id] += order_amount or 0.0
            today_active.add(user_id)
        baseline = existing.get(user_id, {}).get("sync_time")
        if baseline and str(create_time) <= str(baseline):
            continue
        d = deltas[user_id]
        d["amount"] += order_amount or 0.0
        d["count"] += 1
        if not d["max_create_time"] or str(create_time) > str(d["max_create_time"]):
            d["max_create_time"] = create_time

    # withdrawal_activity: latest create_time per user, ANY status (a pending/
    # rejected withdrawal attempt is still "the user did something" for
    # last_active_time purposes). withdrawal_deltas: only status==2 (Complete)
    # amounts, using the same sync-baseline dedup pattern as deposit deltas,
    # feeding total_withdrawal (lifetime, permanent, mirrors total_recharge).
    withdrawal_activity = {}
    withdrawal_deltas = defaultdict(lambda: {"amount": 0.0, "max_create_time": None})
    for withdraw_amount, create_time, status, user_id in withdrawal_rows:
        if user_id is None or not create_time:
            continue
        ts = str(create_time)
        if user_id not in withdrawal_activity or ts > withdrawal_activity[user_id]:
            withdrawal_activity[user_id] = ts
        if status != 2:
            continue
        baseline = existing.get(user_id, {}).get("withdrawal_sync_time")
        if baseline and ts <= str(baseline):
            continue
        wd = withdrawal_deltas[user_id]
        wd["amount"] += withdraw_amount or 0.0
        if not wd["max_create_time"] or ts > str(wd["max_create_time"]):
            wd["max_create_time"] = create_time

    for user_id, ts in withdrawal_activity.items():
        if ts and str(ts).startswith(today_str):
            today_active.add(user_id)
    for user_id, ts in wallet_activity.items():
        if ts and str(ts).startswith(today_str):
            today_active.add(user_id)

    # Day-start snapshot (today's row -- guaranteed to exist by now, either
    # written by this run above or an earlier run today) is the correct
    # "before today" baseline for both reactivation and VIP-upgrade
    # detection below. Using `existing` (pre-THIS-run state) instead would
    # make a user who already reactivated/upgraded in an earlier run today
    # silently vanish from this run's report, since their `existing` value
    # already reflects that earlier update.
    day_start = {
        uid: {"vip_level": vl, "total_recharge": tr, "last_active_time": lat}
        for uid, vl, tr, lat in cur.execute(
            "SELECT user_id, vip_level, total_recharge, last_active_time FROM daily_snapshot WHERE snapshot_date = ?",
            (today_str,),
        ).fetchall()
    }

    reactivation_candidates = []
    for user_id in today_active:
        prior = day_start.get(user_id)
        if not prior or not prior["last_active_time"]:
            continue  # brand-new / never-active user, not a "reactivation"
        try:
            prior_dt = datetime.datetime.fromisoformat(str(prior["last_active_time"]).replace(" ", "T"))
        except ValueError:
            continue
        gap_days = (today - prior_dt.date()).days
        if gap_days <= 0:
            continue  # already active as of the start of today
        reactivation_candidates.append({
            "user_id": user_id,
            "inactive_days": gap_days,
            "total_deposit": round(today_amount.get(user_id, 0.0), 2),
        })

    # Union of every user touched by ANY of the three sources this run --
    # each may need a last_active_time bump even with zero deposit delta.
    # Banned users (dashboard's Ban User feature) are intentionally NOT
    # excluded here -- banning is a soft, report-time-only exclusion (see
    # build_deposit_report.py), not a deletion, so their real record keeps
    # updating normally in the background like any other user.
    touched_users = set(deltas.keys()) | set(withdrawal_activity.keys()) | set(wallet_activity.keys())

    new_users = updated = 0
    for user_id in touched_users:
        d = deltas.get(user_id)
        wd = withdrawal_deltas.get(user_id)
        candidate_times = []
        if d and d["max_create_time"]:
            candidate_times.append(str(d["max_create_time"]))
        if withdrawal_activity.get(user_id):
            candidate_times.append(str(withdrawal_activity[user_id]))
        if wallet_activity.get(user_id):
            candidate_times.append(str(wallet_activity[user_id]))
        if not candidate_times:
            continue
        latest_activity = max(candidate_times)

        prior = existing.get(user_id)
        fresh_balance = wallet_balance_by_user.get(user_id)
        if fresh_balance is not None and user_id in adjustments:
            fresh_balance = round(fresh_balance + adjustments[user_id], 2)
        if prior is None:
            deposit_amount = round(d["amount"], 2) if d else 0.0
            deposit_count = d["count"] if d else 0
            withdrawal_amount = round(wd["amount"], 2) if wd else 0.0
            vip = vip_level_for_total(deposit_amount)
            dep = deposit_info.get(user_id, {})
            deposit_sync_time = str(d["max_create_time"]) if d and d["max_create_time"] else None
            withdrawal_sync_time = str(wd["max_create_time"]) if wd and wd["max_create_time"] else None
            cur.execute(
                "INSERT INTO users (user_id, phone, city, channel, total_recharge, vip_level, "
                "last_active_time, deposit_sync_time, create_time, total_withdrawal, withdrawal_sync_time, user_balance, recharge_count) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, dep.get("phone"), dep.get("city"), dep.get("channel"), deposit_amount, vip,
                 latest_activity, deposit_sync_time, str(dep.get("register_time") or latest_activity),
                 withdrawal_amount, withdrawal_sync_time, fresh_balance, deposit_count),
            )
            new_users += 1
        else:
            sets, params = [], []
            if d and d["max_create_time"]:
                new_total = round((prior["total_recharge"] or 0.0) + d["amount"], 2)
                new_vip = vip_level_for_total(new_total)
                new_recharge_count = (prior["recharge_count"] or 0) + d["count"]
                sets += ["total_recharge = ?", "vip_level = ?", "deposit_sync_time = ?", "recharge_count = ?"]
                params += [new_total, new_vip, str(d["max_create_time"]), new_recharge_count]
                prior["total_recharge"] = new_total
                prior["vip_level"] = new_vip
                prior["recharge_count"] = new_recharge_count
            if wd and wd["max_create_time"]:
                new_total_withdrawal = round((prior["total_withdrawal"] or 0.0) + wd["amount"], 2)
                sets += ["total_withdrawal = ?", "withdrawal_sync_time = ?"]
                params += [new_total_withdrawal, str(wd["max_create_time"])]
                prior["total_withdrawal"] = new_total_withdrawal
            if fresh_balance is not None:
                sets.append("user_balance = ?")
                params.append(fresh_balance)
            current_last_active = prior["last_active_time"]
            if not current_last_active or latest_activity > str(current_last_active):
                sets.append("last_active_time = ?")
                params.append(latest_activity)
            if sets:
                params.append(user_id)
                cur.execute(f"UPDATE users SET {', '.join(sets)} WHERE user_id = ?", params)
                updated += 1

    # VIP upgrade candidates: compare each user's CURRENT vip_level (as of
    # right now, after everything above) against the stable day-start
    # snapshot (fetched earlier as `day_start`). Only counts users who were
    # actually in the near-upgrade cohort at day start -- a user who jumped
    # several tiers from far away (a huge lump-sum deposit) doesn't belong
    # in a "near upgrade converted" report.
    vip_upgrade_low, vip_upgrade_high = [], []
    for user_id, ds in day_start.items():
        cur_info = existing.get(user_id)
        if not cur_info or cur_info["vip_level"] <= ds["vip_level"]:
            continue
        ds_vip = ds["vip_level"]
        ds_total = ds["total_recharge"] or 0.0
        if ds_vip >= 15 or (ds_vip + 1) not in VIP_THRESHOLDS:
            continue  # no next tier to have been "near"
        gap = VIP_THRESHOLDS[ds_vip + 1] - ds_total
        deposit_today = round(today_amount.get(user_id, 0.0), 2)
        row = {
            "user_id": user_id,
            "vip_before": ds_vip,
            "vip_after": cur_info["vip_level"],
            "total_deposit": deposit_today,
            "amount_over_minimum": round(deposit_today - gap, 2),
        }
        if 2 <= ds_vip <= 4 and 1 <= gap <= 1000:
            vip_upgrade_low.append(row)
        elif 5 <= ds_vip <= 15 and 1 <= gap <= 50000:
            vip_upgrade_high.append(row)
    vip_upgrade_candidates = {"low": vip_upgrade_low, "high": vip_upgrade_high}

    conn.commit()
    conn.close()
    print(f"Master userlist VIP recompute: {fixed} users' vip_level actually changed")
    print(f"Master userlist sync: {new_users} new users inserted, {updated} users updated from deposit/withdrawal/wallet activity")
    print(f"user_balance refreshed from wallet ledger for {len(wallet_balance_by_user)} users with wallet activity in the retained window")
    print(f"Reactivation candidates today: {len(reactivation_candidates)}")
    print(f"VIP upgrade candidates today: {len(vip_upgrade_low)} low, {len(vip_upgrade_high)} high")
    changed = fixed > 0 or new_users > 0 or updated > 0 or snapshot_created
    return changed, reactivation_candidates, vip_upgrade_candidates


def main():
    bucket = os.environ["R2_BUCKET"]
    s3 = ci_ingest.r2_client()

    for fname in ["master_userlist.db", "daily_records.db"]:
        local_path = os.path.join(ci_ingest.BASE, fname)
        try:
            ci_ingest.download_with_retry(s3, bucket, fname, local_path)
            print(f"Downloaded existing {fname} from R2")
        except Exception as e:
            print(f"FATAL: could not download {fname} from R2: {e}", file=sys.stderr)
            sys.exit(1)

    token = fetch_token(s3, bucket)
    today = ist_today()
    ts = int(time.time() * 1000)

    try:
        # Deposits: 5-day window, date-only bounds (confirmed inclusive of the full end day)
        dep_start = today - datetime.timedelta(days=4)
        deposit_bytes = fetch_export(token, "water/export", {
            "packageId": PACKAGE_ID, "pageNum": 1, "pageSize": 10, "useUpiQuery": "true",
            "queryDate[0]": dep_start.isoformat(), "queryDate[1]": today.isoformat(),
        })
        deposit_path = save_xlsx(deposit_bytes, f"{ts}_water_api_pull.xlsx")
        print(f"Fetched deposits {dep_start} .. {today}: {len(deposit_bytes)} bytes")

        # Withdrawals: end bound is exclusive of the named day, so use (today + 1) at
        # 00:00:00 to include all of today. Query all 5 statuses (In-Review, Processing,
        # Complete, Rejected, Failed) -- the whole point of the 5-day window is to catch
        # orders that transition into any of those terminal states after creation.
        wd_start = today - datetime.timedelta(days=4)
        wd_end = today + datetime.timedelta(days=1)
        withdraw_bytes = fetch_export(token, "withdraw/export", {
            "packageId": PACKAGE_ID, "pageNum": 1, "pageSize": 10,
            "statusList[0]": 0, "statusList[1]": 1, "statusList[2]": 2, "statusList[3]": 3, "statusList[4]": 4,
            "queryDate[0]": f"{wd_start.isoformat()} 00:00:00", "queryDate[1]": f"{wd_end.isoformat()} 00:00:00",
        })
        withdraw_path = save_xlsx(withdraw_bytes, f"{ts}_withdraw_api_pull.xlsx")
        print(f"Fetched withdrawals {wd_start} .. {today} (inclusive): {len(withdraw_bytes)} bytes")

        # Wallet: single day, with day-rollover-aware target date
        wallet_state = get_wallet_state(s3, bucket)
        last_run_date = wallet_state.get("last_run_date")
        if last_run_date != today.isoformat():
            wallet_target = today - datetime.timedelta(days=1)
            print(f"First run of {today} -- wallet export will finalize {wallet_target}")
        else:
            wallet_target = today
            print(f"Same-day rerun -- wallet export continues with {wallet_target}")
        wallet_bytes = fetch_export(token, "detail/export", {
            "packageId": PACKAGE_ID, "pageNum": 1, "pageSize": 10,
            "queryDate[0]": wallet_target.isoformat(), "queryDate[1]": wallet_target.isoformat(),
        })
        wallet_path = save_xlsx(wallet_bytes, f"{ts}_detail_api_pull.xlsx")
        print(f"Fetched wallet {wallet_target}: {len(wallet_bytes)} bytes")
    except Exception as e:
        # Every export uses the same bearer token, so any unrecoverable fetch failure
        # here is treated as an expired/invalid token -- surfaced on the upload page.
        put_token_status(s3, bucket, ok=False, message="update new bearer token to run the pipeline")
        print(f"FATAL: business API fetch failed, marking token as invalid: {e}", file=sys.stderr)
        sys.exit(1)

    # Ingest everything in one pass (handles purge + re-upload to R2 internally)
    argv_backup = sys.argv
    sys.argv = [
        "ingest_update.py",
        "--deposits", deposit_path,
        "--withdrawals", withdraw_path,
        "--wallet", wallet_path,
    ]
    try:
        iu.main()
    finally:
        sys.argv = argv_backup

    # Keep master_userlist.db current on every pull: VIP level/total_recharge
    # are derived purely from cumulative deposits, total_withdrawal purely
    # from cumulative Complete withdrawals, but last_active_time is bumped by
    # ANY of deposit, withdrawal, or wallet activity (see sync_master_userlist
    # docstring). Read straight from the just-ingested daily_records.db (not
    # the raw xlsx files) so this always matches what's actually stored.
    # withdrawals is fetched in FULL (needed for total_withdrawal amounts,
    # and it's a modest table -- thousands/day, not tens of millions).
    # wallet_activity stays a GROUP BY MAX query -- wallet_transactions alone
    # can be tens of millions of rows across its 33-day window, so fetching
    # every row into Python here would be a real cost, not just a
    # correctness risk.
    master_db_path = os.path.join(ci_ingest.BASE, "master_userlist.db")
    daily_db_path = os.path.join(ci_ingest.BASE, "daily_records.db")
    daily_conn = sqlite3.connect(daily_db_path)
    # Backs the ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY create_time
    # DESC, id DESC) window function below -- without this, that query would
    # need a full sort of wallet_transactions (tens of millions of rows)
    # every run instead of walking this index directly.
    daily_conn.execute("CREATE INDEX IF NOT EXISTS idx_wt_user_time_id ON wallet_transactions(user_id, create_time DESC, id DESC)")
    deposit_rows_for_sync = daily_conn.execute(
        "SELECT pay_channel, order_amount, create_time, update_time, status, user_id, is_first_deposit FROM deposits"
    ).fetchall()
    withdrawal_rows_for_sync = daily_conn.execute(
        "SELECT withdraw_amount, create_time, status, user_id FROM withdrawals"
    ).fetchall()
    # change_after is the wallet ledger's own balance snapshot, but the
    # source export lags it by exactly one row: row i's change_after is
    # actually the TRUE balance BEFORE row i's own transaction was applied
    # (equivalently, the true resulting balance of row i-1), not the result
    # of row i itself -- confirmed by replaying change_value/direction across
    # 127,490 consecutive real transaction pairs (verify_ledger_lag.py),
    # 100% match, zero exceptions. So the true CURRENT balance is the most
    # recent row's own change_after PLUS (direction 0, credit) or MINUS
    # (direction 1, debit) that same row's own change_value -- one more step
    # than just reading change_after directly.
    #
    # "Most recent row" MUST be tie-broken by id, not create_time alone --
    # multiple transactions routinely land in the same second (confirmed:
    # user 949900 had a bet and a win both stamped '2026-07-06 03:08:38'),
    # and a bare GROUP BY/MAX(create_time) has no defined behavior for which
    # tied row's OTHER columns get returned (SQLite's docs say it's
    # "arbitrary which particular input row is used" when the max is
    # achieved by more than one row -- previously misread as guaranteed-safe
    # here, which it isn't). That's exactly what caused this user's balance
    # to keep reverting to a stale value every single sync. ROW_NUMBER()
    # partitioned by user_id, ordered by (create_time, id) DESC, picking
    # rn=1 gives the true latest row per user deterministically, same
    # tie-break resync_user_balances.py already uses.
    wallet_rows_for_sync = daily_conn.execute(
        "SELECT user_id, change_after, change_value, direction, create_time FROM ("
        "  SELECT user_id, change_after, change_value, direction, create_time,"
        "         ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY create_time DESC, id DESC) AS rn"
        "  FROM wallet_transactions WHERE user_id IS NOT NULL"
        ") WHERE rn = 1"
    ).fetchall()
    wallet_activity = {}
    wallet_balance_by_user = {}
    for user_id, change_after, change_value, direction, max_create_time in wallet_rows_for_sync:
        wallet_activity[user_id] = max_create_time
        if change_after is not None and change_value is not None and direction is not None:
            wallet_balance_by_user[user_id] = change_after + change_value if direction == 0 else change_after - change_value
    try:
        bonus_rows_for_sync = daily_conn.execute(
            "SELECT matched_category, user_id, change_value, create_time FROM bonuses"
        ).fetchall()
    except sqlite3.OperationalError:
        bonus_rows_for_sync = []  # table doesn't exist yet (e.g. no wallet data ingested so far)
    daily_conn.close()
    dep_info = extract_deposit_user_info(deposit_path)
    ok, reactivation_candidates, vip_upgrade_candidates = sync_master_userlist(
        master_db_path, deposit_rows_for_sync, withdrawal_rows_for_sync, wallet_activity,
        wallet_balance_by_user, bonus_rows_for_sync, dep_info, today
    )
    if ok:
        subprocess.run(
            [sys.executable, os.path.join(ci_ingest.BASE, "upload_to_r2.py"), "--files", "master_userlist.db"],
            check=True,
        )
        print("Uploaded refreshed master_userlist.db to R2")

    # Handed off to build_deposit_report.py (runs next, same job/workspace) via
    # local files. ALSO uploaded to R2 (reports/reactivation_candidates.json,
    # reports/vip_upgrade_candidates.json): ingest.yml -- dispatched by ANY
    # dashboard file upload (userlist/deposits/withdrawals/wallet/agents/
    # bulk_reassign), not just this hourly api_pull.yml job -- separately
    # re-runs build_deposit_report.py in its OWN fresh checkout with no local
    # copy of these files, which silently zeroed Reactivation/VIP Upgrade on
    # every such upload until build_deposit_report.py started falling back to
    # this R2 copy when the local file is missing.
    reactivation_path = os.path.join(ci_ingest.BASE, "reactivation_candidates.json")
    with open(reactivation_path, "w") as f:
        json.dump(reactivation_candidates, f)
    print(f"Wrote {len(reactivation_candidates)} reactivation candidates to {reactivation_path}")
    s3.upload_file(reactivation_path, bucket, "reports/reactivation_candidates.json")

    vip_upgrade_path = os.path.join(ci_ingest.BASE, "vip_upgrade_candidates.json")
    with open(vip_upgrade_path, "w") as f:
        json.dump(vip_upgrade_candidates, f)
    print(f"Wrote {len(vip_upgrade_candidates['low'])} low + {len(vip_upgrade_candidates['high'])} high VIP upgrade candidates to {vip_upgrade_path}")
    s3.upload_file(vip_upgrade_path, bucket, "reports/vip_upgrade_candidates.json")

    # Only mark the wallet target date as covered after a successful ingest
    put_wallet_state(s3, bucket, {"last_run_date": today.isoformat(), "last_wallet_target": wallet_target.isoformat()})
    print(f"Wallet state updated: last_run_date={today}")

    # Successful pull+ingest confirms the token is valid -- clear any stale alert
    put_token_status(s3, bucket, ok=True)


if __name__ == "__main__":
    main()
