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

# Rutas de Cursor CLI (hook afterAgentResponse → usage-events.jsonl)
CURSOR_USAGE_JSONL = Path.home() / ".cursor" / "usage-events.jsonl"
CURSOR_CHATS_DIR = Path.home() / ".cursor" / "chats"
CURSOR_AGENT_LOGS_DIR = Path("/tmp") / f"cursor-agent-logs-{__import__('os').getuid()}"

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


# Semántica de cache por fuente (derivada, no persistida)
SOURCE_CACHE_SEMANTICS = {
    "codex":    {"input_includes_cache_read": True,  "cache_write_billable": True},
    "opencode": {"input_includes_cache_read": False, "cache_write_billable": False},
    "hermes":   {"input_includes_cache_read": False, "cache_write_billable": True},
    "kilocode": {"input_includes_cache_read": False, "cache_write_billable": False},
    "cursor":   {"input_includes_cache_read": False, "cache_write_billable": False},
    "unknown":  {"input_includes_cache_read": False, "cache_write_billable": False},
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
        "deepseek-ai/",
        "google/",
        "anthropic/",
        "openai/",
        "moonshot/",
        "openrouter/",
        "arcee-ai/",
        "minimax/",
        "nvidia/",
        "qwen/",
        "stepfun/",
        "xiaomi/",
        "zai-org/",
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
        ":free",
        ":pro",
        ":lite",
        ":discounted",
    ]
    for suffix in suffixes:
        model_lower = model_lower.replace(suffix, "")

    if model in MODEL_ALIASES:
        return MODEL_ALIASES[model]
    if model_lower in MODEL_ALIASES:
        return MODEL_ALIASES[model_lower]

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
        cached = last_token_count.get("cached_input_tokens", 0)
        result["cache"] = cached
        result["cache_read"] = cached
        result["cache_write"] = 0
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
                        "cache_read": 0,
                        "cache_write": 0,
                    }

                by_model[model]["requests"] += 1
                requests += 1
                cache_obj = tokens.get("cache") or {}
                cache_read = cache_obj.get("read", 0)
                cache_write = cache_obj.get("write", 0)
                by_model[model]["input"] += abs(tokens.get("input", 0) or 0)
                by_model[model]["cache"] += abs(cache_read or 0) + abs(cache_write or 0)
                by_model[model]["cache_read"] += abs(cache_read or 0)
                by_model[model]["cache_write"] += abs(cache_write or 0)
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
            WHERE source IN ('cli', 'telegram', 'subagent') AND input_tokens > 0
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
            ended_at = row[9]
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
                    "cache": cache_read + cache_write,
                    "cache_read": cache_read,
                    "cache_write": cache_write,
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
                "ended_at": ended_at,
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
            "SELECT input_tokens FROM sessions WHERE id = ? AND source IN ('cli', 'telegram')",
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
            FROM sessions WHERE id = ? AND source IN ('cli', 'telegram')
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
                "cache": cache_read + cache_write,
                "cache_read": cache_read,
                "cache_write": cache_write,
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


# --- Cursor CLI ---
def _load_cursor_events_from_jsonl():
    """Lee eventos del hook JSONL, deduplicados por generation_id."""
    if not CURSOR_USAGE_JSONL.exists():
        return []
    seen = set()
    events = []
    try:
        with open(CURSOR_USAGE_JSONL) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                gen_id = ev.get("generation_id")
                if not gen_id or gen_id in seen:
                    continue
                seen.add(gen_id)
                events.append(ev)
    except OSError:
        pass
    return events


