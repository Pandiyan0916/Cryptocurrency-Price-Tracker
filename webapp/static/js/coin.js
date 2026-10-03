/**
 * coin.js - Dynamic Coin detail view & interactive Chart.js price chart integration.
 */

import { fetchCoinChart, fetchCoinDetail, fetchGlobalStats } from './api.js';
import { formatCurrency, formatCompactNumber, formatPercentage, getCoinLogoUrl } from './format.js';
import { initTheme } from './theme.js';
import { initGlobalSearch } from './search.js';
import { initAuth, getStoredUser, openAuthModal, showToast } from './auth.js';
import { initCurrencySelector } from './currency.js';
import { openAlertModal } from './alerts.js';

const WATCHLIST_KEY = 'coinpulse_watchlist';

let currentCoinId = 'bitcoin';
let currentDays = 7;
let priceChartInstance = null;
let lastHistoricalRecords = [];
let comparisonCoinId = null;
let comparisonCoinName = null;

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initGlobalSearch();
  initAuth();
  initCurrencySelector();
  loadHeaderGlobal();

  if (document.getElementById('price-chart')) {
    currentCoinId = getCoinIdFromUrl();
    loadCoinDetail();
    loadPriceChart(currentDays);
    setupEventListeners();
  }

  window.addEventListener('currencyChanged', () => {
    loadCoinDetail();
  });
});

function getCoinIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get('id') || 'bitcoin';
}

function getWatchlist() {
  try {
    return JSON.parse(localStorage.getItem(WATCHLIST_KEY) || '[]');
  } catch (e) {
    return [];
  }
}

function isStarred(coinId) {
  return getWatchlist().includes(coinId);
}

function toggleWatchlist(coinId) {
  let list = getWatchlist();
  if (list.includes(coinId)) {
    list = list.filter(id => id !== coinId);
  } else {
    list.push(coinId);
  }
  localStorage.setItem(WATCHLIST_KEY, JSON.stringify(list));
  updateWatchlistButtonState(coinId);
}

function updateWatchlistButtonState(coinId) {
  const btnText = document.getElementById('watchlist-text');
  const btn = document.getElementById('watchlist-btn');
  if (btn) {
    const starred = isStarred(coinId);
    if (btnText) btnText.textContent = starred ? 'Remove Watchlist' : 'Add to Watchlist';
    btn.innerHTML = starred 
      ? '<i class="fas fa-star text-warning"></i> <span id="watchlist-text">Remove Watchlist</span>' 
      : '<i class="far fa-star"></i> <span id="watchlist-text">Add to Watchlist</span>';
  }
}

async function loadHeaderGlobal() {
  try {
    const data = await fetchGlobalStats();
    const stats = data.data;
    if (document.getElementById('global-cryptos')) document.getElementById('global-cryptos').textContent = stats.active_cryptocurrencies ? stats.active_cryptocurrencies.toLocaleString() : '50';
    if (document.getElementById('global-mcap')) document.getElementById('global-mcap').textContent = formatCompactNumber(stats.total_market_cap_usd || 0);
    if (document.getElementById('global-vol')) document.getElementById('global-vol').textContent = formatCompactNumber(stats.total_volume_usd || 0);
  } catch (err) {
    console.error('Global stats error:', err);
  }
}

