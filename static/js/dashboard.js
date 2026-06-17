/**
 * Payfin Financial — Dashboard JS
 * dashboard.js — Main banking dashboard logic
 */

'use strict';

const { Auth, API, Toast, Fmt, Modal, Form, animateNumber, confirmDialog } = window.Payfin;

// State
let state = {
  accounts: [],
  activeAccount: null,
  stats: null,
  transactions: [],
};

// ── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  // Validate session via server — the HttpOnly cookie handles auth automatically.
  // We do NOT rely on localStorage isLoggedIn() here to avoid Base64URL redirect loops.
  const meResult = await API.get('/api/auth/me');
  if (!meResult?.ok) { window.location.href = '/login'; return; }
  const user = meResult.data.user;

  // Keep localStorage in sync with fresh token if available
  // (no action needed — cookie handles server auth; localStorage is for client-side UX only)

  // Update UI with user info
  document.querySelectorAll('[data-user-name]').forEach(el => el.textContent = user.full_name);
  document.querySelectorAll('[data-user-initials]').forEach(el => el.textContent = Fmt.initials(user.full_name));
  document.querySelectorAll('[data-user-upi]').forEach(el => el.textContent = user.upi_id || '—');
  document.querySelectorAll('[data-sidebar-upi]').forEach(el => el.textContent = user.upi_id || '—');

  await loadData();
}

async function loadData() {
  await Promise.all([
    loadAccounts(),
    loadStats(),
    loadTransactions(),
  ]);
}

// ── Load Accounts ─────────────────────────────────────────────────────────────
async function loadAccounts() {
  const result = await API.get('/api/accounts');
  if (!result?.ok) return;

  state.accounts = result.data.accounts || [];
  state.activeAccount = state.accounts.find(a => a.is_primary) || state.accounts[0] || null;

  renderAccounts();
  renderAccountSelector();
}

