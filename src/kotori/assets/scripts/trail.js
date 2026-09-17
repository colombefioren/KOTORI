/* ─────────────────────────────────────────────────────────────────────────────
   trail.js — the DOM bus, the paper/night-desk switch, and the cursor trail
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
        console.warn("[kotori] listener failed", error);
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

  function onReady(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  onReady(function () {
    if (!document.body) return;
    new MutationObserver(schedule).observe(document.body, {
      childList: true,
      subtree: true,
    });
    schedule();
  });

  /* ── the switch between the paper and the night desk ──────────────────── */

  var THEME_KEY = "kotori-theme";

  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
  }

  function paintSwitches(theme) {
    var word = theme === "dark" ? "paper" : "night desk";
    Array.prototype.forEach.call(
      document.querySelectorAll('[data-role="theme-word"]'),
      function (node) {
        node.textContent = word;
      }
    );
    Array.prototype.forEach.call(document.querySelectorAll("#ast-theme"), function (node) {
      node.setAttribute("data-theme", theme);
    });
  }

  function applyTheme(theme, remember) {
    var root = document.documentElement;
    theme = theme === "dark" ? "dark" : "light";
    root.setAttribute("data-theme", theme);
    root.classList.toggle("dark", theme === "dark");
    root.classList.remove("light", "dark-mode");
    if (document.body) {
      document.body.classList.toggle("dark", theme === "dark");
    }
    if (remember) {
      try {
        window.localStorage.setItem(THEME_KEY, theme);
      } catch (error) {
        /* private mode: the theme just will not be remembered */
      }
    }
    paintSwitches(theme);
  }

  window.ASTTheme = {
    get: currentTheme,
    set: function (theme) {
      applyTheme(theme, true);
    },
    toggle: function () {
      applyTheme(currentTheme() === "dark" ? "light" : "dark", true);
    },
  };

  /* one delegated listener survives every re-render of the masthead */
  document.addEventListener("click", function (event) {
    var node = event.target;
    while (node && node !== document.body) {
      if (node.id === "ast-theme") {
        event.preventDefault();
        window.ASTTheme.toggle();
        return;
      }
      node = node.parentNode;
    }
  });

  onReady(function () {
    applyTheme(currentTheme(), false);
  });
  window.ASTBus.onUpdate(function () {
    applyTheme(currentTheme(), false);
  });

  /* ── the cursor trail: pink and blue ink ──────────────────────────────── */

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (reduced.matches) return;

  var COLOURS = ["#e288ae", "#82aae0", "#f2b3cd", "#b3d0f2", "#bd5f8b"];
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
        context.globalAlpha = ratio * 0.4;
        context.strokeStyle = point.colour;
        context.lineWidth = ratio * 2.4 + 0.3;
        context.beginPath();
        context.moveTo(previous.x, previous.y);
        context.lineTo(point.x, point.y);
        context.stroke();
      }
      context.globalAlpha = 0.45;
      context.fillStyle = COLOURS[colourIndex];
      context.beginPath();
      context.arc(head.x, head.y, 2.4, 0, Math.PI * 2);
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