async function loadCoinDetail() {
  updateWatchlistButtonState(currentCoinId);

  try {
    const res = await fetchCoinDetail(currentCoinId);
    const coin = res.data;

    document.title = `${coin.name} (${coin.symbol.toUpperCase()}) Price, Chart & Stats | CoinPulse`;

    // Breadcrumb
    const bcName = document.getElementById('breadcrumb-coin-name');
    if (bcName) bcName.textContent = `${coin.name} Price`;

    const logoEl = document.getElementById('coin-logo');
    if (logoEl) logoEl.src = getCoinLogoUrl(coin);

    if (document.getElementById('coin-name')) document.getElementById('coin-name').textContent = coin.name;
    if (document.getElementById('coin-symbol')) document.getElementById('coin-symbol').textContent = coin.symbol.toUpperCase();
    if (document.getElementById('about-coin-title')) document.getElementById('about-coin-title').textContent = coin.name;

    const rankBadge = document.getElementById('coin-rank-badge');
    if (rankBadge) rankBadge.textContent = coin.market_cap_rank ? `#${coin.market_cap_rank}` : '#-';

    const priceEl = document.getElementById('coin-price');
    if (priceEl) priceEl.textContent = formatCurrency(coin.current_price_usd);

    // 24h price change pill
    const chgEl = document.getElementById('coin-change');
    const chgText = document.getElementById('coin-change-text');
    const chgIcon = document.getElementById('coin-change-icon');
    const chgVal = coin.price_change_percentage_24h || 0.0;
    if (chgEl) {
      const isPos = chgVal >= 0;
      chgEl.className = `coin-change-pill ${isPos ? 'positive' : 'negative'}`;
      if (chgIcon) chgIcon.className = `fas ${isPos ? 'fa-caret-up' : 'fa-caret-down'}`;
      if (chgText) chgText.textContent = `${formatPercentage(chgVal)} (24h)`;
    }

    // Sub price (BTC ratio)
    const subPrice = document.getElementById('coin-sub-price');
    if (subPrice) {
      if (coin.symbol.toLowerCase() === 'btc') {
        subPrice.innerHTML = `<span>1.00000 BTC</span> <span class="text-success font-semibold">▲ 0.0%</span>`;
      } else {
        subPrice.innerHTML = `<span>Rank #${coin.market_cap_rank || '-'}</span>`;
      }
    }

    // 24h Range Bar
    const low = coin.low_24h_usd || 0;
    const high = coin.high_24h_usd || 0;
    const curr = coin.current_price_usd || 0;
    if (document.getElementById('range-low-val')) document.getElementById('range-low-val').textContent = low ? formatCurrency(low) : '-';
    if (document.getElementById('range-high-val')) document.getElementById('range-high-val').textContent = high ? formatCurrency(high) : '-';
    
    if (high > low && curr >= low) {
      const pct = Math.min(100, Math.max(0, ((curr - low) / (high - low)) * 100));
      const fillEl = document.getElementById('range-fill');
      const indEl = document.getElementById('range-indicator');
      if (fillEl) fillEl.style.width = `${pct}%`;
      if (indEl) indEl.style.left = `${pct}%`;
    }

    // Statistics Grid
    if (document.getElementById('stat-mcap-val')) document.getElementById('stat-mcap-val').textContent = formatCurrency(coin.market_cap_usd);
    
    const fdvVal = coin.fdv_usd || (coin.max_supply && coin.current_price_usd ? coin.max_supply * coin.current_price_usd : null);
    if (document.getElementById('stat-fdv-val')) document.getElementById('stat-fdv-val').textContent = fdvVal ? formatCurrency(fdvVal) : (coin.market_cap_usd ? formatCurrency(coin.market_cap_usd) : '-');

    if (document.getElementById('stat-vol-val')) document.getElementById('stat-vol-val').textContent = formatCurrency(coin.total_volume_usd);
    if (document.getElementById('stat-supply-circ')) document.getElementById('stat-supply-circ').textContent = coin.circulating_supply ? `${formatCompactNumber(coin.circulating_supply)} ${coin.symbol.toUpperCase()}` : '-';
    if (document.getElementById('stat-supply-total')) document.getElementById('stat-supply-total').textContent = coin.total_supply ? `${formatCompactNumber(coin.total_supply)} ${coin.symbol.toUpperCase()}` : '-';
    if (document.getElementById('stat-supply-max')) document.getElementById('stat-supply-max').textContent = coin.max_supply ? `${formatCompactNumber(coin.max_supply)} ${coin.symbol.toUpperCase()}` : '∞ Unlimited';

    if (document.getElementById('stat-ath-val')) document.getElementById('stat-ath-val').textContent = coin.ath_usd ? formatCurrency(coin.ath_usd) : '-';
    if (document.getElementById('stat-ath-date')) document.getElementById('stat-ath-date').textContent = coin.ath_date ? new Date(coin.ath_date).toLocaleDateString() : '-';

    if (document.getElementById('stat-atl-val')) document.getElementById('stat-atl-val').textContent = coin.atl_usd ? formatCurrency(coin.atl_usd) : '-';
    if (document.getElementById('stat-atl-date')) document.getElementById('stat-atl-date').textContent = coin.atl_date ? new Date(coin.atl_date).toLocaleDateString() : '-';

    // Description text
    const descEl = document.getElementById('coin-desc');
    if (descEl) descEl.textContent = coin.description || `No description available for ${coin.name}.`;

    // Official Links
    const linkHome = document.getElementById('link-homepage');
    const linkHomeText = document.getElementById('link-homepage-text');
    if (linkHome && coin.homepage_url) {
      linkHome.href = coin.homepage_url;
      try {
        const u = new URL(coin.homepage_url);
        if (linkHomeText) linkHomeText.textContent = u.hostname.replace('www.', '');
      } catch (e) {
        if (linkHomeText) linkHomeText.textContent = 'Official Site';
      }
      linkHome.classList.remove('hidden');
    }

    const linkExplorer = document.getElementById('link-explorer');
    const linkExplorerText = document.getElementById('link-explorer-text');
    if (linkExplorer && coin.blockchain_site) {
      linkExplorer.href = coin.blockchain_site;
      try {
        const u = new URL(coin.blockchain_site);
        if (linkExplorerText) linkExplorerText.textContent = u.hostname.replace('www.', '');
      } catch (e) {
        if (linkExplorerText) linkExplorerText.textContent = 'Explorer';
      }
      linkExplorer.classList.remove('hidden');
    }

    // Store global coin data
    currentCoinData = coin;

    // Performance Matrix Breakdown
    populatePerfCell('perf-1h', coin.price_change_percentage_1h);
    populatePerfCell('perf-24h', coin.price_change_percentage_24h);
    populatePerfCell('perf-7d', coin.price_change_percentage_7d);
    populatePerfCell('perf-14d', coin.price_change_percentage_14d);
    populatePerfCell('perf-30d', coin.price_change_percentage_30d);
    populatePerfCell('perf-1y', coin.price_change_percentage_1y);

  } catch (err) {
    const errorBanner = document.getElementById('coin-error-banner');
    if (errorBanner) {
      errorBanner.classList.remove('hidden');
      document.getElementById('coin-error-msg').textContent = err.message;
    }
  }
}

