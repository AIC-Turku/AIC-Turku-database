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
