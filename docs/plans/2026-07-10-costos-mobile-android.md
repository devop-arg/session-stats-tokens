# Comparador de costos mobile Android — Plan de implementación

> **Para Hermes:** ejecutar tarea por tarea, con TDD y verificación después de cada cambio.

**Objetivo:** Convertir `/costos` en una vista práctica para Android (Chrome y Firefox), comparando costo por API contra costo efectivo por suscripción y mostrando el modelo elegido junto con sus cinco vecinos más baratos y cinco más caros.

**Arquitectura:** Mantener el endpoint y la calculadora actuales. Extraer la comparación a funciones JavaScript puras y testeables. El precio manual guardado continúa como fuente de verdad; los Codex sin precio usan `cost_api / 20` solo para comparar y conservan el estado visible `precio pendiente`. La tabla completa sigue en desktop y se reemplaza por un comparador compacto únicamente en mobile.

**Stack:** FastAPI/Jinja2, JavaScript vanilla, CSS responsive, Node.js test runner, Playwright Chromium/Firefox.

---

## Requisitos confirmados

- [x] Plataforma objetivo: Android Chrome y Android Firefox.
- [x] No implementar ajustes específicos para iPhone/Safari.
- [x] Etiquetas principales: `Costo por API` y `Costo efectivo por suscripción`.
- [x] El `cost_sub` manual guardado tiene prioridad.
- [x] Fallback Codex sin precio: `cost_api / 20`, no persistido y visible como `precio pendiente`.
- [x] No agregar filtros temporales ni cambiar la extrapolación de la calculadora.
- [x] Agregar punto de equilibrio.
- [x] Mobile: elegido + 5 inmediatamente más baratos + 5 inmediatamente más caros.
- [x] Desktop: conservar inicialmente la tabla completa.

## Archivos previstos

- Crear: `stats-web/static/costos-logic.js`
- Crear: `stats-web/tests/costos-logic.test.js`
- Modificar: `stats-web/templates/costos.html`
- Modificar: `stats-web/static/app.js`
- Modificar: `stats-web/static/style.css`
- Modificar: `stats-web/templates/base.html`
- Modificar: `README.md`
- Modificar: este plan para registrar avance y verificaciones.

## Tarea 1 — Backup y línea base

- [x] Respaldar los archivos afectados y archivos de precios en un directorio fechado dentro del proyecto.
- [x] Registrar la ruta completa del backup: `/home/capw/scripts/session-stats/model_backups/costos-mobile-android-2026-07-10_173937_-0300`.
- [x] Verificar `/healthz`, `/costos` y `/api/subscription-estimate` antes de modificar.
- [x] Registrar cambios preexistentes del working tree para no sobrescribirlos.

## Tarea 2 — Lógica pura del comparador (TDD)

### RED

- [x] Crear pruebas para prioridad de precio manual.
- [x] Crear prueba para fallback Codex `cost_api / 20` con `precio pendiente`.
- [x] Crear prueba para excluir modelos sin precio ni fallback.
- [x] Crear prueba para obtener cinco vecinos inmediatamente más baratos y cinco más caros.
- [x] Crear pruebas de bordes cuando existen menos de cinco vecinos.
- [x] Ejecutar `node --test stats-web/tests/costos-logic.test.js` y verificar fallo por implementación ausente.

### GREEN

- [x] Implementar `getComparableSubscriptionCost()`.
- [x] Implementar `getCostNeighbors()`.
- [x] Ejecutar las pruebas y verificar que pasen.

## Tarea 3 — Punto de equilibrio (TDD)

### RED

- [x] Probar cálculo de tokens de equilibrio usando el costo semanal del plan y el costo API por millón.
- [x] Probar porcentaje de equilibrio respecto del volumen estimado al 100%.
- [x] Probar entradas cero o inválidas.
- [x] Ejecutar y verificar los fallos esperados.

### GREEN

- [x] Implementar `calculateBreakEven()`.
- [x] Ejecutar las pruebas y verificar que pasen.

## Tarea 4 — Integración del comparador mobile

- [ ] Agregar panel del modelo elegido con costo API, costo efectivo por suscripción, diferencia, multiplicador y punto de equilibrio.
- [ ] Agregar lista de cinco más baratos.
- [ ] Destacar el modelo elegido.
- [ ] Agregar lista de cinco más caros.
- [ ] Marcar los fallback con `precio pendiente`.
- [ ] Recalcular al cambiar el modelo de referencia, precio manual o datos de la calculadora.
- [ ] Mantener guardado explícito mediante el botón `Guardar`.
- [ ] Ocultar tabla completa y controles de ordenamiento solo en mobile.
- [ ] Mantener comparador oculto y tabla intacta en desktop.

## Tarea 5 — CSS Android mobile

- [ ] Diseñar filas compactas para 360, 390 y 430 px.
- [ ] Mantener targets táctiles compatibles con Chrome/Firefox Android.
- [ ] Evitar scroll horizontal.
- [ ] Evitar reglas específicas de Safari/iOS.
- [ ] Preservar los cambios responsive preexistentes del working tree.

## Tarea 6 — Verificación

- [ ] Ejecutar `node --test stats-web/tests/costos-logic.test.js`.
- [ ] Verificar sintaxis JavaScript.
- [ ] Verificar endpoints y healthcheck.
- [ ] Renderizar 360/390/430 px con Chromium usando user-agent Android Chrome.
- [ ] Renderizar 360/390/430 px con Firefox usando user-agent Android Firefox.
- [ ] Confirmar elegido +5/-5, fallback pendiente y punto de equilibrio.
- [ ] Confirmar ausencia de errores de consola.
- [ ] Confirmar ausencia de overflow horizontal.
- [ ] Verificar desktop 1280 px sin regresiones.

## Tarea 7 — Documentación, deploy y cierre

- [ ] Documentar el comparador y fallback en `README.md`.
- [ ] Incrementar cache-bust de assets.
- [ ] Revisar diff completo y preservar cambios ajenos/preexistentes.
- [ ] Reiniciar `session-stats-web.service` solo si la aplicación no recarga los archivos o si cambia código Python.
- [ ] Verificar nuevamente `/healthz`, `/costos`, API y logs después del deploy.
- [ ] Commit atómico y push al remoto privado; sincronizar público únicamente sin datos privados.
- [ ] Conservar el backup hasta autorización explícita para eliminarlo.

## Criterios de aceptación

1. En Android Chrome y Firefox, `/costos` no muestra la tabla de 36 cards.
2. El modelo seleccionado aparece entre cinco costos inferiores y cinco superiores.
3. Un precio manual siempre reemplaza al fallback.
4. Un Codex sin precio usa `cost_api / 20` para comparar, pero muestra `precio pendiente` y no lo persiste.
5. El punto de equilibrio muestra volumen y porcentaje de la capacidad estimada.
6. No hay overflow horizontal ni errores de consola en 360–430 px.
7. Desktop conserva la tabla completa y su ordenamiento.
8. Todas las pruebas automatizadas pasan.
