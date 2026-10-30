/* Refresh only dashboard lists; modal forms and their event handlers stay mounted. */
(() => {
  const status = document.getElementById('admin-refresh-status');
  if (!status) return;
  let busy = false;
  let lastInteraction = 0;
  let submitting = false;
  ['input', 'click', 'keydown'].forEach(event => document.addEventListener(event, () => {
    lastInteraction = Date.now();
  }, true));
  document.addEventListener('submit', () => { submitting = true; }, true);
  window.addEventListener('pageshow', () => { submitting = false; });
  function paused() {
    return document.hidden || submitting || Date.now() - lastInteraction < 2500 ||
      document.activeElement?.matches('input, textarea, select, [contenteditable="true"]') ||
      Array.from(document.querySelectorAll('.modal-overlay')).some(el =>
        getComputedStyle(el).display !== 'none');
  }
  async function refresh() {
    if (busy) return;
    if (paused()) {
      status.textContent = status.dataset.paused;
      return;
    }
    busy = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    const interactionAtStart = lastInteraction;
    try {
      const response = await fetch(window.location.href, {
        credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
      });
      if (!response.ok || response.redirected) throw new Error('Dashboard unavailable');
      const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
      const payload = doc.getElementById('admin-dashboard-data');
      const incoming = Array.from(doc.querySelectorAll('.admin-section'));
      const current = Array.from(document.querySelectorAll('.admin-section'));
      if (!payload || incoming.length !== current.length || !incoming.length) throw new Error('Invalid dashboard');
      const data = JSON.parse(payload.textContent);
      if (!data.user_matches || !data.match_notes || !data.student_notes || !data.match_feedback) throw new Error('Invalid data');
      // The user may have started editing while the request was in flight.
      if (paused() || lastInteraction !== interactionAtStart) return;
      const search = document.getElementById('user-search').value;
      const expandedMatches = Array.from(document.querySelectorAll('.older-match')).some(row => row.style.display !== 'none');
      const filterButtons = ['star-filter-btn', 'language-tutor-filter-btn'].map(id => {
        const button = document.getElementById(id);
        return [id, button.style.cssText, button.textContent];
      });
      const position = [window.scrollX, window.scrollY];
      incoming.forEach((section, index) => current[index].replaceWith(document.importNode(section, true)));
      USER_MATCHES = data.user_matches;
      MATCH_NOTES = data.match_notes;
      STUDENT_NOTES = data.student_notes;
      MATCH_FEEDBACK = data.match_feedback;
      document.getElementById('user-search').value = search;
      filterButtons.forEach(([id, style, text]) => {
        const button = document.getElementById(id);
        button.style.cssText = style;
        button.textContent = text;
      });
      const usersButton = document.getElementById('toggle-older-users-btn');
      if (olderUsersExpanded && usersButton) usersButton.textContent = 'Show less';
      applyUserFilters();
      if (expandedMatches) {
        document.querySelectorAll('.older-match').forEach(row => { row.style.display = ''; });
        const button = document.querySelector('[onclick="toggleOlderMatches(this)"]');
        if (button) button.textContent = 'Hide older';
      }
      window.scrollTo(...position);
      status.textContent = status.dataset.ready + ' · ' + new Date().toLocaleTimeString();
    } catch (error) {
      status.textContent = status.dataset.failed;
    } finally {
      clearTimeout(timeout);
      busy = false;
    }
  }
  setInterval(refresh, 20000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
})();
