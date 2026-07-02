#!/usr/bin/env python3
"""Recalcula todos los costos almacenados en session_history.db
con el nuevo calculate_cost() que maneja correctamente input vs cache.

USO: session-stats/scripts/fix-costs.py [--dry-run]

--dry-run: muestra cambios sin escribir a DB.
"""
import sys
import sqlite3
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))
from stats_common import calculate_cost, DB_PATH

DRY_RUN = "--dry-run" in sys.argv

def main():
    db_path = DB_PATH
    if not db_path.exists():
        print(f"DB no encontrada: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # 1. Recalcular model_usage
    rows = conn.execute(
        "SELECT session_id, model, requests, input_tokens, output_tokens, cache_tokens, cost "
        "FROM model_usage"
    ).fetchall()

    updates = []
    total_old = 0
    total_new = 0
    changed = 0

    for r in rows:
        new_cost = calculate_cost(r["model"], r["input_tokens"], r["output_tokens"], r["cache_tokens"])
        old_cost = r["cost"]
        total_old += old_cost
        total_new += new_cost
        if abs(new_cost - old_cost) > 0.0001:
            changed += 1
            updates.append((new_cost, r["session_id"], r["model"]))

    if DRY_RUN:
        print("=== DRY RUN ===")
        print(f"Registros revisados: {len(rows)}")
        print(f"Cambiarían: {changed}")
        print(f"Costo total actual: ${total_old:.4f}")
        print(f"Costo total nuevo:  ${total_new:.4f}")
        print(f"Diferencia: ${total_new - total_old:.4f}")
    else:
        print(f"Actualizando {changed} registros en model_usage...")
        c = conn.cursor()
        for new_cost, sid, model in updates:
            c.execute(
                "UPDATE model_usage SET cost = ? WHERE session_id = ? AND model = ?",
                (new_cost, sid, model)
            )
        conn.commit()

        # 2. Recalcular costos por sesion
        print("Recalculando costos por sesion...")
        sess_rows = conn.execute(
            "SELECT s.id, COALESCE(SUM(mu.cost), 0) as total_cost "
            "FROM sessions s "
            "LEFT JOIN model_usage mu ON mu.session_id = s.id "
            "GROUP BY s.id"
        ).fetchall()
        for sr in sess_rows:
            conn.execute(
                "UPDATE sessions SET cost = ? WHERE id = ?",
                (sr["total_cost"], sr["id"])
            )
        conn.commit()

        print("Listo.")

    conn.close()

if __name__ == "__main__":
    main()
