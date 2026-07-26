"""Read-only: lists everyone currently in banned_users."""
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
    conn.execute("CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY, banned_at TEXT)")
    rows = conn.execute("SELECT user_id, banned_at FROM banned_users ORDER BY banned_at").fetchall()
    print(f"=== {len(rows)} users currently in banned_users ===")
    for uid, banned_at in rows:
        print(f"  {uid} -- banned at {banned_at}")
    conn.close()


if __name__ == "__main__":
    main()
