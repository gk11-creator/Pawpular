
const HOT_WINDOW = 24 * 60 * 60 * 1000; // 24 hours in ms

let hotLog = {};

function getNextMidnight() {
  const now = new Date();
  const midnight = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate() + 1, // tomorrow
    0, 0, 0, 0         // 00:00:00
  );
  return midnight.getTime();
}

let hotResetAt = getNextMidnight();

function recordHotLike(username) {
  if (!hotLog[username]) hotLog[username] = [];
  hotLog[username].push(Date.now());
}

function getHotCount(username) {
  if (!hotLog[username]) return 0;
  const cutoff = hotResetAt - HOT_WINDOW; // = today midnight
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
  const now = Date.now();
  const rem = hotResetAt - now;

  if (rem <= 0) {
    // Reset at midnight
    hotLog = {};
    hotResetAt = getNextMidnight();
    renderHotList();
  }

  const h = Math.floor(rem / 3600000);
  const m = Math.floor((rem % 3600000) / 60000);
  const s = Math.floor((rem % 60000) / 1000);

  const el = document.getElementById('hot-timer');
  if (el) el.textContent =
    `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}