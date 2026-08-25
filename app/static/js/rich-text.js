const richTextEscape = (value) => String(value ?? '').replace(/[&<>"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[character]);

function insertAtSelection(node) {
	const selection = window.getSelection();
	if (!selection?.rangeCount) return false;
	const range = selection.getRangeAt(0);
	range.deleteContents();
	range.insertNode(node);
	range.collapse(false);
	selection.removeAllRanges();
	selection.addRange(range);
	return true;
}

function cleanPastedHtml(html) {
	const source = document.implementation.createHTMLDocument('clipboard');
	source.body.innerHTML = html;
	source.querySelectorAll('script, style, link, meta, iframe, object, embed, form, svg, img').forEach((node) => node.remove());
	source.querySelectorAll('*').forEach((node) => {
		[...node.attributes].forEach((attribute) => {
			if (attribute.name.startsWith('on') || attribute.name === 'style' || attribute.name === 'class' || attribute.name === 'id' || attribute.name.startsWith('data-') || attribute.name.startsWith('aria-') || attribute.name.includes(':')) node.removeAttribute(attribute.name);
		});
	});
	return source.body;
}

function createTable(rows, columns) {
	const table = document.createElement('table');
	const body = document.createElement('tbody');
	for (let rowIndex = 0; rowIndex < rows; rowIndex += 1) {
		const row = document.createElement('tr');
		for (let columnIndex = 0; columnIndex < columns; columnIndex += 1) {
			const cell = document.createElement('td');
			cell.appendChild(document.createElement('br'));
			row.appendChild(cell);
		}
		body.appendChild(row);
	}
	table.appendChild(body);
	return table;
}

function showTablePicker(editor, sync) {
	document.querySelector('.table-picker')?.remove();
	const selection = window.getSelection();
	const savedRange = selection?.rangeCount ? selection.getRangeAt(0).cloneRange() : null;
	const picker = document.createElement('div');
	picker.className = 'table-picker';
	picker.setAttribute('role', 'dialog');
	picker.setAttribute('aria-label', 'Choose table size');
	const label = document.createElement('strong');
	label.className = 'table-picker-label';
	label.textContent = 'Insert table';
	picker.appendChild(label);
	const grid = document.createElement('div');
	grid.className = 'table-picker-grid';
	grid.setAttribute('role', 'grid');
	for (let row = 1; row <= 8; row += 1) {
		for (let column = 1; column <= 8; column += 1) {
			const cell = document.createElement('button');
			cell.type = 'button';
			cell.className = 'table-picker-cell';
			cell.dataset.rows = row;
			cell.dataset.columns = column;
			cell.setAttribute('aria-label', `${row} rows by ${column} columns`);
			cell.addEventListener('mouseenter', () => { label.textContent = `${row} x ${column} table`; grid.querySelectorAll('.table-picker-cell').forEach((item) => item.classList.toggle('active', Number(item.dataset.rows) <= row && Number(item.dataset.columns) <= column)); });
			cell.addEventListener('click', () => {
				picker.remove();
				editor.focus();
				if (savedRange) { selection.removeAllRanges(); selection.addRange(savedRange); }
				if (insertAtSelection(createTable(row, column))) sync();
			});
			grid.appendChild(cell);
		}
	}
	picker.appendChild(grid);
	document.body.appendChild(picker);
	const button = editor.previousElementSibling.querySelector('[data-table]');
	const box = button.getBoundingClientRect();
	picker.style.top = `${box.bottom + window.scrollY + 6}px`;
	picker.style.left = `${Math.min(box.left + window.scrollX, window.innerWidth - 220 + window.scrollX)}px`;
	grid.querySelector('.table-picker-cell').focus();
	const close = (event) => { if (!picker.contains(event.target) && event.target !== button) { picker.remove(); document.removeEventListener('mousedown', close); editor.focus(); } };
	document.addEventListener('mousedown', close);
	picker.addEventListener('keydown', (event) => { if (event.key === 'Escape') { picker.remove(); document.removeEventListener('mousedown', close); editor.focus(); } });
}

function createRichTextEditor(editor) {
	const input = document.querySelector(editor.dataset.input);
	input.removeAttribute('required');
	input.removeAttribute('maxlength');
	const toolbar = editor.previousElementSibling;
	toolbar.insertAdjacentHTML('beforeend', '<button type="button" data-table aria-label="Insert table" title="Insert table">▦</button><button type="button" data-format-block="h1" aria-label="Title" title="Title">T</button><button type="button" data-format-block="h2" aria-label="Heading 1" title="Heading 1">H1</button><button type="button" data-format-block="h3" aria-label="Heading 2" title="Heading 2">H2</button><button type="button" data-font-name="Georgia" aria-label="Serif font" title="Serif font">Aa</button><button type="button" data-font-size="5" aria-label="Large font" title="Large font">A+</button><button type="button" data-command="foreColor" data-value="#d65a68" aria-label="Maroon text" title="Maroon text">A</button><button type="button" data-command="hiliteColor" data-value="#54262c" aria-label="Maroon highlight" title="Maroon highlight">&#9632;</button><button type="button" data-emoji="📌" aria-label="Pin emoji" title="Pin emoji">📌</button><button type="button" data-emoji="🎯" aria-label="Target emoji" title="Target emoji">🎯</button><button type="button" data-emoji="🔦" aria-label="Torch emoji" title="Torch emoji">🔦</button>');
	const sync = () => { input.value = editor.innerHTML; input.dispatchEvent(new Event('input', { bubbles: true })); };
	const focusEditor = () => editor.focus();
	toolbar.querySelector('[data-table]').onclick = () => showTablePicker(editor, sync);
	toolbar.querySelectorAll('[data-command]').forEach((button) => button.onclick = () => {
		focusEditor();
		document.execCommand(button.dataset.command, false, button.dataset.value || null);
		sync();
	});
	toolbar.querySelectorAll('[data-format-block]').forEach((button) => button.onclick = () => { focusEditor(); document.execCommand('formatBlock', false, button.dataset.formatBlock); sync(); });
	toolbar.querySelectorAll('[data-font-name], [data-font-size]').forEach((button) => button.onclick = () => { focusEditor(); document.execCommand(button.dataset.fontName ? 'fontName' : 'fontSize', false, button.dataset.fontName || button.dataset.fontSize); sync(); });
	const linkButton = toolbar.querySelector('[data-link]');
	if (linkButton) linkButton.onclick = () => {
		focusEditor();
		const url = window.prompt('Enter an HTTPS or HTTP link');
		if (url && /^https?:\/\/[^\s]+$/i.test(url)) document.execCommand('createLink', false, url);
		sync();
	};
	toolbar.querySelectorAll('[data-emoji]').forEach((button) => button.onclick = () => {
		focusEditor();
		document.execCommand('insertText', false, button.dataset.emoji);
		sync();
	});
	editor.addEventListener('input', sync);
	editor.addEventListener('paste', (event) => {
		event.preventDefault();
		const html = event.clipboardData.getData('text/html');
		if (html) {
			const fragment = cleanPastedHtml(html);
			const wrapper = document.createDocumentFragment();
			while (fragment.firstChild) wrapper.appendChild(fragment.firstChild);
			insertAtSelection(wrapper);
		} else {
			insertAtSelection(document.createTextNode(event.clipboardData.getData('text/plain')));
		}
		sync();
	});
	editor.closest('form').addEventListener('submit', sync, true);
	editor.closest('form').addEventListener('reset', () => { editor.innerHTML = ''; sync(); });
	editor.innerHTML = input.value || '';
	return { setValue: (value) => { editor.innerHTML = value || ''; sync(); }, clear: () => { editor.innerHTML = ''; sync(); } };
}

function setupCollapsibleRichContent(root = document) {
	root.querySelectorAll('.rich-content').forEach((content) => {
		if (content.dataset.collapsibleReady) return;
		content.dataset.collapsibleReady = 'true';
		if (content.scrollHeight <= 220) return;
		content.classList.add('is-collapsible');
		const button = document.createElement('button');
		button.type = 'button';
		button.className = 'rich-content-toggle';
		button.textContent = '...see more';
		button.setAttribute('aria-expanded', 'false');
		content.after(button);
	});
}

document.addEventListener('click', (event) => {
	const button = event.target.closest('.rich-content-toggle');
	if (!button) return;
	const content = button.previousElementSibling;
	const expanded = content.classList.toggle('is-expanded');
	button.textContent = expanded ? '...see less' : '...see more';
	button.setAttribute('aria-expanded', String(expanded));
});

window.richTextEditors = Object.fromEntries([...document.querySelectorAll('[data-rich-editor]')].map((editor) => [editor.id, createRichTextEditor(editor)]));