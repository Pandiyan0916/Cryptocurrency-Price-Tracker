/**
 * categories.js - Handles loading crypto categories listing.
 */

import { fetchCategories, fetchGlobalStats } from './api.js';
import { formatCompactNumber, formatPercentage } from './format.js';
import { initTheme } from './theme.js';
import { initGlobalSearch } from './search.js';
import { initAuth } from './auth.js';
import { initCurrencySelector } from './currency.js';

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initGlobalSearch();
  initAuth();
  initCurrencySelector();
  loadHeaderGlobal();
  loadCategoriesList();

  window.addEventListener('currencyChanged', () => {
    loadHeaderGlobal();
    loadCategoriesList();
  });
});

async function loadHeaderGlobal() {
  try {
    const data = await fetchGlobalStats();
    const stats = data.data;
    if (document.getElementById('global-cryptos')) document.getElementById('global-cryptos').textContent = stats.active_cryptocurrencies.toLocaleString();
    if (document.getElementById('global-mcap')) document.getElementById('global-mcap').textContent = formatCompactNumber(stats.total_market_cap_usd);
    if (document.getElementById('global-vol')) document.getElementById('global-vol').textContent = formatCompactNumber(stats.total_volume_usd);
    const badge = document.getElementById('data-source-badge');
    if (badge) badge.textContent = `Source: ${data.source.toUpperCase()}`;
  } catch (err) {
    console.error('Global stats error:', err);
  }
}

async function loadCategoriesList() {
  const tbody = document.getElementById('categories-tbody');
  if (!tbody) return;

  try {
    const data = await fetchCategories();
    const categories = data.data || [];

    if (!categories.length) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center">No category data available.</td></tr>`;
      return;
    }

    tbody.innerHTML = categories.map((cat, idx) => {
      const chg = cat.market_cap_change_24h !== null && cat.market_cap_change_24h !== undefined ? cat.market_cap_change_24h : 0.0;
      const chgClass = chg >= 0 ? 'text-success' : 'text-danger';
      const chgIcon = chg >= 0 ? '<i class="fas fa-caret-up"></i>' : '<i class="fas fa-caret-down"></i>';

      const topCoins = (cat.top_3_coins || []).map(icon => {
        if (typeof icon === 'string' && icon.startsWith('http')) {
          return `<img src="${icon}" class="top-coin-thumb" alt="coin">`;
        }
        return `<span class="badge badge-tag">${escapeHtml(icon)}</span>`;
      }).join(' ');

      return `
        <tr>
          <td class="text-muted">#${idx + 1}</td>
          <td>
            <a href="index.html?q=${encodeURIComponent(cat.name)}" class="coin-name-cell">
              <strong>${escapeHtml(cat.name)}</strong>
            </a>
          </td>
          <td>${topCoins || '-'}</td>
          <td class="${chgClass}">${chgIcon} ${formatPercentage(chg)}</td>
          <td>${cat.volume_24h ? formatCompactNumber(cat.volume_24h) : '-'}</td>
          <td class="text-right"><strong>${cat.market_cap ? formatCompactNumber(cat.market_cap) : '-'}</strong></td>
        </tr>
      `;
    }).join('');

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Failed to load category data. (${escapeHtml(err.message)})</td></tr>`;
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
