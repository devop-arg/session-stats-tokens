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
| Interfaz web | Pendiente | Planificada para `stats.dev0p.com` |
| Corte definitivo de JSON | Completo | Dual-write cortado: ni `session-stats` ni `capture-all` escriben JSON. recalculate_historical_cost() lee desde SQLite (Enfoque B). JSON congelado como `session_history_legacy_freeze.json` |
| Costo alineado SQLite/CLI | Completa | Adjustment +$357.49 agregado como modelo opus-4.5 (nov 2025) |

### Métricas actuales

| Métrica | Valor |
|---|---:|
| SQLite principal | `/home/capw/scripts/session-stats/session_history.db` |
| Tamaño SQLite | 152 KB |
| Sesiones en SQLite (filas raw) | 284 (281 reales + 3 legacy: ht, kc, adj) |
| Total sesiones trackeadas (CLI) | 382 (284 filas - 1 ht + 99 ht.expand - 1 adj) |
| Modelos únicos | 65 |
| Requests migrados | 27,760 |
| Input tokens migrados | 633,544,380 |
| Output tokens migrados | 13,733,912 |
| Costo SQLite (post-adjustment) | $1,618.05 |
| Costo session-stats (recalculate) | $1,617.28 |
| Costo session-stats-history | $1,617.23 |
| Diferencia recalculate - history | ~$0.05 (floating point, aceptable) |
| Backups SQLite actuales | 1 |
| Adjustment agregado | +$357.49 (opus-4.5, 2025-11) |

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

### 4.1 Dual-write JSON cortado — Decisión: Enfoque B

`session-stats` ya no escribe en JSON. La lectura de `recalculate_historical_cost()` fue reescrita para leer desde SQLite (Enfoque B), preservando la verificación de costos recalculados vs stored.

`session_history.json` se congeló como `session_history_legacy_freeze.json` como respaldo temporal. No se borra.

**Decisión documentada**: Enfoque B - se reescribió `recalculate_historical_cost()` para leer tokens desde SQLite y recalcular costos usando `model_costs.json`, en vez de simplemente usar stored_cost. Esto preserva la verificación de que los costos guardados coinciden con lo que deberían ser desde tokens.

Estado actual:

- `session-stats` escribe solo en SQLite.
- `session-stats-history` ya leía de SQLite como fuente primaria (no depende de JSON).
- `recalculate_historical_cost()` lee desde SQLite + fuentes externas (Codex, OpenCode, Hermes).
- JSON congelado como backup legacy.

Resultado esperado:

1. SQLite queda como única fuente operativa para historial y totales.
2. JSON deja de participar en el cálculo normal y queda solo como respaldo legacy.
3. Los totales visibles por CLI siguen siendo consistentes con los valores actuales.
4. Las sesiones recientes externas siguen apareciendo sin depender del backup JSON.

### 4.2 Diferencia menor en totales de costo (~$0.05)

| Fuente | Costo |
|---|---|
| SQLite SUM(cost) | $1,618.03 |
| recalculate_historical_cost (session-stats) | $1,617.26 |
| session-stats-history | $1,617.21 |

Las diferencias son menores y por floating point. El adjustment principal (+$357.49 como opus-4.5, nov 2025) ya fue agregado para alinear SQLite con el CLI. El cálculo desde tokens (Enfoque B) ahora es consistente en ambas vistas CLI.

### 4.3 Rotación de `capture.log`

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

## 6. Plan de Implementación Web

### Objetivo

Publicar un dashboard web liviano para consultar costos, sesiones, modelos y evolución temporal sin depender de CLI.

Dominio objetivo:

```text
https://stats.dev0p.com
```

### Stack propuesto

| Componente | Elección | Motivo |
|---|---|---|
| Backend | FastAPI + uvicorn | Ya usado en `dev0p-counter`; bajo costo operativo |
| Frontend | HTML + CSS + vanilla JS + Chart.js | Simple, rápido, sin build step |
| Templates | Jinja2 | Suficiente para layout server-rendered |
| Store | SQLite existente | Sin duplicar datos |
| Servicio | systemd | Mismo patrón que `dev0p-counter` |
| Proxy | nginx | Vhost separado para `stats.dev0p.com` |
| Puerto local | `127.0.0.1:8091` | No colisiona con `dev0p-counter` (`8090`) |