def _load_cursor_events_from_agent_logs():
    """Backfill desde logs de debug del cursor-agent (cli.request.*)."""
    if not CURSOR_AGENT_LOGS_DIR.exists():
        return []
    pending = {}
    events = []
    for log_file in sorted(CURSOR_AGENT_LOGS_DIR.glob("session-*.log")):
        try:
            lines = log_file.read_text(errors="ignore").splitlines()
        except OSError:
            continue
        for line in lines:
            marker = "] analytics.track "
            if marker not in line:
                continue
            try:
                obj = json.loads(line.split(marker, 1)[1])
            except (json.JSONDecodeError, IndexError):
                continue
            ev_name = obj.get("eventName")
            props = obj.get("props") or {}
            inv_id = props.get("invocationID")
            if not inv_id:
                continue
            if ev_name == "cli.request.create":
                pending[inv_id] = {
                    "conversation_id": props.get("conversationId"),
                    "model": props.get("model") or "unknown",
                    "timestamp": line[1:25] + "Z",
                }
            elif ev_name == "cli.request.completed":
                base = pending.pop(inv_id, {})
                total = props.get("estimated_tokens") or 0
                if total <= 0 or props.get("end_reason") != "success":
                    continue
                conv_id = base.get("conversation_id") or props.get("conversationId")
                if not conv_id:
                    continue
                # estimated_tokens = total real reportado por Cursor CLI
                input_tokens = int(total * 0.85)
                output_tokens = total - input_tokens
                events.append({
                    "conversation_id": conv_id,
                    "generation_id": inv_id,
                    "model": base.get("model") or "unknown",
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cache_read_tokens": 0,
                    "cache_write_tokens": 0,
                    "timestamp": line[1:25] + "Z",
                    "source": "agent_log",
                })
    return events


def _load_cursor_events():
    """Combina hook JSONL + backfill de agent logs (hook gana en duplicados)."""
    by_gen = {}
    for ev in _load_cursor_events_from_agent_logs():
        gen_id = ev.get("generation_id")
        if gen_id:
            by_gen[gen_id] = ev
    for ev in _load_cursor_events_from_jsonl():
        gen_id = ev.get("generation_id")
        if gen_id:
            by_gen[gen_id] = ev
    return list(by_gen.values())


