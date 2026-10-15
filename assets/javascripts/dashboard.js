// Shared dashboard utilities (kept intentionally small).
// Fleet filtering is implemented inline on index.md for maximum portability.

document.addEventListener('DOMContentLoaded', () => {
  // Prevent placeholder "#" links from jumping to the top of the page or stealing focus.
  document.addEventListener('click', (e) => {
    const a = e.target.closest('a');
    if (!a) return;
    
    // If it's a dummy anchor, stop the browser from scrolling to the top
    const href = a.getAttribute('href');
    if (href === '#') {
      e.preventDefault();
    }
  });
});

// Content tabs (pymdownx.tabbed) hide every panel but the active one, so a
// heading inside an inactive tab exists in the DOM but cannot be scrolled to.
// The sidebar table of contents lists all of them, so clicking an entry from a
// non-active tab did nothing. Activate the owning tab, then scroll to the target.
(function () {
  function revealTarget(id) {
    if (!id) return;
    var target = document.getElementById(id);
    if (!target) return;
    var panel = target.closest('.tabbed-block');
    if (!panel) return;
    var blocks = panel.parentElement;
    var set = blocks.parentElement;
    var index = Array.prototype.indexOf.call(blocks.children, panel);
    var input = set.querySelectorAll(':scope > input[type="radio"]')[index];
    if (input && !input.checked) {
      input.checked = true;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }
    target.scrollIntoView();
  }

  function fromHash() {
    var raw = window.location.hash.slice(1);
    if (!raw) return;
    try { revealTarget(decodeURIComponent(raw)); } catch (e) { revealTarget(raw); }
  }

  document.addEventListener('DOMContentLoaded', fromHash);
  window.addEventListener('hashchange', fromHash);
  // Clicking the link for the current hash does not fire hashchange.
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href^="#"]');
    if (!a || a.getAttribute('href') === '#') return;
    var id = a.getAttribute('href').slice(1);
    try { id = decodeURIComponent(id); } catch (err) { /* keep raw id */ }
    setTimeout(function () { revealTarget(id); }, 0);
  });
})();

// Vocabulary dictionary filter: hide table rows, then whole vocabularies and
// groups, that do not match. Matching is plain substring over the row text.
document.addEventListener('DOMContentLoaded', function () {
  var input = document.getElementById('vocab-filter');
  var root = document.querySelector('.vocab-dictionary');
  if (!input || !root) return;
  var status = document.getElementById('vocab-filter-status');
  var tables = Array.prototype.slice.call(root.querySelectorAll('table'));

  function sectionNodes(table) {
    // Heading, source lines and table form one vocabulary section.
    // Material wraps tables in scroll containers; climb to the direct child of root.
    var wrap = table;
    while (wrap.parentElement && wrap.parentElement !== root) wrap = wrap.parentElement;
    var nodes = [wrap];
    var prev = wrap.previousElementSibling;
    while (prev && !/^H[23]$/.test(prev.tagName)) { nodes.push(prev); prev = prev.previousElementSibling; }
    if (prev) nodes.push(prev);
    return nodes;
  }

  function apply() {
    var q = input.value.trim().toLowerCase();
    var shown = 0, total = 0;
    tables.forEach(function (table) {
      var rows = table.querySelectorAll('tbody tr');
      var any = false;
      rows.forEach(function (row) {
        total += 1;
        var hit = !q || row.textContent.toLowerCase().indexOf(q) !== -1;
        row.hidden = !hit;
        if (hit) { any = true; shown += 1; }
      });
      sectionNodes(table).forEach(function (n) { n.hidden = !any; });
    });
    root.querySelectorAll('h2[id^="group-"]').forEach(function (h) {
      var el = h.nextElementSibling, visible = false;
      while (el && !(el.tagName === 'H2')) {
        if (el.tagName === 'H3' && !el.hidden) visible = true;
        el = el.nextElementSibling;
      }
      h.hidden = !visible;
    });
    if (status) status.textContent = q ? shown + ' of ' + total + ' terms match' : '';
  }
  input.addEventListener('input', apply);
});
