// ── Hot List (30-min window) ───────────────────────────────────────────────

const HOT_WINDOW = 30 * 60 * 1000; // 30 minutes in ms

let hotLog = {};
let hotResetAt = Date.now() + HOT_WINDOW;

function recordHotLike(username) {
  if (!hotLog[username]) hotLog[username] = [];
  hotLog[username].push(Date.now());
}

function getHotCount(username) {
  if (!hotLog[username]) return 0;
  const cutoff = hotResetAt - HOT_WINDOW;
  return hotLog[username].filter(t => t >= cutoff).length;
}

function renderHotList() {
  const scored = allEntries
    .map(e => ({ ...e, hot: getHotCount(e.owner) }))
    .filter(e => e.hot > 0)
    .sort((a, b) => b.hot - a.hot)
    .slice(0, 10);

  const el = document.getElementById('hot-list');

  if (!scored.length) {
    el.innerHTML = `
      <div class="loading">
        No hot activity yet.<br/>Start liking! 🤍
      </div>`;
    return;
  }

  const max = scored[0].hot;

  el.innerHTML = scored.map((e, i) => {
    const pct   = Math.round(e.hot / max * 100);
    const emoji = PET_EMOJI[e.pet_type] || '🐾';

    return `
      <div class="hot-item ${i < 3 ? 'top3' : ''}">
        <div class="h-rank">${MEDALS[i] || (i + 1)}</div>
        <div class="h-emoji">${emoji}</div>
        <div class="h-info">
          <div class="h-name">${e.pet_name}</div>
          <div class="h-owner">@${e.owner}</div>
          <div class="h-bar">
            <div class="h-bar-fill" style="width:${pct}%"></div>
          </div>
        </div>
        <div class="h-count">+${e.hot} 🔥</div>
      </div>`;
  }).join('');
}

function tickCountdown() {
  const rem = hotResetAt - Date.now();

  if (rem <= 0) {
    // Reset hot window
    hotLog = {};
    hotResetAt = Date.now() + HOT_WINDOW;
    renderHotList();
  }

  const m = Math.floor(rem / 60000);
  const s = Math.floor((rem % 60000) / 1000);
  const el = document.getElementById('hot-timer');
  if (el) el.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}