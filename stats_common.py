import json
import re
import sqlite3
import datetime
from pathlib import Path

# Rutas de Codex CLI
CODEX_SESSIONS_DIR = Path.home() / ".codex/sessions"

# Rutas de Hermes
HERMES_DB_PATH = Path.home() / ".hermes/state.db"
HERMES_SESSIONS_DIR = Path.home() / ".hermes/sessions"

# Rutas de OpenCode SQLite (v1.3.0+)
OPENCODE_DB_PATH = Path.home() / ".local/share/opencode/opencode.db"

# Rutas de Kilocode CLI
KILOCODE_STATE_FILE = Path.home() / ".kilocode/cli/global/global-state.json"
KILOCODE_TASKS_DIR = Path.home() / ".kilocode/cli/global/tasks"

# Directorio del script (para JSON de modelos)
SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_COSTS_FILE = SCRIPT_DIR / "model_costs.json"
MODEL_ALIASES_FILE = SCRIPT_DIR / "model_aliases.json"


# Costos por 1M tokens (USD) — valores por defecto, pisados por JSON si existe
MODEL_COSTS = {
    "glm-4.7": {"input": 0.39, "output": 1.75, "cache": 0.195},
    "glm-4.7-flash": {"input": 0.06, "output": 0.4, "cache": 0.01},
    "gpt-5.1-codex-max": {"input": 1.25, "output": 10},
    "codex-max": {"input": 1.25, "output": 10},
    "gpt-5.2-codex": {"input": 1.75, "output": 14},
    "gpt-5.2": {"input": 1.75, "output": 14},
    "gpt-5.3-codex": {"input": 1.75, "output": 14},
    "gpt-5.4": {"input": 1.75, "output": 14},
    "gpt-5-mini": {"input": 0.25, "output": 2},
    "step-3.5-flash": {"input": 0.10, "output": 0.30, "cache": 0.02},
    "antigravity-claude-opus-4-5-thinking": {"input": 5, "output": 25},
    "antigravity-claude-opus-4-5-thinking/high": {"input": 5, "output": 25},
    "antigravity-claude-opus-4-5-thinking/low": {"input": 5, "output": 25},
    "claude-opus-4.5": {"input": 5, "output": 25},
    "claude-opus-4.5-thinking": {"input": 5, "output": 25},
    "claude-opus-4.5-thinking/high": {"input": 5, "output": 25},
    "claude-opus-4.5-thinking/low": {"input": 5, "output": 25},
    "antigravity-claude-opus-4-6-thinking": {"input": 5, "output": 25},
    "claude-opus-4.6": {"input": 5, "output": 25},
    "antigravity-claude-sonnet-4-5": {"input": 3, "output": 15},
    "antigravity-claude-sonnet-4-5-thinking": {"input": 3, "output": 15},
    "antigravity-claude-sonnet-4-5-thinking/high": {"input": 3, "output": 15},
    "antigravity-claude-sonnet-4-5-thinking/low": {"input": 3, "output": 15},
    "claude-sonnet-4.5": {"input": 3, "output": 15},
    "claude-sonnet-4.5-thinking": {"input": 3, "output": 15},
    "claude-sonnet-4.5-thinking/high": {"input": 3, "output": 15},
    "claude-sonnet-4.5-thinking/low": {"input": 3, "output": 15},
    "claude-haiku-4.5": {"input": 1, "output": 5},
    "antigravity-gemini-3-flash": {"input": 0.5, "output": 3},
    "antigravity-gemini-3-flash/minimal": {"input": 0.5, "output": 3},
    "antigravity-gemini-3-flash/low": {"input": 0.5, "output": 3},
    "antigravity-gemini-3-flash/medium": {"input": 0.5, "output": 3},
    "antigravity-gemini-3-flash/high": {"input": 0.5, "output": 3},
    "gemini-3-flash": {"input": 0.5, "output": 3},
    "gemini-3-flash/minimal": {"input": 0.5, "output": 3},
    "gemini-3-flash/low": {"input": 0.5, "output": 3},
    "gemini-3-flash/medium": {"input": 0.5, "output": 3},
    "gemini-3-flash/high": {"input": 0.5, "output": 3},
    "tab_flash_lite_preview": {"input": 0.5, "output": 3},
    "antigravity-gemini-3-pro": {"input": 2, "output": 12},
    "antigravity-gemini-3-pro/low": {"input": 2, "output": 12},
    "antigravity-gemini-3-pro/high": {"input": 2, "output": 12},
    "gemini-3-pro": {"input": 2, "output": 12},
    "gemini-3-pro/low": {"input": 2, "output": 12},
    "gemini-3-pro/high": {"input": 2, "output": 12},
    "antigravity-gemini-3.1-pro": {"input": 2, "output": 12, "cache": 0.2},
    "antigravity-gemini-3.1-pro/low": {"input": 2, "output": 12, "cache": 0.2},
    "antigravity-gemini-3.1-pro/high": {"input": 2, "output": 12, "cache": 0.2},
    "gemini-3.1-pro": {"input": 2, "output": 12, "cache": 0.2},
    "gemini-3.1-pro/low": {"input": 2, "output": 12, "cache": 0.2},
    "gemini-3.1-pro/high": {"input": 2, "output": 12, "cache": 0.2},
    "gemini-3.1-flash-lite": {"input": 0.25, "output": 1.5, "cache": 0.025},
    "gemini-3.1-flash-image": {"input": 0.5, "output": 3.0},
    "x-ai/grok-4.1-fast": {"input": 0.20, "output": 0.50, "cache": 0.05},
    "kimi-k2.5": {"input": 0.50, "output": 2.60, "cache": 0.09},
    "minimax-m2.1": {"input": 0.27, "output": 0.95},
    "trinity-large-preview": {"input": 0.25, "output": 1.00},
    "glm-5.1": {"input": 1.40, "output": 4.40, "cache": 0.26},
    "glm-5": {"input": 0.80, "output": 2.56, "cache": 0.16},
    "grok-code-fast-1-optimized-free": {"input": 0.20, "output": 1.50, "cache": 0.02},
    "mimo-v2-pro": {"input": 1, "output": 3},
    "qwen3.6-plus": {"input": 0.50, "output": 3.00, "cache": 0.50},
    "minimax-m2.5": {"input": 0.30, "output": 1.20, "cache": 0.03},
    "minimax-m2.7": {"input": 0.30, "output": 1.20, "cache": 0.06},
    "gemma-4-31b": {"input": 0.15, "output": 0.40},
    "deepseek-v4-flash": {"input": 0.14, "output": 0.28, "cache": 0.028},
    "deepseek-v4-pro": {"input": 1.74, "output": 3.48, "cache": 0.145},
}

