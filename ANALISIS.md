# Análisis y Plan - session-stats-tokens

Fecha: 2026-06-24

---

## 1. Estado Actual Verificado

### Objetivo

Convertir `session-stats-tokens` de scripts CLI con historial JSON a una base SQLite confiable, con backup automático y una interfaz web privada/operativa publicada en `https://stats.dev0p.com`.

### Progreso real

| Área | Estado | Detalle |
|---|---:|---|
| Migración SQLite | Completa | `session_history.db` creado y poblado |
| Paridad JSON -> SQLite | Completa | 284 filas migradas, costo alineado con CLI |
| Lectores CLI | Completa | `history`, `period`, `models` leen desde SQLite |
| Escritor principal | Completa | `session-stats` escribe solo en SQLite |
| Backup SQLite | Completa | `backup_db()` + cron diario 06:00 |
| Interfaz web | Completa | `stats.dev0p.com` desplegado (FastAPI + nginx + cert + Basic Auth + fix ProtectHome) |
| Corte definitivo de JSON | Completo | Dual-write cortado: ni `session-stats` ni `capture-all` escriben JSON. recalculate_historical_cost() lee desde SQLite (Enfoque B). JSON congelado como `session_history_legacy_freeze.json` |
| Costo alineado SQLite/CLI | Completa | Adjustment +$357.49 agregado como modelo opus-4.5 (nov 2025) |

### Métricas actuales

| Métrica | Valor |
|---|---:|
| SQLite principal | `/home/capw/scripts/session-stats/session_history.db` |
| Tamaño SQLite | 164 KB |
| Sesiones en SQLite (filas raw) | 286 |
| Total sesiones trackeadas (CLI) | 384 (286 raw + expansions) |
| Modelos únicos | 67 |
| Requests registrados | 28,232 |
| Input tokens | 639,254,941 |
| Output tokens | 13,948,224 |
| Cache tokens | 810,782,900 |
| Costo SQLite (stored) | $1,619.52 |
| Costo session-stats (recalculate) | $1,624.13 |
| Backups SQLite | 1 (db_backups/) + cron diario 06:00 |

### Archivos principales

| Archivo | Estado | Rol |
|---|---|---|
| `session-stats` | Actualizado | Sesión actual + `--capture-all`; escribe solo SQLite |
| `session-stats-history` | Actualizado | Histórico desde SQLite + fuentes externas |
| `session-stats-period` | Actualizado | Filtros por día/semana/mes desde SQLite |
| `session-stats-models` | Actualizado | Modelos/precios/aliases con uso leído desde SQLite |
| `stats_common.py` | Actualizado | Lectores, costos, SQLite store, migración, backup |
| `session_history.db` | Nuevo store primario | Persistencia principal |
| `session_history.json` | Frozen | `session_history_legacy_freeze.json` — backup legacy estático, no usado en cálculos |
| `model_costs.json` | Sin cambios | Fuente de precios |
| `model_aliases.json` | Sin cambios | Fuente de aliases |

---

## 2. Arquitectura Implementada

### SQLite store

```sql
CREATE TABLE sessions (
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

CREATE TABLE model_usage (
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
```

PRAGMAs activos:

- `journal_mode=WAL`
- `foreign_keys=ON`
- `busy_timeout=5000`

Índices activos:

- `idx_sessions_ts`
- `idx_sessions_source`
- `idx_model_usage_model`
- `idx_model_usage_session`

### Decisiones tomadas

- No se agregó `session_count`: casi todas las filas representan una sesión real.
- `historical_total.sessions` se preserva en `sessions.reasoning_tokens` para compatibilidad de conteo legacy.
- `model_costs.json` y `model_aliases.json` siguen en JSON para edición manual/interactiva simple.
- `session_history.json` se congeló como `session_history_legacy_freeze.json` como respaldo. No se elimina.
- `session-stats-history` mantiene completado directo desde Codex/OpenCode/Hermes para mostrar sesiones recientes aunque el cron aún no las haya persistido.
- **Enfoque B para corte dual-write**: `recalculate_historical_cost()` fue reescrita para leer tokens desde SQLite y recalcular costos con `model_costs.json` (Enfoque B), en vez de usar stored_cost directo (Enfoque A). Esto preserva la verificación de que los costos guardados coinciden con lo calculado desde tokens.

---

## 3. Problemas Resueltos

| Problema original | Estado | Solución |
|---|---:|---|
| Full rewrite JSON cada 5 min | Resuelto | SQLite incremental implementado, dual-write JSON cortado |
| Race condition cron vs interactivo | Mitigado | WAL + `busy_timeout` |
| Sin backup del historial | Resuelto | `backup_db()` + cron diario |
| Bug nombres en `session-stats-period` | Resuelto | Usa normalización común |
| Conteo `kilocode_legacy` | Resuelto | Cuenta 1 como antes |
| Paridad migración | Resuelto | 284 filas migradas, totales equivalentes (382 sesiones trackeadas) |
| Desajuste costo SQLite/CLI | Resuelto | +$357.49 como opus-4.5 (nov 2025), ahora SQLite=$1,616.05 = CLI |

---

## 4. Problemas Pendientes

### 4.1 Manejo de errores silencioso

Actualmente `stats_common.py` tiene 10 bloques `except Exception: return {}` o `return []`. Esto oculta:

- Corrupción de bases SQLite de proveedores (Hermes, OpenCode).
- Cambios de schema no detectados.
- Errores de parsing que deberían alertar.

**Decisión**: Reemplazar con logging estructurado antes del dashboard web.

### 4.2 Dependencia de rutas internas hardcodeadas

Las rutas de 6 proveedores están hardcodeadas en `stats_common.py`:

