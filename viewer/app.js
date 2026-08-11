// Sala Chaturamuk Phaichit viewer.
//
// Drag horizontally to rotate. The frames are photographs and flow-interpolated
// in-between views produced by src/interpolate.py -- there is no 3D model here,
// nothing is rendered, we only choose which frame to show.
//
// The capture is a PARTIAL ARC (the lake blocks the far side), so the ends are
// clamped: dragging past either end stops rather than wrapping to the start.

(function () {
  "use strict";

  var els = {
    stage: document.getElementById("stage"),
    image: document.getElementById("frame"),
    status: document.getElementById("status"),
    angle: document.getElementById("angle"),
    counter: document.getElementById("counter"),
    mode: document.getElementById("mode"),
    progress: document.getElementById("progress"),
    bar: document.getElementById("bar"),
  };

  var manifest = null;
  var active = [];        // frames for the current mode
  var position = 0;       // index into `active`
  var interpolated = true;

  function fail(message) {
    els.status.textContent = message;
    els.status.classList.add("error");
  }

  function loadManifest() {
    if (window.SALA_MANIFEST) return Promise.resolve(window.SALA_MANIFEST);
    // Fallback for when the page is served over http(s). Browsers refuse this
    // over file://, which is why build_sequence.py also emits manifest.js.
    return fetch("manifest.json").then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  function setMode(useInterpolated) {
    if (!manifest) return;
    var previous = active[position];
    interpolated = useInterpolated;
    active = useInterpolated
      ? manifest.frames
      : manifest.frames.filter(function (f) { return f.real; });

    // Keep looking at roughly the same angle when the mode changes.
    if (previous) {
      var best = 0;
      for (var i = 1; i < active.length; i++) {
        if (Math.abs(active[i].index - previous.index) <
            Math.abs(active[best].index - previous.index)) best = i;
      }
      position = best;
    }
    els.mode.textContent = useInterpolated
      ? "Interpolated — " + active.length + " frames"
      : "Baseline (captured only) — " + active.length + " frames";
    show(position);
  }

  function show(index) {
    if (!active.length) return;
    position = Math.max(0, Math.min(active.length - 1, index)); // clamp: partial arc
    var frame = active[position];
    els.image.src = frame.file;
    els.counter.textContent = (position + 1) + " / " + active.length +
      (frame.real ? "  captured" : "  synthesized");
    els.angle.textContent = frame.angle_deg === null || frame.angle_deg === undefined
      ? "—"
      : frame.angle_deg.toFixed(1) + "°";
  }

  function preload(frames) {
    var loaded = 0;
    els.progress.hidden = false;
    frames.forEach(function (frame) {
      var img = new Image();
      var done = function () {
        loaded++;
        els.bar.style.width = ((loaded / frames.length) * 100).toFixed(1) + "%";
        if (loaded === frames.length) {
          els.progress.hidden = true;
          els.status.textContent = "Drag to rotate";
        }
      };
      img.onload = done;
      img.onerror = done;
      img.src = frame.file;
    });
  }

  // --- input -----------------------------------------------------------------

  var dragging = false;
  var lastX = 0;
  var accumulated = 0;

  function pointerDown(event) {
    dragging = true;
    lastX = (event.touches ? event.touches[0] : event).clientX;
    accumulated = 0;
    els.stage.classList.add("dragging");
  }

  function pointerMove(event) {
    if (!dragging) return;
    var x = (event.touches ? event.touches[0] : event).clientX;
    accumulated += x - lastX;
    lastX = x;
    // One frame per N pixels of drag, scaled so a full sweep is one stage width.
    var pixelsPerFrame = Math.max(4, els.stage.clientWidth / Math.max(active.length, 1));
    while (Math.abs(accumulated) >= pixelsPerFrame) {
      show(position - Math.sign(accumulated));
      accumulated -= Math.sign(accumulated) * pixelsPerFrame;
    }
    if (event.cancelable) event.preventDefault();
  }

  function pointerUp() {
    dragging = false;
    els.stage.classList.remove("dragging");
  }

  els.stage.addEventListener("mousedown", pointerDown);
  window.addEventListener("mousemove", pointerMove);
  window.addEventListener("mouseup", pointerUp);
  els.stage.addEventListener("touchstart", pointerDown, { passive: true });
  els.stage.addEventListener("touchmove", pointerMove, { passive: false });
  els.stage.addEventListener("touchend", pointerUp);

  window.addEventListener("keydown", function (event) {
    if (event.key === "ArrowLeft") show(position - 1);
    else if (event.key === "ArrowRight") show(position + 1);
    else if (event.key === "Home") show(0);
    else if (event.key === "End") show(active.length - 1);
    else if (event.key.toLowerCase() === "b") {
      document.getElementById("toggle").checked = !interpolated;
      setMode(!interpolated);
    } else return;
    event.preventDefault();
  });

  document.getElementById("toggle").addEventListener("change", function (event) {
    setMode(event.target.checked);
  });

  // --- start -----------------------------------------------------------------

  loadManifest().then(function (data) {
    manifest = data;
    if (!manifest.frames || !manifest.frames.length) {
      fail("Manifest contains no frames. Run src/build_sequence.py first.");
      return;
    }
    document.getElementById("summary").textContent =
      manifest.n_captured + " captured, " + manifest.n_synthesized + " synthesized" +
      (manifest.angular_step_deg ? ", " + manifest.angular_step_deg + "° capture step" : "");
    setMode(true);
    preload(manifest.frames);
  }).catch(function (error) {
    fail("Could not load the manifest (" + error.message + "). " +
         "Run:  python src/build_sequence.py --frames output/sequence/ --out viewer/manifest.json");
  });
})();
