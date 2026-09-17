/* ─────────────────────────────────────────────────────────────────────────────
   deck.js — client-side exports, share links and the story codec.

   Every button works on the deck it lives in, so exports always describe the
   story on screen rather than whichever story was written last.
   ───────────────────────────────────────────────────────────────────────────── */

(function () {
  "use strict";

  var bound = [];

  function toast(message, tone) {
    if (typeof window.ASTToast === "function") window.ASTToast(message, tone);
  }

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
      console.warn("[ast] copy failed", error);
    }
    field.remove();
    return Promise.resolve();
  }

  /* base64url so story links survive being pasted anywhere */
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
      console.warn("[ast] could not decode link", error);
      return "";
    }
  }

  window.ASTCodec = { encode: encode, decode: decode };

  function slugOf(deck) {
    var slug = deck.getAttribute("data-slug") || "story";
    return slug.replace(/[^a-z0-9-]+/gi, "-") || "story";
  }

  function audioOf(deck) {
    return deck.querySelector(".deck__audio");
  }

  function act(deck, action) {
    var audio = audioOf(deck);
    var prose = payload(deck, "text");
    var slug = slugOf(deck);

    if (action === "restart") {
      if (!audio) return;
      audio.currentTime = 0;
      var promise = audio.play();
      if (promise && promise.catch) promise.catch(function () {});
      return;
    }

    if (action === "copy") {
      copyText(prose).then(function () {
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
      if (!audio || !audio.getAttribute("src")) {
        toast("this story has no voice yet", "error");
        return;
      }
      var link = document.createElement("a");
      link.href = audio.getAttribute("src");
      link.download = slug + ".mp3";
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast("the mp3 is yours", "ok");
      return;
    }

    if (action === "share") {
      var url = window.location.origin + window.location.pathname + "#s=" + encode(prose);
      if (window.history && window.history.replaceState) {
        window.history.replaceState(null, "", "#s=" + encode(prose));
      }
      copyText(url).then(function () {
        toast("share link copied", "ok");
      });
    }
  }

  function bind(deck) {
    if (deck.dataset.astTools === "1") return;
    deck.dataset.astTools = "1";
    bound.push(deck);
    Array.prototype.forEach.call(deck.querySelectorAll("[data-act]"), function (button) {
      button.addEventListener("click", function () {
        act(deck, button.getAttribute("data-act"));
      });
    });
  }

  window.ASTBus.onUpdate(function () {
    bound = bound.filter(function (deck) {
      return document.contains(deck);
    });
    Array.prototype.forEach.call(document.querySelectorAll(".deck"), bind);
  });
})();
