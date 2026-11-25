import sqlite3
import os

def migrate(path):
    if not os.path.exists(path):
        print(f"Skipping {path} (does not exist)")
        return
    print(f"Migrating {path}...")
    conn = sqlite3.connect(path)
    cur = conn.cursor()

    def get_cols(tbl):
        try:
            cur.execute(f"PRAGMA table_info({tbl})")
            return [c[1] for c in cur.fetchall()]
        except Exception:
            return []

    # 1. users
    u_cols = get_cols("users")
    add_u = [
        ("is_verified", "BOOLEAN DEFAULT 0"),
        ("email_verification_token", "VARCHAR(255)"),
        ("email_verification_expires_at", "DATETIME"),
        ("password_reset_token", "VARCHAR(255)"),
        ("password_reset_expires_at", "DATETIME"),
        ("role", "VARCHAR(128) DEFAULT 'Data Analyst'"),
        ("primary_goal", "JSON DEFAULT '[]'"),
        ("experience_level", "VARCHAR(64) DEFAULT 'Intermediate'"),
        ("preferences", "JSON DEFAULT '{}'"),
        ("onboarding_completed", "BOOLEAN DEFAULT 0"),
        ("avatar_url", "VARCHAR(255)"),
        ("last_login_at", "DATETIME"),
    ]
    for col, typ in add_u:
        if col not in u_cols:
            print(f"Adding {col} to users")
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")

    # Mark existing demo user as verified and completed onboarding
    cur.execute("UPDATE users SET is_verified = 1, onboarding_completed = 1 WHERE email = 'demo@analyticx.ai'")

    # 2. datasets
    d_cols = get_cols("datasets")
    add_d = [
        ("user_id", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ("workspace_id", "INTEGER REFERENCES workspaces(id) ON DELETE SET NULL"),
        ("is_sample", "BOOLEAN DEFAULT 0"),
    ]
    for col, typ in add_d:
        if col not in d_cols:
            print(f"Adding {col} to datasets")
            cur.execute(f"ALTER TABLE datasets ADD COLUMN {col} {typ}")

    # Mark existing datasets #1-#5 as sample datasets
    cur.execute("UPDATE datasets SET is_sample = 1 WHERE id <= 5")
    # Assign existing datasets to demo user (user_id=1) if unassigned
    cur.execute("UPDATE datasets SET user_id = 1 WHERE user_id IS NULL")

    # 3. dashboards
    db_cols = get_cols("dashboards")
    if "user_id" not in db_cols:
        print("Adding user_id to dashboards")
        cur.execute("ALTER TABLE dashboards ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL")
    cur.execute("UPDATE dashboards SET user_id = 1 WHERE user_id IS NULL")

    # 4. notifications
    n_cols = get_cols("notifications")
    add_n = [
        ("link", "VARCHAR(255)"),
        ("event_type", "VARCHAR(64) DEFAULT 'general'"),
    ]
    for col, typ in add_n:
        if col not in n_cols:
            print(f"Adding {col} to notifications")
            cur.execute(f"ALTER TABLE notifications ADD COLUMN {col} {typ}")

    # 5. user_activities table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        workspace_id INTEGER REFERENCES workspaces(id) ON DELETE SET NULL,
        action_type VARCHAR(64) NOT NULL,
        entity_type VARCHAR(64),
        entity_id INTEGER,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        details JSON,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_user_activities_user_id ON user_activities(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_user_activities_action_type ON user_activities(action_type)")

    conn.commit()
    conn.close()
    print(f"Migration complete for {path}")

if __name__ == "__main__":
    migrate("analyticx.db")
    migrate("backend/analyticx.db")
