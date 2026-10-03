/**
 * auth.js - User Authentication, Login Modal, SQLite Sync & Hamburger Menu Manager
 */

const AUTH_STORAGE_KEY = 'coinpulse_user_session';

export function getStoredUser() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

export function setStoredUser(user) {
  try {
    if (user) {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    }
  } catch (e) {
    console.error('LocalStorage error:', e);
  }
}

let isAuthInitialized = false;
let isClickDelegationSetup = false;

export function initAuth() {
  if (isAuthInitialized) {
    updateUserUI();
    return;
  }
  isAuthInitialized = true;

  injectAuthModal();
  setupGlobalClickDelegation();
  updateUserUI();

  // If user is already logged in, sync user data from backend
  const user = getStoredUser();
  if (user && user.token) {
    fetchUserSync(user.token);
  }
}

function injectAuthModal() {
  if (document.getElementById('auth-modal')) return;

  const modalHTML = `
    <div class="modal-backdrop hidden" id="auth-modal" aria-hidden="true">
      <div class="modal-box auth-modal-box">
        <div class="modal-header">
          <div class="auth-tabs">
            <button class="auth-tab active" id="tab-btn-login" type="button">Sign In</button>
            <button class="auth-tab" id="tab-btn-register" type="button">Create Account</button>
          </div>
          <button class="modal-close" id="close-auth-modal" aria-label="Close">&times;</button>
        </div>
        
        <div class="auth-form-container">
          <!-- Demo Login Hint Box -->
          <div class="auth-demo-hint">
            <i class="fas fa-info-circle text-primary"></i> Demo Account: <strong>demo@coinpulse.com</strong> | Password: <strong>password123</strong>
          </div>

          <!-- Error Feedback Banner -->
          <div class="auth-error-banner hidden" id="auth-error-banner">
            <i class="fas fa-exclamation-triangle"></i> <span id="auth-error-text">Invalid email or password.</span>
          </div>

          <!-- Login Form -->
          <form id="auth-login-form" class="auth-form" action="javascript:void(0);" onsubmit="return false;">
            <div class="form-group">
              <label class="form-label" for="auth-email">Email Address</label>
              <div class="input-icon-group">
                <i class="fas fa-envelope input-icon"></i>
                <input type="email" id="auth-email" class="form-input" placeholder="demo@coinpulse.com" value="demo@coinpulse.com" required autocomplete="email">
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="auth-password">Password</label>
              <div class="input-icon-group password-group">
                <i class="fas fa-lock input-icon"></i>
                <input type="password" id="auth-password" class="form-input" placeholder="••••••••" value="password123" required autocomplete="current-password">
                <i class="fas fa-eye password-toggle-btn" id="toggle-login-pass" title="Toggle password visibility"></i>
              </div>
            </div>
            <div class="auth-options">
              <label class="checkbox-label"><input type="checkbox" id="auth-remember" checked> Remember me</label>
              <a href="#" class="forgot-link" id="forgot-password-link">Forgot password?</a>
            </div>
            <button type="submit" class="btn btn-primary btn-block" id="login-submit-btn">
              <i class="fas fa-sign-in-alt"></i> Sign In
            </button>
          </form>

          <!-- Registration Form -->
          <form id="auth-register-form" class="auth-form hidden" action="javascript:void(0);" onsubmit="return false;">
            <div class="form-group">
              <label class="form-label" for="reg-full-name">Full Name</label>
              <div class="input-icon-group">
                <i class="fas fa-user input-icon"></i>
                <input type="text" id="reg-full-name" class="form-input" placeholder="Satoshi Nakamoto" required>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="reg-email-input">Email Address</label>
              <div class="input-icon-group">
                <i class="fas fa-envelope input-icon"></i>
                <input type="email" id="reg-email-input" class="form-input" placeholder="satoshi@example.com" required>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="reg-password-input">Password</label>
              <div class="input-icon-group password-group">
                <i class="fas fa-lock input-icon"></i>
                <input type="password" id="reg-password-input" class="form-input" placeholder="At least 6 characters" minlength="6" required>
                <i class="fas fa-eye password-toggle-btn" id="toggle-reg-pass" title="Toggle password visibility"></i>
              </div>
            </div>
            <button type="submit" class="btn btn-primary btn-block" id="reg-submit-btn">
              <i class="fas fa-user-plus"></i> Create Free Account
            </button>
          </form>

          <div class="auth-divider"><span>OR CONTINUE WITH</span></div>
          <div class="social-login-grid">
            <button type="button" class="btn btn-outline social-btn" id="btn-social-google">
              <i class="fab fa-google text-danger"></i> Google
            </button>
            <button type="button" class="btn btn-outline social-btn" id="btn-social-apple">
              <i class="fab fa-apple"></i> Apple
            </button>
          </div>
        </div>
      </div>
    </div>
  `;

  document.body.insertAdjacentHTML('beforeend', modalHTML);

  const closeBtn = document.getElementById('close-auth-modal');
  const modal = document.getElementById('auth-modal');
  const tabLogin = document.getElementById('tab-btn-login');
  const tabRegister = document.getElementById('tab-btn-register');
  const loginForm = document.getElementById('auth-login-form');
  const registerForm = document.getElementById('auth-register-form');
  const googleBtn = document.getElementById('btn-social-google');
  const appleBtn = document.getElementById('btn-social-apple');

  const toggleLoginPass = document.getElementById('toggle-login-pass');
  if (toggleLoginPass) {
    toggleLoginPass.addEventListener('click', () => {
      const input = document.getElementById('auth-password');
      if (input) {
        const isPass = input.type === 'password';
        input.type = isPass ? 'text' : 'password';
        toggleLoginPass.className = isPass ? 'fas fa-eye-slash password-toggle-btn' : 'fas fa-eye password-toggle-btn';
      }
    });
  }

  const toggleRegPass = document.getElementById('toggle-reg-pass');
  if (toggleRegPass) {
    toggleRegPass.addEventListener('click', () => {
      const input = document.getElementById('reg-password-input');
      if (input) {
        const isPass = input.type === 'password';
        input.type = isPass ? 'text' : 'password';
        toggleRegPass.className = isPass ? 'fas fa-eye-slash password-toggle-btn' : 'fas fa-eye password-toggle-btn';
      }
    });
  }

  if (closeBtn) closeBtn.addEventListener('click', () => closeAuthModal());
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeAuthModal();
    });
  }

  if (tabLogin && tabRegister) {
    tabLogin.addEventListener('click', () => switchAuthTab('login'));
    tabRegister.addEventListener('click', () => switchAuthTab('register'));
  }

  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideAuthError();
      const email = document.getElementById('auth-email').value.trim();
      const password = document.getElementById('auth-password').value;

      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Invalid credentials.');

        const user = { ...data.user, token: data.token };
        setStoredUser(user);
        updateUserUI();
        closeAuthModal();
        showToast(`Welcome back, ${user.name}!`, 'success');
        await fetchUserSync(data.token);
        window.dispatchEvent(new CustomEvent('userAuthStateChanged'));
      } catch (err) {
        showAuthError(err.message || 'Invalid email or password.');
      }
    });
  }

  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideAuthError();
      const name = document.getElementById('reg-full-name').value.trim();
      const email = document.getElementById('reg-email-input').value.trim();
      const password = document.getElementById('reg-password-input').value;

      try {
        const res = await fetch('/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, email, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Registration failed.');

        const user = { ...data.user, token: data.token };
        setStoredUser(user);
        updateUserUI();
        closeAuthModal();
        showToast(`Account created! Welcome, ${user.name}`, 'success');
      } catch (err) {
        showAuthError(err.message || 'Registration failed.');
      }
    });
  }

  if (googleBtn) {
    googleBtn.addEventListener('click', () => {
      const user = { name: 'Google User', email: 'user@google.com', token: 'google_token_123', provider: 'Google' };
      setStoredUser(user);
      updateUserUI();
      closeAuthModal();
      showToast('Signed in with Google Account', 'success');
    });
  }

  if (appleBtn) {
    appleBtn.addEventListener('click', () => {
      const user = { name: 'Apple User', email: 'user@apple.com', token: 'apple_token_456', provider: 'Apple' };
      setStoredUser(user);
      updateUserUI();
      closeAuthModal();
      showToast('Signed in with Apple ID', 'success');
    });
  }
}

