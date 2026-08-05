"""
Reassign (or unassign) one or more users to the same calling agent. Runs
inside GitHub Actions, triggered either by the single-user "Reassign Agent"
widget or the "Bulk Reassign Agent" (paste User IDs) widget on the
dashboard's Search User page (via the 08-project-upload worker's
/reassign-agent endpoint).

Agent assignments live in their OWN small R2 object
(config/agent_assignments.json -- {user_id_str: agent_name}), NOT inside
master_userlist.db. They used to be a table in master_userlist.db, which
meant every reassignment had to re-upload the ENTIRE 60MB+ database just to
change a couple of rows -- by far the slowest part of this script. Moving
the mapping to its own tiny JSON file removes that upload entirely (this
script no longer writes master_userlist.db at all, only reads it, to check
the user_id actually exists).

master_userlist.db is still downloaded read-only here because
build_deposit_report.py (run right after this script, in the same job
workspace) expects it already present locally and doesn't download it
itself.

Usage: python3 reassign_agent.py --user-ids 12345 --agent "Sathya (WFH)"
       python3 reassign_agent.py --user-ids 12345,67890,111 --agent "Sathya (WFH)"
       python3 reassign_agent.py --user-ids 12345 --agent ""   (un-assign)
"""
import argparse
import json
import os
import sqlite3
import sys

import boto3
from botocore.exceptions import ClientError

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER_DB = os.path.join(BASE, "master_userlist.db")
DAILY_DB = os.path.join(BASE, "daily_records.db")
AGENT_ASSIGNMENTS_KEY = "config/agent_assignments.json"


def r2_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def load_agent_assignments(s3, bucket):
    """Only a genuinely-missing object (first run ever, before this file has
    been created) defaults to an empty mapping. Any other error (network,
    auth, etc.) must fail loudly -- silently treating a transient failure as
    "no assignments yet" would upload a near-empty mapping over the real
    one, wiping out every existing assignment."""
    try:
        obj = s3.get_object(Bucket=bucket, Key=AGENT_ASSIGNMENTS_KEY)
        return json.loads(obj["Body"].read())
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
            return {}
        raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-ids", required=True, help="Comma-separated user IDs")
    ap.add_argument("--agent", required=True, help="Agent name, or empty string to un-assign")
    args = ap.parse_args()

    user_ids = [int(x.strip()) for x in args.user_ids.split(",") if x.strip()]
    if not user_ids:
        print("FATAL: no user IDs given", file=sys.stderr)
        sys.exit(1)

    bucket = os.environ["R2_BUCKET"]
    s3 = r2_client()

    try:
        s3.download_file(bucket, "master_userlist.db", MASTER_DB)
        # build_deposit_report.py needs this present locally too -- see
        # module docstring.
        s3.download_file(bucket, "daily_records.db", DAILY_DB)
    except Exception as e:
        print(f"FATAL: could not download DBs from R2: {e}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(MASTER_DB)
    existing_ids = {
        row[0] for row in conn.execute(
            f"SELECT user_id FROM users WHERE user_id IN ({','.join('?' * len(user_ids))})",
            user_ids,
        ).fetchall()
    }
    conn.close()

    try:
        mapping = load_agent_assignments(s3, bucket)
    except Exception as e:
        print(f"FATAL: could not load {AGENT_ASSIGNMENTS_KEY} from R2: {e}", file=sys.stderr)
        sys.exit(1)

    agent = args.agent.strip()
    assigned, missing = [], []
    for user_id in user_ids:
        if user_id not in existing_ids:
            missing.append(user_id)
            continue
        if agent:
            mapping[str(user_id)] = agent
        else:
            mapping.pop(str(user_id), None)
        assigned.append(user_id)

    if missing:
        print(f"Skipped {len(missing)} user_id(s) not found in users table: {missing}", file=sys.stderr)
    label = agent or "Un-Assigned"
    print(f"Assigned {len(assigned)} user(s) -> {label}: {assigned}")
    if not assigned:
        print("FATAL: no valid user IDs to reassign", file=sys.stderr)
        sys.exit(1)

    s3.put_object(Bucket=bucket, Key=AGENT_ASSIGNMENTS_KEY, Body=json.dumps(mapping), ContentType="application/json")
    print(f"Uploaded updated {AGENT_ASSIGNMENTS_KEY} ({len(mapping)} total assignments)")


if __name__ == "__main__":
    main()
