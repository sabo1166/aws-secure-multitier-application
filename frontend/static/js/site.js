// SOLE ATELIER storefront behaviour. Vanilla JS; the server is always the source of truth for prices and stock.
(function () {
  'use strict';

  var csrf = (document.querySelector('meta[name="csrf-token"]') || {}).content || '';

  function api(method, url, body) {
    var opts = { method: method, headers: { 'X-CSRF-Token': csrf, 'Accept': 'application/json' }, credentials: 'same-origin' };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    return fetch(url, opts).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        return { ok: res.ok, status: res.status, data: data };
      });
    }).catch(function () {
      return { ok: false, status: 0, data: { error: { message: 'Network problem. Please check your connection and try again.' } } };
    });
  }

  function errorMessage(r) {
    return (r.data && r.data.error && r.data.error.message) || 'Something went wrong. Please try again.';
  }

  var toastTimer;
  function toast(message, isError) {
    var el = document.getElementById('toast');
    if (!el) return;
    el.textContent = message;
    el.classList.toggle('error', !!isError);
    el.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.classList.remove('show'); }, 4200);
  }

  function setCount(n) {
    document.querySelectorAll('[data-cart-count]').forEach(function (el) {
      el.textContent = n;
      el.classList.remove('bump'); void el.offsetWidth; el.classList.add('bump');
    });
    var bag = document.querySelector('.bag');
    if (bag) bag.setAttribute('aria-label', 'Shopping bag, ' + n + (n === 1 ? ' item' : ' items'));
  }

  // --- Mobile navigation ---
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('primary-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && nav.classList.contains('open')) {
        nav.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.focus();
      }
    });
  }

  // --- Sort select submits its form ---
  document.querySelectorAll('[data-autosubmit]').forEach(function (sel) {
    sel.addEventListener('change', function () { sel.form.submit(); });
  });

  // --- Quick add on product cards ---
  document.querySelectorAll('[data-quick-add]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var panel = document.getElementById(btn.getAttribute('aria-controls'));
      var open = panel.hasAttribute('hidden');
      if (open) panel.removeAttribute('hidden'); else panel.setAttribute('hidden', '');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  });
  document.querySelectorAll('[data-add]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      btn.disabled = true;
      api('POST', '/api/cart/items', { product_id: Number(btn.dataset.productId), size: btn.dataset.size, quantity: 1 }).then(function (r) {
        btn.disabled = false;
        if (r.ok) { setCount(r.data.count); toast('Added to your bag (US ' + btn.dataset.size + ')'); }
        else toast(errorMessage(r), true);
      });
    });
  });

  // --- Product detail page ---
  var addForm = document.getElementById('add-form');
  if (addForm) {
    var qty = document.getElementById('qty');
    var status = document.getElementById('stock-status');
    var err = document.getElementById('add-error');
    var maxQty = function () {
      var chosen = addForm.querySelector('input[name="size"]:checked');
      return Math.max(1, Math.min(5, chosen ? Number(chosen.dataset.stock) : 5));
    };
    addForm.querySelectorAll('input[name="size"]').forEach(function (radio) {
      radio.addEventListener('change', function () {
        var stock = Number(radio.dataset.stock);
        status.className = 'stock-status ' + (stock > 0 ? 'in' : 'out');
        status.textContent = stock <= 3 ? 'Low stock: only ' + stock + ' left in US ' + radio.value + '.' : 'In stock in US ' + radio.value + '.';
        if (qty) { qty.max = maxQty(); if (Number(qty.value) > maxQty()) qty.value = maxQty(); }
        err.textContent = '';
      });
    });
    addForm.querySelectorAll('[data-qty-step]').forEach(function (b) {
      b.addEventListener('click', function () {
        var next = Number(qty.value || 1) + Number(b.dataset.qtyStep);
        qty.value = Math.min(maxQty(), Math.max(1, next));
      });
    });
    addForm.addEventListener('submit', function (e) {
      e.preventDefault();
      err.textContent = '';
      var chosen = addForm.querySelector('input[name="size"]:checked');
      if (!chosen) { err.textContent = 'Please select a size.'; return; }
      var submit = addForm.querySelector('button[type="submit"]');
      submit.disabled = true;
      api('POST', '/api/cart/items', { product_id: Number(addForm.dataset.productId), size: chosen.value, quantity: Math.max(1, Number(qty.value) || 1) }).then(function (r) {
        submit.disabled = false;
        if (r.ok) { setCount(r.data.count); toast('Added to your bag'); }
        else err.textContent = errorMessage(r);
      });
    });
  }

  // --- Cart page ---
  var cartError = document.getElementById('cart-error');
  document.querySelectorAll('.cart-line').forEach(function (line) {
    var id = line.dataset.itemId;
    var current = Number((line.querySelector('output') || {}).textContent || 1);
    line.querySelectorAll('[data-cart-step]').forEach(function (b) {
      b.addEventListener('click', function () {
        b.disabled = true;
        api('PATCH', '/api/cart/items/' + encodeURIComponent(id), { quantity: current + Number(b.dataset.cartStep) }).then(function (r) {
          if (r.ok) location.reload();
          else { b.disabled = false; cartError.textContent = errorMessage(r); }
        });
      });
    });
    var remove = line.querySelector('[data-cart-remove]');
    if (remove) remove.addEventListener('click', function () {
      remove.disabled = true;
      api('DELETE', '/api/cart/items/' + encodeURIComponent(id)).then(function (r) {
        if (r.ok) location.reload();
        else { remove.disabled = false; cartError.textContent = errorMessage(r); }
      });
    });
  });

  // --- Checkout ---
  var checkout = document.getElementById('checkout-form');
  if (checkout) {
    var submitBtn = document.getElementById('place-order');
    var formError = document.getElementById('checkout-error');
    checkout.addEventListener('submit', function (e) {
      e.preventDefault();
      formError.textContent = '';
      checkout.querySelectorAll('[data-error-for]').forEach(function (s) { s.textContent = ''; });
      var payload = {};
      new FormData(checkout).forEach(function (v, k) { payload[k] = String(v); });
      submitBtn.disabled = true;                  // blocks double clicks; the idempotency key blocks replays
      submitBtn.textContent = 'Placing demo order...';
      api('POST', '/api/orders', payload).then(function (r) {
        if (r.ok && r.data.redirect) { location.assign(r.data.redirect); return; }
        submitBtn.disabled = false;
        submitBtn.textContent = 'Place demo order';
        var details = r.data && r.data.error && r.data.error.details;
        if (r.status === 422 && details) {
          var first = null;
          details.forEach(function (d) {
            var slot = checkout.querySelector('[data-error-for="' + d.field + '"]');
            if (slot) { slot.textContent = d.message; first = first || checkout.querySelector('[name="' + d.field + '"]'); }
          });
          formError.textContent = 'Please correct the highlighted fields.';
          if (first) first.focus();
        } else {
          formError.textContent = errorMessage(r);
        }
      });
    });
  }

  // --- Newsletter (demo) ---
  var news = document.getElementById('newsletter-form');
  if (news) {
    news.addEventListener('submit', function (e) {
      e.preventDefault();
      var msg = document.getElementById('newsletter-msg');
      var email = document.getElementById('news-email').value.trim();
      msg.textContent = '';
      api('POST', '/api/newsletter', { email: email }).then(function (r) {
        msg.textContent = r.ok ? r.data.message : (r.status === 422 ? 'Please enter a valid email address.' : errorMessage(r));
      });
    });
  }
})();
