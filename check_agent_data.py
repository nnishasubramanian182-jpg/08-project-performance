"""Read-only diagnostic:
1. Any user_id assigned to more than one agent in agent_assignments (should
   never happen -- agent_for() silently picks whichever row a dict()
   construction happens to keep last, hiding the problem downstream).
2. Any agent in the current agent list missing from agent_performance
   (today's date), to confirm whether newly-added agents are actually
   getting performance rows computed."""
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

    print("=== 1. Users assigned to more than one agent ===")
    dupes = conn.execute(
        "SELECT user_id, COUNT(*) as c, GROUP_CONCAT(agent_name) FROM agent_assignments "
        "GROUP BY user_id HAVING c > 1 ORDER BY c DESC"
    ).fetchall()
    if not dupes:
        print("  none -- every user is assigned to exactly one agent")
    else:
        print(f"  {len(dupes)} users have duplicate agent assignments:")
        for uid, c, agents in dupes:
            print(f"    user {uid}: {c} rows -> {agents}")

    print()
    print("=== 2. Total rows / distinct users / distinct agents in agent_assignments ===")
    total_rows = conn.execute("SELECT COUNT(*) FROM agent_assignments").fetchone()[0]
    distinct_users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM agent_assignments").fetchone()[0]
    agent_counts = conn.execute(
        "SELECT agent_name, COUNT(*) FROM agent_assignments GROUP BY agent_name ORDER BY agent_name"
    ).fetchall()
    print(f"  total rows: {total_rows}, distinct users: {distinct_users}")
    for name, c in agent_counts:
        print(f"    {name}: {c} users")

    print()
    print("=== 3. Agents present today in agent_performance vs current agent list ===")
    try:
        today_agents = set(
            r[0] for r in conn.execute(
                "SELECT DISTINCT agent_name FROM agent_performance WHERE date = (SELECT MAX(date) FROM agent_performance)"
            ).fetchall()
        )
        latest_date = conn.execute("SELECT MAX(date) FROM agent_performance").fetchone()[0]
    except sqlite3.OperationalError:
        today_agents, latest_date = set(), None
    current_agents = set(name for name, _ in agent_counts)
    print(f"  latest agent_performance date: {latest_date}")
    print(f"  agents in agent_performance on that date: {sorted(today_agents)}")
    missing = current_agents - today_agents
    if missing:
        print(f"  MISSING from agent_performance: {sorted(missing)}")
    else:
        print("  none missing -- every current agent has a performance row for the latest date")

    conn.close()


if __name__ == "__main__":
    main()