function renderAccounts() {
  const container = document.getElementById('accounts-container');
  if (!container) return;

  if (!state.accounts.length) {
    container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🏦</div><div class="empty-state-title">No accounts found</div></div>`;
    return;
  }

  container.innerHTML = state.accounts.map(acc => {
    const isPrimary = acc.is_primary;
    const isActive = state.activeAccount?.id === acc.id;
    return `
      <div class="account-pill ${isActive ? 'active' : ''}" onclick="selectAccount(${acc.id})" style="
        display:flex; align-items:center; gap:0.75rem; padding:0.75rem 1rem;
        background:${isActive ? 'var(--teal-faint)' : 'var(--bg-surface)'};
        border:1px solid ${isActive ? 'rgba(0,212,200,0.25)' : 'var(--border)'};
        border-radius:var(--radius-lg); cursor:pointer; transition:var(--transition);
        margin-bottom:0.5rem;
      ">
        <div style="
          width:40px; height:40px; border-radius:50%;
          background:${isActive ? 'var(--teal)' : 'var(--bg-elevated)'};
          display:flex; align-items:center; justify-content:center;
          color:${isActive ? 'var(--text-on-teal)' : 'var(--text-muted)'};
          font-size:1.1rem;
        ">🏦</div>
        <div style="flex:1; min-width:0;">
          <div style="font-weight:600; font-size:0.875rem; color:var(--text-primary);">${acc.account_type}</div>
          <div style="font-family:var(--font-mono); font-size:0.75rem; color:var(--text-muted);">${Fmt.accountNo(acc.account_no)}</div>
        </div>
        <div style="text-align:right;">
          <div style="font-weight:700; color:${isActive ? 'var(--teal)' : 'var(--text-primary)'}; font-size:0.9rem;">${Fmt.currency(acc.balance)}</div>
          ${isPrimary ? '<div class="badge badge-gold" style="font-size:0.6rem;">Primary</div>' : ''}
        </div>
      </div>
    `;
  }).join('');

  // Update hero balance
  renderHeroBalance();
}

function renderHeroBalance() {
  const acc = state.activeAccount;
  if (!acc) return;

  const balanceEl = document.getElementById('hero-balance');
  if (balanceEl) {
    animateNumber(balanceEl, acc.balance, '₹', '', 800);
  }
  const typeEl = document.getElementById('hero-acc-type');
  if (typeEl) typeEl.textContent = acc.account_type;

  const noEl = document.getElementById('hero-acc-no');
  if (noEl) noEl.textContent = Fmt.accountNo(acc.account_no);
}

function renderAccountSelector() {
  const sel = document.getElementById('account-selector');
  if (!sel || !state.accounts.length) return;
  sel.innerHTML = state.accounts.map(a =>
    `<option value="${a.id}">${a.account_type} — ${Fmt.accountNo(a.account_no)}</option>`
  ).join('');
  if (state.activeAccount) sel.value = state.activeAccount.id;
}

function selectAccount(id) {
  state.activeAccount = state.accounts.find(a => a.id === id);
  renderAccounts();
  loadTransactions();
}

// ── Load Stats ────────────────────────────────────────────────────────────────
async function loadStats() {
  const result = await API.get('/api/dashboard/stats');
  if (!result?.ok) return;

  state.stats = result.data.stats;
  renderStats();
}

function renderStats() {
  const s = state.stats;
  if (!s) return;

  setElText('stat-total-balance',   Fmt.currency(s.total_balance));
  setElText('stat-monthly-credits', Fmt.currency(s.monthly_credits));
  setElText('stat-monthly-debits',  Fmt.currency(s.monthly_debits));
  setElText('stat-txn-count',       s.txn_count_30d);
  setElText('stat-account-count',   s.account_count);
}

// ── Load Transactions ─────────────────────────────────────────────────────────
async function loadTransactions() {
  if (!state.activeAccount) return;

  const result = await API.get(`/api/transactions/account/${state.activeAccount.id}?limit=20`);
  if (!result?.ok) return;

  state.transactions = result.data.transactions || [];
  renderTransactions();
}

function renderTransactions() {
  const container = document.getElementById('recent-transactions');
  if (!container) return;

  if (!state.transactions.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📋</div>
        <div class="empty-state-title">No transactions yet</div>
        <div class="empty-state-desc">Deposit funds to get started</div>
      </div>`;
    return;
  }

  container.innerHTML = state.transactions.slice(0, 8).map(t => {
    const isCredit = t.txn_type === 'CREDIT';
    const catClass = t.txn_category === 'UPI' ? 'upi' : t.txn_category === 'PAYMENT' ? 'payment' : (isCredit ? 'credit' : 'debit');
    const catIcon  = t.txn_category === 'UPI' ? '⚡' : t.txn_category === 'PAYMENT' ? '💳' : (isCredit ? '↓' : '↑');

    return `
      <div style="
        display:flex; align-items:center; gap:1rem; padding:0.875rem;
        border-bottom:1px solid var(--border);
        transition:var(--transition);
      " onmouseenter="this.style.background='var(--bg-surface)'" onmouseleave="this.style.background='transparent'">
        <div class="txn-icon ${catClass}">${catIcon}</div>
        <div style="flex:1; min-width:0;">
          <div style="font-weight:500; font-size:0.875rem; color:var(--text-primary); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${t.description || t.txn_type}</div>
          <div style="font-size:0.72rem; color:var(--text-muted);">${Fmt.date(t.created_at)} · <span class="badge badge-${catClass === 'upi' ? 'teal' : catClass === 'payment' ? 'blue' : catClass}">${t.txn_category}</span></div>
        </div>
        <div style="text-align:right; flex-shrink:0;">
          <div class="txn-amount ${isCredit ? 'credit' : 'debit'}">${isCredit ? '+' : '−'}${Fmt.currency(t.amount)}</div>
          <div style="font-size:0.72rem; color:var(--text-muted);">${Fmt.currency(t.balance_after)}</div>
        </div>
      </div>`;
  }).join('');
}