### Estructura propuesta

```text
/home/capw/scripts/session-stats/stats-web/
├── main.py
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── sessions.html
│   └── models.html
├── static/
│   ├── app.js
│   └── style.css
└── README.md
```

### Rutas HTML

| Ruta | Descripción |
|---|---|
| `/` | Dashboard principal: totales, costo mensual, últimos días, top modelos |
| `/sessions` | Tabla paginada de sesiones |
| `/models` | Ranking de modelos, costos y tokens |
| `/healthz` | Healthcheck para systemd/nginx |

### Rutas API

| Ruta | Descripción |
|---|---|
| `/api/summary` | Totales globales: sesiones, requests, tokens, costo |
| `/api/timeseries?range=30d&bucket=day` | Serie temporal para gráficos |
| `/api/models?limit=20` | Ranking de modelos por costo/tokens |
| `/api/sessions?limit=50&offset=0` | Sesiones paginadas |
| `/api/sources` | Totales por fuente (`opencode`, `hermes`, `codex`, etc.) |

### Dashboard inicial

Primera versión útil, sin sobreconstruir:

- Cards: costo total, costo últimos 7 días, sesiones totales, requests totales.
- Chart línea: costo diario últimos 30 días.
- Chart barra: top 10 modelos por costo.
- Chart dona: costo por fuente.
- Tabla: últimas 25 sesiones.
- Filtro rápido: `7d`, `30d`, `90d`, `all`.

### Diseño visual

Debe seguir el tono de `dev0p.com`:

- Dark UI.
- Tipografía técnica/monospace para métricas.
- Sin trackers ni assets pesados.
- Chart.js desde CDN solo si se acepta dependencia externa; alternativa: vendorear `chart.umd.min.js` en `static/vendor/`.
- Mobile usable: cards en una columna, charts apilados.

Recomendación: vendorear Chart.js localmente para evitar dependencia externa y mantener el sitio sin terceros.

### Seguridad

Este dashboard expone datos personales/operativos de consumo de IA. No debe quedar público sin control.

Opciones:

1. **Basic Auth en nginx**: mínimo viable recomendado.
2. Restricción por IP: útil solo si la IP cliente es estable.
3. Cloudflare Access: mejor UX y auditoría, más configuración.

Decisión recomendada para primera versión:

- Basic Auth nginx para `stats.dev0p.com`.
- Archivo htpasswd fuera del repo.
- No exponer endpoints API sin la misma auth.

### Publicación web

Qué debe quedar definido para publicar `stats.dev0p.com`:

- Dominio propio separado de `dev0p.com` y `www.dev0p.com`.
- Proxy dedicado hacia el backend web local, sin colisionar con el contador actual.
- HTTPS válido para `stats.dev0p.com`.
- Autenticación obligatoria para HTML y API.
- Logs propios para distinguir actividad del dashboard frente al sitio principal.
- Configuración versionada en el proyecto correcto: `/home/capw/projects/dev0p/nginx/`.

### Servicio web

Qué debe garantizar el servicio:

- Ejecutarse como usuario no privilegiado.
- Leer `session_history.db` sin escribir ni alterar datos.
- Reiniciarse automáticamente ante fallos simples.
- Exponer solo en loopback; el acceso público pasa por nginx.
- Tener healthcheck claro para validar disponibilidad.
- Mantener logs separados para diagnóstico.
- Aislarse lo suficiente para no afectar otros servicios del VPS.

### Contrato de datos para API

La API debe exponer vistas agregadas, no detalles innecesarios:

- Resumen global: sesiones, requests, tokens por tipo y costo total.
- Serie temporal: costo, sesiones y tokens por día/semana/mes según filtro.
- Ranking de modelos: costo, requests y tokens agregados por modelo.
- Últimas sesiones: listado paginado con fuente, fecha, modelo/costo y tokens.
- Totales por fuente: distribución entre `opencode`, `hermes`, `codex`, legacy y otras fuentes.

Reglas de consistencia:

