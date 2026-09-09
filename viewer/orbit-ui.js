// On-screen orbit controls for the splat pages: a direction pad, an auto-rotate
// toggle for showing a full 360 hands-free, zoom, and reset. One shared file so
// the five viewer pages cannot drift apart. Plain script, works over file://.
(function () {
  var STEP = Math.PI / 24;        // a tap nudges 7.5 degrees
  var HOLD_DELAY = 280;           // ms before a hold becomes continuous
  var HOLD_RATE = 0.011;          // radians per frame while held

  var CSS = [
    '.orbit-ui{position:absolute;left:50%;bottom:12px;transform:translateX(-50%);z-index:5;',
    'display:flex;align-items:center;gap:10px;padding:7px 9px;border-radius:12px;',
    'background:rgba(8,7,6,.72);border:1px solid rgba(216,180,90,.24);',
    'backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px)}',
    '.orbit-pad{display:grid;grid-template-columns:repeat(3,30px);grid-template-rows:repeat(2,26px);gap:3px}',
    '.orbit-ui button{font:inherit;font-size:12px;line-height:1;color:#f3eadc;cursor:pointer;',
    'background:linear-gradient(180deg,rgba(38,30,24,.9),rgba(20,16,13,.9));',
    'border:1px solid rgba(216,180,90,.28);border-radius:7px;padding:0;',
    'display:grid;place-items:center;user-select:none;-webkit-user-select:none;touch-action:none;',
    'transition:border-color .15s,background-color .15s,color .15s}',
    '.orbit-ui button:hover{border-color:rgba(216,180,90,.75);color:#f0d68e}',
    '.orbit-ui button:active{background:rgba(216,180,90,.85);color:#17100c}',
    '.orbit-ui button:focus-visible{outline:2px solid #f0d68e;outline-offset:2px}',
    '.orbit-pad .up{grid-area:1/2}.orbit-pad .left{grid-area:2/1}',
    '.orbit-pad .down{grid-area:2/2}.orbit-pad .right{grid-area:2/3}',
    '.orbit-sep{width:1px;height:30px;background:rgba(216,180,90,.22)}',
    '.orbit-ui .wide{height:26px;padding:0 10px;font-size:11.5px;white-space:nowrap}',
    '.orbit-ui .wide.on{background:linear-gradient(180deg,#f0d68e,#d8b45a);color:#17100c;border-color:#f0d68e}',
    '.orbit-zoom{display:grid;grid-template-rows:repeat(2,26px);gap:3px}',
    '.orbit-zoom button{width:30px}',
    '@media(max-width:560px){.orbit-ui{gap:7px;padding:6px}.orbit-pad{grid-template-columns:repeat(3,27px)}}'
  ].join('');

  function hold(btn, onStep, onFrame) {
    var timer = null, raf = null;
    function stop() {
      if (timer) { clearTimeout(timer); timer = null; }
      if (raf) { cancelAnimationFrame(raf); raf = null; }
    }
    btn.addEventListener('pointerdown', function (e) {
      e.preventDefault();
      btn.setPointerCapture && btn.setPointerCapture(e.pointerId);
      onStep();                                  // a tap moves a fixed step
      timer = setTimeout(function () {           // a hold keeps going smoothly
        var tick = function () { onFrame(); raf = requestAnimationFrame(tick); };
        raf = requestAnimationFrame(tick);
      }, HOLD_DELAY);
    });
    ['pointerup', 'pointercancel', 'pointerleave'].forEach(function (ev) {
      btn.addEventListener(ev, stop);
    });
    window.addEventListener('blur', stop);
  }

  function build() {
    var stage = document.querySelector('.stage');
    if (!stage || !window.splatOrbit || stage.querySelector('.orbit-ui')) return;

    var st = document.createElement('style');
    st.textContent = CSS;
    document.head.appendChild(st);

    var bar = document.createElement('div');
    bar.className = 'orbit-ui';
    bar.innerHTML =
      '<div class="orbit-pad">' +
        '<button class="up"    title="Tilt up"      aria-label="Tilt up">&#9650;</button>' +
        '<button class="left"  title="Rotate left"  aria-label="Rotate left">&#9664;</button>' +
        '<button class="down"  title="Tilt down"    aria-label="Tilt down">&#9660;</button>' +
        '<button class="right" title="Rotate right" aria-label="Rotate right">&#9654;</button>' +
      '</div>' +
      '<div class="orbit-zoom">' +
        '<button class="zin"  title="Zoom in"  aria-label="Zoom in">+</button>' +
        '<button class="zout" title="Zoom out" aria-label="Zoom out">&minus;</button>' +
      '</div>' +
      '<div class="orbit-sep"></div>' +
      '<button class="wide auto" title="Rotate continuously" aria-pressed="false">Auto&nbsp;360</button>' +
      '<button class="wide reset" title="Back to the opening view">Reset</button>';
    stage.appendChild(bar);

    var O = window.splatOrbit;
    var q = function (s) { return bar.querySelector(s); };
    hold(q('.left'),  function () { O.nudge(-STEP, 0); }, function () { O.nudge(-HOLD_RATE, 0); });
    hold(q('.right'), function () { O.nudge(STEP, 0); },  function () { O.nudge(HOLD_RATE, 0); });
    hold(q('.up'),    function () { O.nudge(0, STEP); },  function () { O.nudge(0, HOLD_RATE); });
    hold(q('.down'),  function () { O.nudge(0, -STEP); }, function () { O.nudge(0, -HOLD_RATE); });
    hold(q('.zin'),   function () { O.zoom(0.88); },      function () { O.zoom(0.995); });
    hold(q('.zout'),  function () { O.zoom(1.14); },      function () { O.zoom(1.005); });

    var auto = q('.auto');
    auto.addEventListener('click', function () {
      var on = O.auto(!O.autoOn());
      auto.classList.toggle('on', on);
      auto.setAttribute('aria-pressed', String(on));
    });
    q('.reset').addEventListener('click', function () {
      O.reset();
      auto.classList.remove('on');
      auto.setAttribute('aria-pressed', 'false');
    });
    // a drag on the canvas stops auto-rotation inside the renderer; reflect that
    setInterval(function () {
      var on = O.autoOn();
      if (auto.classList.contains('on') !== on) {
        auto.classList.toggle('on', on);
        auto.setAttribute('aria-pressed', String(on));
      }
    }, 400);
  }

  // splatOrbit only exists once the renderer has started, so wait for it
  var tries = 0;
  var wait = setInterval(function () {
    if (window.splatOrbit || ++tries > 200) { clearInterval(wait); build(); }
  }, 100);
})();
