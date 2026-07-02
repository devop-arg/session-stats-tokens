(function() {
'use strict';

var BAR_COLORS = ['#ff8904','#ffb900','#00bc7d','#00d3f2','#00d5be','#51a2ff','#7c86ff','#9ae600','#a684ff','#ed6aff'];

function fmt(n) {
  if (n == null) return '—';
  if (typeof n === 'number' && n > 1e12) return (n / 1e12).toFixed(1) + 'T';
  if (typeof n === 'number' && n > 1e9) return (n / 1e9).toFixed(1) + 'B';
  if (typeof n === 'number' && n > 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (typeof n === 'number' && n > 1e3) return (n / 1e3).toFixed(1) + 'K';
  return String(n ?? '—');
}

function fmtCost(n) {
  if (n == null) return '—';
  if (n < 0.01) return '$' + n.toFixed(4);
  return '$' + Number(n).toFixed(2);
}

function fmtPct(n) {
  if (n == null) return '—';
  return n.toFixed(1) + '%';
}

function fmtTokens(n) {
  if (n >= 1e12) return (n / 1e12).toFixed(n >= 1e13 ? 0 : 1) + 'T';
  if (n >= 1e9)  return (n / 1e9).toFixed(n >= 1e10 ? 0 : 1) + 'B';
  if (n >= 1e6)  return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3)  return (n / 1e3).toFixed(1) + 'K';
  return String(n);
}

function displayModelName(model) {
  // Strip known provider prefixes for display (keep data-model raw for highlighting)
  return model.replace(/^(stepfun|deepseek-ai|deepseek|openrouter|arcee-ai|nvidia|x-ai|zai-org|nex-agi)\//, '');
}

function getPPMColor(price) {
  if (price <= 0.10) return '#4ade80';   // verde
  if (price <= 0.20) return '#facc15';   // amarillo
  if (price <= 0.50) return '#fb923c';   // naranja
  return '#f87171';                       // naranja rojizo
}

function fmtDateTimeArt(ts, fallback) {
  if (!ts) return fallback || '—';
  try {
    return new Intl.DateTimeFormat('es-AR', {
      timeZone: 'America/Argentina/Buenos_Aires',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    }).format(new Date(ts * 1000)).replace(',', '');
  } catch (err) {
    return fallback || '—';
  }
}

Chart.defaults.color = '#808080';
Chart.defaults.font.family = '"IBM Plex Mono", monospace';
Chart.defaults.font.size = 11;
Chart.defaults.font.weight = '500';
Chart.defaults.animation = false;

// --- Dashboard ---
if (document.querySelector('.stats-grid')) {

  // Summary
  fetch('/api/summary')
    .then(function(r) { return r.json(); })
    .then(function(d) {
      var cli = d.header_totals_cli;
      var ts = cli ? cli.sessions : d.total_sessions;
      var tc = cli ? cli.cost : d.total_cost;
      var tr = cli ? cli.requests : d.total_requests;
      var ti = cli ? cli.input_tokens : d.total_input_tokens;
      var to = cli ? cli.output_tokens : d.total_output_tokens;
      var tca = cli ? cli.cache_tokens : d.total_cache_tokens;
      document.querySelector('[data-stat="total-cost"]').textContent = fmtCost(tc);
      var totalTk = cli ? cli.total_tokens : d.total_tokens;
      document.querySelector('[data-stat="total-tokens"]').textContent = fmt(totalTk);
      document.querySelector('[data-stat="total-sessions"]').textContent = fmt(ts);
      document.querySelector('[data-stat="cache-ratio"]').textContent = fmtPct(cli ? cli.cache_ratio : d.cache_ratio);
      document.querySelector('[data-stat="total-requests"]').textContent = fmt(tr);
      var sc = document.getElementById('session-count');
      if (sc) sc.textContent = fmt(d.total_sessions);
      var upd = document.getElementById('updated-badge');
      if (upd && d.last_updated) upd.textContent = 'Actualizado ' + d.last_updated;
    });

  // --- Today Summary (hora Argentina) ---
  var todaySection = document.getElementById('today-section');
  var todayStats = document.getElementById('today-stats');
  var todayModels = document.getElementById('today-models');

  fetch('/api/today-summary')
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (!d || !d.top_models || d.top_models.length === 0) {
        todaySection.classList.remove('has-data');
        return;
      }
      todaySection.classList.add('has-data');
      document.getElementById('today-tokens').textContent = fmt(d.total_tokens);
      document.getElementById('today-requests').textContent = fmt(d.total_requests);
      document.getElementById('today-cost').textContent = fmtCost(d.total_cost);

      todayModels.innerHTML = '';
      d.top_models.forEach(function(m, i) {
        var row = document.createElement('div');
        row.className = 'today-model-row';
        var barPct = m.percent;
        var cacheRatio = typeof m.cache_ratio === 'number' ? m.cache_ratio : 0;
        row.innerHTML =
          '<span class="today-model-rank">' + String(i + 1).padStart(2, '0') + '</span>' +
          '<span class="today-model-name">' + displayModelName(m.model) + '</span>' +
          '<span class="today-model-reqs">' + fmt(m.requests) + ' req</span>' +
          '<span class="today-model-ioc i">In ' + fmtTokens(m.input_tokens) + '</span>' +
          '<span class="today-model-sep">-</span>' +
          '<span class="today-model-ioc o">Out ' + fmtTokens(m.output_tokens) + '</span>' +
          '<span class="today-model-sep">-</span>' +
          '<span class="today-model-ioc c">Cache ' + fmtTokens(m.cache_tokens) + '</span>' +
          '<span class="today-model-sep">-</span>' +
          '<span class="today-model-cache-ratio">Ratio ' + fmtPct(cacheRatio) + '</span>' +
          '<span class="today-model-sep">-</span>' +
          '<span class="today-model-total">Total ' + fmtTokens(m.tokens) + '</span>' +
          '<span class="today-model-sep">-</span>' +
          '<span class="today-model-cost">Costo ' + fmtCost(m.cost) + '</span>' +
          '<span class="today-model-sep">-</span>' +
          '<span class="today-model-pct">' + barPct + '%</span>';
        todayModels.appendChild(row);
      });
    })
    .catch(function(err) { console.error('today-summary error:', err); });

  // --- Top Models (12 meses semanal, colores por modelo) ---
  // 20 colores distinguibles para los top 20 modelos
  var MODEL_COLORS = ['#ff8904','#ffb900','#00bc7d','#00d3f2','#51a2ff','#7c86ff','#ed6aff','#ff5e5e','#9ae600','#c77dff','#ffd23f','#00d5be','#a684ff','#f15bb5','#7fb069','#ff073a','#0eb7c0','#b8d12a','#ff6b9d','#8b5cf6'];
  var GRAY = '#808080';

  function isColumnLabelHidden(i, count) {
    // Mostrar ~8 labels para 52 semanas
    if (count <= 8) return false;
    if (count <= 14) return i % 2 !== 0 && i !== count - 1;
    var interval = Math.max(1, Math.round(count / 8));
    return i !== count - 1 && i % interval !== 0;
  }

  function getMaxTotal(points) {
    var max = 0;
    points.forEach(function(p) {
      var t = 0;
      (p.segments || []).forEach(function(s) { t += s.value; });
      if (t > max) max = t;
    });
    if (max === 0) return 1;
    return max;
  }

  function getBarHeight(total, max) {
    if (total <= 0) return 0;
    return Math.max(2, Math.min(100, total / max * 100));
  }

  function getYAxisStep(maxVal) {
    if (maxVal <= 0) return 1;
    var rough = maxVal / 4;
    var power = Math.pow(10, Math.floor(Math.log10(rough)));
    var normalized = rough / power;
    var factor = 1;
    if (normalized > 5) factor = 10;
    else if (normalized > 2) factor = 5;
    else if (normalized > 1) factor = 2;
    return factor * power;
  }

  function getYAxisWidth(maxVal) {
    return Math.max(60, Math.min(88, fmtTokens(maxVal).length * 8 + 12));
  }

  function getBarGap(totalPoints) {
    if (totalPoints >= 28) return 3;
    if (totalPoints >= 20) return 4;
    if (totalPoints >= 12) return 6;
    return 8;
  }

  function buildBar(barEl, point, pointIndex, maxTotal, totalPoints, getModelColor) {
    var total = 0;
    var totalCost = 0;
    (point.segments || []).forEach(function(s) { total += s.value; totalCost += s.cost || 0; });

    barEl.setAttribute('data-slot', 'top-models-bar');
    barEl.className = 'top-models-bar';
    barEl.setAttribute('role', 'button');
    barEl.setAttribute('tabindex', '0');
    barEl.setAttribute('aria-label', point.date + ': ' + fmtTokens(total) + ' tokens');
    barEl.style.setProperty('--bar-height', getBarHeight(total, maxTotal) + '%');

    if (total === 0) return;

    var stack = document.createElement('div');
    stack.setAttribute('data-slot', 'top-models-stack');
    stack.className = 'top-models-stack';

    var visible = point.segments.filter(function(s) { return s.value > 0; });
    var sorted = visible.slice().sort(function(a, b) { return b.value - a.value; });
    stack.style.gridTemplateRows = sorted.map(function(s) {
      return (s.value / total * 100).toFixed(3) + '%';
    }).join(' ');

    sorted.forEach(function(s) {
      var el = document.createElement('i');
      el.setAttribute('data-model', s.model);
      el.setAttribute('title', displayModelName(s.model));
      el.style.background = getModelColor(s.model);
      stack.appendChild(el);
    });

    barEl.appendChild(stack);

    // Tooltip
    var tip = document.createElement('div');
    tip.setAttribute('data-component', 'chart-tooltip');
    tip.className = 'chart-tooltip';
    var threshold = totalPoints - Math.max(4, Math.floor(totalPoints * 0.4));
    tip.setAttribute('data-placement', pointIndex >= threshold ? 'left' : 'right');

    var strong = document.createElement('strong');
    strong.textContent = point.date;
    tip.appendChild(strong);

    var sub = document.createElement('span');
    sub.textContent = fmtTokens(total) + ' total  ·  ' + fmtCost(totalCost);
    tip.appendChild(sub);

    var divider = document.createElement('div');
    divider.setAttribute('data-slot', 'tooltip-divider');
    divider.className = 'tooltip-divider';
    tip.appendChild(divider);

    visible.slice().sort(function(a, b) { return b.value - a.value; }).forEach(function(s) {
      var p = document.createElement('p');
      var label = document.createElement('span');
      label.className = 'tooltip-label';
      var dot = document.createElement('i');
      dot.style.background = getModelColor(s.model);
      label.appendChild(dot);
      var nameSpan = document.createElement('span');
      nameSpan.textContent = displayModelName(s.model);
      label.appendChild(nameSpan);
      p.appendChild(label);
      var b = document.createElement('b');
      b.textContent = fmtTokens(s.value) + '  ' + fmtCost(s.cost);
      p.appendChild(b);
      tip.appendChild(p);
    });

    barEl.appendChild(tip);
  }

  function buildLeaderCard(entry, onToggle) {
    var card = document.createElement('div');
    card.className = 'leader-card';
    card.setAttribute('data-model', entry.model);
    card.setAttribute('role', 'listitem');

    var rank = document.createElement('span');
    rank.className = 'leader-rank';
    rank.textContent = String(entry.rank).padStart(2, '0');
    card.appendChild(rank);

    var inner = document.createElement('div');
    inner.className = 'leader-inner';

    var row1 = document.createElement('div');
    row1.className = 'leader-row1';

    var name = document.createElement('span');
    name.className = 'leader-name';
    name.textContent = displayModelName(entry.model);
    row1.appendChild(name);

    var pct = document.createElement('span');
    pct.className = 'leader-percent';
    pct.textContent = entry.percent.toFixed(1) + '%';
    row1.appendChild(pct);

    var cost = document.createElement('span');
    cost.className = 'leader-cost';
    cost.textContent = fmtCost(entry.cost);
    row1.appendChild(cost);

    var ppm = document.createElement('span');
    ppm.className = 'leader-ppm';
    ppm.textContent = '$' + (entry.price_per_1m || 0).toFixed(2) + '/M';
    ppm.style.color = getPPMColor(entry.price_per_1m || 0);
    row1.appendChild(ppm);

    inner.appendChild(row1);

    var row2 = document.createElement('div');
    row2.className = 'leader-row2';

    var tokens = document.createElement('span');
    tokens.className = 'leader-tokens';
    tokens.textContent = 'I ' + fmtTokens(entry.input_tokens || 0).replace('.0', '') +
                         '  O ' + fmtTokens(entry.output_tokens || 0).replace('.0', '') +
                         '  C ' + fmtTokens(entry.cache_tokens || 0).replace('.0', '') +
                         '  T ' + fmtTokens(entry.tokens).replace('.0', '') +
                         '  R ' + fmt(entry.requests || 0);
    row2.appendChild(tokens);

    inner.appendChild(row2);
    card.appendChild(inner);

    card.addEventListener('click', function() {
      onToggle(entry.model);
    });

    return card;
  }

  function renderLeaderboard(container, entries, onToggle) {
    if (!container) return;
    container.innerHTML = '';
    if (!entries || entries.length === 0) return;
    entries.forEach(function(e) {
      container.appendChild(buildLeaderCard(e, onToggle));
    });
  }

  function createTopModelsSection(config) {
    var section = document.getElementById(config.sectionId);
    var chartEl = document.getElementById(config.chartId);
    var barsEl = document.getElementById(config.barsId);
    var axisEl = document.getElementById(config.axisId);
    var yAxisEl = document.getElementById(config.yAxisId);
    var leaderboardContainer = document.getElementById(config.leaderboardId);
    var activeModel = '';
    var modelColorMap = {};

    if (!barsEl || !axisEl || !leaderboardContainer) return;

    function getModelColor(model) {
      return modelColorMap[model] || GRAY;
    }

    function syncHighlightState() {
      barsEl.querySelectorAll('.top-models-stack i').forEach(function(seg) {
        var matches = !activeModel || seg.getAttribute('data-model') === activeModel;
        seg.setAttribute('data-dimmed', matches ? 'false' : 'true');
      });
      leaderboardContainer.querySelectorAll('.leader-card').forEach(function(card) {
        var selected = activeModel && card.getAttribute('data-model') === activeModel;
        card.setAttribute('data-selected', selected ? 'true' : 'false');
        card.setAttribute('data-dimmed', activeModel && !selected ? 'true' : 'false');
      });
    }

    function toggleModel(model) {
      activeModel = activeModel === model ? '' : model;
      syncHighlightState();
    }

    fetch(config.endpoint)
      .then(function(r) { return r.json(); })
      .then(function(data) {
        var rangeKey = data.range || config.rangeKey;
        var points = (data.usage && data.usage['All Users'] && data.usage['All Users'][rangeKey]) || [];
        var leaders = data.leaderboard || [];
        var topModels = data.topModels || [];

        if (section) {
          section.style.display = leaders.length > 0 ? 'block' : 'none';
        }

        modelColorMap = {};
        topModels.forEach(function(m, i) {
          modelColorMap[m] = MODEL_COLORS[i % MODEL_COLORS.length];
        });

        if (chartEl) {
          chartEl.setAttribute('data-range', rangeKey);
        }

        var maxTotal = getMaxTotal(points);
        var totalPoints = points.length;
        var yAxisStep = config.yAxisStep || getYAxisStep(maxTotal);

        if (chartEl) {
          chartEl.style.setProperty('--y-axis-width', getYAxisWidth(Math.ceil(maxTotal / yAxisStep) * yAxisStep) + 'px');
          chartEl.style.setProperty('--bar-gap', getBarGap(totalPoints) + 'px');
        }

        axisEl.innerHTML = '';
        points.forEach(function(p, i) {
          var cell = document.createElement('div');
          if (isColumnLabelHidden(i, totalPoints)) {
            cell.setAttribute('data-label-hidden', 'true');
          }
          var label = document.createElement('span');
          label.className = 'axis-label';
          var dateSpan = document.createElement('span');
          dateSpan.className = 'axis-date';
          dateSpan.textContent = p.date;
          label.appendChild(dateSpan);
          cell.appendChild(label);
          axisEl.appendChild(cell);
        });

        barsEl.innerHTML = '';
        points.forEach(function(p, i) {
          var bar = document.createElement('div');
          buildBar(bar, p, i, maxTotal, totalPoints, getModelColor);
          barsEl.appendChild(bar);
        });

        renderLeaderboard(leaderboardContainer, leaders, toggleModel);
        syncHighlightState();

        if (yAxisEl) {
          yAxisEl.innerHTML = '';
          var maxVal = maxTotal;
          if (maxVal > 0) {
            var step = yAxisStep;
            var top = Math.ceil(maxVal / step) * step;
            var labels = [];
            for (var v = 0; v <= top; v += step) {
              labels.push(v);
            }
            labels.forEach(function(v) {
              var el = document.createElement('div');
              el.className = 'top-y-axis-label';
              el.textContent = fmtTokens(v);
              yAxisEl.appendChild(el);
            });
          }
        }
      })
      .catch(function(err) { console.error(config.endpoint + ' error:', err); });
  }

  createTopModelsSection({
    sectionId: 'top-models-30d',
    chartId: 'top-models-30d-chart',
    barsId: 'top-models-30d-bars',
    axisId: 'top-models-30d-axis',
    yAxisId: 'top-models-30d-y-axis',
    leaderboardId: 'top-models-30d-leaderboard',
    endpoint: '/api/top-models-30d',
    rangeKey: '30D'
  });

  createTopModelsSection({
    sectionId: 'top-models',
    chartId: 'top-models-chart',
    barsId: 'top-bars',
    axisId: 'top-axis',
    yAxisId: 'top-y-axis',
    leaderboardId: 'leaderboard',
    endpoint: '/api/top-models',
    rangeKey: '12M'
  });

  // --- Activity (weekly timeseries) ---
  var activityCanvas = document.getElementById('activity-chart');
  var activityMetric = 'tokens';
  var activityChart = null;
  var sourcesLegend = document.getElementById('sources-legend');
  var sourcesLastData = null;

  var SOURCE_COLORS = {
    hermes: '#ff8904',
    opencode: '#3b82f6',
    codex: '#22c55e',
    cursor: '#a855f7',
    kilocode: '#64748b',
    legacy: '#94a3b8',
    unknown: '#ef4444'
  };

  function buildActivityDataset(rows, metric) {
    return rows.map(function(r) {
      if (metric === 'cost') return Number(r.cost || 0);
      if (metric === 'sessions') return Number(r.sessions || 0);
      return Number(r.input_tokens || 0) + Number(r.output_tokens || 0) + Number(r.cache_tokens || 0);
    });
  }

  function activityLabel(metric, value) {
    if (metric === 'cost') return fmtCost(value);
    if (metric === 'sessions') return fmt(value);
    return fmt(value);
  }

  function buildSourcesDatasets(rows) {
    // rows: [{period, source, sessions, requests}, ...]
    var periods = [];
    var sourceMap = {};
    rows.forEach(function(r) {
      if (periods.indexOf(r.period) === -1) periods.push(r.period);
      if (!sourceMap[r.source]) sourceMap[r.source] = {};
      sourceMap[r.source][r.period] = Number(r.sessions || 0);
    });
    // Sort sources by total sessions descending
    var sortedSources = Object.keys(sourceMap).sort(function(a, b) {
      var totalA = Object.values(sourceMap[a]).reduce(function(s, v) { return s + v; }, 0);
      var totalB = Object.values(sourceMap[b]).reduce(function(s, v) { return s + v; }, 0);
      return totalB - totalA;
    });
    var datasets = [];
    sortedSources.forEach(function(source) {
      var data = periods.map(function(p) { return sourceMap[source][p] || 0; });
      datasets.push({
        label: source.charAt(0).toUpperCase() + source.slice(1),
        data: data,
        backgroundColor: SOURCE_COLORS[source] || '#808080',
        borderWidth: 0,
        barPercentage: 0.9,
        categoryPercentage: 0.96
      });
    });
    return { periods: periods, datasets: datasets };
  }

  function renderSourcesChart(rows) {
    if (!activityCanvas) return;
    sourcesLastData = rows;
    var built = buildSourcesDatasets(rows);
    var labels = built.periods.map(function(p) {
      var date = new Date(p + 'T00:00:00');
      var months = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC'];
      return String(date.getDate()).padStart(2, '0') + '/' + months[date.getMonth()];
    });

    if (activityChart) activityChart.destroy();
    activityChart = new Chart(activityCanvas.getContext('2d'), {
      type: 'bar',
      data: { labels: labels, datasets: built.datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            mode: 'index',
            callbacks: {
              label: function(ctx) {
                return ctx.dataset.label + ': ' + fmt(ctx.parsed.y) + ' sesiones';
              }
            }
          }
        },
        scales: {
          x: { stacked: true, grid: { display: false }, ticks: { color: '#808080', maxTicksLimit: 8 } },
          y: {
            stacked: true,
            grid: { color: 'rgba(255,255,255,0.08)' },
            ticks: { color: '#808080', callback: function(v) { return fmt(v); } }
          }
        }
      }
    });

    // Build color legend
    if (sourcesLegend) {
      sourcesLegend.style.display = 'flex';
      sourcesLegend.style.flexWrap = 'wrap';
      sourcesLegend.style.gap = '10px';
      sourcesLegend.style.justifyContent = 'center';
      sourcesLegend.innerHTML = '';
      built.datasets.forEach(function(ds) {
        var item = document.createElement('span');
        item.style.display = 'inline-flex';
        item.style.alignItems = 'center';
        item.style.gap = '5px';
        item.style.fontSize = '11px';
        item.style.fontFamily = 'var(--mono)';
        item.style.color = '#aaa';
        var dot = document.createElement('span');
        dot.style.width = '10px';
        dot.style.height = '10px';
        dot.style.borderRadius = '2px';
        dot.style.background = ds.backgroundColor;
        item.appendChild(dot);
        item.appendChild(document.createTextNode(ds.label));
        sourcesLegend.appendChild(item);
      });
    }
  }

  function renderActivity(rows) {
    if (!activityCanvas) return;
    // Si es sources mode, redirigir a renderSourcesChart
    if (activityMetric === 'sources') {
      if (sourcesLastData) { renderSourcesChart(sourcesLastData); }
      return;
    }

    sourcesLegend.style.display = 'none';
    var labels = rows.map(function(r) {
      var date = new Date(r.period + 'T00:00:00');
      var months = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC'];
      return String(date.getDate()).padStart(2, '0') + '/' + months[date.getMonth()];
    });
    var values = buildActivityDataset(rows, activityMetric);
    var peak = 0;
    var peakIndex = 0;
    values.forEach(function(v, i) {
      if (v >= peak) {
        peak = v;
        peakIndex = i;
      }
    });

    if (activityChart) activityChart.destroy();
    activityChart = new Chart(activityCanvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: values.map(function(_, i) { return i === peakIndex ? '#ff8904' : '#3a3a3a'; }),
          borderWidth: 0,
          barPercentage: 0.9,
          categoryPercentage: 0.96
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(ctx) { return activityLabel(activityMetric, ctx.parsed.y); }
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              color: '#808080',
              maxTicksLimit: 8
            }
          },
          y: {
            grid: { color: 'rgba(255,255,255,0.08)' },
            ticks: {
              color: '#808080',
              callback: function(value) { return activityLabel(activityMetric, value); }
            }
          }
        }
      }
    });
  }

  // Fetch timeseries + sources in parallel
  var timeseriesPromise = fetch('/api/timeseries?range=all&bucket=week').then(function(r) { return r.json(); });
  var sourcesPromise = fetch('/api/timeseries/sources?range=all&bucket=week').then(function(r) { return r.json(); });

  Promise.all([timeseriesPromise, sourcesPromise]).then(function(results) {
    var rows = results[0];
    var sourceRows = results[1];

    var last52 = rows.slice(-52);
    // Also slice sources to last 52 weeks
    var periods52 = last52.map(function(r) { return r.period; });
    var last52Sources = sourceRows.filter(function(r) { return periods52.indexOf(r.period) !== -1; });
    sourcesLastData = last52Sources;

    function getPeak(metric) {
      if (metric === 'sources') return '';
      var values = buildActivityDataset(last52, metric);
      var peak = 0;
      values.forEach(function(v) { if (v > peak) peak = v; });
      return peak;
    }
    document.getElementById('activity-peak-tokens').textContent = fmt(getPeak('tokens'));
    document.getElementById('activity-peak-cost').textContent = fmtCost(getPeak('cost'));
    document.getElementById('activity-peak-sessions').textContent = fmt(getPeak('sessions'));
    renderActivity(last52);

    var tabs = document.querySelectorAll('.activity-tab');
    tabs.forEach(function(tab) {
      tab.addEventListener('click', function() {
        activityMetric = tab.getAttribute('data-metric');
        tabs.forEach(function(t) {
          t.removeAttribute('data-active');
          t.setAttribute('aria-selected', 'false');
        });
        tab.setAttribute('data-active', 'true');
        tab.setAttribute('aria-selected', 'true');

        if (activityMetric === 'sources') {
          renderSourcesChart(sourcesLastData);
        } else {
          renderActivity(last52);
        }
      });
    });
  });

  // --- Token Cost ---
  var tokenCostData = null;
  var tokenCostSort = 'price';

  function renderTokenCost() {
    var list = document.getElementById('token-cost-list');
    if (!list || !tokenCostData) return;
    list.innerHTML = '';

    var models = tokenCostData.models.slice();
    models.sort(function(a, b) {
      if (tokenCostSort === 'tokens') return (b.total_tokens || 0) - (a.total_tokens || 0);
      return (b.price_per_1m || 0) - (a.price_per_1m || 0);
    });

    var refMax = tokenCostSort === 'tokens'
      ? (models.length ? Math.max.apply(null, models.map(function(m) { return m.total_tokens || 0; })) : 1)
      : (models.length ? Math.max.apply(null, models.map(function(m) { return m.price_per_1m || 0; })) : 1);

    models.forEach(function(m, i) {
      var val = tokenCostSort === 'tokens' ? (m.total_tokens || 0) : (m.price_per_1m || 0);
      var pct = refMax > 0 ? (val / refMax * 100).toFixed(0) : 0;
      var color = BAR_COLORS[i % BAR_COLORS.length];
      var row = document.createElement('div');
      row.className = 'token-row';
      row.innerHTML =
        '<span class="token-row-name">' + m.model + '</span>' +
        '<div class="metric-bar"><div class="metric-bar-fill" style="width:' + pct + '%;background:' + color + '"></div></div>' +
        '<span class="token-row-value">' + fmtCost(m.price_per_1m) + '</span>' +
        '<span class="token-row-tokens">' + fmt(m.total_tokens) + '</span>';
      list.appendChild(row);
    });
  }

  fetch('/api/token-cost')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      document.getElementById('overall-price-per-1m').textContent = fmtCost(data.overall.price_per_1m);
      document.getElementById('token-total-tokens').textContent = fmt(data.overall.total_tokens);
      tokenCostData = data;
      renderTokenCost();

      var sortBtns = document.querySelectorAll('.sort-btn');
      sortBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
          tokenCostSort = btn.getAttribute('data-sort');
          sortBtns.forEach(function(b) {
            b.removeAttribute('data-active');
            b.setAttribute('aria-pressed', 'false');
          });
          btn.setAttribute('data-active', 'true');
          btn.setAttribute('aria-pressed', 'true');
          renderTokenCost();
        });
      });
    });

  // --- Cache Ratio ---
  fetch('/api/cache-ratio')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      document.getElementById('overall-cache-ratio').textContent = fmtPct(data.overall.ratio);
      document.getElementById('overall-cached').textContent = fmt(data.overall.cached);
      document.getElementById('overall-uncached').textContent = fmt(data.overall.uncached);
      document.getElementById('overall-total-input').textContent = fmt(data.overall.cached + data.overall.uncached);

      var list = document.getElementById('cache-ratio-list');
      if (!list) return;
      list.innerHTML = '';

      data.models.forEach(function(m, i) {
        var left = m.ratio;
        var row = document.createElement('div');
        row.className = 'cache-row';
        row.innerHTML =
          '<span class="cache-rank">' + String(i + 1).padStart(2, '0') + '</span>' +
          '<span class="cache-name">' + m.model + '</span>' +
          '<div class="cache-bar-wrap">' +
            '<div class="cache-bar"><div class="cache-marker" style="left:calc(' + left + '% - 3.5px)"></div></div>' +
            '<span class="cache-value">' + fmtPct(m.ratio) + '</span>' +
          '</div>';
        list.appendChild(row);
      });
    });
}

