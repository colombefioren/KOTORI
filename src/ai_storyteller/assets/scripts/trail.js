/* ─────────────────────────────────────────────────────────────────────────────
   trail.js — a tiny DOM bus plus the neon pastel cursor trail
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

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", observe);
  } else {
    observe();
  }

  /* keep the studio dark whatever the OS thinks */
  function forceDark() {
    ["dark", "dark-mode"].forEach(function (cls) {
      document.documentElement.classList.add(cls);
      if (document.body) document.body.classList.add(cls);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", forceDark);
  } else {
    forceDark();
  }
  window.ASTBus.onUpdate(forceDark);

  /* ── cursor trail ─────────────────────────────────────────────────────── */

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (reduced.matches) return;

  var COLOURS = ["#96f7d2", "#cbb8ff", "#ffb2cb", "#ffe8a3", "#a6d8ff"];
  var MAX_POINTS = 30;

  var canvas = document.createElement("canvas");
  canvas.id = "ast-trail";
  canvas.setAttribute("aria-hidden", "true");
  var context = canvas.getContext("2d");
  var points = [];
  var width = 0;
  var height = 0;
  var dpr = 1;
  var head = { x: 0, y: 0, active: false };
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
    head.active = true;
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
        context.globalAlpha = ratio * 0.6;
        context.strokeStyle = point.colour;
        context.lineWidth = ratio * 3.2 + 0.35;
        context.beginPath();
        context.moveTo(previous.x, previous.y);
        context.lineTo(point.x, point.y);
        context.stroke();
      }
      /* the glowing head of the trail */
      context.globalAlpha = 0.85;
      context.fillStyle = COLOURS[colourIndex];
      context.beginPath();
      context.arc(head.x, head.y, 3.2, 0, Math.PI * 2);
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

  document.body.appendChild(canvas);
  resize();
  window.requestAnimationFrame(frame);
})();