MODEL_ALIASES = {
    "step-3.5-flash": "step-3.5-flash",
    "step-3.5-flash-free": "step-3.5-flash",
    "k2p5": "kimi-k2.5",
    "kimi-k2.5-free": "kimi-k2.5",
    "minimax-m2.1-free": "minimax-m2.1",
    "minimax-m2.1-pro": "minimax-m2.1",
    "minimax-m2.5-free": "minimax-m2.5",
    "minimax-m2.5": "minimax-m2.5",
    "minimax-m2.7": "minimax-m2.7",
    "trinity-large-preview": "trinity-large-preview",
    "trinity-large-preview-free": "trinity-large-preview",
    "glm-5-free": "glm-5",
    "claude-opus-4.5": "claude-opus-4.5",
    "antigravity-claude-opus-4-5-thinking": "claude-opus-4.5",
    "antigravity-claude-opus-4-5-thinking-high": "claude-opus-4.5",
    "antigravity-claude-opus-4-5-thinking-low": "claude-opus-4.5",
    "claude-opus-4.5-thinking": "claude-opus-4.5",
    "claude-opus-4.5-thinking/high": "claude-opus-4.5",
    "claude-opus-4.5-thinking/low": "claude-opus-4.5",
    "claude-opus-4.6": "claude-opus-4.6",
    "antigravity-claude-opus-4-6-thinking": "claude-opus-4.6",
    "antigravity-claude-opus-4-6-thinking-high": "claude-opus-4.6",
    "antigravity-claude-opus-4-6-thinking-low": "claude-opus-4.6",
    "claude-sonnet-4.5": "claude-sonnet-4.5",
    "antigravity-claude-sonnet-4-5-thinking": "claude-sonnet-4.5",
    "antigravity-claude-sonnet-4-5-thinking-high": "claude-sonnet-4.5",
    "antigravity-claude-sonnet-4-5-thinking-low": "claude-sonnet-4.5",
    "claude-sonnet-4.5-thinking": "claude-sonnet-4.5",
    "claude-sonnet-4.5-thinking/high": "claude-sonnet-4.5",
    "claude-sonnet-4.5-thinking/low": "claude-sonnet-4.5",
    "claude-haiku-4.5": "claude-haiku-4.5",
    "gemini-3-flash": "gemini-3-flash",
    "antigravity-gemini-3-flash": "gemini-3-flash",
    "antigravity-gemini-3-flash/minimal": "gemini-3-flash",
    "antigravity-gemini-3-flash/low": "gemini-3-flash",
    "antigravity-gemini-3-flash/medium": "gemini-3-flash",
    "antigravity-gemini-3-flash/high": "gemini-3-flash",
    "antigravity-gemini-3-flash-lite": "gemini-3-flash",
    "antigravity-gemini-3-flash-preview": "gemini-3-flash",
    "gemini-3-flash-preview": "gemini-3-flash",
    "tab_flash_lite_preview": "gemini-3-flash",
    "gemini-3-pro": "gemini-3-pro",
    "antigravity-gemini-3-pro": "gemini-3-pro",
    "antigravity-gemini-3-pro/low": "gemini-3-pro",
    "antigravity-gemini-3-pro/high": "gemini-3-pro",
    "antigravity-gemini-3-pro-low": "gemini-3-pro",
    "antigravity-gemini-3-pro-high": "gemini-3-pro",
    "gemini-3.1-pro": "gemini-3.1-pro",
    "gemini-3.1": "gemini-3.1-pro",
    "antigravity-gemini-3.1-pro": "gemini-3.1-pro",
    "antigravity-gemini-3.1-pro/low": "gemini-3.1-pro",
    "antigravity-gemini-3.1-pro/high": "gemini-3.1-pro",
    "antigravity-gemini-3.1-pro-low": "gemini-3.1-pro",
    "antigravity-gemini-3.1-pro-high": "gemini-3.1-pro",
    "gpt-5.2": "gpt-5.2",
    "gpt-5.4": "gpt-5.4",
    "gpt-5.2-codex": "gpt-5.2-codex",
    "gpt-5.3-codex": "gpt-5.3-codex",
    "gpt-5.1-codex-max": "gpt-5.1-codex-max",
    "gpt-5-mini": "gpt-5-mini",
    "glm-4.7-free": "glm-4.7",
    "glm-4.7": "glm-4.7",
    "glm4.7": "glm-4.7",
    "glm-5": "glm-5",
    "glm-5-free": "glm-5",
    "glm5": "glm-5",
    "glm-5.1": "glm-5.1",
    "glm-5.1-free": "glm-5.1",
    "historical_adjustment": "historical_adjustment",
    "x-ai/grok-4.1-fast": "x-ai/grok-4.1-fast",
    "grok-4.1-fast": "x-ai/grok-4.1-fast",
    "grok-code-fast-1-optimized-free": "grok-code-fast-1-optimized-free",
    "grok-code-fast": "grok-code-fast-1-optimized-free",
    "grok-code": "grok-code-fast-1-optimized-free",
    "mimo-v2-pro": "mimo-v2-pro",
    "mimo-v2": "mimo-v2-pro",
    "xiaomi/mimo-v2-pro": "mimo-v2-pro",
    "hunter-alpha": "mimo-v2-pro",
    "pony-alpha": "mimo-v2-pro",
    "healer-alpha": "mimo-v2-pro",
    "qwen3.6-plus-free": "qwen3.6-plus",
    "qwen3.6-plus-preview-free": "qwen3.6-plus",
    "qwen3.6-plus-preview": "qwen3.6-plus",
    "qwen-modelo": "qwen3.6-plus",
    "gemma-4-31b": "gemma-4-31b",
    "gemma-4-31b-free": "gemma-4-31b",
    "deepseek-v4-flash": "deepseek-v4-flash",
    "deepseek-v4-flash-free": "deepseek-v4-flash",
    "deepseek/deepseek-v4-flash": "deepseek-v4-flash",
    "deepseek-v4-pro": "deepseek-v4-pro",
    "deepseek-v4-pro-free": "deepseek-v4-pro",
    "deepseek/deepseek-v4-pro": "deepseek-v4-pro",
}