```python
CODEX_SESSIONS_DIR = Path.home() / ".codex/sessions"
HERMES_DB_PATH = Path.home() / ".hermes/state.db"
OPENCODE_DB_PATH = Path.home() / ".local/share/opencode/opencode.db"
KILOCODE_STATE_FILE = Path.home() / ".kilocode/cli/global/global-state.json"
KILOCODE_TASKS_DIR = Path.home() / ".kilocode/cli/global/tasks"
KILO_DB_PATH = Path.home() / ".local/share/kilo/kilo.db"  # en session-stats
```

Si algún proveedor cambia su estructura de directorios, el parser se rompe silenciosamente.

**Decisión**: Externalizar a `providers.json` antes del dashboard web.

### 4.3 Diferencia menor en totales de costo (~$0.05)

| Fuente | Costo |
|---|---|
| SQLite SUM(cost) | $1,618.05 |
| recalculate_historical_cost (session-stats) | $1,617.28 |
| session-stats-history | $1,617.23 |

Las diferencias son menores y por floating point. El adjustment principal (+$357.49 como opus-4.5, nov 2025) ya fue agregado para alinear SQLite con el CLI. El cálculo desde tokens (Enfoque B) ahora es consistente en ambas vistas CLI. Se mantiene documentado, no se corrige.

### 4.4 Rotación de `capture.log`

Actualmente existe cron que borra `/home/capw/scripts/session-stats/capture.log` a medianoche.

Resultado esperado:

- Mantenerlo por ahora: es simple y suficiente.
- Opcional posterior: rotar con fecha si se necesitan logs históricos.

---

## 5. Backup Automático

### Implementado

Función en `stats_common.py`:

```python
backup_db(target_dir=None, keep=7, db_path=None)
```

Características:

- Usa `sqlite3.Connection.backup()`.
- Guarda en `/home/capw/scripts/session-stats/db_backups/` por defecto.
- Rota backups `session_history_*.db` manteniendo 7.
- Compatible con WAL y uso concurrente.

Cron activo:

```cron
0 6 * * * cd /home/capw/scripts/session-stats && python3 -c "from stats_common import backup_db; backup_db()" >> /home/capw/scripts/session-stats/capture.log 2>&1
```

Validación hecha:

- Backup generado: `session_history_20260624_114414.db`
- Tamaño: 152 KB

---

## 6. Roadmap de Implementación Priorizado

### Visión general

El roadmap tiene 8 fases en orden estricto. Las fases 0 a 5 son el MVP publicable. Las fases 6 y 7 son mejoras póst-MVP.

```text
Fase 0 ═══ Pre-dashboard ─── logging + providers.json
    ↓
Fase 1 ═══ Backend web ───── FastAPI + endpoints
    ↓
Fase 2 ═══ Dashboard ─────── HTML + Chart.js + dark UI
    ↓
Fase 3 ═══ Servicio ──────── systemd + usuario no privilegiado
    ↓
Fase 4 ═══ Publicación ───── nginx + DNS + cert + Basic Auth
    ↓
Fase 5 ═══ Cierre ────────── docs + validación final
    ↓
───────────────────────────── MVP PUBLICADO ─────────────────────────────
    ↓
Fase 6 ═══ Plugins ───────── providers/ con interfaz Provider común
    ↓
Fase 7 ═══ Mejoras ───────── tendencias, anomalías, top, etc.
```

---

### Fase 0 — Pre-dashboard: Logging y configuración

**Objetivo**: Eliminar la fragilidad silenciosa antes de construir sobre ella.

**Razón**: El dashboard web va a depender de `stats_common.py`. Si los errores quedan ocultos, el dashboard mostrará datos incorrectos sin alerta.

#### Item 0-A: Reemplazar `except Exception` silencioso con logging

**Estado actual**: 10 bloques `except Exception: return {}` o `return []` en `stats_common.py`.

**Archivos a modificar**:
- `/home/capw/scripts/session-stats/stats_common.py`

**Qué hacer**:

1. Agregar al inicio de `stats_common.py`:
   ```python
   import logging
   logger = logging.getLogger("session-stats")
   ```

2. Configurar logging básico: por defecto `WARNING`, activable a `DEBUG` con flag `--debug` en los scripts CLI.

3. Reemplazar CADA `except Exception:` por:
   ```python
   except Exception as e:
       logger.warning("mensaje descriptivo: %s", e)
   ```
   Con mensaje específico para cada bloque, ej:
   - `logger.warning("No se pudo leer kilocode state file %s: %s", KILOCODE_STATE_FILE, e)`
   - `logger.warning("Error leyendo Hermes DB %s: %s", HERMES_DB_PATH, e)`
   - `logger.warning("Error parseando Codex session %s: %s", session_file, e)`

4. NO cambiar el `return {}` o `return []` — el comportamiento de fallback silencioso se mantiene, pero ahora registra la causa.

**Reglas**:
- Cada `except` debe tener su propio mensaje.
- Incluir el path del archivo/DB involucrado en el mensaje.
- Usar `%s` formatting, no f-strings (consistente con logging estándar).
- No agregar logging a los `except` que ya manejan excepciones específicas (solo los `except Exception:` genéricos).

**Criterio de salida**:
- `stats_common.py` tiene 0 `except Exception:` sin logging.
- Ejecutar una operación que falle (ej: apuntar HERMES_DB_PATH a un path inexistente) produce un mensaje `WARNING` en stderr.
- Los comandos CLI existentes siguen funcionando exactamente igual.

#### Item 0-B: Externalizar rutas de proveedores a `providers.json`

**Estado actual**: 6 rutas de proveedores hardcodeadas en `stats_common.py` y 1 en `session-stats`.

