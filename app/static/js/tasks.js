const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
const dateKey = (value) => value.toISOString().slice(0, 10);
const taskDate = (task) => new Date(task.deadline);
const state = { tasks: [], cursor: new Date(), selected: new Date(), view: 'month', activeId: null, pendingAction: 'create', pin: '' };

async function api(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}
function tasksOn(date) { return state.tasks.filter((task) => dateKey(taskDate(task)) === dateKey(date)).sort((a, b) => taskDate(a) - taskDate(b)); }
function taskMarkup(task, className) { return `<button type="button" class="${className}" data-task="${task.id}"><strong>${escapeHtml(task.title)}</strong><small>${escapeHtml(task.course)}</small></button>`; }
function updateViewButtons() { document.querySelectorAll('[data-view]').forEach((button) => button.classList.toggle('active', button.dataset.view === state.view)); }
function renderCalendar() {
  const calendar = $('#calendar');
  if (state.view === 'month') {
    $('#calendarTitle').textContent = state.cursor.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
    const first = new Date(Date.UTC(state.cursor.getUTCFullYear(), state.cursor.getUTCMonth(), 1));
    const start = new Date(first); start.setUTCDate(1 - first.getUTCDay());
    let markup = '<div class="month-grid"><div class="weekday">SUN</div><div class="weekday">MON</div><div class="weekday">TUE</div><div class="weekday">WED</div><div class="weekday">THU</div><div class="weekday">FRI</div><div class="weekday">SAT</div>';
    for (let index = 0; index < 42; index += 1) { const date = new Date(start); date.setUTCDate(start.getUTCDate() + index); markup += `<div class="day-cell ${date.getUTCMonth() !== state.cursor.getUTCMonth() ? 'muted' : ''}" data-date="${dateKey(date)}"><span class="day-number">${date.getUTCDate()}</span>${tasksOn(date).slice(0, 3).map((task) => taskMarkup(task, 'task-chip')).join('')}</div>`; }
    calendar.innerHTML = `${markup}</div>`;
    return;
  }
  const base = new Date(state.selected); const start = new Date(base);
  if (state.view === 'week') start.setUTCDate(base.getUTCDate() - base.getUTCDay());
  const dates = state.view === 'week' ? Array.from({ length: 7 }, (_, index) => { const date = new Date(start); date.setUTCDate(start.getUTCDate() + index); return date; }) : [base];
  $('#calendarTitle').textContent = state.view === 'week' ? `Week of ${start.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}` : base.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
  calendar.innerHTML = state.view === 'week' ? `<div class="week-grid">${dates.map((date) => `<section class="week-column"><header><span>${date.toLocaleDateString(undefined, { weekday: 'short' })}</span><strong>${date.getUTCDate()}</strong></header><div class="week-items">${tasksOn(date).map((task) => taskMarkup(task, 'week-item')).join('') || '<p class="empty-slot">No deadlines</p>'}</div></section>`).join('')}</div>` : `<div class="day-view"><div class="day-summary"><span class="day-number-large">${base.getUTCDate()}</span><div><strong>${base.toLocaleDateString(undefined, { weekday: 'long' })}</strong><small>${tasksOn(base).length} deadline${tasksOn(base).length === 1 ? '' : 's'} scheduled</small></div></div><div class="day-items">${tasksOn(base).map((task) => taskMarkup(task, 'day-item')).join('') || '<p class="empty-slot">No deadlines scheduled for this day.</p>'}</div></div>`;
}
function openTask(taskId) { const task = state.tasks.find((item) => item.id === taskId); if (!task) return; state.activeId = task.id; state.selected = taskDate(task); state.view = 'day'; updateViewButtons(); renderCalendar(); $('#taskModalContent').innerHTML = `<p class="eyebrow">${escapeHtml(task.course)} · ${escapeHtml(task.difficulty)}</p><h2>${escapeHtml(task.title)}</h2><p class="task-description">${escapeHtml(task.description)}</p><p><strong>Due</strong><br>${taskDate(task).toLocaleString()}</p>`; $('#taskModal').hidden = false; }
function beginPin(action) { state.pendingAction = action; $('#pinInput').value = ''; $('#pinError').hidden = true; $('#pinModal').hidden = false; }
function openTaskForm(task = null) { state.pendingAction = task ? 'edit' : 'create'; const form = $('#taskForm'); form.reset(); $('#taskFormTitle').textContent = task ? 'Edit task' : 'Add a task'; $('#taskFormEyebrow').textContent = task ? 'UPDATE ENTRY' : 'NEW ENTRY'; if (task) Object.entries(task).forEach(([key, value]) => { if (form.elements[key]) form.elements[key].value = key === 'deadline' ? taskDate(task).toISOString().slice(0, 16) : value; }); $('#taskError').hidden = true; $('#taskFormModal').hidden = false; }
async function loadTasks() { state.tasks = (await api('/api/tasks')).tasks; renderCalendar(); }
$('#openTask').onclick = () => beginPin('create');
$('#pinForm').onsubmit = async (event) => { event.preventDefault(); try { await api('/api/verify-pin', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pin: $('#pinInput').value }) }); state.pin = $('#pinInput').value; $('#pinModal').hidden = true; if (state.pendingAction === 'delete') { await api(`/api/tasks/${state.activeId}`, { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pin: state.pin }) }); $('#taskModal').hidden = true; await loadTasks(); } else openTaskForm(state.pendingAction === 'edit' ? state.tasks.find((task) => task.id === state.activeId) : null); } catch (error) { $('#pinError').textContent = error.message; $('#pinError').hidden = false; } };
$('#taskForm').onsubmit = async (event) => { event.preventDefault(); const body = new FormData(event.currentTarget); body.append('pin', state.pin); try { await api(state.pendingAction === 'edit' ? `/api/tasks/${state.activeId}` : '/api/tasks', { method: state.pendingAction === 'edit' ? 'PATCH' : 'POST', body }); $('#taskFormModal').hidden = true; await loadTasks(); } catch (error) { $('#taskError').textContent = error.message; $('#taskError').hidden = false; } };
$('#editTask').onclick = () => { $('#taskModal').hidden = true; beginPin('edit'); };
$('#deleteTask').onclick = () => { if (window.confirm('Delete this task?')) beginPin('delete'); };
document.addEventListener('click', (event) => { const taskButton = event.target.closest('[data-task]'); if (taskButton) { openTask(Number(taskButton.dataset.task)); return; } const cell = event.target.closest('.day-cell'); if (cell) { state.selected = new Date(`${cell.dataset.date}T00:00:00Z`); renderCalendar(); } });
document.querySelectorAll('[data-close]').forEach((button) => { button.onclick = () => { document.querySelector(`#${button.dataset.close}`).hidden = true; }; });
document.querySelectorAll('[data-view]').forEach((button) => { button.onclick = () => { state.view = button.dataset.view; updateViewButtons(); renderCalendar(); }; });
$('#previousMonth').onclick = () => { if (state.view === 'month') state.cursor.setUTCMonth(state.cursor.getUTCMonth() - 1); else state.selected.setUTCDate(state.selected.getUTCDate() - (state.view === 'week' ? 7 : 1)); renderCalendar(); };
$('#nextMonth').onclick = () => { if (state.view === 'month') state.cursor.setUTCMonth(state.cursor.getUTCMonth() + 1); else state.selected.setUTCDate(state.selected.getUTCDate() + (state.view === 'week' ? 7 : 1)); renderCalendar(); };
$('#todayButton').onclick = () => { state.cursor = new Date(); state.selected = new Date(); renderCalendar(); };
updateViewButtons(); loadTasks().catch((error) => { $('#calendar').innerHTML = `<p class="form-error">${escapeHtml(error.message)}</p>`; });
