import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

import sqlite3
import datetime
import zoneinfo
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from stats_common import DB_PATH, get_monthly_data, recalculate_historical_cost

app = FastAPI(title="session-stats dashboard")

templates = Jinja2Templates(directory=str(SCRIPT_DIR / "stats-web/templates"))
app.mount("/static", StaticFiles(directory=str(SCRIPT_DIR / "stats-web/static")), name="static")
app.mount("/vendor", StaticFiles(directory=str(SCRIPT_DIR / "stats-web/vendor")), name="vendor")

ART_TZ = zoneinfo.ZoneInfo("America/Argentina/Buenos_Aires")
ART_SQL_OFFSET = "-3 hours"


def _db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def _art_today():
    return datetime.datetime.now(ART_TZ).date()


def _art_day_bounds(day: datetime.date):
    start = datetime.datetime.combine(day, datetime.time.min, tzinfo=ART_TZ)
    end = start + datetime.timedelta(days=1)
    return start, end, int(start.timestamp()), int(end.timestamp())


def _art_window_days(days: int):
    end_day = _art_today()
    start_day = end_day - datetime.timedelta(days=days - 1)
    start_dt, _, start_ts, _ = _art_day_bounds(start_day)
    _, end_dt, _, end_ts = _art_day_bounds(end_day)
    return {
        "start_day": start_day,
        "end_day": end_day,
        "start_dt": start_dt,
        "end_dt": end_dt,
        "start_ts": start_ts,
        "end_ts": end_ts,
    }


def _sql_period_expr(bucket: str, column: str = "timestamp") -> str:
    local_dt = f"datetime({column}, 'unixepoch', '{ART_SQL_OFFSET}')"
    if bucket == "month":
        return f"strftime('%Y-%m-01', {local_dt})"
    if bucket == "week":
        return f"date({local_dt}, 'weekday 0', '-6 days')"
    return f"date({local_dt})"


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
    window_7d = _art_window_days(7)
    window_30d = _art_window_days(30)

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
        "SELECT COALESCE(SUM(cost),0) FROM sessions WHERE source != 'legacy' AND timestamp >= ? AND timestamp < ?",
        (window_7d["start_ts"], window_7d["end_ts"])
    ).fetchone()[0]

    cost_30d = conn.execute(
        "SELECT COALESCE(SUM(cost),0) FROM sessions WHERE source != 'legacy' AND timestamp >= ? AND timestamp < ?",
        (window_30d["start_ts"], window_30d["end_ts"])
    ).fetchone()[0]

    conn.close()

    try:
        rh = recalculate_historical_cost()
        hc = {
            "sessions": rh["total_sessions"],
            "requests": rh["total_requests"],
            "cost": round(rh["total_cost"], 2),
            "input_tokens": rh["total_input"],
            "output_tokens": rh["total_output"],
            "cache_tokens": sum(m.get("cache", 0) for m in rh["models_totals"].values()),
        }
        hc["cache_ratio"] = round(
            hc["cache_tokens"] / (hc["input_tokens"] + hc["cache_tokens"]) * 100, 1
        ) if (hc["input_tokens"] + hc["cache_tokens"]) > 0 else 0
        totals_cli = hc
    except Exception:
        totals_cli = None

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
        "header_totals_cli": totals_cli,
        "last_updated": datetime.datetime.now(ART_TZ).isoformat(timespec="minutes"),
    }


@app.get("/api/today-summary")
def api_today_summary():
    """Métricas del día actual en hora Argentina (00:00 a 23:59 ART)."""
    _, _, start_utc, end_utc = _art_day_bounds(_art_today())

    conn = _db()

    sess = conn.execute("""
        SELECT COALESCE(SUM(requests),0) as total_requests,
               COALESCE(SUM(input_tokens),0) + COALESCE(SUM(output_tokens),0) + COALESCE(SUM(cache_tokens),0) as total_tokens,
               COALESCE(SUM(cost),0) as total_cost
        FROM sessions
        WHERE source != 'legacy' AND timestamp >= ? AND timestamp < ?
    """, (start_utc, end_utc)).fetchone()

    total_tokens = sess["total_tokens"]
    if total_tokens == 0:
        conn.close()
        return None

    models = conn.execute("""
        SELECT mu.model,
               COALESCE(SUM(mu.requests),0) as requests,
               COALESCE(SUM(mu.cost),0) as cost,
               COALESCE(SUM(mu.input_tokens),0) + COALESCE(SUM(mu.output_tokens),0) + COALESCE(SUM(mu.cache_tokens),0) as tokens
        FROM model_usage mu
        JOIN sessions s ON s.id = mu.session_id
        WHERE s.source != 'legacy' AND s.timestamp >= ? AND s.timestamp < ?
        GROUP BY mu.model
        ORDER BY tokens DESC
        LIMIT 5
    """, (start_utc, end_utc)).fetchall()

    conn.close()

    top_models = []
    for m in models:
        top_models.append({
            "model": m["model"],
            "requests": m["requests"],
            "cost": round(m["cost"], 4),
            "tokens": m["tokens"],
            "percent": round(m["tokens"] / total_tokens * 100, 1),
        })

    return {
        "total_requests": sess["total_requests"],
        "total_tokens": total_tokens,
        "total_cost": round(sess["total_cost"], 4),
        "top_models": top_models,
    }


