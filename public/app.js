const state = { user: null, view: 'compare', lastQuery: '' };

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.error || `Request failed (${res.status})`);
  return json;
}

function money(n, currency = 'USD') {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(n);
}

// ---------- Navigation ----------
function showView(name) {
  state.view = name;
  $$('.tab').forEach(b => b.classList.toggle('active', b.dataset.view === name));
  $$('.view').forEach(v => v.classList.toggle('active', v.id === `view-${name}`));
  if (name === 'wholesalers') renderWholesalers();
}

$$('.tab').forEach(b => b.addEventListener('click', () => showView(b.dataset.view)));

// ---------- Account ----------
function renderAccount() {
  const area = $('#account-area');
  area.innerHTML = '';
  if (state.user) {
    const span = document.createElement('span');
    span.className = 'email';
    span.textContent = state.user.email;
    const btn = document.createElement('button');
    btn.className = 'ghost';
    btn.textContent = 'Sign out';
    btn.onclick = signOut;
    area.append(span, btn);
  } else {
    const btn = document.createElement('button');
    btn.className = 'ghost';
    btn.id = 'signin-btn';
    btn.textContent = 'Sign in';
    btn.onclick = () => openModal('#signin-modal');
    area.append(btn);
  }
}

async function refreshUser() {
  const { user } = await api('/api/auth/me');
  state.user = user;
  renderAccount();
}

async function signOut() {
  await api('/api/auth/logout', { method: 'POST' });
  state.user = null;
  renderAccount();
  if (state.view === 'wholesalers') showView('compare');
  if (state.lastQuery) runSearch(state.lastQuery);
}

// ---------- Modals ----------
function openModal(sel) { $(sel).classList.remove('hidden'); }
function closeModal(sel) { $(sel).classList.add('hidden'); }
document.addEventListener('click', e => {
  if (e.target.matches('[data-close]')) {
    e.target.closest('.modal').classList.add('hidden');
  }
});

$('#signin-form').addEventListener('submit', async e => {
  e.preventDefault();
  const email = new FormData(e.target).get('email');
  try {
    const { user } = await api('/api/auth/login', { method: 'POST', body: { email } });
    state.user = user;
    renderAccount();
    closeModal('#signin-modal');
    e.target.reset();
    if (state.view === 'wholesalers') renderWholesalers();
    if (state.lastQuery) runSearch(state.lastQuery);
  } catch (err) {
    alert(err.message);
  }
});

// ---------- Search & Compare ----------
$('#search-btn').addEventListener('click', () => runSearch($('#search-input').value));
$('#search-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') runSearch(e.target.value);
});

async function runSearch(query) {
  state.lastQuery = query;
  const results = $('#results');
  results.innerHTML = '<div class="empty">Searching all wholesalers…</div>';

  const data = await api(`/api/search?q=${encodeURIComponent(query)}`);
  renderSearchResults(data);
}

function renderSearchResults(data) {
  const banner = $('#status-banner');
  const blocked = data.results.filter(r => r.status === 'requires_signin' || r.status === 'requires_connection' || r.status === 'auth_failed');

  if (blocked.length === 0) {
    banner.classList.add('hidden');
  } else {
    banner.classList.remove('hidden');
    banner.className = 'banner info';
    const names = blocked.map(r => r.wholesaler.name).join(', ');
    const needsSignin = blocked.some(r => r.status === 'requires_signin');
    const needsConn = blocked.some(r => r.status === 'requires_connection');
    const needsAuth = blocked.some(r => r.status === 'auth_failed');
    const parts = [];
    if (needsSignin) parts.push('Sign in to enable login-gated wholesalers');
    if (needsConn) parts.push('Connect your trade account on the Wholesalers tab');
    if (needsAuth) parts.push('A connection has invalid credentials — re-connect to refresh');
    banner.innerHTML = `<strong>${blocked.length} wholesaler(s) not included:</strong> ${names}. ${parts.join('. ')}.`;
  }

  const results = $('#results');
  if (!data.comparison.length) {
    results.innerHTML = `<div class="empty">No matching products found for "${data.query || 'your search'}".</div>`;
    return;
  }

  results.innerHTML = '';
  for (const row of data.comparison) {
    const card = document.createElement('div');
    card.className = 'comparison-card';
    card.innerHTML = `
      <div>
        <h3>${escapeHtml(row.name)}
          ${row.spread > 0 ? `<span class="spread">save ${money(row.spread)} (${row.spreadPct}%)</span>` : ''}
        </h3>
        <div class="sku">SKU ${escapeHtml(row.sku)} · per ${escapeHtml(row.unit)}</div>
        <table class="offers-table">
          <thead>
            <tr><th>Wholesaler</th><th>Price</th><th>Stock</th><th>Min Qty</th><th>Ships in</th><th></th></tr>
          </thead>
          <tbody>
            ${row.offers.map((o, i) => `
              <tr class="${i === 0 ? 'best' : ''}">
                <td>${escapeHtml(o.wholesalerName)}</td>
                <td class="price">${money(o.price, o.currency)}${i === 0 ? '<span class="badge">best</span>' : ''}</td>
                <td>${o.stock.toLocaleString()}</td>
                <td>${o.minOrderQty}</td>
                <td>${escapeHtml(o.shipsIn)}</td>
                <td><a href="${escapeAttr(o.productUrl)}" target="_blank" rel="noopener">View</a></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
    results.append(card);
  }
}