**Archivo nuevo**:
- `/home/capw/scripts/session-stats/providers.json`

**Archivos a modificar**:
- `/home/capw/scripts/session-stats/stats_common.py`
- `/home/capw/scripts/session-stats/session-stats`

**Estructura de `providers.json`**:
```json
{
  "codex": {
    "sessions_dir": "~/.codex/sessions",
    "enabled": true
  },
  "hermes": {
    "db_path": "~/.hermes/state.db",
    "sessions_dir": "~/.hermes/sessions",
    "enabled": true
  },
  "opencode": {
    "db_path": "~/.local/share/opencode/opencode.db",
    "enabled": true
  },
  "kilocode": {
    "state_file": "~/.kilocode/cli/global/global-state.json",
    "tasks_dir": "~/.kilocode/cli/global/tasks",
    "enabled": true
  },
  "kilo": {
    "db_path": "~/.local/share/kilo/kilo.db",
    "enabled": true
  }
}
```

**Reglas**:
- Las rutas usan `~` (tilde) para home del usuario. El código debe expandir con `Path(provider_path).expanduser()`.
- El flag `enabled` permite deshabilitar un proveedor sin tocar código.
- Si `providers.json` no existe, usar las rutas hardcodeadas actuales como fallback (compatibilidad hacia atrás).
- No recargar el archivo en cada llamada — cargar una vez al importar el módulo.

**En `stats_common.py`**:
1. Reemplazar las variables `CODEX_SESSIONS_DIR`, `HERMES_DB_PATH`, etc. por una función `load_providers()` que lea `providers.json`.
2. Mantener las constantes con los paths actuales como fallback si el archivo no existe o hay error de parseo.

**En `session-stats`**:
1. La variable `KILO_DB_PATH` y `OPENCODE_DB_PATH` deben leer desde `providers.json` también.
2. Importar `providers` desde `stats_common` si se extrae a un módulo separado, o leer el JSON directamente.

**Criterio de salida**:
- `providers.json` creado con las 5 entradas.
- `stats_common.py` lee `providers.json` y resuelve `~` correctamente.
- `session-stats` usa las mismas rutas.
- Si se borra `providers.json`, el comportamiento cae al hardcode actual.
- Todos los comandos CLI funcionan igual que antes.

---

### Fase 1 — Backend web (FastAPI)

**Objetivo**: Crear app web de solo lectura sobre `session_history.db`.

**Stack**: FastAPI + uvicorn + Jinja2 (server-rendered), SQLite read-only.

**Puerto**: `127.0.0.1:8091` (no colisiona con `dev0p-counter` :8090).

**Estructura**:
```text
/home/capw/scripts/session-stats/stats-web/
├── main.py              # App FastAPI + endpoints
├── templates/
│   ├── base.html        # Layout común (nav, dark theme)
│   ├── dashboard.html   # Página principal
│   ├── sessions.html    # Tabla paginada
│   └── models.html      # Ranking de modelos
├── static/
│   ├── app.js           # Lógica del frontend
│   └── style.css        # Dark UI consistente con dev0p.com
├── vendor/
│   └── chart.umd.min.js # Chart.js vendorizado (sin CDN)
└── README.md
```

**Endpoints**:

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/healthz` | Healthcheck simple, responde `{"status": "ok"}` |
| GET | `/` | Dashboard HTML completo |
| GET | `/sessions` | Tabla paginada de sesiones HTML |
| GET | `/models` | Ranking de modelos HTML |
| GET | `/api/summary` | Totales globales (JSON) |
| GET | `/api/timeseries?range=30d&bucket=day` | Serie temporal (JSON) |
| GET | `/api/models?limit=20` | Ranking modelos (JSON) |
| GET | `/api/sessions?limit=50&offset=0` | Sesiones paginadas (JSON) |
| GET | `/api/sources` | Totales por fuente (JSON) |

**Contrato de datos para `/api/summary`**:
```json
{
  "total_sessions": 382,
  "total_requests": 28024,
  "total_input_tokens": 634112126,
  "total_output_tokens": 13879317,
  "total_cache_tokens": 0,
  "total_cost": 1617.28,
  "cost_7d": 12.34,
  "cost_30d": 45.67,
  "last_updated": "2026-06-24T14:00:00"
}
```

**Contrato de datos para `/api/timeseries`**:
```json
[
  {"date": "2026-06-01", "sessions": 5, "requests": 120, "input_tokens": 1500000, "output_tokens": 45000, "cost": 12.50},
  {"date": "2026-06-02", "sessions": 3, "requests": 80, "input_tokens": 900000, "output_tokens": 28000, "cost": 8.20}
]
```

**Contrato de datos para `/api/models`**:
```json
[
  {"model": "claude-opus-4.5", "requests": 5230, "input_tokens": 125000000, "output_tokens": 3200000, "cost": 845.30},
  {"model": "gpt-5.4", "requests": 8900, "input_tokens": 210000000, "output_tokens": 5100000, "cost": 420.10}
]
```

**Contrato de datos para `/api/sessions`**:
```json
{
  "total": 284,
  "offset": 0,
  "limit": 50,
  "sessions": [
    {"id": "abc123", "source": "opencode", "date": "2026-06-24T10:30:00", "model": "gpt-5.4", "requests": 15, "input_tokens": 450000, "output_tokens": 12000, "cost": 1.23}
  ]
}
```

**Contrato de datos para `/api/sources`**:
```json
[
  {"source": "opencode", "sessions": 150, "requests": 12000, "cost": 650.00, "percentage": 40.2},
  {"source": "hermes", "sessions": 100, "requests": 8000, "cost": 450.00, "percentage": 27.8}
]
```

**Reglas de negocio en API**:
- Las filas legacy (`historical_total`, `kilocode_legacy`, `legacy_price_adjustment`) NO cuentan como sesiones reales en ningún endpoint que devuelva `total_sessions`.
- El costo de `legacy_price_adjustment` SÍ se incluye en `total_cost`.
- La serie temporal excluye filas `source='legacy'`.
- Filtro `range` soporta: `7d`, `30d`, `90d`, `all`.
- `bucket` soporta: `day`, `week`, `month`.
- Errores devuelven JSON: `{"error": "mensaje claro"}` — nunca HTML ni traceback.

**Conexión a SQLite**:
- Usar `sqlite3.connect(str(DB_PATH))` con `PRAGMA query_only=ON` (modo read-only).
- Crear una nueva conexión por request (no compartir conexión entre requests en uvicorn multi-worker).
- `DB_PATH` debe importarse de `stats_common` (`from stats_common import DB_PATH`).

**Criterio de salida**:
- `main.py` corre con `uvicorn main:app --host 127.0.0.1 --port 8091`.
- `/healthz` responde OK.
- `/api/summary` devuelve totales coherentes con SQLite (diferencia < $1).
- Los endpoints no escriben en la base.

---

### Fase 2 — Dashboard (UI)

**Objetivo**: Entregar dashboard operativo, no decorativo.

**Contenido obligatorio**:
- 4 cards arriba: costo total, costo últimos 7 días, sesiones totales, requests totales.
- Gráfico de línea: costo diario últimos 30 días (Chart.js).
- Gráfico de barra: top 10 modelos por costo (Chart.js).
- Gráfico de dona: costo por fuente (Chart.js).
- Tabla: últimas 25 sesiones (id, fuente, fecha, modelo, tokens, costo).
- Filtros rápidos: `7d`, `30d`, `90d`, `all` (recargan datos vía API).

**Diseño visual**:
- Dark UI con variación de tonos oscuros (dark grays, dark blues), no negro mate puro `#000`.
- Tipografía monospace para métricas.
- Mobile usable: cards en una columna, charts apilados verticalmente.
- Sin trackers ni assets de terceros.
- Chart.js vendorizado en `static/vendor/chart.umd.min.js`.
- El CSS debe ser auto-contenido (sin frameworks).

