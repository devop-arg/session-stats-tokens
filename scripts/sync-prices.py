#!/usr/bin/env python3
"""Sync de precios contra models.dev (https://models.dev/api.json).

- --dry-run (default): reporta (1) modelos PENDIENTES (0/0/0) con uso que se
  pueden completar desde models.dev y (2) drift de los ya precio-ados.
  No escribe nada.
- --apply-pending: completa SOLO pendientes con uso cuyo precio matcheado sea
  no-cero. Nunca toca entradas ya precio-adas ni reporta drift como acción.

Prioridad de providers: opencode-go (la suscripción real) > anthropic >
openai > openrouter. Los tiers/context_over_200k NO se aplican: la DB no
guarda el tamaño de contexto por request, así que el precio plano es lo único
facturable (ver README).
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from stats_common import (  # noqa: E402
    DB_PATH, MODEL_COSTS_FILE,
    normalize_model_name, reload_model_costs,
)

API_URL = "https://models.dev/api.json"
CACHE = Path("/tmp/models_dev_api.json")
PROVIDER_PRIORITY = ["opencode-go", "anthropic", "openai", "openrouter"]


def price_from_cost(cost):
    """Convierte el formato 'cost' de models.dev al esquema de model_costs."""
    if not cost:
        return None
    entry = {}
    if cost.get("input") is None or cost.get("output") is None:
        return None
    entry["input"] = cost["input"]
    entry["output"] = cost["output"]
    if cost.get("cache_read") is not None:
        entry["cache"] = cost["cache_read"]
    if cost.get("cache_write"):
        entry["cache_write"] = cost["cache_write"]
    return entry


def build_report(costs, used_canon, api):
    """Pure. Devuelve (fills, drift, no_match) para los canónicos usados.

    fills: pendientes (0/0/0 sin marcador free) con precio no-cero matcheado.
    drift: precio-ados cuyo input/output difiere del matcheado (solo reporte).
    no_match: sin entrada en ningún provider de la prioridad.
    """
    fills, drift, no_match = [], [], []
    for canon in sorted(used_canon):
        entry = costs.get(canon) or {}
        if entry.get("free", False):
            continue  # gratis confirmada: no es pendiente ni drift
        pending = entry.get("input", 0) == 0 and entry.get("output", 0) == 0
        matched = None
        for p in PROVIDER_PRIORITY:
            m = api.get(p, {}).get("models", {}).get(canon)
            if m:
                matched = (p, m)
                break
        if not matched:
            no_match.append(canon)
            continue
        p, m = matched
        price = price_from_cost(m.get("cost"))
        if pending:
            if price and (price["input"] or price["output"]):
                fills.append({"model": canon, "provider": p, "price": price})
            continue
        if price and entry.get("input") is not None:
            if (abs(price["input"] - entry["input"]) > 1e-9
                    or abs(price["output"] - entry["output"]) > 1e-9):
                drift.append({
                    "model": canon, "provider": p,
                    "ours": {k: entry[k] for k in ("input", "output") if k in entry},
                    "dev": {k: price[k] for k in ("input", "output")},
                })
    return fills, drift, no_match


def fetch_api():
    import datetime
    fresh = False
    if CACHE.exists():
        age_h = (datetime.datetime.now().timestamp() - CACHE.stat().st_mtime) / 3600
        fresh = age_h < 24
    if fresh:
        return json.loads(CACHE.read_text())
    req = urllib.request.Request(
        API_URL, headers={"User-Agent": "session-stats-sync/1.0",
                          "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            api = json.load(r)
        CACHE.write_text(json.dumps(api))
        return api
    except Exception as e:
        if CACHE.exists():
            print(f"[WARN] models.dev inaccesible ({e}); uso caché local {CACHE}")
            return json.loads(CACHE.read_text())
        raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply-pending", action="store_true",
                    help="escribe los fills (solo pendientes con uso y precio no-cero)")
    args = ap.parse_args()

    import sqlite3
    reload_model_costs()
    from stats_common import MODEL_COSTS
    costs = dict(MODEL_COSTS)
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    used_canon = set()
    for (raw,) in conn.execute(
        "SELECT DISTINCT mu.model FROM model_usage mu JOIN sessions s ON s.id=mu.session_id"
        " WHERE s.source != 'legacy'"
    ):
        used_canon.add(normalize_model_name(raw))
    conn.close()

    api = fetch_api()
    fills, drift, no_match = build_report(costs, used_canon, api)

    print("== pendientes completables (%d) ==" % len(fills))
    for f in fills:
        print("  %-32s %-12s -> %s" % (f["model"], f["provider"], f["price"]))
    print("\n== drift (SOLO reporte, no se escribe) (%d) ==" % len(drift))
    for d in drift:
        print("  %-32s %-12s ours=%s dev=%s" % (d["model"], d["provider"], d["ours"], d["dev"]))
    print("\n== sin match en models.dev (%d) ==" % len(no_match))
    for m in no_match:
        print("  ", m)

    if not args.apply_pending:
        print("\ndry-run: nada escrito.")
        return 0

    if not fills:
        print("\nnada para aplicar.")
        return 0

    import fcntl
    import datetime
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = SCRIPT_DIR / "model_backups"
    backup_dir.mkdir(exist_ok=True)
    for src in (MODEL_COSTS_FILE,):
        (backup_dir / f"{src.stem}_pre_sync_{ts}{src.suffix}").write_text(src.read_text())

    lock = MODEL_COSTS_FILE.with_suffix(".json.lock")
    with open(lock, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            costs_disk = json.loads(MODEL_COSTS_FILE.read_text())
            changed = 0
            for f in fills:
                m = f["model"]
                e = costs_disk.setdefault(m, {})
                if e.get("input", 0) == 0 and e.get("output", 0) == 0:
                    e.clear()
                    e.update(f["price"])
                    changed += 1
            MODEL_COSTS_FILE.write_text(json.dumps(costs_disk, indent=2) + "\n")
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)
    print(f"\naplicados {changed} precios pendientes (backup en model_backups/*_pre_sync_{ts}.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
