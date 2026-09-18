const compoundInterestForm = document.querySelector('#compoundInterestForm');
const discountForm = document.querySelector('#discountForm');
const equationOfValueForm = document.querySelector('#equationOfValueForm');
const nominalRateForm = document.querySelector('#nominalRateForm');
const effectiveRateForm = document.querySelector('#effectiveRateForm');
const continuousCompoundingForm = document.querySelector('#continuousCompoundingForm');

function renderMathResult(container, errorContainer, formula, result, title, summary) {
  if (!container) return;
  const entries = [];
  if (result && typeof result === 'object') {
    Object.entries(result).forEach(([key, value]) => {
      if (typeof value === 'number') {
        const label = key.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
        entries.push({ label, value });
      }
    });
  }
  const number = new Intl.NumberFormat('en-PH', { maximumFractionDigits: 6 });
  const money = new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP' });
  const summaryHtml = summary ? `<p class="muted">${summary}</p>` : '';
  const statHtml = entries.length ? `
    <div class="interest-result-grid">
      ${entries.map(({ label, value }) => `
        <div>
          <span>${label}</span>
          <strong>${typeof value === 'number' && Math.abs(value) > 1000 ? money.format(value) : number.format(value)}</strong>
        </div>
      `).join('')}
    </div>
  ` : '';
  const steps = Array.isArray(result?.steps) ? result.steps.map((step, index) => `<li>${index + 1}. ${step.replace(/^[0-9]+\.\s*/, '')}</li>`).join('') : '';
  container.innerHTML = `
    <div class="solution-block">
      <p class="solution-label">Formula</p>
      <p class="solution-formula">${formula}</p>
    </div>
    ${summaryHtml}
    ${statHtml}
    ${steps ? `<ol class="solution-steps">${steps}</ol>` : ''}
    <button class="button button-quiet" type="button" data-save-study-example>${title}</button>
  `;
  container.hidden = false;
  const saveButton = container.querySelector('[data-save-study-example]');
  if (saveButton) {
    saveButton.onclick = async () => {
      saveButton.disabled = true;
      try {
        const saved = await fetch('/api/interactive/simple-interest/example', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ result }) });
        const payload = await saved.json().catch(() => ({}));
        if (!saved.ok) throw new Error(payload.error || 'Unable to save study example');
        saveButton.textContent = 'Saved to study sources';
      } catch (error) {
        if (errorContainer) {
          errorContainer.textContent = error.message || 'Unable to save study example';
          errorContainer.hidden = false;
        }
      }
    };
  }
}

function handleCalculator(form, endpoint, errorId, resultId, formula, keys, summaryBuilder, payloadTransformer) {
  if (!form) return;
  const errorBox = document.querySelector(`#${errorId}`);
  const resultBox = document.querySelector(`#${resultId}`);
  const solveFor = form.elements.solve_for;
  const fields = Object.fromEntries(Object.keys(keys).map((key) => [key, form.querySelector(`[data-interest-field="${key}"]`)]));
  const inputs = Object.fromEntries(Object.keys(keys).map((key) => [key, form.elements[key]]));

  function updateInputs() {
    const target = solveFor ? solveFor.value : 'future_value';
    Object.keys(keys).forEach((key) => {
      const field = fields[key];
      const input = inputs[key];
      if (!field || !input) return;
      const isRequired = keys[target]?.includes(key) ?? false;
      field.hidden = !isRequired;
      input.required = isRequired;
      if (!isRequired) input.value = '';
    });
  }

  if (solveFor) solveFor.addEventListener('change', updateInputs);
  updateInputs();

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (errorBox) errorBox.hidden = true;
    if (resultBox) resultBox.hidden = true;
    const button = form.querySelector('button[type="submit"]');
    if (button) {
      button.disabled = true;
      button.textContent = 'Calculating...';
    }
    try {
      const payload = Object.fromEntries(new FormData(form).entries());
      const transformed = payloadTransformer ? payloadTransformer(payload) : payload;
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(transformed),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Unable to calculate');
      const result = data.result;
      const summary = summaryBuilder ? summaryBuilder(result) : '';
      resultBox.innerHTML = '';
      renderMathResult(resultBox, errorBox, formula, result, 'Save as study example', summary);
    } catch (error) {
      if (errorBox) {
        errorBox.textContent = error.message;
        errorBox.hidden = false;
      }
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = 'Calculate';
      }
    }
  });
}

