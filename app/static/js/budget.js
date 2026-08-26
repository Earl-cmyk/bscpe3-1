const $ = (selector) => document.querySelector(selector);
const money = (value) => `PHP ${Number(value || 0).toFixed(2)}`;
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
let budgetData = { wallets: [], contributors: [] };
const auditLists = { payees: [], purchased_items: [] };
function renderAuditList(name) {
	const target = name === 'payees' ? '#payeesList' : '#purchasedItemsList';
	$(target).innerHTML = auditLists[name].map((item, index) => `<span class="audit-list-item">${escapeHtml(item)}<button type="button" class="list-remove" data-list="${name}" data-index="${index}" aria-label="Remove ${escapeHtml(item)}">&times;</button></span>`).join('');
}
function addAuditListItem(name) {
	const input = $(`[data-list-input="${name}"]`);
	const value = input.value.trim();
	if (!value || auditLists[name].includes(value)) return;
	auditLists[name].push(value);
	input.value = '';
	renderAuditList(name);
}
document.querySelectorAll('.add-list-item').forEach((button) => { button.onclick = () => addAuditListItem(button.dataset.list); });
document.querySelectorAll('.list-item-input').forEach((input) => { input.onkeydown = (event) => { if (event.key === 'Enter') { event.preventDefault(); addAuditListItem(input.dataset.list); } }; });
document.querySelector('#auditModal').onclick = (event) => { const button = event.target.closest('.list-remove'); if (!button) return; auditLists[button.dataset.list].splice(Number(button.dataset.index), 1); renderAuditList(button.dataset.list); };
async function loadBudget() { 
	const walletId = $('#walletSelect').value; 
	const response = await fetch(`/api/budget${walletId ? `?wallet_id=${walletId}` : ''}`); 
	const data = await response.json(); 
	if (!response.ok) throw new Error(data.error || 'Unable to load wallet'); 
	budgetData = data; 
	const deposits = Number(data.deposits); 
	const withdrawals = Number(data.withdrawals); 
	const total = deposits + withdrawals; 
	const depositPercent = total ? (deposits / total) * 100 : 0; 
	$('#balanceValue').textContent = money(data.balance); 
	$('#entryCount').textContent = `${data.entries.length} entries`; 
	$('#depositTotal').textContent = money(deposits); 
	$('#withdrawTotal').textContent = money(withdrawals); 
	$('#pieLabel').textContent = total ? money(data.balance) : 'No entries'; 
	$('#pieDeposit').style.strokeDasharray = `${depositPercent} ${100 - depositPercent}`; 
	$('#pieWithdraw').style.strokeDasharray = `${100 - depositPercent} ${depositPercent}`; 
	$('#pieWithdraw').style.strokeDashoffset = `${-depositPercent}`; 
	$('#budgetEntries').innerHTML = data.entries.map((entry) => `<div class="budget-entry"><span class="entry-icon ${entry.type}">${entry.type === 'deposit' ? '+' : '-'}</span><span><strong>${escapeHtml(entry.title || entry.reason || '')}</strong><small>${escapeHtml(entry.reason || '')} · ${entry.type} · ${entry.status}</small>${entry.payees?.length ? `<small>Payees: ${escapeHtml(entry.payees.join(', '))}</small>` : ''}${entry.purchased_items?.length ? `<small>Items: ${escapeHtml(entry.purchased_items.join(', '))}</small>` : ''}</span><b>${entry.type === 'deposit' ? '+' : '-'}${money(entry.amount)}</b>${entry.type === 'withdraw' && entry.status === 'pending' ? `<span class="entry-actions"><button class="button button-quiet" data-action="cancel" data-id="${entry.id}" aria-label="Cancel withdrawal">&times;</button><button class="button button-primary" data-action="spent" data-id="${entry.id}" aria-label="Mark spent">&check;</button></span>` : ''}</div>`).join('') || '<p class="muted">No entries yet.</p>'; 
	$('#auditHistory').innerHTML = data.audit.map((event) => `<div class="audit-event"><strong>${escapeHtml(event.event_type)}</strong><small>${escapeHtml(event.actor)} · ${escapeHtml(event.created_at)}</small></div>`).join('') || '<p class="muted">No audit events yet.</p>'; 
}
function fillSelects() { 
	$('#walletSelect').innerHTML = budgetData.wallets.map((wallet) => `<option value="${wallet.id}">${escapeHtml(wallet.name)}${wallet.course ? ` · ${escapeHtml(wallet.course)}` : ''}</option>`).join(''); 
	$('#auditWallet').innerHTML = $('#walletSelect').innerHTML; 
}
async function loadReferenceData() { 
	const response = await fetch('/api/budget'); 
	const data = await response.json(); 
	if (!response.ok) throw new Error(data.error || 'Unable to load wallets'); 
	budgetData = data; 
	fillSelects(); 
}
$('#walletSelect').onchange = () => loadBudget().catch((error) => { $('#budgetEntries').innerHTML = `<p class="form-error">${escapeHtml(error.message)}</p>`; });
$('#addWallet').onclick = async () => { const name = window.prompt('Wallet name'); if (!name?.trim()) return; const course = window.prompt('Course code (optional)'); const pin = window.prompt('Enter your PIN'); if (!pin) return; const response = await fetch('/api/wallets', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: name.trim(), course: course?.trim() || '', pin }) }); const data = await response.json(); if (!response.ok) window.alert(data.error); else { await loadReferenceData(); $('#walletSelect').value = data.wallet.id; await loadBudget(); } };
$('#openAudit').onclick = async () => { $('#pinInput').value = ''; $('#pinError').hidden = true; $('#pinModal').hidden = false; };
$('#pinForm').onsubmit = async (event) => { 
	event.preventDefault(); 
	const response = await fetch('/api/verify-pin', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pin: $('#pinInput').value }) }); 
	if (!response.ok) { 
		$('#pinError').textContent = 'Invalid PIN'; 
		$('#pinError').hidden = false; 
		return; 
	} 
	$('#auditForm').dataset.pin = $('#pinInput').value; 
	$('#pinModal').hidden = true; 
	$('#auditModal').hidden = false; 
	$('#auditWallet').value = $('#walletSelect').value; 
	auditLists.payees.length = 0; auditLists.purchased_items.length = 0; renderAuditList('payees'); renderAuditList('purchased_items');
};
document.querySelectorAll('[data-close]').forEach((button) => { 
	button.onclick = () => { document.querySelector(`#${button.dataset.close}`).hidden = true; }; 
});
$('#auditForm').onsubmit = async (event) => { 
	event.preventDefault(); 
	const formData = new FormData(event.currentTarget);
	const payload = Object.fromEntries(formData); 
	payload.pin = event.currentTarget.dataset.pin || ''; 
	formData.set('payees', JSON.stringify(auditLists.payees));
	formData.set('purchased_items', JSON.stringify(auditLists.purchased_items));
	formData.set('pin', payload.pin);
	const response = await fetch('/api/budget', { method: 'POST', body: formData }); 
	const data = await response.json(); 
	if (!response.ok) { 
		$('#auditError').textContent = data.error; 
		$('#auditError').hidden = false; 
		return; 
	} 
	$('#auditModal').hidden = true; 
	event.currentTarget.reset(); 
	await loadReferenceData(); 
	await loadBudget(); 
};
$('#budgetEntries').onclick = async (event) => { 
	const button = event.target.closest('[data-action]'); 
	if (!button) return; 
	if (button.dataset.action === 'edit-payers') { const entry = budgetData.entries.find((item) => String(item.id) === button.dataset.id); if (!entry) return; const names = window.prompt('Edit payer names, one per line', (entry.payer_names || []).join('\n')); if (names === null) return; const pin = window.prompt('Enter your PIN'); if (!pin) return; const payerNames = [...new Set(names.split(/[\n,]/).map((name) => name.trim()).filter(Boolean))]; const response = await fetch(`/api/budget/${entry.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ payer_names: payerNames, pin }) }); const data = await response.json(); if (!response.ok) window.alert(data.error); else await loadBudget(); return; }
	const pin = window.prompt('Enter your PIN'); 
	if (pin === null) return; 
	const response = await fetch(`/api/budget/${button.dataset.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: button.dataset.action, pin }) }); 
	const data = await response.json(); 
	if (!response.ok) window.alert(data.error); 
	else await loadBudget(); 
};
loadReferenceData().then(loadBudget).catch((error) => { $('#budgetEntries').innerHTML = `<p class="form-error">${escapeHtml(error.message)}</p>`; });