// ---------- Wholesalers / Connections ----------
async function renderWholesalers() {
  const list = $('#wholesaler-list');
  if (!state.user) {
    list.innerHTML = `<div class="empty">Sign in to connect wholesalers that require login.</div>`;
    return;
  }
  list.innerHTML = '<div class="empty">Loading…</div>';
  const { wholesalers } = await api('/api/wholesalers');
  list.innerHTML = '';
  for (const w of wholesalers) {
    const row = document.createElement('div');
    row.className = 'wholesaler-row';
    const isPublic = w.authType === 'none';
    const isConnected = !!w.connection;
    const pill = isPublic
      ? '<span class="status-pill open">Open catalog</span>'
      : isConnected
        ? `<span class="status-pill connected">Connected</span>`
        : `<span class="status-pill disconnected">Not connected</span>`;

    row.innerHTML = `
      <div>
        <div class="name">${escapeHtml(w.name)} ${pill}</div>
        <div class="tagline">${escapeHtml(w.tagline || '')}</div>
      </div>
      <div class="actions"></div>
    `;
    const actions = row.querySelector('.actions');
    if (!isPublic) {
      if (isConnected) {
        const btn = document.createElement('button');
        btn.className = 'danger';
        btn.textContent = 'Disconnect';
        btn.onclick = async () => {
          if (!confirm(`Disconnect from ${w.name}?`)) return;
          await api(`/api/wholesalers/${w.id}/connect`, { method: 'DELETE' });
          renderWholesalers();
        };
        actions.append(btn);
      } else {
        const btn = document.createElement('button');
        btn.className = 'primary';
        btn.textContent = 'Connect';
        btn.onclick = () => openConnectModal(w);
        actions.append(btn);
      }
    }
    list.append(row);
  }
}

function openConnectModal(wholesaler) {
  $('#connect-title').textContent = `Connect to ${wholesaler.name}`;
  $('#connect-subtitle').textContent = wholesaler.tagline || '';
  const fields = $('#connect-fields');
  fields.innerHTML = '';
  for (const f of (wholesaler.credentialFields || [])) {
    const label = document.createElement('label');
    label.textContent = f.label;
    const input = document.createElement('input');
    input.name = f.name;
    input.type = f.type || 'text';
    input.required = true;
    input.autocomplete = f.type === 'password' ? 'new-password' : 'off';
    label.append(input);
    fields.append(label);
  }
  $('#connect-error').classList.add('hidden');
  const form = $('#connect-form');
  form.onsubmit = async e => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    try {
      await api(`/api/wholesalers/${wholesaler.id}/connect`, {
        method: 'POST',
        body: { credentials: data },
      });
      closeModal('#connect-modal');
      renderWholesalers();
      if (state.lastQuery) runSearch(state.lastQuery);
    } catch (err) {
      const box = $('#connect-error');
      box.textContent = err.message;
      box.classList.remove('hidden');
    }
  };
  openModal('#connect-modal');
}

// ---------- Helpers ----------
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

// ---------- Boot ----------
(async function init() {
  await refreshUser();
  runSearch('');
})();
