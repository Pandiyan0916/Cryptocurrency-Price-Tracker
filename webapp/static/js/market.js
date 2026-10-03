/**
 * market.js - Live Scraped Cryptocurrency Market Dashboard.
 * Powered by Selenium Web Scraping + FastAPI Backend.
 */

import { fetchGlobalStats, fetchMarkets, fetchTrending } from './api.js';
import { formatCurrency, formatCompactNumber, formatPercentage, getCoinLogoUrl } from './format.js';
import { initTheme } from './theme.js';
import { initGlobalSearch } from './search.js';
import { initAuth, getStoredUser, openAuthModal, showToast } from './auth.js';
import { initCurrencySelector } from './currency.js';

const WATCHLIST_KEY = 'coinpulse_watchlist';

let currentPage = 1;
let perPage = 50;
let currentTab = 'all';
let searchQuery = '';
let currentSortKey = 'market_cap_rank';
let currentSortAsc = true;
let searchDebounceTimer = null;
let autoRefreshTimer = null;
let latestMarketResponse = null;

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initGlobalSearch();
  initAuth();
  initCurrencySelector();
  loadGlobalHeader();
  loadMarketsData(false);
  setupEventListeners();
  setupAutoRefresh(30);

  window.addEventListener('currencyChanged', () => {
    loadGlobalHeader();
    renderTableData();
    if (latestMarketResponse && latestMarketResponse.data) {
      renderOverviewMovers(latestMarketResponse.data);
    }
  });
});

function getWatchlist() {
  try {
    return JSON.parse(localStorage.getItem(WATCHLIST_KEY) || '[]');
  } catch (e) {
    return [];
  }
}

function toggleWatchlist(coinId) {
  let list = getWatchlist();
  if (list.includes(coinId)) {
    list = list.filter(id => id !== coinId);
  } else {
    list.push(coinId);
  }
  localStorage.setItem(WATCHLIST_KEY, JSON.stringify(list));
  renderTableData();
}

async function loadGlobalHeader() {
  try {
    const res = await fetchGlobalStats();
    const data = res.data;
    if (document.getElementById('global-cryptos')) {
      document.getElementById('global-cryptos').textContent = data.active_cryptocurrencies ? data.active_cryptocurrencies.toLocaleString() : '50';
    }
    if (document.getElementById('global-mcap')) {
      document.getElementById('global-mcap').textContent = formatCompactNumber(data.total_market_cap_usd || 0);
    }
    if (document.getElementById('global-vol')) {
      document.getElementById('global-vol').textContent = formatCompactNumber(data.total_volume_usd || 0);
    }
    if (document.getElementById('global-btc-dom')) {
      document.getElementById('global-btc-dom').textContent = (data.btc_dominance || 54.2).toFixed(1);
    }
    if (document.getElementById('global-eth-dom')) {
      document.getElementById('global-eth-dom').textContent = (data.eth_dominance || 14.5).toFixed(1);
    }

    const badge = document.getElementById('data-source-badge');
    if (badge) {
      badge.innerHTML = `<i class="fas fa-broadcast-tower"></i> Source: ${(res.source || 'web_scrape').toUpperCase()}`;
      badge.className = 'data-source-badge';
    }
  } catch (err) {
    console.warn('Global header load fallback warning:', err);
  }
}

async function loadMarketsData(forceRefresh = false) {
  const tbody = document.getElementById('market-tbody');
  const errorBanner = document.getElementById('market-error-banner');
  const freshnessEl = document.getElementById('data-freshness-status');
  if (!tbody) return;

  try {
    if (errorBanner) errorBanner.classList.add('hidden');

    const res = await fetchMarkets(currentPage, perPage, 'market_cap_desc', searchQuery, '', forceRefresh);
    latestMarketResponse = res;

    // Update freshness indicator
    if (freshnessEl) {
      const age = res.data_age_seconds !== undefined ? res.data_age_seconds : 0;
      freshnessEl.innerHTML = `<span class="text-success font-semibold">LIVE • Scraped ${age}s ago</span> (${res.as_of || 'Just now'})`;
    }

    renderTableData();
    renderOverviewMovers(res.data);

    // Update pagination controls
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    const pageInfo = document.getElementById('page-info');

    if (prevBtn && nextBtn && pageInfo) {
      prevBtn.disabled = currentPage <= 1;
      nextBtn.disabled = !res.data || res.data.length < perPage;
      pageInfo.textContent = `Page ${currentPage}`;
    }
  } catch (err) {
    if (errorBanner) {
      errorBanner.classList.remove('hidden');
      document.getElementById('market-error-msg').textContent = `LIVE DATA TEMPORARILY UNAVAILABLE. ${err.message || 'Scraper is running...'}`;
    }
    tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">Scraper is initializing live market data. <button class="btn btn-sm btn-primary margin-left-xs" onclick="window.location.reload()">Retry Now</button></td></tr>`;
  }
}

