/* ─────────────────────────────────────────────────────────────────────────────
   trail.js — a tiny DOM bus plus the pastel cursor trail
   ───────────────────────────────────────────────────────────────────────────── */

(function () {
  "use strict";

  /* ── shared bus ─────────────────────────────────────────────────────────
     Gradio swaps component HTML in place, so every script subscribes here and
     re-binds whatever it owns whenever the DOM settles. */
  var listeners = [];
  var scheduled = false;

  function flush() {
    scheduled = false;
    listeners.forEach(function (fn) {
      try {
        fn();
      } catch (error) {
        console.warn("[ast] listener failed", error);
      }
    });
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    window.requestAnimationFrame(flush);
  }

  window.ASTBus = {
    onUpdate: function (fn) {
      listeners.push(fn);
      schedule();
    },
    refresh: schedule,
  };

  function observe() {
    if (!document.body) return;
    new MutationObserver(schedule).observe(document.body, {
      childList: true,
      subtree: true,
    });
    schedule();
  }

  function onReady(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  onReady(observe);

  /* the studio is paper, never midnight: strip anything that says otherwise */
  function keepLight() {
    var root = document.documentElement;
    ["dark", "dark-mode"].forEach(function (cls) {
      root.classList.remove(cls);
      if (document.body) document.body.classList.remove(cls);
    });
    root.classList.add("light");
    if (document.body) document.body.classList.add("light");
  }

  onReady(keepLight);
  window.ASTBus.onUpdate(keepLight);

  /* ── cursor trail ─────────────────────────────────────────────────────── */

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (reduced.matches) return;

  var COLOURS = ["#a795e0", "#d98ea2", "#7cb79b", "#d8b96b", "#8ab3d6"];
  var MAX_POINTS = 26;

  var canvas = document.createElement("canvas");
  canvas.id = "ast-trail";
  canvas.setAttribute("aria-hidden", "true");
  var context = canvas.getContext("2d");
  var points = [];
  var width = 0;
  var height = 0;
  var dpr = 1;
  var head = { x: 0, y: 0 };
  var colourIndex = 0;

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    if (context) context.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function push(x, y) {
    head.x = x;
    head.y = y;
    points.push({ x: x, y: y, colour: COLOURS[colourIndex] });
    colourIndex = (colourIndex + 1) % COLOURS.length;
    if (points.length > MAX_POINTS) points.shift();
  }

  function frame() {
    if (!context) return;
    context.clearRect(0, 0, width, height);

    if (points.length > 1) {
      context.lineCap = "round";
      context.lineJoin = "round";
      for (var i = 1; i < points.length; i += 1) {
        var previous = points[i - 1];
        var point = points[i];
        var ratio = i / points.length;
        context.globalAlpha = ratio * 0.45;
        context.strokeStyle = point.colour;
        context.lineWidth = ratio * 2.6 + 0.3;
        context.beginPath();
        context.moveTo(previous.x, previous.y);
        context.lineTo(point.x, point.y);
        context.stroke();
      }
      context.globalAlpha = 0.5;
      context.fillStyle = COLOURS[colourIndex];
      context.beginPath();
      context.arc(head.x, head.y, 2.6, 0, Math.PI * 2);
      context.fill();
      context.globalAlpha = 1;
    }

    if (points.length) points.shift();
    window.requestAnimationFrame(frame);
  }

  window.addEventListener("pointermove", function (event) {
    if (event.pointerType === "touch") return;
    push(event.clientX, event.clientY);
  });

  window.addEventListener("resize", resize);
  window.addEventListener("blur", function () {
    points = [];
  });

  onReady(function () {
    document.body.appendChild(canvas);
    resize();
    window.requestAnimationFrame(frame);
  });
})();
