const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
const dayKey = (date) => date.toISOString().slice(0, 10);
const state = { tasks: [], cursor: new Date() };

async function loadTasks() { const response = await fetch('/api/tasks'); const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Unable to load tasks'); state.tasks = data.tasks; renderCalendar(); }
function tasksOn(date) { return state.tasks.filter((task) => dayKey(new Date(task.deadline)) === dayKey(date)); }
function renderCalendar() {
  const year = state.cursor.getUTCFullYear(); const month = state.cursor.getUTCMonth();
  $('#calendarTitle').textContent = state.cursor.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
  const first = new Date(Date.UTC(year, month, 1)); const start = new Date(first); start.setUTCDate(1 - first.getUTCDay());
  let markup = '<div class="month-grid"><div class="weekday">SUN</div><div class="weekday">MON</div><div class="weekday">TUE</div><div class="weekday">WED</div><div class="weekday">THU</div><div class="weekday">FRI</div><div class="weekday">SAT</div>';
  for (let index = 0; index < 42; index += 1) { const date = new Date(start); date.setUTCDate(start.getUTCDate() + index); markup += `<div class="day-cell"><span class="day-number">${date.getUTCDate()}</span>${tasksOn(date).slice(0, 3).map((task) => `<button class="task-chip" data-task="${task.id}">${escapeHtml(task.title)}</button>`).join('')}</div>`; }
  $('#calendar').innerHTML = `${markup}</div>`;
}
function openTaskForm() { $('#pinInput').value = ''; $('#pinError').hidden = true; $('#pinModal').hidden = false; }
$('#openTask').onclick = openTaskForm;
$('#pinForm').onsubmit = async (event) => { event.preventDefault(); const response = await fetch('/api/verify-pin', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pin: $('#pinInput').value }) }); if (!response.ok) { $('#pinError').textContent = 'Invalid PIN'; $('#pinError').hidden = false; return; } $('#taskForm').dataset.pin = $('#pinInput').value; $('#pinModal').hidden = true; $('#taskFormModal').hidden = false; };
$('#taskForm').onsubmit = async (event) => { event.preventDefault(); const body = new FormData(event.currentTarget); body.append('pin', event.currentTarget.dataset.pin || ''); const response = await fetch('/api/tasks', { method: 'POST', body }); const data = await response.json(); if (!response.ok) { $('#taskError').textContent = data.error; $('#taskError').hidden = false; return; } $('#taskFormModal').hidden = true; event.currentTarget.reset(); await loadTasks(); };
document.querySelectorAll('[data-close]').forEach((button) => { button.onclick = () => { document.querySelector(`#${button.dataset.close}`).hidden = true; }; });
$('#previousMonth').onclick = () => { state.cursor.setUTCMonth(state.cursor.getUTCMonth() - 1); renderCalendar(); };
$('#nextMonth').onclick = () => { state.cursor.setUTCMonth(state.cursor.getUTCMonth() + 1); renderCalendar(); };
$('#todayButton').onclick = () => { state.cursor = new Date(); renderCalendar(); };
loadTasks().catch((error) => { $('#calendar').innerHTML = `<p class="form-error">${escapeHtml(error.message)}</p>`; });