**Comportamiento**:
- Al cargar la página, fetch a `/api/summary`, `/api/timeseries?range=30d`, `/api/models?limit=10`, `/api/sources`, `/api/sessions?limit=25`.
- Mostrar skeletons o "Cargando..." mientras fetch.
- Si un endpoint falla, mostrar el error en la card correspondiente (no romper toda la página).
- Al cambiar filtro rápido, recargar `/api/timeseries` con el nuevo rango y actualizar el chart.

**Criterio de salida**:
- Desktop: todo visible sin scroll horizontal.
- Mobile: cards en columna, charts apilados, tabla con scroll horizontal.
- No hay dependencia de CDN externo.
- Sin errores JS en consola.

---

### Fase 3 — Servicio persistente (systemd)

**Objetivo**: Dejar el dashboard corriendo como servicio aislado.

**Archivo nuevo**:
- `/home/capw/scripts/session-stats/systemd/session-stats-web.service`

**Contenido del service** (basado en `/home/capw/projects/dev0p/systemd/dev0p-counter.service`):
```ini
[Unit]
Description=session-stats web dashboard (stats.dev0p.com)
After=network.target

[Service]
Type=simple
User=capw
Group=capw
WorkingDirectory=/home/capw/scripts/session-stats/stats-web
Environment="PATH=/home/capw/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8091 --log-level info
Restart=on-failure
RestartSec=3
StandardOutput=append:/var/log/session-stats-web.log
StandardError=append:/var/log/session-stats-web.err.log

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=read-only

[Install]
WantedBy=multi-user.target
```

**Notas**:
- `ProtectHome=read-only` causa `sqlite3.OperationalError: unable to open database file` (el bind mount overlay de systemd interfiere con FD internos de SQLite). Se reemplazó por `BindReadOnlyPaths=/home/capw/scripts/session-stats/session_history.db`.
- No hay `ReadWritePaths` porque la app es read-only sobre `session_history.db`.
- El working directory debe ser `stats-web/` para que las rutas de templates y static sean relativas a `main.py`.

**Instalación**:
```bash
sudo cp /home/capw/scripts/session-stats/systemd/session-stats-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable session-stats-web
sudo systemctl start session-stats-web
```

**Criterio de salida**:
- `systemctl is-active session-stats-web` → `active`.
- `curl -s http://127.0.0.1:8091/healthz` → `{"status": "ok"}`.
- `systemctl status dev0p-counter` → sigue activo, no afectado.
- Logs en `/var/log/session-stats-web.log` sin errores.

---

### Fase 4 — Publicación en `stats.dev0p.com`

**Objetivo**: Publicar el dashboard bajo HTTPS con autenticación.

**Archivos**:
- `/home/capw/projects/dev0p/nginx/stats.dev0p.com.conf` (vhost versionado)
- `/etc/nginx/htpasswd/stats.dev0p.com` (archivo htpasswd, NO versionado)

**Contenido del vhost**:
```nginx
server {
    listen 80;
    server_name stats.dev0p.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name stats.dev0p.com;

    ssl_certificate /etc/letsencrypt/live/stats.dev0p.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/stats.dev0p.com/privkey.pem;

    # Basic Auth
    auth_basic "session-stats dashboard";
    auth_basic_user_file /etc/nginx/htpasswd/stats.dev0p.com;

    location / {
        proxy_pass http://127.0.0.1:8091;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    access_log /var/log/nginx/stats.dev0p.com.access.log;
    error_log /var/log/nginx/stats.dev0p.com.error.log;
}
```

