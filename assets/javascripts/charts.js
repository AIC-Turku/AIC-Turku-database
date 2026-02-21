(function () {
  // Chart.js is loaded via mkdocs extra_javascript.
  // This renderer looks for elements with data-aic-charts='{"metric":{...}}'

  function cssVar(name, fallback) {
    const v = getComputedStyle(document.body).getPropertyValue(name);
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
      // Prioritize the primary link color, fallback to default primary
      primary: cssVar('--md-typeset-a-color', cssVar('--md-primary-fg-color', '#4051b5')),
      text: cssVar('--md-default-fg-color', '#333'),
      grid: cssVar('--md-default-fg-color--lightest', 'rgba(0,0,0,0.1)'),
    };
  }

  function buildChart(container, metricId, chartData, metricNames, colors) {
    const wrapper = document.createElement('div');
    wrapper.className = 'aic-chartcard';

    const title = document.createElement('div');
    title.className = 'aic-chartcard__title';
    title.textContent = (metricNames && metricNames[metricId]) ? metricNames[metricId] : metricId;
    wrapper.appendChild(title);

    const canvasWrapper = document.createElement('div');
    canvasWrapper.className = 'aic-chartcard__canvas-wrapper';
    
    const canvas = document.createElement('canvas');
    canvasWrapper.appendChild(canvas);
    wrapper.appendChild(canvasWrapper);
    container.appendChild(wrapper);

    const ctx = canvas.getContext('2d');

    const data = {
      labels: chartData.labels || [],
      datasets: [
        {
          label: title.textContent,
          data: chartData.values || [],
          borderColor: colors.primary,
          backgroundColor: 'transparent',
          pointBackgroundColor: colors.primary,
          borderWidth: 2,
          pointRadius: 3,
          tension: 0.2,
          spanGaps: true
        }
      ]
    };

    const options = {
      responsive: true,
      maintainAspectRatio: false, // Relies on css wrapper to dictate dimensions
      plugins: {
        legend: { display: false },
        tooltip: { mode: 'index', intersect: false },
      },
      scales: {
        x: {
          grid: { color: colors.grid },
          ticks: { color: colors.text, maxRotation: 45 },
        },
        y: {
          grid: { color: colors.grid },
          ticks: { color: colors.text },
          beginAtZero: false
        },
      },
      interaction: { mode: 'index', intersect: false },
    };

    return new Chart(ctx, { type: 'line', data, options });
  }

  function renderAll() {
    if (!window.Chart) return;

    const containers = document.querySelectorAll('[data-aic-charts]');
    if (!containers.length) return;

    window.__aicCharts = window.__aicCharts || [];

    // Clear any existing charts (for theme re-render)
    window.__aicCharts.forEach((c) => {
      try { c.destroy(); } catch (_) {}
    });
    window.__aicCharts = [];

    const colors = getThemeColors();

    containers.forEach((container) => {
      // Clear DOM to prevent duplicates
      container.innerHTML = '';

      const charts = parseJsonAttr(container, 'data-aic-charts', {});
      const metricNames = parseJsonAttr(container, 'data-aic-metric-names', {});

      const metricIds = Object.keys(charts || {}).sort();

      if (metricIds.length === 0) {
        container.innerHTML = '<p class="aic-muted">No historical metrics available.</p>';
        return;
      }

      metricIds.forEach((metricId) => {
        const chartData = charts[metricId];
        if (!chartData || !Array.isArray(chartData.labels) || !Array.isArray(chartData.values)) return;
        
        // Only render if at least one numeric value exists
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
          // Slight delay to allow MkDocs CSS variables to fully apply to the DOM
          setTimeout(renderAll, 50);
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
