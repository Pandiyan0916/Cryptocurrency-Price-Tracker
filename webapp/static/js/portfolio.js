/**
 * portfolio.js - Portfolio manager with live P&L calculation, allocation doughnut chart, and CSV export.
 */

import { fetchGlobalStats, fetchMarkets } from './api.js';
import { formatCurrency, formatCompactNumber, formatPercentage, formatQuantity, getCoinLogoUrl } from './format.js';
import { initTheme } from './theme.js';
import { initGlobalSearch } from './search.js';
import { initAuth, getStoredUser, openAuthModal, showToast } from './auth.js';
import { initCurrencySelector } from './currency.js';

const PORTFOLIO_KEY = 'coinpulse_portfolio';
let doughnutChartInstance = null;
let availableCoinsList = [];

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initGlobalSearch();
  initAuth();
  initCurrencySelector();
  loadHeaderGlobal();
  loadPortfolioPage();
  setupPortfolioEventListeners();

  window.addEventListener('currencyChanged', () => {
    loadPortfolioPage();
  });

  window.addEventListener('userAuthStateChanged', () => {
    loadPortfolioPage();
  });
});

function getPortfolioHoldings() {
  try {
    return JSON.parse(localStorage.getItem(PORTFOLIO_KEY) || '[]');
  } catch (e) {
    return [];
  }
}

function savePortfolioHoldings(holdings) {
  localStorage.setItem(PORTFOLIO_KEY, JSON.stringify(holdings));
  loadPortfolioPage();
}

function addHolding(coinId, symbol, name, amount, buyPrice) {
  let list = getPortfolioHoldings();
  const existingIdx = list.findIndex(h => h.id === coinId);
  if (existingIdx >= 0) {
    list[existingIdx].amount += amount;
    list[existingIdx].buyPrice = buyPrice;
  } else {
    list.push({ id: coinId, symbol, name, amount, buyPrice });
  }
  savePortfolioHoldings(list);
}

function deleteHolding(coinId) {
  let list = getPortfolioHoldings().filter(h => h.id !== coinId);
  savePortfolioHoldings(list);
}

async function loadHeaderGlobal() {
  try {
    const data = await fetchGlobalStats();
    const stats = data.data;
    if (document.getElementById('global-cryptos')) {
      document.getElementById('global-cryptos').textContent = stats.active_cryptocurrencies ? stats.active_cryptocurrencies.toLocaleString() : '50';
    }
    if (document.getElementById('global-mcap')) {
      document.getElementById('global-mcap').textContent = formatCompactNumber(stats.total_market_cap_usd || 0);
    }
    if (document.getElementById('global-vol')) {
      document.getElementById('global-vol').textContent = formatCompactNumber(stats.total_volume_usd || 0);
    }
    const badge = document.getElementById('data-source-badge');
    if (badge) badge.textContent = `Source: ${data.source.toUpperCase()}`;
  } catch (err) {
    console.error('Global stats error:', err);
  }
}

async function populateCoinSelect() {
  const select = document.getElementById('coin-select');
  if (!select) return;

  try {
    const res = await fetchMarkets(1, 50);
    availableCoinsList = res.data || [];
    if (availableCoinsList.length) {
      select.innerHTML = availableCoinsList.map(c => `
        <option value="${c.id}" data-price="${c.current_price || 0}" data-symbol="${c.symbol}" data-name="${escapeHtml(c.name)}">
          ${escapeHtml(c.name)} (${c.symbol.toUpperCase()}) - ${formatCurrency(c.current_price)}
        </option>
      `).join('');
      updatePriceInputFromSelect();
    }
  } catch (err) {
    console.warn('Failed to load live coins list for portfolio select:', err);
  }
}

function updatePriceInputFromSelect() {
  const select = document.getElementById('coin-select');
  const priceInput = document.getElementById('holding-price');
  if (select && priceInput && select.selectedIndex >= 0) {
    const opt = select.options[select.selectedIndex];
    const price = opt.getAttribute('data-price');
    if (price && (!priceInput.value || priceInput.value === '0')) {
      priceInput.value = parseFloat(price).toFixed(2);
    }
  }
}