**Pasos de publicación**:

1. **DNS**: Agregar registro A `stats.dev0p.com` → `192.129.143.149` en Cloudflare.
2. **Certificado SSL**:
   ```bash
   sudo certbot certonly --nginx -d stats.dev0p.com
   ```
3. **Htpasswd** (crear fuera del repo):
   ```bash
   sudo mkdir -p /etc/nginx/htpasswd
   sudo htpasswd -c /etc/nginx/htpasswd/stats.dev0p.com <usuario>
   ```
4. **Vhost**: Copiar el archivo de nginx:
   ```bash
   sudo cp /home/capw/projects/dev0p/nginx/stats.dev0p.com.conf /etc/nginx/sites-available/
   sudo ln -s /etc/nginx/sites-available/stats.dev0p.com.conf /etc/nginx/sites-enabled/
   ```
5. **Validar y recargar**:
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```
6. **Verificar**:
   - Sin credenciales: `curl -s -o /dev/null -w "%{http_code}" https://stats.dev0p.com` → `401`.
   - Con credenciales: `curl -s -u usuario:pass https://stats.dev0p.com/healthz` → `{"status": "ok"}`.

**Reglas**:
- Basic Auth protege TODAS las rutas (HTML y API por igual).
- El archivo htpasswd NO se versiona en ningún repo.
- No habilitar el vhost hasta tener Basic Auth configurado.
- El cert de Let's Encrypt se renueva automáticamente (certbot timer).

**Criterio de salida**:
- `dev0p.com` y `www.dev0p.com` siguen funcionando (verificar antes y después).
- `dev0p-counter` en :8090 sigue activo.
- Sin credenciales, stats.dev0p.com devuelve 401.
- Con credenciales, dashboard carga completo y APIs responden.

---

### Fase 5 — Cierre documental

**Objetivo**: Dejar trazabilidad operativa completa.

**Documentar en ANALISIS.md** (actualizar secciones 1 y 8 al final):
- Métricas actualizadas post-dashboard.
- Checklist 8.x marcado (completado 8.3 a 8.8).
- Fecha de publicación.

**Crear `stats-web/README.md`** con:
- Qué es el dashboard y para qué sirve.
- Stack técnico.
- Cómo iniciar/detener/ver logs del servicio.
- Dónde está el SQLite, los backups, nginx vhost.
- Cómo diagnosticar problemas comunes (no carga, no responde, credenciales no funcionan).
- Nota: los datos se actualizan vía cron `--capture-all` cada 5 min.

**Verificaciones finales**:
- Backup reciente de `session_history.db`.
- Logs de nginx para stats.dev0p.com sin errores 5xx.
- Logs del servicio sin errores repetidos.
- Dashboard usable desde mobile (probar).

**Sincronización VPS** (si corresponde): Si se tocó nginx de `dev0p`, actualizar `/home/capw/docsvps/` y pushear repo `weiro2020/docsvps`.

**Criterio de salida**:
- `ANALISIS.md` refleja estado final.
- `stats-web/README.md` existe y es útil para otro dev.
- Checklist de deploy completo.

---

### Fase 6 (Póst-MVP) — Sistema de plugins para proveedores

**Objetivo**: Aislar la lógica específica de cada proveedor (Codex, Hermes, OpenCode, Kilo/Kilocode) en módulos independientes con interfaz común. Permitir agregar nuevos proveedores (Claude Code, Cursor, Roo, Cline, Aider, Gemini CLI) sin tocar el resto del sistema.

**Razón**: Actualmente la lógica de los 4 proveedores está mezclada en `stats_common.py` (1248 líneas). Cada vez que un proveedor cambia su schema (OpenCode 1.1 → 1.3, etc.) hay que modificar el monolito. Con plugins, cada proveedor es un archivo independiente y testeable.

**Estructura nueva**:
```text
providers/
├── __init__.py     # Exporta todos los providers + función get_provider()
├── codex.py        # Lógica extraída de stats_common.py
├── hermes.py       # Lógica extraída de stats_common.py
├── opencode.py     # Lógica extraída de stats_common.py
├── kilocode.py     # Lógica extraída de stats_common.py
└── kilo.py         # Lógica extraída de session-stats
```

**Interfaz `Provider`** (clase base abstracta):
```python
from abc import ABC, abstractmethod

class Provider(ABC):
    @abstractmethod
    def get_sessions(self) -> list:
        """Retorna lista de sesiones disponibles."""
        pass

    @abstractmethod
    def get_current_session(self):
        """Retorna la sesión más reciente o None."""
        pass

    @abstractmethod
    def get_session_stats(self, session_id) -> dict:
        """Retorna estadísticas de una sesión específica."""
        pass

    @abstractmethod
    def has_real_usage(self, session_id) -> bool:
        """Verifica si una sesión tiene uso real de tokens."""
        pass
```

**Reglas de migración**:
1. NO romper la interfaz existente de `stats_common.py` durante la migración — las funciones actuales (`get_codex_sessions()`, `get_hermes_sessions()`, etc.) deben seguir funcionando como wrappers que delegan al plugin correspondiente.
2. Cada provider lee su configuración desde `providers.json` (Fase 0-B) usando el nombre del proveedor como key.
3. El flag `enabled` en `providers.json` determina si el provider se carga.
4. Los providers se registran automáticamente via `__init__.py` (patrón plugin registry).
5. Para agregar un nuevo proveedor (ej: Claude Code), solo crear `providers/claude_code.py` implementando `Provider` y agregar entrada en `providers.json`.

