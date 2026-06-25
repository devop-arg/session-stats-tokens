import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

import sqlite3
import datetime
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from stats_common import DB_PATH, get_monthly_data, recalculate_historical_cost

app = FastAPI(title="session-stats dashboard")

templates = Jinja2Templates(directory=str(SCRIPT_DIR / "stats-web/templates"))
app.mount("/static", StaticFiles(directory=str(SCRIPT_DIR / "stats-web/static")), name="static")
app.mount("/vendor", StaticFiles(directory=str(SCRIPT_DIR / "stats-web/vendor")), name="vendor")


def _db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def _today():
    return datetime.date.today().isoformat()


def _days_ago(n):
    return (datetime.date.today() - datetime.timedelta(days=n)).isoformat()


def _author(model_name: str) -> str:
    """Mapea un nombre de modelo a su autor/fabricante."""
    m = model_name.lower()
    if "/" in m:
        # openrouter/hunter-alpha, etc.
        return "OpenRouter"
    if any(k in m for k in ["gpt", "o1", "o3", "o4", "codex", "openai"]):
        return "OpenAI"
    if any(k in m for k in ["claude", "anthropic"]):
        return "Anthropic"
    if any(k in m for k in ["deepseek"]):
        return "DeepSeek"
    if any(k in m for k in ["kimi", "moonshot"]):
        return "Moonshot"
    if any(k in m for k in ["mimo", "xiaomi"]):
        return "Xiaomi"
    if any(k in m for k in ["qwen", "qwq", "tongyi"]):
        return "Qwen"
    if any(k in m for k in ["glm", "chatglm", "zhipu"]):
        return "Zhipu"
    if any(k in m for k in ["minimax", "abab"]):
        return "MiniMax"
    if any(k in m for k in ["gemini", "gemma", "palm"]):
        return "Google"
    if any(k in m for k in ["llama", "meta"]):
        return "Meta"
    if any(k in m for k in ["mistral", "mixtral"]):
        return "Mistral"
    if any(k in m for k in ["command", "cohere"]):
        return "Cohere"
    if any(k in m for k in ["nex-agi", "nex-"]):
        return "Nex AGI"
    if any(k in m for k in ["grok", "xai"]):
        return "xAI"
    return "Other"


# --- HTML Pages ---

@app.get("/healthz")
def healthz():
    if DB_PATH.exists():
        conn = _db()
        conn.execute("SELECT 1")
        conn.close()
        return {"status": "ok"}
    return JSONResponse({"status": "error", "msg": "DB not found"}, status_code=503)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/sessions", response_class=HTMLResponse)
def sessions_page(request: Request):
    return templates.TemplateResponse("sessions.html", {"request": request})


@app.get("/models", response_class=HTMLResponse)
def models_page(request: Request):
    return templates.TemplateResponse("models.html", {"request": request})


# --- API Endpoints ---

@app.get("/api/summary")
def api_summary():
    conn = _db()

    overall = conn.execute("""
        SELECT COUNT(*) as total_sessions,
               COALESCE(SUM(requests),0) as total_requests,
               COALESCE(SUM(input_tokens),0) as total_input_tokens,
               COALESCE(SUM(output_tokens),0) as total_output_tokens,
               COALESCE(SUM(cache_tokens),0) as total_cache_tokens,
               COALESCE(SUM(cost),0) as total_cost
        FROM sessions
        WHERE source != 'legacy'
    """).fetchone()

    cost_7d = conn.execute(
        "SELECT COALESCE(SUM(cost),0) FROM sessions WHERE source != 'legacy' AND date >= ?",
        (_days_ago(7),)
    ).fetchone()[0]

    cost_30d = conn.execute(
        "SELECT COALESCE(SUM(cost),0) FROM sessions WHERE source != 'legacy' AND date >= ?",
        (_days_ago(30),)
    ).fetchone()[0]

    conn.close()

    return {
        "total_sessions": overall["total_sessions"],
        "total_requests": overall["total_requests"],
        "total_input_tokens": overall["total_input_tokens"],
        "total_output_tokens": overall["total_output_tokens"],
        "total_cache_tokens": overall["total_cache_tokens"],
        "total_cost": round(overall["total_cost"], 2),
        "cache_ratio": round((overall["total_cache_tokens"] / (overall["total_input_tokens"] + overall["total_cache_tokens"]) * 100) if (overall["total_input_tokens"] + overall["total_cache_tokens"]) > 0 else 0, 1),
        "cost_7d": round(cost_7d, 2),
        "cost_30d": round(cost_30d, 2),
        "last_updated": datetime.datetime.now().isoformat(timespec="minutes"),
    }


