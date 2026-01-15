/**
 * Month Detail Page JavaScript
 * Handles per-component adjustments and redistribution UI
 */

/**
 * Initialize the month detail page
 * @param {Array} componentIds - Array of component IDs
 * @param {Object} dynamicBaseMaps - Map of component ID to participant base values
 */
function initMonthDetail(componentIds, dynamicBaseMaps) {
  document.addEventListener('DOMContentLoaded', function() {
    wireDynamicAdjustments(componentIds, dynamicBaseMaps);
  });
}

/**
 * Format a number to 2 decimal places
 * @param {number} n - The number to format
 * @returns {string} Formatted number string
 */
function fmt(n) {
  if (isNaN(n)) return '0.00';
  return (Math.round(n * 100) / 100).toFixed(2);
}

/**
 * Recompute the summary display for a dynamic adjustment panel
 * @param {string|number} compId - Component ID
 * @param {string|number} pid - Participant ID
 * @param {Object} baseMap - Map of participant IDs to base values
 */
function recomputeDynamicPanel(compId, pid, baseMap) {
  const modeSel = document.getElementById(`mode_comp_${compId}_${pid}`);
  if (!modeSel) return;
  
  const mode = modeSel.value;
  const summary = document.querySelector(`[data-redis-summary='comp-${compId}-${pid}'] small`);
  const base = parseFloat(baseMap[String(pid)] || baseMap[pid] || 0);
  
  let sum = 0;
  const inputs = document.querySelectorAll(`input[id^=redis_comp_${compId}_${pid}_]`);
  const values = [];
  inputs.forEach(inp => {
    const v = parseFloat(inp.value);
    values.push(isNaN(v) ? 0 : v);
    if (!isNaN(v)) sum += v;
  });
  
  // Update computed amounts next to each input
  let idx = 0;
  inputs.forEach(inp => {
    const targetId = inp.id.split('_').pop();
    const computedSpan = document.querySelector(`[data-computed='comp-${compId}-${pid}-${targetId}'] small`);
    if (computedSpan) {
      const v = values[idx];
      if (mode === 'percent' && v > 0) {
        // Show computed amount for percentage
        const computed = (v / 100) * base;
        computedSpan.textContent = `= ₱${fmt(computed)}`;
      } else {
        computedSpan.textContent = '';
      }
    }
    idx++;
  });
  
  if (mode === 'percent') {
    const diff = 100 - sum;
    if (Math.abs(diff) < 0.01) {
      summary.textContent = `Sum: ${fmt(sum)}% ✓`;
      summary.style.color = 'var(--success-color, #2e7d32)';
    } else {
      summary.textContent = `Sum: ${fmt(sum)}% (needs ${fmt(diff)}% more)`;
      summary.style.color = 'var(--error-color, #b00020)';
    }
  } else if (mode === 'amount') {
    const diff = base - sum;
    if (Math.abs(diff) < 0.01) {
      summary.textContent = `Sum: ₱${fmt(sum)} ✓`;
      summary.style.color = 'var(--success-color, #2e7d32)';
    } else {
      summary.textContent = `Sum: ₱${fmt(sum)} (needs ₱${fmt(diff)} more)`;
      summary.style.color = 'var(--error-color, #b00020)';
    }
  } else {
    const anyVal = Array.from(inputs).some(inp => {
      const v = parseFloat(inp.value);
      return !isNaN(v) && v > 0;
    });
    summary.textContent = anyVal ? 'Select a mode (Percent or Amount) or clear values' : 'No redistribution';
    summary.style.color = anyVal ? 'var(--error-color, #b00020)' : 'var(--muted-color, #666)';
  }
}

/**
 * Wire up event handlers for dynamic adjustments
 * @param {Array} componentIds - Array of component IDs
 * @param {Object} dynamicBaseMaps - Map of component ID to participant base values
 */
function wireDynamicAdjustments(componentIds, dynamicBaseMaps) {
  (componentIds || []).forEach(compId => {
    const baseMap = dynamicBaseMaps[String(compId)] || dynamicBaseMaps[compId] || {};
    const rows = document.querySelectorAll(`[data-panel^='comp-${compId}-']`);
    
    rows.forEach(panel => {
      const pid = panel.getAttribute('data-panel').split('-').pop();
      const modeSel = document.getElementById(`mode_comp_${compId}_${pid}`);
      if (!modeSel) return;
      
      modeSel.addEventListener('change', () => {
        panel.style.display = modeSel.value ? 'block' : 'none';
        recomputeDynamicPanel(compId, pid, baseMap);
      });
      
      const inputs = document.querySelectorAll(`input[id^=redis_comp_${compId}_${pid}_]`);
      inputs.forEach(inp => inp.addEventListener('input', () => {
        panel.style.display = 'block';
        recomputeDynamicPanel(compId, pid, baseMap);
      }));
      
      // Open panel if there is an existing rule or mode selected
      const hasExisting = Array.from(inputs).some(i => {
        const v = parseFloat(i.value);
        return !isNaN(v) && v > 0;
      }) || (modeSel.value === 'percent' || modeSel.value === 'amount');
      
      if (hasExisting) {
        panel.style.display = 'block';
      }
      
      recomputeDynamicPanel(compId, pid, baseMap);
    });
  });
  
  // Per-component toggle buttons
  document.querySelectorAll('.comp-adj-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const compId = btn.getAttribute('data-comp');
      const panels = document.querySelectorAll(`[data-panel^='comp-${compId}-']`);
      const anyVisible = Array.from(panels).some(p => getComputedStyle(p).display !== 'none');
      const nextShow = !anyVisible;
      
      panels.forEach(p => p.style.display = nextShow ? 'block' : 'none');
      
      const icon = btn.querySelector('.adj-toggle-icon');
      if (icon) icon.textContent = nextShow ? '▾' : '▸';
      btn.setAttribute('aria-expanded', nextShow ? 'true' : 'false');
    });
  });
  
  // Global toggle all button
  document.querySelectorAll('.comp-adj-toggle-all').forEach(btn => {
    btn.addEventListener('click', () => {
      const panels = document.querySelectorAll('.comp-redis-box');
      const anyVisible = Array.from(panels).some(p => getComputedStyle(p).display !== 'none');
      const nextShow = !anyVisible;
      
      panels.forEach(p => p.style.display = nextShow ? 'block' : 'none');
      
      const icon = btn.querySelector('.adj-toggle-icon');
      if (icon) icon.textContent = nextShow ? '▾' : '▸';
      btn.setAttribute('aria-expanded', nextShow ? 'true' : 'false');
    });
  });
}