// --- Sessions page ---
if (document.getElementById('sessions-tbody')) {
  var offset = 0;
  var limit = 50;
  var sourceFilter = '';

  function loadSessions() {
    var tbody = document.getElementById('sessions-tbody');
    tbody.innerHTML = '<tr><td colspan="9" class="loading-row">Cargando...</td></tr>';
    var url = '/api/sessions?limit=' + limit + '&offset=' + offset;
    if (sourceFilter) url += '&source=' + sourceFilter;

    fetch(url)
      .then(function(r) { return r.json(); })
      .then(function(data) {
        tbody.innerHTML = '';
        var total = data.total;
        document.getElementById('total-sessions-label').textContent = total;
        document.getElementById('page-num').textContent = Math.floor(offset / limit) + 1;
        document.getElementById('prev-page').disabled = offset <= 0;
        document.getElementById('next-page').disabled = (offset + limit) >= total;

        if (data.sessions.length === 0) {
          tbody.innerHTML = '<tr><td colspan="9" class="loading-row">Sin resultados</td></tr>';
          return;
        }

        data.sessions.forEach(function(s) {
          var tr = document.createElement('tr');
          var totalT = (s.input_tokens || 0) + (s.output_tokens || 0) + (s.cache_tokens || 0);
          tr.innerHTML =
            '<td title="' + (s.id || '') + '">' + (s.id ? s.id.slice(0, 24) + '...' : '—') + '</td>' +
            '<td>' + fmtDateTimeArt(s.timestamp, s.date) + '</td>' +
            '<td>' + (s.source || '—') + '</td>' +
            '<td class="num">' + fmt(s.requests) + '</td>' +
            '<td class="num">' + fmt(s.input_tokens) + '</td>' +
            '<td class="num">' + fmt(s.output_tokens) + '</td>' +
            '<td class="num">' + fmt(s.cache_tokens) + '</td>' +
            '<td class="num">' + fmtCost(s.cost) + '</td>';
          tbody.appendChild(tr);
        });
      })
      .catch(function() {
        tbody.innerHTML = '<tr><td colspan="9" class="loading-row">Error al cargar</td></tr>';
      });
  }

  document.getElementById('prev-page').addEventListener('click', function() {
    if (offset > 0) { offset -= limit; loadSessions(); }
  });
  document.getElementById('next-page').addEventListener('click', function() {
    offset += limit; loadSessions();
  });
  document.getElementById('source-filter').addEventListener('change', function(e) {
    sourceFilter = e.target.value; offset = 0; loadSessions();
  });
  loadSessions();
}

