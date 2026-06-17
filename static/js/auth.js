/**
 * Payfin Financial — Authentication JS
 * auth.js — Login and Registration logic
 * Wrapped in DOMContentLoaded to ensure DOM + window.Payfin are both ready.
 */

'use strict';

document.addEventListener('DOMContentLoaded', () => {
  // Destructure after DOM is ready — window.Payfin is set by app.js which loads first
  const { Auth, API, Toast, updatePasswordStrength } = window.Payfin;

  // ── Login Page ──────────────────────────────────────────────────────────────
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    const submitBtn = document.getElementById('login-btn');
    const errorBox  = document.getElementById('login-error');

    const showError = (msg) => {
      const msgSpan = errorBox.querySelector('span:last-child');
      if (msgSpan) msgSpan.textContent = msg;
      else errorBox.textContent = msg;
      errorBox.style.display = 'flex';
    };
    const hideError = () => { errorBox.style.display = 'none'; };

    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      hideError();

      const username = document.getElementById('username').value.trim();
      const password = document.getElementById('password').value;

      if (!username || !password) {
        showError('Please enter your username and password.');
        return;
      }

      submitBtn.classList.add('btn-loading');
      submitBtn.disabled = true;

      try {
        const result = await API.post('/api/auth/login', { username, password });

        if (result && result.ok && result.data.success) {
          Auth.setToken(result.data.token);
          Toast.success('Welcome back!', `Hello, ${result.data.user.full_name}`);
          // Small delay so toast is visible, then redirect
          setTimeout(() => { window.location.href = '/dashboard'; }, 700);
        } else {
          const msg = result?.data?.error || 'Login failed. Please try again.';
          showError(msg);
          submitBtn.classList.remove('btn-loading');
          submitBtn.disabled = false;
        }
      } catch (err) {
        showError('Network error. Please check your connection.');
        submitBtn.classList.remove('btn-loading');
        submitBtn.disabled = false;
      }
    });

    // Password visibility toggle
    document.getElementById('pwd-toggle')?.addEventListener('click', () => {
      const input = document.getElementById('password');
      const btn   = document.getElementById('pwd-toggle');
      if (input.type === 'password') { input.type = 'text';     btn.textContent = '🙈'; }
      else                           { input.type = 'password'; btn.textContent = '👁️'; }
    });
  }

  // ── Register Page ───────────────────────────────────────────────────────────
  const registerForm = document.getElementById('register-form');
  if (registerForm) {
    const submitBtn  = document.getElementById('register-btn');
    const errorBox   = document.getElementById('register-error');
    const successBox = document.getElementById('register-success');

    const showError = (msg) => {
      const msgSpan = errorBox.querySelector('span:last-child');
      if (msgSpan) msgSpan.textContent = msg;
      else errorBox.textContent = msg;
      errorBox.style.display = 'flex';
      successBox.style.display = 'none';
    };
    const hideError = () => { errorBox.style.display = 'none'; };

    // Password strength meter
    document.getElementById('password')?.addEventListener('input', (e) => {
      updatePasswordStrength(e.target.value, 'strength-meter');
    });

    // Live UPI preview
    document.getElementById('username')?.addEventListener('input', (e) => {
      const val     = e.target.value.trim().toLowerCase().replace(/[^a-z0-9_]/g, '');
      const preview = document.getElementById('upi-preview');
      if (preview) preview.textContent = val ? `${val}@payfin` : '';
    });

    // Password visibility toggles
    ['pwd-toggle', 'cpwd-toggle'].forEach(id => {
      document.getElementById(id)?.addEventListener('click', () => {
        const inputId = id === 'pwd-toggle' ? 'password' : 'confirm_password';
        const input   = document.getElementById(inputId);
        const btn     = document.getElementById(id);
        if (input.type === 'password') { input.type = 'text';     btn.textContent = '🙈'; }
        else                           { input.type = 'password'; btn.textContent = '👁️'; }
      });
    });

    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      hideError();

      const data = {
        username:         document.getElementById('username').value.trim(),
        full_name:        document.getElementById('full_name').value.trim(),
        email:            document.getElementById('email').value.trim().toLowerCase(),
        phone:            document.getElementById('phone')?.value.trim() || '',
        password:         document.getElementById('password').value,
        confirm_password: document.getElementById('confirm_password').value,
        account_type:     document.getElementById('account_type')?.value || 'Savings',
      };

      if (!data.username || !data.full_name || !data.email || !data.password) {
        showError('Please fill all required fields.');
        return;
      }
      if (data.password !== data.confirm_password) {
        showError('Passwords do not match.');
        return;
      }

      submitBtn.classList.add('btn-loading');
      submitBtn.disabled = true;

      try {
        const result = await API.post('/api/auth/register', data);
        submitBtn.classList.remove('btn-loading');
        submitBtn.disabled = false;

        if (result && result.ok && result.data.success) {
          errorBox.style.display = 'none';
          successBox.innerHTML = `
            <span>🎉</span>
            <div>
              <strong>Account created successfully!</strong><br>
              Account No: <strong>${result.data.account_no}</strong><br>
              UPI ID: <strong style="color:var(--teal);">${result.data.upi_id}</strong><br>
              <a href="/login" style="color:var(--teal);margin-top:0.5rem;display:inline-block;font-weight:600;">
                Sign in now →
              </a>
            </div>
          `;
          successBox.style.display = 'flex';
          registerForm.reset();
          document.getElementById('upi-preview').textContent = '';
        } else {
          showError(result?.data?.error || 'Registration failed. Please try again.');
        }
      } catch (err) {
        submitBtn.classList.remove('btn-loading');
        submitBtn.disabled = false;
        showError('Network error. Please check your connection.');
      }
    });
  }

}); // end DOMContentLoaded