if (compoundInterestForm) {
  handleCalculator(
    compoundInterestForm,
    '/api/interactive/compound-interest',
    'compoundInterestError',
    'compoundInterestResult',
    'F = P(1 + i)^n',
    {
      future_value: ['principal', 'interest_rate', 'n'],
      principal: ['future_value', 'interest_rate', 'n'],
      interest_rate: ['principal', 'future_value', 'n'],
      periods: ['principal', 'future_value', 'interest_rate'],
    },
    (result) => `${result.n} compounding period(s) at ${result.interest_rate}%` 
  );
}

if (discountForm) {
  handleCalculator(
    discountForm,
    '/api/interactive/discount',
    'discountError',
    'discountResult',
    'D = F d t and P = F - D',
    {
      discount: ['future_value', 'discount_rate', 't'],
      present_value: ['future_value', 'discount_rate', 't'],
      discount_rate: ['future_value', 'discount', 't'],
      time: ['future_value', 'discount', 'discount_rate'],
    },
    (result) => `Present value = ${result.present_value}`
  );
}

if (equationOfValueForm) {
  handleCalculator(
    equationOfValueForm,
    '/api/interactive/equation-of-value',
    'equationOfValueError',
    'equationOfValueResult',
    'Sum(obligations at focal date) = Sum(payments at focal date)',
    {
      unknown_x: ['interest_rate', 'focal_date', 'unknown_time', 'obligations', 'payments'],
      interest_rate: ['focal_date', 'obligations', 'payments'],
      focal_date: ['interest_rate', 'obligations', 'payments'],
    },
    (result) => `Balance at focal date = ${result.obligation_value ?? 0}`,
    (payload) => {
      const next = { ...payload };
      if (payload.obligations) next.obligations = JSON.parse(payload.obligations || '[]');
      if (payload.payments) next.payments = JSON.parse(payload.payments || '[]');
      return next;
    }
  );
}

if (nominalRateForm) {
  handleCalculator(
    nominalRateForm,
    '/api/interactive/nominal-rate',
    'nominalRateError',
    'nominalRateResult',
    'j = n1 x i',
    {
      nominal_rate: ['period_rate', 'n1'],
      period_rate: ['nominal_rate', 'n1'],
      periods_per_year: ['nominal_rate', 'period_rate'],
    },
    (result) => `Nominal rate = ${result.nominal_rate}`
  );
}

if (effectiveRateForm) {
  handleCalculator(
    effectiveRateForm,
    '/api/interactive/effective-rate',
    'effectiveRateError',
    'effectiveRateResult',
    'i_e = (1 + j / n1)^n1 - 1',
    {
      effective_rate: ['nominal_rate', 'n1'],
      nominal_rate: ['effective_rate', 'n1'],
      periods_per_year: ['nominal_rate', 'effective_rate'],
    },
    (result) => `Effective rate = ${result.effective_rate}`
  );
}

if (continuousCompoundingForm) {
  handleCalculator(
    continuousCompoundingForm,
    '/api/interactive/continuous-compounding',
    'continuousCompoundingError',
    'continuousCompoundingResult',
    'F = P e^(j t)',
    {
      future_value: ['principal', 'nominal_rate', 't'],
      principal: ['future_value', 'nominal_rate', 't'],
      nominal_rate: ['principal', 'future_value', 't'],
      time: ['principal', 'future_value', 'nominal_rate'],
    },
    (result) => `Future value = ${result.future_value}`
  );
}