def _load_model_overrides():
    """Pisa MODEL_COSTS y MODEL_ALIASES desde JSON si los archivos existen."""
    for var_name, file_path in [
        ("MODEL_COSTS", MODEL_COSTS_FILE),
        ("MODEL_ALIASES", MODEL_ALIASES_FILE),
    ]:
        try:
            if file_path.exists():
                with open(file_path) as fh:
                    data = json.load(fh)
                globals()[var_name].clear()
                globals()[var_name].update(data)
        except Exception:
            pass

    # Alias protegidos: siempre presentes, nunca en JSON
    MODEL_ALIASES["historical_adjustment"] = "historical_adjustment"


_load_model_overrides()


def normalize_model_name(model):
    """Normaliza modelo a su base + version, agrupando variantes."""
    if not model:
        return "unknown"

    model_lower = model.lower()

    # Remover prefijos de provider
    for prefix in [
        "antigravity-",
        "z-ai/",
        "deepseek/",
        "google/",
        "anthropic/",
        "openai/",
        "moonshot/",
        "openrouter/",
    ]:
        model_lower = model_lower.replace(prefix, "")

    # Remover sufijos/variantes
    suffixes = [
        "-thinking-high",
        "-thinking/low",
        "-thinking/medium",
        "-thinking/minimal",
        "-thinking-low",
        "-thinking-medium",
        "-thinking-minimal",
        "-thinking/high",
        "/high",
        "/low",
        "/medium",
        "/minimal",
        "-high",
        "-low",
        "-medium",
        "-minimal",
        "-free",
        "-preview",
        "-pro",
        "-lite",
        ":free",
        ":pro",
        ":lite",
        ":discounted",
    ]
    for suffix in suffixes:
        model_lower = model_lower.replace(suffix, "")

    # Verificar primero en MODEL_ALIASES (compatibilidad hacia atras)
    if model in MODEL_ALIASES:
        return MODEL_ALIASES[model]
    if model_lower in MODEL_ALIASES:
        return MODEL_ALIASES[model_lower]

    # Patrones especificos con version
    # Claude (versiones explicitas)
    if "claude-opus-4.6" in model_lower:
        return "claude-opus-4.6"
    elif "claude-opus-4.5" in model_lower:
        return "claude-opus-4.5"
    elif "claude-sonnet-4.5" in model_lower:
        return "claude-sonnet-4.5"
    elif "claude-haiku-4.5" in model_lower:
        return "claude-haiku-4.5"

    # Gemini (versiones explicitas)
    elif "gemini-3.1-pro" in model_lower:
        return "gemini-3.1-pro"
    elif "gemini-3.1-flash" in model_lower:
        return "gemini-3.1-flash"
    elif "gemini-3-pro" in model_lower:
        return "gemini-3-pro"
    elif "gemini-3-flash" in model_lower:
        return "gemini-3-flash"

    # GLM (versiones explicitas)
    elif model_lower.startswith("glm-5."):
        return "glm-5.1"
    elif model_lower == "glm-5":
        return "glm-5"
    elif "glm-4.7" in model_lower or "glm-4" in model_lower:
        return "glm-4.7-free"

    # Otros (versiones explicitas)
    elif "gemma-4-31b" in model_lower:
        return "gemma-4-31b"
    elif "kimi-k2.5" in model_lower:
        return "kimi-k2.5"
    elif "minimax-m2.7" in model_lower:
        return "minimax-m2.7"
    elif "minimax-m2.5" in model_lower:
        return "minimax-m2.5"
    elif "minimax-m2.1" in model_lower:
        return "minimax-m2.1"
    elif "trinity-large-preview" in model_lower:
        return "trinity-large-preview"
    elif "gpt-5.3-codex" in model_lower:
        return "gpt-5.3-codex"
    elif "gpt-5.2-codex" in model_lower:
        return "gpt-5.2-codex"
    elif "gpt-5.2" in model_lower:
        return "gpt-5.2"
    elif "gpt-5.4" in model_lower:
        return "gpt-5.4"
    elif "gpt-5.1-codex-max" in model_lower or "codex-max" in model_lower:
        return "gpt-5.1-codex-max"
    elif "gpt-5-mini" in model_lower:
        return "gpt-5-mini"
    elif "grok-code" in model_lower or "grok-4.1-fast" in model_lower:
        return "grok-code"
    elif "deepseek-v4-pro" in model_lower:
        return "deepseek-v4-pro"
    elif "deepseek-v4-flash" in model_lower or "deepseek-v4" in model_lower:
        return "deepseek-v4-flash"
    elif "step-3.5-flash" in model_lower:
        return "step-3.5-flash"
    elif "mimo-v2" in model_lower:
        return "mimo-v2-pro"
    elif "qwen3.6-plus" in model_lower:
        return "qwen3.6-plus"

    return model_lower


