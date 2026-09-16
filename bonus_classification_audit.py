"""One-off read-only diagnostic: find bonus-shaped wallet_transactions/
bonuses rows that are splitting into near-duplicate matched_category
values instead of rolling up into one category -- same shape as the
Weekly Loss Bonus bug fixed earlier. Also specifically checks for
VIP_DAILY_RECHARGE_CASHBACK.

Usage: python3 bonus_classification_audit.py
"""
import os
import re
import sqlite3
from collections import Counter

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


def strip_suffix(label):
    """Heuristic: strip a trailing per-instance suffix (timestamp, random
    hex, colon/dash-separated numeric id) to guess the "family" a
    fragmented matched_category belongs to."""
    s = str(label)
    s = re.sub(r"[:\-][0-9a-fA-F]{6,}.*$", "", s)
    s = re.sub(r"[:\-]\d{8,}.*$", "", s)
    s = re.sub(r"\s+\d{8,}.*$", "", s)
    return s.strip()


def main():
    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()
    s3.download_file(bucket, "daily_records.db", DAILY_DB)
    print("downloaded daily_records.db")

    conn = sqlite3.connect(DAILY_DB)
    cur = conn.cursor()

    print("\n=== bonuses.matched_category fragmentation (grouped by guessed family) ===")
    rows = cur.execute("SELECT matched_category, COUNT(*), SUM(change_value) FROM bonuses GROUP BY matched_category").fetchall()
    print(f"total distinct matched_category values: {len(rows)}")

    families = Counter()
    family_amount = Counter()
    family_examples = {}
    for cat, cnt, total in rows:
        fam = strip_suffix(cat)
        families[fam] += cnt
        family_amount[fam] += total or 0.0
        family_examples.setdefault(fam, [])
        if len(family_examples[fam]) < 3:
            family_examples[fam].append(cat)

    # Families backed by >1 distinct raw matched_category value are the
    # fragmented ones (same shape as pre-fix Weekly Loss Bonus).
    raw_count_per_family = Counter()
    for cat, cnt, total in rows:
        raw_count_per_family[strip_suffix(cat)] += 1

    print("\nFragmented families (>1 distinct raw matched_category value), sorted by total row count:")
    for fam, cnt in sorted(families.items(), key=lambda x: -x[1]):
        if raw_count_per_family[fam] > 1:
            print(f"  {fam!r}: {raw_count_per_family[fam]} distinct raw values, {cnt} total rows, "
                  f"{family_amount[fam]:.2f} total amount -- examples: {family_examples[fam]}")

    print("\n=== VIP_DAILY_RECHARGE_CASHBACK specific check ===")
    vip_rows = cur.execute(
        "SELECT w.game_name, w.source, w.source_id, COUNT(*), SUM(w.change_value) FROM wallet_transactions w "
        "WHERE w.source_id LIKE 'VIP_DAILY_RECHARGE_CASHBACK%' "
        "GROUP BY w.game_name, w.source, w.source_id LIMIT 20"
    ).fetchall()
    total_vip = cur.execute(
        "SELECT COUNT(*), SUM(change_value) FROM wallet_transactions WHERE source_id LIKE 'VIP_DAILY_RECHARGE_CASHBACK%'"
    ).fetchone()
    print(f"total rows: {total_vip[0]}, total amount: {total_vip[1]}")
    print("sample rows (game_name, source, source_id, count, sum):")
    for r in vip_rows:
        print(f"  {r}")

    already_classified = cur.execute(
        "SELECT COUNT(*) FROM bonuses WHERE id IN "
        "(SELECT id FROM wallet_transactions WHERE source_id LIKE 'VIP_DAILY_RECHARGE_CASHBACK%')"
    ).fetchone()[0]
    print(f"of which already present in bonuses table: {already_classified}")

    print("\n=== Other unclassified bonus-shaped rows (blank game_name, blank source, non-empty source_id, not already in bonuses) ===")
    unclassified = cur.execute(
        "SELECT source_id, COUNT(*), SUM(change_value) FROM wallet_transactions "
        "WHERE (game_name IS NULL OR game_name = '') AND (source IS NULL OR source = '') "
        "AND source_id IS NOT NULL AND source_id != '' "
        "AND id NOT IN (SELECT id FROM bonuses) "
        "GROUP BY source_id ORDER BY COUNT(*) DESC LIMIT 40"
    ).fetchall()
    fam2 = Counter()
    fam2_amount = Counter()
    fam2_examples = {}
    for sid, cnt, total in unclassified:
        fam = strip_suffix(sid)
        fam2[fam] += cnt
        fam2_amount[fam] += total or 0.0
        fam2_examples.setdefault(fam, [])
        if len(fam2_examples[fam]) < 3:
            fam2_examples[fam].append(sid)
    for fam, cnt in sorted(fam2.items(), key=lambda x: -x[1]):
        print(f"  {fam!r}: {cnt} rows, {fam2_amount[fam]:.2f} total -- examples: {fam2_examples[fam]}")

    conn.close()


if __name__ == "__main__":
    main()