def _get_cursor_meta(conversation_id):
    """Busca meta.json de una conversación Cursor CLI."""
    if not CURSOR_CHATS_DIR.exists():
        return {}
    for user_dir in CURSOR_CHATS_DIR.iterdir():
        if not user_dir.is_dir():
            continue
        meta_path = user_dir / conversation_id / "meta.json"
        if meta_path.exists():
            try:
                with open(meta_path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
    return {}


def _aggregate_cursor_session(conversation_id, events):
    """Agrega eventos de una conversación en stats por modelo."""
    conv_events = [e for e in events if e.get("conversation_id") == conversation_id]
    if not conv_events:
        return None

    by_model = {}
    for ev in conv_events:
        model = normalize_model_name(ev.get("model") or "unknown")
        if model not in by_model:
            by_model[model] = {
                "requests": 0, "input": 0, "output": 0,
                "cache": 0, "cache_read": 0, "cache_write": 0,
                "reasoning": 0,
            }
        ev_cache_read = ev.get("cache_read_tokens") or 0
        ev_cache_write = ev.get("cache_write_tokens") or 0
        by_model[model]["requests"] += 1
        by_model[model]["input"] += ev.get("input_tokens") or 0
        by_model[model]["output"] += ev.get("output_tokens") or 0
        by_model[model]["cache"] += ev_cache_read + ev_cache_write
        by_model[model]["cache_read"] += ev_cache_read
        by_model[model]["cache_write"] += ev_cache_write

    meta = _get_cursor_meta(conversation_id)
    title = meta.get("title") or ""

    date_str = ""
    ts_epoch = None
    for ev in conv_events:
        ts = ev.get("timestamp")
        if ts:
            date_str = ts
            ts_epoch = _parse_timestamp(ts)

    if ts_epoch is None and meta.get("updatedAtMs"):
        ts_epoch = int(meta["updatedAtMs"] / 1000)
        try:
            date_str = datetime.datetime.fromtimestamp(ts_epoch).isoformat()
        except Exception:
            date_str = ""

    return {
        "id": conversation_id,
        "title": title,
        "date": date_str,
        "updated_at": ts_epoch or 0,
        "requests": sum(m["requests"] for m in by_model.values()),
        "input": sum(m["input"] for m in by_model.values()),
        "output": sum(m["output"] for m in by_model.values()),
        "cache": sum(m["cache"] for m in by_model.values()),
        "reasoning": 0,
        "by_model": by_model,
    }


def get_cursor_sessions():
    """Lista sesiones Cursor CLI agregadas desde usage-events.jsonl."""
    events = _load_cursor_events()
    if not events:
        return []
    conv_ids = list(dict.fromkeys(
        e["conversation_id"] for e in events if e.get("conversation_id")
    ))
    sessions = []
    for cid in conv_ids:
        agg = _aggregate_cursor_session(cid, events)
        if agg and (agg["input"] > 0 or agg["output"] > 0):
            sessions.append(agg)
    sessions.sort(key=lambda s: s.get("updated_at") or 0, reverse=True)
    return sessions


def has_real_usage_cursor(session_id):
    """Verifica si una sesión Cursor tiene uso real de tokens."""
    sid = session_id.removeprefix("cursor_")
    for sess in get_cursor_sessions():
        if sess["id"] == sid:
            return sess["input"] > 0 or sess["output"] > 0
    return False


def get_cursor_session_stats(session_id):
    """Extrae estadísticas de una sesión Cursor CLI."""
    sid = session_id.removeprefix("cursor_")
    events = _load_cursor_events()
    agg = _aggregate_cursor_session(sid, events)
    if not agg:
        return {}
    return {
        "session_id": sid,
        "session_title": agg.get("title", ""),
        "model": next(iter(agg["by_model"]), "unknown"),
        "input": agg["input"],
        "output": agg["output"],
        "cache": agg["cache"],
        "reasoning": 0,
        "requests": agg["requests"],
        "date": agg["date"],
        "by_model": agg["by_model"],
    }


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

    if cache_tokens >= input_tokens:
        input_cost = (input_tokens / 1000000) * costs["input"]
    else:
        uncached = input_tokens - cache_tokens
        input_cost = (uncached / 1000000) * costs["input"]
    output_cost = (output_tokens / 1000000) * costs["output"]
    cache_cost = (cache_tokens / 1000000) * costs.get("cache", 0)
    return input_cost + output_cost + cache_cost


def effective_billable_tokens(source, input_tokens, output_tokens,
                              cache_read_tokens=0, cache_write_tokens=0):
    """Tokens efectivamente facturables según semántica de la fuente."""
    sem = SOURCE_CACHE_SEMANTICS.get(source, SOURCE_CACHE_SEMANTICS["unknown"])
    total = (input_tokens or 0) + (output_tokens or 0)
    if not sem["input_includes_cache_read"]:
        total += cache_read_tokens or 0
    if sem["cache_write_billable"]:
        total += cache_write_tokens or 0
    return total


def effective_cache_ratio_input(source, input_tokens, cache_read_tokens=0):
    """Input total considerado para el cálculo de cache ratio."""
    sem = SOURCE_CACHE_SEMANTICS.get(source, SOURCE_CACHE_SEMANTICS["unknown"])
    if sem["input_includes_cache_read"]:
        return input_tokens or 0
    return (input_tokens or 0) + (cache_read_tokens or 0)


def recalculate_historical_cost():
    """Recalcula el costo total histórico desde SQLite.
    Lee sesiones de la DB principal + fuentes externas (Codex, OpenCode, Hermes)
    que aún no estén persistidas.

    El recalculo calcula el costo desde tokens usando model_costs.json,
    preservando la verificación de que los stored_cost coinciden con lo esperado.

    Retorna dict con: total_cost, total_sessions, total_requests,
    total_input, total_output, models_totals
    """
    if not DB_PATH.exists():
        return {
            "total_cost": 0,
            "total_sessions": 0,
            "total_requests": 0,
            "total_input": 0,
            "total_output": 0,
            "total_tokens": 0,
            "cache_ratio": 0,
            "models_totals": {},
        }

    conn = sqlite3.connect(str(DB_PATH))

    # 1. Leer sesiones de SQLite (excluyendo las que manejan lógica especial)
    session_keys = []
    base_sessions = 0
    historical_total_cost = 0.0
    historical_models_cost = 0.0
    models_totals = {}

    srows = conn.execute(
        "SELECT id, requests, input_tokens, output_tokens, cost, reasoning_tokens "
        "FROM sessions ORDER BY timestamp"
    ).fetchall()

    for sid, reqs, inp, out, cost, reasoning in srows:
        if sid == "historical_total":
            base_sessions = reasoning  # sessions stored in reasoning_tokens
            historical_total_cost = cost
            # Leer by_model de historical_total: agregar a models_totals + calcular adjustment
            mrows = conn.execute(
                "SELECT model, requests, input_tokens, output_tokens, cache_tokens FROM model_usage "
                "WHERE session_id = ?", (sid,)
            ).fetchall()
            for model, m_req, m_in, m_out, m_cache in mrows:
                normalized = normalize_model_name(model)
                if normalized not in models_totals:
                    models_totals[normalized] = {
                        "requests": 0, "input": 0, "output": 0,
                        "cache": 0, "cache_read": 0, "cache_write": 0,
                        "stored_cost": 0.0,
                    }
                models_totals[normalized]["requests"] += m_req
                models_totals[normalized]["input"] += m_in
                models_totals[normalized]["output"] += m_out
                models_totals[normalized]["cache"] += m_cache
                models_totals[normalized]["cache_read"] += m_cache
                historical_models_cost += calculate_cost(normalized, m_in, m_out, m_cache)
            continue
        if sid == "legacy_price_adjustment":
            # Ajuste de precio legacy: no cuenta como sesión
            continue
        session_keys.append(sid)

    # 2. Agregar tokens por modelo desde sesiones guardadas
    total_requests = 0
    total_input = 0
    total_output = 0
    total_tokens = 0
    cache_ratio_input = 0
    total_cache_read = 0

    if session_keys:
        placeholders = ",".join("?" for _ in session_keys)
        mrows = conn.execute(
            f"SELECT mu.model, mu.requests, mu.input_tokens, mu.output_tokens, "
            f"mu.cache_tokens, mu.cache_read_tokens, mu.cache_write_tokens "
            f"FROM model_usage mu WHERE mu.session_id IN ({placeholders})",
            session_keys,
        ).fetchall()
        for model, reqs, inp, out, cache, cache_read, cache_write in mrows:
            normalized = normalize_model_name(model)
            if normalized not in models_totals:
                models_totals[normalized] = {
                    "requests": 0, "input": 0, "output": 0,
                    "cache": 0, "cache_read": 0, "cache_write": 0,
                    "stored_cost": 0.0,
                }
            models_totals[normalized]["requests"] += reqs
            models_totals[normalized]["input"] += inp
            models_totals[normalized]["output"] += out
            models_totals[normalized]["cache"] += cache
            models_totals[normalized]["cache_read"] += cache_read
            models_totals[normalized]["cache_write"] += cache_write

        # Totales de sesión desde la tabla sessions
        srows_agg = conn.execute(
            f"SELECT source, requests, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens "
            f"FROM sessions WHERE id IN ({placeholders})",
            session_keys,
        ).fetchall()
        for source, reqs, inp, out, cache_read, cache_write in srows_agg:
            total_requests += reqs
            total_input += inp
            total_output += out
            total_tokens += effective_billable_tokens(source, inp, out, cache_read, cache_write)
            cache_ratio_input += effective_cache_ratio_input(source, inp, cache_read)
            total_cache_read += cache_read

    conn.close()

    total_sessions = base_sessions + len(session_keys)

    # Agregar tokens de historical_total desde model_usage
    if base_sessions > 0 and historical_total_cost > 0:
        conn2 = sqlite3.connect(str(DB_PATH))
        ht_rows = conn2.execute(
            "SELECT requests, input_tokens, output_tokens FROM model_usage WHERE session_id = 'historical_total'"
        ).fetchall()
        for reqs, inp, out in ht_rows:
            total_requests += reqs
            total_input += inp
            total_output += out
        conn2.close()

    # 3. Agregar sesiones de Codex que NO estan en SQLite
    existing_codex_ids = {
        k.replace("codex_", "") for k in session_keys if k.startswith("codex_")
    }
    for sess_file in get_codex_sessions():
        if not has_real_usage_codex(sess_file):
            continue
        stats = get_codex_session_stats(sess_file)
        sid = stats.get("session_id", "")
        if sid and sid not in existing_codex_ids:
            normalized = normalize_model_name(stats["model"])
            if normalized not in models_totals:
                models_totals[normalized] = {
                    "requests": 0, "input": 0, "output": 0,
                    "cache": 0, "cache_read": 0, "cache_write": 0,
                    "stored_cost": 0.0,
                }
            models_totals[normalized]["requests"] += stats["requests"]
            models_totals[normalized]["input"] += stats["input"]
            models_totals[normalized]["output"] += stats["output"]
            models_totals[normalized]["cache"] += stats["cache"]
            total_requests += stats["requests"]
            total_input += stats["input"]
            total_output += stats["output"]
            cache_read = stats.get("cache_read", stats.get("cache", 0))
            cache_write = stats.get("cache_write", 0)
            total_tokens += effective_billable_tokens("codex", stats["input"], stats["output"], cache_read, cache_write)
            cache_ratio_input += effective_cache_ratio_input("codex", stats["input"], cache_read)
            total_cache_read += cache_read
            total_sessions += 1

    # 4. Agregar sesiones de OpenCode SQLite (v1.3.0+) que NO estan en SQLite
    opencode_sqlite_sessions = get_opencode_sqlite_sessions()
    for sid, stats in opencode_sqlite_sessions.items():
        if sid in session_keys:
            continue
        by_model = stats.get("by_model", {})
        for model, model_data in by_model.items():
            normalized = normalize_model_name(model)
            if normalized not in models_totals:
                models_totals[normalized] = {
                    "requests": 0, "input": 0, "output": 0,
                    "cache": 0, "cache_read": 0, "cache_write": 0,
                    "stored_cost": 0.0,
                }
            models_totals[normalized]["requests"] += model_data.get("requests", 0)
            models_totals[normalized]["input"] += model_data.get("input", 0)
            models_totals[normalized]["output"] += model_data.get("output", 0)
            cache_read = model_data.get("cache_read", model_data.get("cache", 0))
            cache_write = model_data.get("cache_write", 0)
            models_totals[normalized]["cache"] += model_data.get("cache", 0)
            models_totals[normalized]["cache_read"] += cache_read
            models_totals[normalized]["cache_write"] += cache_write
        cache_read = stats.get("cache_read", stats.get("cache", 0))
        cache_write = stats.get("cache_write", 0)
        total_requests += stats["requests"]
        total_input += stats["input"]
        total_output += stats["output"]
        total_tokens += effective_billable_tokens("opencode", stats["input"], stats["output"], cache_read, cache_write)
        cache_ratio_input += effective_cache_ratio_input("opencode", stats["input"], cache_read)
        total_cache_read += cache_read
        total_sessions += 1

    # 5. Agregar sesiones de Hermes que NO estan en SQLite
    for sess in get_hermes_sessions():
        sid = sess["id"]
        if sid in session_keys:
            continue
        by_model = sess.get("by_model", {})
        for model, model_data in by_model.items():
            normalized = normalize_model_name(model)
            if normalized not in models_totals:
                models_totals[normalized] = {
                    "requests": 0, "input": 0, "output": 0,
                    "cache": 0, "cache_read": 0, "cache_write": 0,
                    "stored_cost": 0.0,
                }
            models_totals[normalized]["requests"] += model_data.get("requests", 0)
            models_totals[normalized]["input"] += model_data.get("input", 0)
            models_totals[normalized]["output"] += model_data.get("output", 0)
            cache_read = model_data.get("cache_read", model_data.get("cache", 0))
            cache_write = model_data.get("cache_write", 0)
            models_totals[normalized]["cache"] += model_data.get("cache", 0)
            models_totals[normalized]["cache_read"] += cache_read
            models_totals[normalized]["cache_write"] += cache_write
        cache_read = sess.get("cache_read", sess.get("cache", 0))
        cache_write = sess.get("cache_write", 0)
        total_requests += sess.get("requests", 0)
        total_input += sess.get("input", 0)
        total_output += sess.get("output", 0)
        total_tokens += effective_billable_tokens("hermes", sess.get("input", 0), sess.get("output", 0), cache_read, cache_write)
        cache_ratio_input += effective_cache_ratio_input("hermes", sess.get("input", 0), cache_read)
        total_cache_read += cache_read
        total_sessions += 1

    # 6. Calcular costo total desde tokens + ajuste histórico
    # Agregar modelos de historical_total a models_totals (mismo comportamiento que versión JSON)
    historical_cost_adjustment = historical_total_cost - historical_models_cost

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
        "total_tokens": total_tokens,
        "cache_ratio": round(total_cache_read / cache_ratio_input * 100, 1) if cache_ratio_input > 0 else 0,
        "models_totals": models_totals,
    }


