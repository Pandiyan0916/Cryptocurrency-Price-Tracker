/**
 * theme.js - Reliable Dark / Light theme switcher logic for CoinPulse
 */

const THEME_KEY = 'coinpulse_theme';

export function getPreferredTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === 'dark' || saved === 'light') return saved;
  return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'dark';
}

export function setTheme(theme) {
  const targetTheme = (theme === 'light') ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', targetTheme);
  if (document.body) {
    document.body.setAttribute('data-theme', targetTheme);
  }

  // Update theme icons across the page
  const themeIcons = document.querySelectorAll('#theme-icon, .theme-toggle i, .theme-icon-i');
  themeIcons.forEach(icon => {
    if (icon.tagName.toLowerCase() === 'i') {
      icon.className = targetTheme === 'light' ? 'fas fa-sun text-warning' : 'fas fa-moon';
    }
  });

  const themeLabels = document.querySelectorAll('#theme-label, .theme-label-text');
  themeLabels.forEach(label => {
    label.textContent = targetTheme === 'light' ? 'Light Mode' : 'Dark Mode';
  });

  try {
    localStorage.setItem(THEME_KEY, targetTheme);
  } catch (e) {
    console.error('LocalStorage access error:', e);
  }
}

export function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || getPreferredTheme();
  const next = (current === 'light') ? 'dark' : 'light';
  setTheme(next);
}

export function initTheme() {
  const current = getPreferredTheme();
  setTheme(current);
}

// Global delegated event listener to ensure theme toggle ALWAYS works on click
document.addEventListener('click', (e) => {
  const toggleBtn = e.target.closest('#theme-toggle-btn, .theme-toggle, #dropdown-theme-toggle');
  if (toggleBtn) {
    e.preventDefault();
    e.stopPropagation();
    toggleTheme();
  }
});

// Auto-apply theme immediately on script execution
initTheme();

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTheme);
}
