/* ─────────────────────────────────────────────────────────────────────────────
   shell.js — toasts, the command palette, shortcuts, shared-story restore
   ───────────────────────────────────────────────────────────────────────────── */

(function () {
  "use strict";

  var TRAIL_KEY = "kotori-trail-off";
  var ROOMS = ["home", "playground", "history"];

  /* ── the index tabs ───────────────────────────────────────────────────── */

  var currentRoom = "";

  function tabButtons() {
    return Array.prototype.slice.call(document.querySelectorAll("#ast-tabs .index-tab"));
  }

  function roomPanels() {
    ROOMS.forEach(function (name) {
      var panel = document.getElementById("room-" + name);
      if (!panel) return;
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", "tab-" + name);
    });
  }

  function show(room) {
    if (ROOMS.indexOf(room) < 0) room = "home";
    currentRoom = room;
    document.documentElement.setAttribute("data-room", room);
    tabButtons().forEach(function (button) {
      var on = button.getAttribute("data-room") === room;
      button.setAttribute("aria-selected", on ? "true" : "false");
      button.setAttribute("tabindex", on ? "0" : "-1");
    });
    return room;
  }

  /* the little number on the history tab, counted from the cards themselves */
  function syncCount() {
    var badge = document.querySelector('#ast-tabs [data-role="count"]');
    if (!badge) return;
    var total = document.querySelectorAll(".story-card").length;
    badge.textContent = String(total);
    if (total) badge.removeAttribute("hidden");
    else badge.setAttribute("hidden", "");
  }

  /* the server moves the reader by re-rendering a hidden note */
  function watchRoom() {
    var signal = document.getElementById("ast-room");
    if (!signal) return;
    var apply = function () {
      var room = (signal.textContent || "").trim();
      if (room && room !== currentRoom) show(room);
    };
    if (signal.dataset.kotoriWatch !== "1") {
      signal.dataset.kotoriWatch = "1";
      new MutationObserver(apply).observe(signal, {
        childList: true,
        subtree: true,
        characterData: true,
      });
    }
    apply();
  }

  window.ASTRooms = { show: show, current: function () { return currentRoom; } };

  document.addEventListener("click", function (event) {
    var node = event.target;
    if (!node || !node.closest) return;
    var tab = node.closest("#ast-tabs .index-tab");
    if (tab) {
      show(tab.getAttribute("data-room"));
      return;
    }
    var jump = node.closest("[data-room-jump]");
    if (jump) show(jump.getAttribute("data-room-jump"));
  });

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
      node.style.transition = "opacity 0.35s ease";
      window.setTimeout(function () {
        node.remove();
      }, 360);
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
      field.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }

  function tab(name) {
    if (typeof window.ASTRooms === "object") window.ASTRooms.show(name);
  }

  function deckAction(action) {
    var deck = window.ASTPlayer ? window.ASTPlayer.deck() : null;
    var button = deck && deck.querySelector('[data-act="' + action + '"]');
    if (button) button.click();
  }

  /* ── overlays ─────────────────────────────────────────────────────────── */

  var SHORTCUTS = [
    ["Ctrl / ⌘ + K", "command palette"],
    ["1 · 2 · 3", "home · playground · history"],
    ["/", "jump to the brief"],
    ["Ctrl / ⌘ + Enter", "write the story"],
    ["Space", "play or pause the voice"],
    ["← / →", "skip five seconds"],
    ["D", "paper or night desk"],
    ["P", "open a shared story"],
    ["T", "toggle the cursor trail"],
    ["?", "this sheet"],
    ["Esc", "close this"],
  ];

  var COMMANDS = [
    {
      label: "Write a story",
      hint: "⌘ + ⏎",
      run: function () {
        tab("playground");
        if (!click("ast-ignite")) window.ASTToast("the brief is not ready", "error");
      },
    },
    {
      label: "Roll a seed topic",
      hint: "surprise me",
      run: function () {
        tab("playground");
        click("ast-seed");
      },
    },
    {
      label: "Go to the playground",
      hint: "2",
      run: function () {
        tab("playground");
      },
    },
    {
      label: "Go to the history",
      hint: "3",
      run: function () {
        tab("history");
      },
    },
    {
      label: "Read the home page",
      hint: "1",
      run: function () {
        tab("home");
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
      label: "Copy the words",
      hint: "clipboard",
      run: function () {
        deckAction("copy");
      },
    },
    {
      label: "Save the mp3",
      hint: ".mp3",
      run: function () {
        deckAction("download-mp3");
      },
    },
    {
      label: "Switch the paper",
      hint: "D",
      run: function () {
        if (window.ASTTheme) window.ASTTheme.toggle();
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
  ];

  function buildOverlay(id, heading) {
    var overlay = document.createElement("div");
    overlay.className = "ast-overlay";
    overlay.id = id;
    overlay.dataset.open = "false";
    overlay.innerHTML =
      '<div class="ast-sheet"><i class="tape tape--blue tape--right" aria-hidden="true"></i>' +
      "<h3></h3><ul></ul></div>";
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
    if (palette && document.body.contains(palette)) {
      if (keysheet && document.body.contains(keysheet)) return;
    }
    if (!palette || !document.body.contains(palette)) {
      palette = buildOverlay("ast-palette", "what next?");
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
    if (!keysheet || !document.body.contains(keysheet)) {
      keysheet = buildOverlay("ast-keys", "keyboard");
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

  function trailCanvas() {
    return document.getElementById("ast-trail");
  }

  function toggleTrail() {
    var canvas = trailCanvas();
    var off = window.localStorage.getItem(TRAIL_KEY) === "1";
    window.localStorage.setItem(TRAIL_KEY, off ? "0" : "1");
    if (canvas) canvas.style.display = off ? "" : "none";
    window.ASTToast(off ? "the trail is back" : "trail hidden");
  }

  function applyTrailPreference() {
    if (window.localStorage.getItem(TRAIL_KEY) !== "1") return;
    var canvas = trailCanvas();
    if (canvas) canvas.style.display = "none";
  }

  function adoptStory(text) {
    if (!text) {
      window.ASTToast("there is nothing to open", "error");
      return;
    }
    var field = gradioInput("ast-incoming");
    if (!field) {
      window.ASTToast("restoring is unavailable right now", "error");
      return;
    }
    field.value = text;
    field.dispatchEvent(new Event("input", { bubbles: true }));
    tab("playground");
    if (!click("ast-adopt")) window.ASTToast("restoring is unavailable right now", "error");
  }

  function restoreFromPrompt() {
    var raw = window.prompt("Paste a KOTORI share link (or just the text):");
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

    /* left/right walk the index tabs, the way a tablist should */
    var onTab = event.target && event.target.closest && event.target.closest("#ast-tabs");
    if (onTab && (event.key === "ArrowRight" || event.key === "ArrowLeft")) {
      var buttons = tabButtons();
      var step = event.key === "ArrowRight" ? 1 : -1;
      var at = Math.max(0, buttons.indexOf(event.target.closest(".index-tab")));
      var next = buttons[(at + step + buttons.length) % buttons.length];
      if (next) {
        event.preventDefault();
        show(next.getAttribute("data-room"));
        next.focus();
      }
      return;
    }

    if (meta && (event.key === "k" || event.key === "K")) {
      event.preventDefault();
      buildOverlays();
      toggleOverlay(palette);
      return;
    }

    if (meta && event.key === "Enter") {
      event.preventDefault();
      tab("playground");
      if (!click("ast-ignite")) window.ASTToast("the brief is not ready", "error");
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
    if (key === "1") {
      tab("home");
    } else if (key === "2") {
      tab("playground");
    } else if (key === "3") {
      tab("history");
    } else if (key === "d") {
      if (window.ASTTheme) window.ASTTheme.toggle();
    } else if (key === "p") {
      restoreFromPrompt();
    } else if (key === "t") {
      toggleTrail();
    }
  });

  /* ── boot ─────────────────────────────────────────────────────────────── */

  window.ASTBus.onUpdate(function () {
    applyTrailPreference();
    roomPanels();
    syncCount();
    watchRoom();
  });

  window.addEventListener("load", function () {
    applyTrailPreference();
    roomPanels();
    syncCount();
    watchRoom();
    show(currentRoom || "home");
    window.setTimeout(restoreFromHash, 600);
  });
})();
