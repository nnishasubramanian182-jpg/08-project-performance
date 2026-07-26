"""Read-only diagnostic: inspect agent_performance table's actual row/date
coverage directly in master_userlist.db, to check why the Performance page's
"Yesterday" preset might be missing a day."""
import os
import sqlite3

import boto3

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER_DB = os.path.join(BASE, "master_userlist.db")


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
    s3.download_file(bucket, "master_userlist.db", MASTER_DB)

    conn = sqlite3.connect(MASTER_DB)
    cur = conn.cursor()
    print("=== agent_performance: rows per date ===")
    for date, n in cur.execute(
        "SELECT date, COUNT(*) FROM agent_performance GROUP BY date ORDER BY date"
    ).fetchall():
        print(f"  {date}: {n} rows")

    print("=== agent_performance: total rows ===")
    print(" ", cur.execute("SELECT COUNT(*) FROM agent_performance").fetchone()[0])

    print("=== SQLite table info ===")
    print(" ", cur.execute("PRAGMA table_info(agent_performance)").fetchall())
    conn.close()


if __name__ == "__main__":
    main()
