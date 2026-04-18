// ── Leaderboard Rendering ─────────────────────────────────────────────────

const PET_EMOJI = { Dog:'🐕', Cat:'🐈', Rabbit:'🐰', Hamster:'🐹', Bird:'🐦', Other:'🐾' };
const BG_COLORS = ['#fff5f5','#f0fff8','#f0f5ff','#fffbf0','#fdf0ff','#f0faff'];
const MEDALS = ['🥇','🥈','🥉'];

let allEntries = [];
let liked = {};

async function loadLeaderboard() {
  const { ok, data } = await apiGetLeaderboard();

  if (!ok) {
    document.getElementById('rank-list').innerHTML =
      `<div style="text-align:center;padding:40px;color:#e74c3c;font-weight:700">
        ${data.detail}
      </div>`;
    return;
  }

  allEntries = data.leaderboard;
  document.getElementById('entry-count').textContent = data.total_entries + ' entries';
  renderRankList();
  renderHotList();
}

function renderRankList() {
  const el = document.getElementById('rank-list');

  if (!allEntries.length) {
    el.innerHTML = '<div class="loading">No entries yet! Be the first ➕</div>';
    return;
  }

  el.innerHTML = allEntries.map((e, i) => {
    const cls   = i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : '';
    const emoji = PET_EMOJI[e.pet_type] || '🐾';
    const bg    = BG_COLORS[i % BG_COLORS.length];

    return `
      <div class="rank-row ${cls}">

        <div class="rank-num">
          ${MEDALS[i] || (i + 1)}
        </div>

        <div class="rank-pet">
          <div class="pet-av" style="background:${bg}">${emoji}</div>
          <div>
            <div class="pet-name">${e.pet_name}</div>
            <div class="pet-owner">@${e.owner}</div>
            <span class="type-tag">${e.pet_type}</span>
          </div>
        </div>

        <div class="score-col">
          <div class="score-num" id="sc-${e.owner}">❤️ ${e.score}</div>
          <div class="score-lbl">likes</div>
        </div>

      </div>`;
  }).join('');
}

async function loadStats() {
  const [ir, pr] = await Promise.all([apiGetInfo(), apiGetPerformance()]);

  if (!ir.ok) {
    document.getElementById('stats-log').textContent = JSON.stringify(ir.data, null, 2);
    return;
  }

  const s = ir.data.statistics;

  document.getElementById('stats-cards').innerHTML = `
    <div class="stat-card"><div class="stat-val">${ir.data.total_entries}</div><div class="stat-lbl">Entries</div></div>
    <div class="stat-card"><div class="stat-val">${s.mean}</div><div class="stat-lbl">Mean</div></div>
    <div class="stat-card"><div class="stat-val">${s.median}</div><div class="stat-lbl">Median</div></div>
    <div class="stat-card"><div class="stat-val">${s.min}</div><div class="stat-lbl">Min</div></div>
    <div class="stat-card"><div class="stat-val">${s.max}</div><div class="stat-lbl">Max</div></div>
    <div class="stat-card"><div class="stat-val">${s.iqr}</div><div class="stat-lbl">IQR</div></div>
    <div class="stat-card"><div class="stat-val">${s.q1}</div><div class="stat-lbl">Q1</div></div>
    <div class="stat-card"><div class="stat-val">${s.q3}</div><div class="stat-lbl">Q3</div></div>
    <div class="stat-card"><div class="stat-val">${ir.data.top_pet}</div><div class="stat-lbl">Top Pet 🏆</div></div>
  `;

  if (pr.ok) {
    document.getElementById('perf-table').innerHTML =
      Object.entries(pr.data.endpoint_performance).map(([ep, v]) => `
        <div class="perf-row">
          <span class="perf-ep">/${ep}</span>
          <span style="font-size:11px;color:var(--muted)">${v.calls} calls</span>
          <span class="perf-val">${v.avg_ms !== null ? v.avg_ms + ' ms' : '—'}</span>
        </div>
      `).join('');
  }

  document.getElementById('stats-log').textContent = JSON.stringify(ir.data, null, 2);
}