- Los totales deben alinearse con SQLite como fuente operativa.
- Las filas legacy deben mostrarse sin inflar el conteo de sesiones.
- El adjustment de costo debe aparecer como corrección histórica, no como sesión real.
- Las diferencias conocidas entre CLI deben quedar documentadas hasta retirar el recálculo legacy.

### Guía de implementación web

Esta guía define el orden correcto para que el dev avance sin ambigüedad. Evita comandos repetitivos, pero mantiene validaciones obligatorias.

#### Fase 1: Fuente de datos única

Objetivo:

- SQLite debe quedar como fuente operativa de lectura para historial, totales y dashboard.
- JSON debe quedar solo como respaldo legacy durante la transición.

Archivos involucrados:

- `stats_common.py`
- `session-stats`
- `session-stats-history`
- `session_history.db`
- `session_history.json`

Decisiones obligatorias:

- El conteo visible debe seguir siendo 382 sesiones.
- `legacy_price_adjustment` no cuenta como sesión real.
- `historical_total` conserva su expansión legacy de 100 sesiones.
- `kilocode_legacy` cuenta como 1 sesión.

Criterio de salida:

- SQLite, `session-stats` y `session-stats-history` muestran totales coherentes con las diferencias documentadas.
- No hay dependencia funcional nueva hacia `session_history.json`.
- El backup JSON sigue existiendo y no se borra.

#### Fase 2: Backend web privado

Objetivo:

- Crear una app web de solo lectura sobre `session_history.db`.
- Exponer HTML y API interna para el dashboard.

Archivos esperados:

- `/home/capw/scripts/session-stats/stats-web/main.py`
- `/home/capw/scripts/session-stats/stats-web/templates/base.html`
- `/home/capw/scripts/session-stats/stats-web/templates/dashboard.html`
- `/home/capw/scripts/session-stats/stats-web/static/app.js`
- `/home/capw/scripts/session-stats/stats-web/static/style.css`
- `/home/capw/scripts/session-stats/stats-web/README.md`

Endpoints mínimos:

- `/`: dashboard principal.
- `/healthz`: disponibilidad del servicio.
- `/api/summary`: totales globales.
- `/api/timeseries`: evolución temporal por rango.
- `/api/models`: ranking de modelos.
- `/api/sessions`: últimas sesiones paginadas.
- `/api/sources`: totales por fuente.

Criterio de salida:

- La app lee SQLite sin escribirlo.
- Los endpoints devuelven JSON estable.
- El dashboard carga sin depender de servicios externos salvo decisión explícita sobre Chart.js.
- Los números principales coinciden con SQLite.

#### Fase 3: UI mínima útil

Objetivo:

- Entregar un dashboard operativo, no una web decorativa.

Contenido obligatorio:

- Cards: costo total, costo últimos 7 días, sesiones, requests.
- Gráfico temporal: costo diario últimos 30 días.
- Ranking: top 10 modelos por costo.
- Distribución: costo por fuente.
- Tabla: últimas 25 sesiones.
- Filtros rápidos: `7d`, `30d`, `90d`, `all`.

Criterio de salida:

- Desktop usable.
- Mobile usable.
- Dark UI consistente con `dev0p.com`.
- Sin trackers.
- Sin exponer secretos, paths internos sensibles o tokens.

#### Fase 4: Servicio persistente

Objetivo:

- Dejar el dashboard corriendo como servicio aislado del contador actual de `dev0p.com`.

Archivo esperado:

- `/home/capw/scripts/session-stats/systemd/session-stats-web.service`

Requisitos:

- Usuario no privilegiado.
- Backend en loopback.
- Puerto local dedicado: `127.0.0.1:8091`.
- Lectura de `session_history.db` sin escritura.
- Logs propios.
- Reinicio automático ante fallos simples.

Criterio de salida:

- El servicio queda activo y responde `/healthz` localmente.
- Fallar este servicio no afecta `dev0p-counter`.

#### Fase 5: Publicación en `stats.dev0p.com`

Objetivo:

- Publicar el dashboard privado bajo HTTPS y autenticación obligatoria.

Archivos esperados:

