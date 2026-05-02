/* csmakeci-ui client utilities */

// ⌘K / Ctrl+K focuses search
document.addEventListener('keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    const root = document.getElementById('cm-root');
    if (root) {
      const data = root._x_dataStack?.[0];
      if (data) {
        data.searchOpen = true;
        setTimeout(() => {
          const inp = document.querySelector('[x-ref="searchInput"]');
          if (inp) inp.focus();
        }, 50);
      }
    }
  }
});