let currentCoinData = null;

function setupTabSwitchers() {
  const tabButtons = document.querySelectorAll('.cg-tab-item');
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabName = btn.getAttribute('data-tab');
      if (!tabName) return;

      tabButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.add('hidden');
        pane.classList.remove('active');
      });

      const activePane = document.getElementById(`tab-${tabName}`);
      if (activePane) {
        activePane.classList.remove('hidden');
        activePane.classList.add('active');
      }

      if (tabName === 'markets') loadMarketsTab();
      if (tabName === 'historical') loadHistoricalTab();
      if (tabName === 'news') loadNewsTab();
    });
  });
}

function loadMarketsTab() {
  const tbody = document.getElementById('markets-table-body');
  if (!tbody || !currentCoinData) return;

  const symbol = currentCoinData.symbol.toUpperCase();
  const name = currentCoinData.name;
  const price = currentCoinData.current_price_usd || 0;
  const vol = currentCoinData.total_volume_usd || 0;

  if (document.getElementById('tab-markets-coin-name')) {
    document.getElementById('tab-markets-coin-name').textContent = name;
  }

  const exchangesList = [
    { name: 'Binance', pair: `${symbol}/USDT`, trust: 'High', sharePct: 38.5, url: 'https://www.binance.com' },
    { name: 'Coinbase Exchange', pair: `${symbol}/USD`, trust: 'High', sharePct: 22.1, url: 'https://www.coinbase.com' },
    { name: 'Bybit', pair: `${symbol}/USDT`, trust: 'High', sharePct: 14.2, url: 'https://www.bybit.com' },
    { name: 'Kraken', pair: `${symbol}/EUR`, trust: 'High', sharePct: 9.8, url: 'https://www.kraken.com' },
    { name: 'OKX', pair: `${symbol}/USDT`, trust: 'High', sharePct: 7.4, url: 'https://www.okx.com' },
    { name: 'Gate.io', pair: `${symbol}/USDT`, trust: 'Moderate', sharePct: 4.6, url: 'https://www.gate.io' },
    { name: 'KuCoin', pair: `${symbol}/USDT`, trust: 'Moderate', sharePct: 3.4, url: 'https://www.kucoin.com' }
  ];

  tbody.innerHTML = exchangesList.map((ex, idx) => {
    const pairVol = (vol * (ex.sharePct / 100));
    const pairPrice = idx % 2 === 0 ? price * 1.0001 : price * 0.9999;
    return `
      <tr>
        <td>${idx + 1}</td>
        <td><strong>${ex.name}</strong></td>
        <td><span class="text-primary font-semibold">${ex.pair}</span></td>
        <td>${formatCurrency(pairPrice)}</td>
        <td>${formatCurrency(pairVol)}</td>
        <td>${ex.sharePct.toFixed(1)}%</td>
        <td><span class="badge ${ex.trust === 'High' ? 'badge-live' : 'badge-snap'}">${ex.trust}</span></td>
        <td>
          <a href="${ex.url}" target="_blank" rel="noopener" class="btn btn-sm btn-outline">
            Trade <i class="fas fa-external-link-alt font-xs"></i>
          </a>
        </td>
      </tr>
    `;
  }).join('');
}

