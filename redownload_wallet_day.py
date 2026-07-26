"""
Targeted, single-day re-fetch of the wallet detail export -- NOT the full
hourly pipeline. Re-queries the business API for one specific calendar day
and re-ingests it via ingest_update.py's --wallet path (now multi-sheet
aware, and idempotent: re-ingesting a day already captured is a safe no-op
for every row already present, since wallet_transactions.id is the primary
key and ingestion uses INSERT OR IGNORE -- only genuinely new/missing rows
get added).

Usage: python3 redownload_wallet_day.py --date 2026-07-05
"""
import argparse
import os
import subprocess
import sys
import time

import boto3
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
API_BASE = "https://api.anmanagers.online/prod-api/business"
PACKAGE_ID = "13"
TOKEN_KEY = "config/business_api_token.txt"


def r2_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def fetch_token(s3, bucket):
    obj = s3.get_object(Bucket=bucket, Key=TOKEN_KEY)
    token = obj["Body"].read().decode("utf-8").strip()
    if not token:
        print("FATAL: business API token is empty", file=sys.stderr)
        sys.exit(1)
    return token


def fetch_export(token, path, payload, attempts=3):
    last_err = None
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.post(
                f"{API_BASE}/{path}",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/x-www-form-urlencoded"},
                data=payload,
                timeout=180,
            )
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "")
            if "spreadsheet" not in ctype and "ms-excel" not in ctype:
                raise RuntimeError(f"Unexpected response (content-type={ctype}): {resp.text[:300]}")
            return resp.content
        except Exception as e:
            last_err = e
            print(f"  fetch attempt {attempt}/{attempts} failed: {e}")
            if attempt < attempts:
                time.sleep(5 * attempt)
    raise last_err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="YYYY-MM-DD, single calendar day to re-fetch")
    args = ap.parse_args()

    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()
    token = fetch_token(s3, bucket)

    print(f"Re-fetching wallet detail export for {args.date} (full day, not incremental)")
    wallet_bytes = fetch_export(token, "detail/export", {
        "packageId": PACKAGE_ID, "pageNum": 1, "pageSize": 10,
        "queryDate[0]": args.date, "queryDate[1]": args.date,
    })
    print(f"Fetched {len(wallet_bytes)} bytes")

    wallet_path = os.path.join(BASE, f"redownload_{args.date}_detail.xlsx")
    with open(wallet_path, "wb") as f:
        f.write(wallet_bytes)

    # Download current DBs so ingest_update.py has something to update --
    # same pattern ci_ingest.py uses.
    for fname in ["master_userlist.db", "daily_records.db"]:
        s3.download_file(bucket, fname, os.path.join(BASE, fname))
    print("Downloaded current master_userlist.db + daily_records.db")

    subprocess.run(
        [sys.executable, os.path.join(BASE, "ingest_update.py"), "--wallet", wallet_path],
        check=True,
    )


if __name__ == "__main__":
    main()
