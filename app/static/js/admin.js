/**
 * Admin Page JavaScript
 * Handles month creation form, component creation, and validation
 */

// Template for per-participant distribution editors
let COMP_EDITOR_TEMPLATE = '';

/**
 * Initialize the admin page
 * @param {string} participantsHtml - HTML template for participant inputs
 */
function initAdmin(participantsHtml) {
  COMP_EDITOR_TEMPLATE = `
    <div class="muted"><small>Set per-person values (<span class="mode">__MODE__</span>).</small></div>
    <div class="row">
      ${participantsHtml}
    </div>
  `;
  
  // Initialize legacy editors
  ['electricity', 'water', 'internet'].forEach(toggleLegacyEditor);
  ['electricity', 'water', 'internet'].forEach(attachLegacyHandlers);
}

/**
 * Add a new component row to the form
 * @param {HTMLElement} btn - The button that triggered this action
 */
function addCompRow(btn) {
  const box = btn.previousElementSibling;
  const row = document.createElement('div');
  row.className = 'row comp-row';
  row.innerHTML = `
    <label><small>Name</small><input type="text" name="comp_name[]" placeholder="e.g., Gas"></label>
    <label><small>Amount</small><input type="number" step="0.01" min="0" name="comp_amount[]" placeholder="0.00"></label>
    <label><small>Split</small>
      <select name="comp_split[]" onchange="toggleCompEditorForRow(this)">
        <option value="equal">Equal</option>
        <option value="usage">By usage</option>
        <option value="percentage">Percentage</option>
        <option value="amount">Amount</option>
      </select>
    </label>
    <label><small>Position</small><input type="number" step="1" name="comp_position[]" value="0"></label>`;
  box.appendChild(row);
}

/**
 * Build a distribution editor element
 * @param {string} kind - The distribution mode (percentage/amount)
 * @param {number} index - Row index
 * @returns {HTMLElement} The editor element
 */
function buildEditor(kind, index) {
  const wrapper = document.createElement('div');
  wrapper.className = 'card comp-editor';
  wrapper.innerHTML = COMP_EDITOR_TEMPLATE
    .replaceAll('__MODE__', kind)
    .replaceAll('__IDX__', String(index));
  return wrapper;
}

/**
 * Toggle the distribution editor for a component row
 * @param {HTMLSelectElement} selectEl - The split method select element
 */
function toggleCompEditorForRow(selectEl) {
  const row = selectEl.closest('.comp-row');
  const container = row.parentElement;
  const rows = Array.from(container.querySelectorAll('.comp-row'));
  const index = rows.indexOf(row);
  
  // Remove existing editor for this row if any
  const existing = container.querySelector(`.comp-editor[data-index="${index}"]`);
  if (existing) existing.remove();
  
  const val = selectEl.value;
  if (val === 'percentage' || val === 'amount') {
    const editor = buildEditor(val, index);
    editor.dataset.index = String(index);
    container.insertBefore(editor, row.nextSibling);
    
    // Update mode label
    const mode = editor.querySelector('.mode');
    if (mode) mode.textContent = val;
    attachCustomEditorHandlers(container, index);
  }
}

/**
 * Attach event handlers to custom editor inputs
 * @param {HTMLElement} container - The container element
 * @param {number} idx - Row index
 */
function attachCustomEditorHandlers(container, idx) {
  const editor = container.querySelector(`.comp-editor[data-index="${idx}"]`);
  if (!editor) return;
  
  const inputs = editor.querySelectorAll('input[type="number"]');
  const row = container.querySelectorAll('.comp-row')[idx];
  const amountEl = row?.querySelector('input[name="comp_amount[]"]');
  const splitSel = row?.querySelector('select[name="comp_split[]"]');
  
  const update = () => updateCustomSum(container, idx);
  inputs.forEach(inp => inp.addEventListener('input', update));
  amountEl?.addEventListener('input', update);
  splitSel?.addEventListener('change', update);
  update();
}

/**
 * Ensure a sum display element exists in the editor
 * @param {HTMLElement} editor - The editor element
 * @returns {HTMLElement} The sum display element
 */