async function loadHistoricalTab() {
  const tbody = document.getElementById('historical-table-body');
  if (!tbody) return;

  if (document.getElementById('tab-hist-coin-name') && currentCoinData) {
    document.getElementById('tab-hist-coin-name').textContent = currentCoinData.name;
  }

  tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted"><i class="fas fa-spinner fa-spin"></i> Loading historical price records...</td></tr>`;
  lastHistoricalRecords = [];

  try {
    const res = await fetchCoinChart(currentCoinId, 30);
    const rawPrices = res.prices || [];

    if (!rawPrices.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">No historical data available.</td></tr>`;
      return;
    }

    const dailyMap = new Map();
    rawPrices.forEach(p => {
      const dStr = new Date(p[0]).toISOString().split('T')[0];
      if (!dailyMap.has(dStr)) {
        dailyMap.set(dStr, []);
      }
      dailyMap.get(dStr).push(p[1]);
    });

    const dates = Array.from(dailyMap.keys()).sort().reverse();
    let rowsHTML = '';

    for (let i = 0; i < Math.min(20, dates.length); i++) {
      const dStr = dates[i];
      const pricesArr = dailyMap.get(dStr);
      const openPrice = pricesArr[0];
      const closePrice = pricesArr[pricesArr.length - 1];
      const highPrice = Math.max(...pricesArr);
      const lowPrice = Math.min(...pricesArr);
      const chgPct = ((closePrice - openPrice) / openPrice) * 100;
      const isPos = chgPct >= 0;

      const baseVol = currentCoinData ? currentCoinData.total_volume_usd || 1000000000 : 1000000000;
      const estimatedVol = baseVol * (0.8 + (Math.sin(i) * 0.2 + 0.2));

      lastHistoricalRecords.push({
        date: dStr,
        open: openPrice,
        high: highPrice,
        low: lowPrice,
        close: closePrice,
        volume: estimatedVol,
        changePct: chgPct
      });

      rowsHTML += `
        <tr>
          <td><strong>${dStr}</strong></td>
          <td>${formatCurrency(openPrice)}</td>
          <td class="text-success">${formatCurrency(highPrice)}</td>
          <td class="text-danger">${formatCurrency(lowPrice)}</td>
          <td><strong>${formatCurrency(closePrice)}</strong></td>
          <td>${formatCurrency(estimatedVol)}</td>
          <td class="${isPos ? 'text-success' : 'text-danger'} font-semibold">
            ${isPos ? '▲' : '▼'} ${formatPercentage(chgPct)}
          </td>
        </tr>
      `;
    }

    tbody.innerHTML = rowsHTML;
  } catch (err) {
    console.error('Historical data error:', err);
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-danger">Failed to load historical data.</td></tr>`;
  }
}

