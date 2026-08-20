const searchInput = document.querySelector('#globalSearchInput');
const searchResults = document.querySelector('#globalSearchResults');
let searchTimer;
const searchEscape = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);

function renderSearchResults(results) {
  const getIcon = (kind) => {
    if (kind === 'Task') return '&#128197;';
    if (kind === 'Note') return '&#128196;';
    return '&#128226;';
  };
  searchResults.innerHTML = results.length ? results.map((result) => `<a class="search-result" href="${result.url}"><span class="search-result-icon">${getIcon(result.kind)}</span><span><strong>${searchEscape(result.title)}</strong><small>${searchEscape(result.kind)} - ${searchEscape(result.meta || '')}</small></span><time>${new Date(result.created_at).toLocaleDateString()}</time></a>`).join('') : '<p class="search-empty">No matches found.</p>';
  searchResults.hidden = false;
}

searchInput.oninput = () => {
  clearTimeout(searchTimer);
  const term = searchInput.value.trim();
  if (!term) { searchResults.hidden = true; searchResults.innerHTML = ''; return; }
  searchTimer = setTimeout(async () => {
    const response = await fetch(`/api/search?q=${encodeURIComponent(term)}`);
    const data = await response.json();
    renderSearchResults(data.results || []);
  }, 180);
};

document.addEventListener('click', (event) => {
  if (!event.target.closest('.global-search')) searchResults.hidden = true;
});