// ── Quick Actions ─────────────────────────────────────────────────────────────
window.openDepositModal = function() {
  if (!state.activeAccount) { Toast.error('No account selected'); return; }

  const overlay = Modal.show(`
    <div class="modal">
      <div class="modal-header">
        <h3 class="modal-title">💰 Deposit Funds</h3>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">✕</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">Amount (₹)</label>
          <div class="input-group">
            <span class="input-prefix">₹</span>
            <input id="deposit-amount" class="form-input" type="number" min="1" step="0.01" placeholder="e.g. 5000" style="padding-left:2.5rem;">
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Description</label>
          <input id="deposit-desc" class="form-input" type="text" placeholder="e.g. Salary credit" value="Deposit">
        </div>
        <div id="deposit-error" class="alert alert-error" style="display:none;"></div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
        <button class="btn btn-primary" id="deposit-confirm-btn" onclick="doDeposit()">Deposit</button>
      </div>
    </div>
  `);
  setTimeout(() => overlay.querySelector('#deposit-amount')?.focus(), 100);
};

window.doDeposit = async function() {
  const amount = document.getElementById('deposit-amount')?.value;
  const desc   = document.getElementById('deposit-desc')?.value || 'Deposit';
  const errEl  = document.getElementById('deposit-error');
  const btn    = document.getElementById('deposit-confirm-btn');

  if (!amount || parseFloat(amount) <= 0) {
    errEl.textContent = 'Please enter a valid amount.';
    errEl.style.display = 'flex';
    return;
  }

  Form.setLoading(btn, true);
  const result = await API.post('/api/transactions/deposit', {
    account_id: state.activeAccount.id,
    amount: parseFloat(amount),
    description: desc,
  });
  Form.setLoading(btn, false);

  if (result?.ok && result.data.success) {
    document.querySelector('.modal-overlay')?.remove();
    Toast.success('Deposit successful!', `${Fmt.currency(parseFloat(amount))} added to your account.`);
    state.activeAccount.balance = result.data.new_balance;
    await loadData();
  } else {
    errEl.textContent = result?.data?.error || 'Deposit failed.';
    errEl.style.display = 'flex';
  }
};

window.openWithdrawModal = function() {
  if (!state.activeAccount) { Toast.error('No account selected'); return; }

  const overlay = Modal.show(`
    <div class="modal">
      <div class="modal-header">
        <h3 class="modal-title">💸 Withdraw Funds</h3>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">✕</button>
      </div>
      <div class="modal-body">
        <div style="background:var(--bg-surface);border-radius:var(--radius-md);padding:0.75rem 1rem;margin-bottom:1rem;">
          <div style="font-size:0.75rem;color:var(--text-muted);">Available Balance</div>
          <div style="font-size:1.5rem;font-weight:800;color:var(--text-primary);">${Fmt.currency(state.activeAccount.balance)}</div>
        </div>
        <div class="form-group">
          <label class="form-label">Amount (₹)</label>
          <div class="input-group">
            <span class="input-prefix">₹</span>
            <input id="withdraw-amount" class="form-input" type="number" min="1" step="0.01" placeholder="e.g. 2000" style="padding-left:2.5rem;">
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Description</label>
          <input id="withdraw-desc" class="form-input" type="text" placeholder="e.g. ATM Withdrawal" value="Withdrawal">
        </div>
        <div id="withdraw-error" class="alert alert-error" style="display:none;"></div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
        <button class="btn btn-danger" id="withdraw-confirm-btn" onclick="doWithdraw()">Withdraw</button>
      </div>
    </div>
  `);
  setTimeout(() => overlay.querySelector('#withdraw-amount')?.focus(), 100);
};

