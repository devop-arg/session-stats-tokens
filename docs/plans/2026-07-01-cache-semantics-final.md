# Plan final: semántica robusta de cache + fix timestamp

**Principio:** no se persiste `billing_mode` en DB. Se deriva de `source` en helpers Python.

---

## Tarea 0 — Backup

```bash
cp session_history.db db_backups/session_history_$(date +%Y%m%d_%H%M%S)_pre-full-fix.db
```

## Tarea 1 — Helpers en stats_common.py

`SOURCE_CACHE_SEMANTICS` dict + `effective_billable_tokens()` + `effective_cache_ratio_input()`

## Tarea 2 — Schema + save_session()

2.1 ALTER TABLE agregar `cache_read_tokens` y `cache_write_tokens` a sessions y model_usage
2.2 save_session() extender firma + derivación + INSERT con MIN(timestamp)

## Tarea 3 — Extractores

3a. stats_common.py: Codex, OpenCode, Hermes, Cursor/Kilo
3b. session-stats script: get_session_stats_sqlite(), merge_model_stats(), Codex capture path

## Tarea 4 — Migración histórica

scripts/migrate-cache-semantics.py

## Tarea 5 — API web

stats-web/main.py: endpoints token-cost, subscription-estimate, cache-ratio, today

## Tarea 6 — CLI

session-stats-period: mostrar billable_tokens

## Tarea 7 — Recaptura y verificación

--capture-all + queries SQL de control + smoke test HTTP
