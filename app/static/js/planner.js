const plannerEscape = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
const plannerMoney = (value) => `PHP ${Number(value).toFixed(2)}`;
const plannerQuery = document.querySelector('#queryForm');
const plannerHistory = document.querySelector('#chatHistory');
const plannerMessages = document.querySelector('#chatMessages');
const plannerAddMessage = (role, content) => { plannerMessages.insertAdjacentHTML('beforeend', `<div class="chat-message ${role}"><span>${role === 'user' ? 'You' : 'Planner'}</span><p>${content}</p></div>`); plannerHistory.hidden = false; plannerHistory.scrollTop = plannerHistory.scrollHeight; };
document.querySelector('#closeChat').onclick = () => { plannerHistory.hidden = true; };
plannerQuery.onsubmit = async (event) => {
  event.preventDefault();
  const query = document.querySelector('#queryInput').value.trim();
  if (!query) return;
  plannerAddMessage('user', plannerEscape(query));
  document.querySelector('#queryInput').value = '';
  const response = await fetch(`/api/query?q=${encodeURIComponent(query)}`);
  const data = await response.json();
  let answer;
  if (!response.ok) {
    answer = plannerEscape(data.error);
  } else if (data.entries) {
    answer = data.entries.length ? data.entries.map((entry) => `${plannerEscape(entry.reason)} - ${plannerMoney(entry.amount)} spent`).join('<br>') : `No spending found. Total: ${plannerMoney(data.total)}`;
  } else if (data.notes) {
    answer = data.notes.length ? data.notes.map((note) => `<strong>${plannerEscape(note.title)}</strong> (${plannerEscape(note.course)})<br><small>${plannerEscape(note.caption)}</small>`).join('<br><br>') : 'No notes found.';
  } else if (data.tasks && data.notes) {
    const tasks = data.tasks.length ? data.tasks.map((task) => `${plannerEscape(task.title)} - ${new Date(task.deadline).toLocaleString()}`).join('<br>') : 'No pending deadlines.';
    const notes = data.notes.length ? data.notes.map((note) => `<strong>${plannerEscape(note.title)}</strong><br><small>${plannerEscape(note.caption)}</small>`).join('<br><br>') : 'No notes.';
    answer = `<strong>Deadlines:</strong><br>${tasks}<br><br><strong>Notes:</strong><br>${notes}`;
  } else {
    answer = data.tasks?.length ? data.tasks.map((task) => `${plannerEscape(task.title)} - ${plannerEscape(task.course)} - ${new Date(task.deadline).toLocaleString()}`).join('<br>') : 'No matching tasks.';
  }
  plannerAddMessage('assistant', answer);
};
