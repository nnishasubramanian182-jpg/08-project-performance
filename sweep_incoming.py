"""
Safety net for the upload pipeline. When several files are uploaded close together,
GitHub can silently cancel a *queued* ingest.yml run in favor of a newer one (the
`db-ingest` concurrency group only holds one queued run at a time) -- the dropped
run's file is left sitting in R2 under incoming/ and never gets ingested.

This script looks for such orphaned files (present in incoming/ for longer than a
normal ingest run should take) and re-dispatches ingest.yml for the oldest one. It
dispatches at most one per run so repeated sweeps never reintroduce the same race.

Usage: python3 sweep_incoming.py
"""
import os
import sys
import time
import boto3
import requests

ORPHAN_AGE_SECONDS = 5 * 60  # a normal ingest run finishes in well under a minute


def r2_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def gh_headers():
    return {
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "master-userlist-sweep",
    }


def active_ingest_run_exists(owner, repo):
    for status in ("queued", "in_progress"):
        resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/ingest.yml/runs",
            headers=gh_headers(),
            params={"status": status, "per_page": 1},
            timeout=30,
        )
        resp.raise_for_status()
        if resp.json()["total_count"] > 0:
            return True
    return False


def dispatch_ingest(owner, repo, file_type, key):
    resp = requests.post(
        f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/ingest.yml/dispatches",
        headers=gh_headers(),
        json={"ref": "main", "inputs": {"file_type": file_type, "key": key}},
        timeout=30,
    )
    resp.raise_for_status()


def main():
    owner, repo = os.environ["GITHUB_REPOSITORY"].split("/")
    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()

    resp = s3.list_objects_v2(Bucket=bucket, Prefix="incoming/")
    objects = resp.get("Contents", [])
    if not objects:
        print("No files under incoming/ -- nothing to sweep.")
        return

    now = time.time()
    orphans = []
    for obj in objects:
        age = now - obj["LastModified"].timestamp()
        if age >= ORPHAN_AGE_SECONDS:
            orphans.append((obj["Key"], age))

    if not orphans:
        print(f"{len(objects)} file(s) under incoming/, none older than {ORPHAN_AGE_SECONDS}s -- nothing to sweep.")
        return

    if active_ingest_run_exists(owner, repo):
        print("An ingest run is already queued/in progress -- skipping this sweep, will retry next tick.")
        return

    orphans.sort(key=lambda x: -x[1])  # oldest first
    key, age = orphans[0]
    parts = key.split("/")
    if len(parts) < 2 or parts[0] != "incoming":
        print(f"Skipping unrecognized key shape: {key}", file=sys.stderr)
        return
    file_type = parts[1]
    if file_type not in ("userlist", "deposits", "withdrawals", "wallet"):
        print(f"Skipping key with unknown file_type '{file_type}': {key}", file=sys.stderr)
        return

    print(f"Found orphaned file (age {age:.0f}s): {key} -- re-dispatching ingest as '{file_type}'")
    dispatch_ingest(owner, repo, file_type, key)
    print("Re-dispatched.")


if __name__ == "__main__":
    main()