@app.get("/api/timeseries")
def api_timeseries(
    range: str = Query("30d", regex=r"^(7d|30d|90d|all)$"),
    bucket: str = Query("day", regex=r"^(day|week|month)$"),
):
    date_from = None if range == "all" else _days_ago(int(range.replace("d", "")))

    conn = _db()
    if bucket == "month":
        rows = conn.execute("""
            SELECT strftime('%Y-%m-01', date) as period,
                   COUNT(*) as sessions,
                   COALESCE(SUM(requests),0) as requests,
                   COALESCE(SUM(input_tokens),0) as input_tokens,
                   COALESCE(SUM(output_tokens),0) as output_tokens,
                   COALESCE(SUM(cache_tokens),0) as cache_tokens,
                   COALESCE(SUM(cost),0) as cost
            FROM sessions
            WHERE source != 'legacy'""" + (" AND date >= ?" if date_from else "") + """
            GROUP BY period ORDER BY period ASC
        """, ([date_from] if date_from else [])).fetchall()
    elif bucket == "week":
        rows = conn.execute("""
            SELECT date(date, 'weekday 1') as period,
                   COUNT(*) as sessions,
                   COALESCE(SUM(requests),0) as requests,
                   COALESCE(SUM(input_tokens),0) as input_tokens,
                   COALESCE(SUM(output_tokens),0) as output_tokens,
                   COALESCE(SUM(cache_tokens),0) as cache_tokens,
                   COALESCE(SUM(cost),0) as cost
            FROM sessions
            WHERE source != 'legacy'""" + (" AND date >= ?" if date_from else "") + """
            GROUP BY period ORDER BY period ASC
        """, ([date_from] if date_from else [])).fetchall()
    else:
        rows = conn.execute("""
            SELECT DATE(date) as period,
                   COUNT(*) as sessions,
                   COALESCE(SUM(requests),0) as requests,
                   COALESCE(SUM(input_tokens),0) as input_tokens,
                   COALESCE(SUM(output_tokens),0) as output_tokens,
                   COALESCE(SUM(cache_tokens),0) as cache_tokens,
                   COALESCE(SUM(cost),0) as cost
            FROM sessions
            WHERE source != 'legacy'""" + (" AND date >= ?" if date_from else "") + """
            GROUP BY period ORDER BY period ASC
        """, ([date_from] if date_from else [])).fetchall()

    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/models")