@app.get("/api/timeseries")
def api_timeseries(
    range: str = Query("30d", pattern=r"^(7d|30d|90d|all)$"),
    bucket: str = Query("day", pattern=r"^(day|week|month)$"),
):
    window = None if range == "all" else _art_window_days(int(range.replace("d", "")))
    period_expr = _sql_period_expr(bucket)

    conn = _db()
    query = f"""
        SELECT {period_expr} as period,
               COUNT(*) as sessions,
               COALESCE(SUM(requests),0) as requests,
               COALESCE(SUM(input_tokens),0) as input_tokens,
               COALESCE(SUM(output_tokens),0) as output_tokens,
               COALESCE(SUM(cache_tokens),0) as cache_tokens,
               COALESCE(SUM(cost),0) as cost
        FROM sessions
        WHERE source != 'legacy'
    """
    params = []
    if window:
        query += " AND timestamp >= ? AND timestamp < ?"
        params.extend([window["start_ts"], window["end_ts"]])
    query += " GROUP BY period ORDER BY period ASC"
    rows = conn.execute(query, params).fetchall()

    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/timeseries/sources")
def api_timeseries_sources(
    range: str = Query("all", pattern=r"^(7d|30d|90d|all)$"),
    bucket: str = Query("week", pattern=r"^(day|week|month)$"),
):
    window = None if range == "all" else _art_window_days(int(range.replace("d", "")))
    period_expr = _sql_period_expr(bucket)

    conn = _db()
    query = f"""
        SELECT {period_expr} as period,
               source,
               COUNT(*) as sessions,
               COALESCE(SUM(requests),0) as requests
        FROM sessions
        WHERE source NOT IN ('legacy')
    """
    params = []
    if window:
        query += " AND timestamp >= ? AND timestamp < ?"
        params.extend([window["start_ts"], window["end_ts"]])
    query += " GROUP BY period, source ORDER BY period ASC, sessions DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/models")
