/**
 * Industry redesign behaviors for the month detail view:
 * - Grid/Ledger table layout toggle (persisted in localStorage)
 * - Live meter usage recalculation + grid/ledger input mirroring
 * - "Edit amounts" toggle for component bill totals
 * - Split-method segmented control + custom share sum validation
 * - Transient "Readings saved" confirmation
 */
(function () {
  'use strict';

  var CURRENCY = '₱';

  function num(n) {
    n = Number(n) || 0;
    return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  /* ── Grid / Ledger layout toggle ─────────────────────────────────── */
  function initLayoutToggle() {
    var root = document.getElementById('layout-root');
    var seg = document.getElementById('layout-seg');
    if (!root || !seg) return;

    var saved = 'grid';
    try { saved = localStorage.getItem('bo-table-layout') || 'grid'; } catch (e) { /* private mode */ }
    apply(saved);

    seg.addEventListener('change', function (e) {
      if (e.target.name === 'bo-layout') {
        apply(e.target.value);
        try { localStorage.setItem('bo-table-layout', e.target.value); } catch (err) { /* ignore */ }
      }
    });

    function apply(style) {
      style = style === 'ledger' ? 'ledger' : 'grid';
      root.classList.toggle('layout-grid', style === 'grid');
      root.classList.toggle('layout-ledger', style === 'ledger');
      var radio = seg.querySelector('input[value="' + style + '"]');
      if (radio) radio.checked = true;
    }
  }

  /* ── Meter readings: mirroring + live usage ──────────────────────── */
  function initReadings() {
    var named = document.querySelectorAll('input[data-reading]');
    if (!named.length) return;

    var byKey = {};
    named.forEach(function (inp) { byKey[inp.getAttribute('data-reading')] = inp; });

    document.querySelectorAll('input[data-mirror]').forEach(function (mirror) {
      var source = byKey[mirror.getAttribute('data-mirror')];
      if (!source) return;
      mirror.addEventListener('input', function () {
        source.value = mirror.value;
        recompute(source);
      });
      source.addEventListener('input', function () {
        mirror.value = source.value;
      });
    });

    named.forEach(function (inp) {
      inp.addEventListener('input', function () { recompute(inp); });
    });

    function recompute(inp) {
      var key = inp.getAttribute('data-reading');
      var pid = key.split('-').slice(1).join('-');
      var prev = byKey['prev-' + pid];
      var curr = byKey['curr-' + pid];
      var usage = Math.max(0, (parseFloat(curr && curr.value) || 0) - (parseFloat(prev && prev.value) || 0));
      document.querySelectorAll('[data-usage-for="' + pid + '"]').forEach(function (el) {
        el.textContent = num(usage);
      });
    }
  }

  /* ── Edit amounts toggle ─────────────────────────────────────────── */
  function initEditAmounts() {
    var btn = document.getElementById('edit-amounts-toggle');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var on = btn.getAttribute('aria-pressed') !== 'true';
      btn.setAttribute('aria-pressed', String(on));
      btn.classList.toggle('btn-primary', on);
      btn.classList.toggle('btn-secondary', !on);
      document.querySelectorAll('input[data-bill-total]').forEach(function (inp) {
        inp.disabled = !on;
      });
    });
  }

  /* ── Component split methods + custom share validation ───────────── */
  function initAdjustBlocks() {
    document.querySelectorAll('[data-adjust-block]').forEach(function (block) {
      var form = block.querySelector('[data-component-form]');
      if (!form) return;
      var custom = form.querySelector('[data-custom-block]');
      var totalInput = form.querySelector('input[data-bill-total]');

      form.querySelectorAll('input[data-method-radio]').forEach(function (radio) {
        radio.addEventListener('change', function () { update(); });
      });
      form.querySelectorAll('input[data-share-input]').forEach(function (inp) {
        inp.addEventListener('input', function () { update(); });
      });
      if (totalInput) totalInput.addEventListener('input', function () { update(); });

      update();

      function method() {
        var checked = form.querySelector('input[data-method-radio]:checked');
        return checked ? checked.value : 'equal';
      }

      function update() {
        var m = method();
        var isCustom = m === 'amount' || m === 'percentage';
        if (custom) custom.hidden = !isCustom;
        if (!custom || !isCustom) return;

        var total = parseFloat(totalInput && totalInput.value) || 0;
        var sum = 0;
        form.querySelectorAll('input[data-share-input]').forEach(function (inp) {
          sum += parseFloat(inp.value) || 0;
          var derived = inp.parentElement.querySelector('[data-share-derived]');
          if (derived) {
            var v = parseFloat(inp.value) || 0;
            derived.textContent = (m === 'percentage' && v) ? '= ' + CURRENCY + num(total * v / 100) : '';
          }
        });

        var line = custom.querySelector('[data-sum-line]');
        var value = custom.querySelector('[data-sum-value]');
        var ok;
        if (m === 'amount') {
          ok = Math.abs(sum - total) < 0.01;
          if (value) value.textContent = CURRENCY + num(sum) + ' / ' + CURRENCY + num(total);
        } else {
          ok = Math.abs(sum - 100) < 0.02;
          if (value) value.textContent = sum.toFixed(2) + '% / 100%';
        }
        if (line) line.classList.toggle('invalid', !ok);
      }
    });
  }

  /* ── Transient save confirmation ─────────────────────────────────── */
  function initSaveConfirm() {
    var confirmEl = document.getElementById('save-confirm');
    if (!confirmEl) return;
    try {
      var url = new URL(window.location.href);
      url.searchParams.delete('saved');
      window.history.replaceState({}, '', url);
    } catch (e) { /* ignore */ }
    setTimeout(function () {
      confirmEl.classList.add('fading');
      setTimeout(function () { confirmEl.remove(); }, 500);
    }, 2000);
  }

  document.addEventListener('DOMContentLoaded', function () {
    initLayoutToggle();
    initReadings();
    initEditAmounts();
    initAdjustBlocks();
    initSaveConfirm();
  });
})();