function ensureSumDisplay(editor) {
  let hint = editor.querySelector('.sum-display');
  if (!hint) {
    hint = document.createElement('small');
    hint.className = 'sum-display muted';
    const header = editor.querySelector('.muted small');
    if (header) {
      header.insertAdjacentElement('afterend', hint);
    } else {
      editor.prepend(hint);
    }
  }
  return hint;
}

/**
 * Update the sum display for a custom component editor
 * @param {HTMLElement} container - The container element
 * @param {number} idx - Row index
 */
function updateCustomSum(container, idx) {
  const row = container.querySelectorAll('.comp-row')[idx];
  const editor = container.querySelector(`.comp-editor[data-index="${idx}"]`);
  if (!row || !editor) return;
  
  const sel = row.querySelector('select[name="comp_split[]"]');
  const amtEl = row.querySelector('input[name="comp_amount[]"]');
  const inputs = editor.querySelectorAll(`input[name^="comp_dist_${idx}_"]`);
  
  let total = 0;
  inputs.forEach(inp => {
    const v = parseFloat(inp.value);
    if (!isNaN(v)) total += v;
  });
  
  const mode = sel?.value;
  const expected = (mode === 'percentage') ? 100 : parseFloat(amtEl?.value || '0');
  const hint = ensureSumDisplay(editor);
  hint.textContent = ` Sum: ${total.toFixed(2)} / ${isFinite(expected) ? expected.toFixed(2) : '—'}`;
  
  const mismatch = (mode === 'percentage' && Math.abs(total - 100) > 0.01) || 
                   (mode === 'amount' && Math.abs(total - parseFloat(amtEl?.value || '0')) > 0.01);
  editor.style.borderColor = mismatch ? 'var(--danger, #c0392b)' : '';
  inputs.forEach(inp => { inp.style.borderColor = mismatch ? 'var(--danger, #c0392b)' : ''; });
}

/**
 * Toggle legacy bill type editor visibility
 * @param {string} kind - Bill type (electricity/water/internet)
 */
function toggleLegacyEditor(kind) {
  const select = document.getElementById(`legacy_${kind}_split`);
  const editor = document.getElementById(`legacy_${kind}_editor`);
  const mode = document.getElementById(`legacy_${kind}_mode`);
  if (!select || !editor) return;
  
  const val = select.value;
  if (val === 'percentage' || val === 'amount') {
    editor.style.display = '';
    if (mode) mode.textContent = val;
  } else {
    editor.style.display = 'none';
  }
}

/**
 * Attach event handlers for legacy bill type editors
 * @param {string} kind - Bill type (electricity/water/internet)
 */
function attachLegacyHandlers(kind) {
  const editor = document.getElementById(`legacy_${kind}_editor`);
  if (!editor) return;
  
  const inputs = editor.querySelectorAll('input[type="number"]');
  inputs.forEach(inp => inp.addEventListener('input', () => updateLegacySum(kind)));
  
  const sel = document.getElementById(`legacy_${kind}_split`);
  sel?.addEventListener('change', () => updateLegacySum(kind));
  
  const amountEl = document.querySelector(`[name="${kind}_amount"]`);
  amountEl?.addEventListener('input', () => updateLegacySum(kind));
  
  updateLegacySum(kind);
}

/**
 * Update the sum display for legacy bill type editors
 * @param {string} kind - Bill type (electricity/water/internet)
 */
function updateLegacySum(kind) {
  const editor = document.getElementById(`legacy_${kind}_editor`);
  if (!editor) return;
  
  const sel = document.getElementById(`legacy_${kind}_split`);
  const inputs = editor.querySelectorAll(`input[name^="legacy_${kind}_dist_"]`);
  
  let total = 0;
  inputs.forEach(inp => {
    const v = parseFloat(inp.value);
    if (!isNaN(v)) total += v;
  });
  
  const mode = sel?.value;
  let expected = 0;
  if (mode === 'percentage') expected = 100;
  if (mode === 'amount') {
    const amountEl = document.querySelector(`[name="${kind}_amount"]`);
    expected = parseFloat(amountEl?.value || '0');
  }
  
  const header = editor.querySelector('.muted small');
  let hint = editor.querySelector('.sum-display');
  if (!hint) {
    hint = document.createElement('small');
    hint.className = 'sum-display muted';
    if (header) header.insertAdjacentElement('afterend', hint);
    else editor.prepend(hint);
  }
  
  if (mode === 'percentage' || mode === 'amount') {
    hint.textContent = ` Sum: ${total.toFixed(2)} / ${isFinite(expected) ? expected.toFixed(2) : '—'}`;
    const mismatch = (mode === 'percentage' && Math.abs(total - 100) > 0.01) || 
                     (mode === 'amount' && Math.abs(total - expected) > 0.01);
    editor.style.borderColor = mismatch ? 'var(--danger, #c0392b)' : '';
    inputs.forEach(inp => { inp.style.borderColor = mismatch ? 'var(--danger, #c0392b)' : ''; });
  } else {
    hint.textContent = '';
    editor.style.borderColor = '';
    inputs.forEach(inp => { inp.style.borderColor = ''; });
  }
}

