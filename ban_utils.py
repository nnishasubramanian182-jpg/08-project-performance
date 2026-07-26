"""
Shared helper for the "Ban User" feature -- banned_users lives in
master_userlist.db and is the single source of truth for who's banned.
Banning is a soft, report-time-only exclusion, not a deletion: real records
are never touched. build_deposit_report.py is the only consumer -- it reads
this list once per run and generates every report/export/search-index entry
from a throwaway filtered COPY of both DBs, so banned users are invisible
everywhere on the dashboard without losing any history.
"""
import sqlite3


def get_banned_user_ids(master_db_path):
    conn = sqlite3.connect(master_db_path)
    conn.execute("CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY, banned_at TEXT)")
    conn.commit()
    ids = [r[0] for r in conn.execute("SELECT user_id FROM banned_users").fetchall()]
    conn.close()
    return ids