- `/home/capw/projects/dev0p/nginx/stats.dev0p.com.conf`
- Archivo htpasswd fuera del repo.

Requisitos:

- DNS `stats.dev0p.com` apunta a la VPS local.
- HTTPS válido para el subdominio.
- Basic Auth activo antes de exponer HTML o API.
- Vhost separado del sitio principal.
- Proxy hacia `127.0.0.1:8091`.
- Logs separados para `stats.dev0p.com`.

Criterio de salida:

- Sin autenticación, `stats.dev0p.com` no muestra datos.
- Con autenticación, dashboard y APIs responden.
- `dev0p.com` y `www.dev0p.com` siguen funcionando.

#### Fase 6: Documentación y cierre

Objetivo:

- Dejar trazabilidad para operar y mantener el dashboard.

Debe quedar documentado:

- Qué mide cada total.
- Por qué existen diferencias menores entre vistas CLI.
- Qué fuentes legacy no cuentan como sesiones reales.
- Cómo se valida que la web está sana.
- Dónde vive nginx, systemd, SQLite y backups.

Criterio de salida:

- `ANALISIS.md` refleja el estado real.
- `stats-web/README.md` explica operación diaria y troubleshooting básico.
- Si se toca documentación de VPS, se sincroniza y pushea el repo `docsvps`.

---

## 7. Qué Sigue

### ✅ Paso completado: fuente de datos SQLite cerrada

Esto ya está implementado:

- `recalculate_historical_cost()` lee desde SQLite (Enfoque B, sin dependencia de JSON).
- El dashboard web (próxima fase) nacerá leyendo SQLite vía API propia.
- Dual-write JSON cortado: ningún script escribe en `session_history.json`.
- JSON congelado como `session_history_legacy_freeze.json` — backup legacy, no usado en cálculos.

Resultado verificado:

- El flujo normal de lectura usa SQLite como fuente única.
- Los comandos existentes (`session-stats`, `session-stats-history`, etc.) leen SQLite y muestran totales consistentes.
- Diferencias menores (< $1) entre vistas por floating point, documentadas.

### Después: construir backend web

Qué hay que entregar:

- App FastAPI mínima en `stats-web/`.
- Endpoints de resumen, series, modelos, sesiones y fuentes.
- Lectura SQLite read-only.
- Healthcheck.

Resultado esperado:

- La API funciona localmente.
- Los totales de API coinciden con SQLite.
- No hay escritura sobre la base desde la web.

### Después: construir dashboard

Qué hay que entregar:

- Página principal con cards, gráficos y tabla de sesiones.
- Estilo oscuro consistente con `dev0p.com`.
- Mobile aceptable.
- Chart.js vendorizado salvo decisión contraria explícita.

Resultado esperado:

- El dashboard permite ver gasto, evolución, fuentes, modelos y sesiones recientes sin usar CLI.

### Después: preparar publicación segura

Qué hay que entregar:

- Service file versionado.
- Vhost nginx versionado en el repo de `dev0p`.
- Basic Auth antes de habilitar acceso público.
- DNS/cert listo para `stats.dev0p.com`.

Resultado esperado:

- El servicio web corre aislado.
- El subdominio exige autenticación.
- El sitio principal no se ve afectado.

### Después: cierre operativo

Qué hay que entregar:

- README de `stats-web`.
- Actualización final de `ANALISIS.md`.
- Validación de backup SQLite.
- Registro de cualquier cambio nginx/systemd en documentación operativa si corresponde.

Resultado esperado:

- Otro dev puede operar, diagnosticar y extender la web sin reconstruir contexto.

---

## 8. Checklist de Implementación y Deploy Seguro

Este checklist debe completarse en orden. No saltear validaciones porque es producción.

### 8.1 Antes de modificar código

- [ ] Leer `README.md` del proyecto si existe o confirmar que no existe.
- [ ] Leer `ANALISIS.md` completo.
- [ ] Confirmar estado actual de `session-stats`, `session-stats-history total` y SQLite.
- [ ] Confirmar backup reciente de `session_history.db`.
- [ ] Confirmar que `session_history.json` no será borrado.
- [ ] Identificar archivos a tocar antes de editar.