def extract_model_from_task(task_id):
    """Extrae modelo del archivo api_conversation_history.json de kilocode."""
    if not task_id:
        return "unknown"

    task_file = KILOCODE_TASKS_DIR / task_id / "api_conversation_history.json"
    if not task_file.exists():
        return "unknown"

    try:
        content = task_file.read_text()
        match = re.search(r"<model>([^<]+)</model>", content)
        if match:
            return match.group(1)
    except Exception:
        pass

    return "unknown"


def get_kilocode_history():
    """Lee taskHistory de kilocode CLI y extrae modelo de cada tarea.

    Retorna dict: {task_id: {model, input, output, cache, cost, date, task}}
    """
    if not KILOCODE_STATE_FILE.exists():
        return None

    try:
        with open(KILOCODE_STATE_FILE) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    task_history = data.get("taskHistory", [])
    if not task_history:
        return None

    result = {}
    for task in task_history:
        task_id = task.get("id")
        if not task_id:
            continue

        # Extraer modelo del archivo de tarea
        raw_model = extract_model_from_task(task_id)
        normalized_model = normalize_model_name(raw_model)

        # Costo: usar totalCost si > 0, sino calcular
        cost = task.get("totalCost", 0)
        if cost == 0:
            tokens_in = task.get("tokensIn", 0)
            tokens_out = task.get("tokensOut", 0)
            cache_tokens = (task.get("cacheReads", 0) or 0) + (
                task.get("cacheWrites", 0) or 0
            )
            cost = calculate_cost(normalized_model, tokens_in, tokens_out, cache_tokens)

        ts = task.get("ts", 0)
        try:
            import datetime

            date_str = datetime.datetime.fromtimestamp(ts / 1000).isoformat()
        except Exception:
            date_str = ""

        result[f"kilocode_{task_id}"] = {
            "model": normalized_model,
            "input": task.get("tokensIn", 0) or 0,
            "output": task.get("tokensOut", 0) or 0,
            "cache": (task.get("cacheReads", 0) or 0)
            + (task.get("cacheWrites", 0) or 0),
            "cost": cost,
            "date": date_str,
            "task": task.get("task", "")[:50] if task.get("task") else "",
        }

    return result if result else None