/**
 * Clear all inline error messages within a scope
 * @param {HTMLElement} scope - The element to search within
 */
function clearErrors(scope) {
  scope.querySelectorAll('.field-error-inline').forEach(e => e.remove());
}

/**
 * Show an error message after an element
 * @param {HTMLElement} afterEl - The element to show the error after
 * @param {string} msg - The error message
 */
function showError(afterEl, msg) {
  const small = document.createElement('small');
  small.className = 'field-error field-error-inline';
  small.textContent = msg;
  afterEl.parentElement.appendChild(small);
}

/**
 * Validate distribution values on form submission
 * @param {HTMLFormElement} form - The form to validate
 * @returns {boolean} Whether validation passed
 */
function validateCreationDistributions(form) {
  let ok = true;
  clearErrors(form);
  
  // Legacy validators
  const legacy = [
    { kind: 'electricity', select: '#legacy_electricity_split', amount: form.querySelector('[name="electricity_amount"]') },
    { kind: 'water', select: '#legacy_water_split', amount: form.querySelector('[name="water_amount"]') },
    { kind: 'internet', select: '#legacy_internet_split', amount: form.querySelector('[name="internet_amount"]') },
  ];
  
  legacy.forEach(item => {
    const sel = form.querySelector(item.select);
    if (!sel) return;
    
    const val = sel.value;
    if (val === 'percentage' || val === 'amount') {
      const inputs = form.querySelectorAll(`[name^="legacy_${item.kind}_dist_"]`);
      let total = 0;
      inputs.forEach(inp => {
        const v = parseFloat(inp.value);
        if (!isNaN(v)) total += v;
      });
      
      if (val === 'percentage' && Math.abs(total - 100) > 0.01) {
        ok = false;
        showError(sel, `Percentages must sum to 100 (current: ${total.toFixed(2)})`);
      }
      if (val === 'amount') {
        const amt = parseFloat(item.amount?.value || '0');
        if (Math.abs(total - amt) > 0.01) {
          ok = false;
          showError(sel, `Amounts must sum to ${amt.toFixed(2)} (current: ${total.toFixed(2)})`);
        }
      }
    }
  });
  
  // Custom component rows
  const container = form.querySelector('#comp-creator');
  if (container) {
    const rows = Array.from(container.querySelectorAll('.comp-row'));
    rows.forEach((row, idx) => {
      const sel = row.querySelector('select[name="comp_split[]"]');
      const amtEl = row.querySelector('input[name="comp_amount[]"]');
      if (!sel) return;
      
      const val = sel.value;
      if (val === 'percentage' || val === 'amount') {
        const inputs = container.querySelectorAll(`input[name^="comp_dist_${idx}_"]`);
        let total = 0;
        inputs.forEach(inp => {
          const v = parseFloat(inp.value);
          if (!isNaN(v)) total += v;
        });
        
        if (val === 'percentage' && Math.abs(total - 100) > 0.01) {
          ok = false;
          showError(sel, `Percentages must sum to 100 (current: ${total.toFixed(2)})`);
        }
        if (val === 'amount') {
          const amt = parseFloat(amtEl?.value || '0');
          if (Math.abs(total - amt) > 0.01) {
            ok = false;
            showError(sel, `Amounts must sum to ${amt.toFixed(2)} (current: ${total.toFixed(2)})`);
          }
        }
      }
    });
  }
  
  return ok;
}