window.doWithdraw = async function() {
  const amount = document.getElementById('withdraw-amount')?.value;
  const desc   = document.getElementById('withdraw-desc')?.value || 'Withdrawal';
  const errEl  = document.getElementById('withdraw-error');
  const btn    = document.getElementById('withdraw-confirm-btn');

  if (!amount || parseFloat(amount) <= 0) {
    errEl.textContent = 'Please enter a valid amount.';
    errEl.style.display = 'flex';
    return;
  }

  Form.setLoading(btn, true);
  const result = await API.post('/api/transactions/withdraw', {
    account_id: state.activeAccount.id,
    amount: parseFloat(amount),
    description: desc,
  });
  Form.setLoading(btn, false);

  if (result?.ok && result.data.success) {
    document.querySelector('.modal-overlay')?.remove();
    Toast.success('Withdrawal successful!', `${Fmt.currency(parseFloat(amount))} withdrawn.`);
    state.activeAccount.balance = result.data.new_balance;
    await loadData();
  } else {
    errEl.textContent = result?.data?.error || 'Withdrawal failed.';
    errEl.style.display = 'flex';
  }
};

window.openTransferModal = function() {
  if (!state.accounts.length) { Toast.error('No account selected'); return; }

  const accountOptions = state.accounts.map(a =>
    `<option value="${a.id}">${a.account_type} (${Fmt.accountNo(a.account_no)}) — ${Fmt.currency(a.balance)}</option>`
  ).join('');

  Modal.show(`
    <div class="modal">
      <div class="modal-header">
        <h3 class="modal-title">⇄ Send Transfer</h3>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">✕</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">From Account</label>
          <select id="transfer-from" class="form-select">${accountOptions}</select>
        </div>
        <div class="form-group">
          <label class="form-label">Destination Account Number</label>
          <input id="transfer-to" class="form-input" type="text" placeholder="12-digit account number" maxlength="12">
        </div>
        <div class="form-group">
          <label class="form-label">Amount (₹)</label>
          <div class="input-group">
            <span class="input-prefix">₹</span>
            <input id="transfer-amount" class="form-input" type="number" min="1" step="0.01" placeholder="e.g. 1000" style="padding-left:2.5rem;">
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Remarks (Optional)</label>
          <input id="transfer-note" class="form-input" type="text" placeholder="e.g. Rent payment">
        </div>
        <div id="transfer-error" class="alert alert-error" style="display:none;"></div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
        <button class="btn btn-primary" id="transfer-confirm-btn" onclick="doTransfer()">Send ₹</button>
      </div>
    </div>
  `);
};

window.doTransfer = async function() {
  const fromId    = document.getElementById('transfer-from')?.value;
  const toAccNo   = document.getElementById('transfer-to')?.value.trim();
  const amount    = document.getElementById('transfer-amount')?.value;
  const note      = document.getElementById('transfer-note')?.value.trim();
  const errEl     = document.getElementById('transfer-error');
  const btn       = document.getElementById('transfer-confirm-btn');

  if (!toAccNo || toAccNo.length < 10) {
    errEl.textContent = 'Please enter a valid destination account number.';
    errEl.style.display = 'flex'; return;
  }
  if (!amount || parseFloat(amount) <= 0) {
    errEl.textContent = 'Please enter a valid amount.';
    errEl.style.display = 'flex'; return;
  }

  Form.setLoading(btn, true);
  const result = await API.post('/api/transactions/transfer', {
    from_account_id: parseInt(fromId),
    to_account_no: toAccNo,
    amount: parseFloat(amount),
    note,
  });
  Form.setLoading(btn, false);

  if (result?.ok && result.data.success) {
    document.querySelector('.modal-overlay')?.remove();
    Toast.success('Transfer sent!', `${Fmt.currency(parseFloat(amount))} transferred. Ref: ${result.data.reference_id}`);
    await loadData();
  } else {
    errEl.textContent = result?.data?.error || 'Transfer failed.';
    errEl.style.display = 'flex';
  }
};

// ── Sign Out ──────────────────────────────────────────────────────────────────
window.signOut = function() {
  confirmDialog('Sign Out', 'Are you sure you want to sign out of Payfin?', async () => {
    await API.post('/api/auth/logout');
    Auth.removeToken();
    window.location.href = '/login';
  });
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function setElText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

// ── Start ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
