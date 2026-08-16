/* Animated favicon: redraws the bolt icon on a canvas with a gently pulsing
   glow and swaps the <link rel="icon"> href to the rendered frame. Chrome and
   Safari never animate SVG or GIF favicons, so a JS canvas swap is the only
   cross-browser route. The static favicon.svg stays as the fallback when JS
   is off, canvas/Path2D are unavailable, or the user prefers reduced motion. */
(function () {
  "use strict";
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  if (typeof Path2D === "undefined" || !document.createElement("canvas").getContext) return;

  var links = document.querySelectorAll('link[rel="icon"]');
  if (!links.length) return;

  var SIZE = 64;
  var SCALE = SIZE / 24; // favicon.svg geometry is a 24x24 viewBox
  var PERIOD_MS = 2400;
  var canvas = document.createElement("canvas");
  canvas.width = canvas.height = SIZE;
  var ctx = canvas.getContext("2d");
  var bolt = new Path2D("M13 2 3 14h9l-1 8 10-12h-9l1-8z");

  function frame(elapsed) {
    var pulse = 0.5 + 0.5 * Math.sin((elapsed / PERIOD_MS) * 2 * Math.PI); // 0..1
    ctx.clearRect(0, 0, SIZE, SIZE);
    ctx.save();
    ctx.fillStyle = "#5980a6";
    if (ctx.roundRect) {
      ctx.beginPath();
      ctx.roundRect(0, 0, SIZE, SIZE, 5.5 * SCALE);
      ctx.fill();
    } else {
      ctx.fillRect(0, 0, SIZE, SIZE);
    }
    ctx.scale(SCALE, SCALE);
    ctx.shadowColor = "rgba(242, 242, 243, " + (0.35 + 0.65 * pulse).toFixed(3) + ")";
    ctx.shadowBlur = 2 + 8 * pulse;
    ctx.globalAlpha = 0.7 + 0.3 * pulse;
    ctx.fillStyle = "#f2f2f3";
    ctx.fill(bolt);
    ctx.restore();
    var url = canvas.toDataURL("image/png");
    links.forEach(function (link) { link.href = url; });
  }

  /* setInterval rather than requestAnimationFrame: rAF stops entirely in
     background tabs, where the favicon is the only part of the page still
     visible. Background intervals get throttled to ~1fps, which still reads
     as a slow pulse. */
  var t0 = Date.now();
  frame(0);
  setInterval(function () { frame(Date.now() - t0); }, 100);
})();
