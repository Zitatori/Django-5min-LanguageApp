(() => {
  const form = document.getElementById('study-form');
  if (!form) return;
  let pending = false;
  const button = document.getElementById('study-generate');
  const loading = document.getElementById('study-loading');
  form.addEventListener('submit', event => {
    if (pending) { event.preventDefault(); return; }
    pending = true;
    button.disabled = true;
    loading.hidden = false;
    form.setAttribute('aria-busy', 'true');
  });
  window.addEventListener('pageshow', () => {
    pending = false;
    button.disabled = false;
    loading.hidden = true;
    form.removeAttribute('aria-busy');
  });
})();
