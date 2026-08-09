/* Fix legacy AUTH_API_BASE pointing to 127.0.0.1 on production */
(function () {
  var orig = window.fetch;
  window.fetch = function (input, init) {
    if (typeof input === 'string' && input.indexOf('http://127.0.0.1:5000') === 0) {
      input = input.replace('http://127.0.0.1:5000', '');
    } else if (input && typeof input.url === 'string' && input.url.indexOf('http://127.0.0.1:5000') === 0) {
      input = new Request(input.url.replace('http://127.0.0.1:5000', ''), input);
    }
    return orig.call(this, input, init);
  };
})();
