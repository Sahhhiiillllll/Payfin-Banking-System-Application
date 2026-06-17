/**
 * Payfin Financial — Core JS Utilities
 * app.js — API client, auth, toast system, utilities
 */

'use strict';

// ── Constants ────────────────────────────────────────────────────────────────
const API_BASE = '';
const TOKEN_KEY = 've_token';

// ── Token Management ─────────────────────────────────────────────────────────
const Auth = {
  getToken() {
    return localStorage.getItem(TOKEN_KEY);
  },
  setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
  },
  removeToken() {
    localStorage.removeItem(TOKEN_KEY);
  },

  // JWT uses URL-safe Base64 (RFC 4648): '-' instead of '+', '_' instead of '/'
  // Browser's atob() only handles standard Base64, so we must convert first.
  _decodeJWTPayload(token) {
    try {
      const part = token.split('.')[1];
      if (!part) return null;
      // Convert Base64URL → Base64, then pad to multiple of 4
      const base64 = part.replace(/-/g, '+').replace(/_/g, '/');
      const padded  = base64 + '=='.slice(0, (4 - base64.length % 4) % 4);
      return JSON.parse(atob(padded));
    } catch {
      return null;
    }
  },

  isLoggedIn() {
    const token = this.getToken();
    if (!token) return false;
    const payload = this._decodeJWTPayload(token);
    if (!payload) return false;
    return payload.exp * 1000 > Date.now();
  },

  getUser() {
    const token = this.getToken();
    if (!token) return null;
    return this._decodeJWTPayload(token);
  }
};


// ── API Client ───────────────────────────────────────────────────────────────
const API = {
  async request(method, path, body = null, opts = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...opts.headers,
    };
    const token = Auth.getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const config = {
      method,
      headers,
      credentials: 'include',
    };
    if (body && method !== 'GET') {
      config.body = JSON.stringify(body);
    }

    try {
      const resp = await fetch(`${API_BASE}${path}`, config);
      const data = await resp.json();
      if (resp.status === 401) {
        Auth.removeToken();
        window.location.href = '/login';
        return;
      }
      return { ok: resp.ok, status: resp.status, data };
    } catch (err) {
      console.error('API error:', err);
      return { ok: false, status: 0, data: { error: 'Network error. Please check your connection.' } };
    }
  },

  get(path, opts = {})       { return this.request('GET',    path, null, opts); },
  post(path, body, opts = {}) { return this.request('POST',   path, body, opts); },
  put(path, body, opts = {})  { return this.request('PUT',    path, body, opts); },
  delete(path, opts = {})    { return this.request('DELETE', path, null, opts); },
};

