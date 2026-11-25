/* Refreshes any element that has data-refresh-url every few seconds.
   On the staff queue it also beeps when a new order arrives. */
(function () {
  var box = document.querySelector('[data-refresh-url]');
  if (!box) { return; }
  var url = box.getAttribute('data-refresh-url');
  var seconds = parseInt(box.getAttribute('data-refresh-seconds') || '8', 10);
  var lastNew = null;

  function beep() {
    try {
      var ctx = new (window.AudioContext || window.webkitAudioContext)();
      var osc = ctx.createOscillator();
      osc.frequency.value = 880;
      osc.connect(ctx.destination);
      osc.start();
      setTimeout(function () { osc.stop(); ctx.close(); }, 180);
    } catch (e) { /* sound is optional */ }
  }

  function readNew() {
    var marker = box.querySelector('[data-new-count]');
    return marker ? parseInt(marker.getAttribute('data-new-count'), 10) : null;
  }

  lastNew = readNew();
  setInterval(function () {
    fetch(url, { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (html) {
        if (html === null) { return; }
        box.innerHTML = html;
        var now = readNew();
        if (lastNew !== null && now !== null && now > lastNew) { beep(); }
        lastNew = now;
      })
      .catch(function () { /* try again next time */ });
  }, seconds * 1000);
})();
