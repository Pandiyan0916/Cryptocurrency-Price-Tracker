/**
 * watchlist.js - Manages user favorite crypto watchlist with localStorage persistence.
 */

import { fetchGlobalStats, fetchMarkets } from './api.js';
import { formatCurrency, formatCompactNumber, formatPercentage } from './format.js';
import { initTheme } from './theme.js';
import { initGlobalSearch } from './search.js';
import { initAuth } from './auth.js';
import { initCurrencySelector } from './currency.js';

const WATCHLIST_KEY = 'coinpulse_watchlist';

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initGlobalSearch();
  initAuth();
  initCurrencySelector();
  loadHeaderGlobal();
  loadWatchlistPage();

  window.addEventListener('currencyChanged', () => {
    loadWatchlistPage();
  });

  const clearBtn = document.getElementById('clear-watchlist-btn');
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      if (confirm('Are you sure you want to clear your watchlist?')) {
        localStorage.removeItem(WATCHLIST_KEY);
        loadWatchlistPage();
      }
    });
  }
});

function getWatchlist() {
  try {
    return JSON.parse(localStorage.getItem(WATCHLIST_KEY) || '[]');
  } catch (e) {
    return [];
  }
}

function removeFromWatchlist(coinId) {
  let list = getWatchlist().filter(id => id !== coinId);
  localStorage.setItem(WATCHLIST_KEY, JSON.stringify(list));
  loadWatchlistPage();
}

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

async function loadWatchlistPage() {
  const tbody = document.getElementById('watchlist-tbody');
  if (!tbody) return;

  const watchlistIds = getWatchlist();
  if (watchlistIds.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" class="text-center padding-xl">
          <i class="far fa-star icon-3x text-muted margin-bottom-md"></i>
          <h3>Your Watchlist is Empty</h3>
          <p class="text-muted margin-bottom-md">Star cryptocurrencies on the markets page to build your personalized watchlist.</p>
          <a href="index.html" class="btn btn-sm btn-outline">Explore Markets</a>
        </td>
      </tr>
    `;
    return;
  }

  try {
    const res = await fetchMarkets(1, 100, 'market_cap_desc', '', watchlistIds.join(','));
    const coins = res.data.filter(c => watchlistIds.includes(c.id));

    if (coins.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">No current market data for saved watchlist coins.</td></tr>`;
      return;
    }

    tbody.innerHTML = coins.map(c => {
      const chg24h = c.price_change_percentage_24h_in_currency || 0.0;
      const class24h = chg24h >= 0 ? 'text-success' : 'text-danger';

      return `
        <tr>
          <td class="th-fav">
            <i class="fas fa-star text-warning remove-star-btn" data-id="${c.id}" title="Remove from watchlist"></i>
          </td>
          <td class="text-muted">#${c.market_cap_rank || '—'}</td>
          <td>
            <a href="coin.html?id=${encodeURIComponent(c.id)}" class="coin-name-cell">
              <img src="${c.image || 'https://assets.coingecko.com/coins/images/1/small/bitcoin.png'}" class="coin-icon" alt="${c.name}">
              <span class="coin-name">${escapeHtml(c.name)}</span>
              <span class="coin-symbol">${escapeHtml(c.symbol.toUpperCase())}</span>
            </a>
          </td>
          <td class="text-right font-semibold">${formatCurrency(c.current_price)}</td>
          <td class="text-right ${class24h}">${formatPercentage(chg24h)}</td>
          <td class="text-right font-semibold">${formatCompactNumber(c.market_cap)}</td>
          <td class="text-right">${formatCompactNumber(c.total_volume)}</td>
          <td class="text-right">
            <button class="btn btn-sm btn-outline remove-btn" data-id="${c.id}">Remove</button>
          </td>
        </tr>
      `;
    }).join('');

    tbody.querySelectorAll('.remove-btn, .remove-star-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const id = btn.getAttribute('data-id');
        if (id) removeFromWatchlist(id);
      });
    });

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Failed to load watchlist: ${escapeHtml(err.message)}</td></tr>`;
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
