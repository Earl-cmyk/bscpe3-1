const $ = (selector) => document.querySelector(selector);
const money = (value) => `PHP ${Number(value || 0).toFixed(2)}`;
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
let budgetData = { wallets: [], contributors: [] };
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
	$('#budgetEntries').innerHTML = data.entries.map((entry) => `<div class="budget-entry"><span class="entry-icon ${entry.type}">${entry.type === 'deposit' ? '+' : '-'}</span><span><strong>${entry.reason || ''}</strong><small>${escapeHtml(entry.contributor_name || 'Unknown')} · ${entry.type} · ${entry.status}</small></span><b>${entry.type === 'deposit' ? '+' : '-'}${money(entry.amount)}</b>${entry.type === 'withdraw' && entry.status === 'pending' ? `<span class="entry-actions"><button class="button button-quiet" data-action="cancel" data-id="${entry.id}" aria-label="Cancel withdrawal">&times;</button><button class="button button-primary" data-action="spent" data-id="${entry.id}" aria-label="Mark spent">&check;</button></span>` : ''}</div>`).join('') || '<p class="muted">No entries yet.</p>'; 
	$('#auditHistory').innerHTML = data.audit.map((event) => `<div class="audit-event"><strong>${escapeHtml(event.event_type)}</strong><small>${escapeHtml(event.actor)} · ${escapeHtml(event.created_at)}</small></div>`).join('') || '<p class="muted">No audit events yet.</p>'; 
}
function fillSelects() { 
	$('#walletSelect').innerHTML = budgetData.wallets.map((wallet) => `<option value="${wallet.id}">${escapeHtml(wallet.name)}${wallet.course ? ` · ${escapeHtml(wallet.course)}` : ''}</option>`).join(''); 
	$('#auditWallet').innerHTML = $('#walletSelect').innerHTML; 
	$('#auditContributor').innerHTML = '<option value="">Select contributor</option>' + budgetData.contributors.map((person) => `<option value="${person.id}">${escapeHtml(person.name)}</option>`).join(''); 
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
$('#addContributor').onclick = async () => { const name = window.prompt('Payer name'); if (!name?.trim()) return; const pin = window.prompt('Enter your PIN'); if (!pin) return; const response = await fetch('/api/contributors', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: name.trim(), pin }) }); const data = await response.json(); if (!response.ok) window.alert(data.error); else { await loadReferenceData(); $('#auditContributor').value = data.contributor.id; } };
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
};
document.querySelectorAll('[data-close]').forEach((button) => { 
	button.onclick = () => { document.querySelector(`#${button.dataset.close}`).hidden = true; }; 
});
$('#auditForm').onsubmit = async (event) => { 
	event.preventDefault(); 
	const formData = new FormData(event.currentTarget);
	const payload = Object.fromEntries(formData); 
	payload.pin = event.currentTarget.dataset.pin || ''; 
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
	const pin = window.prompt('Enter your PIN'); 
	if (pin === null) return; 
	const response = await fetch(`/api/budget/${button.dataset.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: button.dataset.action, pin }) }); 
	const data = await response.json(); 
	if (!response.ok) window.alert(data.error); 
	else await loadBudget(); 
};
loadReferenceData().then(loadBudget).catch((error) => { $('#budgetEntries').innerHTML = `<p class="form-error">${escapeHtml(error.message)}</p>`; });
