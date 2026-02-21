(function () {
  function norm(s) {
    return (s || "").toString().toLowerCase().trim();
  }

  function applyFleetFilters() {
    const searchEl = document.getElementById('aicSearch');
    const modalityEl = document.getElementById('aicModality');
    const statusEl = document.getElementById('aicStatus');
    if (!searchEl || !modalityEl || !statusEl) return;

    const q = norm(searchEl.value);
    const modality = norm(modalityEl.value);
    const status = norm(statusEl.value);

    const cards = document.querySelectorAll('.aic-card[data-filterable="true"]');
    cards.forEach((card) => {
      const name = norm(card.getAttribute('data-name'));
      const manufacturer = norm(card.getAttribute('data-manufacturer'));
      const modalities = norm(card.getAttribute('data-modalities'));
      const cardStatus = norm(card.getAttribute('data-status'));

      const matchesSearch = !q || name.includes(q) || manufacturer.includes(q) || modalities.includes(q);
      const matchesModality = modality === 'all' || modalities.split(',').map(norm).includes(modality);
      const matchesStatus = status === 'all' || cardStatus === status;

      card.style.display = (matchesSearch && matchesModality && matchesStatus) ? '' : 'none';
    });
  }

  function initFleetFilters() {
    const searchEl = document.getElementById('aicSearch');
    const modalityEl = document.getElementById('aicModality');
    const statusEl = document.getElementById('aicStatus');
    const resetEl = document.getElementById('aicReset');
    if (!searchEl || !modalityEl || !statusEl) return;

    const handler = () => applyFleetFilters();
    searchEl.addEventListener('input', handler);
    modalityEl.addEventListener('change', handler);
    statusEl.addEventListener('change', handler);

    if (resetEl) {
      resetEl.addEventListener('click', () => {
        searchEl.value = '';
        modalityEl.value = 'all';
        statusEl.value = 'all';
        applyFleetFilters();
      });
    }

    applyFleetFilters();
  }

  document.addEventListener('DOMContentLoaded', initFleetFilters);
})();
