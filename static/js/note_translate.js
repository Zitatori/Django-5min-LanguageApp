(() => {
  document.querySelectorAll('.sheet-translate').forEach(form => {
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const button = form.querySelector('button');
      if (button.disabled) return;
      button.disabled = true;
      const status = form.querySelector('.translation-status');
      status.textContent = status.dataset.loading;
      try {
        const response = await fetch(form.action, {method:'POST',body:new FormData(form),credentials:'same-origin'});
        if (!response.ok || response.redirected) throw new Error();
        // Read the saved, fingerprint-checked translation through the owner-scoped view.
        window.location.reload();
      } catch (_) {
        status.textContent = status.dataset.error;
        button.disabled = false;
      }
    });
  });
})();
