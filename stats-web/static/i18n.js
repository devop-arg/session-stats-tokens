/* session-stats i18n — selector ES/EN client-side.
 * Default: inglés. Elección persistida en localStorage ('ss_lang').
 * Al cambiar idioma se guarda y se recarga la página para que TODOS los
 * componentes dinámicos (charts, leaderboards, tooltips) re-rendericen.
 */
(function () {
  'use strict';

  var DICT = {
    en: {
      'title': 'session-stats \u00b7 LLM usage',
      // Nav
      'nav.dashboard': 'Dashboard',
      'nav.sessions': 'Sessions',
      'nav.models': 'Models',
      'nav.costos': 'Costs',
      'footer.tagline': 'LLM API monitoring',
      'footer.sessions_badge': 'sessions',
      'aria.open_menu': 'Open menu',
      'aria.back_top': 'Back to top',
      // Hero
      'hero.lede': 'LLM usage statistics',
      // Cards
      'card.input': 'Input',
      'card.output': 'Output',
      'card.cache_input': 'Cache input',
      'card.cache_ratio': 'Cache Ratio',
      'card.sessions': 'Sessions',
      'card.requests': 'Requests',
      'card.tokens': 'Tokens',
      'card.cost_total': 'Total Cost',
      // Sections
      'sec.weekly': 'Weekly Statistics',
      'sec.monthly': 'Monthly Statistics',
      'sec.yearly': 'Yearly Statistics',
      // Range tabs
      'range.today': 'Today',
      'range.yesterday': 'Yesterday',
      'range.48h': '48h',
      'range.7d': '7 days',
      'rangelabel.today': 'Today',
      'rangelabel.yesterday': 'Yesterday',
      'rangelabel.48h': 'Last 48h',
      'rangelabel.7d': 'Last 7 days',
      // Leaderboard
      'all_models': 'All models',
      'one_model_selected': ' model selected',
      'n_models_selected': ' models selected',
      'clear_selection': 'Clear selection',
      'aria.leaderboard30': 'Model picker for the last 30 days',
      'aria.leaderboardhist': 'Historical model picker',
      'aria.chart30': 'Stacked model usage chart (30 days)',
      'aria.charthist': 'Stacked model usage chart (12 months)',
      'aria.activity': 'Weekly activity over time',
      // Activity section
      'act.title': 'Activity over time \u2014 weekly evolution of sessions, effective tokens and cost over the last 12 months',
      'act.peak_tokens': 'Peak Week Effective Tokens',
      'act.peak_cost': 'Peak Week Cost',
      'act.peak_sessions': 'Peak Week Sessions',
      'metric.tokens': 'Effective tokens',
      'metric.cost': 'Cost',
      'metric.sessions': 'Sessions',
      'metric.sources': 'Sources',
      // Token cost section
      'tc.title': 'Cost per million tokens \u2014 effective price per model',
      'tc.price_per_1m': 'Price / 1M tokens',
      'tc.eff_tokens': 'Effective tokens',
      'tc.sort_by': 'Sort by:',
      'tc.sort_cost': 'Effective cost',
      'tc.sort_tokens': 'Effective tokens',
      'th.model': 'Model',
      'th.cost_1m': 'Cost / 1M',
      // Cache section
      'cache.title': 'Cache share \u2014 models with cache',
      'cache.ratio_models': 'Ratio across cached models',
      'cache.cached': 'Cached tokens',
      'cache.uncached': 'Uncached tokens',
      'cache.measured_input': 'Measured input',
      // Sessions page
      'sess.title_strong': 'Sessions.',
      'sess.title_rest': ' Paginated list of all recorded sessions.',
      'sess.all_sources': 'All sources',
      'sess.page': 'Page',
      'sess.sessions_word': 'sessions',
      'sess.th_date': 'Date',
      'sess.th_source': 'Source',
      'sess.th_requests': 'Requests',
      'sess.th_input': 'Input',
      'sess.th_output': 'Output',
      'sess.th_cache_input': 'Cache input',
      'sess.th_raw_input': 'Raw input',
      'sess.th_effective': 'Effective total',
      'sess.th_cost': 'Cost',
      'sess.tip_input': 'Input excluding cache read',
      'sess.tip_cache': 'Cache read',
      'sess.tip_raw': 'Source-reported input; for Codex includes cache read',
      'sess.tip_effective': 'Effective tokens per source semantics',
      'common.loading': 'Loading...',
      'sess.next': 'Next \u2192',
      // Models page
      'mod.title_strong': 'Models.',
      'mod.title_rest': ' Model ranking by cost. Editable prices.',
      'mod.recalc': 'Recalculate historical costs',
      'mod.sort_label': 'Sort:',
      'mod.sort_cost': 'Cost',
      'mod.sort_tokens': 'Effective tokens',
      'mod.sort_requests': 'Requests',
      'mod.sort_name': 'Model',
      // Costos page
      'cos.title_strong': 'Costs with subscriptions.',
      'cos.title_rest': ' Real cost per 1M tokens estimate vs cost if a paid subscription applied.',
      'cos.ocg_explain': '<strong>OpenCode Go:</strong> $10/mo \u2192 $60 credit (6\u00d7). Covers deepseek, glm, mimo, minimax, nex-agi, nemotron.',
      'cos.codex_explain': '<strong>Codex:</strong> $20/mo \u2192 reduced pricing on GPT models. Pick the reference model below.',
      'cos.calc_codex': 'Codex Calculator',
      'cos.calc_ocg': 'OpenCode Go Calculator',
      'cos.plan_params': 'Plan parameters',
      'cos.sub_cost': 'Subscription cost ($/mo)',
      'cos.ref_model': 'Reference model',
      'cos.loading_opt': '\u2014 Loading \u2014',
      'cos.eff_cost': 'Effective cost ($/1M)',
      'cos.save': 'Save',
      'cos.saved_server': '\u2713 saved on server',
      'cos.weekly_usage': 'Estimated weekly usage',
      'cos.pct_quota': '% of weekly quota used',
      'cos.in_used': 'Input tokens used (M)',
      'cos.out_used': 'Output tokens used (M)',
      'cos.cache_used': 'Cache tokens used (M)',
      'cos.res_ref_model': 'Reference model',
      'cos.res_ref_entered': 'Entered effective cost',
      'cos.res_api_cost': 'API cost',
      'cos.res_api_week': 'Direct API cost (no sub) weekly',
      'cos.res_savings': 'Savings vs direct API',
      'cos.res_week_tokens': 'Estimated tokens/week (100%)',
      'cos.res_eff_sub': 'Effective cost with subscription',
      'cos.credit': 'Credit ($)',
      'cos.mobile_eyebrow': 'Comparison by effective cost',
      'cos.mobile_title': 'Selected model and nearby costs',
      'cos.restore': '\u21bb Restore',
      'cos.calculating': 'Computing comparison\u2026',
      'cos.cheaper5': '5 cheapest',
      'cos.pricier5': '5 most expensive',
      'cos.sort_label': 'Sort:',
      'cos.sort_cost_sub': 'Cost with sub',
      'cos.savings': 'Savings',
      'cos.tokens': 'Tokens',
      'cos.cost_api': 'API cost',
      'cos.th_total_tokens': 'Total tokens',
      'cos.th_api_1m': 'Cost/1M (real API)',
      'cos.plan': 'Plan',
      'cos.th_sub_1m': 'Cost/1M (with sub)',
      'cos.vs_ref_sub_prefix': 'vs ',
      'cos.vs_ref_sub_suffix': ' sub',
      // Login
      'login.restricted': 'Restricted access',
      'login.subtitle': 'Enter your credentials to see the dashboard.',
      'login.user': 'Username',
      'login.password': 'Password',
      'login.enter': 'Sign in',
      'login.note': 'The session lasts 90 days.',
      'login.bad_credentials': 'Incorrect credentials',
      // Dynamic (app.js)
      'dyn.invalid_number': 'Invalid number',
      'dyn.saved_pending': '\u2713 saved (recalc pending)',
      'dyn.more_cheap': '\u00d7 cheaper',
      'dyn.more_expensive': '\u00d7 pricier',
      'dyn.no_comparable': 'No comparable models.',
      'dyn.no_comparable_selected': 'The selected model has no comparable cost.',
      'dyn.api_cost_metric': 'API cost',
      'dyn.eff_sub_metric': 'Effective cost with subscription',
      'dyn.select_ref_first': 'Pick a reference model first.',
      'dyn.lbl_rank': '#',
      'dyn.lbl_model': 'Model',
      'dyn.lbl_requests': 'Requests',
      'dyn.lbl_input_nocache': 'Input w/o cache',
      'dyn.lbl_output': 'Output',
      'dyn.lbl_cache_input': 'Cache input',
      'dyn.lbl_cache_pct': 'Cache %',
      'dyn.lbl_total': 'Total',
      'dyn.lbl_cost': 'Cost',
      'dyn.lbl_pct': '%',
      'dyn.tooltip_total': ' total  ·  ',
      'dyn.sessions_word': ' sessions',
      'dyn.percent_more': '% more',
      'dyn.percent_less': '% less · ',
      'dyn.price_pending': 'price pending',
      'dyn.reference': 'reference',
      'dyn.difference': 'Difference',
      'dyn.break_even': 'Break-even point',
      'dyn.models_word': ' models',
      'dyn.save_error': 'Save error: '
    },
    es: {
      'title': 'session-stats \u00b7 consumo LLM',
      'nav.dashboard': 'Dashboard',
      'nav.sessions': 'Sesiones',
      'nav.models': 'Modelos',
      'nav.costos': 'Costos',
      'footer.tagline': 'monitoreo de APIs LLM',
      'footer.sessions_badge': 'sesiones',
      'aria.open_menu': 'Abrir men\u00fa',
      'aria.back_top': 'Volver arriba',
      'hero.lede': 'Estad\u00edsticas de uso LLM',
      'card.input': 'Input',
      'card.output': 'Output',
      'card.cache_input': 'Cache input',
      'card.cache_ratio': 'Cache Ratio',
      'card.sessions': 'Sesiones',
      'card.requests': 'Requests',
      'card.tokens': 'Tokens',
      'card.cost_total': 'Costo Total',
      'sec.weekly': 'Estad\u00edsticas Semanales',
      'sec.monthly': 'Estad\u00edsticas Mensuales',
      'sec.yearly': 'Estad\u00edsticas Anuales',
      'range.today': 'Hoy',
      'range.yesterday': 'Ayer',
      'range.48h': '48hs',
      'range.7d': '7 d\u00edas',
      'rangelabel.today': 'Hoy',
      'rangelabel.yesterday': 'Ayer',
      'rangelabel.48h': '\u00daltimas 48hs',
      'rangelabel.7d': '\u00daltimos 7 d\u00edas',
      'all_models': 'Todos los modelos',
      'one_model_selected': ' modelo seleccionado',
      'n_models_selected': ' modelos seleccionados',
      'clear_selection': 'Limpiar selecci\u00f3n',
      'aria.leaderboard30': 'Selector de modelos de los \u00faltimos 30 d\u00edas',
      'aria.leaderboardhist': 'Selector hist\u00f3rico de modelos',
      'aria.chart30': 'Gr\u00e1fico apilado de uso de modelos (30 d\u00edas)',
      'aria.charthist': 'Gr\u00e1fico apilado de uso de modelos (12 meses)',
      'aria.activity': 'Actividad temporal semanal',
      'act.title': 'Actividad temporal \u2014 evoluci\u00f3n semanal de sesiones, tokens efectivos y costo en los \u00faltimos 12 meses',
      'act.peak_tokens': 'Semana Pico Tokens efectivos',
      'act.peak_cost': 'Semana Pico Costo',
      'act.peak_sessions': 'Semana Pico Sesiones',
      'metric.tokens': 'Tokens efectivos',
      'metric.cost': 'Costo',
      'metric.sessions': 'Sesiones',
      'metric.sources': 'Fuentes',
      'tc.title': 'Costo por mill\u00f3n de tokens \u2014 precio efectivo por modelo',
      'tc.price_per_1m': 'Precio / 1M tokens',
      'tc.eff_tokens': 'Tokens efectivos',
      'tc.sort_by': 'Ordenar por:',
      'tc.sort_cost': 'Costo efectivo',
      'tc.sort_tokens': 'Tokens efectivos',
      'th.model': 'Modelo',
      'th.cost_1m': 'Costo / 1M',
      'cache.title': 'Proporci\u00f3n de cache \u2014 modelos con cache',
      'cache.ratio_models': 'Ratio en modelos con cache',
      'cache.cached': 'Tokens cacheados',
      'cache.uncached': 'Tokens sin cache',
      'cache.measured_input': 'Input medido',
      'sess.title_strong': 'Sesiones.',
      'sess.title_rest': ' Listado paginado de todas las sesiones registradas.',
      'sess.all_sources': 'Todas las fuentes',
      'sess.page': 'P\u00e1gina',
      'sess.sessions_word': 'sesiones',
      'sess.th_date': 'Fecha',
      'sess.th_source': 'Fuente',
      'sess.th_requests': 'Requests',
      'sess.th_input': 'Input',
      'sess.th_output': 'Output',
      'sess.th_cache_input': 'Cache input',
      'sess.th_raw_input': 'Input crudo',
      'sess.th_effective': 'Total efectivo',
      'sess.th_cost': 'Costo',
      'sess.tip_input': 'Input sin cache read',
      'sess.tip_cache': 'Cache read',
      'sess.tip_raw': 'Input reportado por la fuente; en Codex incluye cache read',
      'sess.tip_effective': 'Tokens efectivos seg\u00fan la sem\u00e1ntica de la fuente',
      'common.loading': 'Cargando...',
      'sess.next': 'Siguiente \u2192',
      'mod.title_strong': 'Modelos.',
      'mod.title_rest': ' Ranking de modelos por costo. Precios editables.',
      'mod.recalc': 'Recalcular costos hist\u00f3ricos',
      'mod.sort_label': 'Ordenar:',
      'mod.sort_cost': 'Costo',
      'mod.sort_tokens': 'Tokens efectivos',
      'mod.sort_requests': 'Requests',
      'mod.sort_name': 'Modelo',
      'cos.title_strong': 'Costos con suscripciones.',
      'cos.title_rest': ' Estimaci\u00f3n de costo real /1M tokens vs costo si aplicara una suscripci\u00f3n paga.',
      'cos.ocg_explain': '<strong>OpenCode Go:</strong> $10/mes \u2192 $60 cr\u00e9dito (6\u00d7). Cubre deepseek, glm, mimo, minimax, nex-agi, nemotron.',
      'cos.codex_explain': '<strong>Codex:</strong> $20/mes \u2192 precios reducidos en modelos GPT. Seleccion\u00e1 el modelo de referencia abajo.',
      'cos.calc_codex': 'Calculadora Codex',
      'cos.calc_ocg': 'Calculadora OpenCode Go',
      'cos.plan_params': 'Par\u00e1metros del plan',
      'cos.sub_cost': 'Costo suscripci\u00f3n ($/mes)',
      'cos.ref_model': 'Modelo de referencia',
      'cos.loading_opt': '\u2014 Cargando \u2014',
      'cos.eff_cost': 'Costo efectivo ($/1M)',
      'cos.save': 'Guardar',
      'cos.saved_server': '\u2713 guardado en servidor',
      'cos.weekly_usage': 'Uso semanal estimado',
      'cos.pct_quota': '% del cupo semanal usado',
      'cos.in_used': 'Input tokens usados (M)',
      'cos.out_used': 'Output tokens usados (M)',
      'cos.cache_used': 'Cache tokens usados (M)',
      'cos.res_ref_model': 'Modelo de referencia',
      'cos.res_ref_entered': 'Costo efectivo ingresado',
      'cos.res_api_cost': 'Costo por API',
      'cos.res_api_week': 'Costo API directo (sin sub) semanal',
      'cos.res_savings': 'Ahorro vs API directa',
      'cos.res_week_tokens': 'Tokens/semana estimados (100%)',
      'cos.res_eff_sub': 'Costo efectivo por suscripci\u00f3n',
      'cos.credit': 'Cr\u00e9dito ($)',
      'cos.mobile_eyebrow': 'Comparaci\u00f3n por costo efectivo',
      'cos.mobile_title': 'Modelo elegido y costos cercanos',
      'cos.restore': '\u21bb Restaurar',
      'cos.calculating': 'Calculando comparaci\u00f3n\u2026',
      'cos.cheaper5': '5 m\u00e1s baratos',
      'cos.pricier5': '5 m\u00e1s caros',
      'cos.sort_label': 'Ordenar:',
      'cos.sort_cost_sub': 'Costo con sub',
      'cos.savings': 'Ahorro',
      'cos.tokens': 'Tokens',
      'cos.cost_api': 'Costo API',
      'cos.th_total_tokens': 'Tokens totales',
      'cos.th_api_1m': 'Costo/1M (API real)',
      'cos.plan': 'Plan',
      'cos.th_sub_1m': 'Costo/1M (con sub)',
      'cos.vs_ref_sub_prefix': 'vs ',
      'cos.vs_ref_sub_suffix': ' sub',
      'login.restricted': 'Acceso restringido',
      'login.subtitle': 'Ingres\u00e1 tus credenciales para ver el dashboard.',
      'login.user': 'Usuario',
      'login.password': 'Contrase\u00f1a',
      'login.enter': 'Ingresar',
      'login.note': 'La sesi\u00f3n se mantiene por 90 d\u00edas.',
      'login.bad_credentials': 'Credenciales incorrectas',
      'dyn.invalid_number': 'N\u00famero inv\u00e1lido',
      'dyn.saved_pending': '\u2713 guardado (rec\u00e1lculo pendiente)',
      'dyn.more_cheap': '\u00d7 m\u00e1s barato',
      'dyn.more_expensive': '\u00d7 m\u00e1s caro',
      'dyn.no_comparable': 'No hay modelos comparables.',
      'dyn.no_comparable_selected': 'El modelo elegido no tiene un costo comparable.',
      'dyn.api_cost_metric': 'Costo por API',
      'dyn.eff_sub_metric': 'Costo efectivo por suscripci\u00f3n',
      'dyn.select_ref_first': 'Seleccion\u00e1 un modelo de referencia primero.',
      'dyn.lbl_rank': '#',
      'dyn.lbl_model': 'Modelo',
      'dyn.lbl_requests': 'Requests',
      'dyn.lbl_input_nocache': 'Input sin cache',
      'dyn.lbl_output': 'Output',
      'dyn.lbl_cache_input': 'Cache input',
      'dyn.lbl_cache_pct': 'Cache %',
      'dyn.lbl_total': 'Total',
      'dyn.lbl_cost': 'Costo',
      'dyn.lbl_pct': '%',
      'dyn.tooltip_total': ' total  \u00b7  ',
      'dyn.sessions_word': ' sesiones',
      'dyn.percent_more': '% m\u00e1s',
      'dyn.percent_less': '% menos \u00b7 ',
      'dyn.price_pending': 'precio pendiente',
      'dyn.reference': 'referencia',
      'dyn.difference': 'Diferencia',
      'dyn.break_even': 'Punto de equilibrio',
      'dyn.models_word': ' modelos',
      'dyn.save_error': 'Error al guardar: '
    }
  };

  var LS_KEY = 'ss_lang';

  function getLang() {
    try {
      var saved = window.localStorage.getItem(LS_KEY);
      if (saved === 'es' || saved === 'en') return saved;
    } catch (err) { /* storage bloqueado */ }
    return 'en'; // default inglés
  }

  function t(key) {
    var lang = getLang();
    var dict = DICT[lang] || DICT.en;
    return dict[key] != null ? dict[key] : (DICT.en[key] != null ? DICT.en[key] : key);
  }

  function applyI18n(root) {
    var scope = root || document;
    var lang = getLang();
    scope.querySelectorAll('[data-i18n]').forEach(function (el) {
      var key = el.getAttribute('data-i18n');
      // etiqueta corta opcional (data-i18n-short) para tablas compactas
      var shortKey = el.getAttribute('data-i18n-short');
      if (el.hasAttribute('data-short') || el.closest('[data-compact-labels]')) {
        var shortVal = shortKey || null;
        if (shortVal != null) { el.textContent = shortVal; return; }
      }
      var val = t(key);
      if (el.getAttribute('data-i18n-html') === '1') {
        el.innerHTML = val;
      } else {
        el.textContent = val;
      }
    });
    scope.querySelectorAll('[data-i18n-attr]').forEach(function (el) {
      // formato: data-i18n-attr="attr:key;attr2:key2"
      el.getAttribute('data-i18n-attr').split(';').forEach(function (pair) {
        var parts = pair.split(':');
        if (parts.length === 2) {
          el.setAttribute(parts[0].trim(), t(parts[1].trim()));
        }
      });
    });
    var htmlEl = document.documentElement;
    if (htmlEl) htmlEl.setAttribute('lang', lang);
    var titleKeys = document.querySelectorAll('title[data-i18n]');
    titleKeys.forEach(function (el) { el.textContent = t(el.getAttribute('data-i18n')); });
    // marcar botón activo
    document.querySelectorAll('.lang-btn').forEach(function (btn) {
      var active = btn.getAttribute('data-lang') === lang;
      btn.setAttribute('data-active', active ? 'true' : 'false');
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
  }

  function setLang(lang) {
    if (lang !== 'es' && lang !== 'en') return;
    try { window.localStorage.setItem(LS_KEY, lang); } catch (err) { /* noop */ }
    window.location.reload();
  }

  function wireToggle() {
    document.querySelectorAll('.lang-btn').forEach(function (btn) {
      btn.addEventListener('click', function () { setLang(btn.getAttribute('data-lang')); });
    });
  }

  // Exponer para app.js
  window.SS_I18N = {
    t: t,
    getLang: getLang,
    setLang: setLang,
    applyI18n: applyI18n,
    monthsShort: function () {
      return getLang() === 'en'
        ? ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
        : ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC'];
    },
    intlLocale: function () { return getLang() === 'en' ? 'en-US' : 'es-AR'; }
  };

  function init() {
    wireToggle();
    applyI18n();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