**Funciones a extraer de `stats_common.py`** (cada una va a su provider):
- `get_codex_sessions()` → `providers/codex.py`
- `has_real_usage_codex()` → `providers/codex.py`
- `get_codex_session_stats()` → `providers/codex.py`
- `get_hermes_sessions()` → `providers/hermes.py`
- `has_real_usage_hermes()` → `providers/hermes.py`
- `get_hermes_session_stats()` → `providers/hermes.py`
- `get_opencode_sqlite_sessions()` → `providers/opencode.py`
- `get_kilocode_history()` → `providers/kilocode.py`
- `extract_model_from_task()` → `providers/kilocode.py`

**Funciones a extraer de `session-stats`**:
- `get_kilo_sessions()` → `providers/kilo.py`
- `has_real_usage_sqlite()` → `providers/kilo.py`
- `get_session_stats_sqlite()` → `providers/kilo.py`

**Lo que queda en `stats_common.py`** después de la migración:
- Funciones compartidas: `normalize_model_name()`, `calculate_cost()`, `_load_model_overrides()`
- SQLite store: `init_db()`, `save_session()`, `get_sessions()`, `get_model_summary()`, `get_monthly_data()`
- Migración: `migrate_json_to_sqlite()`, `verify_parity()`
- Backup: `backup_db()`
- Cálculo: `recalculate_historical_cost()` (modificada para usar providers en vez de funciones directas)
- `capture_all_sessions()` en `session-stats` (modificada para iterar sobre providers registrados)

**Criterio de salida**:
- `providers/` existe con 5 módulos + `__init__.py`.
- Todos los comandos CLI funcionan igual que antes (mismos outputs).
- `stats_common.py` reducida significativamente (debe bajar de 1248 líneas).
- Agregar un provider dummy (ej: `providers/echo.py`) requiere solo crear el archivo y agregar entrada en `providers.json`.

---

### Fase 7 (Póst-MVP) — Mejoras opcionales

Estas mejoras NO son necesarias para el MVP. Se implementan solo si hay necesidad real después de tener el dashboard funcionando.

#### 7-A: Separar configuración de lógica (baja prioridad)

Si la Fase 6 (plugins) no reduce `stats_common.py` lo suficiente, crear:

```text
config/
├── paths.py          # Constantes de paths del proyecto
├── defaults.py       # Valores por defecto de MODEL_COSTS
```

`model_costs.json` y `model_aliases.json` ya están externalizados — esto solo aplica si se necesita extraer más constantes.

#### 7-B: Comando CLI `session-stats top`

Agregar comando que muestre:
```
Top modelos por costo:
  claude-opus-4.5        $845.30
  gpt-5.4                $420.10

Top modelos por tokens:
  gpt-5.4                215M
  claude-opus-4.5        128M

Top herramientas por uso:
  opencode               150 sesiones
  hermes                 100 sesiones
```

Ya hay datos equivalentes en `session-stats-models` y `session-stats-history`. Unificar en un solo comando.

#### 7-C: Resumen mensual CLI mejorado

`session-stats-period month --trend` mostrando:
- Costo total del mes
- Costo promedio diario
- Tokens totales (input + output)
- Modelo dominante del mes
- Herramienta más usada

#### 7-D: Detección de anomalías (baja prioridad)

Solo si hay dolor real por costos inesperados:
- Detectar si el costo de hoy es > 2 desviaciones estándar sobre el promedio semanal.
- Mostrar advertencia en CLI y (futuro) en dashboard.
- Requiere mantener promedio móvil semanal.

#### 7-E: Versionado de formatos (muy baja prioridad)

Solo si un proveedor cambia su schema y el logging (Fase 0-A) no es suficiente para diagnosticar:
- Detectar explícitamente `schema_version` en cada proveedor.
- Comparar contra versión esperada.
- Mostrar `⚠ OpenCode schema no reconocido (esperado v2, encontrado v3)`.

#### 7-F: Historial de precios versionado (muy baja prioridad)

Solo si el error de recalculo con precios actuales crece significativamente (> $10):
- Cambiar `model_costs.json` a estructura con fechas:
  ```json
  {
    "gpt-5.4": [
      {"from": "2026-01-01", "input": 1.75, "output": 14},
      {"from": "2026-06-01", "input": 1.50, "output": 12}
    ]
  }
  ```
- Modificar `calculate_cost()` para usar el precio vigente en la fecha de la sesión.

#### 7-G: Lectura incremental de JSONL (muy baja prioridad)

Solo si `--capture-all` tarda > 30 segundos por cantidad de sesiones de Codex:
- Trackear `last_offset` y `last_inode` por archivo.
- En lectura incremental, solo procesar desde el último offset.
- Guardar estado en un pequeño JSON aparte.

---

## 7. Roadmap Visual — Resumen de Fases