# --- SQLite Store ---

DB_PATH = SCRIPT_DIR / "session_history.db"


def _parse_timestamp(date_str):
    if not date_str:
        return None
    try:
        if date_str.endswith("Z"):
            date_str = date_str[:-1] + "+00:00"
        return int(datetime.datetime.fromisoformat(date_str).timestamp())
    except (ValueError, TypeError):
        return None


def _detect_source(session_id):
    if session_id in ("historical_total", "kilocode_legacy"):
        return "legacy"
    if session_id.startswith("codex_"):
        return "codex"
    if re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", session_id):
        try:
            if any(session_id in Path(p).name for p in get_codex_sessions()):
                return "codex"
        except Exception:
            pass
    if session_id.startswith("kilocode_") or session_id.startswith("kilo_"):
        return "kilocode"
    if session_id.startswith("hermes_"):
        return "hermes"
    if session_id.startswith("cursor_"):
        return "cursor"
    if session_id.startswith("opencode_") or session_id.startswith("ses_"):
        return "opencode"
    # Sesiones Hermes: formato YYYYMMDD_HHMMSS_*
    if len(session_id) > 15 and session_id[8] == '_' and session_id[15] == '_':
        try:
            int(session_id[:8])
            return "hermes"
        except ValueError:
            pass
    return "unknown"


