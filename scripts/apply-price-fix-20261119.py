#!/usr/bin/env python3
"""Aplica el fix de precios 2026-11-19 a model_costs.json / model_aliases.json.

- 8 modelos pagos que estaban en 0/0/0 con uso.
- alias gemini-3.1-flash-lite-preview -> gemini-3.1-flash-lite (y se borra su entrada 0).
- entradas 0 para las variantes -free de los modelos que se precio-an
  (normalize_model_name las mandaría al precio pagado).
- 8 modelos pagos del catálogo opencode-go sin entrada.

No dispara recálculo: el recálculo es explícito (preview -> confirm -> apply).
Escribe con indent=2 sin sort_keys para minimizar el diff.
"""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
from stats_common import MODEL_COSTS_FILE, MODEL_ALIASES_FILE  # noqa: E402

PRICES = {
    # pagos que estaban en 0/0/0 con uso
    "claude-fable-5-2": {"input": 8, "output": 40, "cache": 0.2, "cache_write": 10},
    "claude-sonnet-5-5": {"input": 2, "output": 10, "cache": 0.1, "cache_write": 2.5},
    "gpt-6.1-sol": {"input": 2, "output": 10, "cache": 0.1, "cache_write": 2.5},
    "step-5-preview": {"input": 1, "output": 2.7, "cache": 0.1},
    "mimo-v2.6-flash": {"input": 0.14, "output": 0.28, "cache": 0.0028},
    "gpt-5-nano": {"input": 0.05, "output": 0.4, "cache": 0.005},
    "hy4-flash": {"input": 0.035, "output": 0.1405, "cache": 0.0015},
    # variantes free de los modelos de arriba (0 real, no pendiente)
    "step-5-preview-free": {"input": 0.0, "output": 0.0, "cache": 0.0},
    "mimo-v2.6-flash-free": {"input": 0.0, "output": 0.0, "cache": 0.0},
    "hy4-flash-free": {"input": 0.0, "output": 0.0, "cache": 0.0},
    # catálogo opencode-go sin entrada
    "mimo-v2.6-pro": {"input": 0.435, "output": 0.87, "cache": 0.003625},
    "kimi-k3.1-pro": {"input": 2, "output": 10, "cache": 0.2, "cache_write": 2},
    "qwen4-max": {"input": 1.5, "output": 4.5, "cache": 0.075, "cache_write": 1.875},
    "gemini-4-argon": {"input": 2, "output": 10, "cache": 0.1},
    "gemini-4-argon-contributor": {"input": 4, "output": 20, "cache": 0.2},
    "grok-4.7": {"input": 2, "output": 6, "cache": 0.5},
    "hy4": {"input": 0.834, "output": 2.501, "cache": 0.042},
    "hy4-preview": {"input": 0.834, "output": 2.501, "cache": 0.042},
}

DELETE = ["gemini-3.1-flash-lite-preview"]

ALIASES = {
    "gemini-3.1-flash-lite-preview": "gemini-3.1-flash-lite",
    # variantes free: mapear a su propio canon en 0 para que el strip de
    # -free no las cobre como pagas
    "step-5-preview-free": "step-5-preview-free",
    "mimo-v2.6-flash-free": "mimo-v2.6-flash-free",
    "hy4-flash-free": "hy4-flash-free",
}


def main():
    import fcntl
    costs_lock = MODEL_COSTS_FILE.with_suffix(MODEL_COSTS_FILE.suffix + ".lock")
    aliases_lock = MODEL_ALIASES_FILE.with_suffix(MODEL_ALIASES_FILE.suffix + ".lock")
    with open(costs_lock, "w") as lf1, open(aliases_lock, "w") as lf2:
        # Read-modify-write bajo el mismo flock que el cron (_atomic_write_costs)
        # y la UI: si se leen los JSON fuera del lock, un seed del cron que corra
        # en el medio se pierde.
        fcntl.flock(lf1, fcntl.LOCK_EX)
        fcntl.flock(lf2, fcntl.LOCK_EX)
        try:
            costs = json.loads(MODEL_COSTS_FILE.read_text())
            aliases = json.loads(MODEL_ALIASES_FILE.read_text())

            before = {k: dict(costs.get(k, {})) for k in PRICES}
            removed = {k: dict(costs[k]) for k in DELETE if k in costs}

            for k, v in PRICES.items():
                costs[k] = dict(v)
            for k in DELETE:
                costs.pop(k, None)
            aliases.update(ALIASES)

            for path, data in ((MODEL_COSTS_FILE, costs), (MODEL_ALIASES_FILE, aliases)):
                with open(path, "w") as fh:
                    fh.write(json.dumps(data, indent=2) + "\n")
                    fh.flush()
                    import os
                    os.fsync(fh.fileno())
        finally:
            fcntl.flock(lf2, fcntl.LOCK_UN)
            fcntl.flock(lf1, fcntl.LOCK_UN)

    print("== cambios de precio ==")
    for k in sorted(PRICES):
        print(f"  {k:32} {before.get(k) or '(nuevo)'} -> {PRICES[k]}")
    print("== eliminados ==")
    for k in sorted(removed):
        print(f"  {k:32} {removed[k]}")
    print("== aliases ==")
    for k, v in ALIASES.items():
        print(f"  {k} -> {v}")
    print(f"\nmodel_costs.json: {len(costs)} entradas; model_aliases.json: {len(aliases)}")


if __name__ == "__main__":
    main()
