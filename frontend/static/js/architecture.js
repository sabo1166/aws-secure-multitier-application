// Architecture view: steps a small packet along the real paths of each traffic flow, highlights the
// components involved, and shows what each one is for. Everything it shows comes from
// /static/data/architecture.json; the page is fully readable without this script.
(function () {
  'use strict';

  var svg = document.getElementById('arch-svg');
  if (!svg) return;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');

  var packet = document.getElementById('packet');
  var tag = document.getElementById('edge-tag');
  var tagText = tag.querySelector('text');
  var tagBg = tag.querySelector('rect');
  var nodes = [].slice.call(svg.querySelectorAll('[data-component]'));
  var stepCount = document.getElementById('step-count');
  var stepTitle = document.getElementById('step-title');
  var stepText = document.getElementById('step-text');
  var inspector = document.getElementById('inspector');
  var btnPlay = document.getElementById('ctl-play');
  var btnBack = document.getElementById('ctl-back');
  var btnNext = document.getElementById('ctl-next');
  var btnReplay = document.getElementById('ctl-replay');
  var flowButtons = [].slice.call(document.querySelectorAll('.flow-btn'));

  var flows = [];
  var flow = null;
  var stepIndex = -1;
  var playing = false;
  var run = 0;                    // incremented to cancel any animation or timer in flight
  var selected = null;

  function el(id) { return document.getElementById(id); }

  function clearHighlights() {
    nodes.forEach(function (n) { n.classList.remove('is-active', 'is-dim'); });
    [].forEach.call(svg.querySelectorAll('.edge.is-active-edge'), function (e) { e.classList.remove('is-active-edge'); });
    packet.setAttribute('visibility', 'hidden');
    tag.setAttribute('visibility', 'hidden');
  }

  function setPlaying(on) {
    playing = on;
    btnPlay.textContent = on ? 'Pause' : 'Play';
    btnPlay.setAttribute('aria-pressed', on ? 'true' : 'false');
  }

  function updateButtons() {
    btnBack.disabled = stepIndex <= 0;
    btnNext.disabled = !flow || stepIndex >= flow.steps.length - 1;
  }

  function showFlowIntro() {
    clearHighlights();
    stepCount.textContent = flow.steps.length + ' steps';
    stepTitle.textContent = flow.title;
    stepText.textContent = flow.intro;
    updateButtons();
  }

  function highlight(step) {
    clearHighlights();
    nodes.forEach(function (n) {
      var on = step.focus.indexOf(n.getAttribute('data-component')) !== -1;
      n.classList.add(on ? 'is-active' : 'is-dim');
    });
    step.edges.forEach(function (e) { var p = el(e.id); if (p) p.classList.add('is-active-edge'); });
    stepCount.textContent = 'Step ' + (stepIndex + 1) + ' of ' + flow.steps.length + ' · ' + flow.title;
    stepTitle.textContent = step.label;
    stepText.textContent = step.text;
    updateButtons();
  }

  function placeTag(path, label) {
    var mid = path.getPointAtLength(path.getTotalLength() / 2);
    tagText.textContent = label;
    var w = Math.ceil(tagText.getComputedTextLength()) + 16;
    tagBg.setAttribute('width', w);
    tag.setAttribute('transform', 'translate(' + Math.round(mid.x - w / 2) + ',' + Math.round(mid.y - 34) + ')');
    tag.setAttribute('visibility', 'visible');
  }

  // Move the packet along each edge of the step in turn, then call done().
  function travel(step, token, done) {
    var edges = step.edges.slice();
    function next() {
      if (token !== run) return;
      var spec = edges.shift();
      if (!spec) { packet.setAttribute('visibility', 'hidden'); tag.setAttribute('visibility', 'hidden'); done(); return; }
      var path = el(spec.id);
      if (!path) { next(); return; }
      var len = path.getTotalLength();
      var ms = Math.max(550, Math.min(1300, len * 3.2));
      if (edges.length === step.edges.length - 1) placeTag(path, step.label);
      packet.setAttribute('visibility', 'visible');
      var start = performance.now();
      (function frame(now) {
        if (token !== run) return;
        var p = Math.min(1, (now - start) / ms);
        var at = spec.reverse ? len * (1 - p) : len * p;
        var pt = path.getPointAtLength(at);
        packet.setAttribute('cx', pt.x);
        packet.setAttribute('cy', pt.y);
        if (p < 1) requestAnimationFrame(frame); else next();
      })(start);
    }
    next();
  }

  function goTo(i, animate) {
    run++;
    var token = run;
    stepIndex = i;
    var step = flow.steps[i];
    highlight(step);
    if (animate && !reduce.matches) {
      travel(step, token, function () {
        if (!playing || token !== run) return;
        if (stepIndex >= flow.steps.length - 1) { setPlaying(false); return; }
        setTimeout(function () { if (playing && token === run) goTo(stepIndex + 1, true); }, 800);
      });
    } else if (playing) {
      setPlaying(false);            // with reduced motion there is nothing to autoplay
    }
  }

  function setFlow(id) {
    run++;
    setPlaying(false);
    flow = flows.filter(function (f) { return f.id === id; })[0];
    stepIndex = -1;
    flowButtons.forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.flow === id ? 'true' : 'false'); });
    showFlowIntro();
  }

  function play() {
    if (reduce.matches) { goTo(Math.min(stepIndex + 1, flow.steps.length - 1), false); return; }
    setPlaying(true);
    goTo(stepIndex >= flow.steps.length - 1 || stepIndex < 0 ? 0 : stepIndex + 1, true);
  }

  btnPlay.addEventListener('click', function () {
    if (playing) { run++; setPlaying(false); packet.setAttribute('visibility', 'hidden'); tag.setAttribute('visibility', 'hidden'); }
    else play();
  });
  btnNext.addEventListener('click', function () { setPlaying(false); if (stepIndex < flow.steps.length - 1) goTo(stepIndex + 1, !reduce.matches); });
  btnBack.addEventListener('click', function () { setPlaying(false); if (stepIndex > 0) goTo(stepIndex - 1, false); });
  btnReplay.addEventListener('click', function () { stepIndex = -1; clearHighlights(); play(); });
  flowButtons.forEach(function (b) { b.addEventListener('click', function () { setFlow(b.dataset.flow); if (!reduce.matches) play(); }); });

  // ---- component inspector ----
  function select(id) {
    selected = id;
    nodes.forEach(function (n) { n.classList.toggle('is-selected', n.getAttribute('data-component') === id); });
    while (inspector.firstChild) inspector.removeChild(inspector.firstChild);
    var card = id && document.getElementById('c-' + id);
    if (!card) {
      var p = document.createElement('p');
      p.className = 'inspector-empty';
      p.textContent = 'Select a component to see its responsibility, its controls, and the evidence it still needs.';
      inspector.appendChild(p);
      return;
    }
    var copy = card.cloneNode(true);
    copy.removeAttribute('id');                      // avoid duplicate ids
    [].forEach.call(copy.querySelectorAll('[id]'), function (x) { x.removeAttribute('id'); });
    inspector.appendChild(copy);
  }

  nodes.forEach(function (n) {
    var id = n.getAttribute('data-component');
    n.addEventListener('click', function () { select(selected === id ? null : id); });
    n.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(selected === id ? null : id); }
    });
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && selected) select(null); });

  if (reduce.addEventListener) reduce.addEventListener('change', function () { if (reduce.matches) { run++; setPlaying(false); clearHighlights(); } });

  fetch('/static/data/architecture.json', { credentials: 'same-origin' })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      flows = data.flows;
      setFlow(flows[0].id);
      if (!reduce.matches) setTimeout(play, 700);
    })
    .catch(function () {
      stepText.textContent = 'The animation data could not be loaded. The diagram and the text below it are complete without it.';
    });
})();
