/* ─────────────────────────────────────────────────────────────────────────────
   teleprompter.js — karaoke highlighting, the trailing halo, playback controls
   ───────────────────────────────────────────────────────────────────────────── */

(function () {
  "use strict";

  var GLYPH_PLAY = "▶";
  var GLYPH_PAUSE = "❚❚";

  var state = {
    paper: null,
    audio: null,
    deck: null,
    words: [],
    fractions: [],
    index: -1,
    raf: 0,
    storyId: "",
  };

  function formatTime(seconds) {
    if (!isFinite(seconds) || seconds < 0) seconds = 0;
    var whole = Math.floor(seconds);
    var minutes = Math.floor(whole / 60);
    var rest = whole % 60;
    return minutes + ":" + (rest < 10 ? "0" : "") + rest;
  }

  function cumulative(words) {
    var weights = words.map(function (word) {
      var value = parseFloat(word.getAttribute("data-w") || "0");
      return value > 0 ? value : 1;
    });
    var total = weights.reduce(function (sum, value) {
      return sum + value;
    }, 0);
    if (total <= 0) return [];
    var running = 0;
    return weights.map(function (value) {
      running += value;
      return running / total;
    });
  }

  /* first index whose end fraction reaches `progress` */
  function indexAt(progress) {
    var fractions = state.fractions;
    if (!fractions.length) return -1;
    var low = 0;
    var high = fractions.length - 1;
    while (low < high) {
      var middle = (low + high) >> 1;
      if (fractions[middle] < progress) low = middle + 1;
      else high = middle;
    }
    return low;
  }

  function halo() {
    return state.paper ? state.paper.querySelector(".tp-halo") : null;
  }

  function paint(index) {
    if (!state.words.length) return;
    if (index < 0) index = 0;
    if (index > state.words.length - 1) index = state.words.length - 1;
    if (index === state.index) return;
    state.index = index;

    state.words.forEach(function (word, position) {
      word.classList.toggle("is-current", position === index);
      word.classList.toggle("is-spoken", position < index);
      word.classList.toggle("is-pending", position > index);
    });

    var active = state.words[index];
    if (!active) return;

    var glow = halo();
    if (glow) {
      glow.style.transform =
        "translate(" +
        (active.offsetLeft + active.offsetWidth / 2) +
        "px," +
        (active.offsetTop + active.offsetHeight / 2) +
        "px)";
    }

    if (state.paper) {
      var top = active.offsetTop;
      var target = top - state.paper.clientHeight * 0.42;
      if (state.paper.scrollHeight > state.paper.clientHeight + 8) {
        state.paper.scrollTop = Math.max(0, target);
      }
    }

    var caption = state.deck && state.deck.querySelector('[data-role="caption"]');
    if (caption) {
      caption.textContent = "now speaking: “" + active.textContent.trim() + "”";
    }
  }

  function setRail(progress, current, duration) {
    var fill = state.deck && state.deck.querySelector('[data-role="fill"]');
    if (fill) fill.style.width = Math.min(100, Math.max(0, progress * 100)) + "%";
    var label = state.deck && state.deck.querySelector('[data-role="time"]');
    if (label) {
      label.textContent = formatTime(current) + " / " + formatTime(duration);
    }
  }

  function glyph(value) {
    var node = state.deck && state.deck.querySelector('[data-role="glyph"]');
    if (node) node.textContent = value;
  }

  function frame() {
    state.raf = 0;
    if (!state.audio || state.audio.paused) return;
    var duration = state.audio.duration;
    if (isFinite(duration) && duration > 0) {
      var progress = state.audio.currentTime / duration;
      paint(indexAt(progress));
      setRail(progress, state.audio.currentTime, duration);
    }
    state.raf = window.requestAnimationFrame(frame);
  }

  function loop() {
    if (!state.raf) state.raf = window.requestAnimationFrame(frame);
  }

  function speaking(on) {
    if (state.paper) state.paper.classList.toggle("tp-paper--speaking", on);
    glyph(on ? GLYPH_PAUSE : GLYPH_PLAY);
  }

  function toggle() {
    var audio = state.audio;
    if (!audio) return;
    if (audio.paused) {
      var promise = audio.play();
      if (promise && promise.catch) promise.catch(function () {});
    } else {
      audio.pause();
    }
  }

  function seek(seconds) {
    var audio = state.audio;
    if (!audio || !audio.duration) return;
    audio.currentTime = Math.min(audio.duration, Math.max(0, seconds));
    var duration = audio.duration;
    paint(indexAt(audio.currentTime / duration));
    setRail(audio.currentTime / duration, audio.currentTime, duration);
  }

  function jump(offset) {
    if (!state.audio) return;
    seek((state.audio.currentTime || 0) + offset);
  }

  function readStage() {
    var paper = document.getElementById("ast-paper");
    if (!paper) return;
    var storyId = paper.getAttribute("data-story-id") || "";
    if (paper !== state.paper || storyId !== state.storyId) {
      state.paper = paper;
      state.storyId = storyId;
      state.index = -1;
    }
    state.words = Array.prototype.slice.call(paper.querySelectorAll(".tp-word"));
    state.fractions = cumulative(state.words);

    /* while prose is streaming there is nothing to follow: stay at the caret */
    if (paper.classList.contains("tp-paper--live") && !state.audio) {
      paper.scrollTop = paper.scrollHeight;
    }
  }

  function bindDeck() {
    var deck = document.querySelector(".deck");
    var audio = document.getElementById("ast-audio");
    state.deck = deck || state.deck;
    if (!deck || !audio) {
      var label = deck && deck.querySelector('[data-role="caption"]');
      if (label && state.words.length) {
        label.textContent = "follow the light: the current word glows once the voice starts.";
      }
      return;
    }
    if (state.audio === audio) return;

    state.audio = audio;
    state.index = -1;

    ["timeupdate", "seeked", "loadedmetadata"].forEach(function (event) {
      audio.addEventListener(event, function () {
        var duration = audio.duration;
        if (isFinite(duration) && duration > 0) {
          var progress = audio.currentTime / duration;
          paint(indexAt(progress));
          setRail(progress, audio.currentTime, duration);
        }
      });
    });

    audio.addEventListener("play", function () {
      speaking(true);
      loop();
    });
    audio.addEventListener("pause", function () {
      speaking(false);
    });
    audio.addEventListener("ended", function () {
      speaking(false);
      setRail(1, audio.duration, audio.duration);
    });

    var toggleButton = deck.querySelector('[data-role="toggle"]');
    if (toggleButton && toggleButton.dataset.astBound !== "1") {
      toggleButton.dataset.astBound = "1";
      toggleButton.addEventListener("click", toggle);
    }

    var rail = deck.querySelector('[data-role="rail"]');
    if (rail && rail.dataset.astBound !== "1") {
      rail.dataset.astBound = "1";
      rail.addEventListener("click", function (event) {
        var box = rail.getBoundingClientRect();
        var ratio = (event.clientX - box.left) / Math.max(1, box.width);
        if (state.audio && state.audio.duration) seek(ratio * state.audio.duration);
      });
      rail.addEventListener("keydown", function (event) {
        if (event.key === "ArrowRight") jump(5);
        if (event.key === "ArrowLeft") jump(-5);
      });
    }

    /* autoplay is usually blocked after a long stream: invite a click instead */
    var attempt = audio.play();
    if (attempt && attempt.catch) {
      attempt.catch(function () {
        var play = deck.querySelector(".deck__play");
        if (play) play.classList.add("deck__play--ready");
      });
    }
  }

  window.ASTPlayer = {
    toggle: toggle,
    seek: seek,
    jump: jump,
    pause: function () {
      if (state.audio && !state.audio.paused) state.audio.pause();
    },
  };

  window.ASTBus.onUpdate(function () {
    readStage();
    bindDeck();
  });
})();
