const richTextEscape = (value) => String(value ?? '').replace(/[&<>"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[character]);

function createRichTextEditor(editor) {
	const input = document.querySelector(editor.dataset.input);
	const toolbar = editor.previousElementSibling;
	const sync = () => { input.value = editor.innerHTML; input.dispatchEvent(new Event('input', { bubbles: true })); };
	const focusEditor = () => editor.focus();
	toolbar.querySelectorAll('[data-command]').forEach((button) => button.onclick = () => {
		focusEditor();
		document.execCommand(button.dataset.command, false, button.dataset.value || null);
		sync();
	});
	toolbar.querySelector('[data-link]').onclick = () => {
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
	editor.closest('form').addEventListener('submit', sync, true);
	editor.closest('form').addEventListener('reset', () => { editor.innerHTML = ''; sync(); });
	editor.innerHTML = input.value || '';
	return { setValue: (value) => { editor.innerHTML = value || ''; sync(); }, clear: () => { editor.innerHTML = ''; sync(); } };
}

window.richTextEditors = Object.fromEntries([...document.querySelectorAll('[data-rich-editor]')].map((editor) => [editor.id, createRichTextEditor(editor)]));