"""
One-off backfill: re-fetch deposits, withdrawals, and wallet details for an
explicit date range and re-ingest everything. Unlike the hourly pipeline
(which only ever looks at a rolling 5-day window for deposits/withdrawals,
and one day at a time for wallet), this can reach arbitrarily far back --
for verifying/filling a specific historical window on demand (e.g. after an
outage, or when a user reports something looks off for a range of days).

Deposits and withdrawals each support a real date-range query on the
business API, so those are fetched in ONE call covering the whole range.
Wallet detail export is single-day only (same constraint the hourly
pipeline works around), so it's fetched once per day in the range.

Every fetch is re-ingested via ingest_update.py's normal INSERT OR REPLACE
(deposits/withdrawals) / INSERT OR IGNORE (wallet, keyed by id) paths, so
re-running this against a day that's already fully captured is a safe
no-op -- it only adds rows that were actually missing.

Usage: python3 backfill_range.py --from 2026-09-10 --to 2026-09-15
"""
import argparse
import datetime
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
                raise RuntimeError(f"Unexpected response from {path} (content-type={ctype}): {resp.text[:300]}")
            return resp.content
        except Exception as e:
            last_err = e
            print(f"  fetch attempt {attempt}/{attempts} for {path} failed: {e}")
            if attempt < attempts:
                time.sleep(10 * attempt)
    raise last_err


def save_xlsx(content, name):
    path = os.path.join(BASE, name)
    with open(path, "wb") as f:
        f.write(content)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-date", dest="from_date", required=True, help="YYYY-MM-DD, inclusive")
    ap.add_argument("--to-date", dest="to_date", required=True, help="YYYY-MM-DD, inclusive")
    args = ap.parse_args()

    start = datetime.date.fromisoformat(args.from_date)
    end = datetime.date.fromisoformat(args.to_date)
    if start > end:
        print("FATAL: --from-date must be <= --to-date", file=sys.stderr)
        sys.exit(1)

    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()
    token = fetch_token(s3, bucket)
    ts = int(time.time() * 1000)

    for fname in ["master_userlist.db", "daily_records.db"]:
        s3.download_file(bucket, fname, os.path.join(BASE, fname))
    print("Downloaded current master_userlist.db + daily_records.db")

    print(f"Re-fetching deposits {start} .. {end} (one range query)")
    deposit_bytes = fetch_export(token, "water/export", {
        "packageId": PACKAGE_ID, "pageNum": 1, "pageSize": 10, "useUpiQuery": "true",
        "queryDate[0]": start.isoformat(), "queryDate[1]": end.isoformat(),
    })
    deposit_path = save_xlsx(deposit_bytes, f"{ts}_backfill_water.xlsx")
    print(f"  {len(deposit_bytes)} bytes")

    print(f"Re-fetching withdrawals {start} .. {end} (one range query)")
    wd_end_exclusive = end + datetime.timedelta(days=1)
    withdraw_bytes = fetch_export(token, "withdraw/export", {
        "packageId": PACKAGE_ID, "pageNum": 1, "pageSize": 10,
        "statusList[0]": 0, "statusList[1]": 1, "statusList[2]": 2, "statusList[3]": 3, "statusList[4]": 4,
        "queryDate[0]": f"{start.isoformat()} 00:00:00", "queryDate[1]": f"{wd_end_exclusive.isoformat()} 00:00:00",
    })
    withdraw_path = save_xlsx(withdraw_bytes, f"{ts}_backfill_withdraw.xlsx")
    print(f"  {len(withdraw_bytes)} bytes")

    wallet_paths = []
    day = start
    while day <= end:
        print(f"Re-fetching wallet detail for {day}")
        wallet_bytes = fetch_export(token, "detail/export", {
            "packageId": PACKAGE_ID, "pageNum": 1, "pageSize": 10,
            "queryDate[0]": day.isoformat(), "queryDate[1]": day.isoformat(),
        })
        wallet_path = save_xlsx(wallet_bytes, f"{ts}_backfill_detail_{day.isoformat()}.xlsx")
        wallet_paths.append(wallet_path)
        print(f"  {len(wallet_bytes)} bytes")
        day += datetime.timedelta(days=1)

    print(f"Ingesting: 1 deposits file, 1 withdrawals file, {len(wallet_paths)} wallet files")
    subprocess.run(
        [
            sys.executable, os.path.join(BASE, "ingest_update.py"),
            "--deposits", deposit_path,
            "--withdrawals", withdraw_path,
            "--wallet", *wallet_paths,
        ],
        check=True,
    )


if __name__ == "__main__":
    main()

# Trigger marker 2026-09-15: touched to fire backfill_range.yml's temporary
# push trigger (GitHub Actions "Run workflow" button isn't rendering for
# this repo, no available credential has API dispatch rights either).