def api_models(limit: int = Query(20, ge=1, le=200)):
    conn = _db()
    rows = conn.execute("""
        SELECT model,
               COALESCE(SUM(requests),0) as requests,
               COALESCE(SUM(input_tokens),0) as input_tokens,
               COALESCE(SUM(output_tokens),0) as output_tokens,
               COALESCE(SUM(cache_tokens),0) as cache_tokens,
               COALESCE(SUM(cost),0) as cost
        FROM model_usage
        GROUP BY model
        ORDER BY cost DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/sessions")
def api_sessions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    source: str = Query(None),
):
    conn = _db()

    where = "WHERE source != 'legacy'"
    params = []
    if source:
        where += " AND source = ?"
        params.append(source)

    total = conn.execute(
        f"SELECT COUNT(*) FROM sessions {where}", params
    ).fetchone()[0]

    rows = conn.execute(
        f"SELECT id, source, date, requests, input_tokens, output_tokens, cache_tokens, cost "
        f"FROM sessions {where} ORDER BY date DESC, timestamp DESC LIMIT ? OFFSET ?",
        params + [limit, offset]
    ).fetchall()

    conn.close()
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "sessions": [dict(r) for r in rows],
    }


@app.get("/api/sources")
def api_sources():
    conn = _db()
    total_cost = conn.execute(
        "SELECT COALESCE(SUM(cost),0) FROM sessions WHERE source != 'legacy'"
    ).fetchone()[0]

    rows = conn.execute("""
        SELECT source,
               COUNT(*) as sessions,
               COALESCE(SUM(requests),0) as requests,
               COALESCE(SUM(cost),0) as cost
        FROM sessions
        WHERE source != 'legacy'
        GROUP BY source
        ORDER BY cost DESC
    """).fetchall()

    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["percentage"] = round((d["cost"] / total_cost * 100) if total_cost > 0 else 0, 1)
        result.append(d)
    return result


# --- Nuevos endpoints estilo opencode.ai/data ---

# Format de fecha para chart: "25/JUN", "01/ENE", etc.
_MONTH_ABBR = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN",
               "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]


def _fmt_date_short(iso_date: str) -> str:
    """Convierte '2026-06-25' -> '25/JUN'."""
    try:
        y, m, d = iso_date.split("-")
        return f"{int(d):02d}/{_MONTH_ABBR[int(m) - 1]}"
    except Exception:
        return iso_date


def _provider_key(author: str) -> str:
    """Convierte un author al slug usado en el leaderboard de opencode."""
    a = author.lower()
    if a == "minimax":
        return "minimax"
    if a == "moonshot":
        return "moonshotai"
    if a == "zhipu":
        return "zhipuai"
    return a


@app.get("/api/top-models")
def api_top_models():
    """Top modelos — 12 meses, agrupado por semana (52 semanas).

    - `usage`: 52 puntos semanales. Segmentos = top 20 modelos all-time + "Other".
    - `leaderboard`: top 20 all-time con % de uso.
    - `topModels`: lista de los 20 modelos con color asignado.

    Response shape:
      {
        "range": "12M",
        "updatedAt": "...",
        "usage": {"All Users": {"12M": Point[]}},
        "leaderboard": [Leader, ...],
        "topModels": ["gpt-5.4", "minimax-m3", ...]
      }
      Point  = {"date": "MAY 5", "segments": [{"model": "gpt-5.4", "value": 123}]}
      Leader = {"model": "...", "author": "...", "tokens": 12345, "percent": 82.4, "rank": 1}
    """
    conn = _db()

    # 1) Top 20 modelos all-time (segmentos del chart + colores)
    top20_rows = conn.execute("""
        SELECT mu.model,
               COALESCE(SUM(mu.input_tokens),0) + COALESCE(SUM(mu.output_tokens),0) + COALESCE(SUM(mu.cache_tokens),0) as total_tokens
        FROM model_usage mu
        JOIN sessions s ON s.id = mu.session_id
        WHERE s.source != 'legacy'
        GROUP BY mu.model
        ORDER BY total_tokens DESC
        LIMIT 20
    """).fetchall()
    top_models = [r["model"] for r in top20_rows]
    top_set = set(top_models)

    # 2) Leaderboard all-time (top 20 para las tarjetas)
    all_time_rows = conn.execute("""
        SELECT mu.model,
               COALESCE(SUM(mu.input_tokens),0) + COALESCE(SUM(mu.output_tokens),0) + COALESCE(SUM(mu.cache_tokens),0) as total_tokens
        FROM model_usage mu
        JOIN sessions s ON s.id = mu.session_id
        WHERE s.source != 'legacy'
        GROUP BY mu.model
        ORDER BY total_tokens DESC
        LIMIT 20
    """).fetchall()

    # 3) Grand total all-time
    grand_total_row = conn.execute("""
        SELECT COALESCE(SUM(mu.input_tokens),0) + COALESCE(SUM(mu.output_tokens),0) + COALESCE(SUM(mu.cache_tokens),0) as total
        FROM model_usage mu
        JOIN sessions s ON s.id = mu.session_id
        WHERE s.source != 'legacy'
    """).fetchone()
    grand_total = max(1, grand_total_row["total"] or 1)

    # 4) Breakdown semanal por modelo (52 semanas)
    today = datetime.date.today()
    current_monday = today - datetime.timedelta(days=today.weekday())
    first_monday = current_monday - datetime.timedelta(weeks=51)
    date_from = first_monday.isoformat()

    weekly_rows = conn.execute("""
        SELECT date(date(s.date), 'weekday 1') as week_start, mu.model,
               COALESCE(SUM(mu.input_tokens),0) + COALESCE(SUM(mu.output_tokens),0) + COALESCE(SUM(mu.cache_tokens),0) as tokens
        FROM model_usage mu
        JOIN sessions s ON s.id = mu.session_id
        WHERE s.source != 'legacy' AND s.date >= ?
        GROUP BY week_start, mu.model
        ORDER BY week_start ASC
    """, (date_from,)).fetchall()

    conn.close()

    # 5) Agrupar por semana → modelo
    weekly_by_model: dict[str, dict[str, int]] = {}
    for r2 in weekly_rows:
        weekly_by_model.setdefault(r2["week_start"], {})[r2["model"]] = r2["tokens"]

    # 6) Generar las 52 semanas (incluyendo vacías)
    week_starts = [(current_monday - datetime.timedelta(weeks=i)).isoformat()
                   for i in range(51, -1, -1)]

    # 7) Construir points
    points = []
    for ws in week_starts:
        week_data = weekly_by_model.get(ws, {})
        segments = []
        for m in top_models:
            v = week_data.get(m, 0)
            if v > 0:
                segments.append({"model": m, "value": v})
        other_val = sum(v for m, v in week_data.items() if m not in top_set)
        if other_val > 0:
            segments.append({"model": "Other", "value": other_val})
        points.append({
            "date": _fmt_date_short(ws),
            "_iso": ws,
            "segments": segments,
        })

    # 8) Leaderboard all-time con %
    leaderboard = []
    for i, r2 in enumerate(all_time_rows):
        author = _author(r2["model"])
        tokens = r2["total_tokens"]
        leaderboard.append({
            "model": r2["model"],
            "author": author,
            "tokens": tokens,
            "percent": round(tokens / grand_total * 100, 2),
            "rank": i + 1,
        })

    return {
        "range": "12M",
        "updatedAt": datetime.datetime.utcnow().isoformat() + "Z",
        "usage": {
            "All Users": {"12M": points},
        },
        "leaderboard": leaderboard,
        "topModels": top_models,
    }


@app.get("/api/token-cost")
def api_token_cost():
    """Precio efectivo por 1M de tokens por modelo."""
    conn = _db()

    overall = conn.execute("""
        SELECT COALESCE(SUM(cost),0) as total_cost,
               COALESCE(SUM(input_tokens),0) + COALESCE(SUM(output_tokens),0) + COALESCE(SUM(cache_tokens),0) as total_tokens
        FROM sessions WHERE source != 'legacy'
    """).fetchone()

    rows = conn.execute("""
        SELECT model,
               COALESCE(SUM(cost),0) as total_cost,
               COALESCE(SUM(input_tokens),0) as input_tokens,
               COALESCE(SUM(output_tokens),0) as output_tokens,
               COALESCE(SUM(cache_tokens),0) as cache_tokens
        FROM model_usage
        GROUP BY model
        HAVING (COALESCE(SUM(input_tokens),0) + COALESCE(SUM(output_tokens),0) + COALESCE(SUM(cache_tokens),0)) >= 1000000
        ORDER BY total_cost DESC
    """).fetchall()

    models = []
    for r in rows:
        d = dict(r)
        tt = d["input_tokens"] + d["output_tokens"] + d["cache_tokens"]
        d["total_tokens"] = tt
        d["price_per_1m"] = round(d["total_cost"] / tt * 1_000_000, 4) if tt > 0 else 0
        models.append(d)

    conn.close()

    tt = overall["total_tokens"]
    return {
        "overall": {
            "total_cost": round(overall["total_cost"], 2),
            "total_tokens": tt,
            "price_per_1m": round(overall["total_cost"] / tt * 1_000_000, 4) if tt > 0 else 0,
        },
        "models": models,
    }


@app.get("/api/cache-ratio")
def api_cache_ratio():
    """Proporción de tokens input servidos desde cache por modelo.

    Se omiten los modelos sin cache_tokens > 0 (no trabajan con cache) para
    no distorsionar el cache ratio real.
    """
    conn = _db()

    # Overall: solo modelos que realmente usan cache (cache_tokens > 0)
    overall = conn.execute("""
        SELECT COALESCE(SUM(mu.input_tokens),0) + COALESCE(SUM(mu.cache_tokens),0) as total_input,
               COALESCE(SUM(mu.cache_tokens),0) as cached
        FROM model_usage mu
        JOIN sessions s ON s.id = mu.session_id
        WHERE s.source != 'legacy' AND mu.cache_tokens > 0
    """).fetchone()

    rows = conn.execute("""
        SELECT model,
               COALESCE(SUM(input_tokens),0) as input_tokens,
               COALESCE(SUM(cache_tokens),0) as cache_tokens
        FROM model_usage
        GROUP BY model
        HAVING COALESCE(SUM(cache_tokens),0) > 0
           AND (COALESCE(SUM(input_tokens),0) + COALESCE(SUM(cache_tokens),0)) >= 1000000
        ORDER BY (CAST(COALESCE(SUM(cache_tokens),0) AS REAL) / (COALESCE(SUM(input_tokens),0) + COALESCE(SUM(cache_tokens),0))) DESC
    """).fetchall()

    models = []
    for r in rows:
        d = dict(r)
        ti = d["input_tokens"] + d["cache_tokens"]
        d["ratio"] = round(d["cache_tokens"] / ti * 100, 1) if ti > 0 else 0
        models.append(d)

    conn.close()

    ti = overall["total_input"]
    return {
        "overall": {
            "ratio": round(overall["cached"] / ti * 100, 1) if ti > 0 else 0,
            "cached": overall["cached"],
            "uncached": ti - overall["cached"],
        },
        "models": models,
    }


@app.exception_handler(Exception)
def global_exception(request: Request, exc: Exception):
    return JSONResponse({"error": str(exc)}, status_code=500)
