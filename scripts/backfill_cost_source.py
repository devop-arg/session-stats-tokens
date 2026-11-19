#!/usr/bin/env python3
"""Backfill de sessions.cost_source.

reported: sesiones Claude con cost-state válido (has_real_cost, según el JSONL
vigente, misma semántica que la captura) y también las Claude SIN JSONL
(conservador: el recálculo no las toca). estimated: el resto.

Uso:
  python3 scripts/backfill_cost_source.py --dry-run
  python3 scripts/backfill_cost_source.py --apply
"""
import argparse
import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from stats_common import DB_PATH, get_claude_sessions, get_claude_session_stats  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="solo muestra el plan")
    ap.add_argument("--apply", action="store_true", help="escribe cost_source")
    args = ap.parse_args()
    if not (args.dry_run or args.apply):
        args.dry_run = True
        print("sin --apply: modo dry-run\n")

    conn = sqlite3.connect(str(DB_PATH))
    cols = {r[1] for r in conn.execute("PRAGMA table_info(sessions)")}
    if "cost_source" not in cols:
        print("ERROR: falta la columna sessions.cost_source (correr init_db)")
        return 1

    # Costos facturados por JSONL vigente (misma función que usa la captura).
    jsonl_state = {}
    for sess in get_claude_sessions():
        try:
            st = get_claude_session_stats(sess)
        except Exception:
            continue
        jsonl_state["claude_" + sess["session_id"]] = bool(st.get("has_real_cost"))

    plan = []
    for (sid,) in conn.execute("SELECT id FROM sessions WHERE source='claude'").fetchall():
        if sid in jsonl_state:
            cs = "reported" if jsonl_state[sid] else "estimated"
        else:
            cs = "reported"  # conservador: sin JSONL no se puede re-capturar
        plan.append((cs, sid))
    for (sid,) in conn.execute("SELECT id FROM sessions WHERE source!='claude'").fetchall():
        plan.append(("estimated", sid))

    n_rep = sum(1 for cs, _ in plan if cs == "reported")
    n_est = len(plan) - n_rep
    print(f"plan: {len(plan)} sesiones -> reported={n_rep} estimated={n_est}")
    rep_ids = sorted(s for cs, s in plan if cs == "reported")
    print("reported (claude):")
    for s in rep_ids:
        print(f"   {s}")

    if args.dry_run:
        conn.close()
        return 0

    with conn:
        conn.executemany(
            "UPDATE sessions SET cost_source=? WHERE id=?", plan
        )
    counts = conn.execute(
        "SELECT cost_source, COUNT(*) FROM sessions GROUP BY cost_source"
    ).fetchall()
    conn.close()
    print("aplicado. cost_source por grupo:")
    for cs, n in counts:
        print(f"   {cs}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