function renderOverviewMovers(coins) {
  if (!coins || !coins.length) return;

  // Trending
  const trendingContainer = document.getElementById('mover-trending-list');
  if (trendingContainer) {
    trendingContainer.innerHTML = coins.slice(0, 2).map(c => `
      <a href="coin.html?id=${c.id}" class="mover-item">
        <div class="mover-info">
          <img src="${getCoinLogoUrl(c)}" class="mover-thumb" alt="${c.name}">
          <span class="mover-name">${escapeHtml(c.name)}</span>
          <span class="mover-symbol">${escapeHtml(c.symbol.toUpperCase())}</span>
        </div>
        <div class="mover-stats text-right">
          <span class="font-semibold">${formatCurrency(c.current_price)}</span>
        </div>
      </a>
    `).join('');
  }

  // Top Gainer
  const gainersContainer = document.getElementById('mover-gainers-list');
  const validGainers = coins.filter(c => (c.price_change_percentage_24h_in_currency || 0) > 0)
                            .sort((a, b) => (b.price_change_percentage_24h_in_currency || 0) - (a.price_change_percentage_24h_in_currency || 0));
  if (gainersContainer && validGainers.length) {
    const topG = validGainers[0];
    gainersContainer.innerHTML = `
      <a href="coin.html?id=${topG.id}" class="mover-item">
        <div class="mover-info">
          <img src="${getCoinLogoUrl(topG)}" class="mover-thumb" alt="${topG.name}">
          <span class="mover-name">${escapeHtml(topG.name)}</span>
          <span class="mover-symbol">${escapeHtml(topG.symbol.toUpperCase())}</span>
        </div>
        <div class="mover-stats text-right">
          <span class="font-semibold">${formatCurrency(topG.current_price)}</span>
          <span class="text-success font-xs font-semibold">${formatPercentage(topG.price_change_percentage_24h_in_currency)}</span>
        </div>
      </a>
    `;
  }

  // Top Loser
  const losersContainer = document.getElementById('mover-losers-list');
  const validLosers = coins.filter(c => (c.price_change_percentage_24h_in_currency || 0) < 0)
                           .sort((a, b) => (a.price_change_percentage_24h_in_currency || 0) - (b.price_change_percentage_24h_in_currency || 0));
  if (losersContainer && validLosers.length) {
    const topL = validLosers[0];
    losersContainer.innerHTML = `
      <a href="coin.html?id=${topL.id}" class="mover-item">
        <div class="mover-info">
          <img src="${getCoinLogoUrl(topL)}" class="mover-thumb" alt="${topL.name}">
          <span class="mover-name">${escapeHtml(topL.name)}</span>
          <span class="mover-symbol">${escapeHtml(topL.symbol.toUpperCase())}</span>
        </div>
        <div class="mover-stats text-right">
          <span class="font-semibold">${formatCurrency(topL.current_price)}</span>
          <span class="text-danger font-xs font-semibold">${formatPercentage(topL.price_change_percentage_24h_in_currency)}</span>
        </div>
      </a>
    `;
  }
}

