// ── Main App ──────────────────────────────────────────────────────────────

function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  document.querySelectorAll('.nav-tab')[['rank','stats','add'].indexOf(name)].classList.add('active');
  if (name === 'stats') loadStats();
}

function toast(msg) {
  const el = document.getElementById('toast-el');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 2200);
}

// ── Init ──────────────────────────────────────────────────────────────────
loadLeaderboard();
setInterval(tickCountdown, 1000);
setInterval(loadLeaderboard, 15000);
tickCountdown();