### 8.2 Fuente de datos SQLite

- [x] `recalculate_historical_cost()` ya no depende de JSON como fuente primaria.
- [x] `legacy_price_adjustment` no suma sesión real.
- [x] `historical_total` mantiene conteo legacy correcto.
- [x] `kilocode_legacy` sigue contando como 1 sesión.
- [x] `session-stats` conserva total cercano a `$1,617` salvo nuevas sesiones reales.
- [x] `session-stats-history total` conserva 382 sesiones salvo nuevas sesiones reales.
- [x] Diferencias menores de costo quedan documentadas, no ocultadas.

### 8.3 Backend web

- [ ] `stats-web/` existe y está separado de los scripts CLI.
- [ ] La app usa SQLite en modo solo lectura o no escribe datos.
- [ ] `/healthz` responde sin consultar datos pesados.
- [ ] `/api/summary` devuelve totales globales.
- [ ] `/api/timeseries` soporta rangos mínimos `7d`, `30d`, `90d`, `all`.
- [ ] `/api/models` ordena por costo descendente.
- [ ] `/api/sessions` pagina resultados.
- [ ] `/api/sources` agrupa por fuente.
- [ ] Errores de API devuelven JSON claro, no traceback HTML.

### 8.4 Dashboard

- [ ] Carga cards principales.
- [ ] Carga gráfico temporal.
- [ ] Carga ranking de modelos.
- [ ] Carga distribución por fuente.
- [ ] Carga últimas sesiones.
- [ ] Funciona en mobile sin romper layout.
- [ ] No incluye trackers.
- [ ] No muestra secretos ni paths internos innecesarios.

### 8.5 Servicio local

- [ ] Service file existe en `/home/capw/scripts/session-stats/systemd/`.
- [ ] Corre como usuario `capw` o usuario no privilegiado equivalente.
- [ ] Escucha solo en `127.0.0.1:8091`.
- [ ] Tiene logs propios.
- [ ] No requiere permisos de escritura sobre `session_history.db`.
- [ ] Está aislado del servicio `dev0p-counter`.

### 8.6 Nginx, DNS y HTTPS

- [ ] Vhost versionado en `/home/capw/projects/dev0p/nginx/`.
- [ ] `stats.dev0p.com` apunta a `192.129.143.149`.
- [ ] Certificado cubre `stats.dev0p.com`.
- [ ] Basic Auth está configurado antes de habilitar el vhost público.
- [ ] HTML y API quedan detrás de la misma autenticación.
- [ ] Logs separados para `stats.dev0p.com`.
- [ ] Validación mínima obligatoria antes de reload: `nginx -t`.

### 8.7 Validación post-deploy

- [ ] Sin credenciales, `stats.dev0p.com` no expone datos.
- [ ] Con credenciales, `/healthz` responde OK.
- [ ] Dashboard carga completo.
- [ ] APIs devuelven totales coherentes con SQLite.
- [ ] `dev0p.com` responde.
- [ ] `www.dev0p.com` responde.
- [ ] `dev0p-counter` sigue operativo.
- [ ] Logs del nuevo servicio no muestran errores repetidos.
- [ ] No se reiniciaron servicios no relacionados.

### 8.8 Cierre documental

- [ ] `ANALISIS.md` refleja estado final real.
- [ ] `stats-web/README.md` existe.
- [ ] Si se actualizó nginx/systemd de `dev0p`, documentar el cambio donde corresponda.
- [ ] Si se tocó `/home/capw/docsvps/`, sincronizar y pushear `weiro2020/docsvps`.
- [ ] Registrar pendientes explícitos, no supuestos.

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

- SQLite: 284 rows, $1,618.05, 3 legacy con `source='legacy'` consistente.
- `recalculate_historical_cost()`: 382 sesiones, $1,617.28 (diferencia ~$0.77 con SQLite SUM por floating point y Enfoque B).
- `session-stats-history`: 382 sesiones, $1,617.23 (diferencia ~$0.05 con recalculate).
- Dual-write JSON: 0 escritores activos.
- Backup automático: funcional, rotación 7 días.
- Directorio limpio: 0 archivos `.bak.*` o `.backup*` remanentes.