def api_models(limit: int = Query(20, ge=1, le=200)):
    conn = _db()
    rows = conn.execute("""
        SELECT mu.model,
               COALESCE(SUM(mu.requests),0) as requests,
               COALESCE(SUM(mu.input_tokens),0) as input_tokens,
               COALESCE(SUM(mu.output_tokens),0) as output_tokens,
               COALESCE(SUM(mu.cache_tokens),0) as cache_tokens,
               COALESCE(SUM(mu.cost),0) as cost
        FROM model_usage mu
        JOIN sessions s ON s.id = mu.session_id
        WHERE s.source != 'legacy'
        GROUP BY mu.model
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
        f"SELECT id, source, date, timestamp, requests, input_tokens, output_tokens, cache_tokens, cost "
        f"FROM sessions {where} ORDER BY timestamp DESC, id DESC LIMIT ? OFFSET ?",
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


def _build_top_models_payload(days: int, bucket: str, limit: int = 20):
    """Construye series y ranking de modelos para una ventana móvil."""
    today = _art_today()
    if bucket == "week":
        period_expr = _sql_period_expr("week", "s.timestamp")
        points_range = [
            (today - datetime.timedelta(days=today.weekday()) - datetime.timedelta(weeks=i)).isoformat()
            for i in range(51, -1, -1)
        ]
        range_label = "12M"
    else:
        start_date = today - datetime.timedelta(days=days - 1)
        period_expr = _sql_period_expr("day", "s.timestamp")
        points_range = [
            (start_date + datetime.timedelta(days=i)).isoformat()
            for i in range(days)
        ]
        range_label = f"{days}D"

    start_day = datetime.date.fromisoformat(points_range[0])
    _, _, start_ts, _ = _art_day_bounds(start_day)
    _, _, _, end_ts = _art_day_bounds(today)
    conn = _db()

    top_rows = conn.execute("""
        SELECT mu.model,
               COALESCE(SUM(mu.input_tokens),0) + COALESCE(SUM(mu.output_tokens),0) + COALESCE(SUM(mu.cache_tokens),0) as total_tokens
        FROM model_usage mu
        JOIN sessions s ON s.id = mu.session_id
        WHERE s.source != 'legacy' AND s.timestamp >= ? AND s.timestamp < ?
        GROUP BY mu.model
        ORDER BY total_tokens DESC
        LIMIT ?
    """, (start_ts, end_ts, limit)).fetchall()
    top_models = [r["model"] for r in top_rows]
    top_set = set(top_models)

    leaderboard_rows = conn.execute("""
        SELECT mu.model,
               COALESCE(SUM(mu.input_tokens),0) + COALESCE(SUM(mu.output_tokens),0) + COALESCE(SUM(mu.cache_tokens),0) as total_tokens,
               COALESCE(SUM(mu.cost),0) as total_cost
        FROM model_usage mu
        JOIN sessions s ON s.id = mu.session_id
        WHERE s.source != 'legacy' AND s.timestamp >= ? AND s.timestamp < ?
        GROUP BY mu.model
        ORDER BY total_tokens DESC
        LIMIT ?
    """, (start_ts, end_ts, limit)).fetchall()

    total_row = conn.execute("""
        SELECT COALESCE(SUM(mu.input_tokens),0) + COALESCE(SUM(mu.output_tokens),0) + COALESCE(SUM(mu.cache_tokens),0) as total
        FROM model_usage mu
        JOIN sessions s ON s.id = mu.session_id
        WHERE s.source != 'legacy' AND s.timestamp >= ? AND s.timestamp < ?
    """, (start_ts, end_ts)).fetchone()
    grand_total = max(1, total_row["total"] or 1)

    grouped_rows = conn.execute(f"""
        SELECT {period_expr} as period, mu.model,
               COALESCE(SUM(mu.input_tokens),0) + COALESCE(SUM(mu.output_tokens),0) + COALESCE(SUM(mu.cache_tokens),0) as tokens,
               COALESCE(SUM(mu.cost),0) as cost
        FROM model_usage mu
        JOIN sessions s ON s.id = mu.session_id
        WHERE s.source != 'legacy' AND s.timestamp >= ? AND s.timestamp < ?
        GROUP BY period, mu.model
        ORDER BY period ASC
    """, (start_ts, end_ts)).fetchall()

    conn.close()

    grouped_by_model: dict[str, dict[str, dict]] = {}
    for row in grouped_rows:
        period_data = grouped_by_model.setdefault(row["period"], {})
        model_data = period_data.setdefault(row["model"], {"tokens": 0, "cost": 0})
        model_data["tokens"] += row["tokens"]
        model_data["cost"] += row["cost"]

    points = []
    for period in points_range:
        period_data = grouped_by_model.get(period, {})
        segments = []
        for model in top_models:
            model_data = period_data.get(model)
            if model_data and model_data["tokens"] > 0:
                segments.append({
                    "model": model,
                    "value": model_data["tokens"],
                    "cost": round(model_data["cost"], 4),
                })
        other_tokens = sum(model_data["tokens"] for model, model_data in period_data.items() if model not in top_set)
        other_cost = sum(model_data["cost"] for model, model_data in period_data.items() if model not in top_set)
        if other_tokens > 0:
            segments.append({"model": "Other", "value": other_tokens, "cost": round(other_cost, 4)})
        points.append({
            "date": _fmt_date_short(period),
            "_iso": period,
            "segments": segments,
        })

    leaderboard = []
    for i, row in enumerate(leaderboard_rows):
        author = _author(row["model"])
        tokens = row["total_tokens"]
        leaderboard.append({
            "model": row["model"],
            "author": author,
            "tokens": tokens,
            "cost": round(row["total_cost"], 2),
            "percent": round(tokens / grand_total * 100, 2),
            "rank": i + 1,
        })

    return {
        "range": range_label,
        "updatedAt": datetime.datetime.utcnow().isoformat() + "Z",
        "usage": {
            "All Users": {range_label: points},
        },
        "leaderboard": leaderboard,
        "topModels": top_models,
    }


@app.get("/api/top-models")
def api_top_models():
    """Top modelos — últimos 12 meses, agrupado por semana (52 semanas).

    - `usage`: 52 puntos semanales. Segmentos = top 20 del período + "Other".
    - `leaderboard`: top 20 del período con % de uso.
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
    return _build_top_models_payload(days=364, bucket="week", limit=20)


@app.get("/api/top-models-30d")
def api_top_models_30d():
    """Top modelos de los últimos 30 días corridos, agrupado por día."""
    return _build_top_models_payload(days=30, bucket="day", limit=20)


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
        SELECT mu.model,
               COALESCE(SUM(mu.cost),0) as total_cost,
               COALESCE(SUM(mu.input_tokens),0) as input_tokens,
               COALESCE(SUM(mu.output_tokens),0) as output_tokens,
               COALESCE(SUM(mu.cache_tokens),0) as cache_tokens
        FROM model_usage mu
        JOIN sessions s ON s.id = mu.session_id
        WHERE s.source != 'legacy'
        GROUP BY mu.model
        HAVING (COALESCE(SUM(mu.input_tokens),0) + COALESCE(SUM(mu.output_tokens),0) + COALESCE(SUM(mu.cache_tokens),0)) >= 1000000
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
        SELECT mu.model,
               COALESCE(SUM(mu.input_tokens),0) as input_tokens,
               COALESCE(SUM(mu.cache_tokens),0) as cache_tokens
        FROM model_usage mu
        JOIN sessions s ON s.id = mu.session_id
        WHERE s.source != 'legacy'
        GROUP BY mu.model
        HAVING COALESCE(SUM(mu.cache_tokens),0) > 0
           AND (COALESCE(SUM(mu.input_tokens),0) + COALESCE(SUM(mu.cache_tokens),0)) >= 1000000
        ORDER BY (CAST(COALESCE(SUM(mu.cache_tokens),0) AS REAL) / (COALESCE(SUM(mu.input_tokens),0) + COALESCE(SUM(mu.cache_tokens),0))) DESC
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
