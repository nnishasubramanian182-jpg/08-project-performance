"""Read-only diagnostic: sizes and row counts across the whole storage layer,
to ground an architecture/performance review in real numbers instead of
guesses. Downloads both DBs, reports file sizes, table row counts, index
list, and R2 object sizes for the big generated report files."""
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


def human(n):
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def main():
    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()

    print("=== R2 object sizes ===")
    keys = [
        "master_userlist.db",
        "daily_records.db",
        "reports/deposit_report.json",
        "reports/agent_list.json",
    ]
    for key in keys:
        try:
            head = s3.head_object(Bucket=bucket, Key=key)
            print(f"  {key}: {human(head['ContentLength'])} ({head['ContentLength']:,} bytes)")
        except Exception as e:
            print(f"  {key}: ERROR {e}")

    # Sample a few agent report shards + user_search shards for size, and count how many exist
    for prefix, label in [("reports/agent/", "per-agent reports"), ("user_search/", "user_search shards"), ("reports/analytics_history/", "analytics_history snapshots")]:
        try:
            resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            objs = resp.get("Contents", [])
            total = sum(o["Size"] for o in objs)
            print(f"  {label}: {len(objs)} files, {human(total)} total")
        except Exception as e:
            print(f"  {label}: ERROR {e}")

    print()
    print("=== Downloading DBs ===")
    s3.download_file(bucket, "master_userlist.db", MASTER_DB)
    s3.download_file(bucket, "daily_records.db", DAILY_DB)
    print(f"  master_userlist.db on disk: {human(os.path.getsize(MASTER_DB))}")
    print(f"  daily_records.db on disk: {human(os.path.getsize(DAILY_DB))}")

    print()
    print("=== master_userlist.db tables ===")
    conn = sqlite3.connect(MASTER_DB)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    for t in tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}: {count:,} rows")
        except Exception as e:
            print(f"  {t}: ERROR {e}")
    print("  indexes:", [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()])
    conn.close()

    print()
    print("=== daily_records.db tables ===")
    conn = sqlite3.connect(DAILY_DB)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    for t in tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}: {count:,} rows")
        except Exception as e:
            print(f"  {t}: ERROR {e}")
    print("  indexes:", [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()])

    # Date range actually retained in wallet_transactions/deposits/withdrawals
    for t, col in [("wallet_transactions", "create_time"), ("deposits", "create_time"), ("withdrawals", "create_time")]:
        try:
            row = conn.execute(f"SELECT MIN({col}), MAX({col}) FROM {t}").fetchone()
            print(f"  {t}.{col} range: {row[0]} .. {row[1]}")
        except Exception as e:
            print(f"  {t}.{col}: ERROR {e}")
    conn.close()


if __name__ == "__main__":
    main()
