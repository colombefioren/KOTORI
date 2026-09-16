/* ─────────────────────────────────────────────────────────────────────────────
   deck.js — client-side exports, share links and the story codec
   ───────────────────────────────────────────────────────────────────────────── */

(function () {
  "use strict";

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

  function slugOf(deck, fallback) {
    var slug = deck.getAttribute("data-slug") || fallback;
    return slug.replace(/[^a-z0-9-]+/gi, "-") || fallback;
  }

  function bind(deck) {
    var audio = deck.querySelector("#ast-audio");
    var buttons = deck.querySelectorAll("[data-act]");
    if (!buttons.length || deck.dataset.astTools === "1") return;
    deck.dataset.astTools = "1";

    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        var action = button.getAttribute("data-act");
        var prose = payload(deck, "text");
        var markdown = payload(deck, "markdown");
        var slug = slugOf(deck, "story");

        if (action === "restart") {
          if (audio) {
            audio.currentTime = 0;
            var promise = audio.play();
            if (promise && promise.catch) promise.catch(function () {});
          }
          return;
        }

        if (action === "copy") {
          copyText(prose).then(function () {
            toast("prose copied", "ok");
          });
          return;
        }

        if (action === "download-md") {
          saveBlob(slug + ".md", markdown, "text/markdown;charset=utf-8");
          toast("markdown saved", "ok");
          return;
        }

        if (action === "download-txt") {
          saveBlob(slug + ".txt", prose, "text/plain;charset=utf-8");
          toast("plain text saved", "ok");
          return;
        }

        if (action === "download-mp3") {
          if (!audio || !audio.getAttribute("src")) {
            toast("no audio rendered", "error");
            return;
          }
          var link = document.createElement("a");
          link.href = audio.getAttribute("src");
          link.download = slug + ".mp3";
          document.body.appendChild(link);
          link.click();
          link.remove();
          toast("mp3 saved", "ok");
          return;
        }

        if (action === "share") {
          var url =
            window.location.origin +
            window.location.pathname +
            "#s=" +
            encode(prose);
          if (window.history && window.history.replaceState) {
            window.history.replaceState(null, "", "#s=" + encode(prose));
          }
          copyText(url).then(function () {
            toast("share link copied", "ok");
          });
        }
      });
    });
  }

  window.ASTBus.onUpdate(function () {
    var deck = document.querySelector(".deck");
    if (deck) bind(deck);
  });
})();
