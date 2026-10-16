// Roadmap: turns the server-rendered phase list into an accessible tab interface.
// Without JavaScript every phase stays expanded and the phase links jump to their section.
(function () {
  'use strict';

  var nodes = [].slice.call(document.querySelectorAll('.phase-node'));
  var panels = [].slice.call(document.querySelectorAll('.phase-panel'));
  var track = document.querySelector('.phase-track');
  if (!nodes.length || nodes.length !== panels.length || !track) return;

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  var narrow = window.matchMedia('(max-width: 760px)');

  track.setAttribute('role', 'tablist');
  track.setAttribute('aria-orientation', narrow.matches ? 'vertical' : 'horizontal');
  narrow.addEventListener('change', function () { track.setAttribute('aria-orientation', narrow.matches ? 'vertical' : 'horizontal'); });
  [].forEach.call(track.querySelectorAll('.phase-item'), function (li) { li.setAttribute('role', 'presentation'); });

  nodes.forEach(function (n) {
    n.setAttribute('role', 'tab');
    n.id = 'tab-' + n.dataset.phase;
    n.setAttribute('aria-controls', 'phase-' + n.dataset.phase);
  });
  panels.forEach(function (p) { p.setAttribute('role', 'tabpanel'); });

  function select(num, opts) {
    opts = opts || {};
    var chosen = null;
    nodes.forEach(function (n) {
      var on = n.dataset.phase === String(num);
      n.setAttribute('aria-selected', on ? 'true' : 'false');
      n.setAttribute('tabindex', on ? '0' : '-1');
      n.classList.toggle('is-selected', on);
      if (on) chosen = n;
    });
    panels.forEach(function (p) {
      var on = p.dataset.phase === String(num);
      p.hidden = !on;
      p.classList.remove('is-entering');
      if (on && opts.animate) {
        void p.offsetWidth;                         // restart the CSS animation
        p.classList.add('is-entering');
      }
    });
    if (!chosen) return;
    if (opts.focus) chosen.focus();
    if (opts.updateHash !== false && history.replaceState) history.replaceState(null, '', '#phase-' + num);
    if (opts.scroll && narrow.matches) {
      document.getElementById('phase-' + num).scrollIntoView({ behavior: reduce.matches ? 'auto' : 'smooth', block: 'start' });
    }
  }

  function initialPhase() {
    var m = /^#phase-(\d+)$/.exec(location.hash);
    if (m && document.getElementById('phase-' + m[1])) return m[1];
    var active = track.querySelector('.state-in_progress, .state-blocked');
    return active ? active.querySelector('.phase-node').dataset.phase : nodes[0].dataset.phase;
  }

  nodes.forEach(function (n, i) {
    n.addEventListener('click', function (e) { e.preventDefault(); select(n.dataset.phase, { animate: true, scroll: true }); });
    n.addEventListener('keydown', function (e) {
      var next = null;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') next = nodes[(i + 1) % nodes.length];
      else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') next = nodes[(i - 1 + nodes.length) % nodes.length];
      else if (e.key === 'Home') next = nodes[0];
      else if (e.key === 'End') next = nodes[nodes.length - 1];
      if (next) { e.preventDefault(); select(next.dataset.phase, { animate: true, focus: true }); }
    });
  });

  window.addEventListener('hashchange', function () {
    var m = /^#phase-(\d+)$/.exec(location.hash);
    if (m && document.getElementById('phase-' + m[1])) select(m[1], { animate: true, updateHash: false });
  });

  select(initialPhase(), { updateHash: false });
})();