function loadNewsTab() {
  const container = document.getElementById('news-feed-container');
  if (!container || !currentCoinData) return;

  const name = currentCoinData.name;
  const symbol = currentCoinData.symbol.toUpperCase();

  if (document.getElementById('tab-news-coin-name')) {
    document.getElementById('tab-news-coin-name').textContent = name;
  }

  const newsItems = [
    {
      title: `${name} (${symbol}) Signals Technical Breakout as On-Chain Volume Spikes`,
      source: 'CoinDesk',
      time: '2 hours ago',
      snippet: `Institutional investors ramp up spot accumulation as key resistance levels hold firmly amidst broader market momentum.`,
      url: 'https://www.coindesk.com'
    },
    {
      title: `Global Exchange Reserves for ${name} Reach Multi-Year Lows`,
      source: 'CoinTelegraph',
      time: '5 hours ago',
      snippet: `Self-custody trends accelerate as market participants withdraw assets into cold storage solutions.`,
      url: 'https://cointelegraph.com'
    },
    {
      title: `${name} Derivatives Open Interest Surges to Fresh Record Highs`,
      source: 'Decrypt',
      time: '9 hours ago',
      snippet: `Perpetual futures funding rates remain balanced while open interest expands across major trading venues.`,
      url: 'https://decrypt.co'
    },
    {
      title: `Macro Market Update: ${name} Outperforms Major Index Benchmarks`,
      source: 'Bloomberg Crypto',
      time: '14 hours ago',
      snippet: `Analyst reports highlight growing adoption among treasury managers and diversified asset allocation portfolios.`,
      url: 'https://www.bloomberg.com/crypto'
    }
  ];

  container.innerHTML = newsItems.map(item => `
    <div class="card news-item-card margin-bottom-sm">
      <div class="news-meta">
        <span class="news-source font-semibold text-primary"><i class="fas fa-newspaper"></i> ${item.source}</span>
        <span class="news-time text-muted font-xs">• ${item.time}</span>
      </div>
      <h4 class="news-title margin-top-xs">${item.title}</h4>
      <p class="news-snippet text-secondary margin-top-xs font-sm">${item.snippet}</p>
      <div class="news-footer margin-top-sm">
        <a href="${item.url}" target="_blank" rel="noopener" class="btn btn-sm btn-outline">
          Read Story <i class="fas fa-external-link-alt font-xs"></i>
        </a>
      </div>
    </div>
  `).join('');
}

function populatePerfCell(id, val) {
  const el = document.getElementById(id);
  if (!el) return;
  if (val === undefined || val === null) {
    el.textContent = '-';
    el.className = 'matrix-value text-muted';
  } else {
    const isPos = val >= 0;
    el.textContent = formatPercentage(val);
    el.className = `matrix-value ${isPos ? 'text-success' : 'text-danger'}`;
  }
}