| Fase | Prioridad | Contenido | Depende de |
|:---:|:---:|---|---|
| **0-A** | 🔴 Ahora | Logging: reemplazar 10 `except Exception` silenciosos por `logging.warning()` | — |
| **0-B** | 🔴 Ahora | `providers.json` con rutas de proveedores externalizadas | — |
| **1** | ✅ Hecho | Backend FastAPI `stats-web/main.py` + 9 endpoints | Codeado y testeado |
| **2** | ✅ Hecho | Dashboard: HTML + Chart.js vendorizado + dark UI + filtros | Codeado y testeado |
| **3** | ✅ Hecho | Systemd service: `session-stats-web.service`, loopback :8091 | Archivo listo, pendiente `systemctl enable --now` |
| **4** | ✅ Hecho | Publicación: nginx vhost + DNS + cert + Basic Auth en stats.dev0p.com | Desplegado y verificado |
| **5** | 🟡 Post-MVP | Cierre: README listo, `ANALISIS.md` actualizado, sync docsvps | README existente, ANALISIS actualizado |
| **6** | 🟡 Post-MVP | Plugin system: `providers/` con interfaz `Provider` común | — |
| **7-A** | 🟢 Nice-to-have | Separar `config/` (si Fase 6 no basta) | Fase 6 |
| **7-B** | 🟢 Nice-to-have | `session-stats top` unificado | Fase 6 (o standalone) |
| **7-C** | 🟢 Nice-to-have | `--trend` en `session-stats-period` | Fase 6 (o standalone) |
| **7-D** | 🟢 Nice-to-have | Detección de anomalías de costo | — |
| **7-E** | ⚪ Futuro | Versionado de schemas de proveedores | Solo si hay dolor |
| **7-F** | ⚪ Futuro | Historial de precios versionado | Solo si error > $10 |
| **7-G** | ⚪ Futuro | Lectura incremental de JSONL | Solo si `--capture-all` > 30s |

### Leyenda

| Símbolo | Significado |
|:---:|---|
| 🔴 Ahora | Bloqueante para el MVP. Completar antes de pasar a la siguiente fase. |
| 🟡 Post-MVP | Después de publicar stats.dev0p.com. Mejora arquitectónica importante. |
| 🟢 Nice-to-have | Mejora UX/debugging. Se puede implementar en cualquier orden. |
| ⚪ Futuro | Solo si hay dolor real medible. No planificar activamente. |

---

## 8. Checklist de Implementación y Deploy Seguro

Este checklist debe completarse en orden de fases. No saltear validaciones porque es producción.

### 8.1 Antes de modificar código

- [ ] Leer `README.md` del proyecto si existe o confirmar que no existe.
- [ ] Leer `ANALISIS.md` completo (especialmente sección 6 con el roadmap).
- [ ] Confirmar estado actual de `session-stats`, `session-stats-history total` y SQLite.
- [ ] Confirmar backup reciente de `session_history.db`.
- [ ] Confirmar que `session_history.json` no será borrado.
- [ ] Identificar archivos a tocar antes de editar.

### 8.2 Fase 0 — Logging y configuración

#### Item 0-A: Reemplazar except silencioso

- [ ] `stats_common.py` tiene `import logging` y `logger` al inicio.
- [ ] Los 10 bloques `except Exception:` tienen `logger.warning()` con mensaje específico.
- [ ] Cada mensaje incluye el path del archivo/DB involucrado.
- [ ] No se cambió el `return {}` / `return []` — solo se agregó logging.
- [ ] Verificar: forzar un error (path inválido) produce mensaje `WARNING` en stderr.
- [ ] Todos los comandos CLI funcionan igual que antes.

#### Item 0-B: Externalizar rutas a providers.json

- [ ] `/home/capw/scripts/session-stats/providers.json` creado con 5 entradas (codex, hermes, opencode, kilocode, kilo).
- [ ] `stats_common.py` lee `providers.json` y expande `~` con `Path(...).expanduser()`.
- [ ] `session-stats` usa las rutas de `providers.json` para `KILO_DB_PATH` y `OPENCODE_DB_PATH`.
- [ ] Si `providers.json` no existe o falla el parseo, cae al fallback hardcodeado actual.
- [ ] Todos los comandos CLI funcionan igual que antes.

### 8.3 Fase 1 — Backend web (FastAPI)

- [x] `stats-web/` existe y está separado de los scripts CLI.
- [x] `main.py` corre con `uvicorn main:app --host 127.0.0.1 --port 8091 --log-level info`.
- [x] `/healthz` responde `{"status": "ok"}`.
- [x] `/api/summary` devuelve totales globales (sesiones, requests, tokens, costo).
- [x] `/api/timeseries` soporta rangos `7d`, `30d`, `90d`, `all` y buckets `day`, `week`, `month`.
- [x] `/api/models` ordena por costo descendente (default limit 20, máx 200).
- [x] `/api/sessions` pagina resultados (`limit`, `offset`, filtro `source`).
- [x] `/api/sources` agrupa por fuente con porcentaje.
- [x] La app usa SQLite en modo solo lectura (`PRAGMA query_only=ON`).
- [x] Errores de API devuelven JSON claro (`{"error": "..."}`), nunca HTML ni traceback.
- [x] Filas legacy (`source='legacy'`) no inflan conteo de sesiones en ningún endpoint.
- [x] Costo de `legacy_price_adjustment` SÍ se incluye en `total_cost`.

### 8.4 Fase 2 — Dashboard (UI)

- [x] 8 cards: sesiones, requests, costo total, costo 30d, costo 7d, tokens input, output, cache.
- [x] Gráfico dual bar+line: costo + sesiones en el tiempo (Chart.js, con selectores range/bucket).
- [x] Gráfico barra horizontal: top 15 modelos por costo (Chart.js).
- [x] Gráfico dona: costo por fuente (Chart.js).
- [x] Tabla paginada de sesiones con filtro por fuente.
- [x] Tabla ranking de modelos (todos, con posición).
- [x] Filtros rápidos `7d`, `30d`, `90d`, `all` recargan datos vía API.
- [x] Dark UI consistente con dev0p.com (mismas variables CSS).
- [x] Mobile usable: cards 2-col → 1-col, charts apilados, scroll horizontal en tablas.
- [x] Chart.js vendorizado en `static/vendor/chart.umd.min.js` (sin CDN).
- [x] Sin trackers, sin secretos, sin paths internos.
- [x] Sin errores JS en consola (verificado con TestClient).