def get_codex_sessions():
    """Retorna lista de archivos JSONL de sesiones de Codex CLI.

    Returns list of Path objects sorted by modification time (newest first).
    """
    if not CODEX_SESSIONS_DIR.exists():
        return []

    import glob

    files = glob.glob(str(CODEX_SESSIONS_DIR / "**/*.jsonl"), recursive=True)
    sessions = [Path(f) for f in files]
    sessions.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return sessions


def has_real_usage_codex(session_file):
    """Check if a Codex session JSONL file has real token usage."""
    try:
        with open(session_file) as f:
            for line in f:
                data = json.loads(line)
                if data.get("type") == "event_msg":
                    p = data.get("payload", {})
                    if p.get("type") == "token_count":
                        info = p.get("info", {})
                        if info and "total_token_usage" in info:
                            usage = info["total_token_usage"]
                            total = usage.get("input_tokens", 0) + usage.get(
                                "output_tokens", 0
                            )
                            if total > 0:
                                return True
    except (json.JSONDecodeError, OSError):
        pass
    return False


def get_codex_session_stats(session_file):
    """Extrae estadisticas de tokens de una sesion Codex (archivo JSONL).

    Retorna dict con: model, input, output, cache, reasoning, requests, session_id, date
    """
    result = {
        "model": "gpt-5.4",
        "input": 0,
        "output": 0,
        "cache": 0,
        "reasoning": 0,
        "requests": 0,
        "session_id": "",
        "date": "",
    }

    last_token_count = None
    request_count = 0

    try:
        with open(session_file) as f:
            for line in f:
                data = json.loads(line)
                typ = data.get("type", "")

                if typ == "session_meta":
                    result["session_id"] = data.get("payload", {}).get("id", "")
                    ts_str = data.get("payload", {}).get("timestamp", "")
                    if ts_str:
                        result["date"] = ts_str

                elif typ == "turn_context":
                    model = data.get("payload", {}).get("model", "")
                    if model:
                        result["model"] = model

                elif typ == "event_msg":
                    p = data.get("payload", {})
                    if p.get("type") == "token_count":
                        info = p.get("info", {})
                        if info and "total_token_usage" in info:
                            last_token_count = info["total_token_usage"]
                    elif p.get("type") == "user_message":
                        request_count += 1
    except (json.JSONDecodeError, OSError):
        pass

    if last_token_count:
        result["input"] = last_token_count.get("input_tokens", 0)
        result["output"] = last_token_count.get("output_tokens", 0)
        result["cache"] = last_token_count.get("cached_input_tokens", 0)
        result["reasoning"] = last_token_count.get("reasoning_output_tokens", 0)

    result["requests"] = request_count if request_count > 0 else 1

    return result


