(() => {
  const sheet = document.getElementById('study-sheet');
  const answers = document.querySelector('.sheet-answers');
  let answersWereOpen = false;
  function preparePrint() {
    answersWereOpen = answers.open;
    answers.open = true;
    sheet.style.setProperty('--sheet-print-scale', '1');
    // Print styles are active during beforeprint. Fit the actual content, not a fixed crop.
    const availableHeight = 276 * 96 / 25.4;
    const scale = Math.min(1, availableHeight / sheet.scrollHeight);
    sheet.style.setProperty('--sheet-print-scale', String(scale));
  }
  window.addEventListener('beforeprint', preparePrint);
  window.addEventListener('afterprint', () => {
    answers.open = answersWereOpen;
    sheet.style.removeProperty('--sheet-print-scale');
  });
  document.getElementById('sheet-print').addEventListener('click', async () => {
    await document.fonts.ready;
    await Promise.all(Array.from(document.images, image => image.decode().catch(() => {})));
    window.print();
  });
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