function renderTableData() {
  if (!latestMarketResponse || !latestMarketResponse.data) return;

  const tbody = document.getElementById('market-tbody');
  if (!tbody) return;

  let list = [...latestMarketResponse.data];
  const watchlist = getWatchlist();

  // Apply Tab Filters
  if (currentTab === 'gainers') {
    list = list.filter(c => (c.price_change_percentage_24h_in_currency || 0) > 0)
               .sort((a, b) => (b.price_change_percentage_24h_in_currency || 0) - (a.price_change_percentage_24h_in_currency || 0));
  } else if (currentTab === 'losers') {
    list = list.filter(c => (c.price_change_percentage_24h_in_currency || 0) < 0)
               .sort((a, b) => (a.price_change_percentage_24h_in_currency || 0) - (b.price_change_percentage_24h_in_currency || 0));
  }

  // Apply Search Filter
  if (searchQuery) {
    const qLower = searchQuery.toLowerCase();
    list = list.filter(c => c.name.toLowerCase().includes(qLower) || c.symbol.toLowerCase().includes(qLower));
  }

  // Apply Column Sorting
  list.sort((a, b) => {
    let valA = a[currentSortKey];
    let valB = b[currentSortKey];
    if (valA === null || valA === undefined) valA = -Infinity;
    if (valB === null || valB === undefined) valB = -Infinity;
    if (typeof valA === 'string') {
      return currentSortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }
    return currentSortAsc ? valA - valB : valB - valA;
  });

  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">No cryptocurrencies found matching your criteria.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(c => {
    const isStarred = watchlist.includes(c.id);
    const starClass = isStarred ? 'fav-star active' : 'fav-star';

    const chg24h = c.price_change_percentage_24h_in_currency || 0.0;
    const class24h = chg24h >= 0 ? 'text-success font-semibold' : 'text-danger font-semibold';

    const sparkPrices = c.sparkline_in_7d ? c.sparkline_in_7d.price : [];
    const sparkSvg = generateSparklineSVG(sparkPrices, chg24h >= 0);

    return `
      <tr>
        <td class="th-fav text-center">
          <i class="fas fa-star ${starClass}" data-id="${c.id}"></i>
        </td>
        <td class="text-muted font-xs text-left">#${c.market_cap_rank || '—'}</td>
        <td class="text-left">
          <a href="coin.html?id=${encodeURIComponent(c.id)}" class="coin-name-cell">
            <img src="${getCoinLogoUrl(c)}" alt="${c.name}" class="coin-icon">
            <span class="coin-name font-semibold">${escapeHtml(c.name)}</span>
            <span class="coin-symbol text-muted margin-left-xs">${escapeHtml(c.symbol.toUpperCase())}</span>
          </a>
        </td>
        <td class="text-right font-semibold">${formatCurrency(c.current_price)}</td>
        <td class="text-right ${class24h}">${formatPercentage(chg24h)}</td>
        <td class="text-right font-semibold">${formatCompactNumber(c.market_cap)}</td>
        <td class="text-right">${formatCompactNumber(c.total_volume)}</td>
        <td class="text-right">${sparkSvg}</td>
      </tr>
    `;
  }).join('');

  // Attach favorite star click listeners
  tbody.querySelectorAll('.fav-star').forEach(star => {
    star.addEventListener('click', (e) => {
      e.preventDefault();
      const id = star.getAttribute('data-id');
      if (id) toggleWatchlist(id);
    });
  });
}