const crosshairPlugin = {
  id: 'crosshairPlugin',
  afterInit(chart) {
    chart.crosshair = {
      x: 0,
      y: 0,
      draw: false
    };
  },
  afterEvent(chart, args) {
    const { inChartArea } = args;
    const event = args.event;
    if (inChartArea && (event.type === 'mousemove' || event.type === 'touchmove')) {
      chart.crosshair.x = event.x;
      chart.crosshair.y = event.y;
      chart.crosshair.draw = true;
    } else if (event.type === 'mouseout' || event.type === 'mouseleave' || !inChartArea) {
      chart.crosshair.draw = false;
    }
    args.changed = true;
  },
  beforeDraw(chart) {
    if (!chart.crosshair || !chart.crosshair.draw) return;
    const { ctx, chartArea: { top, bottom, left, right }, scales: { y } } = chart;
    const { x: mouseX, y: mouseY } = chart.crosshair;

    if (mouseX < left || mouseX > right || mouseY < top || mouseY > bottom) return;

    ctx.save();
    ctx.beginPath();
    ctx.setLineDash([4, 4]);
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(148, 163, 184, 0.6)';

    // Vertical line (X-axis pointer)
    ctx.moveTo(mouseX, top);
    ctx.lineTo(mouseX, bottom);

    // Horizontal line (Y-axis pointer)
    ctx.moveTo(left, mouseY);
    ctx.lineTo(right, mouseY);

    ctx.stroke();
    ctx.restore();

    // Draw Y-axis Price Pointer Tag
    const priceVal = y.getValueForPixel(mouseY);
    if (priceVal !== undefined && priceVal !== null && !isNaN(priceVal)) {
      const priceText = formatCurrency(priceVal);
      ctx.save();
      ctx.font = '600 11px Inter, sans-serif';
      const textWidth = ctx.measureText(priceText).width;
      const padX = 6;
      const badgeW = textWidth + padX * 2;
      const badgeH = 20;

      const badgeX = right - badgeW;
      const badgeY = Math.min(Math.max(mouseY - badgeH / 2, top), bottom - badgeH);

      ctx.fillStyle = '#3861fb';
      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(badgeX, badgeY, badgeW, badgeH, 4);
      } else {
        ctx.rect(badgeX, badgeY, badgeW, badgeH);
      }
      ctx.fill();

      ctx.fillStyle = '#ffffff';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(priceText, badgeX + badgeW / 2, badgeY + badgeH / 2);
      ctx.restore();
    }
  }
};

