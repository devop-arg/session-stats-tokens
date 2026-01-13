#!/usr/bin/env python3
import json
import datetime
from pathlib import Path

# Costos por 1M tokens (en USD)
MODEL_COSTS = {
    "glm-4.7-free": {"input": 0.43, "output": 2.2},
    # Codex Max
    "gpt-5.1-codex-max": {"input": 1.25, "output": 10},
    "codex-max": {"input": 1.25, "output": 10},
    # Codex 5.2
    "gpt-5.2-codex": {"input": 1.75, "output": 14},
    # Claude
    "antigravity-claude-opus-4-5-thinking-high": {"input": 5, "output": 25},
    "claude-opus-4-5-thinking": {"input": 5, "output": 25},
    "antigravity-claude-sonnet-4-5": {"input": 3, "output": 15},
    "antigravity-claude-sonnet-4-5-thinking": {"input": 3, "output": 15},
    "claude-sonnet-4-5": {"input": 3, "output": 15},
    "claude-sonnet-4-5-thinking": {"input": 3, "output": 15},
    # Gemini
    "antigravity-gemini-3-flash": {"input": 0.5, "output": 3},
    "gemini-3-flash": {"input": 0.5, "output": 3},
    "antigravity-gemini-3-pro-low": {"input": 2, "output": 12},
    "antigravity-gemini-3-pro-high": {"input": 2, "output": 12},
    "antigravity-gemini-3-pro": {"input": 2, "output": 12},
    "gemini-3-pro-low": {"input": 2, "output": 12},
    "gemini-3-pro-high": {"input": 2, "output": 12},
    "gemini-3-pro": {"input": 2, "output": 12},
    # Grok
    "grok-code": {"input": 0.20, "output": 1.5},
}

def calculate_cost(model, input_tokens, output_tokens):
    costs = MODEL_COSTS.get(model)
    if not costs:
        model_lower = model.lower()
        if "codex-max" in model_lower:
            costs = {"input": 1.25, "output": 10}
        elif "gemini-3-pro" in model_lower:
            costs = {"input": 2, "output": 12}
        elif "gemini-3-flash" in model_lower:
            costs = {"input": 0.5, "output": 3}
        elif "claude-opus" in model_lower:
            costs = {"input": 5, "output": 25}
        elif "claude-sonnet" in model_lower:
            costs = {"input": 3, "output": 15}
        elif "glm-4" in model_lower:
            costs = {"input": 0.43, "output": 2.2}
    if not costs:
        return 0
    input_cost = (input_tokens / 1000000) * costs["input"]
    output_cost = (output_tokens / 1000000) * costs["output"]
    return input_cost + output_cost

def get_session_stats(session_path):
    stats = {"by_model": {}}
    for msg_file in session_path.glob("*.json"):
        try:
            with open(msg_file) as f:
                msg = json.load(f)
            if msg.get("role") != "assistant":
                continue
            tokens = msg.get("tokens", {})
            if not tokens:
                continue
            model = msg.get("modelID", "unknown")
            if model not in stats["by_model"]:
                stats["by_model"][model] = {"requests": 0, "input": 0, "output": 0}
            stats["by_model"][model]["requests"] += 1
            stats["by_model"][model]["input"] += tokens.get("input", 0)
            stats["by_model"][model]["output"] += tokens.get("output", 0)
        except (json.JSONDecodeError, KeyError):
            continue
    return stats

def main():
    msg_dir = Path.home() / ".local/share/opencode/storage/message"
    history_file = Path(__file__).parent / "session_history.json"

    if not msg_dir.exists():
        print(f"Error: No se encontró el directorio de logs en {msg_dir}")
        return

    all_sessions = {}
    print(f"Escaneando sesiones en {msg_dir}...")
    
    for session_path in msg_dir.iterdir():
        if not session_path.is_dir():
            continue
        
        stats = get_session_stats(session_path)
        if not stats["by_model"]:
            continue
        
        total_requests = sum(m["requests"] for m in stats["by_model"].values())
        total_input = sum(m["input"] for m in stats["by_model"].values())
        total_output = sum(m["output"] for m in stats["by_model"].values())
        total_cost = 0
        
        by_model_with_cost = {}
        for model, data in stats["by_model"].items():
            model_cost = calculate_cost(model, data["input"], data["output"])
            total_cost += model_cost
            by_model_with_cost[model] = {
                "requests": data["requests"],
                "input": data["input"],
                "output": data["output"],
                "cost": model_cost
            }
        
        # Obtener fecha de la sesión
        session_date = datetime.datetime.fromtimestamp(session_path.stat().st_mtime).isoformat()
        
        all_sessions[session_path.name] = {
            "date": session_date,
            "requests": total_requests,
            "input": total_input,
            "output": total_output,
            "cost": total_cost,
            "by_model": by_model_with_cost
        }
        print(f"✓ Procesada: {session_path.name} ({total_requests} req)")

    with open(history_file, 'w') as f:
        json.dump(all_sessions, f, indent=2)

    print(f"\n✅ Migración completada: {len(all_sessions)} sesiones guardadas en {history_file}")

if __name__ == "__main__":
    main()
