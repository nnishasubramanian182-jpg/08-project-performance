"""
Runs inside GitHub Actions. Downloads the current DBs + one newly-uploaded
Excel file from R2, ingests it via ingest_update.py, then re-uploads the
updated DBs to R2. The incoming file is deleted from R2 afterwards.

Usage: python3 ci_ingest.py --file-type userlist --key incoming/userlist/foo.xlsx
"""
import argparse
import os
import subprocess
import sys
import time
import boto3

BASE = os.path.dirname(os.path.abspath(__file__))


def r2_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def download_with_retry(s3, bucket, key, local_path, attempts=3):
    last_err = None
    for attempt in range(1, attempts + 1):
        try:
            s3.download_file(bucket, key, local_path)
            return
        except Exception as e:
            last_err = e
            print(f"  download attempt {attempt}/{attempts} for {key} failed: {e}")
            if attempt < attempts:
                time.sleep(5 * attempt)
    raise last_err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file-type", required=True, choices=["userlist", "deposits", "withdrawals", "wallet", "agents", "bulk_reassign"])
    ap.add_argument("--key", required=True, help="R2 object key of the uploaded xlsx file")
    args = ap.parse_args()

    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()

    # Pull down existing DBs. Both must already exist in R2 (they're bootstrapped
    # once, then this pipeline only ever updates them) -- if a download fails for
    # any reason (missing, network error, auth error), we stop rather than silently
    # falling back to a fresh/empty DB, which would corrupt or wipe out live data
    # on the next re-upload.
    for fname in ["master_userlist.db", "daily_records.db"]:
        local_path = os.path.join(BASE, fname)
        try:
            download_with_retry(s3, bucket, fname, local_path)
            print(f"Downloaded existing {fname} from R2")
        except Exception as e:
            # Both DBs are expected to always exist once bootstrapped. Any failure
            # here (missing object, network error, auth error) is fatal -- never
            # silently fall back to a fresh/empty DB, since that would wipe out
            # live data on the next re-upload.
            print(f"FATAL: could not download {fname} from R2: {e}", file=sys.stderr)
            sys.exit(1)

    # Pull down the newly uploaded file
    local_incoming = os.path.join(BASE, os.path.basename(args.key))
    download_with_retry(s3, bucket, args.key, local_incoming)
    print(f"Downloaded incoming file {args.key} -> {local_incoming}")

    # Run the ingest (this also purges >33 days and uploads both DBs to R2).
    # Uses subprocess.run with check=True so a failure here actually fails this
    # job -- os.system() would silently swallow a non-zero exit code and let the
    # workflow report success even though nothing was ingested or re-uploaded.
    flag_map = {
        "userlist": "--userlist",
        "deposits": "--deposits",
        "withdrawals": "--withdrawals",
        "wallet": "--wallet",
        "agents": "--agents",
        "bulk_reassign": "--bulk-reassign",
    }
    cmd_flag = flag_map[args.file_type]
    subprocess.run(
        [sys.executable, os.path.join(BASE, "ingest_update.py"), cmd_flag, local_incoming],
        check=True,
    )

    # Clean up the incoming file from R2 now that it's been processed
    s3.delete_object(Bucket=bucket, Key=args.key)
    print(f"Deleted processed file from R2: {args.key}")


if __name__ == "__main__":
    main()
