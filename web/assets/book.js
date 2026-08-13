(() => {
  const root = document.documentElement;
  const body = document.body;
  const base = body.dataset.base || '';
  const themeButton = document.querySelector('[data-theme-toggle]');
  const menuButton = document.querySelector('[data-menu-toggle]');
  const scrim = document.querySelector('.sidebar-scrim');
  const progress = document.querySelector('.reading-progress');
  const searchDialog = document.querySelector('#search-dialog');
  const searchInput = document.querySelector('#search-input');
  const searchResults = document.querySelector('#search-results');
  let searchIndex = null;

  const savedTheme = localStorage.getItem('notes-theme');
  if (savedTheme) root.dataset.theme = savedTheme;
  const updateThemeLabel = () => {
    if (!themeButton) return;
    const dark = root.dataset.theme === 'dark';
    themeButton.setAttribute('aria-label', dark ? 'Use light theme' : 'Use dark theme');
    themeButton.textContent = dark ? '☀' : '◐';
  };
  updateThemeLabel();
  themeButton?.addEventListener('click', () => {
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('notes-theme', root.dataset.theme);
    updateThemeLabel();
  });

  const closeSidebar = () => body.classList.remove('sidebar-open');
  menuButton?.addEventListener('click', () => body.classList.toggle('sidebar-open'));
  scrim?.addEventListener('click', closeSidebar);
  document.querySelectorAll('.book-sidebar a').forEach(link => link.addEventListener('click', closeSidebar));

  const updateProgress = () => {
    if (!progress) return;
    const max = document.documentElement.scrollHeight - window.innerHeight;
    progress.style.width = `${max > 0 ? Math.min(100, window.scrollY / max * 100) : 0}%`;
  };
  addEventListener('scroll', updateProgress, { passive: true });
  updateProgress();

  const tocLinks = [...document.querySelectorAll('.on-this-page a')];
  if (tocLinks.length) {
    const headings = tocLinks.map(a => document.getElementById(a.hash.slice(1))).filter(Boolean);
    const observer = new IntersectionObserver(entries => {
      const visible = entries.filter(e => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (!visible) return;
      tocLinks.forEach(a => a.classList.toggle('active', a.hash === `#${visible.target.id}`));
    }, { rootMargin: '-80px 0px -72% 0px' });
    headings.forEach(h => observer.observe(h));
  }

  const escapeHtml = text => text.replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const highlight = (text, query) => {
    const safe = escapeHtml(text);
    if (!query) return safe;
    return safe.replace(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'ig'), '<mark>$1</mark>');
  };
  const openSearch = async () => {
    if (!searchDialog) return;
    searchDialog.showModal();
    searchInput.focus();
    if (!searchIndex) {
      try { searchIndex = await fetch(`${base}search-index.json`).then(r => r.json()); }
      catch { searchResults.innerHTML = '<div class="search-empty">Search index is unavailable.</div>'; }
    }
  };
  document.querySelectorAll('[data-search-open]').forEach(el => el.addEventListener('click', openSearch));
  searchDialog?.addEventListener('click', e => {
    if (e.target === searchDialog) searchDialog.close();
  });
  searchInput?.addEventListener('input', () => {
    const q = searchInput.value.trim().toLowerCase();
    if (!q || !searchIndex) {
      searchResults.innerHTML = '<div class="search-empty">Search definitions, theorems, and topics across the notes.</div>';
      return;
    }
    const words = q.split(/\s+/).filter(Boolean);
    const scored = searchIndex.map(item => {
      const title = item.title.toLowerCase();
      const text = item.text.toLowerCase();
      let score = words.reduce((s, word) => s + (title.includes(word) ? 8 : 0) + (text.includes(word) ? 1 : -20), 0);
      return { ...item, score };
    }).filter(item => item.score >= 0).sort((a, b) => b.score - a.score).slice(0, 18);
    if (!scored.length) {
      searchResults.innerHTML = `<div class="search-empty">No results for “${escapeHtml(searchInput.value)}”.</div>`;
      return;
    }
    searchResults.innerHTML = scored.map(item => {
      const lower = item.text.toLowerCase();
      const pos = Math.max(0, lower.indexOf(words[0]) - 70);
      const snippet = `${pos ? '…' : ''}${item.text.slice(pos, pos + 230)}${pos + 230 < item.text.length ? '…' : ''}`;
      return `<a class="search-result" href="${base}${item.url}"><div class="search-result-title">${highlight(item.title, q)}</div><div class="search-result-snippet">${highlight(snippet, q)}</div></a>`;
    }).join('');
  });

  document.addEventListener('keydown', event => {
    if (event.key === '/' && !/input|textarea/i.test(document.activeElement.tagName)) {
      event.preventDefault(); openSearch();
    }
    if (event.key === 'Escape') closeSidebar();
    if (event.key === '[' && body.dataset.prev) location.href = body.dataset.prev;
    if (event.key === ']' && body.dataset.next) location.href = body.dataset.next;
  });

  const active = document.querySelector('.book-sidebar .nav-link.active');
  active?.scrollIntoView({ block: 'center' });
})();
