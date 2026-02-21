// Shared dashboard utilities (kept intentionally small).
// Fleet filtering is implemented inline on index.md for maximum portability.

// Prevent "#" links in cards from stealing focus on click in some browsers.
document.addEventListener('click', (e) => {
  const a = e.target.closest('a');
  if (!a) return;
  // allow normal navigation
});
