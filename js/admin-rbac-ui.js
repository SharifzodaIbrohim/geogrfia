/**
 * Hide admin tabs by role permissions.
 * data-perm on .tab buttons; super_admin sees all.
 */
(() => {
  const TAB_PERMS = {
    monitor: ['monitor.read'],
    students: ['students.read'],
    schools: ['schools.read'],
    gmail: ['students.read', 'admins.read'],
    olympiads: ['olympiads.read', 'quizzes.read'],
    results: ['results.read'],
    leaderboard: ['results.read', 'monitor.read'],
    content: ['content.read'],
    audit: ['admins.read', 'monitor.read'],
    admins: ['admins.read'],
    system: ['admins.read'],
  };

  function can(admin, perms) {
    if (!admin) return false;
    const role = String(admin.role || '').toLowerCase();
    if (role === 'super_admin') return true;
    // soft client filter — server still enforces
    const allowed = {
      user_admin: ['students.read', 'schools.read', 'admins.read'],
      quiz_admin: ['quizzes.read', 'results.read'],
      olympiad_admin: ['olympiads.read', 'results.read', 'monitor.read', 'students.read'],
      monitor: ['monitor.read', 'results.read', 'olympiads.read', 'students.read'],
      content_admin: ['content.read'],
    };
    const set = allowed[role] || [];
    return (perms || []).some((p) => set.includes(p));
  }

  function apply() {
    let admin = null;
    try {
      admin = JSON.parse(localStorage.getItem('geo_admin_user') || 'null');
    } catch {
      admin = null;
    }
    document.querySelectorAll('.tab[data-tab]').forEach((btn) => {
      const tab = btn.dataset.tab;
      const need = TAB_PERMS[tab] || [];
      if (!need.length || can(admin, need)) {
        btn.style.display = '';
      } else {
        btn.style.display = 'none';
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', apply);
  } else {
    apply();
  }
  window.__adminRbacApply = apply;
})();
