/* ─────────────────────────────────────────────────────────────────────────────
   teleprompter.js — one reader per story, and the karaoke that drives it.

   Every reader lives inside its own `.deck` element with its own <audio>, and
   points at the page it narrates through `data-paper`. The page can therefore
   hold the story being written *and* a ledger full of older ones without ever
   playing the wrong voice.
   ───────────────────────────────────────────────────────────────────────────── */

(function () {
  "use strict";

  var GLYPH_PLAY = "▶";
  var GLYPH_PAUSE = "❚❚";
  var players = [];
  var rafId = 0;

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
  function indexAt(fractions, progress) {
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

  function paperFor(deck) {
    var id = deck.getAttribute("data-paper");
    if (id) {
      var found = document.getElementById(id);
      if (found) return found;
    }
    return document.querySelector(".sheet");
  }

  function part(player, role) {
    return player.deck ? player.deck.querySelector('[data-role="' + role + '"]') : null;
  }

  function paint(player, index) {
    var words = player.words;
    if (!words.length) return;
    if (index < 0) index = 0;
    if (index > words.length - 1) index = words.length - 1;
    if (index === player.index) return;
    player.index = index;

    words.forEach(function (word, position) {
      word.classList.toggle("is-current", position === index);
      word.classList.toggle("is-spoken", position < index);
      word.classList.toggle("is-pending", position > index);
    });

    var active = words[index];
    if (!active) return;

    if (player.paper && player.paper.scrollHeight > player.paper.clientHeight + 8) {
      player.paper.scrollTop = Math.max(0, active.offsetTop - player.paper.clientHeight * 0.4);
    }

    var caption = part(player, "caption");
    if (caption) caption.textContent = "“" + active.textContent.trim() + "”";
  }

  function setRail(player, progress, current, duration) {
    var ratio = Math.min(1, Math.max(0, progress));
    var fill = part(player, "fill");
    if (fill) fill.style.width = ratio * 100 + "%";
    var rail = part(player, "rail");
    if (rail) rail.setAttribute("aria-valuenow", Math.round(ratio * 100));
    var label = part(player, "time");
    if (label) label.textContent = formatTime(current) + " / " + formatTime(duration);
  }

  function glyph(player, value) {
    var node = part(player, "glyph");
    if (node) node.textContent = value;
  }

  function frame() {
    rafId = 0;
    var playing = false;
    players.forEach(function (player) {
      var audio = player.audio;
      if (!audio || audio.paused) return;
      playing = true;
      var duration = audio.duration;
      if (isFinite(duration) && duration > 0) {
        var progress = audio.currentTime / duration;
        paint(player, indexAt(player.fractions, progress));
        setRail(player, progress, audio.currentTime, duration);
      }
    });
    if (playing) loop();
  }

  function loop() {
    if (!rafId) rafId = window.requestAnimationFrame(frame);
  }

  function speaking(player, on) {
    if (player.paper) player.paper.classList.toggle("sheet--speaking", on);
    glyph(player, on ? GLYPH_PAUSE : GLYPH_PLAY);
  }

  function pauseOthers(audio) {
    if (window.ASTVoices) window.ASTVoices.pauseOthers(audio);
  }

  function toggle(player) {
    if (!player) return;
    var audio = player.audio;
    if (!audio) return;
    if (audio.paused) {
      pauseOthers(audio);
      var promise = audio.play();
      if (promise && promise.catch) promise.catch(function () {});
    } else {
      audio.pause();
    }
  }

  function seek(player, seconds) {
    var audio = player && player.audio;
    if (!audio || !audio.duration) return;
    audio.currentTime = Math.min(audio.duration, Math.max(0, seconds));
    paint(player, indexAt(player.fractions, audio.currentTime / audio.duration));
    setRail(player, audio.currentTime / audio.duration, audio.currentTime, audio.duration);
  }

  function current() {
    var playing = players.filter(function (player) {
      return player.audio && !player.audio.paused;
    })[0];
    if (playing) return playing;
    var visible = players.filter(function (player) {
      return player.deck && player.deck.offsetParent !== null;
    });
    return visible[0] || players[0] || null;
  }

  function collect() {
    var decks = Array.prototype.slice.call(document.querySelectorAll(".deck"));
    players = players.filter(function (player) {
      return document.contains(player.deck);
    });

    decks.forEach(function (deck) {
      var audio = deck.querySelector(".deck__audio");
      var existing = players.filter(function (player) {
        return player.deck === deck;
      })[0];

      /* no audio in this deck: forget the old one, so a stale player is never
         left holding a detached element from the previous story */
      if (!audio || !document.contains(audio)) {
        if (existing) {
          players = players.filter(function (player) {
            return player !== existing;
          });
        }
        return;
      }
      if (existing && existing.audio === audio) return;
      if (existing) existing.audio.pause();
      players = players.filter(function (player) {
        return player !== existing;
      });
      bind(deck, audio);
    });

    autoplay();
    scrollLiveSheets();
  }

  function bind(deck, audio) {
    var player = {
      deck: deck,
      audio: audio,
      paper: paperFor(deck),
      words: [],
      fractions: [],
      index: -1,
      played: false,
    };
    if (player.paper) {
      player.words = Array.prototype.slice.call(player.paper.querySelectorAll(".tp-word"));
      player.fractions = cumulative(player.words);
    }
    players.push(player);

    ["timeupdate", "seeked", "loadedmetadata"].forEach(function (event) {
      audio.addEventListener(event, function () {
        var duration = audio.duration;
        if (isFinite(duration) && duration > 0) {
          var progress = audio.currentTime / duration;
          paint(player, indexAt(player.fractions, progress));
          setRail(player, progress, audio.currentTime, duration);
        }
      });
    });

    audio.addEventListener("play", function () {
      pauseOthers(audio);
      speaking(player, true);
      loop();
    });
    audio.addEventListener("pause", function () {
      speaking(player, false);
    });
    audio.addEventListener("ended", function () {
      speaking(player, false);
      setRail(player, 1, audio.duration, audio.duration);
    });

    var toggleButton = deck.querySelector('[data-role="toggle"]');
    if (toggleButton) {
      toggleButton.addEventListener("click", function () {
        toggle(player);
      });
    }

    var rail = deck.querySelector('[data-role="rail"]');
    if (rail) {
      rail.addEventListener("click", function (event) {
        var box = rail.getBoundingClientRect();
        var ratio = (event.clientX - box.left) / Math.max(1, box.width);
        if (audio.duration) seek(player, ratio * audio.duration);
      });
      rail.addEventListener("keydown", function (event) {
        if (event.key === "ArrowRight") {
          event.preventDefault();
          seek(player, (audio.currentTime || 0) + 5);
        }
        if (event.key === "ArrowLeft") {
          event.preventDefault();
          seek(player, (audio.currentTime || 0) - 5);
        }
      });
    }
  }

  /* a freshly written story plays itself, if the browser allows it */
  function autoplay() {
    players.forEach(function (player) {
      if (player.played || player.deck.getAttribute("data-autoplay") !== "1") return;
      player.played = true;
      var attempt = player.audio.play();
      if (attempt && attempt.catch) {
        attempt.catch(function () {
          var play = player.deck.querySelector(".deck__play");
          if (play) play.classList.add("deck__play--ready");
        });
      }
    });
  }

  /* while prose is still arriving, keep the newest words in view */
  function scrollLiveSheets() {
    Array.prototype.forEach.call(document.querySelectorAll(".sheet--live"), function (sheet) {
      if (!sheet.classList.contains("sheet--speaking")) sheet.scrollTop = sheet.scrollHeight;
    });
  }

  window.ASTPlayer = {
    toggle: function () {
      toggle(current());
    },
    seek: function (seconds) {
      seek(current(), seconds);
    },
    jump: function (offset) {
      var player = current();
      if (player && player.audio) seek(player, (player.audio.currentTime || 0) + offset);
    },
    deck: function () {
      var player = current();
      return player ? player.deck : null;
    },
    pause: function () {
      if (window.ASTVoices) window.ASTVoices.pauseAll();
    },
  };

  window.ASTBus.onUpdate(collect);
})();
