/* ─────────────────────────────────────────────────────────────────────────────
   deck.js — one voice registry, every player on the page, the exports, and the
   buttons on the index cards.
   ───────────────────────────────────────────────────────────────────────────── */

(function () {
  "use strict";

  var boundDecks = [];
  var voices = [];

  function toast(message, tone) {
    if (typeof window.ASTToast === "function") window.ASTToast(message, tone);
  }

  /* ── one voice at a time, across every player ─────────────────────────── */

  window.ASTVoices = {
    pauseOthers: function (audio) {
      voices.forEach(function (other) {
        if (other !== audio && !other.paused) other.pause();
      });
    },
    pauseAll: function () {
      voices.forEach(function (audio) {
        if (!audio.paused) audio.pause();
      });
    },
  };

  function formatTime(seconds) {
    if (!isFinite(seconds) || seconds < 0) seconds = 0;
    var whole = Math.floor(seconds);
    return Math.floor(whole / 60) + ":" + (whole % 60 < 10 ? "0" : "") + (whole % 60);
  }

  /* ── the exports ──────────────────────────────────────────────────────── */

  function payload(deck, kind) {
    var node = deck.querySelector('.deck__payload[data-kind="' + kind + '"]');
    return node ? node.value : "";
  }

  function saveBlob(filename, text, mime) {
    var blob = new Blob([text], { type: mime });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(function () {
      URL.revokeObjectURL(url);
    }, 4000);
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    var field = document.createElement("textarea");
    field.value = text;
    field.setAttribute("readonly", "readonly");
    field.style.position = "fixed";
    field.style.left = "-9999px";
    document.body.appendChild(field);
    field.select();
    try {
      document.execCommand("copy");
    } catch (error) {
      console.warn("[kotori] copy failed", error);
    }
    field.remove();
    return Promise.resolve();
  }

  /* base64url, so a story link survives being pasted anywhere */
  function encode(text) {
    var bytes = new TextEncoder().encode(text);
    var binary = "";
    bytes.forEach(function (byte) {
      binary += String.fromCharCode(byte);
    });
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function decode(value) {
    try {
      var padded = value.replace(/-/g, "+").replace(/_/g, "/");
      while (padded.length % 4) padded += "=";
      var binary = atob(padded);
      var bytes = Uint8Array.from(binary, function (character) {
        return character.charCodeAt(0);
      });
      return new TextDecoder().decode(bytes);
    } catch (error) {
      console.warn("[kotori] could not decode link", error);
      return "";
    }
  }

  window.ASTCodec = { encode: encode, decode: decode };

  function slugOf(node) {
    var slug = node.getAttribute("data-slug") || "story";
    return slug.replace(/[^a-z0-9-]+/gi, "-") || "story";
  }

  function saveAudio(deck, slug) {
    var audio = deck.querySelector(".deck__audio");
    var src = audio && audio.getAttribute("src");
    if (!src) {
      toast("this story has no voice yet", "error");
      return;
    }
    var link = document.createElement("a");
    link.href = src;
    link.download = slug + ".mp3";
    document.body.appendChild(link);
    link.click();
    link.remove();
    toast("the mp3 is yours", "ok");
  }

  function act(deck, action) {
    var audio = deck.querySelector(".deck__audio");
    var slug = slugOf(deck);

    if (action === "restart") {
      if (!audio) return;
      audio.currentTime = 0;
      var promise = audio.play();
      if (promise && promise.catch) promise.catch(function () {});
      return;
    }
    if (action === "copy") {
      copyText(payload(deck, "text")).then(function () {
        toast("the words are on your clipboard", "ok");
      });
      return;
    }
    if (action === "download-md") {
      saveBlob(slug + ".md", payload(deck, "markdown"), "text/markdown;charset=utf-8");
      toast("saved as markdown", "ok");
      return;
    }
    if (action === "download-mp3") {
      saveAudio(deck, slug);
      return;
    }
    if (action === "share") {
      var text = payload(deck, "text");
      var url = window.location.origin + window.location.pathname + "#s=" + encode(text);
      if (window.history && window.history.replaceState) {
        window.history.replaceState(null, "", "#s=" + encode(text));
      }
      copyText(url).then(function () {
        toast("share link copied", "ok");
      });
    }
  }

  /* ── the players ──────────────────────────────────────────────────────── */

  function bindPlayer(node, audioClass) {
    var audio = node.querySelector("." + audioClass);
    if (!audio || voices.indexOf(audio) >= 0) return;
    voices.push(audio);

    var toggle = node.querySelector('[data-role="toggle"]');
    if (toggle) {
      toggle.addEventListener("click", function () {
        if (audio.paused) {
          window.ASTVoices.pauseOthers(audio);
          var promise = audio.play();
          if (promise && promise.catch) promise.catch(function () {});
        } else {
          audio.pause();
        }
      });
    }

    function reflect(on) {
      var glyph = node.querySelector('[data-role="glyph"]');
      if (glyph) glyph.textContent = on ? "❚❚" : "▶";
    }

    function time() {
      var duration = isFinite(audio.duration) ? audio.duration : 0;
      var ratio = duration ? audio.currentTime / duration : 0;
      var fill = node.querySelector('[data-role="fill"]');
      if (fill) fill.style.width = Math.min(100, ratio * 100) + "%";
      var rail = node.querySelector('[data-role="rail"]');
      if (rail) rail.setAttribute("aria-valuenow", Math.round(ratio * 100));
      var label = node.querySelector('[data-role="time"]');
      if (label) {
        label.textContent =
          formatTime(audio.currentTime) + " / " + (duration ? formatTime(duration) : "--:--");
      }
    }

    ["timeupdate", "seeked", "loadedmetadata"].forEach(function (event) {
      audio.addEventListener(event, time);
    });
    audio.addEventListener("play", function () {
      window.ASTVoices.pauseOthers(audio);
      reflect(true);
    });
    audio.addEventListener("pause", function () {
      reflect(false);
    });
    audio.addEventListener("ended", function () {
      reflect(false);
      time();
    });

    var rail = node.querySelector('[data-role="rail"]');
    if (rail) {
      rail.addEventListener("click", function (event) {
        if (!audio.duration) return;
        var box = rail.getBoundingClientRect();
        audio.currentTime = ((event.clientX - box.left) / Math.max(1, box.width)) * audio.duration;
        time();
      });
    }
  }

  function bindDeck(deck) {
    if (deck.dataset.kotoriTools === "1") return;
    deck.dataset.kotoriTools = "1";
    boundDecks.push(deck);
    Array.prototype.forEach.call(deck.querySelectorAll("[data-act]"), function (button) {
      button.addEventListener("click", function () {
        act(deck, button.getAttribute("data-act"));
      });
    });
    bindPlayer(deck, "deck__audio");
  }

  /* ── the index cards on the shelf ─────────────────────────────────────── */

  function selectStory(storyId, thenClickId) {
    var picker = document.querySelector('#ast-pick input[type="radio"][value="' + storyId + '"]');
    var button = document.getElementById(thenClickId);
    var fallback = document.getElementById("ast-history-pick");
    if ((!picker || !button) && fallback) {
      /* the hidden bridge was not on the page: use the drawer's own controls */
      picker = fallback.querySelector('input[type="radio"][value="' + storyId + '"]');
      button = document.getElementById(
        thenClickId === "ast-open" ? "ast-history-open" : "ast-history-delete"
      );
      if (button && button.tagName !== "BUTTON") button = button.querySelector("button");
    }
    if (!picker || !button) {
      toast("use “manage the shelf” for this one", "error");
      return false;
    }
    picker.checked = true;
    picker.dispatchEvent(new Event("input", { bubbles: true }));
    picker.dispatchEvent(new Event("change", { bubbles: true }));
    button.click();
    return true;
  }

  function selectTab(name) {
    var buttons = document.querySelectorAll('#ast-tabs [role="tab"]');
    for (var i = 0; i < buttons.length; i += 1) {
      var label = (buttons[i].textContent || "").trim().toLowerCase();
      if (label.indexOf(name) === 0) {
        buttons[i].click();
        return true;
      }
    }
    return false;
  }

  function bindCard(card) {
    if (card.dataset.kotoriCard === "1") return;
    card.dataset.kotoriCard = "1";
    var storyId = card.getAttribute("data-story-id") || "";
    var mini = card.querySelector(".mini");
    if (mini) bindPlayer(mini, "mini__audio");

    Array.prototype.forEach.call(card.querySelectorAll("[data-act]"), function (button) {
      button.addEventListener("click", function () {
        var action = button.getAttribute("data-act");
        if (action === "open") {
          if (selectStory(storyId, "ast-open")) selectTab("playground");
          return;
        }
        if (action === "delete") {
          if (!window.confirm("Delete this story, and its recording?")) return;
          selectStory(storyId, "ast-delete");
          return;
        }
        if (action === "download-mp3") {
          saveAudio(card, slugOf(card));
        }
      });
    });
  }

  function tidy() {
    boundDecks = boundDecks.filter(function (deck) {
      return document.contains(deck);
    });
    voices = voices.filter(function (audio) {
      return document.contains(audio);
    });
  }

  window.ASTLibrary = { selectTab: selectTab, open: selectStory };

  window.ASTBus.onUpdate(function () {
    tidy();
    Array.prototype.forEach.call(document.querySelectorAll(".deck"), bindDeck);
    Array.prototype.forEach.call(document.querySelectorAll(".story-card"), bindCard);
    Array.prototype.forEach.call(document.querySelectorAll(".mini"), function (mini) {
      if (mini.dataset.kotoriTools !== "1") {
        mini.dataset.kotoriTools = "1";
        bindPlayer(mini, "mini__audio");
      }
    });
  });
})();