async function loadPriceChart(days = 7) {
  currentDays = days;
  const canvas = document.getElementById('price-chart');
  if (!canvas) return;

  try {
    if (priceChartInstance) {
      priceChartInstance.destroy();
    }

    if (!comparisonCoinId) {
      // 1. Single Asset Mode
      const res = await fetchCoinChart(currentCoinId, days);
      const rawPrices = res.prices || [];

      const labels = rawPrices.map(p => {
        const d = new Date(p[0]);
        return days <= 1 ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : d.toLocaleDateString([], { month: 'short', day: 'numeric' });
      });
      const values = rawPrices.map(p => p[1]);

      const isPositive = values.length >= 2 ? values[values.length - 1] >= values[0] : true;
      const strokeColor = isPositive ? '#16c784' : '#ea3943';
      const fillColor = isPositive ? 'rgba(22, 199, 132, 0.08)' : 'rgba(234, 57, 67, 0.08)';

      if (window.Chart) {
        priceChartInstance = new window.Chart(canvas, {
          type: 'line',
          plugins: [crosshairPlugin],
          data: {
            labels: labels,
            datasets: [{
              label: 'Price (USD)',
              data: values,
              borderColor: strokeColor,
              backgroundColor: fillColor,
              borderWidth: 2,
              fill: true,
              tension: 0.15,
              pointRadius: 0,
              pointHoverRadius: 6,
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
              legend: { display: false },
              tooltip: {
                callbacks: {
                  label: (ctx) => ` Price: ${formatCurrency(ctx.parsed.y)}`
                }
              }
            },
            scales: {
              x: {
                grid: { display: false },
                ticks: { color: '#858e96', maxTicksLimit: 8 }
              },
              y: {
                grid: { color: 'rgba(255, 255, 255, 0.06)' },
                ticks: {
                  color: '#858e96',
                  callback: (val) => formatCurrency(val)
                }
              }
            }
          }
        });
      }
    } else {
      // 2. Comparison Mode (Normalized % Performance)
      const [res1, res2] = await Promise.all([
        fetchCoinChart(currentCoinId, days),
        fetchCoinChart(comparisonCoinId, days)
      ]);

      const rawPrices1 = res1.prices || [];
      const rawPrices2 = res2.prices || [];

      if (!rawPrices1.length) return;

      const labels = rawPrices1.map(p => {
        const d = new Date(p[0]);
        return days <= 1 ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : d.toLocaleDateString([], { month: 'short', day: 'numeric' });
      });

      const start1 = rawPrices1[0][1] || 1;
      const values1 = rawPrices1.map(p => ((p[1] - start1) / start1) * 100);

      // Match length of series 2 to series 1
      const start2 = rawPrices2.length ? rawPrices2[0][1] : 1;
      const values2 = rawPrices1.map((p, idx) => {
        const p2Val = rawPrices2[idx] ? rawPrices2[idx][1] : start2;
        return ((p2Val - start2) / start2) * 100;
      });

      const primaryName = currentCoinData ? currentCoinData.name : currentCoinId.toUpperCase();
      const compName = comparisonCoinName || comparisonCoinId.toUpperCase();

      if (window.Chart) {
        priceChartInstance = new window.Chart(canvas, {
          type: 'line',
          plugins: [crosshairPlugin],
          data: {
            labels: labels,
            datasets: [
              {
                label: primaryName,
                data: values1,
                borderColor: '#16c784',
                backgroundColor: 'rgba(22, 199, 132, 0.05)',
                borderWidth: 2.5,
                fill: false,
                tension: 0.15,
                pointRadius: 0,
                pointHoverRadius: 6,
              },
              {
                label: compName,
                data: values2,
                borderColor: '#3861fb',
                backgroundColor: 'rgba(56, 97, 251, 0.05)',
                borderWidth: 2.5,
                fill: false,
                tension: 0.15,
                pointRadius: 0,
                pointHoverRadius: 6,
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
              legend: {
                display: true,
                position: 'top',
                labels: { color: '#858e96', font: { family: 'Inter', size: 12 } }
              },
              tooltip: {
                callbacks: {
                  label: (ctx) => ` ${ctx.dataset.label}: ${ctx.parsed.y >= 0 ? '+' : ''}${ctx.parsed.y.toFixed(2)}%`
                }
              }
            },
            scales: {
              x: {
                grid: { display: false },
                ticks: { color: '#858e96', maxTicksLimit: 8 }
              },
              y: {
                grid: { color: 'rgba(255, 255, 255, 0.06)' },
                ticks: {
                  color: '#858e96',
                  callback: (val) => `${val >= 0 ? '+' : ''}${val.toFixed(1)}%`
                }
              }
            }
          }
        });
      }
    }
  } catch (err) {
    console.error('Error loading price chart:', err);
  }
}

function downloadHistoricalCSV() {
  const user = getStoredUser();
  if (!user) {
    showToast('Please sign in or create an account to export historical CSV data.', 'info');
    openAuthModal('login');
    return;
  }

  if (!lastHistoricalRecords || !lastHistoricalRecords.length) {
    showToast('No historical data records loaded to export.', 'info');
    return;
  }

  const nowStr = new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  const coinName = currentCoinData ? currentCoinData.name : 'Cryptocurrency';
  const headers = ['Date', 'Open Price (USD)', 'High (USD)', 'Low (USD)', 'Close Price (USD)', '24h Volume (USD)', 'Change %', 'Downloaded At'];
  const rows = lastHistoricalRecords.map(r => [
    r.date,
    r.open,
    r.high,
    r.low,
    r.close,
    r.volume.toFixed(2),
    r.changePct.toFixed(2),
    `"${nowStr}"`
  ]);
  const csvString = `# ${coinName} Historical Daily Price Export\n# Downloaded At: ${nowStr}\n\n` + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  const symbol = currentCoinData ? currentCoinData.symbol.toLowerCase() : 'coin';
  link.setAttribute('href', url);
  link.setAttribute('download', `${symbol}_historical_daily_${new Date().toISOString().slice(0,10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  showToast('Historical daily CSV exported successfully!', 'success');
}

function openCompareModal() {
  const modal = document.getElementById('compare-modal');
  if (!modal) return;

  const baseName = currentCoinData ? currentCoinData.name : 'this asset';
  const baseEl = document.getElementById('compare-base-coin-name');
  if (baseEl) baseEl.textContent = baseName;

  const select = document.getElementById('compare-coin-select');
  if (select) {
    for (let i = 0; i < select.options.length; i++) {
      const opt = select.options[i];
      if (opt.value === currentCoinId) {
        opt.disabled = true;
      } else {
        opt.disabled = false;
      }
    }
    for (let i = 0; i < select.options.length; i++) {
      if (!select.options[i].disabled) {
        select.selectedIndex = i;
        break;
      }
    }
  }

  modal.classList.remove('hidden');
}

function closeCompareModal() {
  const modal = document.getElementById('compare-modal');
  if (modal) modal.classList.add('hidden');
}

function applyComparison() {
  const select = document.getElementById('compare-coin-select');
  if (!select || select.selectedIndex < 0) return;

  const opt = select.options[select.selectedIndex];
  comparisonCoinId = select.value;
  comparisonCoinName = opt.text.split(' (')[0];

  closeCompareModal();

  const pillPrice = document.getElementById('pill-price-btn');
  const pillCompare = document.getElementById('pill-compare-btn');
  const labelText = document.getElementById('compare-btn-text');
  const btnClear = document.getElementById('btn-clear-compare');

  if (pillPrice) pillPrice.classList.remove('active');
  if (pillCompare) pillCompare.classList.add('active');
  if (labelText) labelText.textContent = `vs ${comparisonCoinName}`;
  if (btnClear) btnClear.classList.remove('hidden');

  loadPriceChart(currentDays);
  showToast(`Comparing ${currentCoinData ? currentCoinData.name : 'Asset'} vs ${comparisonCoinName}`, 'info');
}

function clearComparison() {
  comparisonCoinId = null;
  comparisonCoinName = null;

  const pillPrice = document.getElementById('pill-price-btn');
  const pillCompare = document.getElementById('pill-compare-btn');
  const labelText = document.getElementById('compare-btn-text');
  const btnClear = document.getElementById('btn-clear-compare');

  if (pillPrice) pillPrice.classList.add('active');
  if (pillCompare) pillCompare.classList.remove('active');
  if (labelText) labelText.textContent = 'Compare';
  if (btnClear) btnClear.classList.add('hidden');

  loadPriceChart(currentDays);
}

function setupEventListeners() {
  setupTabSwitchers();

  document.querySelectorAll('.tf-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const days = parseInt(btn.getAttribute('data-days'), 10);
      loadPriceChart(days);
    });
  });

  const watchBtn = document.getElementById('watchlist-btn');
  if (watchBtn) {
    watchBtn.addEventListener('click', () => toggleWatchlist(currentCoinId));
  }

  const alertBtn = document.getElementById('set-alert-btn');
  if (alertBtn) {
    alertBtn.addEventListener('click', () => {
      const name = document.getElementById('coin-name')?.textContent || currentCoinId;
      const symbol = document.getElementById('coin-symbol')?.textContent || '';
      const priceText = document.getElementById('coin-price')?.textContent || '';
      openAlertModal(currentCoinId, symbol, name, priceText.replace(/[^0-9.]/g, ''));
    });
  }

  const shareBtn = document.getElementById('share-btn');
  if (shareBtn) {
    shareBtn.addEventListener('click', () => {
      if (navigator.clipboard) {
        navigator.clipboard.writeText(window.location.href);
        alert('Coin page URL copied to clipboard!');
      } else {
        alert(window.location.href);
      }
    });
  }

  const exportHistBtn = document.getElementById('btn-export-historical-csv');
  if (exportHistBtn) {
    exportHistBtn.addEventListener('click', downloadHistoricalCSV);
  }

  const pillPrice = document.getElementById('pill-price-btn');
  if (pillPrice) pillPrice.addEventListener('click', clearComparison);

  const pillCompare = document.getElementById('pill-compare-btn');
  if (pillCompare) pillCompare.addEventListener('click', openCompareModal);

  const btnClear = document.getElementById('btn-clear-compare');
  if (btnClear) btnClear.addEventListener('click', clearComparison);

  const closeCompare = document.getElementById('close-compare-modal');
  if (closeCompare) closeCompare.addEventListener('click', closeCompareModal);

  const cancelCompare = document.getElementById('cancel-compare-btn');
  if (cancelCompare) cancelCompare.addEventListener('click', closeCompareModal);

  const applyCompare = document.getElementById('apply-compare-btn');
  if (applyCompare) applyCompare.addEventListener('click', applyComparison);
}
