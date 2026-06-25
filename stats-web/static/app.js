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
      var totalTokens = d.total_input_tokens + d.total_output_tokens + d.total_cache_tokens;
      document.querySelector('[data-stat="total-cost"]').textContent = fmtCost(d.total_cost);
      document.querySelector('[data-stat="total-tokens"]').textContent = fmt(totalTokens);
      document.querySelector('[data-stat="total-sessions"]').textContent = fmt(d.total_sessions);
      document.querySelector('[data-stat="cache-ratio"]').textContent = fmtPct(d.cache_ratio);
      document.querySelector('[data-stat="total-requests"]').textContent = fmt(d.total_requests);
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
        row.innerHTML =
          '<span class="today-model-rank">' + String(i + 1).padStart(2, '0') + '</span>' +
          '<span class="today-model-name">' + m.model + '</span>' +
          '<div class="today-model-bar"><div class="today-model-bar-fill" style="width:' + barPct + '%"></div></div>' +
          '<span class="today-model-reqs">' + fmt(m.requests) + ' req</span>' +
          '<span class="today-model-cost">' + fmtCost(m.cost) + '</span>' +
          '<span class="today-model-tokens">' + fmtTokens(m.tokens) + '</span>' +
          '<span class="today-model-pct">' + barPct + '%</span>';
        todayModels.appendChild(row);
      });
    })
    .catch(function(err) { console.error('today-summary error:', err); });

  // --- Top Models (12 meses semanal, colores por modelo) ---
  var topChart = document.getElementById('top-models-chart');
  var topBars = document.getElementById('top-bars');
  var topAxis = document.getElementById('top-axis');
  var leaderboardEl = document.getElementById('leaderboard');
  var activeModel = '';

  // 20 colores distinguibles para los top 20 modelos
  var MODEL_COLORS = ['#ff8904','#ffb900','#00bc7d','#00d3f2','#51a2ff','#7c86ff','#ed6aff','#ff5e5e','#9ae600','#c77dff','#ffd23f','#00d5be','#a684ff','#f15bb5','#7fb069','#ff073a','#0eb7c0','#b8d12a','#ff6b9d','#8b5cf6'];
  var GRAY = '#808080';

  // Mapa modelo → color (se llena desde topModels del API)
  var modelColorMap = {};

  function getModelColor(model) {
    return modelColorMap[model] || GRAY;
  }

  function syncHighlightState() {
    if (!topBars) return;
    topBars.querySelectorAll('.top-models-stack i').forEach(function(seg) {
      var matches = !activeModel || seg.getAttribute('data-model') === activeModel;
      seg.setAttribute('data-dimmed', matches ? 'false' : 'true');
    });
    if (!leaderboardEl) return;
    leaderboardEl.querySelectorAll('.leader-card').forEach(function(card) {
      var selected = activeModel && card.getAttribute('data-model') === activeModel;
      card.setAttribute('data-selected', selected ? 'true' : 'false');
      card.setAttribute('data-dimmed', activeModel && !selected ? 'true' : 'false');
    });
  }

  function fmtTokens(n) {
    if (n >= 1e12) return (n / 1e12).toFixed(n >= 1e13 ? 0 : 1) + 'T';
    if (n >= 1e9)  return (n / 1e9).toFixed(n >= 1e10 ? 0 : 1) + 'B';
    if (n >= 1e6)  return (n / 1e6).toFixed(1) + 'M';
    if (n >= 1e3)  return (n / 1e3).toFixed(1) + 'K';
    return String(n);
  }

  function isColumnLabelHidden(i, count) {
    // Mostrar ~8 labels para 52 semanas
    if (count <= 14) return false;
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

  function buildBar(barEl, week, weekIndex, maxTotal, totalWeeks) {
    var total = 0;
    (week.segments || []).forEach(function(s) { total += s.value; });

    barEl.setAttribute('data-slot', 'top-models-bar');
    barEl.className = 'top-models-bar';
    barEl.setAttribute('role', 'button');
    barEl.setAttribute('tabindex', '0');
    barEl.setAttribute('aria-label', week.date + ': ' + fmtTokens(total) + ' tokens');
    barEl.style.setProperty('--bar-height', getBarHeight(total, maxTotal) + '%');

    if (total === 0) return;

    var stack = document.createElement('div');
    stack.setAttribute('data-slot', 'top-models-stack');
    stack.className = 'top-models-stack';

    var visible = week.segments.filter(function(s) { return s.value > 0; });
    var sorted = visible.slice().sort(function(a, b) { return b.value - a.value; });
    stack.style.gridTemplateRows = sorted.map(function(s) {
      return (s.value / total * 100).toFixed(3) + '%';
    }).join(' ');

    sorted.forEach(function(s) {
      var el = document.createElement('i');
      el.setAttribute('data-model', s.model);
      el.setAttribute('title', s.model);
      el.style.background = getModelColor(s.model);
      stack.appendChild(el);
    });

    barEl.appendChild(stack);

    // Tooltip
    var tip = document.createElement('div');
    tip.setAttribute('data-component', 'chart-tooltip');
    tip.className = 'chart-tooltip';
    var threshold = totalWeeks - Math.max(4, Math.floor(totalWeeks * 0.4));
    tip.setAttribute('data-placement', weekIndex >= threshold ? 'left' : 'right');

    var strong = document.createElement('strong');
    strong.textContent = week.date;
    tip.appendChild(strong);

    var sub = document.createElement('span');
    sub.textContent = fmtTokens(total) + ' total';
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
      nameSpan.textContent = s.model;
      label.appendChild(nameSpan);
      p.appendChild(label);
      var b = document.createElement('b');
      b.textContent = fmtTokens(s.value);
      p.appendChild(b);
      tip.appendChild(p);
    });

    barEl.appendChild(tip);
  }

  function buildLeaderCard(entry) {
    var card = document.createElement('div');
    card.className = 'leader-card';
    card.setAttribute('data-model', entry.model);
    card.setAttribute('role', 'listitem');

    var rank = document.createElement('span');
    rank.className = 'leader-rank';
    rank.textContent = String(entry.rank).padStart(2, '0');
    card.appendChild(rank);

    var body = document.createElement('div');
    body.className = 'leader-body';

    var name = document.createElement('span');
    name.className = 'leader-name';
    name.textContent = entry.model;
    body.appendChild(name);

    var meta = document.createElement('span');
    meta.className = 'leader-meta';
    meta.textContent = entry.author;
    body.appendChild(meta);

    var tokens = document.createElement('span');
    tokens.className = 'leader-tokens';
    tokens.textContent = fmtTokens(entry.tokens);
    body.appendChild(tokens);

    card.appendChild(body);

    var pct = document.createElement('span');
    pct.className = 'leader-percent';
    pct.textContent = entry.percent.toFixed(1) + '%';
    card.appendChild(pct);

    card.addEventListener('click', function() {
      activeModel = activeModel === entry.model ? '' : entry.model;
      syncHighlightState();
    });

    return card;
  }

  function renderLeaderboard(entries) {
    if (!leaderboardEl) return;
    leaderboardEl.innerHTML = '';
    if (!entries || entries.length === 0) return;
    entries.forEach(function(e) {
      leaderboardEl.appendChild(buildLeaderCard(e));
    });
  }

  function loadTopModels() {
    if (!topBars) return;
    fetch('/api/top-models')
      .then(function(r) { return r.json(); })
      .then(function(data) {
        var points = (data.usage && data.usage['All Users'] && data.usage['All Users']['12M']) || [];
        var leaders = data.leaderboard || [];
        var topModels = data.topModels || [];

        // Asignar colores a los top 20 modelos
        topModels.forEach(function(m, i) {
          modelColorMap[m] = MODEL_COLORS[i % MODEL_COLORS.length];
        });

        if (topChart) {
          topChart.setAttribute('data-range', '12M');
        }

        var maxTotal = getMaxTotal(points);
        var totalWeeks = points.length;

        // Axis: solo fechas, sin totales
        topAxis.innerHTML = '';
        points.forEach(function(p, i) {
          var cell = document.createElement('div');
          if (isColumnLabelHidden(i, totalWeeks)) {
            cell.setAttribute('data-label-hidden', 'true');
          }
          var label = document.createElement('span');
          label.className = 'axis-label';
          var dateSpan = document.createElement('span');
          dateSpan.className = 'axis-date';
          dateSpan.textContent = p.date;
          label.appendChild(dateSpan);
          cell.appendChild(label);
          topAxis.appendChild(cell);
        });

        // Bars: una por semana
        topBars.innerHTML = '';
        points.forEach(function(p, i) {
          var bar = document.createElement('div');
          buildBar(bar, p, i, maxTotal, totalWeeks);
          topBars.appendChild(bar);
        });

        // Leaderboard all-time
        renderLeaderboard(leaders);
        syncHighlightState();

        // Y-axis: scale in 100M increments
        var yAxis = document.getElementById('top-y-axis');
        if (yAxis) {
          yAxis.innerHTML = '';
          var maxVal = maxTotal;
          if (maxVal > 0) {
            var step = 100000000;
            var top = Math.ceil(maxVal / step) * step;
            var labels = [];
            for (var v = 0; v <= top; v += step) {
              labels.push(v);
            }
            labels.forEach(function(v) {
              var el = document.createElement('div');
              el.className = 'top-y-axis-label';
              el.textContent = fmtTokens(v);
              yAxis.appendChild(el);
            });
          }
        }
      })
      .catch(function(err) { console.error('top-models error:', err); });
  }

  loadTopModels();

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
    tbody.innerHTML = '<tr><td colspan="8" class="loading-row">Cargando...</td></tr>';
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
          tbody.innerHTML = '<tr><td colspan="8" class="loading-row">Sin resultados</td></tr>';
          return;
        }

        data.sessions.forEach(function(s) {
          var tr = document.createElement('tr');
          var totalT = (s.input_tokens || 0) + (s.output_tokens || 0) + (s.cache_tokens || 0);
          tr.innerHTML =
            '<td title="' + (s.id || '') + '">' + (s.id ? s.id.slice(0, 24) + '...' : '—') + '</td>' +
            '<td>' + (s.date || '—') + '</td>' +
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
        tbody.innerHTML = '<tr><td colspan="8" class="loading-row">Error al cargar</td></tr>';
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

})();
