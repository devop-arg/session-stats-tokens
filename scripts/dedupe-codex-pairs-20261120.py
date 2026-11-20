#!/usr/bin/env python3
"""Dedupe de sesiones Codex duplicadas (pares codex_<uuid> / <uuid>).

Origen del bug: el modo display (session-stats sin args) guardaba la sesión
Codex activa con el UUID pelado, mientras --capture-all guarda codex_<uuid>.
Resultado: pares con el mismo consumo contado dos veces.

Este script conserva SIEMPRE la copia codex_ (la que mantiene el cron con la
reconstrucción completa) y borra la copia pelada.

Uso:
  python3 scripts/dedupe-codex-pairs-20261120.py            # dry-run
  python3 scripts/dedupe-codex-pairs-20261120.py --apply
"""
import argparse
import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from stats_common import DB_PATH, backup_db  # noqa: E402

FIND_PAIRS = """
SELECT s_pref.id, s_bare.id, s_pref.timestamp
FROM sessions s_pref
JOIN sessions s_bare
  ON s_bare.id = REPLACE(s_pref.id, 'codex_', '')
 AND s_bare.source = 'codex'
 AND s_bare.timestamp = s_pref.timestamp
WHERE s_pref.source = 'codex' AND s_pref.id LIKE 'codex_%'
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="borra las copias peladas (default: dry-run)")
    args = ap.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys=ON")
    rows = conn.execute(FIND_PAIRS).fetchall()
    if not rows:
        print("no hay pares duplicados")
        return 0

    excess = 0.0
    print("== pares (se conserva codex_, se borra la pelada) ==")
    for pref, bare, ts in rows:
        c_pref = conn.execute("SELECT ROUND(cost,4), input_tokens, output_tokens, cache_tokens FROM sessions WHERE id=?", (pref,)).fetchone()
        c_bare = conn.execute("SELECT ROUND(cost,4), input_tokens, output_tokens, cache_tokens FROM sessions WHERE id=?", (bare,)).fetchone()
        excess += min(c_pref[0], c_bare[0])
        print("  %-50s cost=%.4f (in=%d out=%d cache=%d)" % (pref, c_pref[0], c_pref[1], c_pref[2], c_pref[3]))
        print("  %-50s cost=%.4f (in=%d out=%d cache=%d)  <-- BORRAR" % (bare, c_bare[0], c_bare[1], c_bare[2], c_bare[3]))
    print("\ndoble conteo a eliminar: $%.4f" % excess)

    if not args.apply:
        conn.close()
        print("\ndry-run: nada escrito. Usar --apply para borrar.")
        return 0

    backup_db(keep=99)
    with conn:
        for pref, bare, ts in rows:
            # La FK ON DELETE CASCADE limpia model_usage; foreign_keys=ON.
            cur = conn.execute("DELETE FROM sessions WHERE id=?", (bare,))
            print("  borrada %s (rows=%d)" % (bare, cur.rowcount))
    sess = conn.execute("SELECT ROUND(SUM(cost),4) FROM sessions").fetchone()[0]
    mu = conn.execute("SELECT ROUND(SUM(cost),4) FROM model_usage").fetchone()[0]
    n_pref = conn.execute("SELECT COUNT(*) FROM sessions WHERE source='codex' AND id NOT LIKE 'codex_%'").fetchone()[0]
    conn.close()
    print("\npost-dedupe: sessions=%.4f model_usage=%.4f gap=%+.4f | codex sin prefijo restantes: %d"
          % (sess, mu, sess - mu, n_pref))
    return 0


if __name__ == "__main__":
    sys.exit(main())