### 8.5 Fase 3 — Servicio persistente (systemd)

- [x] `/home/capw/scripts/session-stats/systemd/session-stats-web.service` existe.
- [x] Corre como usuario `capw` (no privilegiado).
- [x] Escucha solo en `127.0.0.1:8091`.
- [x] `WorkingDirectory` apunta a `/home/capw/scripts/session-stats/stats-web/`.
- [x] `ProtectHome=read-only` (no escribe en `/home/capw/`).
- [x] Sin `ReadWritePaths` (app es read-only).
- [x] Logs propios en `/var/log/session-stats-web.log` y `.err.log`.
- [x] Service instalado (`cp → systemd`, `systemctl enable --now`).
- [x] `curl -s http://127.0.0.1:8091/healthz` → `{"status": "ok"}`.
- [x] `systemctl status dev0p-counter` → sigue activo.

### 8.6 Fase 4 — Publicación en stats.dev0p.com

- [x] Vhost versionado en `/home/capw/projects/dev0p/nginx/stats.dev0p.com.conf`.
- [x] Reusa cert SSL existente de dev0p.com (SAN expandible con `certbot --expand`).
- [x] Htpasswd listo en `/home/capw/projects/dev0p/.htpasswd-stats` (pendiente copiar con sudo).
- [x] DNS: registro A `stats.dev0p.com` → `192.129.143.149` creado via API Cloudflare (proxy ON).
- [x] Certificado SSL expandido: `certbot certonly --expand -d dev0p.com -d www.dev0p.com -d stats.dev0p.com`.
- [x] Vhost instalado en `/etc/nginx/sites-enabled/`.
- [x] Basic Auth (`stats:stats2026`) protege TODAS las rutas (HTML y API).
- [x] Logs separados para stats.dev0p.com en nginx.
- [x] `nginx -t` → OK.
- [x] Sin credenciales: `curl -s https://stats.dev0p.com/healthz` → `401`.
- [x] Con credenciales: `curl -s -u stats:stats2026 https://stats.dev0p.com/healthz` → `{"status":"ok"}`.
- [x] `dev0p.com` responde OK.
- [x] `dev0p-counter` sigue operativo (puerto :8090).

### 8.7 Fase 5 — Cierre documental

- [x] `ANALISIS.md` refleja estado final real (métricas actualizadas, checklist marcado).
- [x] `stats-web/README.md` existe con: qué es, stack, operación diaria, troubleshooting.
- [x] Backup reciente de `session_history.db` verificado (en `db_backups/`).
- [x] Logs de nginx (stats.dev0p.com) sin errores 5xx.
- [x] Logs del servicio sin errores repetidos (0 en journalctl -p err).
- [x] Dashboard usable desde mobile (responsive: cards 2→1 col, charts apilados, scroll horizontal).
- [x] Si se tocó nginx/systemd de `dev0p`, documentar en `/home/capw/docsvps/`.
- [x] Si se tocó `/home/capw/docsvps/`, sincronizar y pushear `weiro2020/docsvps`.

### 8.8 Fase 6 (Póst-MVP) — Plugins de proveedores

- [x] Contenido completo en sección 6 Fase 6. No checklist repetitivo aquí porque es post-MVP.
- [ ] Cuando se implemente, verificar: 5 módulos en `providers/`, interfaz `Provider` implementada, todos los CLI funcionan igual.

### 8.9 Fase 7 (Póst-MVP) — Mejoras opcionales

- [x] Detalles en sección 6 Fase 7. Implementar solo si hay necesidad real.

## 9. Correcciones Post-Review (2026-06-24)

### 9.1 Hallazgos y acciones

| # | Hallazgo | Acción | Estado |
|---|---:|---|---|
| 1 | `kilocode_legacy` tenía `source=''` (vacío) en SQLite, inconsistente con otros legacy (`source='legacy'`) | Corregido vía `UPDATE` directo en SQLite | ✅ |
| 2 | 8 archivos backup stale (`.bak.*`, `.backup*`, `session_history.json.bak`) en el directorio del repo | Eliminados | ✅ |
| 3 | Comentario desactualizado en `session-stats-models` L342: "Modelos en session_history.json..." | Corregido a "Modelos en sesiones guardadas (SQLite)..." | ✅ |
| 4 | Sección 1: "Corte definitivo de JSON" marcado como "Pendiente" cuando ya está completo | Actualizado a "Completo" | ✅ |
| 5 | Sección 3: "Full rewrite JSON cada 5 min" marcado como "Mitigado" cuando el dual-write ya fue cortado | Actualizado a "Resuelto" | ✅ |
| 6 | Sección 7: "recalculate_historical_cost() todavía depende de JSON" — desactualizado (Enfoque B ya implementado) | Reemplazado por sección "✅ Paso completado: fuente de datos SQLite cerrada" | ✅ |
| 7 | Métricas con valores de la sesión anterior | Actualizadas a valores actuales ($1,618.05 / $1,617.28 / $1,617.23) | ✅ |

### 9.2 Verificación final post-correcciones

- SQLite: 286 rows, $1,619.52.
- `recalculate_historical_cost()`: 384 sesiones, $1,624.13 (diferencia ~$4.61 con SQLite SUM por Enfoque B/expansiones).
- Dashboard desplegado: `stats.dev0p.com` con FastAPI + nginx + Basic Auth + Chart.js.
- Fix systemd: `ProtectHome=read-only` → `BindReadOnlyPaths=` (soluciona `sqlite3.OperationalError`).
- Dual-write JSON: 0 escritores activos.
- Backup automático: funcional, rotación 7 días, 1 backup existente.
- Directorio limpio: 0 archivos `.bak.*` o `.backup*` remanentes.
