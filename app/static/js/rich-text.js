const richTextEscape = (value) => String(value ?? '').replace(/[&<>"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[character]);

function createRichTextEditor(editor) {
	const input = document.querySelector(editor.dataset.input);
	const toolbar = editor.previousElementSibling;
	toolbar.insertAdjacentHTML('beforeend', '<button type="button" data-format-block="h1" aria-label="Title" title="Title">T</button><button type="button" data-format-block="h2" aria-label="Heading 1" title="Heading 1">H1</button><button type="button" data-format-block="h3" aria-label="Heading 2" title="Heading 2">H2</button><button type="button" data-font-name="Georgia" aria-label="Serif font" title="Serif font">Aa</button><button type="button" data-font-size="5" aria-label="Large font" title="Large font">A+</button><button type="button" data-command="foreColor" data-value="#d65a68" aria-label="Maroon text" title="Maroon text">A</button><button type="button" data-command="hiliteColor" data-value="#54262c" aria-label="Maroon highlight" title="Maroon highlight">&#9632;</button><button type="button" data-emoji="📌" aria-label="Pin emoji" title="Pin emoji">📌</button><button type="button" data-emoji="🎯" aria-label="Target emoji" title="Target emoji">🎯</button><button type="button" data-emoji="🔦" aria-label="Torch emoji" title="Torch emoji">🔦</button>');
	const sync = () => { input.value = editor.innerHTML; input.dispatchEvent(new Event('input', { bubbles: true })); };
	const focusEditor = () => editor.focus();
	toolbar.querySelectorAll('[data-command]').forEach((button) => button.onclick = () => {
		focusEditor();
		document.execCommand(button.dataset.command, false, button.dataset.value || null);
		sync();
	});
	toolbar.querySelectorAll('[data-format-block]').forEach((button) => button.onclick = () => { focusEditor(); document.execCommand('formatBlock', false, button.dataset.formatBlock); sync(); });
	toolbar.querySelectorAll('[data-font-name], [data-font-size]').forEach((button) => button.onclick = () => { focusEditor(); document.execCommand(button.dataset.fontName ? 'fontName' : 'fontSize', false, button.dataset.fontName || button.dataset.fontSize); sync(); });
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