def get_opencode_sqlite_sessions():
    """Lee sesiones de OpenCode SQLite (v1.3.0+).

    Retorna dict: {session_id: {model, input, output, cache, requests, date}}
    Solo incluye sesiones con uso real de tokens.
    """
    if not OPENCODE_DB_PATH.exists():
        return {}

    try:
        import sqlite3

        conn = sqlite3.connect(str(OPENCODE_DB_PATH))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, time_updated FROM session ORDER BY time_updated DESC"
        )
        sessions_raw = cursor.fetchall()

        result = {}
        for sid, title, time_updated in sessions_raw:
            cursor.execute(
                "SELECT data FROM message WHERE session_id = ? ORDER BY time_created",
                (sid,),
            )
            by_model = {}
            requests = 0

            for (data_str,) in cursor.fetchall():
                try:
                    msg = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                if msg.get("role") != "assistant":
                    continue

                tokens = msg.get("tokens", {})
                if not tokens:
                    continue

                model = msg.get("modelID", "unknown")
                if model not in by_model:
                    by_model[model] = {
                        "requests": 0,
                        "input": 0,
                        "output": 0,
                        "cache": 0,
                    }

                by_model[model]["requests"] += 1
                requests += 1
                cache_read = (tokens.get("cache") or {}).get("read", 0)
                by_model[model]["input"] += abs(tokens.get("input", 0) or 0)
                by_model[model]["cache"] += abs(cache_read or 0)
                by_model[model]["output"] += abs(tokens.get("output", 0) or 0)

            if requests > 0:
                # Consolidar en un solo modelo (el más usado)
                primary_model = max(
                    by_model.keys(), key=lambda m: by_model[m]["requests"]
                )
                total_input = sum(m["input"] for m in by_model.values())
                total_output = sum(m["output"] for m in by_model.values())
                total_cache = sum(m["cache"] for m in by_model.values())

                try:
                    date_str = datetime.datetime.fromtimestamp(
                        time_updated / 1000
                    ).isoformat()
                except Exception:
                    date_str = ""

                result[sid] = {
                    "model": primary_model,
                    "input": total_input,
                    "output": total_output,
                    "cache": total_cache,
                    "requests": requests,
                    "date": date_str,
                    "by_model": by_model,
                    "title": title or "",
                }

        conn.close()
        return result
    except Exception:
        return {}


