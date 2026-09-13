/* Progressive enhancement only: inventory facts and warnings come from the validated view. */
(function () {
  'use strict';
  function init() {
    const root = document.getElementById('objective-pool');
    if (!root || root.dataset.initialized) return;
    root.dataset.initialized = 'true';
    const list = root.querySelector('#pool-items');
    const items = Array.from(list.querySelectorAll('.pool-item'));
    const search = root.querySelector('#pool-search');
    const filters = Array.from(root.querySelectorAll('[data-pool-filter]'));
    const sort = root.querySelector('#pool-sort');
    const normal = value => String(value).normalize('NFKC').toLowerCase()
      .replace(/[\u2010-\u2015]/g, '-').replace(/\u00d7/g, 'x').replace(/(\d),(\d)/g, '$1.$2');
    function apply() {
      const tokens = normal(search.value).trim().split(/\s+/).filter(Boolean);
      let count = 0;
      items.forEach(item => {
        const text = normal(item.dataset.search);
        const matches = tokens.every(token => text.includes(token) || text.replace(/\s/g, '').includes(token)) &&
          filters.every(filter => !filter.value || item.getAttribute('data-' + filter.dataset.poolFilter) === filter.value);
        item.hidden = !matches;
        if (matches) count += 1;
      });
      items.slice().sort((a, b) => {
        if (sort.value === 'source') return Number(a.dataset.order) - Number(b.dataset.order);
        const am = a.dataset.magnification;
        const bm = b.dataset.magnification;
        if (!am || !bm) return !am && !bm ? 0 : (!am ? 1 : -1);
        return (Number(am) - Number(bm)) * (sort.value === 'mag-desc' ? -1 : 1);
      }).forEach(item => list.appendChild(item));
      root.querySelector('#pool-count').textContent = `Showing ${count} of ${items.length} records.`;
      root.querySelector('#pool-no-results').hidden = count !== 0;
    }
    function reset() {
      search.value = '';
      filters.forEach(filter => { filter.value = ''; });
      sort.value = 'source';
      apply();
    }
    root.querySelectorAll('[data-pool-reset]').forEach(button => button.addEventListener('click', reset));
    search.addEventListener('input', apply);
    filters.forEach(filter => filter.addEventListener('change', apply));
    sort.addEventListener('change', apply);
    root.querySelectorAll('[data-copy-enquiry]').forEach(button => {
      button.hidden = false;
      button.addEventListener('click', async () => {
        const details = button.closest('details');
        const textarea = details.querySelector('textarea');
        const feedback = details.querySelector('.pool-feedback');
        button.disabled = true;
        try {
          if (!navigator.clipboard || !navigator.clipboard.writeText) throw new Error('Clipboard unavailable');
          await navigator.clipboard.writeText(textarea.value);
          feedback.textContent = 'Enquiry copied. Add your microscope and experiment details before sending.';
        } catch (error) {
          textarea.focus();
          textarea.select();
          feedback.textContent = 'Automatic copying is unavailable. The enquiry is selected; copy it manually.';
        } finally {
          button.disabled = false;
        }
      });
    });
    function revealLinkedRecord() {
      let id;
      try { id = decodeURIComponent(window.location.hash.slice(1)); } catch (error) { return; }
      const item = items.find(row => row.id === id);
      if (!item) return;
      if (item.hidden) reset();
      item.querySelector('details').open = true;
      item.scrollIntoView({ block: 'start' });
    }
    window.addEventListener('hashchange', revealLinkedRecord);
    root.querySelector('#pool-controls').hidden = false;
    apply();
    revealLinkedRecord();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
