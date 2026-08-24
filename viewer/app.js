// Sala Chaturamuk Phaichit viewer.
//
// Drag horizontally to rotate. The frames are photographs and flow-interpolated
// in-between views produced by src/interpolate.py -- there is no 3D model here,
// nothing is rendered, we only choose which frame to show.
//
// The capture is normally a PARTIAL ARC (the lake blocks the far side), so the
// ends are clamped: dragging past either end stops rather than wrapping to the
// start. The manifest sets wraparound: true only when a full revolution was
// genuinely walked, and then rotation loops instead.

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
    versions: document.getElementById("versions"),
  };

  var manifest = null;
  var active = [];        // frames for the current mode
  var position = 0;       // index into `active`
  var interpolated = true;
  var currentVersion = null;

  function fail(message) {
    els.status.textContent = message;
    els.status.classList.add("error");
  }

  // Each captured session (data/raw_versions/<name>/) is a separate,
  // independently-run manifest, kept apart so switching between them never
  // mixes frames from two different walks. See run_pipeline.py --version-name.
  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      var script = document.createElement("script");
      script.src = src;
      script.onload = resolve;
      script.onerror = function () { reject(new Error("could not load " + src)); };
      document.head.appendChild(script);
    });
  }

  function loadManifest(path) {
    if (!path && window.SALA_MANIFEST) return Promise.resolve(window.SALA_MANIFEST);
    // Fallback for when the page is served over http(s). Browsers refuse this
    // over file://, which is why build_sequence.py also emits a .js twin.
    if (window.fetch && location.protocol !== "file:") {
      return fetch(path ? path.replace(/\.js$/, ".json") : "manifest.json").then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      });
    }
    return loadScript(path || "manifest.js").then(function () { return window.SALA_MANIFEST; });
  }

  function buildVersionSwitcher(versions, onSelect) {
    if (!els.versions || !versions || versions.length < 2) return;
    els.versions.hidden = false;
    versions.forEach(function (v) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "version-btn";
      btn.textContent = v.label + " (" + v.n_frames + ")";
      btn.dataset.name = v.name;
      btn.addEventListener("click", function () { onSelect(v); });
      els.versions.appendChild(btn);
    });
  }

  function markActiveVersion(name) {
    if (!els.versions) return;
    Array.prototype.forEach.call(els.versions.querySelectorAll(".version-btn"), function (btn) {
      btn.classList.toggle("active", btn.dataset.name === name);
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
    position = manifest && manifest.wraparound
      ? ((index % active.length) + active.length) % active.length  // closed revolution
      : Math.max(0, Math.min(active.length - 1, index));           // partial arc: clamp
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

  // ◀ ▶ buttons: one frame per click, auto-repeat while held, so a demo can
  // rotate smoothly hands-on-one-button instead of dragging.
  function holdToStep(button, direction) {
    var timer = null;
    function step() { show(position + direction); }
    function start(event) {
      event.preventDefault();     // keep a touch press from also scrolling
      step();
      timer = setInterval(step, 40);   // ~25 frames/s while held
    }
    function stop() {
      if (timer !== null) { clearInterval(timer); timer = null; }
    }
    button.addEventListener("mousedown", start);
    button.addEventListener("touchstart", start, { passive: false });
    ["mouseup", "mouseleave", "touchend", "touchcancel"].forEach(function (name) {
      button.addEventListener(name, stop);
    });
  }
  holdToStep(document.getElementById("step-back"), -1);
  holdToStep(document.getElementById("step-fwd"), +1);

  // --- start -----------------------------------------------------------------

  function activateManifest(data, versionName) {
    manifest = data;
    currentVersion = versionName || null;
    if (!manifest.frames || !manifest.frames.length) {
      fail("Manifest contains no frames. Run src/build_sequence.py first.");
      return;
    }
    els.progress.hidden = false;
    els.bar.style.width = "0%";
    els.status.classList.remove("error");
    document.getElementById("summary").textContent =
      manifest.n_captured + " captured, " + manifest.n_synthesized + " synthesized" +
      (manifest.total_arc_deg ? ", " + manifest.total_arc_deg + "° arc" : "") +
      (manifest.angular_step_deg ? ", " + manifest.angular_step_deg.toFixed(1) + "° mean step" : "");
    document.getElementById("arc-note").textContent = manifest.wraparound
      ? "A full revolution was walked, so rotation loops continuously."
      : "The capture is a partial arc — the lake blocks the far side of the pavilion — so " +
        "rotation stops at both ends rather than looping.";
    markActiveVersion(currentVersion);
    setMode(true);
    preload(manifest.frames);
  }

  function switchToVersion(v) {
    els.status.textContent = "Loading " + v.label + "…";
    loadManifest(v.manifest).then(function (data) {
      activateManifest(data, v.name);
    }).catch(function (error) {
      fail("Could not load " + v.label + " (" + error.message + ").");
    });
  }

  function loadVersionsList() {
    if (window.SALA_VERSIONS) return Promise.resolve(window.SALA_VERSIONS.versions || []);
    if (window.fetch && location.protocol !== "file:") {
      return fetch("versions.json").then(function (r) { return r.ok ? r.json() : { versions: [] }; })
        .then(function (d) { return d.versions || []; }).catch(function () { return []; });
    }
    return loadScript("versions.js").then(function () { return (window.SALA_VERSIONS || {}).versions || []; })
      .catch(function () { return []; });
  }

  loadVersionsList().then(function (versions) {
    if (versions.length >= 2) {
      buildVersionSwitcher(versions, switchToVersion);
      var first = versions[0];
      return loadManifest(first.manifest).then(function (data) { activateManifest(data, first.name); });
    }
    // No registered versions (or just one) — behave exactly as a single-version viewer.
    return loadManifest().then(function (data) { activateManifest(data, versions[0] && versions[0].name); });
  }).catch(function (error) {
    fail("Could not load the manifest (" + error.message + "). " +
         "Run:  python src/build_sequence.py --frames output/sequence/ --out viewer/manifest.json");
  });
})();