def init_db(db_path=None):
    path = Path(db_path or DB_PATH)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL DEFAULT 'unknown',
            date TEXT NOT NULL,
            timestamp INTEGER,
            requests INTEGER NOT NULL DEFAULT 0,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cache_tokens INTEGER NOT NULL DEFAULT 0,
            reasoning_tokens INTEGER NOT NULL DEFAULT 0,
            cost REAL NOT NULL DEFAULT 0.0
        );
        CREATE TABLE IF NOT EXISTS model_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            model TEXT NOT NULL,
            requests INTEGER NOT NULL DEFAULT 0,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cache_tokens INTEGER NOT NULL DEFAULT 0,
            reasoning_tokens INTEGER NOT NULL DEFAULT 0,
            cost REAL NOT NULL DEFAULT 0.0,
            UNIQUE(session_id, model)
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_ts ON sessions(timestamp);
        CREATE INDEX IF NOT EXISTS idx_sessions_source ON sessions(source);
        CREATE INDEX IF NOT EXISTS idx_model_usage_model ON model_usage(model);
        CREATE INDEX IF NOT EXISTS idx_model_usage_session ON model_usage(session_id);
    """)
    _ensure_column(conn, "sessions", "cache_read_tokens", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "sessions", "cache_write_tokens", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "model_usage", "cache_read_tokens", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "model_usage", "cache_write_tokens", "INTEGER NOT NULL DEFAULT 0")
    conn.commit()
    conn.close()


def _ensure_column(conn, table, column, definition):
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def save_session(sid, source, date, timestamp, requests, input_tokens,
                 output_tokens, cache_tokens, reasoning_tokens, cost,
                 by_model, db_path=None,
                 cache_read_tokens=None, cache_write_tokens=None):
    """Persiste/actualiza estadísticas de una sesión en session_history.db.

    NOTA: El 2025-06-25 se cambió INSERT OR REPLACE por INSERT ... ON CONFLICT
    DO UPDATE SET con MAX() para evitar que borrar conversaciones en OpenCode
    (o cualquier fuente) pisé valores históricos altos con datos más bajos.

    Rollback: copiar el .bak sobre este archivo y reiniciar.

    2026-07-01: se agregaron cache_read_tokens, cache_write_tokens y MIN() en timestamp.
    """
    if cache_read_tokens is None:
        cache_read_tokens = sum((m.get("cache_read", m.get("cache", 0)) or 0) for m in by_model.values())
    if cache_write_tokens is None:
        cache_write_tokens = sum((m.get("cache_write", 0) or 0) for m in by_model.values())
    path = Path(db_path or DB_PATH)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute(
        """INSERT INTO sessions
        (id, source, date, timestamp, requests, input_tokens, output_tokens,
         cache_tokens, reasoning_tokens, cost,
         cache_read_tokens, cache_write_tokens)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          date = MIN(date, excluded.date),
          timestamp = MIN(timestamp, excluded.timestamp),
          requests = MAX(requests, excluded.requests),
          input_tokens = MAX(input_tokens, excluded.input_tokens),
          output_tokens = MAX(output_tokens, excluded.output_tokens),
          cache_tokens = MAX(cache_tokens, excluded.cache_tokens),
          reasoning_tokens = MAX(reasoning_tokens, excluded.reasoning_tokens),
          cost = MAX(cost, excluded.cost),
          cache_read_tokens = MAX(cache_read_tokens, excluded.cache_read_tokens),
          cache_write_tokens = MAX(cache_write_tokens, excluded.cache_write_tokens)""",
        (sid, source, date, timestamp, requests, input_tokens, output_tokens,
         cache_tokens, reasoning_tokens, cost,
         cache_read_tokens, cache_write_tokens)
    )
    for model, mdata in by_model.items():
        mu_cache_read = mdata.get("cache_read", mdata.get("cache", 0))
        mu_cache_write = mdata.get("cache_write", 0)
        conn.execute(
            """INSERT INTO model_usage
            (session_id, model, requests, input_tokens, output_tokens,
             cache_tokens, reasoning_tokens, cost,
             cache_read_tokens, cache_write_tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id, model) DO UPDATE SET
              requests = MAX(requests, excluded.requests),
              input_tokens = MAX(input_tokens, excluded.input_tokens),
              output_tokens = MAX(output_tokens, excluded.output_tokens),
              cache_tokens = MAX(cache_tokens, excluded.cache_tokens),
              reasoning_tokens = MAX(reasoning_tokens, excluded.reasoning_tokens),
              cost = MAX(cost, excluded.cost),
              cache_read_tokens = MAX(cache_read_tokens, excluded.cache_read_tokens),
              cache_write_tokens = MAX(cache_write_tokens, excluded.cache_write_tokens)""",
            (sid, model,
             mdata.get("requests", 0),
             mdata.get("input", 0),
             mdata.get("output", 0),
             mdata.get("cache", mdata.get("cache_read", 0) + mdata.get("cache_write", 0)),
             mdata.get("reasoning", 0),
             mdata.get("cost", 0.0),
             mu_cache_read,
             mu_cache_write)
        )
    conn.commit()
    conn.close()


def get_sessions(date_from=None, date_to=None, db_path=None):
    path = Path(db_path or DB_PATH)
    if not path.exists():
        return []
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM sessions"
    params = []
    conditions = []
    if date_from:
        conditions.append("date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("date <= ?")
        params.append(date_to)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY timestamp DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_model_summary(db_path=None):
    path = Path(db_path or DB_PATH)
    if not path.exists():
        return {}
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT model,
        SUM(requests) as requests,
        SUM(input_tokens) as input_tokens,
        SUM(output_tokens) as output_tokens,
        SUM(cache_tokens) as cache_tokens,
        SUM(reasoning_tokens) as reasoning_tokens,
        SUM(cost) as cost
        FROM model_usage
        GROUP BY model
        ORDER BY cost DESC"""
    ).fetchall()
    conn.close()
    return {r["model"]: dict(r) for r in rows}


