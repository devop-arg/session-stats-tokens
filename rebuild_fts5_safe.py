#!/usr/bin/env python3
"""
rebuild_fts5_safe.py — Reconstruye el indice FTS5 corrupto de state.db
SIN BORRAR NADA y SIN TOCAR el state.db original.

Estrategia:
  1. Copiar state.db a /tmp/state_repair_<ts>.db  (el original jamas se toca)
  2. Sobre la COPIA: REINDEX del FTS5 trigram + integrity_check
  3. Reportar resultado. NO reemplaza el original bajo ningun concepto.

No requiere parar el gateway: la copia se hace con cp (snapshot del FS),
y el rebuild corre sobre el archivo aislado en /tmp.

Uso:
  python3 rebuild_fts5_safe.py          # hace la copia + rebuild + chequeo
  python3 rebuild_fts5_safe.py --check  # solo integrity_check de la ultima copia
"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime

SRC = "/home/capw/.hermes/state.db"
TMP_DIR = "/tmp"

FTS_TABLES = [
    "messages_fts",
    "messages_fts_trigram",
]


def stamped_path():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(TMP_DIR, f"state_repair_{ts}.db")


def latest_copy():
    copies = sorted(
        f for f in os.listdir(TMP_DIR)
        if f.startswith("state_repair_") and f.endswith(".db")
    )
    return os.path.join(TMP_DIR, copies[-1]) if copies else None


def integrity(db_path):
    """Devuelve (ok: bool, lines: list)."""
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = db.execute("PRAGMA integrity_check").fetchall()
    finally:
        db.close()
    lines = [r[0] for r in rows]
    return (lines == ["ok"], lines)


def do_copy_and_rebuild():
    # 1. snapshot
    dst = stamped_path()
    print(f"[1/4] Copiando {SRC} -> {dst}")
    shutil.copy2(SRC, dst)
    print(f"      copiaLista ({os.path.getsize(dst)} bytes)")

    # 2. rebuild FTS5 sobre la copia (REINDEX no borra filas, solo reconstruye indices)
    print(f"[2/4] REINDEX de tablas FTS5 sobre la copia...")
    db = sqlite3.connect(dst)
    try:
        # Forzar rebuild del indice FTS interno
        for t in FTS_TABLES:
            try:
                db.execute(f"REINDEX {t}")
                print(f"      REINDEX {t}: ok")
            except Exception as e:
                print(f"      REINDEX {t}: {type(e).__name__}: {e}")
        # Tambien rebuild de todos los indices por las dudas
        db.execute("REINDEX")
        db.commit()
        print("      REINDEX global: ok")
    finally:
        db.close()

    # 3. integrity check sobre la copia reparada
    print(f"[3/4] integrity_check sobre la copia reparada...")
    ok, lines = integrity(dst)
    if ok:
        print("      ✅ integrity_check = ok  (corrupcion FTS5 reparada en la copia)")
    else:
        print("      ⚠️  integrity_check sigue con errores:")
        for ln in lines[:10]:
            print("        -", ln)

    # 4. resumen
    print(f"[4/4] HECHO. El state.db original NO fue modificado.")
    print(f"      Copia reparada en: {dst}")
    print(f"      Para usarla (SOLO con gateway parado, a tu criterio):")
    print(f"        sudo systemctl stop hermes-gateway")
    print(f"        cp {dst} {SRC}")
    print(f"        sudo systemctl start hermes-gateway")
    return ok


def main():
    if "--check" in sys.argv:
        c = latest_copy()
        if not c:
            print("No hay copia previa en /tmp/state_repair_*.db")
            sys.exit(1)
        print(f"integrity_check de {c}:")
        ok, lines = integrity(c)
        print("  ok" if ok else "\n".join("  - " + l for l in lines))
        sys.exit(0 if ok else 1)
    do_copy_and_rebuild()


if __name__ == "__main__":
    main()
