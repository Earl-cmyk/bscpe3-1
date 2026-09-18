const simpleInterestForm = document.querySelector('#simpleInterestForm');
const simpleInterestError = document.querySelector('#simpleInterestError');
const simpleInterestResult = document.querySelector('#simpleInterestResult');

if (simpleInterestForm) {
	const solveFor = simpleInterestForm.elements.solve_for;
	const fields = {
		principal: simpleInterestForm.querySelector('[data-interest-field="principal"]'),
		future_value: simpleInterestForm.querySelector('[data-interest-field="future_value"]'),
		interest_rate: simpleInterestForm.querySelector('[data-interest-field="interest_rate"]'),
	};
	const inputs = Object.fromEntries(Object.keys(fields).map((key) => [key, simpleInterestForm.elements[key]]));
	const requirements = {
		future_value: ['principal', 'interest_rate'],
		principal: ['future_value', 'interest_rate'],
		interest_rate: ['principal', 'future_value'],
	};
	const money = new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP' });
	const number = new Intl.NumberFormat('en-PH', { maximumFractionDigits: 6 });

	function updateInputs() {
		const target = solveFor.value;
		Object.entries(fields).forEach(([key, field]) => {
			const shown = requirements[target].includes(key);
			field.hidden = !shown;
			inputs[key].required = shown;
		});
	}

	solveFor.addEventListener('change', updateInputs);
	updateInputs();

	simpleInterestForm.addEventListener('submit', async (event) => {
		event.preventDefault();
		simpleInterestError.hidden = true;
		simpleInterestResult.hidden = true;
		const button = simpleInterestForm.querySelector('button[type="submit"]');
		button.disabled = true;
		button.textContent = 'Calculating...';
		try {
			const response = await fetch('/api/interactive/simple-interest', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(Object.fromEntries(new FormData(simpleInterestForm))),
			});
			const data = await response.json();
			if (!response.ok) throw new Error(data.error || 'Unable to calculate simple interest');
			const result = data.result;
			simpleInterestResult.innerHTML = `
				<div class="interest-result-grid">
					<div><span>Principal</span><strong>${money.format(result.principal)}</strong></div>
					<div><span>Future value</span><strong>${money.format(result.future_value)}</strong></div>
					<div><span>Interest</span><strong>${money.format(result.interest)}</strong></div>
					<div><span>Annual rate</span><strong>${number.format(result.interest_rate)}%</strong></div>
				</div>
				<p class="muted">${result.days} day(s) using ${result.basis === 'ordinary' ? 'ordinary 30/360' : 'exact actual-day/365'}; time fraction: ${number.format(result.time_fraction)}.</p><button class="button button-quiet" type="button" data-save-study-example>Save as study example</button>`;
			simpleInterestResult.hidden = false;
			simpleInterestResult.querySelector('[data-save-study-example]').onclick = async () => {
				const saveButton = simpleInterestResult.querySelector('[data-save-study-example]');
				saveButton.disabled = true;
				try {
					const saved = await fetch('/api/interactive/simple-interest/example', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ result }) });
					const payload = await saved.json().catch(() => ({}));
					if (!saved.ok) throw new Error(payload.error || 'Unable to save study example');
					saveButton.textContent = 'Saved to study sources';
				} catch (error) {
					saveButton.disabled = false;
					simpleInterestError.textContent = error.message || 'Unable to save study example';
					simpleInterestError.hidden = false;
				}
			};
		} catch (error) {
			simpleInterestError.textContent = error.message;
			simpleInterestError.hidden = false;
		} finally {
			button.disabled = false;
			button.textContent = 'Calculate';
		}
	});
}