def get_monthly_data(db_path=None):
    path = Path(db_path or DB_PATH)
    if not path.exists():
        return {}
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT strftime('%%Y-%%m', date) as month,
        COUNT(*) as sessions,
        SUM(requests) as requests,
        SUM(input_tokens) as input_tokens,
        SUM(output_tokens) as output_tokens,
        SUM(cache_tokens) as cache_tokens,
        SUM(reasoning_tokens) as reasoning_tokens,
        SUM(cost) as cost
        FROM sessions
        WHERE source != 'legacy'
        GROUP BY month
        ORDER BY month DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def migrate_json_to_sqlite(json_path=None, db_path=None):
    json_file = Path(json_path or SCRIPT_DIR / "session_history.json")
    if not json_file.exists():
        print(f"JSON not found: {json_file}")
        return False

    with open(json_file) as f:
        data = json.load(f)

    init_db(db_path)
    count = 0
    for sid, session in data.items():
        source = _detect_source(sid)
        date = session.get("date", "")
        timestamp = _parse_timestamp(date)
        requests = session.get("requests", 0)
        input_tokens = session.get("input", 0)
        output_tokens = session.get("output", 0)
        cache_tokens = session.get("cache", 0)
        cost = session.get("cost", 0.0)
        by_model = session.get("by_model", {})

        reasoning_tokens = sum(
            m.get("reasoning", 0) for m in by_model.values()
        )

        # Store historical_total.sessions count in reasoning_tokens
        if sid == "historical_total":
            reasoning_tokens = session.get("sessions", 0)

        save_session(
            sid=sid, source=source, date=date, timestamp=timestamp,
            requests=requests, input_tokens=input_tokens,
            output_tokens=output_tokens, cache_tokens=cache_tokens,
            reasoning_tokens=reasoning_tokens, cost=cost,
            by_model=by_model, db_path=db_path
        )
        count += 1

    print(f"Migrated {count} sessions to {db_path or DB_PATH}")
    return True


