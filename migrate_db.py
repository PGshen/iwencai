import sqlite3
import os

db_path = "./data/app.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Adding columns to business_templates...")
for stmt in [
    "ALTER TABLE business_templates ADD COLUMN extract_type VARCHAR(20) DEFAULT 'python'",
    "ALTER TABLE business_templates ADD COLUMN json_path TEXT",
    "ALTER TABLE business_templates ADD COLUMN proxy_config_id VARCHAR(36)",
    "ALTER TABLE business_templates ADD COLUMN cookie_config_id VARCHAR(36)",
    "ALTER TABLE business_templates ADD COLUMN header_group_id VARCHAR(36)",
]:
    try:
        cursor.execute(stmt)
    except sqlite3.OperationalError as e:
        print(f"business_templates: {e}")

try:
    # Add columns to scrape_configs
    print("Adding columns to scrape_configs...")
    cursor.execute("ALTER TABLE scrape_configs ADD COLUMN extract_type VARCHAR(20) DEFAULT 'python'")
    cursor.execute("ALTER TABLE scrape_configs ADD COLUMN json_path TEXT")
except sqlite3.OperationalError as e:
    print(f"scrape_configs: {e}")

print("Adding columns to scrape_history...")
for stmt in [
    "ALTER TABLE scrape_history ADD COLUMN request_headers TEXT",
    "ALTER TABLE scrape_history ADD COLUMN request_body TEXT",
    "ALTER TABLE scrape_history ADD COLUMN raw_response TEXT",
    "ALTER TABLE scrape_history ADD COLUMN api_request_headers TEXT",
    "ALTER TABLE scrape_history ADD COLUMN api_request_params TEXT",
    "ALTER TABLE scrape_history ADD COLUMN api_request_body TEXT",
]:
    try:
        cursor.execute(stmt)
    except sqlite3.OperationalError as e:
        print(f"scrape_history: {e}")

# Add name column to proxy_configs if missing
try:
    print("Adding column 'name' to proxy_configs...")
    cursor.execute("ALTER TABLE proxy_configs ADD COLUMN name VARCHAR(100)")
    # Initialize existing rows with a generated name
    cursor.execute("UPDATE proxy_configs SET name = COALESCE(name, ip || ':' || port)")
except sqlite3.OperationalError as e:
    print(f"proxy_configs: {e}")

# Ensure unique index on push_configs.name
try:
    print("Creating unique index on push_configs(name)...")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_push_configs_name ON push_configs(name)")
except sqlite3.OperationalError as e:
    print(f"push_configs index: {e}")

conn.commit()
conn.close()
print("Migration completed.")

# Additional migration for batch tasks
try:
    print("Adding columns to batch_tasks...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE batch_tasks ADD COLUMN status VARCHAR(20) DEFAULT 'pending'")
    cursor.execute("ALTER TABLE batch_tasks ADD COLUMN save_fields TEXT")
    cursor.execute("ALTER TABLE batch_tasks ADD COLUMN data_json_path TEXT")
    conn.commit()
    conn.close()
except sqlite3.OperationalError as e:
    print(f"batch_tasks: {e}")
