import sqlite3
import openpyxl
import os
import re

DB_PATH = "daily_records.db"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

def clean(row):
    return tuple(str(v) if hasattr(v, "isoformat") else v for v in row)

def load_sheet(path):
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    wb.close()
    return rows

# ---------------- deposits (water_*.xlsx) ----------------
cur.execute("""
CREATE TABLE deposits (
    id INTEGER PRIMARY KEY,
    management_group TEXT,
    order_no TEXT,
    user_id INTEGER,
    order_amount REAL,
    ori_amount REAL,
    app_channel TEXT,
    result_date TEXT,
    status TEXT,
    pay_type TEXT,
    tripartite_order_no TEXT,
    pay_center_order_no TEXT,
    source_id TEXT,
    mark TEXT,
    user_phone TEXT,
    channel TEXT,
    pay_app_id TEXT,
    user_register_time TEXT,
    is_first_deposit INTEGER,
    create_date TEXT,
    pay_channel TEXT,
    create_by TEXT,
    update_by TEXT,
    register_city TEXT,
    vip_week_card_buy_flag REAL,
    pay_currency TEXT,
    system_support_amount REAL,
    pay_category TEXT,
    pay_address TEXT,
    fee REAL,
    crypto_amount REAL,
    crypto_received_amount REAL,
    create_time TEXT,
    update_time TEXT,
    package_id REAL
)
""")
cur.execute("CREATE INDEX idx_dep_user ON deposits(user_id)")
cur.execute("CREATE INDEX idx_dep_time ON deposits(create_time)")

dep_rows = load_sheet("/Users/devtr/Downloads/water_1782976595001.xlsx")
cur.executemany(f"INSERT INTO deposits VALUES ({','.join(['?']*35)})", [clean(r) for r in dep_rows])
conn.commit()
print("deposits:", len(dep_rows))

# ---------------- withdrawals (withdraw_*.xlsx) ----------------
cur.execute("""
CREATE TABLE withdrawals (
    payment_channel TEXT,
    risk_reason_list TEXT,
    user_register_channel_id TEXT,
    cf_ip_register_city TEXT,
    bank_name_bdt TEXT,
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    withdraw_amount REAL,
    received_amount REAL,
    order_no TEXT,
    bank_number TEXT,
    bank_name TEXT,
    channel_id REAL,
    upi TEXT,
    ifsc_code TEXT,
    update_date TEXT,
    status INTEGER,
    pay_error_info TEXT,
    application_time TEXT,
    review_time TEXT,
    callback_time TEXT,
    card_withdrawal_users REAL,
    member_level TEXT,
    channel_order_id TEXT,
    payment_center_order_id TEXT,
    if_risk_flag TEXT,
    pay_address TEXT,
    pay_currency TEXT,
    pay_category TEXT,
    system_support_amount REAL,
    crypto_amount REAL,
    crypto_received_amount REAL,
    manual_transfer_img TEXT,
    create_time TEXT,
    update_time TEXT,
    package_id REAL
)
""")
cur.execute("CREATE INDEX idx_wd_user ON withdrawals(user_id)")
cur.execute("CREATE INDEX idx_wd_time ON withdrawals(create_time)")

wd_rows = load_sheet("/Users/devtr/Downloads/withdraw_1782976617016.xlsx")
cur.executemany(f"INSERT INTO withdrawals VALUES ({','.join(['?']*36)})", [clean(r) for r in wd_rows])
conn.commit()
print("withdrawals:", len(wd_rows))
# status: 0 Under review, 1 Payment processing, 2 Completed, 3 Rejected, 4 Failed

# ---------------- wallet_transactions (detail_*.xlsx) ----------------
cur.execute("""
CREATE TABLE wallet_transactions (
    id INTEGER PRIMARY KEY,
    game_name TEXT,
    user_id INTEGER,
    consume_type TEXT,
    direction INTEGER,
    change_value REAL,
    change_after REAL,
    change_desc REAL,
    source_id TEXT,
    user_phone TEXT,
    table_name TEXT,
    create_date REAL,
    source TEXT,
    tripartite_uniqueness TEXT,
    l1_category_id REAL,
    l2_category_id REAL,
    status TEXT,
    create_time TEXT,
    update_time TEXT,
    package_id REAL
)
""")
cur.execute("CREATE INDEX idx_wt_user ON wallet_transactions(user_id)")
cur.execute("CREATE INDEX idx_wt_time ON wallet_transactions(create_time)")
cur.execute("CREATE INDEX idx_wt_game ON wallet_transactions(game_name)")