function showAuthError(msg) {
  const banner = document.getElementById('auth-error-banner');
  const text = document.getElementById('auth-error-text');
  if (banner && text) {
    text.textContent = msg;
    banner.classList.remove('hidden');
  }
}

function hideAuthError() {
  const banner = document.getElementById('auth-error-banner');
  if (banner) banner.classList.add('hidden');
}

export async function fetchUserSync(token) {
  if (!token) return;
  try {
    const res = await fetch(`/api/user/sync?token=${encodeURIComponent(token)}`);
    if (!res.ok) return;
    const data = await res.json();
    if (data.watchlist && data.watchlist.length) {
      localStorage.setItem('coinpulse_watchlist', JSON.stringify(data.watchlist));
    }
    if (data.portfolio && data.portfolio.length) {
      localStorage.setItem('coinpulse_portfolio', JSON.stringify(data.portfolio));
    }
  } catch (e) {
    console.error('User sync error:', e);
  }
}

export async function pushUserSync() {
  const user = getStoredUser();
  if (!user || !user.token) return;

  try {
    const watchlist = JSON.parse(localStorage.getItem('coinpulse_watchlist') || '[]');
    const portfolio = JSON.parse(localStorage.getItem('coinpulse_portfolio') || '[]');

    await fetch('/api/user/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token: user.token,
        watchlist: watchlist,
        portfolio: portfolio
      })
    });
  } catch (e) {
    console.error('Push sync error:', e);
  }
}

