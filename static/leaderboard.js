// ── Leaderboard Rendering ─────────────────────────────────────────────────

const PET_EMOJI = { Dog:'🐕', Cat:'🐈', Rabbit:'🐰', Hamster:'🐹', Bird:'🐦', Other:'🐾' };
const BG_COLORS = ['#fff5f5','#f0fff8','#f0f5ff','#fffbf0','#fdf0ff','#f0faff'];
const MEDALS    = ['🥇','🥈','🥉'];
const PAGE_SIZE = 20;

let allEntries  = [];
let currentPage = 0;
let hasMore     = true;

// ── Load leaderboard ──────────────────────────────────────────────────────
async function loadLeaderboard(reset = true) {
  if (reset) {
    allEntries  = [];
    currentPage = 0;
    hasMore     = true;
  }

  const limit  = PAGE_SIZE;
  const offset = currentPage * PAGE_SIZE;
  const res    = await fetch(`/api/leaderboard?limit=${limit + offset}`);
  const data   = await res.json();

  allEntries = data.leaderboard || [];

  const countEl = document.getElementById('entry-count');
  if (countEl) countEl.textContent = data.total_entries + ' entries';

  hasMore = allEntries.length >= PAGE_SIZE;

  renderRankList();
}

// ── Render rank list ──────────────────────────────────────────────────────
function renderRankList() {
  const el = document.getElementById('rank-list');
  if (!el) return;

  if (!allEntries.length) {
    el.innerHTML = `
      <div class="loading">
        No entries yet! Post your pet to join 🐾
      </div>`;
    renderLoadMore(false);
    return;
  }

  const visible = allEntries.slice(0, (currentPage + 1) * PAGE_SIZE);

  el.innerHTML = visible.map((e, i) => {
    const isTop  = i < 3;
    const cls    = i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : 'normal';
    const emoji  = PET_EMOJI[e.pet_type] || '🐾';
    const bg     = isTop ? BG_COLORS[i] : '#f5f5f5';
    const avatar = e.pet_image
      ? `<img src="${e.pet_image}" style="width:100%;height:100%;object-fit:cover;border-radius:50%"/>`
      : emoji;
    const badge  = i === 0 ? '🥇 Gold Champion'
                 : i === 1 ? '🥈 Silver'
                 : i === 2 ? '🥉 Bronze'
                 : '';

    return `
      <div class="rank-row ${cls}" onclick="location.href='/profile?u=${e.username}'">
        <div class="rank-num">
          ${MEDALS[i] || (i + 1)}
        </div>
        <div class="rank-pet">
          <div class="pet-av" style="background:${bg}">${avatar}</div>
          <div>
            <div class="pet-name">${e.pet_name || e.username}</div>
            <div class="pet-owner">@${e.username}</div>
            ${e.pet_type ? `<span class="type-tag">${e.pet_type}</span>` : ''}
            ${badge ? `<span class="badge-tag">${badge}</span>` : ''}
          </div>
        </div>
        <div class="score-col">
          <div class="score-num" id="sc-${e.username}">❤️ ${e.total_likes}</div>
          <div class="score-lbl">likes</div>
        </div>
      </div>`;
  }).join('');

  renderLoadMore(allEntries.length > (currentPage + 1) * PAGE_SIZE);
}

// ── Load More button ──────────────────────────────────────────────────────
function renderLoadMore(show) {
  let btn = document.getElementById('load-more-btn');
  if (!btn) {
    btn = document.createElement('div');
    btn.id = 'load-more-btn';
    btn.style.textAlign = 'center';
    btn.style.marginTop = '16px';
    document.getElementById('rank-list')?.after(btn);
  }
  if (show) {
    btn.innerHTML = `
      <button onclick="loadMore()"
        style="background:#fff;border:1.5px solid var(--border);
               border-radius:20px;padding:10px 28px;font-size:13px;
               font-weight:800;cursor:pointer;font-family:'Nunito',sans-serif;
               color:var(--muted)">
        Load More ↓
      </button>`;
  } else {
    btn.innerHTML = '';
  }
}

async function loadMore() {
  currentPage++;
  const res  = await fetch(`/api/leaderboard?limit=${(currentPage + 1) * PAGE_SIZE}`);
  const data = await res.json();
  allEntries = data.leaderboard || [];
  renderRankList();
}