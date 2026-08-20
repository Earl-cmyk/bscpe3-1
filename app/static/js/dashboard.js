const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
const money = (value) => `PHP ${Number(value).toFixed(2)}`;

function announcementMarkup(announcement) {
  const options = (announcement.options || []).map((option) => `<button class="poll-option" data-announcement="${announcement.id}" data-option="${option.id}"><span>${escapeHtml(option.label)}</span><strong>${option.votes}</strong></button>`).join('');
  const attachment = announcement.attachment_path ? `<a class="text-link icon-action" href="/uploads/${encodeURIComponent(announcement.attachment_path)}" target="_blank" rel="noreferrer" aria-label="Open attachment" title="Open attachment">&#128206;</a>` : '';
  const link = announcement.link_url ? `<a class="text-link icon-action" href="${escapeHtml(announcement.link_url)}" target="_blank" rel="noreferrer" aria-label="Open link" title="Open link">&#128279;</a>` : '';
  return `<article class="announcement-item"><div class="announcement-meta"><span>${new Date(announcement.created_at).toLocaleDateString()}</span>${link}${attachment}</div><h3>${escapeHtml(announcement.title)}</h3><p>${escapeHtml(announcement.body)}</p>${options ? `<div class="poll-options">${options}</div>` : ''}</article>`;
}

function renderDashboard(data) {
  $('#dashboardBalance').textContent = money(data.balance);
  $('#announcementFeed').innerHTML = data.announcements.length ? data.announcements.map(announcementMarkup).join('') : '<p class="muted">No announcements yet.</p>';
  $('#upcomingDeadlines').innerHTML = data.deadlines.length ? data.deadlines.map((task) => `<div class="deadline-item"><time>${new Date(task.deadline).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</time><span><strong>${escapeHtml(task.title)}</strong><small>${escapeHtml(task.course)}</small></span></div>`).join('') : '<p class="muted">No upcoming deadlines.</p>';
}

async function loadDashboard() {
  const response = await fetch('/api/dashboard');
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Unable to load dashboard');
  renderDashboard(data);
}

async function vote(button) {
  const schoolId = window.prompt('School ID?');
  if (!schoolId) return;
  const response = await fetch(`/api/announcements/${button.dataset.announcement}/vote`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ option_id: button.dataset.option, school_id: schoolId.trim() }) });
  const data = await response.json();
  if (!response.ok) return window.alert(data.error || 'Vote could not be recorded');
  await loadDashboard();
}

document.querySelectorAll('[data-close]').forEach((button) => { button.onclick = () => { $(`#${button.dataset.close}`).hidden = true; }; });
$('#openAnnouncement').onclick = () => { $('#pinInput').value = ''; $('#pinError').hidden = true; $('#pinModal').hidden = false; };
$('#pinForm').onsubmit = async (event) => { event.preventDefault(); const response = await fetch('/api/verify-pin', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pin: $('#pinInput').value }) }); if (!response.ok) { $('#pinError').textContent = 'Invalid PIN'; $('#pinError').hidden = false; return; } $('#announcementForm').elements.pin.value = $('#pinInput').value; $('#pinModal').hidden = true; $('#announcementModal').hidden = false; };
$('#pollToggle').onclick = () => { const expanded = $('#pollToggle').getAttribute('aria-expanded') === 'true'; $('#pollToggle').setAttribute('aria-expanded', String(!expanded)); $('#pollToggle strong').innerHTML = expanded ? '&rarr;' : '&darr;'; $('#pollFields').hidden = expanded; };
$('#announcementForm').onsubmit = async (event) => { event.preventDefault(); const response = await fetch('/api/announcements', { method: 'POST', body: new FormData(event.currentTarget) }); const data = await response.json(); if (!response.ok) { $('#announcementError').textContent = data.error; $('#announcementError').hidden = false; return; } $('#announcementModal').hidden = true; event.currentTarget.reset(); await loadDashboard(); };
$('#announcementFeed').onclick = (event) => { const button = event.target.closest('[data-option]'); if (button) vote(button); };
loadDashboard().catch((error) => { $('#announcementFeed').innerHTML = `<p class="form-error">${escapeHtml(error.message)}</p>`; });