function generateSparklineSVG(prices, isPositive) {
  if (!prices || prices.length < 2) return '<span class="text-muted">—</span>';
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const width = 100;
  const height = 28;

  const points = prices.map((val, idx) => {
    const x = (idx / (prices.length - 1)) * width;
    const y = height - ((val - min) / range) * (height - 6) - 3;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');

  const strokeColor = isPositive ? '#16c784' : '#ea3943';
  return `
    <svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
      <polyline fill="none" stroke="${strokeColor}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" points="${points}" />
    </svg>
  `;
}

function setupEventListeners() {
  // Sub-nav pill buttons
  document.querySelectorAll('.sub-nav-pill').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const filter = btn.getAttribute('data-filter');
      if (filter) {
        e.preventDefault();
        document.querySelectorAll('.sub-nav-pill').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentTab = filter;
        currentPage = 1;
        loadMarketsData(false);
      }
    });
  });

  // Table Filter Input
  const filterInput = document.getElementById('table-filter-input');
  if (filterInput) {
    filterInput.addEventListener('input', (e) => {
      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(() => {
        searchQuery = e.target.value.trim();
        renderTableData();
      }, 200);
    });
  }

  // Export Top 50 Markets CSV
  const exportMarketsBtn = document.getElementById('btn-export-markets-csv');
  if (exportMarketsBtn) {
    exportMarketsBtn.addEventListener('click', downloadTop50MarketsCSV);
  }

  // Manual Refresh Button
  const refreshBtn = document.getElementById('manual-refresh-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', async () => {
      const icon = refreshBtn.querySelector('i');
      if (icon) icon.classList.add('fa-spin');
      refreshBtn.disabled = true;
      showToast('Refreshing live market data...', 'info');

      try {
        await loadGlobalHeader();
        await loadMarketsData(true);
        showToast('Live market data refreshed successfully!', 'success');
      } catch (err) {
        showToast('Failed to refresh market data.', 'error');
      } finally {
        if (icon) icon.classList.remove('fa-spin');
        refreshBtn.disabled = false;
      }
    });
  }

  // Per Page Selector
  const perPageSelect = document.getElementById('per-page-select');
  if (perPageSelect) {
    perPageSelect.addEventListener('change', (e) => {
      perPage = parseInt(e.target.value, 10);
      currentPage = 1;
      loadMarketsData(false);
    });
  }

  // Auto Refresh Interval
  const autoRefreshSelect = document.getElementById('auto-refresh-select');
  if (autoRefreshSelect) {
    autoRefreshSelect.addEventListener('change', (e) => {
      const sec = parseInt(e.target.value, 10);
      setupAutoRefresh(sec);
    });
  }

  // Pagination Controls
  const prevBtn = document.getElementById('prev-page-btn');
  const nextBtn = document.getElementById('next-page-btn');
  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage--;
        loadMarketsData(false);
      }
    });
  }
  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      currentPage++;
      loadMarketsData(false);
    });
  }

  // Retry Button
  const retryBtn = document.getElementById('market-retry-btn');
  if (retryBtn) {
    retryBtn.addEventListener('click', () => {
      loadGlobalHeader();
      loadMarketsData(true);
    });
  }

  // Table Column Sort Headers
  document.querySelectorAll('.market-table th.sortable').forEach(th => {
    th.addEventListener('click', () => {
      const sortKey = th.getAttribute('data-sort');
      if (currentSortKey === sortKey) {
        currentSortAsc = !currentSortAsc;
      } else {
        currentSortKey = sortKey;
        currentSortAsc = true;
      }
      renderTableData();
    });
  });
}

function downloadTop50MarketsCSV() {
  const user = getStoredUser();
  if (!user) {
    showToast('Please sign in or create an account to export top 50 crypto CSV data.', 'info');
    openAuthModal('login');
    return;
  }

  if (!latestMarketResponse || !latestMarketResponse.data || !latestMarketResponse.data.length) {
    showToast('Live market data is currently loading. Please retry in a moment.', 'info');
    return;
  }

  const coins = latestMarketResponse.data.slice(0, 50);
  const nowStr = new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  const headers = ['Rank', 'Name', 'Symbol', 'Price (USD)', '24h Change %', 'Market Cap (USD)', '24h Volume (USD)', 'Downloaded At'];
  
  const rows = coins.map((c, idx) => [
    c.market_cap_rank || (idx + 1),
    `"${(c.name || '').replace(/"/g, '""')}"`,
    c.symbol ? c.symbol.toUpperCase() : '',
    c.current_price || 0,
    c.price_change_percentage_24h_in_currency !== undefined ? c.price_change_percentage_24h_in_currency : 0,
    c.market_cap || 0,
    c.total_volume || 0,
    `"${nowStr}"`
  ]);

  const csvString = `# Top 50 Cryptocurrency Markets Live Export\n# Downloaded At: ${nowStr}\n\n` + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `top_50_crypto_markets_${new Date().toISOString().slice(0, 10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);

  showToast('Top 50 live market CSV exported successfully!', 'success');
}

function setupAutoRefresh(seconds) {
  clearInterval(autoRefreshTimer);
  if (seconds > 0) {
    autoRefreshTimer = setInterval(() => {
      loadGlobalHeader();
      loadMarketsData(false);
    }, seconds * 1000);
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
