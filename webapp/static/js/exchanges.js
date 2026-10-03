/**
 * exchanges.js - Renders exchange listings and single exchange detail views.
 */

import { fetchExchanges, fetchExchangeDetail, fetchGlobalStats } from './api.js';
import { formatCurrency, formatCompactNumber, formatPercentage } from './format.js';
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

  if (document.getElementById('exchanges-tbody')) {
    loadExchangesList();
  } else if (document.getElementById('exchange-name')) {
    loadExchangeDetail();
  }

  window.addEventListener('currencyChanged', () => {
    loadHeaderGlobal();
    if (document.getElementById('exchanges-tbody')) {
      loadExchangesList();
    } else if (document.getElementById('exchange-name')) {
      loadExchangeDetail();
    }
  });
});

async function loadHeaderGlobal() {
  try {
    const data = await fetchGlobalStats();
    const stats = data.data;
    if (document.getElementById('global-cryptos')) document.getElementById('global-cryptos').textContent = stats.active_cryptocurrencies.toLocaleString();
    if (document.getElementById('global-mcap')) document.getElementById('global-mcap').textContent = formatCompactNumber(stats.total_market_cap_usd);
    if (document.getElementById('global-vol')) document.getElementById('global-vol').textContent = formatCompactNumber(stats.total_volume_usd);
    if (document.getElementById('global-btc-dom')) document.getElementById('global-btc-dom').textContent = stats.btc_dominance.toFixed(1);
    if (document.getElementById('global-eth-dom')) document.getElementById('global-eth-dom').textContent = (stats.eth_dominance || 14.5).toFixed(1);
    const badge = document.getElementById('data-source-badge');
    if (badge) badge.textContent = `Source: ${data.source.toUpperCase()}`;
  } catch (err) {
    console.error('Global stats error:', err);
  }
}

async function loadExchangesList() {
  const tbody = document.getElementById('exchanges-tbody');
  const errorBanner = document.getElementById('exchanges-error-banner');
  const retryBtn = document.getElementById('exchanges-retry-btn');

  if (retryBtn) retryBtn.addEventListener('click', loadExchangesList);

  try {
    if (errorBanner) errorBanner.classList.add('hidden');
    const data = await fetchExchanges(1, 50);
    const exchanges = data.data || [];

    if (!exchanges.length) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center">No exchanges available.</td></tr>`;
      return;
    }

    tbody.innerHTML = exchanges.map((ex, idx) => {
      const img = ex.image ? `<img src="${ex.image}" alt="${ex.name}" class="coin-icon">` : '';
      const score = ex.trust_score !== null ? `<span class="badge badge-trust score-${ex.trust_score}">${ex.trust_score}/10</span>` : '-';
      const volBtc = ex.trade_volume_24h_btc ? `${ex.trade_volume_24h_btc.toLocaleString(undefined, {maximumFractionDigits: 0})} BTC` : '-';
      const volUsd = ex.trade_volume_24h_usd ? formatCompactNumber(ex.trade_volume_24h_usd) : '-';

      return `
        <tr>
          <td class="text-muted">#${ex.trust_score_rank || idx + 1}</td>
          <td>
            <a href="exchange.html?id=${ex.id}" class="coin-name-cell">
              ${img}
              <strong>${escapeHtml(ex.name)}</strong>
            </a>
          </td>
          <td>${score}</td>
          <td>${volBtc}</td>
          <td><strong>${volUsd}</strong></td>
          <td>${ex.year_established || 'N/A'}</td>
          <td>${ex.country ? escapeHtml(ex.country) : 'Global'}</td>
          <td class="text-right">
            <a href="exchange.html?id=${ex.id}" class="btn btn-sm btn-outline">Details</a>
          </td>
        </tr>
      `;
    }).join('');

  } catch (err) {
    if (errorBanner) {
      errorBanner.classList.remove('hidden');
      document.getElementById('exchanges-error-msg').textContent = err.message;
    }
    tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Failed to load exchanges.</td></tr>`;
  }
}

async function loadExchangeDetail() {
  const urlParams = new URLSearchParams(window.location.search);
  const exchangeId = urlParams.get('id') || 'binance';

  try {
    const data = await fetchExchangeDetail(exchangeId);
    const ex = data.data;

    document.title = `${ex.name} Exchange Details & Volume | CoinPulse`;
    if (document.getElementById('exchange-name')) document.getElementById('exchange-name').textContent = ex.name;
    if (document.getElementById('exchange-logo') && ex.image) document.getElementById('exchange-logo').src = ex.image;
    if (document.getElementById('exchange-trust-rank')) document.getElementById('exchange-trust-rank').textContent = `Rank #${ex.trust_score_rank || 1}`;
    if (document.getElementById('exchange-country')) document.getElementById('exchange-country').textContent = `Country: ${ex.country || 'Global'}`;
    if (document.getElementById('exchange-year')) document.getElementById('exchange-year').textContent = `Est. ${ex.year_established || 'N/A'}`;
    if (document.getElementById('exchange-trust-score')) document.getElementById('exchange-trust-score').textContent = `${ex.trust_score || 10} / 10`;
    if (document.getElementById('exchange-vol-btc')) document.getElementById('exchange-vol-btc').textContent = `${(ex.trade_volume_24h_btc || 0).toLocaleString(undefined, {maximumFractionDigits: 0})} BTC`;
    if (document.getElementById('exchange-vol-usd')) document.getElementById('exchange-vol-usd').textContent = formatCurrency(ex.trade_volume_24h_usd || 0);
    if (document.getElementById('exchange-url') && ex.url) {
      document.getElementById('exchange-url').href = ex.url;
    }

    const tbody = document.getElementById('tickers-tbody');
    if (tbody && ex.tickers) {
      if (!ex.tickers.length) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center">No active trading tickers reported.</td></tr>`;
        return;
      }
      tbody.innerHTML = ex.tickers.map((t, idx) => `
        <tr>
          <td class="text-muted">#${idx + 1}</td>
          <td><strong>${escapeHtml(t.base)}/${escapeHtml(t.target)}</strong></td>
          <td>${escapeHtml(t.market_name)}</td>
          <td>${t.last_price ? formatCurrency(t.last_price) : '-'}</td>
          <td>${t.converted_volume_usd ? formatCurrency(t.converted_volume_usd) : '-'}</td>
          <td class="text-right">
            ${t.trade_url ? `<a href="${t.trade_url}" target="_blank" rel="noopener" class="btn btn-sm btn-outline">Trade <i class="fas fa-external-link-alt"></i></a>` : '-'}
          </td>
        </tr>
      `).join('');
    }

  } catch (err) {
    const banner = document.getElementById('exchange-error');
    if (banner) {
      banner.classList.remove('hidden');
      document.getElementById('exchange-error-msg').textContent = err.message;
    }
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