# --- Hermes ---
def get_hermes_sessions():
    """Retorna lista de sesiones de Hermes desde SQLite.

    Returns list of dicts: {id, model, input, output, cache, reasoning,
    requests, date, title, by_model}
    Solo incluye sesiones CLI con uso real de tokens.
    """
    if not HERMES_DB_PATH.exists():
        return []
    try:
        conn = sqlite3.connect(str(HERMES_DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, model, input_tokens, output_tokens,
                   cache_read_tokens, cache_write_tokens, reasoning_tokens,
                   estimated_cost_usd, actual_cost_usd, ended_at, started_at, title
            FROM sessions
            WHERE source = 'cli' AND input_tokens > 0
            ORDER BY started_at DESC
        """)
        sessions = []
        for row in cursor.fetchall():
            sid = row[0]
            model = row[1] or "unknown"
            input_tokens = row[2] or 0
            output_tokens = row[3] or 0
            cache_read = row[4] or 0
            cache_write = row[5] or 0
            reasoning = row[6] or 0
            started_at = row[10]
            title = row[11] or ""

            # Contar requests
            cursor2 = conn.cursor()
            cursor2.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id = ? AND role = 'assistant'",
                (sid,)
            )
            requests = cursor2.fetchone()[0] or 1
            cursor2.close()

            try:
                date_str = datetime.datetime.fromtimestamp(started_at).isoformat()
            except Exception:
                date_str = ""

            normalized = normalize_model_name(model)
            by_model = {
                normalized: {
                    "requests": requests,
                    "input": input_tokens,
                    "output": output_tokens,
                    "cache": cache_read,
                    "reasoning": reasoning,
                }
            }

            sessions.append({
                "id": sid,
                "model": model,
                "input": input_tokens,
                "output": output_tokens,
                "cache": cache_read + cache_write,
                "reasoning": reasoning,
                "requests": requests,
                "date": date_str,
                "title": title,
                "started_at": started_at,
                "by_model": by_model,
            })
        conn.close()
        return sessions
    except Exception:
        return []


def has_real_usage_hermes(session_id):
    """Check if a Hermes session has real token usage."""
    if not HERMES_DB_PATH.exists():
        return False
    try:
        conn = sqlite3.connect(str(HERMES_DB_PATH))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT input_tokens FROM sessions WHERE id = ? AND source = 'cli'",
            (session_id,)
        )
        row = cursor.fetchone()
        conn.close()
        return row is not None and (row[0] or 0) > 0
    except Exception:
        return False


def get_hermes_session_stats(session_id):
    """Extrae estadísticas de una sesión Hermes.

    Returns dict compatible con el formato de session-stats:
    {model, input, output, cache, reasoning, requests, session_id, date, by_model}
    """
    if not HERMES_DB_PATH.exists():
        return {}
    try:
        conn = sqlite3.connect(str(HERMES_DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT model, input_tokens, output_tokens,
                   cache_read_tokens, cache_write_tokens, reasoning_tokens,
                   estimated_cost_usd, actual_cost_usd, ended_at, started_at, title
            FROM sessions WHERE id = ? AND source = 'cli'
        """, (session_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {}

        model = row[0] or "unknown"
        input_tokens = row[1] or 0
        output_tokens = row[2] or 0
        cache_read = row[3] or 0
        cache_write = row[4] or 0
        reasoning = row[5] or 0
        estimated_cost = row[6] or 0
        actual_cost = row[7]
        ended_at = row[8]
        started_at = row[9]
        title = row[10] or ""

        # Calcular requests desde message_count
        cursor.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ? AND role = 'assistant'",
            (session_id,)
        )
        requests = cursor.fetchone()[0] or 1
        conn.close()

        try:
            date_str = datetime.datetime.fromtimestamp(started_at).isoformat()
        except Exception:
            date_str = ""

        normalized = normalize_model_name(model)
        by_model = {
            normalized: {
                "requests": requests,
                "input": input_tokens,
                "output": output_tokens,
                "cache": cache_read,
                "reasoning": reasoning,
            }
        }

        return {
            "model": model,
            "input": input_tokens,
            "output": output_tokens,
            "cache": cache_read + cache_write,
            "reasoning": reasoning,
            "requests": requests,
            "session_id": session_id,
            "date": date_str,
            "ended_at": ended_at,
            "title": title,
            "estimated_cost": estimated_cost,
            "actual_cost": actual_cost,
            "by_model": by_model,
        }
    except Exception:
        return {}


def calculate_cost(model, input_tokens, output_tokens, cache_tokens=0):
    """Calcula costo basado en tokens."""
    # Sonar: costo fijo por request
    if model == "sonar":
        return 0.0055

    normalized = normalize_model_name(model)
    costs = MODEL_COSTS.get(normalized)
    if not costs:
        model_lower = model.lower()
        if "codex-max" in model_lower:
            costs = {"input": 1.25, "output": 10}
        elif "gemini-3.1-pro" in model_lower:
            costs = {"input": 2, "output": 12, "cache": 0.2}
        elif "gemini-3-pro" in model_lower:
            costs = {"input": 2, "output": 12}
        elif "gemini-3-flash" in model_lower:
            costs = {"input": 0.5, "output": 3}
        elif "claude-opus-4.6" in model_lower:
            costs = {"input": 5, "output": 25}
        elif "claude-opus" in model_lower:
            costs = {"input": 5, "output": 25}
        elif "claude-sonnet" in model_lower:
            costs = {"input": 3, "output": 15}
        elif "claude-haiku" in model_lower:
            costs = {"input": 1, "output": 5}
        elif "glm-5.1" in model_lower:
            costs = {"input": 1.40, "output": 4.40, "cache": 0.26}
        elif "glm-5" in model_lower:
            costs = {"input": 0.80, "output": 2.56, "cache": 0.16}
        elif "glm-4" in model_lower:
            costs = {"input": 0.43, "output": 2.2}
        elif "kimi" in model_lower:
            costs = {"input": 0.50, "output": 2.60, "cache": 0.09}
        elif "minimax" in model_lower:
            if "m2.5" in model_lower:
                costs = {"input": 0.30, "output": 1.20, "cache": 0.03}
            else:
                costs = {"input": 0.27, "output": 0.95}
        elif "trinity" in model_lower:
            costs = {"input": 0.25, "output": 1.00}

    if not costs:
        return 0

    input_cost = (input_tokens / 1000000) * costs["input"]
    output_cost = (output_tokens / 1000000) * costs["output"]
    cache_cost = (cache_tokens / 1000000) * costs.get("cache", 0)
    return input_cost + output_cost + cache_cost


def recalculate_historical_cost(history_file):
    """Recalcula el costo total histórico desde los tokens de cada sesión.
    Incluye sesiones de Kilo, OpenCode (JSON + SQLite), y Codex (JSONL).

    Retorna dict con: total_cost, total_sessions, total_requests,
    total_input, total_output, models_totals
    """

    import json
    from pathlib import Path

    history_path = Path(history_file)
    data = {}
    if history_path.exists():
        try:
            with open(history_path, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            pass

    session_keys = [k for k in data.keys() if k != "historical_total"]
    base_sessions = data.get("historical_total", {}).get("sessions", 0)

    total_requests = sum(data[k].get("requests", 0) for k in session_keys)
    total_input = sum(data[k].get("input", 0) for k in session_keys)
    total_output = sum(data[k].get("output", 0) for k in session_keys)
    total_sessions = base_sessions + len(session_keys)

    if "historical_total" in data:
        historical = data["historical_total"]
        total_requests += historical.get("requests", 0)
        total_input += historical.get("input", 0)
        total_output += historical.get("output", 0)

    # Agregar tokens por modelo desde sesiones guardadas
    models_totals = {}
    for key in session_keys:
        session = data[key]
        by_model = session.get("by_model", {})
        for model, model_data in by_model.items():
            normalized = normalize_model_name(model)
            if normalized not in models_totals:
                models_totals[normalized] = {
                    "requests": 0,
                    "input": 0,
                    "output": 0,
                    "cache": 0,
                }
            models_totals[normalized]["requests"] += model_data.get("requests", 0)
            models_totals[normalized]["input"] += model_data.get("input", 0)
            models_totals[normalized]["output"] += model_data.get("output", 0)
            models_totals[normalized]["cache"] += model_data.get("cache", 0)

    # Agregar sesiones de Codex que NO estan ya en el historial
    codex_sessions = get_codex_sessions()
    existing_codex_ids = {
        k.replace("codex_", "") for k in session_keys if k.startswith("codex_")
    }
    for sess_file in codex_sessions:
        if not has_real_usage_codex(sess_file):
            continue
        stats = get_codex_session_stats(sess_file)
        sid = stats.get("session_id", "")
        if sid and sid not in existing_codex_ids:
            normalized = normalize_model_name(stats["model"])
            if normalized not in models_totals:
                models_totals[normalized] = {
                    "requests": 0,
                    "input": 0,
                    "output": 0,
                    "cache": 0,
                }
            models_totals[normalized]["requests"] += stats["requests"]
            models_totals[normalized]["input"] += stats["input"]
            models_totals[normalized]["output"] += stats["output"]
            models_totals[normalized]["cache"] += stats["cache"]
            total_requests += stats["requests"]
            total_input += stats["input"]
            total_output += stats["output"]
            total_sessions += 1

    # Agregar sesiones de OpenCode SQLite (v1.3.0+) que NO estan en el historial
    opencode_sqlite_sessions = get_opencode_sqlite_sessions()
    for sid, stats in opencode_sqlite_sessions.items():
        if sid in session_keys:
            continue  # ya está en el historial
        by_model = stats.get("by_model", {})
        for model, model_data in by_model.items():
            normalized = normalize_model_name(model)
            if normalized not in models_totals:
                models_totals[normalized] = {
                    "requests": 0,
                    "input": 0,
                    "output": 0,
                    "cache": 0,
                }
            models_totals[normalized]["requests"] += model_data.get("requests", 0)
            models_totals[normalized]["input"] += model_data.get("input", 0)
            models_totals[normalized]["output"] += model_data.get("output", 0)
            models_totals[normalized]["cache"] += model_data.get("cache", 0)
        total_requests += stats["requests"]
        total_input += stats["input"]
        total_output += stats["output"]
        total_sessions += 1

    # Agregar sesiones de Hermes que NO estan ya en el historial
    hermes_sessions = get_hermes_sessions()
    for sess in hermes_sessions:
        sid = sess["id"]
        if sid in session_keys:
            continue  # ya está en el historial
        by_model = sess.get("by_model", {})
        for model, model_data in by_model.items():
            normalized = normalize_model_name(model)
            if normalized not in models_totals:
                models_totals[normalized] = {
                    "requests": 0,
                    "input": 0,
                    "output": 0,
                    "cache": 0,
                }
            models_totals[normalized]["requests"] += model_data.get("requests", 0)
            models_totals[normalized]["input"] += model_data.get("input", 0)
            models_totals[normalized]["output"] += model_data.get("output", 0)
            models_totals[normalized]["cache"] += model_data.get("cache", 0)
        total_requests += sess.get("requests", 0)
        total_input += sess.get("input", 0)
        total_output += sess.get("output", 0)
        total_sessions += 1

    # Ajuste para sesiones históricas antiguas (pre-guardado)
    historical_cost_adjustment = 0
    if "historical_total" in data:
        historical_models = data["historical_total"].get("by_model", {})
        historical_models_cost = 0
        for model, model_data in historical_models.items():
            normalized = normalize_model_name(model)
            if normalized not in models_totals:
                models_totals[normalized] = {
                    "requests": 0,
                    "input": 0,
                    "output": 0,
                    "cache": 0,
                }
            models_totals[normalized]["requests"] += model_data.get("requests", 0)
            models_totals[normalized]["input"] += model_data.get("input", 0)
            models_totals[normalized]["output"] += model_data.get("output", 0)
            models_totals[normalized]["cache"] += model_data.get("cache", 0)
            historical_models_cost += calculate_cost(
                normalized,
                model_data.get("input", 0),
                model_data.get("output", 0),
                model_data.get("cache", 0),
            )
        historical_total_cost = data["historical_total"].get("cost", 0)
        historical_cost_adjustment = historical_total_cost - historical_models_cost

    # Calcular costo total desde tokens
    total_cost = 0
    for model, mdata in models_totals.items():
        mdata["cost"] = calculate_cost(
            model, mdata["input"], mdata["output"], mdata.get("cache", 0)
        )
        total_cost += mdata["cost"]
    total_cost += historical_cost_adjustment

    return {
        "total_cost": total_cost,
        "total_sessions": total_sessions,
        "total_requests": total_requests,
        "total_input": total_input,
        "total_output": total_output,
        "models_totals": models_totals,
    }
