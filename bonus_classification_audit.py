"""One-off read-only diagnostic: inspect the actual game_name/source/
source_id shape of GAME_RUMMY_DAILY_PROFIT_LOSS_REWARD rows (08-project's
own New Users Lossback bonus) before writing a classify_bonus() rule for
it, and check its current classification state in the bonuses table.

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

    print("\n=== wallet_transactions rows with GAME_RUMMY_DAILY_PROFIT_LOSS_REWARD anywhere ===")
    rows = cur.execute(
        "SELECT id, game_name, source, source_id, direction, change_value FROM wallet_transactions "
        "WHERE source_id LIKE '%GAME\\_RUMMY\\_DAILY\\_PROFIT\\_LOSS\\_REWARD%' ESCAPE '\\' "
        "OR game_name LIKE '%GAME\\_RUMMY\\_DAILY\\_PROFIT\\_LOSS\\_REWARD%' ESCAPE '\\' "
        "LIMIT 20"
    ).fetchall()
    for r in rows:
        print(f"  {r}")
    total = cur.execute(
        "SELECT COUNT(*), SUM(change_value) FROM wallet_transactions "
        "WHERE source_id LIKE '%GAME\\_RUMMY\\_DAILY\\_PROFIT\\_LOSS\\_REWARD%' ESCAPE '\\' "
        "OR game_name LIKE '%GAME\\_RUMMY\\_DAILY\\_PROFIT\\_LOSS\\_REWARD%' ESCAPE '\\'"
    ).fetchone()
    print(f"total rows: {total[0]}, total amount: {total[1]}")

    print("\n=== of those, current classification state in bonuses ===")
    classified = cur.execute(
        "SELECT b.matched_category, COUNT(*) FROM bonuses b "
        "JOIN wallet_transactions w ON w.id = b.id "
        "WHERE w.source_id LIKE '%GAME\\_RUMMY\\_DAILY\\_PROFIT\\_LOSS\\_REWARD%' ESCAPE '\\' "
        "OR w.game_name LIKE '%GAME\\_RUMMY\\_DAILY\\_PROFIT\\_LOSS\\_REWARD%' ESCAPE '\\' "
        "GROUP BY b.matched_category ORDER BY COUNT(*) DESC LIMIT 20"
    ).fetchall()
    for r in classified:
        print(f"  {r}")
    unclassified = cur.execute(
        "SELECT COUNT(*) FROM wallet_transactions w "
        "WHERE (w.source_id LIKE '%GAME\\_RUMMY\\_DAILY\\_PROFIT\\_LOSS\\_REWARD%' ESCAPE '\\' "
        "OR w.game_name LIKE '%GAME\\_RUMMY\\_DAILY\\_PROFIT\\_LOSS\\_REWARD%' ESCAPE '\\') "
        "AND w.id NOT IN (SELECT id FROM bonuses)"
    ).fetchone()[0]
    print(f"not in bonuses table at all: {unclassified}")

    print("\n=== existing 'New Users Lossback' category state (if any) ===")
    nul = cur.execute("SELECT COUNT(*), SUM(change_value) FROM bonuses WHERE matched_category = 'New Users Lossback'").fetchone()
    print(f"  rows: {nul[0]}, total: {nul[1]}")

    conn.close()


if __name__ == "__main__":
    main()
