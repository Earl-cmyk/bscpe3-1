const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);

function noteMarkup(note) {
	const attachments = note.attachments?.length ? note.attachments : (note.attachment_path ? [{ name: note.attachment_name, path: note.attachment_path, type: note.attachment_type }] : []);
	const attachmentDisplay = attachments.length ? `<div class="note-attachments">${attachments.map((attachment) => {
		const url = `/uploads/${encodeURIComponent(attachment.path)}`;
		const name = escapeHtml(attachment.name || attachment.path);
		if (attachment.type?.startsWith('image/')) return `<figure class="note-media"><a href="${url}" target="_blank" rel="noreferrer"><img src="${url}" alt="${name}" loading="lazy" /></a><figcaption><span>${name}</span><a class="text-link" href="${url}?download=1" aria-label="Download ${name}" title="Download ${name}">&#8595;</a></figcaption></figure>`;
		if (attachment.type?.startsWith('video/')) return `<figure class="note-media"><video controls preload="metadata"><source src="${url}" type="${escapeHtml(attachment.type)}" /></video><figcaption><span>${name}</span><a class="text-link" href="${url}?download=1" aria-label="Download ${name}" title="Download ${name}">&#8595;</a></figcaption></figure>`;
		return `<div class="note-attachment"><span>&#128206; ${name}</span><a class="text-link" href="${url}?download=1" aria-label="Download ${name}" title="Download ${name}">&#8595;</a></div>`;
	}).join('')}</div>` : '';
	return `<article class="history-item" data-note-id="${note.id}">
		<div class="announcement-meta">
			<span>${new Date(note.created_at).toLocaleString()}</span>
			<small>${escapeHtml(note.course)}</small>
		</div>
		<h2>${escapeHtml(note.title)}</h2>
		<p>${escapeHtml(note.caption)}</p>
		${attachmentDisplay}
		<div class="note-actions">
			<button class="button button-quiet edit-note" data-note-id="${note.id}">Edit</button>
			<button class="button button-quiet delete-note" data-note-id="${note.id}">Delete</button>
		</div>
	</article>`;
}

async function loadNotes(course = '') {
	const url = course ? `/api/notes?course=${encodeURIComponent(course)}` : '/api/notes';
	const response = await fetch(url);
	const data = await response.json();
	if (!response.ok) throw new Error(data.error || 'Unable to load notes');
	document.querySelector('#notesFeed').innerHTML = data.notes.map(noteMarkup).join('') || '<p class="muted">No notes yet.</p>';
}

const courseFilter = document.querySelector('#courseFilter');
courseFilter.onchange = () => loadNotes(courseFilter.value);

const pinModal = document.querySelector('#pinModal');
const pinForm = document.querySelector('#pinForm');
const pinInput = document.querySelector('#pinInput');
const pinError = document.querySelector('#pinError');
let pendingAction = null;

document.querySelector('#openNote').onclick = () => {
	pendingAction = 'create';
	pinModal.hidden = false;
	pinInput.value = '';
	pinError.hidden = true;
};

pinForm.onsubmit = async (event) => {
	event.preventDefault();
	const pin = pinInput.value.trim();
	const response = await fetch('/api/verify-pin', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ pin })
	});
	const data = await response.json();
	if (!response.ok) {
		pinError.textContent = data.error;
		pinError.hidden = false;
		return;
	}
	pinModal.hidden = true;
	if (pendingAction === 'create') {
		document.querySelector('#noteForm input[name="pin"]').value = pin;
		document.querySelector('#noteModal').hidden = false;
	} else if (pendingAction === 'edit') {
		await editNoteWithPin(pin);
	} else if (pendingAction === 'delete') {
		await deleteNoteWithPin(pin);
	}
};

document.querySelector('#noteModal .close').onclick = () => {
	document.querySelector('#noteModal').hidden = true;
	document.querySelector('#noteForm').reset();
	document.querySelector('#noteError').hidden = true;
};

document.querySelector('#pinModal .close').onclick = () => {
	pinModal.hidden = true;
	pinInput.value = '';
	pinError.hidden = true;
	pendingAction = null;
};

const noteForm = document.querySelector('#noteForm');
const noteError = document.querySelector('#noteError');

noteForm.onsubmit = async (event) => {
	event.preventDefault();
	const formData = new FormData(noteForm);
	const response = await fetch('/api/notes', {
		method: 'POST',
		body: formData
	});
	const data = await response.json();
	if (!response.ok) {
		noteError.textContent = data.error;
		noteError.hidden = false;
		return;
	}
	document.querySelector('#noteModal').hidden = true;
	noteForm.reset();
	noteError.hidden = true;
	loadNotes(courseFilter.value);
};

let editingNoteId = null;

document.querySelector('#notesFeed').onclick = async (event) => {
	const editButton = event.target.closest('.edit-note');
	const deleteButton = event.target.closest('.delete-note');
	
	if (editButton) {
		editingNoteId = editButton.dataset.noteId;
		pendingAction = 'edit';
		pinModal.hidden = false;
		pinInput.value = '';
		pinError.hidden = true;
	} else if (deleteButton) {
		editingNoteId = deleteButton.dataset.noteId;
		pendingAction = 'delete';
		pinModal.hidden = false;
		pinInput.value = '';
		pinError.hidden = true;
	}
};

async function editNoteWithPin(pin) {
	const note = await (await fetch(`/api/notes/${editingNoteId}`)).json().then(d => d.note);
	if (!note) return;
	
	document.querySelector('#noteForm input[name="title"]').value = note.title;
	document.querySelector('#noteForm select[name="course"]').value = note.course;
	document.querySelector('#noteForm textarea[name="caption"]').value = note.caption;
	document.querySelector('#noteForm input[name="pin"]').value = pin;
	
	const response = await fetch(`/api/notes/${editingNoteId}`, {
		method: 'PATCH',
		body: new FormData(noteForm)
	});
	const data = await response.json();
	if (!response.ok) {
		noteError.textContent = data.error;
		noteError.hidden = false;
		document.querySelector('#noteModal').hidden = false;
		return;
	}
	document.querySelector('#noteModal').hidden = true;
	noteForm.reset();
	noteError.hidden = true;
	editingNoteId = null;
	loadNotes(courseFilter.value);
}

async function deleteNoteWithPin(pin) {
	const response = await fetch(`/api/notes/${editingNoteId}`, {
		method: 'DELETE',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ pin })
	});
	const data = await response.json();
	if (!response.ok) {
		alert(data.error);
		return;
	}
	editingNoteId = null;
	loadNotes(courseFilter.value);
}

loadNotes().catch((error) => {
	document.querySelector('#notesFeed').innerHTML = `<p class="form-error">${escapeHtml(error.message)}</p>`;
});