// --- Models page ---
if (document.getElementById('models-tbody')) {
  fetch('/api/models?limit=200')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var tbody = document.getElementById('models-tbody');
      tbody.innerHTML = '';

      data.forEach(function(m, i) {
        var tr = document.createElement('tr');
        var totalT = (m.input_tokens || 0) + (m.output_tokens || 0) + (m.cache_tokens || 0);
        tr.innerHTML =
          '<td class="num"><span class="rank' + (i < 3 ? ' top-3' : '') + '">' + (i + 1) + '</span></td>' +
          '<td><span class="model-name">' + m.model + '</span></td>' +
          '<td class="num">' + fmt(m.requests) + '</td>' +
          '<td class="num">' + fmt(m.input_tokens) + '</td>' +
          '<td class="num">' + fmt(m.output_tokens) + '</td>' +
          '<td class="num">' + fmt(m.cache_tokens) + '</td>' +
          '<td class="num">' + fmt(totalT) + '</td>' +
          '<td class="num">' + fmtCost(m.cost) + '</td>';
        tbody.appendChild(tr);
      });
    });
}
// --- Subscription estimate table with calculator & sorting (standalone block) ---
if (document.getElementById('subscription-tbody')) {
  var subSection = document.getElementById('subscription-section');
  var subTbody = document.getElementById('subscription-tbody');
  var subData = null;  // raw server data
  var subModels = [];  // computed models (after calculator adjustments)
  var subSortField = 'cost_sub';
  var subSortDir = 1;  // 1=asc (cheapest first), -1=desc

  function subSortCompare(a, b) {
    var av, bv;
    if (subSortField === 'name') {
      av = (a.model || '').toLowerCase();
      bv = (b.model || '').toLowerCase();
      return av < bv ? -subSortDir : av > bv ? subSortDir : 0;
    }
    if (subSortField === 'cost_sub') {
      av = a.cost_sub != null ? a.cost_sub : 999;
      bv = b.cost_sub != null ? b.cost_sub : 999;
    } else if (subSortField === 'savings') {
      av = a.savings_pct != null ? a.savings_pct : -1;
      bv = b.savings_pct != null ? b.savings_pct : -1;
    } else if (subSortField === 'tokens') {
      av = a.tokens || 0;
      bv = b.tokens || 0;
    } else if (subSortField === 'cost_api') {
      av = a.cost_api != null ? a.cost_api : 999;
      bv = b.cost_api != null ? b.cost_api : 999;
    }
    return av < bv ? -subSortDir : av > bv ? subSortDir : 0;
  }

  function subApplyCalculator() {
    if (!subData || !subData.models) return;

    var codexCost = parseFloat(document.getElementById('calc-codex-cost').value) || 20;
    var ocgCost = parseFloat(document.getElementById('calc-ocg-cost').value) || 10;
    var ocgCredit = parseFloat(document.getElementById('calc-ocg-credit').value) || 60;
    var ocgMultiplier = ocgCost > 0 ? ocgCredit / ocgCost : 6;

    subModels = subData.models.map(function(m) {
      var item = Object.assign({}, m);

      // For Codex models, keep server's cost_sub and update plan label
      if (item.plan && item.plan.indexOf('Codex') !== -1) {
        item.plan = 'Codex ($' + codexCost.toFixed(0) + '/mes)';
      } else if (item.plan && item.plan.indexOf('OpenCode Go') !== -1) {
        // OCG models: divide by multiplier
        item.cost_sub = item.cost_api / ocgMultiplier;
        item.multiplier = ocgMultiplier;
        item.plan = 'OpenCode Go ($' + ocgCost.toFixed(0) + ' → $' + ocgCredit.toFixed(0) + ')';
      }

      // Recalculate savings_pct
      if (item.cost_sub != null && item.cost_api > 0) {
        item.savings_pct = Math.round((1 - item.cost_sub / item.cost_api) * 100);
      }

      return item;
    });

    subRenderTable();
  }

  function subRenderTable() {
    if (!subTbody) return;

    var sorted = subModels.slice().sort(subSortCompare);
    subTbody.innerHTML = '';

    sorted.forEach(function(m, i) {
      var tr = document.createElement('tr');

      var costSubTxt = m.cost_sub != null ? '$' + m.cost_sub.toFixed(4) : '—';
      var planTxt = m.plan || '—';
      var vsTxt = m.vs_gpt54 || '—';
      var savingsTxt = '—';
      var savingsClass = '';

      if (m.savings_pct != null) {
        savingsTxt = m.savings_pct.toFixed(0) + '%';
        savingsClass = m.savings_pct > 50 ? ' saving-high' : (m.savings_pct > 20 ? ' saving-med' : '');
      }

      var vsClass = '';
      if (m.vs_gpt54 && m.vs_gpt54.indexOf('barato') !== -1) {
        vsClass = ' cheaper';
      } else if (m.vs_gpt54 && m.vs_gpt54.indexOf('caro') !== -1) {
        vsClass = ' pricier';
      }

      tr.innerHTML =
        '<td class="num"><span class="rank' + (i < 3 ? ' top-3' : '') + '">' + (i + 1) + '</span></td>' +
        '<td><span class="model-name">' + m.model + '</span></td>' +
        '<td class="num">' + fmt(m.tokens) + '</td>' +
        '<td class="num">' + fmtCost(m.cost_api) + '</td>' +
        '<td>' + planTxt + '</td>' +
        '<td class="num' + (m.cost_sub != null ? ' cost-sub' : '') + '">' + costSubTxt + '</td>' +
        '<td class="num' + savingsClass + '">' + savingsTxt + '</td>' +
        '<td class="num' + vsClass + '">' + vsTxt + '</td>';

      subTbody.appendChild(tr);
    });
  }

  fetch('/api/subscription-estimate')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (!data.models || data.models.length === 0) {
        if (subSection) subSection.style.display = 'none';
        return;
      }
      subData = data;

      // Populate reference model selector with GPT models only
      var refSelect = document.getElementById('calc-ref-model');
      var refCostInput = document.getElementById('calc-ref-cost');
      var refColHeader = document.getElementById('ref-col-header');

      var gptModels = subData.models.filter(function(m) {
        return m.plan && m.model.toLowerCase().indexOf('gpt') !== -1;
      });
      gptModels.sort(function(a, b) { return (a.model < b.model ? -1 : 1); });

      if (refSelect) {
        refSelect.innerHTML = '<option value="">— Seleccionar —</option>';
        gptModels.forEach(function(m) {
          var opt = document.createElement('option');
          opt.value = m.model;
          opt.textContent = m.model + ' — $' + (m.cost_sub != null ? m.cost_sub.toFixed(4) : '?') + '/1M';
          refSelect.appendChild(opt);
        });

        // Select gpt-5.4 by default if available
        var defaultRef = 'gpt-5.4';
        for (var i = 0; i < gptModels.length; i++) {
          if (gptModels[i].model === defaultRef) {
            refSelect.value = defaultRef;
            break;
          }
        }
        // If no gpt-5.4, select first available
        if (!refSelect.value && gptModels.length > 0) {
          refSelect.value = gptModels[0].model;
        }
      }

      // Get the currently selected reference model data
      function getRefModel() {
        var val = refSelect ? refSelect.value : '';
        for (var i = 0; i < gptModels.length; i++) {
          if (gptModels[i].model === val) return gptModels[i];
        }
        return null;
      }

      // Recalculate table with dynamic reference
      function recalcAll() {
        var refModel = getRefModel();
        var refPrice = parseFloat(refCostInput ? refCostInput.value : 0.0183) || 0.0183;

        // Update header
        if (refColHeader) {
          refColHeader.textContent = refModel ? refModel.model : 'gpt-5.4';
        }

        // Update results header
        function setTxt(id, val) { var e = document.getElementById(id); if (e) e.textContent = val; }
        setTxt('res-ref-model-name', refModel ? refModel.model : '—');
        setTxt('res-ref-ppm', refModel ? '$' + (refModel.cost_sub || 0).toFixed(4) + '/1M' : '—');

        // Recalculate vs_gpt54 for all models
        subData.models.forEach(function(m) {
          if (m.cost_sub != null) {
            var ratio = m.cost_sub / refPrice;
            if (ratio < 0.99) {
              m.vs_gpt54 = (1 / ratio).toFixed(1) + '× más barato';
            } else if (ratio > 1.01) {
              m.vs_gpt54 = ratio.toFixed(1) + '× más caro';
            } else {
              m.vs_gpt54 = '— (referencia)';
            }
          } else {
            m.vs_gpt54 = '—';
          }
        });

        // Update plan labels with current reference model name
        subData.models.forEach(function(m) {
          if (m.plan && m.plan.indexOf('Codex') !== -1) {
            var codexCost = parseFloat(document.getElementById('calc-codex-cost').value) || 20;
            m.plan = 'Codex ($' + codexCost.toFixed(0) + '/mes)';
          }
        });

        subApplyCalculator();
        updateCodexUsageCalc();
      }

      // Update Codex usage calculator
      function updateCodexUsageCalc() {
        var el = function(id) { return document.getElementById(id); };
        var planCost = parseFloat(el('calc-codex-cost').value) || 20;
        var pct = parseFloat(el('calc-codex-pct').value) || 0;
        var inpM = parseFloat(el('calc-codex-in').value) || 0;
        var outM = parseFloat(el('calc-codex-out').value) || 0;
        var cacheM = parseFloat(el('calc-codex-cache').value) || 0;
        var refModel = getRefModel();

        var usedM = inpM + outM + cacheM;
        var weekPct = pct / 100;

        var weekCost = weekPct > 0 ? (planCost / 4) * weekPct : 0;
        var monthCost = planCost;
        var weekFullM = weekPct > 0 ? usedM / weekPct : 0;
        var monthTokensM = weekFullM * 4;

        var effActual = usedM > 0 ? (weekCost / usedM) : 0;
        var effFull = monthTokensM > 0 ? (monthCost / monthTokensM) : 0;

        // API direct cost vs subscription cost for entered tokens
        var refSubPpm = refModel ? (refModel.cost_sub || 0) : (parseFloat(el('calc-ref-cost').value) || 0.0183);
        var refInputPrice = refModel ? refModel.input_price : null;
        var refOutputPrice = refModel ? refModel.output_price : null;
        var refCachePrice = refModel ? refModel.cache_price : null;

        var uncachedInpM = inpM;
        var apiWeekCost;
        if (refInputPrice != null && refOutputPrice != null) {
            uncachedInpM = cacheM >= inpM ? inpM : inpM - cacheM;
            apiWeekCost = uncachedInpM * refInputPrice + outM * refOutputPrice + cacheM * (refCachePrice || 0);
        } else {
            var fallbackPpm = refModel ? (refModel.cost_api || 0) : 0;
            apiWeekCost = usedM * fallbackPpm;
        }
        var effBillableM = uncachedInpM + outM + cacheM;
        var apiBlendedPpm = effBillableM > 0 ? apiWeekCost / effBillableM : 0;
        var subWeekCost = usedM * refSubPpm;
        var savingsWeek = apiWeekCost - subWeekCost;
        var savingsPct = apiWeekCost > 0 ? Math.round((1 - subWeekCost / apiWeekCost) * 100) : 0;

        function setTxt(id, val) { var e = el(id); if (e) e.textContent = val; }
        setTxt('res-ref-api-ppm', apiBlendedPpm > 0 ? '$' + apiBlendedPpm.toFixed(4) + '/1M' : '—');
        setTxt('res-codex-api-week', usedM > 0 ? '$' + apiWeekCost.toFixed(2) : '$—');
        setTxt('res-codex-savings-week', usedM > 0 ? (savingsPct >= 0 ? savingsPct + '% ($' + savingsWeek.toFixed(2) + ')' : '0% ($0)') : '—');
        setTxt('res-codex-week-tokens', weekFullM > 0 ? weekFullM.toFixed(1) + 'M' : '—');
        setTxt('res-codex-eff-actual', usedM > 0 ? '$' + effActual.toFixed(4) + '/1M' : '—');
        setTxt('res-codex-eff-full', monthTokensM > 0 ? '$' + effFull.toFixed(4) + '/1M' : '—');
      }

      // --- localStorage save/restore for calc-ref-cost only ---
      var STORAGE_KEY = 'session-stats-costos';

      function saveCalcState() {
        var el = document.getElementById('calc-ref-cost');
        if (!el || !el.id) return;
        var state = {};
        state[el.id] = el.value;
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch(e) {}
      }

      function restoreCalcState() {
        try {
          var raw = localStorage.getItem(STORAGE_KEY);
          if (!raw) return;
          var state = JSON.parse(raw);
          Object.keys(state).forEach(function(id) {
            if (id === 'calc-ref-cost') {
              var el = document.getElementById(id);
              if (el) el.value = state[id];
            }
          });
        } catch(e) {}
      }

      // Restore saved state BEFORE first calculation
      restoreCalcState();

      // When reference model changes
      if (refSelect) {
        refSelect.addEventListener('change', function() {
          var model = getRefModel();
          if (model) {
            // Auto-fill token fields
            document.getElementById('calc-codex-in').value = Math.round((model.input_tokens || 0) / 1e6);
            document.getElementById('calc-codex-out').value = Math.round((model.output_tokens || 0) / 1e6);
            document.getElementById('calc-codex-cache').value = Math.round((model.cache_tokens || 0) / 1e6);
            // Set reference cost from model's subscription price
            if (refCostInput && model.cost_sub != null) {
              refCostInput.value = model.cost_sub;
            }
          }
          recalcAll();
          });
      }

      // When reference cost is manually edited — solo localStorage
      if (refCostInput) {
        refCostInput.addEventListener('input', function() { recalcAll(); saveCalcState(); });
      }

      // Guardar button: persiste calc-ref-cost en el backend
      var saveBtn = document.getElementById('save-cost-btn');
      var saveBadge = document.getElementById('save-badge');
      if (saveBtn) {
        saveBtn.addEventListener('click', function() {
          var model = refSelect ? refSelect.value : '';
          var cost = parseFloat(refCostInput ? refCostInput.value : 0) || 0;
          if (!model) { alert('Seleccioná un modelo de referencia primero.'); return; }
          fetch('/api/subscription-cost/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: model, cost_sub: cost })
          })
          .then(function(r) { return r.json(); })
          .then(function(data) {
            saveCalcState();
            if (data.success && saveBadge) {
              saveBadge.style.display = 'inline';
              setTimeout(function(){ saveBadge.style.display = 'none'; }, 3000);
            }
          })
          .catch(function(err) {
            console.error('Error saving cost:', err);
            alert('Error al guardar: ' + err.message);
          });
        });
      }

      // Wire up calculator inputs (plan cost and usage fields) — no auto-save
      var codexInputs = ['calc-codex-cost', 'calc-codex-pct', 'calc-codex-in', 'calc-codex-out', 'calc-codex-cache'];
      codexInputs.forEach(function(id) {
        var el = document.getElementById(id);
        if (el) el.addEventListener('input', function() { recalcAll(); });
      });

      // Wire up OCG inputs — no auto-save
      var ocgInputs = ['calc-ocg-cost', 'calc-ocg-credit'];
      ocgInputs.forEach(function(id) {
        var el = document.getElementById(id);
        if (el) el.addEventListener('input', function() { subApplyCalculator(); });
      });

      // Initial calculation
      recalcAll();

      // Wire up sort buttons
      var sortBtns = document.querySelectorAll('[data-sub-sort], [data-sub-sort-dir]');
      sortBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
          var field = btn.getAttribute('data-sub-sort');
          if (field) {
            subSortField = field;
            sortBtns.forEach(function(b) {
              if (b.getAttribute('data-sub-sort')) {
                b.removeAttribute('data-active');
                b.setAttribute('aria-pressed', 'false');
              }
            });
            btn.setAttribute('data-active', 'true');
            btn.setAttribute('aria-pressed', 'true');
          } else {
            // toggle direction button
            subSortDir = subSortDir === 1 ? -1 : 1;
            btn.textContent = subSortDir === 1 ? '↑' : '↓';
            var allDir = document.querySelectorAll('[data-sub-sort-dir]');
            allDir.forEach(function(d) {
              d.setAttribute('data-active', 'true');
              d.setAttribute('aria-pressed', 'true');
            });
          }
          subRenderTable();
        });
      });
    })
    .catch(function(err) {
      console.error('subscription-estimate error:', err);
      if (subTbody) subTbody.innerHTML = '<tr><td colspan="8" class="loading-row">Error al cargar</td></tr>';
    });
}

})();
