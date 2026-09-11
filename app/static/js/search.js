const searchInput = document.querySelector('#globalSearchInput');
const searchResults = document.querySelector('#globalSearchResults');
const searchResultList = document.querySelector('#searchResultList');
const searchForm = document.querySelector('#globalSearchForm');
let searchKind = '';
let searchTimer;
const searchEscape = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);

function renderSearchResults(results) {
  const getIcon = (kind) => {
    if (kind === 'Task') return '&#128197;';
    if (kind === 'Note') return '&#128196;';
    return '&#128226;';
  };
  searchResultList.innerHTML = results.length ? results.map((result) => `<a class="search-result" href="${searchEscape(result.url)}"><span class="search-result-icon">${getIcon(result.kind)}</span><span><strong>${searchEscape(result.title)}</strong><small>${searchEscape(result.kind)} - ${searchEscape(result.meta || '')}</small><em>${searchEscape(result.snippet || result.detail || '')}</em></span><time>${new Date(result.created_at).toLocaleDateString()}</time></a>`).join('') : '<p class="search-empty">No matches found.</p>';
  searchResults.hidden = false;
  searchInput.setAttribute('aria-expanded', 'true');
}

async function runSearch() {
  const term = searchInput.value.trim();
  if (!term) return;
  searchResultList.innerHTML = '<p class="search-empty">Searching...</p>';
  searchResults.hidden = false;
  const response = await fetch(`/api/search?q=${encodeURIComponent(term)}&kind=${encodeURIComponent(searchKind)}`);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Search failed');
  renderSearchResults(data.results || []);
}

searchInput.oninput = () => {
  clearTimeout(searchTimer);
  const term = searchInput.value.trim();
  if (!term) { searchResults.hidden = true; searchResultList.innerHTML = ''; searchInput.setAttribute('aria-expanded', 'false'); return; }
  searchTimer = setTimeout(() => runSearch().catch(() => { searchResultList.innerHTML = '<p class="search-empty">Search is unavailable.</p>'; }), 180);
};

searchForm.onsubmit = (event) => { event.preventDefault(); clearTimeout(searchTimer); runSearch().catch(() => { searchResultList.innerHTML = '<p class="search-empty">Search is unavailable.</p>'; }); };
document.querySelectorAll('[data-search-kind]').forEach((chip) => chip.onclick = () => { searchKind = chip.dataset.searchKind; document.querySelectorAll('[data-search-kind]').forEach((item) => item.classList.toggle('active', item === chip)); runSearch().catch(() => {}); });
document.querySelector('#closeSearch').onclick = () => { searchResults.hidden = true; searchInput.setAttribute('aria-expanded', 'false'); searchInput.focus(); };
searchInput.onkeydown = (event) => { if (event.key === 'Escape') document.querySelector('#closeSearch').click(); };

document.addEventListener('click', (event) => {
  if (!event.target.closest('.global-search')) { searchResults.hidden = true; searchInput.setAttribute('aria-expanded', 'false'); }
});
