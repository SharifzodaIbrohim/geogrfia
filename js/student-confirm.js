/** Confirm before submit + Tajik submitted badge */
(function () {
  function patch() {
    var sub = document.getElementById('submitExamBtn');
    if (!sub || sub.dataset.confirmBound) return;
    sub.dataset.confirmBound = '1';
    sub.addEventListener('click', function (ev) {
      var msg = 'Оё шумо мехоҳед супоред? Баъд аз супоридан тағйир дода намешавад.';
      if (!window.confirm(msg)) {
        ev.stopImmediatePropagation();
        ev.preventDefault();
      }
    }, true);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      setTimeout(patch, 500);
      setTimeout(patch, 2000);
    });
  } else {
    setTimeout(patch, 500);
    setTimeout(patch, 2000);
  }
})();