wt_total = 0
for f in ["/Users/devtr/Downloads/detail_1782976836062.xlsx", "/Users/devtr/Downloads/detail_1782976976094.xlsx"]:
    rows = load_sheet(f)
    cur.executemany(f"INSERT OR IGNORE INTO wallet_transactions VALUES ({','.join(['?']*20)})", [clean(r) for r in rows])
    wt_total += len(rows)
    conn.commit()
print("wallet_transactions rows loaded (raw):", wt_total)

cur.execute("SELECT COUNT(*) FROM wallet_transactions")
print("wallet_transactions unique rows in DB:", cur.fetchone()[0])

# ---------------- bonuses classification ----------------
# Only names that are unambiguously bonus/promo payouts (not real-money game names that
# happen to share a label with a promo *category* in the activity list, e.g. "Crazy Time"
# and "Ice Fishing" are real games — tagging every play of those as a bonus is wrong).
CANONICAL_BONUSES = [
    "Welcome Back Bonus", "Loyalty Bonus", "First deposit", "Second Deposit",
    "Third deposit", "Fourth deposit", "Low VIP", "Mid VIP", "High VIP", "Super VIP",
    "Evolution Live Betting Bonus", "Daily Active Bonus", "Daily Active Bonus Low",
]

cur.execute("""
CREATE TABLE bonuses (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    bonus_name TEXT,
    matched_category TEXT,
    change_value REAL,
    change_after REAL,
    create_time TEXT,
    source TEXT
)
""")
cur.execute("CREATE INDEX idx_bonus_user ON bonuses(user_id)")
cur.execute("CREATE INDEX idx_bonus_name ON bonuses(bonus_name)")

def normalize(s):
    return re.sub(r"\s+", " ", str(s).strip().lower())

canon_norm = {normalize(c): c for c in CANONICAL_BONUSES}
DEPOSIT_ORDINAL = re.compile(r"^(first|second|third|fourth|fifth)\s+deposit$", re.I)
VIP_TIER = re.compile(r"^(low|mid|high|super)\s*vip$", re.I)
VIP_WEEK_OR_LEVEL = re.compile(r"vip\s*(week|level)", re.I)

cur.execute("SELECT id, game_name, user_id, change_value, change_after, create_time, source FROM wallet_transactions WHERE game_name IS NOT NULL AND game_name != ''")
bonus_rows = []
for _id, game_name, user_id, change_value, change_after, create_time, source in cur.fetchall():
    norm = normalize(game_name)
    matched_category = None
    if norm in canon_norm:
        matched_category = canon_norm[norm]
    elif DEPOSIT_ORDINAL.match(str(game_name).strip()):
        matched_category = game_name
    elif VIP_TIER.match(str(game_name).strip()):
        matched_category = game_name
    elif VIP_WEEK_OR_LEVEL.search(str(game_name)):
        matched_category = game_name
    elif "bonus" in norm and ":" not in str(game_name):
        # colon-separated titles (e.g. "Lion Gems: Hold and Win", "Clover Charm: Hit the
        # Bonus") are real slot game names in this dataset, not wallet bonus payouts
        matched_category = game_name
    if matched_category:
        bonus_rows.append((_id, user_id, game_name, matched_category, change_value, change_after, create_time, source))

cur.executemany(
    "INSERT INTO bonuses (id, user_id, bonus_name, matched_category, change_value, change_after, create_time, source) VALUES (?,?,?,?,?,?,?,?)",
    bonus_rows,
)
conn.commit()
print("bonuses classified:", len(bonus_rows))

cur.execute("SELECT bonus_name, COUNT(*), SUM(change_value) FROM bonuses GROUP BY bonus_name ORDER BY 2 DESC")
for row in cur.fetchall():
    print(row)

conn.close()
print("Done ->", DB_PATH)
