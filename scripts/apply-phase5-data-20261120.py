#!/usr/bin/env python3
"""Datos de Fase 5 (2026-11-20): cache_write faltantes + variantes -free.

1. cache_write para 10 modelos precio-ados con uso (models.dev). Sin esto,
   hermes/codex/zcode cobran la escritura de cache al precio de input.
2. Variantes -free del catálogo (opencode-go + opencode): entrada 0/0/0 +
   alias a sí mismas para que normalize_model_name no las mande al canon
   pago. También repunta los aliases -free existentes que apuntaban a un
   canon pago (ej. "glm-5-free": "glm-5"). Solo afecta capturas futuras: el
   histórico ya está fundido en los canónicos pagos y no se toca.
   Exclusión: modelos -free que models.dev lista como pagos (ej.
   grok-code-fast-1-optimized-free).
"""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from stats_common import MODEL_COSTS_FILE, MODEL_ALIASES_FILE  # noqa: E402

API = Path("/tmp/models.json")

# cache_write verificados contra models.dev (provider entre paréntesis)
CACHE_WRITE = {
    "gpt-5.6-luna": 0.25,     # opencode-go
    "gpt-5.6-sol": 5.0,       # openai (merge-gateway igual)
    "gpt-5.6-terra": 2.5,      # openai
    "gpt-6-astra": 12.5,      # openai
    "gpt-6-luna": 0.125,      # opencode-go
    "kimi-k3": 3.0,           # opencode-go
    "minimax-m2.7": 0.375,    # opencode-go
    "qwen3.7-plus": 0.5,      # opencode-go
    "qwen3.8-flash": 0.2,     # opencode-go
    "qwen3.8-max": 2.5,       # opencode-go
}


def main():
    md = json.loads(API.read_text())
    costs = json.loads(MODEL_COSTS_FILE.read_text())
    aliases = json.loads(MODEL_ALIASES_FILE.read_text())

    # --- 1. cache_write ---
    cw_added = []
    for model, cw in CACHE_WRITE.items():
        entry = costs.get(model)
        if entry and "cache_write" not in entry and entry.get("input", 0) > 0:
            entry["cache_write"] = cw
            cw_added.append(model)

    # --- 2. variantes -free genuinamente gratis ---
    free_added, repointed = [], []
    for prov in ("opencode-go", "opencode"):
        for name, m in md.get(prov, {}).get("models", {}).items():
            if not name.endswith("-free"):
                continue
            c = m.get("cost") or {}
            if c.get("input") != 0 or c.get("output") != 0:
                continue  # models.dev la lista como paga (ej. grok-code-fast-1-optimized-free)
            tgt = aliases.get(name)
            tentry = costs.get(tgt) if tgt else None
            # ya está confirmada como free (mismo nombre o alias a un free)
            already_free = bool(tentry and tentry.get("input", 0) == 0
                                and tentry.get("output", 0) == 0
                                and tentry.get("free"))
            if already_free:
                # si le falta el marcador free (entradas 0/0/0 de ayer), agregarlo
                if tgt == name and not tentry.get("free"):
                    tentry["free"] = True
                    free_added.append(name)
                continue
            costs[name] = {"input": 0.0, "output": 0.0, "cache": 0.0, "free": True}
            aliases[name] = name
            if tgt and tgt != name:
                repointed.append((name, tgt))
            else:
                free_added.append(name)

    # --- write bajo flock + backup ---
    import fcntl
    import datetime
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = SCRIPT_DIR / "model_backups"
    bdir.mkdir(exist_ok=True)
    for src in (MODEL_COSTS_FILE, MODEL_ALIASES_FILE):
        (bdir / f"{src.stem}_pre_phase5_{ts}{src.suffix}").write_text(src.read_text())

    c_lock = MODEL_COSTS_FILE.with_suffix(".json.lock")
    a_lock = MODEL_ALIASES_FILE.with_suffix(".json.lock")
    with open(c_lock, "w") as lf1, open(a_lock, "w") as lf2:
        fcntl.flock(lf1, fcntl.LOCK_EX)
        fcntl.flock(lf2, fcntl.LOCK_EX)
        try:
            # re-read dentro del lock (read-modify-write, mismo patrón que la UI)
            costs = json.loads(MODEL_COSTS_FILE.read_text())
            aliases = json.loads(MODEL_ALIASES_FILE.read_text())
            for model, cw in CACHE_WRITE.items():
                entry = costs.get(model)
                if entry and "cache_write" not in entry and entry.get("input", 0) > 0:
                    entry["cache_write"] = cw
            for name in free_added + [n for n, _ in repointed]:
                costs[name] = {"input": 0.0, "output": 0.0, "cache": 0.0, "free": True}
                aliases[name] = name
            MODEL_COSTS_FILE.write_text(json.dumps(costs, indent=2) + "\n")
            MODEL_ALIASES_FILE.write_text(json.dumps(aliases, indent=2) + "\n")
        finally:
            fcntl.flock(lf2, fcntl.LOCK_UN)
            fcntl.flock(lf1, fcntl.LOCK_UN)

    print("== cache_write agregados (%d) ==" % len(cw_added))
    for m in cw_added:
        print("  %-22s cache_write=%s" % (m, CACHE_WRITE[m]))
    print("\n== variantes free nuevas (%d) ==" % len(free_added))
    for n in sorted(free_added):
        print("  ", n)
    print("\n== aliases -free repuntados de pago a free (%d) ==" % len(repointed))
    for n, old in sorted(repointed):
        print("  %-38s (era -> %s)" % (n, old))
    print("\nmodel_costs.json: %d entradas; model_aliases.json: %d" % (len(costs), len(aliases)))


if __name__ == "__main__":
    main()
