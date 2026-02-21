(function () {
  // Chart.js is loaded via mkdocs extra_javascript.
  // This renderer looks for <div class="aic-charts" data-aic-charts='{"metric":{...}}'>

  function cssVar(name, fallback) {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name);
    return (v && v.trim()) ? v.trim() : fallback;
  }

  function parseJsonAttr(el, attrName, fallback) {
    const raw = el.getAttribute(attrName);
    if (!raw) return fallback;
    try {
      return JSON.parse(raw);
    } catch (e) {
      console.warn('[AIC] Failed to parse', attrName, e);
      return fallback;
    }
  }

  function getThemeColors() {
    return {
      primary: cssVar('--md-primary-fg-color', 'rgba(75,192,192,1)'),
      text: cssVar('--md-default-fg-color', '#111'),
      grid: cssVar('--md-default-fg-color--lightest', 'rgba(0,0,0,.08)'),
      bg: cssVar('--md-default-bg-color', '#fff')
    };
  }

  function buildChart(container, metricId, chartData, metricNames, colors) {
    const wrapper = document.createElement('div');
    wrapper.className = 'aic-chart';

    const title = document.createElement('div');
    title.className = 'aic-chart__title';
    title.textContent = (metricNames && metricNames[metricId]) ? metricNames[metricId] : metricId;
    wrapper.appendChild(title);

    const canvas = document.createElement('canvas');
    wrapper.appendChild(canvas);
    container.appendChild(wrapper);

    const ctx = canvas.getContext('2d');

    // Use a minimal dataset config and apply theme colors at runtime.
    const data = {
      labels: chartData.labels || [],
      datasets: [
        {
          label: metricId,
          data: chartData.values || [],
          borderColor: colors.primary,
          backgroundColor: colors.primary,
          tension: 0.2,
          spanGaps: true,
          pointRadius: 3,
        }
      ]
    };

    const options = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { mode: 'index', intersect: false },
      },
      scales: {
        x: {
          grid: { color: colors.grid },
          ticks: { color: colors.text, maxRotation: 0 },
        },
        y: {
          grid: { color: colors.grid },
          ticks: { color: colors.text },
        },
      },
      interaction: { mode: 'index', intersect: false },
    };

    // Fix height for consistent grid; users can scroll.
    wrapper.style.height = '260px';

    return new Chart(ctx, { type: 'line', data, options });
  }

  function renderAll() {
    if (!window.Chart) return;

    const containers = document.querySelectorAll('.aic-charts[data-aic-charts]');
    if (!containers.length) return;

    window.__aicCharts = window.__aicCharts || [];

    // Clear any existing charts (for theme re-render)
    window.__aicCharts.forEach((c) => {
      try { c.destroy(); } catch (_) {}
    });
    window.__aicCharts = [];

    const colors = getThemeColors();

    containers.forEach((container) => {
      container.innerHTML = '';

      const charts = parseJsonAttr(container, 'data-aic-charts', {});
      const metricNames = parseJsonAttr(container, 'data-aic-metric-names', {});

      const metricIds = Object.keys(charts || {}).sort();
      metricIds.forEach((metricId) => {
        const chartData = charts[metricId];
        if (!chartData || !Array.isArray(chartData.labels) || !Array.isArray(chartData.values)) return;
        // Only render if at least one numeric value exists.
        if (!chartData.values.some(v => typeof v === 'number')) return;
        const chart = buildChart(container, metricId, chartData, metricNames, colors);
        window.__aicCharts.push(chart);
      });
    });
  }

  function observeThemeChanges() {
    const target = document.body;
    if (!target) return;

    const obs = new MutationObserver((mutations) => {
      for (const m of mutations) {
        if (m.type === 'attributes' && m.attributeName === 'data-md-color-scheme') {
          renderAll();
          break;
        }
      }
    });

    obs.observe(target, { attributes: true });
  }

  document.addEventListener('DOMContentLoaded', function () {
    renderAll();
    observeThemeChanges();
  });
})();
