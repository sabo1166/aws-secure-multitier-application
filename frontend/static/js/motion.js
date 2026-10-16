// SOLE ATELIER motion layer: pointer-driven 3D tilt, scroll reveal, hero entrance, bag bump.
// Presentation only. It never touches prices, stock or the cart; it only sets CSS custom properties (CSP-safe).
(function () {
  'use strict';

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  var root = document.documentElement;

  // Hero entrance: one orchestrated moment after first paint.
  requestAnimationFrame(function () { requestAnimationFrame(function () { root.classList.add('ready'); }); });

  // Scroll reveal for grids, staggered by index within each group.
  var targets = document.querySelectorAll('.grid > *, .tiles > *, .principles li, .story-copy, .cart-line');
  if (!reduce && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    targets.forEach(function (el) {
      var siblings = el.parentElement ? Array.prototype.indexOf.call(el.parentElement.children, el) : 0;
      el.style.setProperty('--i', Math.min(siblings, 6));
      el.classList.add('reveal');
      io.observe(el);
    });
  }

  if (reduce || !finePointer) return;

  // Generic tilt: cards, tiles, product image.
  function bindTilt(el, max) {
    var raf = 0;
    el.addEventListener('pointermove', function (e) {
      var r = el.getBoundingClientRect();
      var px = (e.clientX - r.left) / r.width, py = (e.clientY - r.top) / r.height;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(function () {
        el.classList.add('live');
        el.style.setProperty('--ry', ((px - 0.5) * 2 * max).toFixed(2) + 'deg');
        el.style.setProperty('--rx', ((0.5 - py) * 2 * max).toFixed(2) + 'deg');
        el.style.setProperty('--mx', (px * 100).toFixed(1) + '%');
        el.style.setProperty('--my', (py * 100).toFixed(1) + '%');
      });
    });
    el.addEventListener('pointerleave', function () {
      cancelAnimationFrame(raf);
      el.classList.remove('live');
      el.style.setProperty('--rx', '0deg');
      el.style.setProperty('--ry', '0deg');
    });
  }
  document.querySelectorAll('.card-media, .tile, .pdp-media').forEach(function (el) {
    el.setAttribute('data-tilt', '');
    bindTilt(el, 9);
  });

  // Hero stage: the whole scene tilts, light sweeps across the plate.
  var stage = document.querySelector('.stage');
  var world = stage && stage.querySelector('.stage-world');
  if (stage && world) {
    var hero = stage.closest('.stage-hero') || stage;
    hero.addEventListener('pointermove', function (e) {
      var r = stage.getBoundingClientRect();
      var px = Math.max(-1, Math.min(1, (e.clientX - (r.left + r.width / 2)) / (window.innerWidth / 2)));
      var py = Math.max(-1, Math.min(1, (e.clientY - (r.top + r.height / 2)) / (window.innerHeight / 2)));
      world.classList.add('live');
      world.style.setProperty('--ry', (px * 16).toFixed(2) + 'deg');
      world.style.setProperty('--rx', (-py * 12).toFixed(2) + 'deg');
      world.style.setProperty('--gx', px.toFixed(2));
    });
    hero.addEventListener('pointerleave', function () {
      world.classList.remove('live');
      world.style.setProperty('--rx', '0deg');
      world.style.setProperty('--ry', '0deg');
    });
  }
})();
