import argparse
import os
import boto3

BASE = os.path.dirname(os.path.abspath(__file__))
CREDS_PATH = os.path.join(BASE, ".r2_credentials")


def load_creds():
    if os.path.exists(CREDS_PATH):
        return dict(line.strip().split("=", 1) for line in open(CREDS_PATH) if "=" in line)
    return {
        "R2_ACCOUNT_ID": os.environ["R2_ACCOUNT_ID"],
        "R2_ACCESS_KEY_ID": os.environ["R2_ACCESS_KEY_ID"],
        "R2_SECRET_ACCESS_KEY": os.environ["R2_SECRET_ACCESS_KEY"],
        "R2_ENDPOINT_URL": os.environ["R2_ENDPOINT_URL"],
        "R2_BUCKET": os.environ["R2_BUCKET"],
    }


def get_client(creds):
    return boto3.client(
        "s3",
        endpoint_url=creds["R2_ENDPOINT_URL"],
        aws_access_key_id=creds["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=creds["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="*", default=["master_userlist.db", "daily_records.db"],
                     help="Which DB files to upload (default: both). Skip files that weren't touched to save time.")
    args = ap.parse_args()

    creds = load_creds()
    s3 = get_client(creds)
    bucket = creds["R2_BUCKET"]

    for fname in args.files:
        path = os.path.join(BASE, fname)
        if not os.path.exists(path):
            print(f"skip (not found): {fname}")
            continue
        size_mb = os.path.getsize(path) / 1024 / 1024
        s3.upload_file(path, bucket, fname)
        print(f"Uploaded {fname} ({size_mb:.2f} MB) -> r2://{bucket}/{fname}")


if __name__ == "__main__":
    main()
