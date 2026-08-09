(function () {
  function showMsg(text, isError) {
    var el = document.getElementById('authMessage');
    if (!el) return;
    el.textContent = text;
    el.className = 'auth-message' + (isError ? ' error' : '');
    el.classList.remove('hidden');
  }

  async function onCredential(response) {
    try {
      var res = await fetch('/api/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ idToken: response.credential }),
      });
      var data = await res.json().catch(function () { return {}; });
      if (!res.ok) throw new Error(data.error || 'Google login failed');
      localStorage.setItem('currentUser', JSON.stringify(data.user));
      if (data.token) localStorage.setItem('userToken', data.token);
      showMsg('Бо Google ворид шудед');
      setTimeout(function () { location.reload(); }, 600);
    } catch (e) {
      showMsg(e.message || 'Хато', true);
    }
  }

  async function init() {
    var host = document.getElementById('googleSignInBtn');
    if (!host) return;
    try {
      var res = await fetch('/api/auth/google/status');
      var status = await res.json();
      if (!status.configured || !status.clientId) {
        host.style.display = 'none';
        return;
      }
      function start() {
        if (!window.google || !google.accounts || !google.accounts.id) return false;
        google.accounts.id.initialize({
          client_id: status.clientId,
          callback: onCredential,
          auto_select: false,
          ux_mode: 'popup',
        });
        google.accounts.id.renderButton(host, {
          theme: 'outline',
          size: 'large',
          shape: 'pill',
          text: 'continue_with',
          width: 280,
        });
        return true;
      }
      if (!start()) {
        var n = 0;
        var t = setInterval(function () {
          n += 1;
          if (start() || n > 50) clearInterval(t);
        }, 200);
      }
    } catch (e) {
      host.style.display = 'none';
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