async function loadPortfolioPage() {
  const tbody = document.getElementById('portfolio-tbody');
  if (!tbody) return;

  const holdings = getPortfolioHoldings();
  if (holdings.length === 0) {
    document.getElementById('total-value').textContent = '$0.00';
    document.getElementById('total-pnl').textContent = '$0.00 (0.00%)';
    document.getElementById('total-pnl').className = 'text-success font-semibold';

    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="text-center padding-xl">
          <i class="fas fa-wallet icon-3x text-muted margin-bottom-md"></i>
          <h3>Your Portfolio is Empty</h3>
          <p class="text-muted margin-bottom-md">Add your crypto holdings to calculate live profit/loss and view asset allocation.</p>
          <button class="btn btn-primary" id="open-add-modal-btn"><i class="fas fa-plus"></i> Add Transaction</button>
        </td>
      </tr>
    `;

    const emptyAddBtn = document.getElementById('open-add-modal-btn');
    if (emptyAddBtn) emptyAddBtn.addEventListener('click', openModal);
    renderAllocationChart([], [], []);
    return;
  }

  try {
    const res = await fetchMarkets(1, 100);
    const marketMap = new Map((res.data || []).map(c => [c.id, c]));

    let totalValue = 0;
    let totalCost = 0;
    const chartLabels = [];
    const chartData = [];
    const chartColors = ['#16c784', '#3861fb', '#f59e0b', '#ec4899', '#8b5cf6', '#06b6d4', '#e11d48'];

    const rows = holdings.map((h, idx) => {
      const market = marketMap.get(h.id);
      const currentPrice = market ? (market.current_price || h.buyPrice) : h.buyPrice;
      const value = h.amount * currentPrice;
      const cost = h.amount * h.buyPrice;
      const pnl = value - cost;
      const pnlPercent = cost > 0 ? (pnl / cost) * 100 : 0;

      totalValue += value;
      totalCost += cost;

      chartLabels.push(h.name);
      chartData.push(value);

      const pnlClass = pnl >= 0 ? 'text-success' : 'text-danger';

      return `
        <tr>
          <td>
            <a href="coin.html?id=${encodeURIComponent(h.id)}" class="coin-name-cell">
              <img src="${getCoinLogoUrl(market)}" class="coin-icon" alt="${h.name}">
              <span class="coin-name">${escapeHtml(h.name)}</span>
              <span class="coin-symbol">${escapeHtml(h.symbol.toUpperCase())}</span>
            </a>
          </td>
          <td class="text-right font-semibold">${formatQuantity(h.amount)}</td>
          <td class="text-right">${formatCurrency(h.buyPrice)}</td>
          <td class="text-right font-semibold">${formatCurrency(currentPrice)}</td>
          <td class="text-right font-semibold">${formatCurrency(value)}</td>
          <td class="text-right ${pnlClass}">${pnl >= 0 ? '+' : ''}${formatCurrency(pnl)} (${formatPercentage(pnlPercent)})</td>
          <td class="text-right">
            <button class="btn btn-sm btn-outline delete-btn" data-id="${h.id}">Delete</button>
          </td>
        </tr>
      `;
    }).join('');

    tbody.innerHTML = rows;

    tbody.querySelectorAll('.delete-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        if (id) deleteHolding(id);
      });
    });

    const totalPnl = totalValue - totalCost;
    const totalPnlPercent = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0;

    document.getElementById('total-value').textContent = formatCurrency(totalValue);
    const pnlEl = document.getElementById('total-pnl');
    pnlEl.textContent = `${totalPnl >= 0 ? '+' : ''}${formatCurrency(totalPnl)} (${formatPercentage(totalPnlPercent)})`;
    pnlEl.className = totalPnl >= 0 ? 'text-success font-semibold' : 'text-danger font-semibold';

    renderAllocationChart(chartLabels, chartData, chartColors);

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Error calculating portfolio: ${escapeHtml(err.message)}</td></tr>`;
  }
}

function renderAllocationChart(labels, data, colors) {
  const canvas = document.getElementById('allocation-chart');
  if (!canvas || !window.Chart) return;

  if (doughnutChartInstance) {
    doughnutChartInstance.destroy();
  }

  doughnutChartInstance = new window.Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: colors.slice(0, labels.length),
        borderWidth: 2,
        borderColor: '#171924'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#858e96', font: { family: 'Inter', size: 11 } }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${formatCurrency(ctx.parsed)}`
          }
        }
      }
    }
  });
}

function downloadPortfolioCSV() {
  const user = getStoredUser();
  if (!user) {
    showToast('Please sign in or create an account to export portfolio CSV data.', 'info');
    openAuthModal('login');
    return;
  }

  const holdings = getPortfolioHoldings();
  if (holdings.length === 0) {
    showToast('Your portfolio is currently empty.', 'info');
    return;
  }

  const nowStr = new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  const headers = ['ID', 'Symbol', 'Name', 'Amount Held', 'Buy Price (USD)', 'Downloaded At'];
  const rows = holdings.map(h => [
    h.id,
    h.symbol ? h.symbol.toUpperCase() : '',
    `"${(h.name || '').replace(/"/g, '""')}"`,
    formatQuantity(h.amount),
    h.buyPrice,
    `"${nowStr}"`
  ]);

  const csvString = `# CoinPulse Portfolio Export\n# Downloaded At: ${nowStr}\n\n` + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `coinpulse_portfolio_${new Date().toISOString().slice(0,10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  showToast('Portfolio CSV exported successfully!', 'success');
}

function openModal() {
  const user = getStoredUser();
  if (!user) {
    showToast('Please sign in or create an account to add portfolio transactions.', 'info');
    openAuthModal('login');
    return;
  }

  const modal = document.getElementById('add-modal');
  if (modal) {
    populateCoinSelect();
    modal.classList.remove('hidden');
  }
}

function closeModal() {
  const modal = document.getElementById('add-modal');
  if (modal) modal.classList.add('hidden');
}

function setupPortfolioEventListeners() {
  const addBtn = document.getElementById('add-holding-btn');
  if (addBtn) addBtn.addEventListener('click', openModal);

  const closeBtn = document.getElementById('modal-close-btn');
  if (closeBtn) closeBtn.addEventListener('click', closeModal);

  const cancelBtn = document.getElementById('modal-cancel-btn');
  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  const selectEl = document.getElementById('coin-select');
  if (selectEl) selectEl.addEventListener('change', updatePriceInputFromSelect);

  const exportBtn = document.getElementById('export-csv-btn');
  if (exportBtn) exportBtn.addEventListener('click', downloadPortfolioCSV);

  const form = document.getElementById('add-holding-form');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const select = document.getElementById('coin-select');
      const amountInput = document.getElementById('holding-amount');
      const priceInput = document.getElementById('holding-price');

      if (!select || select.selectedIndex < 0) return;

      const opt = select.options[select.selectedIndex];
      const coinId = select.value;
      const coinName = opt.getAttribute('data-name') || opt.text.split(' (')[0];
      const coinSymbol = opt.getAttribute('data-symbol') || coinId.slice(0, 4);
      const amount = parseFloat(amountInput.value);
      const buyPrice = parseFloat(priceInput.value);

      if (coinId && amount > 0 && buyPrice >= 0) {
        addHolding(coinId, coinSymbol, coinName, amount, buyPrice);
        closeModal();
        form.reset();
      }
    });
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
