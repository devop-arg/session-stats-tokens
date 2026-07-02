#!/usr/bin/env python3
"""Migra cache_tokens históricos a cache_read_tokens y cache_write_tokens."""
import sys
import sqlite3
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from stats_common import init_db, DB_PATH

init_db()
conn = sqlite3.connect(str(DB_PATH))

# Sessions
updated_s = conn.execute("""
    UPDATE sessions SET
        cache_read_tokens = cache_tokens,
        cache_write_tokens = 0
    WHERE cache_read_tokens = 0 AND cache_write_tokens = 0
""").rowcount

# Model usage
updated_mu = conn.execute("""
    UPDATE model_usage SET
        cache_read_tokens = cache_tokens,
        cache_write_tokens = 0
    WHERE cache_read_tokens = 0 AND cache_write_tokens = 0
""").rowcount

conn.commit()

legacy_s = conn.execute(
    "SELECT COUNT(*) FROM sessions WHERE cache_read_tokens = 0 AND cache_tokens > 0"
).fetchone()[0]
legacy_mu = conn.execute(
    "SELECT COUNT(*) FROM model_usage WHERE cache_read_tokens = 0 AND cache_tokens > 0"
).fetchone()[0]

total_s = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
total_mu = conn.execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]

conn.close()

print(f"Sessions: {total_s} total, {updated_s} migradas, {legacy_s} legacy")
print(f"Model usage: {total_mu} total, {updated_mu} migradas, {legacy_mu} legacy")

if legacy_s > 0 or legacy_mu > 0:
    print("⚠️ Quedan filas sin migrar (cache_tokens sin dividir)")
    sys.exit(1)
else:
    print("✅ Migración completa")