function setupGlobalClickDelegation() {
  if (isClickDelegationSetup) return;
  isClickDelegationSetup = true;

  document.addEventListener('click', (e) => {
    const loginTrigger = e.target.closest('#header-login-btn, #open-login-btn, .open-auth-btn');
    if (loginTrigger) {
      e.preventDefault();
      const user = getStoredUser();
      if (user) {
        toggleUserDropdown();
      } else {
        openAuthModal('login');
        closeUserDropdown();
      }
      return;
    }

    const hamburgerTrigger = e.target.closest('#user-menu-btn, .hamburger-btn');
    if (hamburgerTrigger) {
      e.preventDefault();
      e.stopPropagation();
      toggleUserDropdown();
      return;
    }

    const logoutTrigger = e.target.closest('#menu-logout-btn, .logout-btn');
    if (logoutTrigger) {
      e.preventDefault();
      pushUserSync().finally(() => {
        setStoredUser(null);
        localStorage.removeItem('coinpulse_portfolio');
        localStorage.removeItem('coinpulse_watchlist');
        updateUserUI();
        closeUserDropdown();
        window.dispatchEvent(new CustomEvent('userAuthStateChanged'));
        showToast('Logged out successfully', 'info');
        window.location.href = 'index.html';
      });
      return;
    }

    const dropdown = document.getElementById('user-dropdown-menu');
    if (dropdown && dropdown.classList.contains('active')) {
      if (!dropdown.contains(e.target) && !e.target.closest('#user-menu-btn, #header-login-btn')) {
        closeUserDropdown();
      }
    }
  });
}

export function openAuthModal(mode = 'login') {
  hideAuthError();
  const modal = document.getElementById('auth-modal');
  if (modal) {
    modal.classList.remove('hidden');
    switchAuthTab(mode);
  }
}

export function closeAuthModal() {
  const modal = document.getElementById('auth-modal');
  if (modal) {
    modal.classList.add('hidden');
  }
}

function switchAuthTab(mode) {
  hideAuthError();
  const tabLogin = document.getElementById('tab-btn-login');
  const tabRegister = document.getElementById('tab-btn-register');
  const loginForm = document.getElementById('auth-login-form');
  const registerForm = document.getElementById('auth-register-form');

  if (mode === 'login') {
    tabLogin?.classList.add('active');
    tabRegister?.classList.remove('active');
    loginForm?.classList.remove('hidden');
    registerForm?.classList.add('hidden');
  } else {
    tabRegister?.classList.add('active');
    tabLogin?.classList.remove('active');
    registerForm?.classList.remove('hidden');
    loginForm?.classList.add('hidden');
  }
}

function toggleUserDropdown() {
  const dropdown = document.getElementById('user-dropdown-menu');
  if (dropdown) {
    dropdown.classList.toggle('active');
  }
}

function closeUserDropdown() {
  const dropdown = document.getElementById('user-dropdown-menu');
  if (dropdown) {
    dropdown.classList.remove('active');
  }
}

function toggleMobileNav() {
  const navMenu = document.getElementById('nav-menu');
  if (navMenu) {
    navMenu.classList.toggle('mobile-open');
  }
}

export function updateUserUI() {
  const user = getStoredUser();
  const headerLoginBtn = document.getElementById('header-login-btn');
  const menuInfoBox = document.getElementById('menu-user-info-box');
  const guestItem = document.getElementById('menu-guest-item');
  const logoutItem = document.getElementById('menu-logout-item');

  if (user) {
    if (headerLoginBtn) {
      headerLoginBtn.innerHTML = `<i class="fas fa-user-check text-success"></i> <span>${escapeHTML(user.name)}</span>`;
    }

    if (menuInfoBox) {
      menuInfoBox.innerHTML = `
        <div class="user-avatar-badge">${escapeHTML(user.name.charAt(0).toUpperCase())}</div>
        <div class="user-details-text">
          <div class="user-name-title">${escapeHTML(user.name)}</div>
          <div class="user-email-subtitle">${escapeHTML(user.email)}</div>
        </div>
      `;
    }

    if (guestItem) guestItem.classList.add('hidden');
    if (logoutItem) logoutItem.classList.remove('hidden');
  } else {
    if (headerLoginBtn) {
      headerLoginBtn.innerHTML = `<i class="fas fa-user-circle"></i> <span>Log In</span>`;
    }

    if (menuInfoBox) {
      menuInfoBox.innerHTML = `
        <div class="user-avatar-badge guest"><i class="fas fa-user-circle"></i></div>
        <div class="user-details-text">
          <div class="user-name-title">Guest User</div>
          <div class="user-email-subtitle">Sign in to sync preferences</div>
        </div>
      `;
    }

    if (guestItem) guestItem.classList.remove('hidden');
    if (logoutItem) logoutItem.classList.add('hidden');
  }
}

export function showToast(msg, type = 'info') {
  let toast = document.getElementById('toast-notification');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast-notification';
    toast.className = 'toast-notification';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.className = `toast-notification toast-${type} show`;
  setTimeout(() => {
    toast.classList.remove('show');
  }, 3000);
}

function escapeHTML(str) {
  if (!str) return '';
  return String(str).replace(/[&<>'"]/g, 
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}

// Auto init on load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAuth);
} else {
  initAuth();
}