def verify_parity(json_path=None, db_path=None):
    json_file = Path(json_path or SCRIPT_DIR / "session_history.json")
    path = Path(db_path or DB_PATH)

    with open(json_file) as f:
        json_data = json.load(f)

    conn = sqlite3.connect(str(path))
    db_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    json_count = len(json_data)
    print(f"Sessions: JSON={json_count}, SQLite={db_count}")

    db_cost = conn.execute("SELECT COALESCE(SUM(cost),0) FROM sessions").fetchone()[0]
    json_cost = sum(s.get("cost", 0) for s in json_data.values())
    print(f"Total cost: JSON={json_cost:.6f}, SQLite={db_cost:.6f}")

    db_input = conn.execute("SELECT COALESCE(SUM(input_tokens),0) FROM sessions").fetchone()[0]
    json_input = sum(s.get("input", 0) for s in json_data.values())
    print(f"Total input: JSON={json_input}, SQLite={db_input}")

    db_output = conn.execute("SELECT COALESCE(SUM(output_tokens),0) FROM sessions").fetchone()[0]
    json_output = sum(s.get("output", 0) for s in json_data.values())
    print(f"Total output: JSON={json_output}, SQLite={db_output}")

    db_requests = conn.execute("SELECT COALESCE(SUM(requests),0) FROM sessions").fetchone()[0]
    json_requests = sum(s.get("requests", 0) for s in json_data.values())
    print(f"Total requests: JSON={json_requests}, SQLite={db_requests}")

    conn.close()
    return (
        db_count == json_count
        and abs(db_cost - json_cost) < 0.01
        and db_input == json_input
        and db_output == json_output
        and db_requests == json_requests
    )


def backup_db(target_dir=None, keep=7, db_path=None):
    """Backup online de session_history.db con rotación."""
    target = Path(target_dir or SCRIPT_DIR / "db_backups")
    target.mkdir(exist_ok=True)
    ts = __import__("time").strftime("%Y%m%d_%H%M%S")
    dest = target / f"session_history_{ts}.db"

    srce = Path(db_path or DB_PATH)
    if not srce.exists():
        print(f"DB not found: {srce}")
        return None

    conn_src = sqlite3.connect(str(srce))
    conn_dst = sqlite3.connect(str(dest))
    conn_src.backup(conn_dst)
    conn_dst.close()
    conn_src.close()

    backups = sorted(target.glob("session_history_*.db"))
    for old in backups[:-keep]:
        old.unlink()

    size = dest.stat().st_size
    print(f"Backup: {dest.name} ({size / 1024:.1f} KB), {len(backups)} total, keeping {keep}")
    return str(dest)
