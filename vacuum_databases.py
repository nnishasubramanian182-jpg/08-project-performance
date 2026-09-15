"""One-off maintenance: VACUUM + ANALYZE both databases to reclaim space
SQLite never returns after deletes (the nightly 33-day purge is a large
delete every day) and refresh the query planner's statistics. Meant to be
run manually/on a low-frequency schedule -- NOT part of the hourly pipeline,
since VACUUM rewrites the entire file and briefly needs up to 2x the file's
size in free disk space.

Usage: python3 vacuum_databases.py
"""
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


def vacuum_one(s3, bucket, key, local_path):
    s3.download_file(bucket, key, local_path)
    before = os.path.getsize(local_path)
    conn = sqlite3.connect(local_path)
    conn.execute("VACUUM")
    conn.execute("ANALYZE")
    conn.commit()
    conn.close()
    after = os.path.getsize(local_path)
    print(f"{key}: {human(before)} -> {human(after)} (saved {human(max(before - after, 0))})")
    s3.upload_file(local_path, bucket, key)
    print(f"  uploaded updated {key}")


def main():
    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()
    # Sequential, not parallel -- each VACUUM briefly needs up to 2x the
    # file's own size in free disk, and this only needs to run occasionally,
    # not fast.
    vacuum_one(s3, bucket, "master_userlist.db", MASTER_DB)
    vacuum_one(s3, bucket, "daily_records.db", DAILY_DB)


if __name__ == "__main__":
    main()