// ── Toast System ─────────────────────────────────────────────────────────────
const Toast = {
  container: null,
  icons: { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' },

  init() {
    if (!this.container) {
      this.container = document.getElementById('toast-container');
      if (!this.container) {
        this.container = document.createElement('div');
        this.container.id = 'toast-container';
        document.body.appendChild(this.container);
      }
    }
  },

  show(type, title, message = '', duration = 4000) {
    this.init();
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${this.icons[type] || 'ℹ️'}</span>
      <div class="toast-content">
        <div class="toast-title">${title}</div>
        ${message ? `<div class="toast-msg">${message}</div>` : ''}
      </div>
      <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
    `;
    this.container.appendChild(toast);
    if (duration > 0) {
      setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
      }, duration);
    }
  },

  success(title, msg, dur) { this.show('success', title, msg, dur); },
  error(title, msg, dur)   { this.show('error',   title, msg, dur); },
  info(title, msg, dur)    { this.show('info',    title, msg, dur); },
  warning(title, msg, dur) { this.show('warning', title, msg, dur); },
};

// ── Format Utilities ──────────────────────────────────────────────────────────
const Fmt = {
  currency(amount) {
    return '₹' + parseFloat(amount || 0).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  },
  accountNo(no) {
    if (!no) return '—';
    return '•••• •••• ' + String(no).slice(-4);
  },
  date(dt) {
    if (!dt) return '—';
    const d = new Date(dt.replace(' ', 'T') + (dt.includes('T') ? '' : 'Z'));
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  },
  dateTime(dt) {
    if (!dt) return '—';
    const d = new Date(dt.replace(' ', 'T') + (dt.includes('T') ? '' : 'Z'));
    return d.toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  },
  initials(name) {
    if (!name) return '?';
    return name.split(' ').slice(0, 2).map(p => p[0]?.toUpperCase()).join('');
  },
  referenceId(id) {
    if (!id) return '—';
    return id.length > 12 ? id.slice(0, 4) + '...' + id.slice(-4) : id;
  },
};

// ── Modal System ─────────────────────────────────────────────────────────────
const Modal = {
  show(html, opts = {}) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = html;
    document.body.appendChild(overlay);

    // Close on overlay click (if not prevented)
    if (!opts.preventClose) {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.remove();
      });
    }

    // Close on Escape
    const escHandler = (e) => {
      if (e.key === 'Escape') { overlay.remove(); document.removeEventListener('keydown', escHandler); }
    };
    document.addEventListener('keydown', escHandler);

    return overlay;
  },
  close(overlay) {
    if (overlay) overlay.remove();
  }
};

// ── Form Helpers ─────────────────────────────────────────────────────────────
const Form = {
  getData(formElement) {
    const data = {};
    const formData = new FormData(formElement);
    formData.forEach((val, key) => { data[key] = val; });
    return data;
  },

  setError(inputId, message) {
    const input = document.getElementById(inputId);
    if (!input) return;
    input.classList.add('is-error');
    let hint = input.nextElementSibling;
    if (!hint || !hint.classList.contains('form-error')) {
      hint = document.createElement('div');
      hint.className = 'form-error';
      input.parentNode.insertBefore(hint, input.nextSibling);
    }
    hint.textContent = message;
  },

  clearErrors(formElement) {
    formElement.querySelectorAll('.is-error').forEach(el => el.classList.remove('is-error'));
    formElement.querySelectorAll('.form-error').forEach(el => el.remove());
  },

  setLoading(btn, loading) {
    if (loading) {
      btn.dataset.originalText = btn.innerHTML;
      btn.classList.add('btn-loading');
      btn.disabled = true;
    } else {
      btn.innerHTML = btn.dataset.originalText || btn.innerHTML;
      btn.classList.remove('btn-loading');
      btn.disabled = false;
    }
  },
};

// ── Password Strength ─────────────────────────────────────────────────────────
function updatePasswordStrength(password, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  let score = 0;
  if (password.length >= 8) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  const labels  = ['', 'Weak', 'Fair', 'Good', 'Strong'];
  const classes = ['', 'filled-weak', 'filled-fair', 'filled-good', 'filled-strong'];

  const segs = container.querySelectorAll('.strength-segment');
  segs.forEach((seg, i) => {
    seg.className = 'strength-segment';
    if (i < score) seg.classList.add(classes[score]);
  });

  const lbl = container.querySelector('.strength-label');
  if (lbl) {
    lbl.textContent = password ? (labels[score] || 'Very Weak') : '';
    lbl.style.color = score >= 3 ? 'var(--green)' : score === 2 ? 'var(--gold)' : 'var(--red)';
  }
}

// ── Clock ─────────────────────────────────────────────────────────────────────
function startClock(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const update = () => {
    el.textContent = new Date().toLocaleTimeString('en-IN', {
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
  };
  update();
  setInterval(update, 1000);
}

// ── Copy to clipboard ─────────────────────────────────────────────────────────
async function copyToClipboard(text, successMsg = 'Copied!') {
  try {
    await navigator.clipboard.writeText(text);
    Toast.success(successMsg);
  } catch {
    Toast.error('Copy failed', 'Please copy manually.');
  }
}

// ── Confirm Dialog ────────────────────────────────────────────────────────────
function confirmDialog(title, message, onConfirm, danger = false) {
  const overlay = Modal.show(`
    <div class="modal" style="max-width:420px;">
      <div class="modal-header">
        <h3 class="modal-title">${title}</h3>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">✕</button>
      </div>
      <div class="modal-body">
        <p style="color:var(--text-second);line-height:1.6;">${message}</p>
      </div>
      <div class="modal-footer">
        <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
        <button class="btn ${danger ? 'btn-danger' : 'btn-primary'}" id="confirm-btn">Confirm</button>
      </div>
    </div>
  `);
  overlay.querySelector('#confirm-btn').addEventListener('click', () => {
    overlay.remove();
    onConfirm();
  });
}

// ── Number Animation ──────────────────────────────────────────────────────────
function animateNumber(el, target, prefix = '', suffix = '', duration = 800) {
  const start = 0;
  const startTime = performance.now();
  const format = (n) => n.toLocaleString('en-IN', { maximumFractionDigits: 2 });

  const update = (currentTime) => {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out-cubic
    const current = start + (target - start) * eased;
    el.textContent = prefix + format(current) + suffix;
    if (progress < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}

// ── Intersection Observer for animations ─────────────────────────────────────
function observeAnimations() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.animate-on-scroll').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    observer.observe(el);
  });
}

// ── DOM Ready ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  observeAnimations();
  startClock('topbar-clock');
});

// ── Export globals ────────────────────────────────────────────────────────────
window.Payfin = { Auth, API, Toast, Fmt, Modal, Form, copyToClipboard, confirmDialog, animateNumber, updatePasswordStrength };
