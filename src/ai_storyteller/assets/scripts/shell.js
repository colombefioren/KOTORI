/* ─────────────────────────────────────────────────────────────────────────────
   shell.js — toasts, command palette, shortcuts, shared-story restore
   ───────────────────────────────────────────────────────────────────────────── */

(function () {
  "use strict";

  var TRAIL_KEY = "ast-trail-off";

  /* ── toasts ───────────────────────────────────────────────────────────── */

  var toastHost = null;

  function ensureToastHost() {
    if (toastHost && document.body.contains(toastHost)) return toastHost;
    toastHost = document.createElement("div");
    toastHost.className = "ast-toasts";
    toastHost.setAttribute("role", "status");
    toastHost.setAttribute("aria-live", "polite");
    document.body.appendChild(toastHost);
    return toastHost;
  }

  window.ASTToast = function (message, tone) {
    var host = ensureToastHost();
    var node = document.createElement("div");
    node.className = "ast-toast" + (tone ? " ast-toast--" + tone : "");
    node.textContent = message;
    host.appendChild(node);
    window.setTimeout(function () {
      node.style.opacity = "0";
      node.style.transition = "opacity 0.3s ease";
      window.setTimeout(function () {
        node.remove();
      }, 320);
    }, 2600);
  };

  /* ── gradio plumbing ──────────────────────────────────────────────────── */

  function gradioButton(id) {
    var node = document.getElementById(id);
    if (!node) return null;
    if (node.tagName === "BUTTON") return node;
    return node.querySelector("button");
  }

  function gradioInput(id) {
    var node = document.getElementById(id);
    if (!node) return null;
    return node.querySelector("textarea, input");
  }

  function click(id) {
    var button = gradioButton(id);
    if (button) {
      button.click();
      return true;
    }
    return false;
  }

  function focusTopic() {
    var field = gradioInput("ast-topic");
    if (field) {
      field.focus();
      if (field.select) field.select();
    }
  }

  function openTab(pattern) {
    var tabs = Array.prototype.slice.call(document.querySelectorAll("#ast-tabs .tab-nav button"));
    var match = tabs.find(function (button) {
      return pattern.test(button.textContent || "");
    });
    if (match) match.click();
  }

  function deckAction(action) {
    var button = document.querySelector('.deck [data-act="' + action + '"]');
    if (button) button.click();
  }

  /* ── overlays ─────────────────────────────────────────────────────────── */

  var SHORTCUTS = [
    ["Ctrl / ⌘ + K", "command palette"],
    ["/", "focus the topic field"],
    ["Ctrl / ⌘ + Enter", "ignite a story"],
    ["Space", "play or pause the voice"],
    ["← / →", "scrub five seconds"],
    ["A", "open the archive"],
    ["P", "paste a shared story"],
    ["T", "toggle the cursor trail"],
    ["?", "this sheet"],
    ["Esc", "close overlays"],
  ];

  var COMMANDS = [
    {
      label: "Ignite a story",
      hint: "⌘ + ⏎",
      run: function () {
        if (!click("ast-ignite")) window.ASTToast("composer not ready", "error");
      },
    },
    {
      label: "Roll a seed topic",
      hint: "surprise me",
      run: function () {
        click("ast-seed");
      },
    },
    {
      label: "Focus the topic field",
      hint: "/",
      run: focusTopic,
    },
    {
      label: "Open the archive",
      hint: "A",
      run: function () {
        openTab(/archive|shelf/i);
      },
    },
    {
      label: "Play or pause the voice",
      hint: "space",
      run: function () {
        if (window.ASTPlayer) window.ASTPlayer.toggle();
      },
    },
    {
      label: "Copy the prose",
      hint: "clipboard",
      run: function () {
        deckAction("copy");
      },
    },
    {
      label: "Download the markdown",
      hint: ".md",
      run: function () {
        deckAction("download-md");
      },
    },
    {
      label: "Open a shared story",
      hint: "P",
      run: function () {
        restoreFromPrompt();
      },
    },
    {
      label: "Toggle the cursor trail",
      hint: "T",
      run: function () {
        toggleTrail();
      },
    },
    {
      label: "Back to the top",
      hint: "scroll",
      run: function () {
        window.scrollTo({ top: 0, behavior: "smooth" });
      },
    },
  ];

  function buildOverlay(id, heading) {
    var overlay = document.createElement("div");
    overlay.className = "ast-overlay";
    overlay.id = id;
    overlay.dataset.open = "false";
    overlay.innerHTML = '<div class="ast-sheet"><h3></h3><ul></ul></div>';
    overlay.querySelector("h3").textContent = heading;
    overlay.addEventListener("click", function (event) {
      if (event.target === overlay) closeOverlays();
    });
    document.body.appendChild(overlay);
    return overlay;
  }

  var palette = null;
  var keysheet = null;

  function buildOverlays() {
    if (!palette) {
      palette = buildOverlay("ast-palette", "Command palette");
      var list = palette.querySelector("ul");
      COMMANDS.forEach(function (command) {
        var item = document.createElement("li");
        var label = document.createElement("span");
        label.textContent = command.label;
        var hint = document.createElement("span");
        hint.textContent = command.hint;
        item.appendChild(label);
        item.appendChild(hint);
        item.style.cursor = "pointer";
        item.addEventListener("click", function () {
          closeOverlays();
          command.run();
        });
        list.appendChild(item);
      });
    }
    if (!keysheet) {
      keysheet = buildOverlay("ast-keys", "Keyboard shortcuts");
      var rows = keysheet.querySelector("ul");
      SHORTCUTS.forEach(function (pair) {
        var item = document.createElement("li");
        var label = document.createElement("span");
        label.textContent = pair[1];
        var key = document.createElement("span");
        key.textContent = pair[0];
        item.appendChild(label);
        item.appendChild(key);
        rows.appendChild(item);
      });
    }
  }

  function closeOverlays() {
    [palette, keysheet].forEach(function (overlay) {
      if (overlay) overlay.dataset.open = "false";
    });
  }

  function toggleOverlay(overlay) {
    if (!overlay) return;
    var open = overlay.dataset.open === "true";
    closeOverlays();
    overlay.dataset.open = open ? "false" : "true";
  }

  function overlaysOpen() {
    return (
      (palette && palette.dataset.open === "true") ||
      (keysheet && keysheet.dataset.open === "true")
    );
  }

  /* ── trail toggle + shared links ──────────────────────────────────────── */

  function toggleTrail() {
    var canvas = document.getElementById("ast-trail");
    var off = window.localStorage.getItem(TRAIL_KEY) === "1";
    window.localStorage.setItem(TRAIL_KEY, off ? "0" : "1");
    if (canvas) canvas.style.display = off ? "" : "none";
    window.ASTToast(off ? "cursor trail on" : "cursor trail off");
  }

  function applyTrailPreference() {
    if (window.localStorage.getItem(TRAIL_KEY) !== "1") return;
    var canvas = document.getElementById("ast-trail");
    if (canvas) canvas.style.display = "none";
  }

  function adoptStory(text) {
    if (!text) {
      window.ASTToast("nothing to open", "error");
      return;
    }
    var field = gradioInput("ast-incoming");
    if (!field) {
      window.ASTToast("restore is unavailable", "error");
      return;
    }
    field.value = text;
    field.dispatchEvent(new Event("input", { bubbles: true }));
    if (!click("ast-adopt")) window.ASTToast("restore is unavailable", "error");
  }

  function restoreFromPrompt() {
    var raw = window.prompt("Paste an AI Storyteller share link (or just the text):");
    if (!raw) return;
    var marker = raw.indexOf("#s=");
    var payloadText = marker >= 0 ? raw.slice(marker + 3) : raw.trim();
    var decoded = window.ASTCodec ? window.ASTCodec.decode(payloadText) : "";
    adoptStory(decoded || raw.trim());
  }

  function restoreFromHash() {
    var hash = window.location.hash || "";
    if (hash.indexOf("#s=") !== 0) return;
    var decoded = window.ASTCodec ? window.ASTCodec.decode(hash.slice(3)) : "";
    if (!decoded) return;
    adoptStory(decoded);
    if (window.history && window.history.replaceState) {
      window.history.replaceState(null, "", window.location.pathname);
    }
  }

  /* ── keyboard ─────────────────────────────────────────────────────────── */

  function typing(event) {
    var node = event.target;
    if (!node) return false;
    var tag = (node.tagName || "").toLowerCase();
    return tag === "input" || tag === "textarea" || node.isContentEditable === true;
  }

  document.addEventListener("keydown", function (event) {
    var meta = event.metaKey || event.ctrlKey;

    if (meta && (event.key === "k" || event.key === "K")) {
      event.preventDefault();
      buildOverlays();
      toggleOverlay(palette);
      return;
    }

    if (meta && event.key === "Enter") {
      event.preventDefault();
      click("ast-ignite") || window.ASTToast("composer not ready", "error");
      return;
    }

    if (event.key === "Escape") {
      closeOverlays();
      return;
    }

    if (typing(event) || overlaysOpen()) return;

    if (event.key === "/") {
      event.preventDefault();
      focusTopic();
      return;
    }

    if (event.key === "?") {
      event.preventDefault();
      buildOverlays();
      toggleOverlay(keysheet);
      return;
    }

    if (event.key === " ") {
      event.preventDefault();
      if (window.ASTPlayer) window.ASTPlayer.toggle();
      return;
    }

    if (event.key === "ArrowRight" && window.ASTPlayer) {
      window.ASTPlayer.jump(5);
      return;
    }

    if (event.key === "ArrowLeft" && window.ASTPlayer) {
      window.ASTPlayer.jump(-5);
      return;
    }

    var key = (event.key || "").toLowerCase();
    if (key === "a") {
      openTab(/archive|shelf/i);
    } else if (key === "p") {
      restoreFromPrompt();
    } else if (key === "t") {
      toggleTrail();
    }
  });

  /* ── boot ─────────────────────────────────────────────────────────────── */

  window.ASTBus.onUpdate(function () {
    buildOverlays();
    applyTrailPreference();
  });

  window.addEventListener("load", function () {
    buildOverlays();
    applyTrailPreference();
    window.setTimeout(restoreFromHash, 600);
    window.setTimeout(function () {
      window.ASTToast("press ? for shortcuts", "ok");
    }, 1200);
  });
})();
